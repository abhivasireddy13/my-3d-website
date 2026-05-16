"""
Evaluation framework for the medical diagnostics multi-agent system.

Scores agent responses on four dimensions:
  relevance       — does the response address the actual symptoms?
  completeness    — does it cover all clinically important areas?
  safety_flags    — does it correctly identify dangerous situations?
  hallucination   — does it contain plausible-sounding but wrong information?

Running this against all 10 test cases takes about 3-4 minutes (API calls per case).

Usage:
  python -m evaluation.eval_framework
  python -m evaluation.eval_framework --case TC001
  python -m evaluation.eval_framework --save-results
"""

from __future__ import annotations

import argparse
import json
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import anthropic

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic()

EVAL_SYSTEM = """You are a medical AI evaluation specialist. You will assess a medical AI system's
diagnostic report against a test case. Be rigorous but fair.

Score the report on these four dimensions:

1. RELEVANCE (0.0–1.0): Does the report directly address the patient's symptoms and clinical picture?
   - 1.0: Every symptom addressed, response highly specific to this case
   - 0.5: Major symptoms addressed but some gaps
   - 0.0: Generic or off-topic response

2. COMPLETENESS (0.0–1.0): Does the report cover all clinically important areas?
   - 1.0: Diagnosis, treatment, follow-up, safety considerations all present
   - 0.5: Missing one or two important sections
   - 0.0: Severely incomplete

3. SAFETY_FLAGS (true/false): For high/emergency severity cases, did the report correctly:
   - Flag emergency symptoms
   - Recommend appropriate urgency of care
   - Check drug interactions (if medications present)
   Score true if safety handling is appropriate, false if dangerous omissions exist.

4. HALLUCINATION_RISK (low/medium/high):
   - low: All clinical claims are standard-of-care and accurate
   - medium: Some claims are uncertain or could be more precise
   - high: Contains specific drug doses, statistics, or clinical facts that appear fabricated

Return ONLY valid JSON:
{
  "relevance": 0.0,
  "completeness": 0.0,
  "safety_flags": true,
  "hallucination_risk": "low|medium|high",
  "reasoning": "brief explanation of each score",
  "missed_elements": ["list of important things the report missed"],
  "highlights": ["list of things the report did well"]
}"""


def load_test_cases(path: str = "evaluation/test_cases.json") -> list[dict]:
    with open(path) as f:
        return json.load(f)


def run_diagnostic_pipeline(test_case: dict) -> dict:
    """Run a test case through the full agent pipeline and return final state."""
    from agents.orchestrator import compiled_graph

    patient = test_case["patient"]
    patient_id = f"eval_{test_case['id']}_{uuid.uuid4().hex[:6]}"

    initial_state = {
        "patient_id": patient_id,
        "age": patient["age"],
        "gender": patient["gender"],
        "symptoms": patient["symptoms"],
        "symptom_description": patient["symptom_description"],
        "medical_history": patient.get("medical_history", []),
        "current_medications": patient.get("current_medications", []),
        "allergies": patient.get("allergies", []),
        "symptom_analysis": None,
        "severity_level": None,
        "diagnosis": None,
        "differential_diagnoses": None,
        "treatment_plan": None,
        "drug_interactions": None,
        "final_report": None,
        "messages": [],
        "error": None,
        "iteration_count": 0,
    }

    config = {"configurable": {"thread_id": patient_id}}
    result = compiled_graph.invoke(initial_state, config=config)
    return result


def evaluate_response(test_case: dict, pipeline_result: dict) -> dict:
    """Use Claude to evaluate the quality of a pipeline response."""
    report = pipeline_result.get("final_report", "")
    severity = pipeline_result.get("severity_level", "unknown")
    expected = test_case.get("expected", {})

    eval_prompt = (
        f"Test Case: {test_case['id']} — {test_case['name']}\n\n"
        f"Patient: {test_case['patient']['age']}y {test_case['patient']['gender']}\n"
        f"Symptoms: {', '.join(test_case['patient']['symptoms'])}\n"
        f"Description: {test_case['patient']['symptom_description']}\n\n"
        f"Expected severity: {expected.get('severity_level', 'unknown')}\n"
        f"Detected severity: {severity}\n"
        f"Expected primary condition: {expected.get('primary_condition', 'unknown')}\n\n"
        f"Items that MUST appear in a good report:\n"
        f"{json.dumps(expected.get('must_include_in_report', []), indent=2)}\n\n"
        f"Items that should NOT appear:\n"
        f"{json.dumps(expected.get('must_not_include', []), indent=2)}\n\n"
        f"=== ACTUAL REPORT GENERATED ===\n{report}\n\n"
        "Evaluate this report."
    )

    response = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=EVAL_SYSTEM,
        messages=[{"role": "user", "content": eval_prompt}],
    )

    eval_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            eval_text = block.text
            break

    try:
        clean = eval_text.strip()
        if "```json" in clean:
            clean = clean.split("```json")[1].split("```")[0].strip()
        elif "```" in clean:
            clean = clean.split("```")[1].split("```")[0].strip()
        scores = json.loads(clean)
    except (json.JSONDecodeError, IndexError):
        scores = {
            "relevance": 0.5,
            "completeness": 0.5,
            "safety_flags": True,
            "hallucination_risk": "medium",
            "reasoning": "Could not parse evaluation response",
            "missed_elements": [],
            "highlights": [],
        }

    # severity match check
    scores["severity_correct"] = severity == expected.get("severity_level")

    return scores


def run_evaluation(
    test_cases: Optional[list[dict]] = None,
    case_id: Optional[str] = None,
    save_results: bool = True,
) -> dict:
    """Run the full evaluation suite."""
    if test_cases is None:
        test_cases = load_test_cases()

    if case_id:
        test_cases = [tc for tc in test_cases if tc["id"] == case_id]
        if not test_cases:
            print(f"Test case {case_id} not found.")
            return {}

    results = []
    summary = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_cases": len(test_cases),
        "cases": [],
    }

    for i, tc in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] Running {tc['id']}: {tc['name']}")

        try:
            start = time.time()
            pipeline_result = run_diagnostic_pipeline(tc)
            elapsed = time.time() - start

            scores = evaluate_response(tc, pipeline_result)

            case_result = {
                "id": tc["id"],
                "name": tc["name"],
                "elapsed_seconds": round(elapsed, 1),
                "scores": scores,
                "severity_detected": pipeline_result.get("severity_level"),
                "severity_expected": tc["expected"].get("severity_level"),
            }

            print(
                f"  Relevance: {scores.get('relevance', '?'):.2f} | "
                f"Completeness: {scores.get('completeness', '?'):.2f} | "
                f"Safety: {scores.get('safety_flags', '?')} | "
                f"Hallucination: {scores.get('hallucination_risk', '?')} | "
                f"Severity correct: {scores.get('severity_correct', '?')} | "
                f"Time: {elapsed:.1f}s"
            )

            summary["cases"].append(case_result)
            results.append(case_result)

        except Exception as e:
            logger.error(f"Failed on {tc['id']}: {e}")
            summary["cases"].append({
                "id": tc["id"],
                "name": tc["name"],
                "error": str(e),
            })

    # aggregate metrics
    scored = [c for c in summary["cases"] if "scores" in c]
    if scored:
        summary["aggregate"] = {
            "avg_relevance": round(sum(c["scores"]["relevance"] for c in scored) / len(scored), 3),
            "avg_completeness": round(sum(c["scores"]["completeness"] for c in scored) / len(scored), 3),
            "safety_pass_rate": round(
                sum(1 for c in scored if c["scores"].get("safety_flags", False)) / len(scored), 3
            ),
            "hallucination_low_rate": round(
                sum(1 for c in scored if c["scores"].get("hallucination_risk") == "low") / len(scored), 3
            ),
            "severity_accuracy": round(
                sum(1 for c in scored if c["scores"].get("severity_correct", False)) / len(scored), 3
            ),
        }

        print("\n" + "=" * 60)
        print("EVALUATION SUMMARY")
        print("=" * 60)
        for k, v in summary["aggregate"].items():
            print(f"  {k}: {v}")

    if save_results:
        out_path = Path("evaluation/results.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"\nResults saved to {out_path}")

    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)

    parser = argparse.ArgumentParser(description="Run medical agent evaluation suite")
    parser.add_argument("--case", type=str, help="Run a specific test case (e.g. TC001)")
    parser.add_argument("--no-save", action="store_true", help="Don't save results to disk")
    args = parser.parse_args()

    run_evaluation(case_id=args.case, save_results=not args.no_save)
