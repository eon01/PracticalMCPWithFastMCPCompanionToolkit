import logging

from fastmcp.client.logging import LogMessage

logger = logging.getLogger("mcp.server")


async def log_handler(message: LogMessage) -> None:

    msg = message.data.get("msg", "") if isinstance(message.data, dict) else str(message.data)
    level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
    }
    level = level_map.get(message.level.lower(), logging.INFO)
    log_line = f"[Server Log] {msg}"
    logger.log(level, log_line)
