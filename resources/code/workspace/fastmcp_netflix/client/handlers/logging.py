import logging

from fastmcp.client.logging import LogMessage

logger = logging.getLogger("mcp.server")


async def log_handler(message: LogMessage) -> None:
    """
    Handle log messages from the MCP server.

    Args:
        message: A LogMessage with level and data
    """
    # Extract the message text
    msg = message.data.get("msg", "")

    # Map MCP log level to Python logging level
    # MCP uses: debug, info, warning, error
    # Python uses: DEBUG, INFO, WARNING, ERROR (as integers)
    level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
    }
    level = level_map.get(message.level.lower(), logging.INFO)

    # Log with a prefix so we know it's from the server
    logger.log(level, f"[SERVER] {msg}")
