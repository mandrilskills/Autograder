from groq import Groq
import google.generativeai as genai
from config import GROQ_API_KEY, GEMINI_API_KEY, GROQ_MODEL, GEMINI_MODEL

# ✅ LangChain wrappers
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage

groq_client = None
gemini_model = None
gemini_langchain = None

# ---------- GROQ ----------
if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)

# ---------- GEMINI DIRECT ----------
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel(GEMINI_MODEL)

# ---------- GEMINI VIA LANGCHAIN (FOR COMPILER ERRORS) ----------
if GEMINI_API_KEY:
    gemini_langchain = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=0.3
    )

# ---------- GROQ TEST CASE GENERATION ----------
def groq_generate_tests(prompt):
    if not groq_client:
        return None
    chat = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=GROQ_MODEL
    )
    return chat.choices[0].message.content

# ---------- GEMINI FINAL REPORT ----------
def gemini_generate_report(prompt):
    if not gemini_model:
        return None
    response = gemini_model.generate_content(prompt)
    return response.text

# ✅ ---------- GEMINI COMPILATION ERROR EXPLAINER (LANGCHAIN) ----------
def gemini_explain_compiler_errors(error_log):
    if not gemini_langchain:
        return "Gemini API not configured. Unable to generate AI explanation."

    prompt = f"""
You are an expert C programming tutor.

Rules:
- DO NOT generate a full corrected program.
- DO NOT rewrite the student's code.
- ONLY:
  1. Explain the compilation errors in simple language.
  2. Provide correction hints.
  3. Mention what concept the student should revise.

gcc Error Log:
{error_log}
"""

    response = gemini_langchain.invoke([
        HumanMessage(content=prompt)
    ])

    return response.content
