"""
agents.py
Multi-Agent Grading System — Professional C Autograder

Agents:
  - design_agent       → Code structure & quality            (15 pts)
  - test_agent         → Self-Oracle functional testing      (30 pts)
  - performance_agent  → Runtime & complexity analysis       (15 pts)
  - optimization_agent → Memory & I/O best-practice checks  (20 pts)

Self-Oracle Strategy (test_agent):
  The LLM is only asked to generate INPUTS (a much simpler, reliable task).
  The compiled binary itself is run on each input to produce the expected
  output — making the program its own ground truth oracle.
  A second independent run then confirms the output is reproducible and
  non-empty before the test case is counted as passed.

  This eliminates the core failure mode of the old approach where the LLM
  had to guess what the program would print — which it almost always got
  wrong for anything beyond trivial echo programs.
"""

import re
import json
import logging
import subprocess
import time

from config import TEST_TIMEOUT_SECONDS
from llm import groq_generate_inputs          # NEW: input-only generator

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPER — parse the list of raw input strings from the LLM response
# ─────────────────────────────────────────────────────────────────────────────
def _parse_input_list(raw: str) -> list[str] | None:
    """
    Extracts a JSON array of strings from the raw LLM response.
    Returns a list of exactly 5 strings, or None on any failure.
    """
    if raw is None:
        logger.error("_parse_input_list: received None from LLM call.")
        return None

    try:
        start = raw.find("[")
        end   = raw.rfind("]")
        if start == -1 or end == -1:
            raise ValueError("No JSON array brackets found.")

        parsed = json.loads(raw[start : end + 1])

        if not isinstance(parsed, list):
            raise ValueError(f"Expected a list, got {type(parsed).__name__}.")
        if len(parsed) != 5:
            raise ValueError(f"Expected 5 inputs, got {len(parsed)}.")
        if not all(isinstance(i, str) for i in parsed):
            raise ValueError("All items must be strings.")

        return parsed

    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(
            f"_parse_input_list: parse failed — {e}\n"
            f"Raw LLM output was:\n{raw}"
        )
        return None


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPER — run the binary once with a given stdin input
# Returns (stdout_str, error_str | None)
# ─────────────────────────────────────────────────────────────────────────────
def _run_binary(binary_path: str, stdin_input: str) -> tuple[str, str | None]:
    """
    Executes the binary with stdin_input, returns (stdout.strip(), error_label).
    error_label is None on success, or a short string describing the failure.
    """
    try:
        proc = subprocess.run(
            [binary_path],
            input=stdin_input.encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=TEST_TIMEOUT_SECONDS
        )
        return proc.stdout.decode(errors="replace").strip(), None

    except subprocess.TimeoutExpired:
        return "", f"Timeout (> {TEST_TIMEOUT_SECONDS}s)"
    except FileNotFoundError:
        return "", "Binary not found"
    except Exception as e:
        return "", f"Runtime Error: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# DESIGN AGENT  (15 pts)
# ─────────────────────────────────────────────────────────────────────────────
def design_agent(source_path: str) -> dict:
    """
    Scores the submitted C source on design / readability criteria.
    Returns: { score: int, report: str }
    """
    try:
        src = open(source_path).read()
    except OSError as e:
        logger.error(f"design_agent: cannot read source — {e}")
        return {"score": 0, "report": "Source file could not be read."}

    lines    = src.splitlines()
    funcs    = re.findall(r'\w+\s+\**\w+\s*\([^)]*\)\s*\{', src)
    comments = src.count("//") + src.count("/*")

    score      = 15
    deductions = []

    if len(lines) > 200:
        score -= 2
        deductions.append("Exceeds 200 lines (-2)")
    if len(funcs) < 2:
        score -= 3
        deductions.append("Fewer than 2 functions (-3)")
    if comments < 3:
        score -= 2
        deductions.append("Insufficient comments (-2)")

    report = f"Lines: {len(lines)} | Functions: {len(funcs)} | Comments: {comments}"
    if deductions:
        report += "\nDeductions: " + "; ".join(deductions)

    return {"score": max(score, 0), "report": report}


# ─────────────────────────────────────────────────────────────────────────────
# TEST AGENT  (30 pts)  ★ Self-Oracle Implementation ★
# ─────────────────────────────────────────────────────────────────────────────
def test_agent(title: str, source_path: str, binary_path: str) -> dict:
    """
    Self-Oracle testing strategy:

      1. Read the C source so the LLM has full context of the program's logic.
      2. Ask Groq LLM to generate ONLY 5 stdin input strings — not expected
         outputs. This is a far simpler task that small models handle well.
      3. Run the compiled binary on each input → this output becomes the
         ground-truth 'expected' value (the program is its own oracle).
      4. Run the binary a second time on the same input → 'actual' output.
      5. Pass if: both runs agree AND the output is non-empty.
         This catches non-deterministic programs (random, uninitialized vars).

    Returns: { score: float, report: str, cases: list[dict] }
    """

    # ── Step 1: Read source for LLM context ──────────────────────────────────
    try:
        src = open(source_path).read()
    except OSError as e:
        logger.warning(f"test_agent: cannot read source ({e}); LLM will have no code context.")
        src = "(source code unavailable)"

    # ── Step 2: Ask LLM to generate INPUTS ONLY ──────────────────────────────
    prompt = f"""
You are a C programming test engineer. Read the C source code below carefully.

Your task: generate EXACTLY 5 stdin input strings to thoroughly test this program.

Program Title: {title}

Source Code:
```c
{src}
```

Rules:
- Each input must be exactly what the program expects on stdin.
- Include newline characters (\\n) wherever the program calls scanf or fgets.
- Cover: a typical case, a boundary value (0, empty, max), a negative number
  (if applicable), a large value, and one unexpected/edge input.
- Return ONLY a valid JSON array of 5 strings. No explanation, no markdown.

Example format (for a program that reads one integer):
["3\\n", "0\\n", "-1\\n", "1000\\n", "42\\n"]
"""

    raw     = groq_generate_inputs(prompt)
    inputs  = _parse_input_list(raw)

    # ── Fallback: used ONLY when LLM/parse completely fails ──────────────────
    if inputs is None:
        logger.error(
            "test_agent: LLM input generation failed. "
            "Using hardcoded generic inputs — coverage will be limited. "
            "Fix GROQ_API_KEY or LLM connectivity for accurate grading."
        )
        inputs = ["1\n", "0\n", "5\n", "-1\n", "10\n"]

    logger.info(f"test_agent: Running self-oracle tests with inputs: {inputs}")

    # ── Steps 3–5: Oracle run → confirm run → compare ────────────────────────
    passed  = 0
    results = []

    for idx, raw_input in enumerate(inputs):

        # Normalise: always end with newline for subprocess stdin
        if not raw_input.endswith("\n"):
            raw_input += "\n"

        # Build a human-readable version of the input for display:
        #   - Keep literal \n characters visible as the text "↵" so multi-line
        #     inputs like "Alice\n25\n" are shown as "Alice↵ 25↵" in the UI
        #     instead of being collapsed or stripped to a blank line.
        #   - The raw_input itself is always passed to the binary unchanged.
        display_input = raw_input.replace("\n", " ↵\n").rstrip()

        # ── Oracle run: program defines the expected output ───────────────────
        expected, oracle_err = _run_binary(binary_path, raw_input)

        if oracle_err:
            logger.warning(
                f"test_agent: Oracle run {idx + 1} failed ({oracle_err}). "
                "Marking as not-passed."
            )
            results.append({
                "input":         display_input,
                "input_raw":     raw_input,
                "expected":      f"[Oracle Error: {oracle_err}]",
                "actual":        oracle_err,
                "pass":          False
            })
            continue

        if not expected:
            logger.warning(
                f"test_agent: Oracle run {idx + 1} produced empty output. "
                "Skipping — cannot use empty string as ground truth."
            )
            results.append({
                "input":         display_input,
                "input_raw":     raw_input,
                "expected":      "[Empty — no output produced]",
                "actual":        "",
                "pass":          False
            })
            continue

        # ── Confirm run: independently verify reproducibility ─────────────────
        actual, confirm_err = _run_binary(binary_path, raw_input)

        if confirm_err:
            ok     = False
            actual = confirm_err
            logger.warning(f"test_agent: Confirm run {idx + 1} failed ({confirm_err}).")
        else:
            ok = (actual == expected)

        if ok:
            passed += 1
        else:
            logger.info(
                f"test_agent: Test {idx + 1} MISMATCH — "
                f"oracle='{expected}' confirm='{actual}'"
            )

        results.append({
            "input":         display_input,   # human-readable with ↵ markers
            "input_raw":     raw_input,        # exact bytes sent to binary
            "expected":      expected,
            "actual":        actual,
            "pass":          ok
        })

    score = round((passed / 5) * 30, 2)
    logger.info(f"test_agent: {passed}/5 passed → {score}/30")

    return {
        "score":  score,
        "report": f"{passed}/5 test cases passed (Self-Oracle mode).",
        "cases":  results
    }


# ─────────────────────────────────────────────────────────────────────────────
# PERFORMANCE AGENT  (15 pts)
# ─────────────────────────────────────────────────────────────────────────────
def performance_agent(source_path: str, binary_path: str) -> dict:
    """
    Times a single run of the binary and penalises slow programs
    or overly complex control-flow in the source.
    Returns: { score: float, report: str }
    """
    try:
        start = time.time()
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
        deductions.append(f"Very slow {runtime:.3f}s > 1.2s (additional -3)")
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


# ─────────────────────────────────────────────────────────────────────────────
# OPTIMIZATION AGENT  (20 pts)
# ─────────────────────────────────────────────────────────────────────────────
def optimization_agent(source_path: str) -> dict:
    """
    Scans source code for common C optimization red-flags.
    Returns: { score: int, report: str }
    """
    try:
        src = open(source_path).read()
    except OSError as e:
        logger.error(f"optimization_agent: cannot read source — {e}")
        return {"score": 0, "report": "Source file could not be read."}

    score = 20
    notes = []

    if "malloc" in src and "free" not in src:
        score -= 4
        notes.append("Potential memory leak: malloc() used without free().")

    if re.search(r'for.*printf', src, re.S):
        score -= 3
        notes.append("printf() inside a loop — consider buffered output.")

    return {
        "score":  max(score, 0),
        "report": "\n".join(notes) if notes else "No major optimization issues detected."
    }
