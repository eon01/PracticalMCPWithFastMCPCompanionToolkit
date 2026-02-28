import os
from dotenv import load_dotenv
from fastmcp.client.sampling.handlers.openai import OpenAISamplingHandler

load_dotenv()

# Define the model to use for sampling, defaulting to "gpt-5-mini" if not specified in the .env file
MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
# Create an instance of the OpenAISamplingHandler with the specified model
sampling_handler = OpenAISamplingHandler(default_model=MODEL)
