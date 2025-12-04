# grader.py

from langgraph_agents import CompilerAgent, TesterAgent, JudgeAgent, ReporterAgent
from llm_agent import evaluate_structural_steps
import shutil

def run_grader_pipeline(code_text: str, tests=None, run_examples=False):

    compiler = CompilerAgent()
    tester = TesterAgent()
    judge = JudgeAgent()
    reporter = ReporterAgent()

    evaluation = {}

    # 1) Compile
    comp = compiler.run(code_text)
    evaluation["compile"] = comp["result"]

    # 2) Structural
    structural = evaluate_structural_steps(code_text)
    evaluation["structural_analysis"] = structural

    # 3) Judge LLM reasoning
    judge_out = judge.run(code_text, tests)
    evaluation["judge"] = judge_out["parsed"]

    # Prepare tests (user provided OR LLM-suggested)
    suggested = []
    if "suggested_tests" in judge_out["parsed"]:
        for s in judge_out["parsed"]["suggested_tests"]:
            if "::" in s:
                inp, exp = s.split("::", 1)
                suggested.append({"input": inp.strip(), "expected": exp.strip()})

    final_tests = tests or suggested

    # 4) Test execution
    if evaluation["compile"]["status"] == "success" and final_tests:
        evaluation["test"] = tester.run(evaluation["compile"]["binary"], final_tests)
    else:
        evaluation["test"] = {"note": "No tests run"}

    # 5) Score
    score_compile = 1 if evaluation["compile"]["status"] == "success" else 0
    score_structure = structural["structural_score"] / 100
    score_logic = evaluation["judge"].get("logic_score", 0) / 100
    score_tests = evaluation["test"].get("result", {}).get("score", 0) / 100

    final_score = (
        0.2 * score_compile +
        0.35 * score_structure +
        0.25 * score_logic +
        0.20 * score_tests
    ) * 100

    evaluation["final_score"] = round(final_score, 2)

    # 6) Final Report
    evaluation["report"] = reporter.run(evaluation)["raw"]

    # Cleanup
    try:
        shutil.rmtree(evaluation["compile"]["temp_dir"], ignore_errors=True)
    except:
        pass

    return evaluation
