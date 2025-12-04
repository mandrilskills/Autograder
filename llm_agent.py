# llm_agent.py
"""
Deterministic structural step evaluator used as fallback.
No regex patterns that can break in different environments.
"""

def evaluate_structural_steps(code_text: str) -> dict:
    steps = []
    score = 0

    def add_step(name: str, ok: bool, weight: int, evidence: str):
        nonlocal score
        steps.append({"name": name, "ok": ok, "weight": weight, "evidence": evidence})
        if ok:
            score += weight

    main_ok = "main(" in code_text
    add_step("main function", main_ok, 15, "main detected" if main_ok else "missing")

    includes_ok = "#include" in code_text
    add_step("includes", includes_ok, 10, "includes found" if includes_ok else "none")

    input_ok = ("scanf" in code_text) or ("fscanf" in code_text)
    add_step("input reading", input_ok, 20, "scanf/fscanf present" if input_ok else "none")

    loop_ok = any(k in code_text for k in ("for", "while", "do"))
    add_step("loops/iteration", loop_ok, 20, "loop detected" if loop_ok else "none")

    output_ok = ("printf" in code_text) or ("puts(" in code_text) or ("putchar" in code_text)
    add_step("output", output_ok, 20, "printf/puts present" if output_ok else "none")

    comments_ok = ("//" in code_text) or ("/*" in code_text)
    add_step("comments", comments_ok, 15, "comments present" if comments_ok else "none")

    structural_score = min(score, 100)
    return {"steps": steps, "structural_score": structural_score, "has_comments": comments_ok}


def interpret_compiler_errors(stderr_text: str) -> dict:
    # Lightweight heuristic for compiler messages (used if Gemini not available)
    msgs = []
    s = (stderr_text or "").lower()
    if "error:" in s:
        msgs.append("Compilation error(s) present.")
    if "undefined reference" in s:
        msgs.append("Linker error: undefined reference.")
    if "expected" in s and "before" in s:
        msgs.append("Syntax error — missing token (semicolon/brace).")
    if not msgs:
        msgs.append("See raw compiler output.")
    return {"messages": msgs, "raw": stderr_text}
