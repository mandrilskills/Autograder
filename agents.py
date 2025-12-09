import re
import subprocess
import time
import json
from config import TEST_TIMEOUT_SECONDS
from llm import groq_generate_tests

# ---------------- DESIGN AGENT ----------------
def design_agent(source_path):
    src = open(source_path).read()
    lines = src.splitlines()
    funcs = re.findall(r'\w+\s+\**\w+\s*\([^)]*\)\s*\{', src)
    comments = src.count("//") + src.count("/*")

    score = 15
    if len(lines) > 200: score -= 2
    if len(funcs) < 2: score -= 3
    if comments < 3: score -= 2

    return {
        "score": max(score, 0),
        "report": f"Lines: {len(lines)}, Functions: {len(funcs)}, Comments: {comments}"
    }

# ---------------- ✅ TEST AGENT (GROQ) ----------------
def test_agent(title, source_path, binary_path):
    prompt = f"""
Generate EXACTLY 5 test cases.
Return ONLY valid JSON.

Program Title:
{title}

Format:
[
  {{"input":"value","expected":"value"}}
]
"""

    raw = groq_generate_tests(prompt)

    try:
        block = raw[raw.find("["): raw.rfind("]")+1]
        test_cases = json.loads(block)
        if len(test_cases) != 5:
            raise ValueError
    except:
        test_cases = [
            {"input":"1\n","expected":"1"},
            {"input":"0\n","expected":"0"},
            {"input":"5\n","expected":"5"},
            {"input":"-1\n","expected":"-1"},
            {"input":"10\n","expected":"10"}
        ]

    passed = 0
    results = []

    for tc in test_cases:
        try:
            proc = subprocess.run(
                [binary_path],
                input=tc["input"].encode(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=TEST_TIMEOUT_SECONDS
            )
            actual = proc.stdout.decode().strip()
            expected = str(tc["expected"]).strip()
            ok = actual == expected
        except:
            actual = "Runtime Error"
            ok = False

        if ok: passed += 1

        results.append({
            "input": tc["input"],
            "expected": expected,
            "actual": actual,
            "pass": ok
        })

    return {
        "score": round((passed / 5) * 30, 2),
        "report": f"{passed}/5 test cases passed.",
        "cases": results
    }

# ---------------- ✅ PERFORMANCE AGENT (THIS WAS MISSING) ----------------
def performance_agent(source_path, binary_path):
    try:
        start = time.time()
        subprocess.run([binary_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=1)
        runtime = time.time() - start
    except subprocess.TimeoutExpired:
        runtime = 5.0

    try:
        src = open(source_path).read()
    except:
        src = ""

    loops = len(re.findall(r"for\s*\(|while\s*\(", src))
    branches = len(re.findall(r"\bif\b|\bswitch\b|\bcase\b", src))

    score = 15
    if runtime > 0.7: score -= 3
    if runtime > 1.2: score -= 3
    if loops > 5: score -= 2
    if branches > 12: score -= 2
    if score < 0: score = 0

    return {
        "score": round(score, 2),
        "report": f"Runtime: {runtime:.3f}s | Loops: {loops} | Branches: {branches}"
    }

# ---------------- OPTIMIZATION AGENT ----------------
def optimization_agent(source_path):
    src = open(source_path).read()
    score = 20
    notes = []

    if "malloc" in src and "free" not in src:
        score -= 4
        notes.append("Potential memory leak: malloc without free.")

    if re.search(r'for.*printf', src, re.S):
        score -= 3
        notes.append("printf inside loop — use buffered output.")

    return {
        "score": max(score, 0),
        "report": "\n".join(notes) if notes else "No major optimization issues detected."
    }
