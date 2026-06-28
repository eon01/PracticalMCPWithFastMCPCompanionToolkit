# from mcp.shared.context import RequestContext

from fastmcp.client.elicitation import ElicitRequestParams
from fastmcp.client.elicitation import ElicitResult
from fastmcp.client.elicitation import RequestContext


async def elicitation_handler(
    message: str,
    response_type: type | None,
    params: ElicitRequestParams,
    context: RequestContext,
) -> ElicitResult | object:
    """Handle server requests for user input, showing all three actions."""
    # No-data confirmation: the server just wants a yes or no, no value.
    if response_type is None:
        answer = input(f"[Server asks]: {message}\n> Proceed? (y/n): ").strip().lower()
        if answer == "y":
            return ElicitResult(action="accept")
        return ElicitResult(action="decline")

    try:
        user_input = input(f"[Server asks]: {message}\n> Your choice: ").strip()
    except KeyboardInterrupt:
        # User bailed out of the whole operation.
        return ElicitResult(action="cancel")

    if not user_input:
        # User chose not to answer this particular request.
        return ElicitResult(action="decline")

    # User supplied a value: accept with content.
    return response_type(value=user_input)
