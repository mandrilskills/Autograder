"""
app.py
Professional University-Grade C Autograder UI

Features:
✅ Upload or paste C code
✅ OCR for Handwritten Scans (Image/PDF) via Gemini Vision
✅ Real gcc compilation
✅ Gemini 2.5 Flash (LangChain) error explanation + hints
✅ AST Parsing — Deterministic boundary test generation
✅ Groq LLM — Fallback test generation
✅ Multi-agent grading
✅ cppcheck static analysis
✅ Professional rubric display
✅ Live execution logs
✅ Gemini final report
✅ One-click PDF download
"""

import streamlit as st
import tempfile
import os
from utils import compile_c_code, run_cppcheck, generate_pdf
from orchestrator import run_orchestration
from llm import gemini_explain_compiler_errors, gemini_extract_code_from_file

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="C Autograder Pro",
    page_icon="✅",
    layout="wide"
)

# ── Sidebar rubric ────────────────────────────────────────────────────────────
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

### 🧠 Core Engines Used:
- **AST (pycparser)** → Deterministic Boundary Test Generation
- **Groq LLM** → Fallback Test Generation
- **Gemini 2.5 Flash** → Final Report, Error Explanation & OCR Vision

---

### 🔬 AST + Self-Oracle Testing:
The system parses the C code's **Abstract Syntax Tree (AST)** to mathematically determine input types and generate strict boundary tests.
The compiled binary produces its own expected outputs (Self-Oracle).
No LLM guessing of program output — **zero hallucination risk**.

---

### ⚠️ Academic Policy
- ❌ No auto-correction
- ❌ No full code generation
- ✅ Only explanations & hints
""")

# ── Header ────────────────────────────────────────────────────────────────────
st.title("✅ Professional C Autograder System")
st.caption("University-Ready | Hackathon-Grade | AST Deterministic Testing")

# ── OCR Pre-processing ────────────────────────────────────────────────────────
if "extracted_code" not in st.session_state:
    st.session_state["extracted_code"] = ""

st.header("📝 1. Code Submission Selection")
upload_type = st.radio(
    "Select Input Method:", 
    ["💻 Manual Paste / .c File Upload", "📄 Scan Handwritten Code (Image/PDF)"], 
    horizontal=True
)

if upload_type == "📄 Scan Handwritten Code (Image/PDF)":
    st.info("Upload a scanned image or PDF of handwritten C code. The AI will transcribe it for your review.")
    ocr_file = st.file_uploader("Upload Scanned Image or PDF", type=["png", "jpg", "jpeg", "pdf"])
    if ocr_file:
        if st.button("🔍 Run AI OCR Extraction", use_container_width=True):
            with st.spinner("Extracting handwritten code using Gemini Vision..."):
                extracted = gemini_extract_code_from_file(ocr_file.read(), ocr_file.name)
                st.session_state["extracted_code"] = extracted
                st.success("✅ Extraction complete! Please review and correct the code below before submitting.")

# ── Input form ────────────────────────────────────────────────────────────────
st.header("🚀 2. Review & Evaluate")
with st.form("submission_form"):
    student_name = st.text_input("🎓 Student Name", placeholder="e.g. Rahul Sharma")
    title        = st.text_input("📌 Program Title / Problem Description")
    
    # Text area uses session_state value so OCR results auto-populate here
    code_text    = st.text_area("✍️ Paste / Edit Your C Code Here", value=st.session_state["extracted_code"], height=320)
    uploaded     = st.file_uploader("OR Upload a .c Source File (Overrides Text Area)", type=["c"])
    submitted    = st.form_submit_button("🚀 Evaluate Code")

# ── Main pipeline ─────────────────────────────────────────────────────────────
if submitted:
    # Clear OCR session state so it resets for the next grading session
    st.session_state["extracted_code"] = ""

    if not title.strip():
        st.error("Program title / description is required.")
        st.stop()

    # ── Load code ─────────────────────────────────────────────────────────────
    if uploaded:
        code_bytes = uploaded.read()
        try:
            code_text = code_bytes.decode("utf-8")
        except UnicodeDecodeError:
            code_text = code_bytes.decode("latin-1")

    if not code_text.strip():
        st.error("No C code provided. Please paste code, extract from an image, or upload a .c file.")
        st.stop()

    # ── Save to temp file ─────────────────────────────────────────────────────
    with st.status("📂 Preparing Submission...", expanded=True) as status:
        tmp = tempfile.NamedTemporaryFile(suffix=".c", delete=False)
        tmp.write(code_text.encode("utf-8"))
        tmp.flush()
        tmp.close()
        source_path = tmp.name
        st.write(f"✅ Source saved: `{source_path}`")
        status.update(label="✅ Submission Prepared", state="complete")

    # ── Compile ───────────────────────────────────────────────────────────────
    with st.status("⚙️ Compiling with gcc...", expanded=True) as status:
        compile_result = compile_c_code(source_path)

        if not compile_result["success"]:
            st.error("❌ Compilation Failed")

            st.subheader("🔴 Raw gcc Error Log")
            st.code(compile_result["errors"])

            st.info("🧠 Sending error log to Gemini 2.5 Flash for explanation...")
            ai_explanation = gemini_explain_compiler_errors(compile_result["errors"])

            st.subheader("✅ Gemini AI Explanation & Correction Hints")
            st.write(ai_explanation)

            st.warning(
                "⚠️ Fix the errors above and resubmit.\n\n"
                "This system will **NOT auto-correct or generate full solutions.**"
            )
            os.unlink(source_path)
            status.update(label="❌ Compilation Failed", state="error")
            st.stop()

        status.update(label="✅ Compilation Successful", state="complete")

    binary_path = compile_result["binary"]
    st.success("✅ Compilation Successful — Binary Generated")

    # ── Static analysis ───────────────────────────────────────────────────────
    with st.status("🔍 Running cppcheck Static Analysis...", expanded=True) as status:
        static_report = run_cppcheck(source_path)

        if static_report.strip():
            st.subheader("⚠️ cppcheck Warnings")
            st.code(static_report)
        else:
            st.success("✅ No cppcheck warnings detected")

        status.update(label="✅ Static Analysis Completed", state="complete")

    # ── Multi-agent orchestration ─────────────────────────────────────────────
    with st.status("🤖 Running Multi-Agent Evaluation...", expanded=True) as status:
        st.write("🔬 Test Agent running in **AST + Self-Oracle mode** — System mathematically generates boundary inputs, binary produces expected outputs...")
        final_report = run_orchestration(
            title=title,
            source_c=source_path,
            binary=binary_path,
            static_report=static_report
        )
        status.update(label="✅ Agentic Evaluation Completed", state="complete")

    # ── Score dashboard ───────────────────────────────────────────────────────
    st.header("📊 Evaluation Dashboard")
    if student_name.strip():
        st.markdown(f"**🎓 Student:** {student_name.strip()}")

    col1, col2, col3 = st.columns(3)
    col1.metric("🏗️ Design Score",  f"{final_report['design']['score']} / 15")
    col2.metric("🧪 Test Score",    f"{final_report['tests']['score']} / 30")
    col3.metric("⚡ Performance",   f"{final_report['performance']['score']} / 15")

    col4, col5, col6 = st.columns(3)
    col4.metric("🚀 Optimization",  f"{final_report['optimization']['score']} / 20")
    col5.metric("🛡️ Static",        f"{final_report['static_score']} / 20")
    col6.metric("✅ TOTAL SCORE",   f"{final_report['total_score']} / 100")

    # ── Tabbed agent reports ──────────────────────────────────────────────────
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
        st.subheader("Functional Test Report — AST + Self-Oracle Mode")
        st.caption(
            "🔬 Inputs were generated deterministically via AST parsing (with LLM fallback). "
            "Expected outputs were produced by running the binary itself — zero LLM hallucination risk."
        )
        st.write(final_report["tests"]["report"])

        cases = final_report["tests"]["cases"]
        if cases:
            st.markdown("#### Test Case Results")

            for i, c in enumerate(cases, 1):
                icon   = "✅" if c["pass"] else "❌"
                
                # Show a clean preview in the expander title
                title_preview = c.get("input_raw", c["input"]).replace("\n", " | ").strip()
                if title_preview.endswith("|"): 
                    title_preview = title_preview[:-1].strip()
                if len(title_preview) > 40:
                    title_preview = title_preview[:40] + "…"
                header = f"{icon} Test {i} — Input: `{title_preview}`"

                with st.expander(header, expanded=not c["pass"]):

                    # ── 1. Clean Input View ─────────────────────
                    st.markdown("**📥 Standard Input (stdin):**")
                    clean_input = c.get("input_raw", c["input"]).strip()
                    st.code(clean_input, language="text")

                    # ── 2. Clean Output View ────────────────────
                    if c["pass"]:
                        st.markdown("**🖥️ Program Output (stdout):**")
                        output_display = c["actual"] if c["actual"].strip() else "(No output printed)"
                        st.code(output_display, language="text")
                        st.success("✅ PASS")
                    else:
                        if "Empty" in c["expected"]:
                            st.markdown("**🖥️ Program Output (stdout):**")
                            st.code("(No output printed to terminal)", language="text")
                            st.error("❌ FAIL — Program produced empty output.")
                            
                        elif "Error" in c["expected"] or "Error" in c["actual"]:
                            st.markdown("**🖥️ Execution Error:**")
                            st.code(c["actual"] if c["actual"] else c["expected"], language="text")
                            st.error("❌ FAIL — Program crashed or timed out.")
                            
                        else:
                            st.warning("⚠️ Unstable Output! The program printed different results on consecutive runs with the same input.")
                            col_a, col_b = st.columns(2)
                            col_a.markdown("**Run 1:**")
                            col_a.code(c["expected"], language="text")
                            col_b.markdown("**Run 2:**")
                            col_b.code(c["actual"], language="text")
                            st.error("❌ FAIL — Non-deterministic behavior.")

    with tab3:
        st.subheader("Performance & Complexity")
        st.write(final_report["performance"]["report"])

    with tab4:
        st.subheader("Optimization Suggestions")
        st.write(final_report["optimization"]["report"])

    with tab5:
        st.subheader("Gemini 2.5 Flash — Final Academic Evaluation")
        st.write(final_report.get("gemini_final_report", "Gemini not configured."))

    # ── PDF download ──────────────────────────────────────────────────────────
    st.info("📄 Generating Final Academic PDF Report...")
    pdf_path = generate_pdf(final_report, student_name=student_name.strip())

    with open(pdf_path, "rb") as f:
        st.download_button(
            "⬇️ Download Final PDF Report",
            f,
            file_name="C_Autograder_Final_Report.pdf"
        )

    # ── Cleanup ───────────────────────────────────────────────────────────────
    try:
        os.unlink(source_path)
        if os.path.exists(binary_path):
            os.unlink(binary_path)
    except Exception:
        pass

    st.success("✅ Evaluation Pipeline Completed Successfully")
