import os
from difflib import get_close_matches
from typing import Annotated

from dotenv import load_dotenv
from pydantic import Field

from fastmcp import Context
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

load_dotenv()

mcp = FastMCP(
    name=os.getenv("MCP_NAME"),
    instructions=os.getenv("MCP_INSTRUCTIONS"),
)


BREED_MULTIPLIERS = {
    "labrador": 7,
    "chihuahua": 5,
    "german shepherd": 8,
    "bulldog": 6,
}


def get_breed_multiplier(breed: str) -> int | None:
    """Fetch the age multiplier for a given dog breed."""
    return BREED_MULTIPLIERS.get(breed.lower())


@mcp.tool
async def dog_to_human_age(
    age: Annotated[int, Field(ge=0, le=30, description="The dog's age in years")],
    breed: Annotated[str, Field(description="The dog's breed")],
    ctx: Context,
    # New optional parameter for the dog's name
    name: Annotated[str | None, Field(description="The dog's name")] = None,
) -> str:
    """Calculate the real age of a dog in human years based on its breed."""

    total_steps = 4

    # If a name is provided, store it in session state for future calls
    if name:
        await ctx.set_state("dog_name", name)
    else:
        # No name provided — check if we stored one in a previous call
        name = await ctx.get_state("dog_name")

    # Progress: breed lookup
    await ctx.report_progress(
        progress=0,
        total=total_steps,
        message=f"Looking up breed multiplier for '{breed}'",
    )
    await ctx.info(f"Looking up breed multiplier for '{breed}'")

    multiplier = get_breed_multiplier(breed)

    if multiplier is None:
        # Look for 1 similar breed name
        suggestions = get_close_matches(
            breed.lower(), BREED_MULTIPLIERS.keys(), n=1, cutoff=0.6
        )

        if suggestions:
            await ctx.info(
                f"Breed '{breed}' not found, but found similar: {suggestions}"
            )
            result = await ctx.elicit(
                f"Breed '{breed}' not found. Did you mean one of these: {', '.join(suggestions)}?",
                response_type=suggestions,
            )
            if result.action == "accept":
                breed = result.data
                multiplier = BREED_MULTIPLIERS[breed]
            elif result.action == "decline":
                await ctx.info(f"User declined to select a similar breed for '{breed}'")
                raise ToolError(
                    f"Breed '{breed}' not found. User declined to select a suggestion."
                )
            elif result.action == "cancel":
                await ctx.info(
                    f"User cancelled the operation after breed '{breed}' was not found"
                )
                raise ToolError(
                    f"Breed '{breed}' not found. Operation cancelled by user."
                )
        else:
            raise ToolError(f"Breed '{breed}' not found and no similar breeds found.")

    await ctx.report_progress(
        progress=1, total=total_steps, message="Multiplier resolved"
    )

    human_age = age * multiplier

    await ctx.report_progress(
        progress=2, total=total_steps, message="Generating life-stage tip"
    )
    try:
        tip_result = await ctx.sample(
            messages=f"A {breed} dog is {age} years old",
            system_prompt=(
                "You are a veterinary expert. Given a dog's breed and age, "
                "give one short, practical health or lifestyle tip for that life stage. "
                "One sentence only."
            ),
        )
        tip = tip_result.text if tip_result.text else ""
    except Exception:
        tip = ""

    await ctx.report_progress(
        progress=total_steps,
        total=total_steps,
        message="Done",
    )

    # If a name was provided, include it in the response.
    if name:
        return (
            f"{name} is a {age}-year-old {breed} and is approximately {human_age} years old in human years. "
            f"Health tip: {tip}"
        )
    # Otherwise, return a generic message.
    else:
        return (
            f"A {age}-year-old {breed} is approximately {human_age} years old in human years. "
            f"Health tip: {tip}"
        )
