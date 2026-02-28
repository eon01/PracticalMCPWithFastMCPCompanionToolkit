async def progress_handler(
    progress: float,  # current progress value sent by the server
    total: float | None,  # total scope of work, or None if indeterminate
    message: str | None,  # optional human-readable status message from the server
) -> None:
    if total is not None and total > 0:  # determinate progress: total is known
        percentage = (progress / total) * 100  # convert to 0-100 scale
        percent_str = f"{percentage:.0f}%"  # format as whole-number percentage
    else:  # indeterminate: just show the raw value
        percent_str = str(int(progress))  # cast to int to drop the decimal

    msg_part = f"{message}" if message else ""  # omit separator when no message
    print(f"[Progress] {percent_str} - {msg_part}")  # emit the final progress line
