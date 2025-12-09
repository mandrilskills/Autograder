import os

WEIGHTS = {
    "design": 15.0,
    "tests": 30.0,
    "performance": 15.0,
    "optimization": 20.0,
    "static": 20.0
}

TEST_TIMEOUT_SECONDS = 2

# ✅ LLM API KEYS (SET AS ENV VARIABLES)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

GROQ_MODEL = "meta-llama/llama-4-maverick-17b-128e-instruct"
GEMINI_MODEL = "gemini-2.5-flash"

