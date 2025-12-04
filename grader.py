# grader.py
"""
Orchestrator using langgraph_agents. JudgeAgent (Gemini) inspects code using the reasoning rubric:
 - intent
 - logical correctness
 - syntax errors
 - key steps implemented
 - closeness to a correct solution

CompilerAgent compiles, TesterAgent optionally runs tests, ReporterAgent (Gemini) generates final report.
"""

from langgraph_agents import CompilerAgent, TesterAgent, JudgeAgent, ReporterAgent
from llm_agent import evaluate_structural_steps  # fallback structural analysis
import shutil, json

def run_grader_pipeline(code_text: str, tests: list = None, run_examples: bool = False) -> dict:
    # Create agents
    compiler = CompilerAgent()
    tester = TesterAgent()
    judge = JudgeAgent()
    reporter = ReporterAgent()

    evaluation = {}

    # 1) compile
    comp_out = compiler.run(code_text)
    compile_result = comp_out.get("result", {})
    evaluation["compile"] = compile_result

    # 2) structural analysis (simple deterministic heuristic as well)
    structural = evaluate_structural_steps(code_text)
    evaluation["structural_analysis"] = structural

    # 3) judge (Gemini) — evaluate code against the reasoning rubric
    judge_out = judge.run(code_text, tests or [])
    evaluation["judge"] = judge_out.get("parsed") if judge_out else {"note":"judge unavailable"}

    # 4) determine tests to run: use provided tests, else use judge suggestions if any
    suggested_tests = []
    if isinstance(judge_out, dict) and judge_out.get("parsed"):
        suggested = judge_out["parsed"].get("suggested_tests", [])
        for s in suggested:
            if isinstance(s, str) and "::" in s:
                inp, exp = s.split("::", 1)
                suggested_tests.append({"input": inp.strip(), "expected": exp.strip()})
    final_tests = tests or suggested_tests

    # 5) run tests if compiled and tests exist, or if run_examples True (single liveness run)
    test_out = None
    if compile_result.get("status") == "success" and final_tests:
        test_out = tester.run(compile_result.get("binary"), final_tests)
        evaluation["test"] = test_out
    elif compile_result.get("status") == "success" and run_examples:
        test_out = tester.run(compile_result.get("binary"), tests=None)
        evaluation["test"] = test_out
    else:
        evaluation["test"] = {"note":"No tests executed"}

    # 6) scoring aggregation (weights can be tuned)
    compile_ok = 1 if compile_result.get("status") == "success" else 0
    structure_score = structural.get("structural_score", 0) / 100.0
    test_score = 0.0
    if test_out and test_out.get("result"):
        test_score = (test_out["result"].get("score",0) / 100.0) if isinstance(test_out["result"].get("score",0),(int,float)) else 0.0

    # Weigh judge LLM's logic_score if present
    judge_logic = 0.0
    if evaluation.get("judge") and isinstance(evaluation["judge"], dict):
        judge_logic = (evaluation["judge"].get("logic_score", 0) or 0) / 100.0

    # combine: 20% compile, 35% structure, 25% judge_logic, 20% tests
    final_score = round((0.2 * compile_ok + 0.35 * structure_score + 0.25 * judge_logic + 0.20 * test_score) * 100, 2)
    evaluation["final_score"] = final_score

    # 7) reporter LLM: produce final textual report
    reporter_out = reporter.run(evaluation)
    evaluation["report"] = reporter_out.get("raw", "(no report)")

    # Cleanup temporary binary directory if present
    try:
        tmp = compile_result.get("temp_dir")
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    except Exception:
        pass

    return evaluation
