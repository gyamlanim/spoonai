import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def validate_keys():
    for _name, _value in [
        ("OPENAI_API_KEY", OPENAI_API_KEY),
        ("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY),
        ("GEMINI_API_KEY", GEMINI_API_KEY),
    ]:
        if not _value:
            raise ValueError(f"Missing required environment variable: {_name}")
