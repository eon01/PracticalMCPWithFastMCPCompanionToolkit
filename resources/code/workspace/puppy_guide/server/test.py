import asyncio
from fastmcp import Client
from fastmcp.exceptions import ToolError

async def main():
    client = Client("http://localhost:8000/mcp")

    async with client:
        # This should succeed — labrador is a known breed
        result = await client.call_tool(
            "dog_to_human_age",
            {"age": 5, "breed": "labrador"},
        )
        print(f"Labrador age 5 = {result.data} human years")

        # This should fail — poodle is not in our breed list
        result = await client.call_tool(
            "dog_to_human_age",
            {"age": 5, "breed": "poodle"},
            raise_on_error=False,
        )
        if result.is_error:
            print(f"Tool failed: {result.content[0].text}")

asyncio.run(main())
