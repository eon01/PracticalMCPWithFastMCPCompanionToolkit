from fastmcp import FastMCP

mcp = FastMCP("My MCP Server")

@mcp.tool
def sum(a: int, b: int) -> int:
    """Returns the sum of two numbers."""
    return a + b

if __name__ == "__main__":
    mcp.run(transport="http", host="localhost", port=8000)
