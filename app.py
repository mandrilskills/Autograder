"""
app.py
Professional University-Grade C Autograder UI (FINAL PATCH)

Features:
✅ Upload or paste C code
✅ Real gcc compilation
✅ Case-1 Gemini 2.5 Flash (LangChain) error explanation + hints
✅ Groq LLM test generation
✅ Multi-agent grading
✅ cppcheck static analysis
✅ Professional rubric display
✅ Live execution logs
✅ Gemini final report
✅ One-click PDF download

COPY-PASTE READY FOR GITHUB ✅
"""

import streamlit as st
import tempfile
import os
from utils import compile_c_code, run_cppcheck, generate_pdf
from orchestrator import run_orchestration
from llm import gemini_explain_compiler_errors

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="C Autograder Pro",
    page_icon="✅",
    layout="wide"
)

# ---------------- SESSION STATE INIT ----------------
if "code_content" not in st.session_state:
    st.session_state["code_content"] = ""

# ---------------- SIDEBAR (RUBRIC) ----------------
with st.sidebar:
    st.title("📊 Evaluation Rubric")
    st.markdown("""
- **Design Quality** — 15%
- **Functional Tests** — 30%
- **Performance & Complexity** — 15%
- **Optimization Quality** — 20%
- **Static Analysis (cppcheck)** — 20%

✅ **Total = 100 Marks**

---

### 🧠 AI Engines Used:
- **Groq LLM** → Test Case Generation  
- **Gemini 2.5 Flash** → Final Report & Compile Error Explanation

---

### ⚠️ Academic Policy
- ❌ No auto-correction  
- ❌ No full code generation  
- ✅ Only explanations & hints
""")

# ---------------- HEADER ----------------
st.title("✅ Professional C Autograder System")
st.caption("University-Ready | Hackathon-Grade | AI-Assisted (No Academic Dishonesty)")

# ---------------- INPUT SECTION ----------------
title = st.text_input("📌 Program Title / Problem Description")

# LOGIC: Show File Uploader ONLY if the text area is empty
# We handle the file read inline (no callback) to prevent Streamlit state errors
if not st.session_state["code_content"].strip():
    uploaded_file = st.file_uploader(
        "OR Upload a .c Source File", 
        type=["c"], 
        key="uploaded_c_file"
    )
    
    # If a file is uploaded, read it, update state, and rerun immediately
    if uploaded_file is not None:
        try:
            content = uploaded_file.read().decode("utf-8")
        except:
            content = uploaded_file.read().decode("latin-1")
            
        st.session_state["code_content"] = content
        st.rerun()

# Text Area is bound to session state. 
# It will automatically populate if a file was uploaded above.
code_text = st.text_area(
    "✍️ Paste Your C Code Here", 
    height=320,
    key="code_content"
)

submitted = st.button("🚀 Evaluate Code")

# ---------------- MAIN PIPELINE ----------------
if submitted:
    if not title.strip():
        st.error("Program title / description is required.")
        st.stop()

    if not code_text.strip():
        st.error("No C code provided.")
        st.stop()

    with st.status("📂 Preparing Submission...", expanded=True) as status:
        tmp = tempfile.NamedTemporaryFile(suffix=".c", delete=False)
        tmp.write(code_text.encode("utf-8"))
        tmp.flush()
        tmp.close()
        source_path = tmp.name
        st.write(f"✅ Source saved: `{source_path}`")
        status.update(label="✅ Submission Prepared", state="complete")

    # ---------- COMPILATION ----------
    with st.status("⚙️ Compiling with gcc...", expanded=True) as status:
        compile_result = compile_c_code(source_path)

        # ✅ ✅ ✅ -------- CASE 1: COMPILATION FAILS (GEMINI VIA LANGCHAIN) --------
        if not compile_result["success"]:
            st.error("❌ Compilation Failed")

            st.subheader("🔴 Raw gcc Error Log")
            st.code(compile_result["errors"])

            st.info("🧠 Sending error log to Gemini 2.5 Flash (LangChain) for explanation...")
            ai_explanation = gemini_explain_compiler_errors(compile_result["errors"])

            st.subheader("✅ Gemini AI Explanation & Correction Hints")
            st.write(ai_explanation)

            st.warning("⚠️ You must FIX the errors and RESUBMIT.\n\nThis system will **NOT auto-correct or generate full solutions.**")

            os.unlink(source_path)
            status.update(label="❌ Compilation Failed", state="error")
            st.stop()

        status.update(label="✅ Compilation Successful", state="complete")

    binary_path = compile_result["binary"]
    st.success("✅ Compilation Successful — Binary Generated")

    # ---------- STATIC ANALYSIS ----------
    with st.status("🔍 Running cppcheck Static Analysis...", expanded=True) as status:
        static_report = run_cppcheck(source_path)

        if static_report.strip():
            st.subheader("⚠️ cppcheck Warnings")
            st.code(static_report)
        else:
            st.success("✅ No cppcheck warnings detected")

        status.update(label="✅ Static Analysis Completed", state="complete")

    # ---------- MULTI-AGENT ORCHESTRATION ----------
    with st.status("🤖 Running Multi-Agent Evaluation...", expanded=True) as status:
        final_report = run_orchestration(
            title=title,
            source_c=source_path,
            binary=binary_path,
            static_report=static_report
        )
        status.update(label="✅ Agentic Evaluation Completed", state="complete")

    # ---------- DASHBOARD DISPLAY ----------
    st.header("📊 Evaluation Dashboard")

    col1, col2, col3 = st.columns(3)
    col1.metric("🏗️ Design Score", f"{final_report['design']['score']} / 15")
    col2.metric("🧪 Test Score", f"{final_report['tests']['score']} / 30")
    col3.metric("⚡ Performance", f"{final_report['performance']['score']} / 15")

    col4, col5, col6 = st.columns(3)
    col4.metric("🚀 Optimization", f"{final_report['optimization']['score']} / 20")
    col5.metric("🛡️ Static", f"{final_report['static_score']} / 20")
    col6.metric("✅ TOTAL SCORE", f"{final_report['total_score']} / 100")

    # ---------- TABBED AGENT REPORTS ----------
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏗️ Design",
        "🧪 Tests",
        "⚡ Performance",
        "🚀 Optimization",
        "🧠 Gemini Final Report"
    ])

    with tab1:
        st.subheader("Design Quality Report")
        st.write(final_report["design"]["report"])

    with tab2:
        st.subheader("Functional Test Report (Groq Generated)")
        st.write(final_report["tests"]["report"])
        st.table(final_report["tests"]["cases"])

    with tab3:
        st.subheader("Performance & Complexity")
        st.write(final_report["performance"]["report"])

    with tab4:
        st.subheader("Optimization Suggestions")
        st.write(final_report["optimization"]["report"])

    with tab5:
        st.subheader("Gemini 2.5 Flash — Final Academic Evaluation")
        st.write(final_report.get("gemini_final_report", "Gemini not configured."))

    # ---------- PDF GENERATION ----------
    st.info("📄 Generating Final Academic PDF Report...")
    pdf_path = generate_pdf(final_report)

    with open(pdf_path, "rb") as f:
        st.download_button(
            "⬇️ Download Final PDF Report",
            f,
            file_name="C_Autograder_Final_Report.pdf"
        )

    # ---------- CLEANUP ----------
    try:
        os.unlink(source_path)
        if os.path.exists(binary_path):
            os.unlink(binary_path)
    except Exception:
        pass

    st.success("✅ Evaluation Pipeline Completed Successfully")
