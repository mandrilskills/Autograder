# utils.py
import hashlib, re

def code_hash(code_text: str) -> str:
    return hashlib.sha256(code_text.encode('utf-8')).hexdigest()[:12]

def simple_readability_score(code_text: str) -> int:
    # Very naive: more comments and shorter lines -> higher score
    lines = code_text.splitlines()
    comment_lines = sum(1 for l in lines if l.strip().startswith("//") or "/*" in l)
    avg_len = sum(len(l) for l in lines)/max(1,len(lines))
    score = max(0, min(100, int((comment_lines*5) + (50 - avg_len/2))))
    return score

def strip_whitespace(s: str) -> str:
    return re.sub(r'\\s+', ' ', s).strip()
