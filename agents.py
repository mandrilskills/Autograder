"""
agents.py
Multi-Agent Grading System — Professional C Autograder

Agents:
  - design_agent       → Code structure & quality (15 pts)
  - test_agent         → Groq LLM-generated functional tests (30 pts)
  - performance_agent  → Runtime & complexity analysis (15 pts)
  - optimization_agent → Memory & I/O best practices (20 pts)

Fixes applied to test_agent:
  [1] Source code is now included in the LLM prompt for accurate test generation
  [2] Strict JSON validation (list type + field presence check)
  [3] Explicit None guard when GROQ_API_KEY is missing or LLM call fails
  [4] All errors are logged — no more silent swallowing via bare except
  [5] All inputs are normalized to end with \\n before subprocess execution
  [6] Timeout and runtime errors are reported distinctly in results
"""

import re
import json
import logging
import subprocess
import time

from config import TEST_TIMEOUT_SECONDS
from llm import groq_generate_tests

# Module-level logger — output appears in your terminal / Streamlit logs
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)


# ─────────────────────────────────────────────────────────────
# DESIGN AGENT  (15 pts)
# Evaluates code structure: line count, function count, comments
# ─────────────────────────────────────────────────────────────
def design_agent(source_path: str) -> dict:
    """
    Scores the submitted C source on design / readability criteria.

    Returns:
        dict with keys: score (int), report (str)
    """
    try:
        src = open(source_path).read()
    except OSError as e:
        logger.error(f"design_agent: cannot read source file — {e}")
        return {"score": 0, "report": "Source file could not be read."}

    lines    = src.splitlines()
    funcs    = re.findall(r'\w+\s+\**\w+\s*\([^)]*\)\s*\{', src)
    comments = src.count("//") + src.count("/*")

    score      = 15
    deductions = []

    if len(lines) > 200:
        score -= 2
        deductions.append("File exceeds 200 lines (-2)")
    if len(funcs) < 2:
        score -= 3
        deductions.append("Fewer than 2 functions detected (-3)")
    if comments < 3:
        score -= 2
        deductions.append("Insufficient comments (-2)")

    report = (
        f"Lines: {len(lines)} | Functions: {len(funcs)} | Comments: {comments}"
    )
    if deductions:
        report += "\nDeductions: " + "; ".join(deductions)

    return {"score": max(score, 0), "report": report}


# ─────────────────────────────────────────────────────────────
# TEST AGENT  (30 pts)
# Uses Groq LLM to generate context-aware test cases, then
# runs each against the compiled binary and compares output.
# ─────────────────────────────────────────────────────────────
def test_agent(title: str, source_path: str, binary_path: str) -> dict:
    """
    Generates 5 test cases via Groq LLM (with source-code context),
    executes them against the binary, and scores the results.

    Returns:
        dict with keys: score (float), report (str), cases (list[dict])
    """

    # ── FIX 1: Read source so the LLM understands the program's I/O contract ──
    try:
        src = open(source_path).read()
    except OSError as e:
        logger.warning(f"test_agent: cannot read source file ({e}); LLM prompt will lack code context.")
        src = "(source code unavailable)"

    # ── FIX 2: Rich, context-aware prompt ──────────────────────────────────────
    prompt = f"""
You are a C programming test engineer. Carefully read the C source code below
and generate EXACTLY 5 test cases that verify the program's core functionality.

Program Title: {title}

Source Code:
```c
{src}
```

Instructions:
- "input"    → the exact string sent to stdin (use \\n where the program reads a newline).
- "expected" → the exact string the program writes to stdout, trimmed of leading/trailing whitespace.
- Cover normal cases, boundary values, and at least one edge case.
- Return ONLY a valid JSON array — no explanation, no markdown fences, no extra text.

Required format:
[
  {{"input": "value\\n", "expected": "value"}},
  {{"input": "value\\n", "expected": "value"}},
  {{"input": "value\\n", "expected": "value"}},
  {{"input": "value\\n", "expected": "value"}},
  {{"input": "value\\n", "expected": "value"}}
]
"""

    raw = groq_generate_tests(prompt)

    # ── FIX 3 & 4: Explicit None guard + structured logging ───────────────────
    test_cases = None

    if raw is None:
        logger.error(
            "test_agent: groq_generate_tests() returned None. "
            "Check that GROQ_API_KEY is set and the Groq API is reachable. "
            "Falling back to generic test cases — scores may be inaccurate."
        )
    else:
        try:
            start_idx = raw.find("[")
            end_idx   = raw.rfind("]")

            if start_idx == -1 or end_idx == -1:
                raise ValueError("No JSON array brackets found in LLM response.")

            block  = raw[start_idx : end_idx + 1]
            parsed = json.loads(block)

            # Validate: must be a list of exactly 5 dicts with required keys
            if not isinstance(parsed, list):
                raise ValueError(f"Expected a JSON list, got {type(parsed).__name__}.")
            if len(parsed) != 5:
                raise ValueError(f"Expected 5 test cases, got {len(parsed)}.")
            for i, tc in enumerate(parsed):
                if "input" not in tc or "expected" not in tc:
                    raise ValueError(f"Test case {i} missing 'input' or 'expected' key.")

            test_cases = parsed
            logger.info("test_agent: Successfully parsed 5 LLM-generated test cases.")

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(
                f"test_agent: Failed to parse LLM response — {e}\n"
                f"Raw LLM output was:\n{raw}\n"
                "Falling back to generic test cases — scores may be inaccurate."
            )

    # ── Fallback: only reached when LLM completely fails ──────────────────────
    if test_cases is None:
        logger.error(
            "test_agent: Using hardcoded fallback test cases. "
            "These are generic and unlikely to match the actual program. "
            "Resolve the LLM issue for meaningful grading."
        )
        test_cases = [
            {"input": "1\n",  "expected": "1"},
            {"input": "0\n",  "expected": "0"},
            {"input": "5\n",  "expected": "5"},
            {"input": "-1\n", "expected": "-1"},
            {"input": "10\n", "expected": "10"},
        ]

    # ── Execute each test case against the compiled binary ────────────────────
    passed  = 0
    results = []

    for idx, tc in enumerate(test_cases):
        # ── FIX 5: Normalize input — always end with newline ──────────────────
        raw_input = str(tc["input"])
        if not raw_input.endswith("\n"):
            raw_input += "\n"

        expected = str(tc["expected"]).strip()
        actual   = ""
        ok       = False

        try:
            proc = subprocess.run(
                [binary_path],
                input=raw_input.encode(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=TEST_TIMEOUT_SECONDS
            )
            actual = proc.stdout.decode(errors="replace").strip()
            ok     = (actual == expected)

        # ── FIX 6: Distinguish timeout from other runtime errors ──────────────
        except subprocess.TimeoutExpired:
            actual = f"Timeout (> {TEST_TIMEOUT_SECONDS}s)"
            logger.warning(f"test_agent: Test case {idx + 1} timed out.")

        except FileNotFoundError:
            actual = "Binary not found"
            logger.error(f"test_agent: Binary not found at path '{binary_path}'.")

        except Exception as e:
            actual = f"Runtime Error: {e}"
            logger.warning(f"test_agent: Test case {idx + 1} raised an exception — {e}")

        if ok:
            passed += 1

        results.append({
            "input":    raw_input,
            "expected": expected,
            "actual":   actual,
            "pass":     ok
        })

    score = round((passed / 5) * 30, 2)
    logger.info(f"test_agent: {passed}/5 test cases passed → score {score}/30")

    return {
        "score":  score,
        "report": f"{passed}/5 test cases passed.",
        "cases":  results
    }


# ─────────────────────────────────────────────────────────────
# PERFORMANCE AGENT  (15 pts)
# Measures actual runtime and analyses loop/branch complexity
# ─────────────────────────────────────────────────────────────
def performance_agent(source_path: str, binary_path: str) -> dict:
    """
    Times a single run of the binary and penalises slow programs
    or overly complex control-flow in the source.

    Returns:
        dict with keys: score (float), report (str)
    """
    # Measure runtime
    try:
        start   = time.time()
        subprocess.run(
            [binary_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=1
        )
        runtime = time.time() - start
    except subprocess.TimeoutExpired:
        runtime = 5.0
        logger.warning("performance_agent: Binary timed out during timing run.")
    except Exception as e:
        runtime = 5.0
        logger.warning(f"performance_agent: Error timing binary — {e}")

    # Analyse source complexity
    try:
        src = open(source_path).read()
    except OSError:
        src = ""

    loops    = len(re.findall(r"for\s*\(|while\s*\(", src))
    branches = len(re.findall(r"\bif\b|\bswitch\b|\bcase\b", src))

    score      = 15
    deductions = []

    if runtime > 0.7:
        score -= 3
        deductions.append(f"Slow runtime {runtime:.3f}s > 0.7s (-3)")
    if runtime > 1.2:
        score -= 3
        deductions.append(f"Very slow runtime {runtime:.3f}s > 1.2s (additional -3)")
    if loops > 5:
        score -= 2
        deductions.append(f"High loop count ({loops}) (-2)")
    if branches > 12:
        score -= 2
        deductions.append(f"High branch count ({branches}) (-2)")

    score  = max(score, 0)
    report = f"Runtime: {runtime:.3f}s | Loops: {loops} | Branches: {branches}"
    if deductions:
        report += "\nDeductions: " + "; ".join(deductions)

    return {"score": round(score, 2), "report": report}


# ─────────────────────────────────────────────────────────────
# OPTIMIZATION AGENT  (20 pts)
# Detects common C anti-patterns: memory leaks, I/O in loops
# ─────────────────────────────────────────────────────────────
def optimization_agent(source_path: str) -> dict:
    """
    Scans source code for common optimization red flags.

    Returns:
        dict with keys: score (int), report (str)
    """
    try:
        src = open(source_path).read()
    except OSError as e:
        logger.error(f"optimization_agent: cannot read source file — {e}")
        return {"score": 0, "report": "Source file could not be read."}

    score = 20
    notes = []

    if "malloc" in src and "free" not in src:
        score -= 4
        notes.append("Potential memory leak: malloc() used without free().")

    if re.search(r'for.*printf', src, re.S):
        score -= 3
        notes.append("printf() inside a loop detected — consider buffered output.")

    return {
        "score":  max(score, 0),
        "report": "\n".join(notes) if notes else "No major optimization issues detected."
    }
