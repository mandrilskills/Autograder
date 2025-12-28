import subprocess, os, tempfile, datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

def compile_c_code(src):
    # Safer binary path generation
    if src.endswith(".c"):
        bin_path = src[:-2]
    else:
        bin_path = src + ".bin"
    
    # -lm links math library which is common in student code
    proc = subprocess.run(["gcc", src, "-o", bin_path, "-lm"], capture_output=True, text=True)
    return {"success": proc.returncode == 0, "errors": proc.stderr, "binary": bin_path}

def run_cppcheck(src):
    try:
        # --force ensures all configs are checked
        proc = subprocess.run(["cppcheck", "--enable=all", "--force", src], stderr=subprocess.PIPE, text=True)
        return proc.stderr
    except FileNotFoundError:
        return "cppcheck not installed on server."
    except Exception as e:
        return f"Error running cppcheck: {str(e)}"

def generate_pdf(report):
    # Handle missing keys gracefully
    gemini_text = report.get("gemini_final_report", "Not available.")
    
    # FIX: ReportLab Paragraphs ignore \n. Replace with <br /> for proper formatting.
    gemini_text = gemini_text.replace("\n", "<br />")

    path = f"{tempfile.gettempdir()}/C_Autograder_Final_Report_{int(datetime.datetime.now().timestamp())}.pdf"

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    elements = []

    # -------- TITLE --------
    elements.append(Paragraph("C AUTOGRADER – FINAL EVALUATION REPORT", styles["Title"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Generated on: {datetime.datetime.now()}", styles["Normal"]))
    elements.append(Spacer(1, 18))

    # -------- FINAL SCORE --------
    elements.append(Paragraph("FINAL SCORE", styles["Heading2"]))
    elements.append(Paragraph(f"{report['total_score']} / 100", styles["Heading1"]))
    elements.append(Spacer(1, 16))

    # -------- SCORE SUMMARY TABLE --------
    data = [
        ["Component", "Score"],
        ["Design Quality", f"{report['design']['score']} / 15"],
        ["Functional Tests", f"{report['tests']['score']} / 30"],
        ["Performance", f"{report['performance']['score']} / 15"],
        ["Optimization", f"{report['optimization']['score']} / 20"],
        ["Static Analysis (cppcheck)", f"{report['static_score']} / 20"]
    ]

    table = Table(data, colWidths=[280, 180])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("GRID", (0,0), (-1,-1), 1, colors.black),
        ("ALIGN", (1,1), (-1,-1), "CENTER"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0,0), (-1,0), 10)
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))

    # -------- DESIGN REPORT --------
    elements.append(Paragraph("DESIGN QUALITY ANALYSIS", styles["Heading2"]))
    elements.append(Paragraph(str(report["design"]["report"]), styles["Normal"]))
    elements.append(Spacer(1, 14))

    # -------- TEST REPORT --------
    elements.append(Paragraph("FUNCTIONAL TEST EXECUTION REPORT", styles["Heading2"]))
    elements.append(Paragraph(str(report["tests"]["report"]), styles["Normal"]))
    elements.append(Spacer(1, 10))

    test_data = [["Input", "Expected", "Actual", "Pass"]]
    for c in report["tests"]["cases"]:
        test_data.append([
            str(c["input"])[:50], 
            str(c["expected"])[:50], 
            str(c["actual"])[:50], 
            str(c["pass"])
        ])

    test_table = Table(test_data, colWidths=[120, 120, 120, 80])
    test_table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 1, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey)
    ]))

    elements.append(test_table)
    elements.append(Spacer(1, 16))

    # -------- PERFORMANCE --------
    elements.append(Paragraph("PERFORMANCE & COMPLEXITY ANALYSIS", styles["Heading2"]))
    elements.append(Paragraph(str(report["performance"]["report"]), styles["Normal"]))
    elements.append(Spacer(1, 14))

    # -------- OPTIMIZATION --------
    elements.append(Paragraph("OPTIMIZATION SUGGESTIONS", styles["Heading2"]))
    elements.append(Paragraph(str(report["optimization"]["report"]), styles["Normal"]))
    elements.append(Spacer(1, 14))

    # -------- STATIC ANALYSIS --------
    elements.append(Paragraph("STATIC ANALYSIS (CPPCHECK)", styles["Heading2"]))
    static_text = report["static_report"].replace("\n", "<br/>") if report["static_report"] else "No warnings detected."
    # Truncate text if excessively long to prevent PDF crash
    if len(static_text) > 5000: static_text = static_text[:5000] + "... (truncated)"
    elements.append(Paragraph(static_text, styles["Normal"]))
    elements.append(Spacer(1, 16))

    # -------- GEMINI FINAL REPORT --------
    elements.append(Paragraph("GEMINI 2.5 FLASH – FINAL ACADEMIC EVALUATION", styles["Heading2"]))
    elements.append(Paragraph(gemini_text, styles["Normal"]))
    elements.append(Spacer(1, 20))

    # -------- FOOTER --------
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("Generated by Professional C Autograder System", styles["Italic"]))

    doc.build(elements)
    return path
