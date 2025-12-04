# langgraph_agents.py

import json, re
from compiler_runner import compile_c_code, run_binary
from gemini_client import generate_text
from llm_agent import evaluate_structural_steps


class Agent:
    def run(self, *args, **kwargs):
        raise NotImplementedError()


# ---------------- CompilerAgent ----------------
class CompilerAgent(Agent):
    def run(self, code_text: str):
        return {"role": "compiler", "result": compile_c_code(code_text)}


# ---------------- TesterAgent ----------------
class TesterAgent(Agent):
    def run(self, binary_path: str, tests=None):
        if not binary_path or not tests:
            return {"role": "tester", "result": {"note": "No tests executed"}}

        results = []
        passed = 0

        for t in tests:
            inp, exp = t["input"], t["expected"]
            run = run_binary(binary_path, inp)
            actual = run.get("stdout", "").strip()
            success = actual == exp or actual.endswith(exp)
            results.append({"input": inp, "expected": exp, "actual": actual, "success": success})
            if success: passed += 1

        score = round(passed / len(tests) * 100, 2) if tests else 0
        return {"role": "tester", "result": {"results": results, "score": score}}


# ---------------- JudgeAgent (Gemini Reasoning Rubric) ----------------
class JudgeAgent(Agent):
    def run(self, code_text: str, tests=None):
        prompt = f"""
Analyze the following C program and return ONLY a JSON with fields:

- intent: short label
- solves_problem: {{ "value": true/false, "explanation": "" }}
- syntax_errors: [list]
- key_steps: [{{"name":"", "implemented":true/false, "evidence":""}}]
- logic_score: integer 0-100
- suggested_tests: ["input::expected"]

Code: {code_text}

Tests:
{tests}
"""
        raw = generate_text(prompt)

        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            parsed = json.loads(match.group(0)) if match else json.loads(raw)
        except:
            parsed = {
                "intent": "unknown",
                "solves_problem": {"value": False, "explanation": "LLM parse failure"},
                "syntax_errors": [],
                "key_steps": [],
                "logic_score": 0,
                "suggested_tests": []
            }

        return {"role": "judge", "parsed": parsed, "raw": raw}


# ---------------- ReporterAgent (Gemini Final Report) ----------------
class ReporterAgent(Agent):
    def run(self, evaluation):
        import json
        compact = json.dumps(evaluation, indent=2)

        prompt = f"""
Given the following evaluation JSON, generate a clear 3-5 paragraph feedback report:

- One-line summary with final score
- What student did right
- Issues + how to fix them
- Action checklist (3 bullet points)

Return plain text only.

EVALUATION:
{compact}
"""
        return {"role": "reporter", "raw": generate_text(prompt)}

