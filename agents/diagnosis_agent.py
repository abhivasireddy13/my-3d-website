"""
Diagnosis agent — second node in the pipeline.

Receives symptom analysis output and generates:
  - Primary diagnosis (most likely)
  - Differential diagnoses (ordered by likelihood)
  - Reasoning chain and supporting evidence

I considered merging symptom_analyzer and diagnosis_agent into one node, but
keeping them separate means you can re-run diagnosis with different models
without re-running the expensive symptom search. Also cleaner for logging.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import anthropic

from tools.medical_search import search_medical_info

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are a senior internal medicine physician with expertise in differential diagnosis.

You will receive a structured symptom analysis from a specialist and must produce:
1. A primary diagnosis (most likely condition given available data)
2. An ordered differential diagnosis list (up to 5 conditions, most to least likely)
3. Clinical reasoning — what pattern of symptoms led to each diagnosis
4. What additional tests/information would change the diagnosis

Be appropriately uncertain. If data is insufficient, say so explicitly rather than guessing.

Output valid JSON with these exact keys:
{
  "primary_diagnosis": "condition name",
  "confidence": "low|medium|high",
  "differential_diagnoses": [
    {"condition": "name", "likelihood": "percentage or qualitative", "reasoning": "brief"},
    ...
  ],
  "clinical_reasoning": "detailed narrative of diagnostic logic",
  "recommended_tests": ["test1", "test2"],
  "red_herrings": ["symptoms that might mislead", "if any"],
  "icd10_codes": ["approximate ICD-10 codes for primary + top differentials"]
}"""

_TOOLS = [
    {
        "name": "search_medical_info",
        "description": "Search clinical guidelines or medical literature to support diagnosis.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Clinical query, e.g. 'diagnostic criteria for community acquired pneumonia'",
                }
            },
            "required": ["query"],
        },
    }
]


class DiagnosisAgent:

    def run(self, state: dict) -> dict:
        symptom_analysis = state.get("symptom_analysis", "")
        severity = state.get("severity_level", "medium")
        age = state.get("age", "unknown")
        gender = state.get("gender", "unknown")
        history = state.get("medical_history", [])
        meds = state.get("current_medications", [])
        allergies = state.get("allergies", [])

        user_message = (
            f"Patient Demographics: {age}-year-old {gender}\n"
            f"Medical History: {', '.join(history) if history else 'none'}\n"
            f"Current Medications: {', '.join(meds) if meds else 'none'}\n"
            f"Allergies: {', '.join(allergies) if allergies else 'none reported'}\n"
            f"Pre-assessed Severity: {severity}\n\n"
            f"Symptom Analysis from Specialist:\n{symptom_analysis}\n\n"
            "Generate a differential diagnosis with clinical reasoning."
        )

        messages: list[dict] = [{"role": "user", "content": user_message}]
        final_response = None

        for _ in range(5):
            response = _client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=3000,
                system=SYSTEM_PROMPT,
                tools=_TOOLS,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                final_response = response
                break

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use" and block.name == "search_medical_info":
                        logger.info(f"DiagnosisAgent searching: {block.input['query']}")
                        result = search_medical_info(block.input["query"])
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
            else:
                final_response = response
                break

        if final_response is None:
            final_response = response

        diagnosis_text = _extract_text(final_response)
        differentials = _extract_differentials(diagnosis_text)

        return {
            "diagnosis": diagnosis_text,
            "differential_diagnoses": differentials,
            "messages": [{"role": "diagnosis_agent", "content": diagnosis_text}],
        }


def _extract_text(response: Any) -> str:
    for block in response.content:
        if hasattr(block, "text"):
            return block.text
    return ""


def _extract_differentials(text: str) -> list[str]:
    try:
        clean = text.strip()
        if "```json" in clean:
            clean = clean.split("```json")[1].split("```")[0].strip()
        elif "```" in clean:
            clean = clean.split("```")[1].split("```")[0].strip()

        parsed = json.loads(clean)
        diffs = parsed.get("differential_diagnoses", [])
        return [d.get("condition", "") for d in diffs if isinstance(d, dict)]
    except Exception:
        return []
