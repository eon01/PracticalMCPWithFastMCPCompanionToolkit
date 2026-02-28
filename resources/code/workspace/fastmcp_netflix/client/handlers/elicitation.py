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
    """
    Handle server requests for user input.

    This is the simplest possible implementation - we just ask the user
    in the terminal and return their response. The server's message
    already contains all the context needed (the question and options).

    Args:
        message: The prompt/question from the server (e.g., "Which movie?")
        response_type: A dataclass type to wrap our response
        params: Raw MCP elicitation parameters (we don't use this)
        context: Request context with metadata (we don't use this)

    Returns:
        The user's choice wrapped in response_type, or an ElicitResult
    """
    # Handle the edge case where no response is expected
    # Some elicitation requests just need acknowledgment, not data
    if response_type is None:
        return ElicitResult(action="accept")

    # Show the server's message and get user input
    # The message contains everything - the question and available options
    print()  # Add spacing for readability
    user_input = input(f"[Server asks]: {message}\n> Your choice: ")

    # Handle empty input as "decline"
    # If user just presses Enter, they're declining to answer
    if not user_input.strip():
        return ElicitResult(action="decline")

    # Return the user's choice wrapped in the response type
    # FastMCP expects us to use this dataclass pattern
    return response_type(value=user_input.strip())
