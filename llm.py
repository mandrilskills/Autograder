from groq import Groq
import google.generativeai as genai
from config import GROQ_API_KEY, GEMINI_API_KEY, GROQ_MODEL, GEMINI_MODEL

groq_client = None
gemini_model = None

if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel(GEMINI_MODEL)

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
    response = gemini_model.generate_content(prompt)
    return response.text

