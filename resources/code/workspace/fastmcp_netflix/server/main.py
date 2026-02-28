import os

from dotenv import load_dotenv
from key_value.aio.stores.redis import RedisStore

from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware
from fastmcp.server.middleware import MiddlewareContext
from fastmcp.server.transforms import PromptsAsTools
from fastmcp.server.transforms import ResourcesAsTools

from components import register_prompts
from components import register_resources
from components import register_tools
from database import db_lifespan

# Load environment variables from .env
load_dotenv()


# Redis store for persistent session state (shared across all server instances)
redis_store = RedisStore(url=os.getenv("REDIS_URL", "redis://localhost:6379"))


class DebugToolMiddleware(Middleware):
    """Print tool calls when DEBUG=true environment variable is set."""

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        """Intercept tool calls and log them before execution."""
        if os.getenv("DEBUG", "false").lower() == "true":
            tool_name = context.message.name
            args = context.message.arguments
            print(f"🔧 Tool called: {tool_name}({args})")

        # Continue to the actual tool execution
        result = await call_next(context)
        return result


mcp = FastMCP(
    name="Netflix MCP Server",
    lifespan=db_lifespan,
    list_page_size=10,
    session_state_store=redis_store,
    instructions=os.getenv("MCP_SERVER_INSTRUCTIONS"),
)

# Use if you want to use OpenAI for sampling in the server as a fallback
# when no tools can handle a request.
# from fastmcp.client.sampling.handlers.openai import OpenAISamplingHandler
# sampling_handler = OpenAISamplingHandler(default_model="gpt-5-mini")
# mcp.sampling_handler = sampling_handler
# mcp.sampling_handler_behavior = "fallback"

if os.getenv("DEBUG", "false").lower() == "true":
    mcp.add_middleware(DebugToolMiddleware())

# Register all MCP components
register_tools(mcp)
register_resources(mcp)
register_prompts(mcp)

mcp.add_transform(ResourcesAsTools(mcp))
mcp.add_transform(PromptsAsTools(mcp))

# Expose ASGI app for uvicorn so --reload works with stateful sessions.
# `fastmcp run --reload` forces stateless mode (no mcp-session-id header),
# causing a fresh uuid4() key per request → state is always lost even with Redis.
#
# Dev:  .venv/bin/python -m uvicorn main:app --reload --port 8000
# Prod: fastmcp run main.py --transport http --port 8000
app = mcp.http_app()
