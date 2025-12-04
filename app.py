# app.py
import streamlit as st
from grader import run_grader_pipeline
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

st.set_page_config(page_title="Agentic C Autograder", layout="centered")

st.title("Agentic C Autograder — Agentic Evaluation (No Testcases)")

st.markdown(
    "Upload or paste a C source file. The agent will run intent analysis, try to compile, "
    "provide diagnostics, evaluate algorithmic steps and give a step-wise score and final report."
)

uploaded = st.file_uploader("Upload .c file", type=["c"])
code_text = ""
if uploaded:
    code_text = uploaded.read().decode("utf-8")
else:
    code_text = st.text_area("Or paste C code here:", height=280)

st.sidebar.header("Options")
run_binary_flag = st.sidebar.checkbox("Attempt to run binary (micro-run) — only for safe environments", value=False)
generate_pdf = st.sidebar.checkbox("Generate downloadable PDF report", value=True)

if st.button("Grade submission"):
    if not code_text.strip():
        st.error("No code provided.")
    else:
        with st.spinner("Running agentic pipeline..."):
            evaluation = run_grader_pipeline(code_text, run_example=run_binary_flag)

        st.subheader("Summary")
        st.metric("Final Score", f"{evaluation['final_score']}/100")
        if evaluation["compile"]["status"] != "success":
            st.error("Compilation failed. See diagnostics below.")
        else:
            st.success("Compiled successfully.")

        st.subheader("Compilation & Diagnostics")
        st.text_area("Compiler stdout/stderr", evaluation["compile"].get("stderr","") or evaluation["compile"].get("stdout",""), height=140)
        if evaluation.get("compiler_diagnostics"):
            st.write("Agent diagnostics:")
            st.json(evaluation["compiler_diagnostics"])

        st.subheader("Agentic Structural Analysis (Step-wise)")
        st.json(evaluation.get("structural_analysis", {}))

        st.subheader("Execution (micro-run, if enabled)")
        if evaluation.get("execution"):
            st.json(evaluation["execution"])
        else:
            st.info("No execution performed or execution skipped.")

        st.subheader("AI Feedback Report")
        st.markdown(evaluation.get("report","(No report generated)"))

        if generate_pdf:
            buf = BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=A4)
            styles = getSampleStyleSheet()
            elems = [
                Paragraph("Agentic C Autograder Report", styles["Title"]),
                Spacer(1, 8),
                Paragraph(evaluation.get("report","No report"), styles["Normal"]),
                Spacer(1, 8),
                Paragraph("Evaluation JSON", styles["Heading3"]),
                Paragraph(str(evaluation.get("raw_evaluation","")), styles["Code"])
            ]
            doc.build(elems)
            buf.seek(0)
            st.download_button("Download PDF report", data=buf.getvalue(), file_name="autograder_report.pdf", mime="application/pdf")
