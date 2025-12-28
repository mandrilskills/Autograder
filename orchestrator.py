from agents import design_agent, test_agent, performance_agent, optimization_agent
from config import WEIGHTS
from llm import gemini_generate_report

def run_orchestration(title, source_c, binary, static_report):
    design = design_agent(source_c)
    tests = test_agent(title, source_c, binary)
    performance = performance_agent(source_c, binary)
    optimization = optimization_agent(source_c)

    # Improved Static Analysis Scoring
    # Count occurrences of actual issues, not just lines
    # Cppcheck standard format usually includes ": (error)" or ": (warning)"
    # Fallback to counting lines that have '):' which indicates a file position
    issue_count = static_report.count("error:") + static_report.count("warning:")
    if issue_count == 0 and "Checking" in static_report:
         # Fallback if standard keywords aren't found but report is not empty
         # Filter out "Checking..." lines
         lines = [line for line in static_report.splitlines() if "Checking " not in line and line.strip() != ""]
         issue_count = len(lines)

    static_score = max(0, 20 - issue_count * 2.0)

    total = (
        design["score"]
        + tests["score"]
        + performance["score"]
        + optimization["score"]
        + static_score
    )

    raw_report = {
        "design": design,
        "tests": tests,
        "performance": performance,
        "optimization": optimization,
        "static_report": static_report,
        "static_score": round(static_score,2),
        "total_score": round(min(total,100),2)
    }

    # ✅ FINAL REPORT BY GEMINI 2.5 FLASH
    prompt = f"""
Generate a professional university-grade evaluation report using this data.
No JSON. Human readable format.

DATA:
{raw_report}
"""
    final_text = gemini_generate_report(prompt)
    raw_report["gemini_final_report"] = final_text if final_text else "Gemini API not configured."

    return raw_report
