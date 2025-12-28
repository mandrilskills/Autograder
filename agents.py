import re
import subprocess
import time
import json
from config import TEST_TIMEOUT_SECONDS
from llm import groq_generate_tests

# ---------------- DESIGN AGENT ----------------
def design_agent(source_path):
    try:
        src = open(source_path, encoding="utf-8", errors="ignore").read()
    except Exception:
        src = ""

    lines = src.splitlines()
    # Improved regex to handle braces on new lines
    funcs = re.findall(r'\w+\s+\**\w+\s*\([^)]*\)\s*[\r\n\s]*\{', src)
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
    # FIX: Improved prompt to ensure simpler inputs/outputs for C compatibility
    prompt = f"""
Generate EXACTLY 5 test cases.
Return ONLY valid JSON.
Ensure inputs are simple values suitable for standard input (stdin).

Program Title:
{title}

Format:
[
  {{"input":"value","expected":"value"}}
]
"""

    raw = groq_generate_tests(prompt)

    try:
        # Robust JSON extraction
        start_idx = raw.find("[")
        end_idx = raw.rfind("]")
        if start_idx == -1 or end_idx == -1:
            raise ValueError("No JSON found")
        
        block = raw[start_idx : end_idx+1]
        test_cases = json.loads(block)
        
        if not isinstance(test_cases, list):
            raise ValueError("Result is not a list")
            
        # Ensure we don't process more than 5 if LLM hallucinations occur
        if len(test_cases) > 5:
            test_cases = test_cases[:5]
    except Exception:
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
        expected = str(tc.get("expected", "Unknown")).strip()
        input_val = str(tc.get("input", ""))
        
        # FIX: Ensure input ends with a newline for C 'scanf' compatibility
        if not input_val.endswith("\n"):
            input_val += "\n"

        try:
            proc = subprocess.run(
                [binary_path],
                input=input_val.encode(), # Ensure input is bytes
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=TEST_TIMEOUT_SECONDS
            )
            actual = proc.stdout.decode(errors='replace').strip()
            
            # FIX: Flexible & Case-Insensitive comparison.
            # 1. Normalize both to lowercase
            # 2. Check if expected is contained in actual (handles prompts like "Result: ")
            
            exp_clean = expected.lower()
            act_clean = actual.lower()

            if exp_clean == act_clean:
                ok = True
            elif exp_clean in act_clean:
                ok = True
            else:
                ok = False
                
        except subprocess.TimeoutExpired:
            actual = "Timeout"
            ok = False
        except Exception:
            actual = "Runtime Error"
            ok = False

        if ok: passed += 1

        results.append({
            "input": input_val.strip(),
            "expected": expected,
            "actual": actual,
            "pass": ok
        })

    return {
        "score": round((passed / 5) * 30, 2),
        "report": f"{passed}/5 test cases passed.",
        "cases": results
    }

# ---------------- ✅ PERFORMANCE AGENT ----------------
def performance_agent(source_path, binary_path):
    try:
        start = time.time()
        # FIX: Use configured timeout, not hardcoded 1s
        subprocess.run(
            [binary_path], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            timeout=TEST_TIMEOUT_SECONDS
        )
        runtime = time.time() - start
    except subprocess.TimeoutExpired:
        runtime = float(TEST_TIMEOUT_SECONDS) + 0.5 # Penalize timeout
    except Exception:
        runtime = 0.0

    try:
        src = open(source_path, encoding="utf-8", errors="ignore").read()
    except Exception:
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
    try:
        src = open(source_path, encoding="utf-8", errors="ignore").read()
    except Exception:
        src = ""

    score = 20
    notes = []

    if "malloc" in src and "free" not in src:
        score -= 4
        notes.append("Potential memory leak: malloc without free.")

    if re.search(r'for.*printf', src, re.S):
        score -= 3
        notes.append("printf inside loop — use buffered output or build string first.")

    return {
        "score": max(score, 0),
        "report": "\n".join(notes) if notes else "No major optimization issues detected."
    }
