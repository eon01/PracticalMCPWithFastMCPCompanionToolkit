# agent.py
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain.agents.middleware import SummarizationMiddleware
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

load_dotenv()

LLM = os.getenv("LLM", "gpt-5-mini")
SERVER_PATH = str(Path(__file__).resolve().parent / "server.py")


def _approve_tool_calls(hitl_request: dict) -> list[dict]:
    """Print each pending tool call and wait for the user to approve."""
    for tool_call in hitl_request["action_requests"]:
        print(f"Tool requested: {tool_call['name']}")
        input("Press Enter to approve... ")
    return [{"type": "approve"}] * len(hitl_request["action_requests"])


async def main() -> None:
    client = MultiServerMCPClient(
        {
            "weather": {
                "transport": "stdio",
                "command": sys.executable,
                "args": [SERVER_PATH],
            }
        }
    )

    tools = await client.get_tools()

    agent = create_agent(
        f"openai:{LLM}",
        tools,
        checkpointer=MemorySaver(),
        middleware=[
            SummarizationMiddleware(model=f"openai:{LLM}", trigger=("tokens", 1000)),
            HumanInTheLoopMiddleware(
                interrupt_on={
                    "get_air_quality": {"allowed_decisions": ["approve"]},
                    "get_temperature": {"allowed_decisions": ["approve"]},
                }
            ),
        ],
    )

    print("Weather & Air Quality Agent. Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        config = {"configurable": {"thread_id": "default"}}
        inputs: dict | Command = {"messages": [{"role": "user", "content": user_input}]}

        while True:
            await agent.ainvoke(inputs, config=config)
            state = agent.get_state(config)
            pending_interrupts = [
                interrupt
                for task in state.tasks
                for interrupt in task.interrupts
            ]

            if pending_interrupts:
                approved_decisions = _approve_tool_calls(pending_interrupts[0].value)
                inputs = Command(resume={"decisions": approved_decisions})
            else:
                answer = state.values["messages"][-1].content
                print(f"Agent: {answer}\n")
                break


if __name__ == "__main__":
    asyncio.run(main())
