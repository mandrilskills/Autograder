# llm_agent.py
"""
Minimal agentic layer (mock). Replace with real LLM calls in production.
Functions:
- analyze_intent(code_text) -> dict
- evaluate_structural_steps(code_text) -> dict (step-wise)
- interpret_compiler_errors(error_text) -> dict
- generate_feedback_text(evaluation) -> str
"""

import re

def analyze_intent(code_text: str) -> dict:
    text = code_text.lower()
    intent = "unknown"
    if "scanf" in text or "printf" in text:
        intent = "io_console"
    elif "argc" in text or "argv" in text:
        intent = "cli_args"
    else:
        intent = "computation"
    # short summary
    summary = "Detected intent: " + intent
    return {"intent": intent, "summary": summary}

def evaluate_structural_steps(code_text: str) -> dict:
    """
    Heuristic structural evaluation producing:
    - steps: list of {name, ok, weight}
    - structural_score: 0-100
    - has_comments: bool
    """
    steps = []
    score = 0

    # main present
    if re.search(r'\\bint\\s+main\\s*\\(|\\bmain\\s*\\(', code_text):
        steps.append({"name": "main function", "ok": True, "weight": 15})
        score += 15
    else:
        steps.append({"name": "main function", "ok": False, "weight": 15})

    # includes
    if "#include" in code_text:
        steps.append({"name": "includes (stdio etc.)", "ok": True, "weight": 10})
        score += 10
    else:
        steps.append({"name": "includes", "ok": False, "weight": 10})

    # input reading
    if "scanf" in code_text or "fscanf" in code_text:
        steps.append({"name": "input reading", "ok": True, "weight": 20})
        score += 20
    else:
        steps.append({"name": "input reading", "ok": False, "weight": 20})

    # loops / iteration
    if re.search(r'\\bfor\\s*\\(|\\bwhile\\s*\\(|\\bdo\\s*\\{', code_text):
        steps.append({"name": "loop/iteration", "ok": True, "weight": 20})
        score += 20
    else:
        steps.append({"name": "loop/iteration", "ok": False, "weight": 20})

    # output
    if "printf" in code_text:
        steps.append({"name": "output (printf)", "ok": True, "weight": 20})
        score += 20
    else:
        steps.append({"name": "output (printf)", "ok": False, "weight": 20})

    # comments
    has_comments = ("//" in code_text) or ("/*" in code_text)
    steps.append({"name": "comments", "ok": has_comments, "weight": 15})
    if has_comments:
        score += 15

    # normalize structural_score 0-100
    structural_score = min(int(score), 100)
    return {
        "steps": steps,
        "structural_score": structural_score,
        "has_comments": has_comments
    }

def interpret_compiler_errors(error_text: str) -> dict:
    msgs = []
    et = error_text.lower()
    if "error:" in et:
        msgs.append("Compilation errors found.")
    if "undefined reference" in et:
        msgs.append("Linker: undefined reference - missing function or wrong signature.")
    if "expected" in et and "before" in et:
        msgs.append("Syntax error - probable missing semicolon or parenthesis.")
    if "segmentation fault" in et:
        msgs.append("Runtime segfault likely due to invalid memory access.")
    if not msgs:
        msgs.append("Unknown compilation issue. See raw compiler output.")
    return {"messages": msgs, "raw": error_text}

def generate_feedback_text(evaluation: dict) -> str:
    """
    Produce a readable textual report from evaluation dict.
    This may later be replaced by an LLM-generated, more verbose report.
    """
    lines = []
    lines.append(f"Final Score: {evaluation.get('final_score', 'N/A')}/100")
    lines.append("----")
    comp = evaluation.get("compile", {})
    if comp.get("status") != "success":
        lines.append("Compilation: FAILED")
        stderr = comp.get("stderr","")
        if stderr:
            lines.append("Compiler output (short):")
            lines.append(stderr[:1000])
        # agent diagnostics
        if evaluation.get("compiler_diagnostics"):
            lines.append("Agent diagnostics:")
            for m in evaluation["compiler_diagnostics"].get("messages", []):
                lines.append("- " + m)
    else:
        lines.append("Compilation: SUCCESS")
    # structural
    struct = evaluation.get("structural_analysis", {})
    lines.append("Structural analysis (key steps):")
    for s in struct.get("steps", []):
        ok = "OK" if s.get("ok") else "MISSING"
        lines.append(f"- {s.get('name')}: {ok}")
    # scoring breakdown
    scores = evaluation.get("scores", {})
    lines.append("Scores breakdown:")
    for k,v in scores.items():
        lines.append(f"  {k}: {v}")
    lines.append("Recommendations:")
    if comp.get("status") != "success":
        lines.append("- Fix compilation errors first. Check missing semicolons, types and includes.")
    lines.append("- Add comments to explain algorithm steps.")
    lines.append("- Ensure input reading matches problem statement (use robust scanf checks).")
    return "\\n".join(lines)
