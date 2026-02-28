import asyncio
import json
import logging
import os

from dotenv import load_dotenv
from openai import OpenAI

from fastmcp import Client

from handlers import elicitation_handler
from handlers import log_handler
from handlers import progress_handler
from handlers import sampling_handler

load_dotenv()

# Read configuration from environment
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Your OpenAI API key
MODEL = os.getenv("MODEL", "gpt-5-mini")  # Model for chat

# Set up logging - only show warnings by default
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.WARNING,
    format="%(levelname)s - %(message)s",
)

# Max conversation history to keep (for cost control)
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "10"))

mcp_client = Client(
    MCP_SERVER_URL,
    # These handlers respond to server requests:
    elicitation_handler=elicitation_handler,  # When server needs user input
    sampling_handler=sampling_handler,  # When server needs LLM help
    log_handler=log_handler,  # When server sends log messages
    progress_handler=progress_handler,  # When server reports progress
)  # type: ignore


async def get_tools_for_openai(client: Client) -> list:
    """
    Fetch tools from MCP server and convert to OpenAI format.

    MCP tool format:
        {name: "search_movies", description: "...", inputSchema: {...}}

    OpenAI tool format:
        {type: "function", function: {name: "...", description: "...", parameters: {...}}}
    """
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
    """
    Handle one conversation turn with OpenAI + MCP tools.

    The flow:
      1. Add user's question to conversation history
      2. Send to OpenAI with available tools
      3. If OpenAI wants to call tools -> call MCP tools -> feed results back
      4. Repeat until OpenAI gives a final answer

    Args:
        user_question: What the user asked
        openai_client: OpenAI client for chat completions
        tools: Available tools in OpenAI format
        messages: Conversation history (modified in place!)

    Returns:
        The assistant's final text response
    """
    # Add user's question to the conversation
    messages.append({"role": "user", "content": user_question})

    # Loop until we get a final response (not a tool call)
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
                # Extract the text from the result's content blocks
                result_text = "\n".join(
                    block.text for block in result.content if hasattr(block, "text")
                )
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

        if DEBUG_MODE:
            print(
                f"[DEBUG] Sending {len(assistant_message.tool_calls)} tool result(s) back to OpenAI..."
            )


async def run_repl():
    """
    Run the interactive REPL loop.

    IMPORTANT: The entire REPL runs INSIDE `async with mcp_client:`.
    This keeps one session alive so features like favorites persist!
    """
    print("=" * 60)
    print("Netflix MCP Client (Full Version)")
    print("=" * 60)
    print("Ask questions about Netflix movies!")
    print("Try: 'What are the top 5 movies?' or 'Add Glass Onion to favorites'")
    print("Commands: 'quit' to exit, 'clear' to reset conversation")
    print()

    # Create OpenAI client
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

    messages = [
        {
            "role": "system",
            "content": "You are a helpful Netflix assistant. "
            "Use the available tools to answer questions about movies and manage favorites. "
            "For analysis tasks (trends, performance, comparisons), check list_prompts first - "
            "prompts provide structured templates that format the data for you.",
        }
    ]

    async with mcp_client:
        # Get available tools once at startup
        tools = await get_tools_for_openai(mcp_client)
        print(f"Connected! {len(tools)} tools available.\n")

        # The REPL loop
        while True:
            try:
                user_input = input("Netflix> ").strip()

                # Handle commands
                if not user_input:
                    continue
                if user_input.lower() in ("quit", "exit", "q"):
                    print("Goodbye!")
                    break
                if user_input.lower() == "clear":
                    messages = [messages[0]]  # Keep system prompt, clear rest
                    print("Conversation cleared.\n")
                    continue

                # Process the question
                print()
                answer = await chat(user_input, openai_client, tools, messages)
                print(answer)
                print()

                # Keep conversation history reasonable to control costs
                if len(messages) > MAX_HISTORY + 1:
                    messages = [messages[0]]
                    print("[Conversation history cleared to manage costs]\n")

            except KeyboardInterrupt:
                print("\nGoodbye!")
                break


async def main():
    """Main entry point"""
    await run_repl()


if __name__ == "__main__":
    asyncio.run(main())

# Questions to try in the REPL:
# What are the top 10 most viewed movies?
# What are the top 5 movies by number of views?
# Show me the top 3 movies by hours viewed
# What are the global viewing stats for 'Leave the World Behind'?
# Add 'Leave the World Behind' to my favorites
# Show me my favorites list
# Add 'Extraction 2' to favorites and then list my favorites
# Add the 1st ranked movie in terms of hours viewed to my favorites
# Summarize the plot of 'KPop Demon Hunters'
