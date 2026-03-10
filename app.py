"""
app.py
Professional University-Grade C Autograder UI

Features:
✅ Upload or paste C code
✅ Real gcc compilation
✅ Gemini 2.5 Flash (LangChain) error explanation + hints
✅ Groq LLM — Self-Oracle input generation (inputs only, no guessed outputs)
✅ Multi-agent grading
✅ cppcheck static analysis
✅ Professional rubric display
✅ Live execution logs
✅ Gemini final report
✅ One-click PDF download

Self-Oracle Testing:
  Groq LLM generates only the stdin inputs.
  The compiled binary runs on each input to produce the expected output.
  A second independent run confirms reproducibility.
  This removes all LLM guessing of program output — the program is the oracle.
"""

import streamlit as st
import tempfile
import os
from utils import compile_c_code, run_cppcheck, generate_pdf
from orchestrator import run_orchestration
from llm import gemini_explain_compiler_errors

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

### 🧠 AI Engines Used:
- **Groq LLM** → Test Input Generation (Self-Oracle)
- **Gemini 2.5 Flash** → Final Report & Compile Error Explanation

---

### 🔬 Self-Oracle Testing:
The LLM generates **only stdin inputs**.
The compiled binary produces its own expected outputs.
No LLM guessing of program output — zero hallucination risk.

---

### ⚠️ Academic Policy
- ❌ No auto-correction
- ❌ No full code generation
- ✅ Only explanations & hints
""")

# ── Header ────────────────────────────────────────────────────────────────────
st.title("✅ Professional C Autograder System")
st.caption("University-Ready | Hackathon-Grade | AI-Assisted (Self-Oracle Test Mode)")

# ── Input form ────────────────────────────────────────────────────────────────
with st.form("submission_form"):
    title      = st.text_input("📌 Program Title / Problem Description")
    code_text  = st.text_area("✍️ Paste Your C Code Here", height=320)
    uploaded   = st.file_uploader("OR Upload a .c Source File", type=["c"])
    submitted  = st.form_submit_button("🚀 Evaluate Code")

# ── Main pipeline ─────────────────────────────────────────────────────────────
if submitted:

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
        st.error("No C code provided.")
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
        st.write("🔬 Test Agent running in **Self-Oracle mode** — LLM generates inputs, binary produces expected outputs...")
        final_report = run_orchestration(
            title=title,
            source_c=source_path,
            binary=binary_path,
            static_report=static_report
        )
        status.update(label="✅ Agentic Evaluation Completed", state="complete")

    # ── Score dashboard ───────────────────────────────────────────────────────
    st.header("📊 Evaluation Dashboard")

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
        st.subheader("Functional Test Report — Self-Oracle Mode")
        st.caption(
            "🔬 Inputs were generated by Groq LLM. "
            "Expected outputs were produced by running the binary itself (no LLM guessing)."
        )
        st.write(final_report["tests"]["report"])

        # Colour-coded results table
        cases = final_report["tests"]["cases"]
        if cases:
            st.markdown("#### Test Case Results")
            for i, c in enumerate(cases, 1):
                icon   = "✅" if c["pass"] else "❌"
                header = f"{icon} Test {i} — Input: `{c['input']}`"
                with st.expander(header, expanded=not c["pass"]):
                    col_a, col_b = st.columns(2)
                    col_a.markdown(f"**Expected (Oracle):**\n```\n{c['expected']}\n```")
                    col_b.markdown(f"**Actual (Confirm run):**\n```\n{c['actual']}\n```")
                    if c["pass"]:
                        st.success("PASS — Both runs produced identical, non-empty output.")
                    else:
                        st.error("FAIL — Output mismatch or error between runs.")

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
    pdf_path = generate_pdf(final_report)

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
