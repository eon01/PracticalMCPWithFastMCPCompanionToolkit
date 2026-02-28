from openai import OpenAI
import os
import sys

openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
ngrok_url = os.getenv("MCP_SERVER_URL")

# Get the query from command-line arguments
if len(sys.argv) < 2:
    print("Usage: python simple_client.py '<your query>'")
    sys.exit(1)

query = sys.argv[1]

response = openai.responses.create(
    model="gpt-5-mini",
    tools=[
        {
            "type": "mcp",
            "server_label": "CalculatorServer",
            "server_description": "A simple calculator MCP server",
            "server_url": ngrok_url + "/mcp",
            "require_approval": "never",
        },
    ],
    input=query,
)

print(response.output_text)
