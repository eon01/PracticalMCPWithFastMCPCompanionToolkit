async def progress_handler(
    progress: float,
    total: float | None,
    message: str | None,
) -> None:
    """
    Handle progress updates from the MCP server.

    Args:
        progress: Current progress value
        total: Total value (for percentage), or None if unknown
        message: Description of current operation
    """
    # Calculate percentage if we have a total
    if total is not None and total > 0:
        percentage = (progress / total) * 100
        percent_str = f"{percentage:.0f}%"
    else:
        # If no total, just show the raw progress number
        percent_str = str(int(progress))

    # Format and print the progress message
    msg_part = f" - {message}" if message else ""
    print(f"[Progress] {percent_str}{msg_part}")
