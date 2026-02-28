from openai import OpenAI
import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# Define a simple tool function
def say_hi():
    return "Hi there!"


# Create a chat completion request with a tool call
response = client.chat.completions.create(
    model="gpt-5-mini",
    messages=[
        {
            "role": "user", 
            "content": "Say hi"
        }
    ],
    tools=[
        {
            "type": "function",
            "function": {
                "name": "say_hi",
                "description": "A simple function that says hi",
                "parameters": {},
            },
        }
    ],
)

# Get the model's message
message = response.choices[0].message

# Check if the model called any tools
if message.tool_calls:
    for tool_call in message.tool_calls:
        print(f"Calling tool: {tool_call.function.name}")
        if tool_call.function.name == "say_hi":
            result = say_hi()
            print(f"Tool result: {result}")

else:
    print("Model did not call any tools.")
