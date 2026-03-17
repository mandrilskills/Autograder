"""
llm.py
LLM client wrappers for the C Autograder system.

Functions:
  groq_generate_inputs(prompt)      → generates stdin inputs only (Self-Oracle)
  groq_generate_tests(prompt)       → legacy: kept for backward compatibility
  gemini_generate_report(prompt)    → Gemini final academic report
  gemini_explain_compiler_errors()  → Gemini LangChain error hints
  gemini_extract_code_from_file()   → NEW: OCR for handwritten/scanned C code

Self-Oracle change:
  The old groq_generate_tests() asked the LLM to produce both inputs AND
  expected outputs. This was unreliable because the LLM had to guess the
  program's exact stdout — which it consistently got wrong.

  groq_generate_inputs() is the new entrypoint used by test_agent. It only
  asks the LLM to produce 5 stdin input strings. The binary itself then
  produces the expected outputs (self-oracle). This makes the LLM's job
  trivially easy and removes the main source of test failures.
"""

import io
from PIL import Image
import fitz  # PyMuPDF

from groq import Groq
import google.generativeai as genai
from config import GROQ_API_KEY, GEMINI_API_KEY, GROQ_MODEL, GEMINI_MODEL

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

groq_client      = None
gemini_model     = None
gemini_langchain = None

# ── Groq client ───────────────────────────────────────────────────────────────
if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)

# ── Gemini direct ─────────────────────────────────────────────────────────────
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel(GEMINI_MODEL)

# ── Gemini via LangChain ──────────────────────────────────────────────────────
if GEMINI_API_KEY:
    gemini_langchain = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=0.3
    )

# ─────────────────────────────────────────────────────────────────────────────
# NEW ★  gemini_extract_code_from_file (OCR)
# ─────────────────────────────────────────────────────────────────────────────
def gemini_extract_code_from_file(file_bytes: bytes, file_name: str) -> str:
    """
    Uses Gemini 2.5 Flash to extract handwritten/scanned C code from an image or PDF.
    """
    if not gemini_model:
        return "Gemini API not configured. Cannot perform OCR extraction."

    try:
        images = []
        if file_name.lower().endswith(".pdf"):
            # Convert PDF pages to images using PyMuPDF
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for page in doc:
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("png")
                images.append(Image.open(io.BytesIO(img_bytes)))
        else:
            # Standard image upload (jpg, png)
            images.append(Image.open(io.BytesIO(file_bytes)))

        prompt = (
            "You are an expert OCR system for C programming code. "
            "Extract the C source code from the provided image(s). "
            "If it is handwritten, carefully transcribe it and use your knowledge of C syntax "
            "to fix obvious handwriting ambiguities (like confusing a semicolon for a colon). "
            "Return ONLY the plain C code. Do not include markdown formatting like ```c."
        )

        response = gemini_model.generate_content([prompt] + images)
        text = response.text.strip()
        
        # Clean up any markdown blocks if the LLM ignores instructions
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("\n", 1)[0]
            
        return text.strip()

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"OCR failed: {e}")
        return f"// OCR Extraction Failed: {e}"

# ─────────────────────────────────────────────────────────────────────────────
# groq_generate_inputs
# Used by test_agent (Self-Oracle mode).
# Asks the LLM to produce ONLY stdin input strings — NOT expected outputs.
# ─────────────────────────────────────────────────────────────────────────────
def groq_generate_inputs(prompt: str) -> str | None:
    """
    Sends prompt to Groq and returns the raw response text.
    The prompt instructs the model to return a JSON array of input strings.
    Returns None if the Groq client is unavailable or the call fails.
    """
    if not groq_client:
        return None
    try:
        chat = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=GROQ_MODEL,
            temperature=0.3,      # Low temperature → more deterministic inputs
            max_tokens=512        # Input list is short; cap to avoid padding
        )
        return chat.choices[0].message.content
    except Exception as e:
        # Log and return None so test_agent can fall back gracefully
        import logging
        logging.getLogger(__name__).error(
            f"groq_generate_inputs: API call failed — {e}"
        )
        return None


# ─────────────────────────────────────────────────────────────────────────────
# LEGACY  groq_generate_tests
# Kept for backward compatibility. Not used by the Self-Oracle test_agent.
# ─────────────────────────────────────────────────────────────────────────────
def groq_generate_tests(prompt: str) -> str | None:
    """
    Legacy function — generates full {input, expected} test cases.
    Superseded by groq_generate_inputs() + self-oracle execution.
    Retained so any external callers are not broken.
    """
    if not groq_client:
        return None
    try:
        chat = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=GROQ_MODEL
        )
        return chat.choices[0].message.content
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(
            f"groq_generate_tests: API call failed — {e}"
        )
        return None


# ─────────────────────────────────────────────────────────────────────────────
# gemini_generate_report
# ─────────────────────────────────────────────────────────────────────────────
def gemini_generate_report(prompt: str) -> str | None:
    """
    Uses the Gemini direct client to generate a human-readable academic report.
    Returns None if Gemini is not configured.
    """
    if not gemini_model:
        return None
    try:
        response = gemini_model.generate_content(prompt)
        return response.text
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(
            f"gemini_generate_report: API call failed — {e}"
        )
        return None


# ─────────────────────────────────────────────────────────────────────────────
# gemini_explain_compiler_errors
# ─────────────────────────────────────────────────────────────────────────────
def gemini_explain_compiler_errors(error_log: str) -> str:
    """
    Uses Gemini via LangChain to explain GCC errors and give hints.
    Does NOT rewrite or auto-correct student code.
    Returns a plain-text explanation string.
    """
    if not gemini_langchain:
        return "Gemini API not configured."

    prompt = f"""
You are a C programming instructor reviewing a student's compiler error log.

Rules:
- Do NOT rewrite the student's code.
- Do NOT generate a full solution.
- ONLY explain what each error means in plain language and give a short hint
  on how the student can fix it themselves.

GCC Error Log:
{error_log}
"""
    try:
        response = gemini_langchain.invoke([HumanMessage(content=prompt)])
        return response.content
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(
            f"gemini_explain_compiler_errors: API call failed — {e}"
        )
        return f"Gemini explanation unavailable: {e}"
