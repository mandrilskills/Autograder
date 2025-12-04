# grader.py
from langgraph_agents import CompilerAgent, TesterAgent, JudgeAgent, ReporterAgent
from llm_agent import evaluate_structural_steps, interpret_compiler_errors
import shutil

def run_grader_pipeline(code_text: str, tests: list = None, run_examples: bool = False) -> dict:
    compiler = CompilerAgent()
    tester = TesterAgent()
    judge = JudgeAgent()
    reporter = ReporterAgent()

    evaluation = {}

    # 1) Compile
    comp_out = compiler.run(code_text)
    compile_result = comp_out.get("result", {})
    evaluation["compile"] = compile_result

    # 2) Structural heuristic analysis
    structural = evaluate_structural_steps(code_text)
    evaluation["structural_analysis"] = structural

    # If compilation failed, add compiler diagnostics (heuristic)
    if compile_result.get("status") != "success":
        evaluation["compiler_diagnostics"] = interpret_compiler_errors(compile_result.get("stderr", ""))

    # 3) Judge LLM reasoning (Gemini)
    judge_out = judge.run(code_text, tests or [])
    evaluation["judge"] = judge_out.get("parsed", {})

    # 4) Determine tests: use provided tests else judge suggested_tests
    suggested_tests = []
    for s in evaluation["judge"].get("suggested_tests", []):
        if isinstance(s, str) and "::" in s:
            inp, exp = s.split("::", 1)
            suggested_tests.append({"input": inp.strip(), "expected": exp.strip()})

    final_tests = tests or suggested_tests

    # 5) Run tests if compiled successfully
    if compile_result.get("status") == "success" and final_tests:
        evaluation["test"] = tester.run(compile_result.get("binary"), final_tests)
    elif compile_result.get("status") == "success" and run_examples:
        evaluation["test"] = tester.run(compile_result.get("binary"), tests=None)
    else:
        evaluation["test"] = {"note": "No tests executed"}

    # 6) Score aggregation using weights
    compile_ok = 1 if compile_result.get("status") == "success" else 0
    structure_score = structural.get("structural_score", 0) / 100.0
    logic_score = (evaluation["judge"].get("logic_score", 0) or 0) / 100.0
    test_score = 0.0
    if evaluation["test"] and isinstance(evaluation["test"].get("result"), dict):
        test_score = (evaluation["test"]["result"].get("score", 0) or 0) / 100.0

    final_score = round((0.2 * compile_ok + 0.35 * structure_score + 0.25 * logic_score + 0.20 * test_score) * 100, 2)
    evaluation["final_score"] = final_score

    # 7) Reporter LLM generates final human-readable report
    reporter_out = reporter.run(evaluation)
    evaluation["report"] = reporter_out.get("raw", "(no report)")

    # 8) cleanup compiled temp dir
    try:
        if compile_result.get("temp_dir"):
            shutil.rmtree(compile_result.get("temp_dir"), ignore_errors=True)
    except Exception:
        pass

    return evaluation
