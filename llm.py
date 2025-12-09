from groq import Groq
import google.generativeai as genai
from config import GROQ_API_KEY, GEMINI_API_KEY, GROQ_MODEL, GEMINI_MODEL

# ✅ Correct import for LangChain 1.x
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage   # <-- FIXED

groq_client = None
gemini_model = None
gemini_langchain = None

# ---------------- GROQ ----------------
if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)

# ---------------- GEMINI DIRECT ----------------
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel(GEMINI_MODEL)

# ---------------- GEMINI via LANGCHAIN ----------------
if GEMINI_API_KEY:
    gemini_langchain = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=0.3
    )

def groq_generate_tests(prompt):
    if not groq_client:
        return None
    chat = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=GROQ_MODEL
    )
    return chat.choices[0].message.content

def gemini_generate_report(prompt):
    if not gemini_model:
        return None
    resp = gemini_model.generate_content(prompt)
    return resp.text

def gemini_explain_compiler_errors(error_log):
    if not gemini_langchain:
        return "Gemini API not configured."

    prompt = f"""
Explain the following gcc compilation errors in simple language.
Only give hints. Do NOT rewrite or fix the code.

ERROR LOG:
{error_log}
"""

    response = gemini_langchain.invoke([HumanMessage(content=prompt)])
    return response.content
