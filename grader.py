# grader.py
"""
Agentic grader pipeline (no test-case generation).
Workflow:
1) Intent extraction / attempt recognition (llm_agent)
2) Compile code (compiler_runner)
3) If compile fails: interpret errors and award partial marks
4) If compile succeeds: structural/step-wise evaluation (llm_agent)
5) Optional micro-run (single run) if enabled (NOT for untrusted code)
6) Aggregate scores and produce text report
"""

import shutil
from llm_agent import analyze_intent, evaluate_structural_steps, interpret_compiler_errors, generate_feedback_text
from compiler_runner import compile_c_code, run_binary
from utils import code_hash
import json, os, shutil

# Rubric weights (sum 100)
RUBRIC = {
    "attempt": 10,         # attempt & intent recognition
    "structure": 30,       # structure: main, includes, IO, loops
    "algorithm": 40,       # algorithm steps correctness
    "style": 10,           # comments/readability
    "execution": 10        # micro-run success (optional)
}

def run_grader_pipeline(code_text: str, run_example: bool = False) -> dict:
    result = {}
    # 1) Intent & attempt
    intent = analyze_intent(code_text)
    result["intent"] = intent

    # rough attempt score calculation
    attempt_score = 0
    if "main" in code_text:
        attempt_score += 6
    if "#include" in code_text:
        attempt_score += 4
    attempt_score = min(attempt_score, RUBRIC["attempt"])
    result["attempt_score"] = attempt_score

    # 2) Compile
    comp = compile_c_code(code_text)
    result["compile"] = comp

    # interpret compile failure
    if comp.get("status") != "success":
        diag = interpret_compiler_errors(comp.get("stderr","") + comp.get("stdout",""))
        result["compiler_diagnostics"] = diag

        # structural analysis from LLM (still usable for partial marks)
        struct = evaluate_structural_steps(code_text)
        result["structural_analysis"] = struct

        # compute partial scores: structure * proportion of structure weight
        structure_score = struct.get("structural_score", 0) * (RUBRIC["structure"] / 100.0)
        algorithm_score = struct.get("structural_score", 0) * (RUBRIC["algorithm"] / 100.0) * 0.25  # lower when not compiled
        style_score = (10 if struct.get("has_comments") else 0) * (RUBRIC["style"] / 10.0)

        total = round(attempt_score + structure_score + algorithm_score + style_score, 2)
        result["scores"] = {
            "attempt": attempt_score,
            "structure": round(structure_score,2),
            "algorithm": round(algorithm_score,2),
            "style": round(style_score,2),
            "execution": 0,
            "total": total
        }
        result["final_score"] = total
        result["report"] = generate_feedback_text(result)
        result["raw_evaluation"] = json.dumps(result, indent=2)
        return result

    # 3) If compiled successfully -> structural evaluation
    struct = evaluate_structural_steps(code_text)
    result["structural_analysis"] = struct
    structure_score = struct.get("structural_score", 0) * (RUBRIC["structure"] / 100.0)
    algorithm_score = struct.get("structural_score", 0) * (RUBRIC["algorithm"] / 100.0)
    style_score = (10 if struct.get("has_comments") else 0) * (RUBRIC["style"] / 10.0)

    # 4) Optional micro-run (use with caution)
    execution_score = 0
    exec_detail = None
    if run_example and comp.get("binary"):
        # micro-run: run without input or a simple '1\\n' only if code expects scanf
        try:
            # heuristic: if scanf in code -> give a trivial input; else run once with no input
            sample_input = ""
            if "scanf" in code_text:
                sample_input = "1\n"
            res = run_binary(comp.get("binary"), input_data=sample_input, timeout=3)
            exec_detail = res
            if res.get("ok") and res.get("returncode", 0) == 0:
                execution_score = RUBRIC["execution"]
            else:
                execution_score = 0
        except Exception:
            execution_score = 0

    total = round(attempt_score + structure_score + algorithm_score + style_score + execution_score, 2)
    result["scores"] = {
        "attempt": attempt_score,
        "structure": round(structure_score,2),
        "algorithm": round(algorithm_score,2),
        "style": round(style_score,2),
        "execution": round(execution_score,2),
        "total": total
    }
    result["final_score"] = total
    result["execution"] = exec_detail
    result["report"] = generate_feedback_text(result)
    result["raw_evaluation"] = json.dumps(result, indent=2)

    # cleanup compiled artifact (temp dir inside compile info)
    try:
        td = comp.get("temp_dir")
        if td and os.path.exists(td):
            shutil.rmtree(td, ignore_errors=True)
    except Exception:
        pass

    return result
