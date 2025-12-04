# gemini_client.py
import os
import json
import logging

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except Exception:
    GENAI_AVAILABLE = False

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def configure():
    if not GENAI_AVAILABLE:
        return False
    try:
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
        return True
    except Exception as e:
        logger.error("Gemini configuration failed: %s", e)
        return False


def generate_text(prompt: str, temperature=0.0, max_output_tokens=1500) -> str:
    if not configure():
        return "(Gemini not configured) " + prompt[:200]

    try:
        response = genai.generate_text(
            model=GEMINI_MODEL,
            prompt=prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens
        )
        if hasattr(response, "text"):  
            return response.text
        if hasattr(response, "candidates") and response.candidates:
            return response.candidates[0].output
        return str(response)
    except Exception as e:
        logger.error("Gemini error: %s", e)
        return f"(Gemini error) {e}"
