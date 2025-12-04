# langgraph_agents.py
"""
Small langgraph-style agent classes:
- CompilerAgent
- TesterAgent
- JudgeAgent (Gemini reasoning evaluator)
- ReporterAgent (Gemini report generator)

JudgeAgent uses gemini_client.generate_text() to analyze the code, providing a reasoning rubric:
 - intent
 - does it logically solve the problem
 - syntax errors
 - key steps implemented
 - closeness score (0-100)
"""

import logging, json, re
from typing import List, Dict, Any
from compiler_runner import compile_c_code, run_binary
from gemini_client import generate_text as gemini_generate

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class Agent:
    def run(self, *args, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError()

class CompilerAgent(Agent):
    def __init__(self, timeout: int = 15):
        self.timeout = timeout
    def run(self, code_text: str) -> Dict[str, Any]:
        return {"role":"compiler", "result": compile_c_code(code_text, timeout=self.timeout)}

class TesterAgent(Agent):
    def __init__(self, timeout_per_test: int = 3):
        self.timeout_per_test = timeout_per_test
    def run(self, binary_path: str, tests: List[Dict[str,str]] = None) -> Dict[str, Any]:
        if not binary_path or not tests:
            # single liveness-run
            r = run_binary(binary_path, input_data="", timeout=self.timeout_per_test)
            return {"role":"tester", "result": {"single_run": r}}
        results=[]
        passed=0
        total=len(tests)
        for t in tests:
            inp = t.get("input","")
            exp = t.get("expected","").strip()
            r = run_binary(binary_path, input_data=inp, timeout=self.timeout_per_test)
            actual = r.get("stdout","").strip() if r.get("stdout") else ""
            success=False
            if exp:
                if actual == exp or actual.endswith(exp) or exp in actual:
                    success=True
            else:
                success = (r.get("returncode",1) == 0)
            results.append({"input":inp,"expected":exp,"actual":actual,"success":success,"meta":r})
            if success:
                passed += 1
        score = round((passed/total*100),2) if total else 0.0
        return {"role":"tester","result":{"results":results,"passed":passed,"total":total,"score":score}}

class JudgeAgent(Agent):
    """
    Uses Gemini to perform a reasoning rubric on the code and (optionally) testcases.
    Expects to receive code_text and optionally tests (list of dicts).
    Returns parsed JSON with fields:
      - intent: string
      - solves_problem: {"value": true/false, "explanation": "..."}
      - syntax_errors: [strings...]
      - key_steps: [{name, implemented: true/false, evidence}]
      - logic_score: integer 0-100
      - suggestions: [strings...]
    """
    def __init__(self, model_hint: str = "gemini-2.5-flash"):
        self.model_hint = model_hint

    def _build_prompt(self, code_text: str, tests: List[Dict[str,str]] = None) -> str:
        tests_text = ""
        if tests:
            for t in tests:
                tests_text += f"- {t.get('input','')} :: {t.get('expected','')}\n"
        prompt = f"""
You are an expert teaching assistant for C programming. Analyze the following C source code and the (optional) micro-tests.
Return ONLY a JSON object (no explanation) with these fields:
- intent: short label of the program's intent (e.g., "sum_two_numbers", "factorial", "sort", "string_count", "unknown")
- solves_problem: {{ "value": true/false, "explanation": "2-3 sentence reasoning" }}
- syntax_errors: [ list of compiler-like messages (if obvious), else empty list ]
- key_steps: a list of objects {{ "name": "<step name>", "implemented": true/false, "evidence": "<short text>" }}
    Example key steps names: "read_input", "validate_input", "compute_result", "print_output", "loop_over_elements"
- logic_score: integer in 0-100 estimating how close the logic is to a correct solution (0 = totally wrong, 100 = correct)
- suggestions: [ up to 5 short actionable suggestions for the student ]

Make sure the "key_steps" list covers common steps (input, compute, output, loops, edge-cases). Use the code to find evidence. If tests are provided, comment on their coverage via suggestions (but keep JSON shape constant).

Code: {code_text}
      
Tests:
{tests_text}

Return JSON only.
"""
        return prompt

    def run(self, code_text: str, tests: List[Dict[str,str]] = None) -> Dict[str, Any]:
        prompt = self._build_prompt(code_text, tests)
        raw = gemini_generate(prompt, temperature=0.0, max_output_tokens=1200)
        # try to extract JSON object from raw response
        try:
            m = re.search(r'\{.*\}', raw, flags=re.DOTALL)
            if m:
                parsed = json.loads(m.group(0))
                return {"role":"judge", "raw":raw, "parsed": parsed}
            # fallback: try direct json loads
            parsed = json.loads(raw)
            return {"role":"judge", "raw":raw, "parsed": parsed}
        except Exception as e:
            logger.exception("JudgeAgent: failed to parse Gemini response: %s", e)
            # return a conservative fallback using minimal analysis
            fallback = {
                "intent":"unknown",
                "solves_problem":{"value":False,"explanation":"Could not parse LLM response."},
                "syntax_errors":[],
                "key_steps":[],
                "logic_score": 0,
                "suggestions":["LLM parsing failed; check GEMINI setup."]
            }
            return {"role":"judge","raw":raw,"parsed":fallback}

class ReporterAgent(Agent):
    """
    Use Gemini to produce the final human-readable report.
    Input: evaluation dict (compile, structural, judge, test, final_score)
    Output: {"role":"reporter", "raw": "<text>"}
    """
    def __init__(self, model_hint: str = "gemini-2.5-flash"):
        self.model_hint = model_hint

    def _build_prompt(self, evaluation: Dict[str,Any]) -> str:
        import json
        compact = json.dumps(evaluation, indent=2, default=str)[:8000]
        prompt = f"""
You are a kind, concise teaching assistant. Given the following evaluation JSON, produce a short feedback report (3-6 short paragraphs) that:
 - Starts with a one-line summary (final score + high-level pass/fail).
 - Explains what the student did right.
 - Explains the main issues, with exact fixes for the top 3 problems.
 - Provides an action checklist (3 bullet items) the student should follow to improve and get full marks.
Return plain text (no JSON).
EVALUATION_JSON:
{compact}
"""
        return prompt

    def run(self, evaluation: Dict[str,Any]) -> Dict[str,Any]:
        prompt = self._build_prompt(evaluation)
        raw = gemini_generate(prompt, temperature=0.0, max_output_tokens=1200)
        return {"role":"reporter", "raw": raw}
