# app.py

import streamlit as st
from grader import run_grader_pipeline
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO

st.title("Agentic C Autograder — Gemini 2.5 Flash")

uploaded = st.file_uploader("Upload C file", type=["c"])
code_text = ""

if uploaded:
    code_text = uploaded.read().decode()
else:
    code_text = st.text_area("Paste C code here:", height=300)

run_exec = st.checkbox("Attempt program execution (risky on host)")

if st.button("Evaluate"):
    if not code_text.strip():
        st.error("No code provided.")
    else:
        with st.spinner("Running agentic evaluation..."):
            evaluation = run_grader_pipeline(code_text, tests=None, run_examples=run_exec)

        st.subheader("Final Score")
        st.metric("Score", evaluation["final_score"])

        st.subheader("Judge LLM Output")
        st.json(evaluation["judge"])

        st.subheader("Compilation")
        st.json(evaluation["compile"])

        st.subheader("Structural Analysis")
        st.json(evaluation["structural_analysis"])

        st.subheader("Test Results")
        st.json(evaluation["test"])

        st.subheader("Final Report")
        st.write(evaluation["report"])

        # PDF download
        if st.button("Download Report PDF"):
            buf = BytesIO()
            doc = SimpleDocTemplate(buf)
            styles = getSampleStyleSheet()
            doc.build([
                Paragraph("Autograder Report", styles["Title"]),
                Spacer(1, 12),
                Paragraph(evaluation["report"], styles["Normal"])
            ])
            buf.seek(0)
            st.download_button("Download PDF", buf, file_name="report.pdf")
