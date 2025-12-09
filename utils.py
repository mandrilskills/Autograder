import subprocess, os, tempfile, datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

def compile_c_code(src):
    bin_path = src[:-2]
    proc = subprocess.run(["gcc", src, "-o", bin_path], capture_output=True, text=True)
    return {"success": proc.returncode == 0, "errors": proc.stderr, "binary": bin_path}

def run_cppcheck(src):
    try:
        proc = subprocess.run(["cppcheck", "--enable=all", src], stderr=subprocess.PIPE, text=True)
        return proc.stderr
    except:
        return "cppcheck not installed."

def generate_pdf(report):
    path = f"{tempfile.gettempdir()}/c_report_{int(datetime.datetime.now().timestamp())}.pdf"
    doc = SimpleDocTemplate(path, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Final Gemini AI Evaluation Report", styles["Title"]))
    elements.append(Spacer(1,12))
    elements.append(Paragraph(report["gemini_final_report"], styles["Normal"]))
    elements.append(Spacer(1,12))
    elements.append(Paragraph(f"Final Score: {report['total_score']} / 100", styles["Heading2"]))

    doc.build(elements)
    return path

