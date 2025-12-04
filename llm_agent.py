# llm_agent.py
"""
Minimal agentic layer (mock) with defensive regex usage.
Functions:
- analyze_intent(code_text) -> dict
- evaluate_structural_steps(code_text) -> dict (step-wise)  <-- patched safely
- interpret_compiler_errors(error_text) -> dict
- generate_feedback_text(evaluation) -> str

Replace or extend with a real LLM-backed implementation when ready.
"""

import re
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def analyze_intent(code_text: str) -> dict:
    """
    Heuristic/agentic intent extraction.
    Returns a small dict describing what the code appears to do.
    """
    text = code_text.lower()
    intent = "unknown"
    if "scanf" in text or "printf" in text:
        intent = "io_console"
    elif "argc" in text or "argv" in text:
        intent = "cli_args"
    elif "fopen" in text or "fscanf" in text:
        intent = "file_io"
    elif "malloc" in text or "free" in text:
        intent = "memory_management"
    else:
        intent = "computation"
    summary = f"Detected intent: {intent}"
    return {"intent": intent, "summary": summary}


def evaluate_structural_steps(code_text: str) -> dict:
    """
    Heuristic structural evaluation producing:
    - steps: list of {name, ok, weight, evidence}
    - structural_score: 0-100
    - has_comments: bool

    Defensive: regex usage is wrapped in try/except to avoid PatternError crashes.
    """

    # Helper safe-search to avoid PatternError exceptions
    def safe_search(pattern: str, text: str) -> bool:
        try:
            return bool(re.search(pattern, text))
        except re.error:
            # fallback to a plain substring/token check if regex fails
            try:
                # Remove obvious regex meta-characters to build a crude fallback token list
                plain = re.sub(r'[^0-9A-Za-z_\\s]', ' ', pattern)
                tokens = [t for t in plain.split() if t]
                return any(tok in text for tok in tokens)
            except Exception:
                return False

    steps = []
    score = 0

    # 1) main present (use substring + safe regex)
    main_ok = ('int main' in code_text) or safe_search(r'\bmain\s*\(', code_text)
    if main_ok:
        steps.append({"name": "main function", "ok": True, "weight": 15, "evidence": "main found"})
        score += 15
    else:
        steps.append({"name": "main function", "ok": False, "weight": 15, "evidence": "main not found"})

    # 2) includes
    includes_ok = ('#include' in code_text)
    if includes_ok:
        steps.append({"name": "includes (stdio etc.)", "ok": True, "weight": 10, "evidence": "includes present"})
        score += 10
    else:
        steps.append({"name": "includes (stdio etc.)", "ok": False, "weight": 10, "evidence": "no includes"})

    # 3) input reading
    input_ok = ('scanf' in code_text) or ('fscanf' in code_text) or safe_search(r'\bgets?\b', code_text)
    if input_ok:
        steps.append({"name": "input reading", "ok": True, "weight": 20, "evidence": "scanf/fscanf/gets present"})
        score += 20
    else:
        steps.append({"name": "input reading", "ok": False, "weight": 20, "evidence": "no scanf/fscanf/gets detected"})

    # 4) loops / iteration
    loop_ok = safe_search(r'\bfor\b', code_text) or safe_search(r'\bwhile\b', code_text) or ('do {' in code_text) or ('do\t' in code_text)
    if loop_ok:
        steps.append({"name": "loop/iteration", "ok": True, "weight": 20, "evidence": "loop keyword detected"})
        score += 20
    else:
        steps.append({"name": "loop/iteration", "ok": False, "weight": 20, "evidence": "no loop detected"})

    # 5) output
    output_ok = ('printf' in code_text) or ('puts(' in code_text) or safe_search(r'\bputchar\b', code_text)
    if output_ok:
        steps.append({"name": "output (printf/puts)", "ok": True, "weight": 20, "evidence": "printf/puts/putchar present"})
        score += 20
    else:
        steps.append({"name": "output (printf/puts)", "ok": False, "weight": 20, "evidence": "no printf/puts/putchar"})

    # 6) comments
    has_comments = ("//" in code_text) or ("/*" in code_text)
    steps.append({"name": "comments", "ok": has_comments, "weight": 15, "evidence": "comments present" if has_comments else "none"})
    if has_comments:
        score += 15

    # Normalize structural_score 0-100
    structural_score = min(int(score), 100)

    return {
        "steps": steps,
        "structural_score": structural_score,
        "has_comments": has_comments,
    }


def interpret_compiler_errors(error_text: str) -> dict:
    """
    Lightweight interpretation of compiler/linker/runtime messages.
    Returns messages, severity and a short suggestion.
    """
    msgs = []
    et = (error_text or "").lower()
    if "error:" in et:
        msgs.append("Compilation errors found.")
    if "undefined reference" in et:
        msgs.append("Linker: undefined reference - check function names/signatures and linking order.")
    if "expected" in et and "before" in et:
        msgs.append("Syntax error - probable missing semicolon or parenthesis.")
    if "segmentation fault" in et:
        msgs.append("Runtime segfault likely due to invalid memory access.")
    if not msgs:
        msgs.append("Unknown compilation issue. Inspect raw compiler output.")
    severity = "error" if "error" in et else "warning" if "warning" in et else "info"
    suggestion = msgs[0] if msgs else "Check compiler output."
    return {"messages": msgs, "severity": severity, "suggestion": suggestion, "raw": error_text}


def generate_feedback_text(evaluation: dict) -> str:
    """
    Produce a readable textual report from evaluation dict.
    This is a simple fallback reporter; replace with an LLM-generated report if desired.
    """
    parts = []
    parts.append(f"Final Score: {evaluation.get('final_score', 'N/A')}/100")
    parts.append("----")
    comp = evaluation.get("compile", {})
    if comp.get("status") != "success":
        parts.append("Compilation: FAILED")
        stderr = comp.get("stderr", "")
        if stderr:
            parts.append("Compiler output (short):")
            parts.append(stderr[:1000])
        if evaluation.get("compiler_diagnostics"):
            parts.append("Agent diagnostics:")
            for m in evaluation["compiler_diagnostics"].get("messages", []):
                parts.append("- " + m)
    else:
        parts.append("Compilation: SUCCESS")
    parts.append("Structural analysis (key steps):")
    struct = evaluation.get("structural_analysis", {})
    for s in struct.get("steps", []):
        ok = "OK" if s.get("ok") else "MISSING"
        parts.append(f"- {s.get('name')}: {ok} (evidence: {s.get('evidence','')})")
    parts.append("Scores breakdown:")
    for k, v in evaluation.get("scores", {}).items():
        parts.append(f"  {k}: {v}")
    parts.append("Recommendations:")
    if comp.get("status") != "success":
        parts.append("- Fix compilation errors first; check semicolons, includes and types.")
    parts.append("- Add comments to explain algorithm steps.")
    parts.append("- Ensure input reading matches the problem's specification and validate scanf returns.")
    return "\n".join(parts)


# If this file is run directly, exercise a tiny smoke test.
if __name__ == "__main__":
    sample = """
    #include <stdio.h>
    int main() {
        int a, b;
        if (scanf("%d %d", &a, &b) != 2) {
            printf("Invalid\\n");
            return 1;
        }
        printf("%d\\n", a+b);
        return 0;
    }
    """
    print("Intent:", analyze_intent(sample))
    print("Structure:", evaluate_structural_steps(sample))
    print("Errors parse:", interpret_compiler_errors("submission.c:3:5: error: expected ';' before 'return'"))
    print("Feedback:\n", generate_feedback_text({"final_score": 85, "compile":{"status":"success"}, "structural_analysis": evaluate_structural_steps(sample), "scores": {"attempt": 10, "structure": 25, "algorithm": 30, "style": 10, "execution": 10}}))
