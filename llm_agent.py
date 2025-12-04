# llm_agent.py

def evaluate_structural_steps(code_text: str) -> dict:
    steps = []
    score = 0

    def add_step(name, ok, weight, evidence):
        nonlocal score
        steps.append({"name": name, "ok": ok, "weight": weight, "evidence": evidence})
        if ok: score += weight

    add_step("main function", "main(" in code_text, 15, "main detected" if "main(" in code_text else "missing")
    add_step("includes", "#include" in code_text, 10, "includes found" if "#include" in code_text else "none")
    add_step("input reading", "scanf" in code_text or "fscanf" in code_text, 20, "scanf present" if "scanf" in code_text else "none")
    add_step("loops", any(x in code_text for x in ["for", "while", "do"]), 20, "loop found" if any(x in code_text for x in ["for","while","do"]) else "none")
    add_step("output", "printf" in code_text or "puts(" in code_text, 20, "printf present" if "printf" in code_text else "none")

    comments_ok = ("//" in code_text) or ("/*" in code_text)
    add_step("comments", comments_ok, 15, "present" if comments_ok else "none")

    return {"steps": steps, "structural_score": min(score, 100), "has_comments": comments_ok}
