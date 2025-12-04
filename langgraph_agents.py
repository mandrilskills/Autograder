# langgraph_agents.py
"""
Simple langgraph-style agents. JudgeAgent and ReporterAgent delegate to Gemini via gemini_client.generate_text.
"""

import json
from typing import List, Dict, Any
from compiler_runner import compile_c_code, run_binary
from gemini_client import generate_text
from llm_agent import evaluate_structural_steps, interpret_compiler_errors


class Agent:
    def run(self, *args, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError()


class CompilerAgent(Agent):
    def run(self, code_text: str) -> Dict[str, Any]:
        return {"role": "compiler", "result": compile_c_code(code_text)}


class TesterAgent(Agent):
    def run(self, binary_path: str, tests: List[Dict[str, str]] = None) -> Dict[str, Any]:
        if not binary_path:
            return {"role": "tester", "result": {"note": "binary missing"}}
        if not tests:
            # single liveness run (no input)
            r = run_binary(binary_path, input_data="", timeout=3)
            return {"role": "tester", "result": {"single_run": r}}
        results = []
        passed = 0
        for t in tests:
            inp = t.get("input", "")
            exp = t.get("expected", "").strip()
            r = run_binary(binary_path, input_data=inp, timeout=3)
            actual = r.get("stdout", "").strip() if r.get("stdout") else ""
            success = False
            if exp:
                success = (actual == exp) or actual.endswith(exp) or (exp in actual)
            else:
                success = (r.get("returncode", 1) == 0)
            results.append({"input": inp, "expected": exp, "actual": actual, "success": success})
            if success:
                passed += 1
        score = round((passed / len(tests) * 100), 2) if tests else 0.0
        return {"role": "tester", "result": {"results": results, "passed": passed, "total": len(tests), "score": score}}


class JudgeAgent(Agent):
    """
    Uses Gemini to analyze code according to the reasoning rubric.
    Prompt asks Gemini to output ONLY JSON; this code tries to parse the first JSON object in the reply.
    """

    def run(self, code_text: str, tests: List[Dict[str, str]] = None) -> Dict[str, Any]:
        tests_text = ""
        if tests:
            for t in tests:
                tests_text += f"- {t.get('input','')} :: {t.get('expected','')}\n"
        prompt = f"""
You are an expert teaching assistant for C programs. Analyze the following C program and optional micro-tests.
Return ONLY a JSON object with fields:

- intent: short label (e.g., "sum_two_numbers", "factorial", "sort", "unknown")
- solves_problem: {{ "value": true/false, "explanation": "2-3 sentence reasoning" }}
- syntax_errors: [list of short messages if recognizable]
- key_steps: [ {{ "name": "<step>", "implemented": true/false, "evidence": "<short>" }}, ... ]
- logic_score: integer 0-100
- suggested_tests: ["input::expected", ...]

Code:
{code_text}


Tests:
{tests_text}

Return JSON only.
"""
        raw = generate_text(prompt, temperature=0.0, max_output_tokens=1200)
        parsed = None
        try:
            # try to find first JSON object in raw reply
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1 and end > start:
                blob = raw[start:end+1]
                parsed = json.loads(blob)
        except Exception:
            parsed = None

        if not parsed:
            # fallback conservative parsed structure
            parsed = {
                "intent": "unknown",
                "solves_problem": {"value": False, "explanation": "Could not parse LLM output."},
                "syntax_errors": [],
                "key_steps": [],
                "logic_score": 0,
                "suggested_tests": []
            }
        return {"role": "judge", "raw": raw, "parsed": parsed}


class ReporterAgent(Agent):
    def run(self, evaluation: Dict[str, Any]) -> Dict[str, Any]:
        import json
        compact = json.dumps(evaluation, indent=2, default=str)[:8000]
        prompt = f"""
You are a pedagogical teaching assistant. Given the following evaluation JSON, produce a clear feedback report:
- One-line summary with final score
- Short paragraph: what's correct
- Short paragraph: main issues and exact fixes
- Actionable checklist (3 bullets)

Return plain text only.

EVALUATION:
{compact}
"""
        raw = generate_text(prompt, temperature=0.0, max_output_tokens=1200)
        return {"role": "reporter", "raw": raw}
