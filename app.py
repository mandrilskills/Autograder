# app.py
import streamlit as st
from grader import run_grader_pipeline
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(page_title="Agentic C Autograder (Gemini judge)", layout="centered")
st.title("Agentic C Autograder — Gemini Judge (google-genai)")

st.markdown("Upload/paste a C source file. The Judge LLM (Gemini) will inspect the code and generate the final report.")

uploaded = st.file_uploader("Upload .c file", type=["c"])
code_text = ""
if uploaded:
    code_text = uploaded.read().decode("utf-8")
else:
    code_text = st.text_area("Or paste C code here:", height=300)

run_exec = st.sidebar.checkbox("Attempt to run binary (risky on host)", value=False)

if st.button("Grade submission"):
    if not code_text.strip():
        st.error("Please provide C source code.")
    else:
        with st.spinner("Running agentic pipeline..."):
            evaluation = run_grader_pipeline(code_text, tests=None, run_examples=run_exec)

        st.subheader("Final Score")
        st.metric("Score", f"{evaluation.get('final_score', 'N/A')}/100")

        st.subheader("Judge (Parsed)")
        st.json(evaluation.get("judge"))

        st.subheader("Compilation")
        st.json({k: v for k, v in evaluation.get("compile", {}).items() if k in ("status", "stderr", "stdout")})

        st.subheader("Structural Analysis")
        st.json(evaluation.get("structural_analysis"))

        st.subheader("Test Results")
        st.json(evaluation.get("test"))

        st.subheader("Final LLM Report")
        st.write(evaluation.get("report"))

        if st.button("Download Report PDF"):
            buf = BytesIO()
            doc = SimpleDocTemplate(buf)
            styles = getSampleStyleSheet()
            elems = [
                Paragraph("Agentic C Autograder Report", styles["Title"]),
                Spacer(1, 8),
                Paragraph(evaluation.get("report", "No report"), styles["Normal"])
            ]
            doc.build(elems)
            buf.seek(0)
            st.download_button("Download PDF", data=buf.getvalue(), file_name="autograder_report.pdf", mime="application/pdf")
