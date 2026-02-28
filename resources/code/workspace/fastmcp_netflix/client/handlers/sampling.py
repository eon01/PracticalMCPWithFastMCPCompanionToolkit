from dotenv import load_dotenv

from fastmcp.client.sampling.handlers.openai import OpenAISamplingHandler

# Needed to load environment variables for OpenAI API
load_dotenv()

sampling_handler = OpenAISamplingHandler(
    default_model="gpt-5-mini",
)
