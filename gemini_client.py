# gemini_client.py
"""
Thin wrapper for Google Gemini via google.generativeai.
Requires:
  - pip install google-generative-ai
  - Set environment variable: GEMINI_API_KEY (or set GOOGLE_API_KEY)
  - Default model: gemini-2.5-flash (override with GEMINI_MODEL env var)

This wrapper uses genai.generate_text where available. Adapt if your SDK differs.
"""

import os
import logging
import json

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except Exception:
    GENAI_AVAILABLE = False

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

def _configure():
    if not GENAI_AVAILABLE:
        return False
    try:
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
        # else rely on service account or default credentials
        return True
    except Exception as e:
        logger.exception("Failed to configure google.generativeai: %s", e)
        return False

def generate_text(prompt: str, temperature: float = 0.0, max_output_tokens: int = 1200) -> str:
    """
    Generate text using Gemini.
    Returns the model text (string). If Gemini isn't configured, returns a fallback string.
    """
    if not _configure() or not GENAI_AVAILABLE:
        logger.warning("google.generativeai not configured or not installed — returning fallback.")
        # fallback: return short heuristic response
        return "(Gemini not configured) " + _fallback_summary(prompt)

    try:
        # Use generate_text if available
        try:
            resp = genai.generate_text(model=GEMINI_MODEL, prompt=prompt, temperature=temperature, max_output_tokens=max_output_tokens)
            # resp may expose .text or .candidates[0].output
            text = getattr(resp, "text", None)
            if text:
                return text
            # older/newer sdk might use candidates
            if hasattr(resp, "candidates") and resp.candidates:
                cand = resp.candidates[0]
                out = getattr(cand, "output", None) or getattr(cand, "content", None)
                if out:
                    return out
            # fallback stringify
            return json.dumps(resp.__dict__, default=str) if hasattr(resp, "__dict__") else str(resp)
        except Exception:
            # fallback to chat-style (some SDKs prefer chat.create)
            resp = genai.chat.create(model=GEMINI_MODEL, messages=[{"role":"user","content": prompt}], temperature=temperature, max_output_tokens=max_output_tokens)
            if hasattr(resp, "candidates") and resp.candidates:
                return resp.candidates[0].content
            return str(resp)
    except Exception as e:
        logger.exception("Gemini generate_text failed: %s", e)
        return f"(Gemini error) {e}"

def _fallback_summary(text: str) -> str:
    # crude fallback: return first non-empty line
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return lines[0] if lines else "No prompt provided"
