# llm_agent.py
# SAFE VERSION — NO REGEX ANYWHERE

def evaluate_structural_steps(code_text: str) -> dict:
    steps = []
    score = 0

    # 1) main detection (NO REGEX)
    main_ok = ("int main" in code_text) or ("main(" in code_text)
    steps.append({
        "name": "main function",
        "ok": main_ok,
        "weight": 15,
        "evidence": "found" if main_ok else "missing"
    })
    if main_ok: score += 15

    # 2) includes
    includes_ok = "#include" in code_text
    steps.append({
        "name": "includes",
        "ok": includes_ok,
        "weight": 10,
        "evidence": "found" if includes_ok else "missing"
    })
    if includes_ok: score += 10

    # 3) input
    input_ok = "scanf" in code_text or "fscanf" in code_text
    steps.append({
        "name": "input reading",
        "ok": input_ok,
        "weight": 20,
        "evidence": "scanf present" if input_ok else "none"
    })
    if input_ok: score += 20

    # 4) loop
    loop_ok = ("for" in code_text) or ("while" in code_text) or ("do" in code_text)
    steps.append({
        "name": "loops",
        "ok": loop_ok,
        "weight": 20,
        "evidence": "loop found" if loop_ok else "none"
    })
    if loop_ok: score += 20

    # 5) output
    out_ok = "printf" in code_text or "puts(" in code_text
    steps.append({
        "name": "output",
        "ok": out_ok,
        "weight": 20,
        "evidence": "printf present" if out_ok else "none"
    })
    if out_ok: score += 20

    # 6) comments
    comments_ok = ("//" in code_text) or ("/*" in code_text)
    steps.append({
        "name": "comments",
        "ok": comments_ok,
        "weight": 15,
        "evidence": "present" if comments_ok else "none"
    })
    if comments_ok: score += 15

    return {
        "steps": steps,
        "structural_score": min(score, 100),
        "has_comments": comments_ok
    }
