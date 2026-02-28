import asyncio
import json
import os
import sys
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from openai import OpenAI

async def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python client.py <your question>")

    query = sys.argv[1]
    openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = "gpt-5-mini"
    url = "http://127.0.0.1:8000/mcp"

    # Connect to the MCP server using the streamable HTTP transport
    async with streamable_http_client(url) as (read, write, _):
        # Create an MCP client session
        async with ClientSession(read, write) as session:
            # Initialize the session (handshake with the server)
            await session.initialize()

            # Discover available tools from the MCP server
            available_mcp_tools = (await session.list_tools()).tools

            # Covert MCP tools to OpenAI tool format
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": mcp_tool.name,
                        "description": mcp_tool.description,
                        "parameters": mcp_tool.inputSchema,
                    },
                }
                for mcp_tool in available_mcp_tools
            ]

            # Define the initial messages for the chat completion
            messages = [{"role": "user", "content": query}]

            # Create the initial chat completion request
            response = openai.chat.completions.create(
                model=model, messages=messages, tools=tools
            )

            # Tool calling loop
            while response.choices[0].message.tool_calls:
                messages.append(response.choices[0].message)

                for tool_call in response.choices[0].message.tool_calls:
                    # Get the tool name
                    tool_name = tool_call.function.name
                    # Get the tool arguments
                    tool_args = json.loads(tool_call.function.arguments)
                    # Get the tool ID
                    tool_call_id = tool_call.id

                    # Call the tool on the MCP server
                    result = await session.call_tool(
                        tool_name,
                        tool_args,
                    )

                    # Get the tool result
                    mcp_tool_content = str(result.content)

                    # Append the tool result to the messages with the tool call ID
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": mcp_tool_content,
                        }
                    )

                response = openai.chat.completions.create(
                    model=model, messages=messages, tools=tools
                )

            openai_response = response.choices[0].message.content
            print("OpenAI response:")
            print(openai_response)


if __name__ == "__main__":
    asyncio.run(main())
