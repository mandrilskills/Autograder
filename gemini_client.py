# gemini_client.py
"""
Thin wrapper around google-genai (Gemini) that works on Streamlit Cloud / Python 3.13.

Requires:
  pip install google-genai

Environment:
  - GEMINI_API_KEY (recommended) OR rely on GCP ADC (service account) if configured.
  - GEMINI_MODEL optional (default gemini-2.5-flash will be used if available)
"""

import os
import logging

logger = logging.getLogger(__name__)

try:
    import google.genai as genai
    GENAI_AVAILABLE = True
except Exception:
    GENAI_AVAILABLE = False

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def _configure():
    if not GENAI_AVAILABLE:
        return False
    try:
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
        # If no API key, genai will use ADC/service account if present
        return True
    except Exception as e:
        logger.exception("Failed to configure google-genai: %s", e)
        return False


def generate_text(prompt: str, temperature: float = 0.0, max_output_tokens: int = 1200) -> str:
    """
    Generate text from Gemini. Returns string.
    Fallback: if client unavailable, returns a short placeholder.
    """
    if not _configure():
        logger.warning("google-genai not configured or unavailable; returning fallback text.")
        # Minimal safe fallback
        return "(Gemini not configured) " + (prompt[:400] + "..." if len(prompt) > 400 else prompt)

    try:
        client = genai.Client()
        response = client.responses.generate(
            model=GEMINI_MODEL,
            text=prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens
        )
        # response.output_text is safe in many SDK versions; try best-effort extraction
        text = getattr(response, "output_text", None)
        if text:
            return text
        # fallback: inspect candidates
        if hasattr(response, "candidates") and response.candidates:
            cand = response.candidates[0]
            if hasattr(cand, "content"):
                return cand.content
            return str(cand)
        return str(response)
    except Exception as e:
        logger.exception("Gemini generation failed: %s", e)
        return f"(Gemini error) {e}"
