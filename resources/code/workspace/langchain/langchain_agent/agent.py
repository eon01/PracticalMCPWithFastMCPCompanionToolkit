# agent.py
import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

LLM = os.getenv("LLM", "gpt-4o-mini")

agent = create_agent(
    f"openai:{LLM}",
    middleware=[
        SummarizationMiddleware(
            model=f"openai:{LLM}",
            trigger=("tokens", 1000),
        )
    ],
    checkpointer=MemorySaver(),
)


def main() -> None:
    print("Agent ready. Type 'exit' or 'quit' to stop.\n")

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

        response = agent.invoke(
            {"messages": [{"role": "user", "content": user_input}]},
            config={"configurable": {"thread_id": "default"}},
        )

        answer = response["messages"][-1].content
        print(f"Agent: {answer}\n")


if __name__ == "__main__":
    main()
