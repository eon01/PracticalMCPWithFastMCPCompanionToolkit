import asyncio
import json
import logging
import os

from dotenv import load_dotenv
from openai import OpenAI

from fastmcp import Client

from handlers.elicitation import elicitation_handler
from handlers.logging import log_handler
from handlers.progress import progress_handler
from handlers.sampling import sampling_handler

logging.basicConfig(level=logging.WARNING, format="%(message)s")
logging.getLogger("mcp.server").setLevel(logging.INFO)

load_dotenv()

# Read configuration from environment
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Your OpenAI API key
MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")  # Model for chat
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "10"))
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT")

mcp_client = Client(
    MCP_SERVER_URL,
    # These handlers respond to server requests:
    elicitation_handler=elicitation_handler,
    sampling_handler=sampling_handler,  # When server asks for user input
    log_handler=log_handler,  # When server sends logs
    progress_handler=progress_handler,  # When server sends progress updates
)  # type: ignore


async def get_tools_for_openai(client: Client) -> list:
    mcp_tools = await client.list_tools()

    openai_tools = []
    for tool in mcp_tools:
        openai_tools.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            }
        )

    return openai_tools


async def chat(
    user_question: str, openai_client: OpenAI, tools: list, messages: list
) -> str:
    messages.append({"role": "user", "content": user_question})

    while True:
        # Call OpenAI
        response = openai_client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto",  # Let OpenAI decide when to use tools
        )

        # Extract assistant's message (could contain tool calls)
        assistant_message = response.choices[0].message
        # Add to history
        messages.append(assistant_message)

        # If no tool calls, we have the final answer!
        if not assistant_message.tool_calls:
            return assistant_message.content or ""

        # Process each tool call
        for tool_call in assistant_message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)

            # Call the MCP tool
            try:
                result = await mcp_client.call_tool(tool_name, tool_args)
                result_text = str(result)
            except Exception as e:
                result_text = f"Error: {e}"

            # Add tool result to conversation
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": result_text,
                }
            )


async def run_repl():
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    async with mcp_client:
        # Get available tools once at startup
        tools = await get_tools_for_openai(mcp_client)

        print("Try asking: 'How old is my 5-year-old labrador in human years?'")
        # The REPL loop
        while True:
            try:
                user_input = input("Ask PuppyGuide> ").strip()
                print("[Thinking...]")
                answer = await chat(user_input, openai_client, tools, messages)
                print("[Assistant]:", answer)
                if len(messages) > MAX_HISTORY + 1:
                    messages = [messages[0]]

            except KeyboardInterrupt:
                print("Goodbye!")
                break


async def main():
    await run_repl()


if __name__ == "__main__":
    asyncio.run(main())
