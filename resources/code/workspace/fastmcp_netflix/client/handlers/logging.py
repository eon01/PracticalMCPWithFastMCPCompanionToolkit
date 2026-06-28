import logging

from fastmcp.client.logging import LogMessage

logger = logging.getLogger("mcp.server")

# Collapse MCP's eight RFC 5424 levels onto Python's six.
LEVEL_MAP = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "notice": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
    "alert": logging.CRITICAL,
    "emergency": logging.CRITICAL,
}


async def log_handler(message: LogMessage) -> None:
    """Handle log messages from the MCP server."""
    # data is the full structured payload; "msg" is a convention, not guaranteed.
    msg = (
        message.data.get("msg", "") if isinstance(message.data, dict) else message.data
    )
    level = LEVEL_MAP.get(message.level.lower(), logging.INFO)
    logger.log(level, f"[SERVER] {msg}")
