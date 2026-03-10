"""
utils.py
Utility functions for the C Autograder system.

Functions:
  compile_c_code(src)   → Compiles C source with gcc
  run_cppcheck(src)     → Runs cppcheck static analysis
  generate_pdf(report)  → Produces a fully formatted academic PDF report
"""

import subprocess
import os
import tempfile
import datetime
import re


# ─────────────────────────────────────────────────────────────────────────────
# COMPILE
# ─────────────────────────────────────────────────────────────────────────────
def compile_c_code(src: str) -> dict:
    bin_path = src[:-2]
    proc = subprocess.run(
        ["gcc", src, "-o", bin_path],
        capture_output=True, text=True
    )
    return {
        "success": proc.returncode == 0,
        "errors":  proc.stderr,
        "binary":  bin_path
    }


# ─────────────────────────────────────────────────────────────────────────────
# STATIC ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────
def run_cppcheck(src: str) -> str:
    try:
        proc = subprocess.run(
            ["cppcheck", "--enable=all", src],
            stderr=subprocess.PIPE, text=True
        )
        return proc.stderr
    except Exception:
        return "cppcheck not installed."


# ─────────────────────────────────────────────────────────────────────────────
# PDF GENERATION  — fully redesigned
# ─────────────────────────────────────────────────────────────────────────────
def generate_pdf(report: dict, student_name: str = "") -> str:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm, cm
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, KeepTogether, PageBreak
    )

    path = (
        f"{tempfile.gettempdir()}/"
        f"C_Autograder_Report_{int(datetime.datetime.now().timestamp())}.pdf"
    )

    PAGE_W, PAGE_H = A4
    MARGIN = 2 * cm

    # ── Colour palette ────────────────────────────────────────────────────────
    NAVY        = colors.HexColor("#1B2A4A")   # headings, title bar
    TEAL        = colors.HexColor("#0D7377")   # section accent bars
    LIGHT_TEAL  = colors.HexColor("#E8F4F4")   # section header backgrounds
    PASS_GREEN  = colors.HexColor("#D4EDDA")   # pass row fill
    FAIL_RED    = colors.HexColor("#F8D7DA")   # fail row fill
    HEADER_GREY = colors.HexColor("#2C3E50")   # table column headers
    ROW_ALT     = colors.HexColor("#F7F9FA")   # alternating table rows
    SCORE_BG    = colors.HexColor("#EAF4FB")   # score summary rows
    TEXT_DARK   = colors.HexColor("#212529")
    TEXT_MID    = colors.HexColor("#495057")
    TEXT_LIGHT  = colors.HexColor("#6C757D")
    WHITE       = colors.white

    # ── Custom paragraph styles ───────────────────────────────────────────────
    styles = getSampleStyleSheet()

    def PS(name, **kwargs):
        """Shorthand to create a ParagraphStyle."""
        return ParagraphStyle(name, **kwargs)

    sTitle = PS(
        "sTitle",
        fontName="Helvetica-Bold",
        fontSize=22,
        textColor=WHITE,
        alignment=TA_CENTER,
        spaceAfter=2,
        leading=28,
    )
    sSubtitle = PS(
        "sSubtitle",
        fontName="Helvetica",
        fontSize=9,
        textColor=colors.HexColor("#BDC8D8"),
        alignment=TA_CENTER,
        spaceAfter=0,
    )
    sBigScore = PS(
        "sBigScore",
        fontName="Helvetica-Bold",
        fontSize=40,
        textColor=NAVY,
        alignment=TA_CENTER,
        spaceAfter=2,
        leading=48,
    )
    sScoreLabel = PS(
        "sScoreLabel",
        fontName="Helvetica",
        fontSize=10,
        textColor=TEXT_MID,
        alignment=TA_CENTER,
        spaceAfter=0,
    )
    sSectionHead = PS(
        "sSectionHead",
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=WHITE,
        alignment=TA_LEFT,
        leading=16,
        leftIndent=6,
    )
    sBody = PS(
        "sBody",
        fontName="Helvetica",
        fontSize=9,
        textColor=TEXT_DARK,
        leading=14,
        spaceAfter=4,
    )
    sBodyBold = PS(
        "sBodyBold",
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=TEXT_DARK,
        leading=14,
        spaceAfter=4,
    )
    sSmall = PS(
        "sSmall",
        fontName="Helvetica",
        fontSize=8,
        textColor=TEXT_LIGHT,
        leading=11,
        spaceAfter=2,
    )
    sTableHeader = PS(
        "sTableHeader",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        textColor=WHITE,
        alignment=TA_CENTER,
        leading=12,
    )
    sTableCell = PS(
        "sTableCell",
        fontName="Helvetica",
        fontSize=8,
        textColor=TEXT_DARK,
        leading=11,
        wordWrap="CJK",
    )
    sTableCellC = PS(
        "sTableCellC",
        fontName="Helvetica",
        fontSize=8,
        textColor=TEXT_DARK,
        alignment=TA_CENTER,
        leading=11,
    )
    sPassCell = PS(
        "sPassCell",
        fontName="Helvetica-Bold",
        fontSize=8,
        textColor=colors.HexColor("#155724"),
        alignment=TA_CENTER,
        leading=11,
    )
    sFailCell = PS(
        "sFailCell",
        fontName="Helvetica-Bold",
        fontSize=8,
        textColor=colors.HexColor("#721C24"),
        alignment=TA_CENTER,
        leading=11,
    )
    sGemini = PS(
        "sGemini",
        fontName="Helvetica",
        fontSize=8.5,
        textColor=TEXT_DARK,
        leading=13,
        spaceAfter=4,
    )
    sGeminiBold = PS(
        "sGeminiBold",
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=NAVY,
        leading=14,
        spaceAfter=3,
        spaceBefore=6,
    )
    sFooter = PS(
        "sFooter",
        fontName="Helvetica-Oblique",
        fontSize=7.5,
        textColor=TEXT_LIGHT,
        alignment=TA_CENTER,
    )

    # ── Helper: coloured section header bar ──────────────────────────────────
    def section_header(text: str) -> KeepTogether:
        bar = Table(
            [[Paragraph(text, sSectionHead)]],
            colWidths=[PAGE_W - 2 * MARGIN],
        )
        bar.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, -1), TEAL),
            ("TOPPADDING",   (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
            ("LEFTPADDING",  (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("ROUNDEDCORNERS", [3]),
        ]))
        return KeepTogether([Spacer(1, 10), bar, Spacer(1, 6)])

    # ── Helper: score badge row for summary table ─────────────────────────────
    def score_fraction_color(score: float, max_score: float) -> colors.Color:
        ratio = score / max_score if max_score else 0
        if ratio >= 0.85:
            return colors.HexColor("#D4EDDA")   # green
        elif ratio >= 0.60:
            return colors.HexColor("#FFF3CD")   # amber
        else:
            return colors.HexColor("#F8D7DA")   # red

    # ── Helper: clean Gemini markdown into ReportLab paragraphs ──────────────
    def render_gemini_report(raw_text: str) -> list:
        """
        Converts the Gemini markdown report into a list of Paragraph flowables.
        Handles **bold**, bullet points, numbered lists, and plain lines.
        """
        if not raw_text or raw_text.strip() in ("Not available.", "Gemini API not configured."):
            return [Paragraph("Gemini report not available.", sBody)]

        elements_out = []
        lines = raw_text.split("\n")

        for line in lines:
            stripped = line.strip()
            if not stripped:
                elements_out.append(Spacer(1, 4))
                continue

            # Section headings: lines starting with ** and ending with **
            if stripped.startswith("**") and stripped.endswith("**") and len(stripped) > 4:
                clean = stripped.strip("*").strip()
                elements_out.append(Paragraph(clean, sGeminiBold))
                continue

            # Bullet points
            if stripped.startswith(("* ", "- ", "• ")):
                clean = stripped[2:].strip()
                clean = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', clean)
                elements_out.append(
                    Paragraph(f"&nbsp;&nbsp;• {clean}", sGemini)
                )
                continue

            # Numbered list items
            if re.match(r'^\d+[\.\)]\s', stripped):
                clean = re.sub(r'^\d+[\.\)]\s', '', stripped)
                clean = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', clean)
                elements_out.append(Paragraph(clean, sGeminiBold))
                continue

            # Plain line — replace inline **bold**
            clean = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', stripped)
            clean = clean.replace("---", "").strip()
            if clean:
                elements_out.append(Paragraph(clean, sGemini))

        return elements_out

    # ── Helper: format input_raw for the test table ───────────────────────────
    def format_input(case: dict) -> str:
        """
        Turns raw stdin bytes into a clean multi-line readable string.
        Uses input_raw if present, falls back to input.
        """
        raw = case.get("input_raw", case.get("input", ""))
        lines = [l for l in raw.split("\n") if l.strip() != ""]
        if not lines:
            return raw.strip() or "(empty)"
        if len(lines) == 1:
            return lines[0]
        return "\n".join(f"[{i+1}] {l}" for i, l in enumerate(lines))

    # ─────────────────────────────────────────────────────────────────────────
    # BUILD DOCUMENT
    # ─────────────────────────────────────────────────────────────────────────
    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        rightMargin=MARGIN,
        leftMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN + 5 * mm,
        title="C Autograder Final Evaluation Report",
    )

    E = []   # elements list

    # ═══════════════════════════════════════════════════════════════════════════
    # COVER BANNER
    # ═══════════════════════════════════════════════════════════════════════════
    banner_content = [
        [Paragraph("C AUTOGRADER", sTitle)],
        [Paragraph("FINAL EVALUATION REPORT", sTitle)],
        [Spacer(1, 4)],
        [Paragraph(
            f"Generated: {datetime.datetime.now().strftime('%d %B %Y  |  %H:%M')}",
            sSubtitle
        )],
    ]
    if student_name:
        banner_content.insert(2, [Paragraph(
            f"Student: {student_name}",
            PS("sBannerStudent", fontName="Helvetica-Bold", fontSize=12,
               textColor=colors.HexColor("#A8C8E8"), alignment=TA_CENTER, leading=18)
        )])
    banner = Table(
        banner_content,
        colWidths=[PAGE_W - 2 * MARGIN],
    )
    banner.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 16),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
        ("ROUNDEDCORNERS", [4]),
    ]))
    E.append(banner)
    E.append(Spacer(1, 16))

    # ═══════════════════════════════════════════════════════════════════════════
    # SCORE HERO BLOCK
    # ═══════════════════════════════════════════════════════════════════════════
    total = report.get("total_score", 0)
    ratio = total / 100

    if ratio >= 0.85:
        grade, grade_color = "A", colors.HexColor("#155724")
    elif ratio >= 0.70:
        grade, grade_color = "B", colors.HexColor("#856404")
    elif ratio >= 0.55:
        grade, grade_color = "C", colors.HexColor("#856404")
    else:
        grade, grade_color = "F", colors.HexColor("#721C24")

    sGrade = PS("sGrade", fontName="Helvetica-Bold", fontSize=36,
                textColor=grade_color, alignment=TA_CENTER, leading=44)

    score_block = Table(
        [[
            Paragraph(f"{total}", sBigScore),
            Paragraph(f"/ 100", sScoreLabel),
            Paragraph(grade, sGrade),
        ]],
        colWidths=[
            (PAGE_W - 2 * MARGIN) * 0.4,
            (PAGE_W - 2 * MARGIN) * 0.3,
            (PAGE_W - 2 * MARGIN) * 0.3,
        ],
    )
    score_block.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND",    (0, 0), (-1, -1), SCORE_BG),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LINEBELOW",     (0, 0), (-1, -1), 2, TEAL),
        ("ROUNDEDCORNERS", [4]),
    ]))
    E.append(score_block)
    if student_name:
        sStudentLabel = PS("sStudentLabel", fontName="Helvetica-Bold", fontSize=11,
                           textColor=NAVY, alignment=TA_CENTER, leading=16)
        student_block = Table(
            [[Paragraph(f"Student:  {student_name}", sStudentLabel)]],
            colWidths=[PAGE_W - 2 * MARGIN],
        )
        student_block.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), LIGHT_TEAL),
            ("TOPPADDING",    (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING",   (0, 0), (-1, -1), 12),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
            ("LINEBELOW",     (0, 0), (-1, -1), 1.5, TEAL),
        ]))
        E.append(student_block)
    E.append(Spacer(1, 14))

    # ═══════════════════════════════════════════════════════════════════════════
    # SCORE SUMMARY TABLE
    # ═══════════════════════════════════════════════════════════════════════════
    E.append(section_header("📊  SCORE SUMMARY"))

    components = [
        ("Design Quality",          report["design"]["score"],         15),
        ("Functional Tests",        report["tests"]["score"],          30),
        ("Performance & Complexity",report["performance"]["score"],    15),
        ("Optimization Quality",    report["optimization"]["score"],   20),
        ("Static Analysis",         report.get("static_score", 0),     20),
    ]

    summary_data = [[
        Paragraph("Component", sTableHeader),
        Paragraph("Score", sTableHeader),
        Paragraph("Max", sTableHeader),
        Paragraph("Status", sTableHeader),
    ]]

    summary_style = [
        ("BACKGROUND",    (0, 0), (-1, 0),  HEADER_GREY),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#CED4DA")),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, ROW_ALT]),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]

    for row_idx, (label, score, max_s) in enumerate(components, start=1):
        row_color = score_fraction_color(score, max_s)
        pct = int((score / max_s) * 100) if max_s else 0
        status = "✓ Excellent" if pct >= 85 else ("~ Good" if pct >= 60 else "✗ Needs Work")
        sStatus = PS(f"st{row_idx}", fontName="Helvetica-Bold", fontSize=8,
                     textColor=(colors.HexColor("#155724") if pct >= 85
                                else colors.HexColor("#856404") if pct >= 60
                                else colors.HexColor("#721C24")),
                     alignment=TA_CENTER, leading=11)
        summary_data.append([
            Paragraph(label, sTableCell),
            Paragraph(f"<b>{score}</b>", sTableCellC),
            Paragraph(str(max_s), sTableCellC),
            Paragraph(status, sStatus),
        ])
        summary_style.append(("BACKGROUND", (0, row_idx), (-1, row_idx), row_color))

    # Total row
    summary_data.append([
        Paragraph("<b>TOTAL</b>", sBodyBold),
        Paragraph(f"<b>{total}</b>", sBodyBold),
        Paragraph("<b>100</b>", sBodyBold),
        Paragraph("", sTableCellC),
    ])
    summary_style.append(("BACKGROUND", (0, len(components)+1), (-1, len(components)+1), LIGHT_TEAL))
    summary_style.append(("LINEABOVE",  (0, len(components)+1), (-1, len(components)+1), 1.5, TEAL))

    summary_table = Table(
        summary_data,
        colWidths=[
            (PAGE_W - 2 * MARGIN) * 0.45,
            (PAGE_W - 2 * MARGIN) * 0.15,
            (PAGE_W - 2 * MARGIN) * 0.15,
            (PAGE_W - 2 * MARGIN) * 0.25,
        ],
    )
    summary_table.setStyle(TableStyle(summary_style))
    E.append(summary_table)
    E.append(Spacer(1, 6))

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 1 — DESIGN QUALITY
    # ═══════════════════════════════════════════════════════════════════════════
    E.append(section_header("1.  DESIGN QUALITY ANALYSIS   ▸   "
                            f"{report['design']['score']} / 15"))

    design_report = report["design"]["report"]
    for line in design_report.split("\n"):
        line = line.strip()
        if line:
            E.append(Paragraph(line, sBody))
    E.append(Spacer(1, 6))

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 2 — FUNCTIONAL TESTS
    # ═══════════════════════════════════════════════════════════════════════════
    E.append(section_header("2.  FUNCTIONAL TEST EXECUTION REPORT   ▸   "
                            f"{report['tests']['score']} / 30"))

    E.append(Paragraph(report["tests"]["report"], sBody))
    E.append(Paragraph(
        "Strategy: <b>Self-Oracle</b> — LLM generates stdin inputs only. "
        "The compiled binary produces expected outputs. "
        "A second run confirms reproducibility.",
        sSmall
    ))
    E.append(Spacer(1, 8))

    # Test cases table
    cases = report["tests"].get("cases", [])
    if cases:
        test_header_row = [
            Paragraph("#",         sTableHeader),
            Paragraph("Input\n(LLM Generated)", sTableHeader),
            Paragraph("Expected\n(Oracle Run)",  sTableHeader),
            Paragraph("Actual\n(Confirm Run)",   sTableHeader),
            Paragraph("Result",    sTableHeader),
        ]
        test_data_rows = [test_header_row]
        test_style = [
            ("BACKGROUND",    (0, 0), (-1, 0),  HEADER_GREY),
            ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#CED4DA")),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ]

        for ri, c in enumerate(cases, start=1):
            passed = c.get("pass", False)
            row_bg = PASS_GREEN if passed else FAIL_RED
            result_style = sPassCell if passed else sFailCell
            result_text  = "✓ PASS" if passed else "✗ FAIL"

            # Format input cleanly — numbered lines for multi-value inputs
            input_display = format_input(c)
            # Replace \n with actual newlines for Paragraph (use <br/>)
            input_html    = input_display.replace("\n", "<br/>")
            expected_html = str(c.get("expected", "")).replace("\n", "<br/>")
            actual_html   = str(c.get("actual", "")).replace("\n", "<br/>")

            test_data_rows.append([
                Paragraph(str(ri), sTableCellC),
                Paragraph(input_html,    sTableCell),
                Paragraph(expected_html, sTableCell),
                Paragraph(actual_html,   sTableCell),
                Paragraph(result_text,   result_style),
            ])
            test_style.append(
                ("BACKGROUND", (0, ri), (-1, ri), row_bg)
            )

        AVAIL = PAGE_W - 2 * MARGIN
        test_table = Table(
            test_data_rows,
            colWidths=[
                AVAIL * 0.05,   # #
                AVAIL * 0.25,   # input
                AVAIL * 0.28,   # expected
                AVAIL * 0.28,   # actual
                AVAIL * 0.14,   # result
            ],
            repeatRows=1,
        )
        test_table.setStyle(TableStyle(test_style))
        E.append(test_table)

    E.append(Spacer(1, 6))

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 3 — PERFORMANCE
    # ═══════════════════════════════════════════════════════════════════════════
    E.append(section_header("3.  PERFORMANCE & COMPLEXITY ANALYSIS   ▸   "
                            f"{report['performance']['score']} / 15"))

    perf_report = report["performance"]["report"]
    for line in perf_report.split("\n"):
        line = line.strip()
        if line:
            E.append(Paragraph(line, sBody))
    E.append(Spacer(1, 6))

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 4 — OPTIMIZATION
    # ═══════════════════════════════════════════════════════════════════════════
    E.append(section_header("4.  OPTIMIZATION SUGGESTIONS   ▸   "
                            f"{report['optimization']['score']} / 20"))

    opt_report = report["optimization"]["report"]
    for line in opt_report.split("\n"):
        line = line.strip()
        if line:
            E.append(Paragraph(line, sBody))
    E.append(Spacer(1, 6))

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 5 — STATIC ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════
    E.append(section_header(f"5.  STATIC ANALYSIS (CPPCHECK)   ▸   "
                            f"{report.get('static_score', 0):.1f} / 20"))

    static_raw = report.get("static_report", "")
    if static_raw.strip():
        for line in static_raw.split("\n"):
            line = line.strip()
            if line:
                # Highlight error/warning lines differently
                if any(t in line.lower() for t in ["error", "warning"]):
                    sWarn = PS("sw", fontName="Helvetica",
                               fontSize=8, textColor=colors.HexColor("#856404"),
                               leading=12, spaceAfter=2)
                    E.append(Paragraph(f"⚠ {line}", sWarn))
                else:
                    E.append(Paragraph(line, sSmall))
    else:
        E.append(Paragraph("✓ No warnings or errors detected.", sBody))
    E.append(Spacer(1, 6))

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 6 — GEMINI FINAL REPORT  (new page for breathing room)
    # ═══════════════════════════════════════════════════════════════════════════
    E.append(PageBreak())
    E.append(section_header("6. FINAL ACADEMIC EVALUATION"))

    gemini_raw = report.get("gemini_final_report", "")
    for flowable in render_gemini_report(gemini_raw):
        E.append(flowable)

    # ═══════════════════════════════════════════════════════════════════════════
    # FOOTER
    # ═══════════════════════════════════════════════════════════════════════════
    E.append(Spacer(1, 20))
    E.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CED4DA")))
    E.append(Spacer(1, 6))
    E.append(Paragraph(
        f"Professional C Autograder System  •  "
        f"Self-Oracle Test Mode  •  "
        f"Powered by Groq LLM & Gemini 2.5 Flash  •  "
        f"{datetime.datetime.now().strftime('%d %b %Y')}",
        sFooter
    ))

    # ── Build ─────────────────────────────────────────────────────────────────
    doc.build(E)
    return path
