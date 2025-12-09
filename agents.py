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

# ---------------- GROQ LLM TEST AGENT ----------------
# ---------------- ✅ GROQ LLM TEST AGENT (FIXED & RELIABLE) ----------------
def test_agent(title, source_path, binary_path):
    import json
    import subprocess
    from llm import groq_generate_tests
    from config import TEST_TIMEOUT_SECONDS

    prompt = f"""
You are an automated software test generator for C programs.

Program Title:
{title}

STRICT INSTRUCTIONS:
- Generate exactly 5 test cases.
- Each test case MUST contain:
  1. "input"
  2. "expected"
- Output ONLY valid JSON.
- No explanation. No markdown.

FORMAT:
[
  {{"input": "value", "expected": "value"}},
  {{"input": "value", "expected": "value"}}
]
"""

    raw = groq_generate_tests(prompt)

    # ✅ HARD VALIDATION + FALLBACK
    try:
        json_block = raw[raw.find("["): raw.rfind("]")+1]
        test_cases = json.loads(json_block)
        if len(test_cases) != 5:
            raise ValueError("Not exactly 5 cases")
    except:
        # 🔴 Deterministic fallback if Groq fails
        test_cases = [
            {"input": "5\n", "expected": "5"},
            {"input": "0\n", "expected": "0"},
            {"input": "1\n", "expected": "1"},
            {"input": "-1\n", "expected": "-1"},
            {"input": "10\n", "expected": "10"}
        ]

    results = []
    passed = 0

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
            status = actual == expected

        except:
            actual = "Runtime Error"
            status = False

        if status:
            passed += 1

        results.append({
            "input": tc["input"],
            "expected": expected,
            "actual": actual,
            "pass": status
        })

    score = (passed / len(test_cases)) * 30

    return {
        "score": round(score, 2),
        "report": f"{passed}/{len(test_cases)} test cases passed.",
        "cases": results
    }

# ---------------- OPTIMIZATION AGENT ----------------
def optimization_agent(source_path):
    src = open(source_path).read()
    score = 20
    suggestions = []

    if "malloc" in src and "free" not in src:
        score -= 4
        suggestions.append("Possible memory leak: malloc without free.")

    if re.search(r'for.*printf', src, re.S):
        score -= 3
        suggestions.append("printf used inside loop — buffer output.")

    return {
        "score": max(score, 0),
        "report": "\n".join(suggestions) if suggestions else "No major optimizations required."
    }

def performance_agent(source_path, binary_path):
    """
    Measures runtime + checks complexity patterns.
    Returns score out of 15.
    """

    import subprocess, time, re

    try:
        start = time.time()
        proc = subprocess.run(
            [binary_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=1
        )
        runtime = time.time() - start
    except subprocess.TimeoutExpired:
        runtime = 5.0  # heavy timeout penalty

    # Try reading source
    try:
        src = open(source_path).read()
    except:
        src = ""

    # Complexity signals
    loops = len(re.findall(r"for\s*\(|while\s*\(", src))
    branches = len(re.findall(r"\bif\b|\bswitch\b|\bcase\b", src))

    score = 15

    # Runtime penalties
    if runtime > 0.7: score -= 3
    if runtime > 1.2: score -= 3

    # Complexity penalties
    if loops > 5: score -= 2
    if branches > 12: score -= 2

    if score < 0: score = 0

    return {
        "score": round(score, 2),
        "report": f"Runtime: {runtime:.3f}s | Loops: {loops} | Branches: {branches}"
    }


