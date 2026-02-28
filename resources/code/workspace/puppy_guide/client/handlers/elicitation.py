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
    Called whenever the server needs extra input from the user mid-tool.

    message       -- the question the server is asking
    response_type -- a dataclass FastMCP built from the server's schema;
                     we call response_type(value=...) to send the answer back
    params        -- raw MCP parameters (we use these to extract valid options)
    context       -- request metadata (unused here)
    """

    # Read the **single** allowed value from the server's JSON Schema (const field)
    try:
        # Get the server suggestion
        schema = params.requestedSchema or {}
        properties = schema.get("properties", {})
        options = []
        for option in properties.values():
            if "const" in option:
                options.append(str(option["const"]))
    except Exception:
        options = []

    # Print the server's question and the numbered menu
    print()
    print(f"[Server asks]: {message}")
    print()
    print("Please enter the number of your choice:")
    for i, option in enumerate(options, 1):
        print(f"  {i}. {option}")
    print(f"  {len(options) + 1}. Abandon or quit")

    raw = input("> ").strip()

    # Only accept integer input
    try:
        choice = int(raw)
    except ValueError:
        return ElicitResult(action="decline")

    # "Abandon" option or out-of-range → decline
    if choice < 1 or choice == len(options) + 1:
        return ElicitResult(action="decline")

    # Server only wanted a confirmation with no data
    if response_type is None:
        return ElicitResult(action="accept")

    # Wrap the chosen string in the dataclass the server expects
    return response_type(value=options[choice - 1])
