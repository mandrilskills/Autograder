# app.py
import streamlit as st
from grader import run_grader_pipeline
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

st.set_page_config(page_title="Agentic C Autograder (Gemini judge)", layout="centered")
st.title("Agentic C Autograder — Gemini Judge (2.5 Flash)")

st.markdown("Upload or paste a C source file. The Judge LLM (Gemini) will inspect the code and provide a reasoning rubric and final report.")

uploaded = st.file_uploader("Upload .c file", type=["c"])
code_text = ""
if uploaded:
    code_text = uploaded.read().decode("utf-8")
else:
    code_text = st.text_area("Or paste C code here:", height=280)

run_exec = st.sidebar.checkbox("Attempt to run binary (micro-run) — only in safe env", value=False)

if st.button("Grade submission"):
    if not code_text.strip():
        st.error("Provide C source code.")
    else:
        with st.spinner("Running agentic grader..."):
            evaluation = run_grader_pipeline(code_text, tests=None, run_examples=run_exec)
        st.subheader("Final score")
        st.metric("Score", f"{evaluation.get('final_score')}/100")
        st.subheader("Judge LLM reasoning (parsed)")
        st.json(evaluation.get("judge"))
        st.subheader("Compilation info")
        st.json(evaluation.get("compile"))
        st.subheader("Structural heuristic analysis")
        st.json(evaluation.get("structural_analysis"))
        st.subheader("Test results")
        st.json(evaluation.get("test"))
        st.subheader("Final LLM Report")
        st.write(evaluation.get("report"))

        if st.button("Download report PDF"):
            buf = BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=A4)
            styles = getSampleStyleSheet()
            elems = [Paragraph("Agentic C Autograder Report", styles["Title"]), Spacer(1,8), Paragraph(evaluation.get("report","No report"), styles["Normal"])]
            doc.build(elems)
            buf.seek(0)
            st.download_button("Download PDF", data=buf.getvalue(), file_name="autograder_report.pdf", mime="application/pdf")
