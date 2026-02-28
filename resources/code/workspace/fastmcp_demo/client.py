import asyncio
from fastmcp import Client

client = Client("http://localhost:8000/mcp")

async def call_sum(a: int, b: int):
    async with client:
        result = await client.call_tool("sum", {"a": a, "b": b})
        print(f"Execution result: {result}")

asyncio.run(call_sum(3, 5))
