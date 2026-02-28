# Import the FastMCP class from the MCP SDK
from mcp.server.fastmcp import FastMCP

# Create a new MCP server instance
mcp_server = FastMCP("Calculator Server")

# Add a tool
@mcp_server.tool()
def sum(a, b):
    """Returns the sum of two numbers."""
    return int(a) + int(b)

# Start the MCP server
if __name__ == "__main__": 
  mcp_server.run(transport="streamable-http")
