from agents import design_agent, test_agent, performance_agent, optimization_agent
from config import WEIGHTS
from llm import gemini_generate_report

def run_orchestration(title, source_c, binary, static_report):
    design = design_agent(source_c)
    tests = test_agent(title, source_c, binary)
    performance = performance_agent(source_c, binary)
    optimization = optimization_agent(source_c)

    static_warnings = len(static_report.splitlines()) if static_report.strip() else 0
    static_score = max(0, 20 - static_warnings * 1.5)

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

