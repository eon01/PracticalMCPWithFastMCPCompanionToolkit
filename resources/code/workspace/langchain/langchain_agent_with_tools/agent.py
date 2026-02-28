# agent.py
import os

import httpx
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain.agents.middleware import SummarizationMiddleware
from langchain.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

load_dotenv()

LLM = os.getenv("LLM", "gpt-5-mini")


def _get_coordinates(location: str) -> tuple[float, float]:
    """Resolve a place name to (latitude, longitude) via the Open-Meteo Geocoding API."""
    response = httpx.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": location, "count": 1, "language": "en", "format": "json"},
    )
    data = response.json()
    if "results" in data and len(data["results"]) > 0:
        return data["results"][0]["latitude"], data["results"][0]["longitude"]
    raise ValueError(f"Could not find coordinates for location: {location}")


@tool
def get_air_quality(location: str) -> str:
    """Get air quality information based on a location."""
    latitude, longitude = _get_coordinates(location)
    response = httpx.get(
        "https://air-quality-api.open-meteo.com/v1/air-quality",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "pm10,pm2_5",
            "forecast_days": 1,
        },
    )
    data = response.json()
    if "hourly" in data and "pm10" in data["hourly"] and "pm2_5" in data["hourly"]:
        pm10 = data["hourly"]["pm10"][0]
        pm2_5 = data["hourly"]["pm2_5"][0]
        result = f"PM10: {pm10} μg/m³, PM2.5: {pm2_5} μg/m³"
    else:
        result = "Air quality data not available"
    return f"Air quality in {location}: {result}"


@tool
def get_temperature(location: str) -> str:
    """Get the current temperature for a location."""
    latitude, longitude = _get_coordinates(location)
    response = httpx.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "temperature_2m",
            "forecast_days": 1,
        },
    )
    data = response.json()
    if "hourly" in data and "temperature_2m" in data["hourly"]:
        temperature = data["hourly"]["temperature_2m"][0]
        result = f"Temperature: {temperature} °C"
    else:
        result = "Temperature data not available"
    return f"Temperature in {location}: {result}"


agent = create_agent(
    f"openai:{LLM}",
    tools=[get_air_quality, get_temperature],
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


def _approve_tool_calls(hitl_request: dict) -> list[dict]:
    """Print each pending tool call and wait for the user to approve."""
    for tool_call in hitl_request["action_requests"]:
        print(f"Tool requested: {tool_call['name']}")
        input("Press Enter to approve... ")
    return [{"type": "approve"}] * len(hitl_request["action_requests"])


def main() -> None:
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
            agent.invoke(inputs, config=config)
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
    main()
