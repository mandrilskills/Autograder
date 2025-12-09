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
def test_agent(title, source_path, binary_path):
    prompt = f"""
Generate 5-6 logical test cases for the following C program.

Program Title:
{title}

Return JSON only in this format:
[
  {{ "input": "value", "expected": "value" }}
]
"""
    raw = groq_generate_tests(prompt)

    if not raw:
        # fallback heuristic if Groq key missing
        test_cases = [{"input":"5\n"},{"input":"0\n"},{"input":"-1\n"},{"input":"10\n"}]
    else:
        test_cases = json.loads(re.findall(r'\[.*\]', raw, re.S)[0])

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
            out = proc.stdout.decode().strip()
            status = out == str(tc.get("expected", out)).strip()
            if status: passed += 1
        except:
            status = False

        results.append({
            "input": tc["input"],
            "expected": tc.get("expected", "LLM"),
            "actual": out if "out" in locals() else "",
            "pass": status
        })

    score = (passed / len(test_cases)) * 30

    return {
        "score": round(score, 2),
        "report": f"{passed}/{len(test_cases)} test cases passed.",
        "cases": results
    }

# ---------------- PERFORMANCE AGENT ----------------
def performance_agent(source_path, binary_path):
    start = time.time()
    try:
        subprocess.run([binary_path], timeout=1)
    except:
        pass
    runtime = time.time() - start

    score = 15 if runtime < 0.5 else 12 if runtime < 1 else 8

    return {
        "score": score,
        "report": f"Measured runtime ≈ {runtime:.4f}s"
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

