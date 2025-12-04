# llm_agent.py
"""
Deterministic/local structural analysis used as fallback.
Keeps same safe evaluate_structural_steps implementation as before.
"""

import re

def evaluate_structural_steps(code_text: str) -> dict:
    def safe_search(p, t):
        try:
            return bool(re.search(p, t))
        except re.error:
            plain = re.sub(r'[^0-9A-Za-z_\\s]', ' ', p)
            tokens = [x for x in plain.split() if x]
            return any(tok in t for tok in tokens)

    steps=[]
    score=0

    main_ok = ('int main' in code_text) or safe_search(r'\bmain\s*\(', code_text)
    if main_ok:
        steps.append({"name":"main function","ok":True,"weight":15,"evidence":"main found"}); score+=15
    else:
        steps.append({"name":"main function","ok":False,"weight":15,"evidence":"missing"})

    if "#include" in code_text:
        steps.append({"name":"includes","ok":True,"weight":10,"evidence":"includes present"}); score+=10
    else:
        steps.append({"name":"includes","ok":False,"weight":10,"evidence":"none"})

    if "scanf" in code_text or "fscanf" in code_text:
        steps.append({"name":"input reading","ok":True,"weight":20,"evidence":"scanf present"}); score+=20
    else:
        steps.append({"name":"input reading","ok":False,"weight":20,"evidence":"none"})

    if safe_search(r'\bfor\b', code_text) or safe_search(r'\bwhile\b', code_text) or 'do {' in code_text:
        steps.append({"name":"loops","ok":True,"weight":20,"evidence":"loop found"}); score+=20
    else:
        steps.append({"name":"loops","ok":False,"weight":20,"evidence":"none"})

    if "printf" in code_text:
        steps.append({"name":"output","ok":True,"weight":20,"evidence":"printf present"}); score+=20
    else:
        steps.append({"name":"output","ok":False,"weight":20,"evidence":"none"})

    has_comments = ("//" in code_text) or ("/*" in code_text)
    steps.append({"name":"comments","ok":has_comments,"weight":15,"evidence":"present" if has_comments else "none"})
    if has_comments:
        score += 15

    return {"steps":steps,"structural_score": min(int(score),100), "has_comments": has_comments}
