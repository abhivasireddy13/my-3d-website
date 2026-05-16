"""
Treatment planning agent — third node in the pipeline.

Takes diagnosis output and generates:
  - Treatment recommendations (pharmacological + non-pharmacological)
  - Drug interaction check against current medications
  - Dosage considerations based on patient demographics
  - Follow-up plan

The drug interaction check is the most important part here.
Getting a treatment recommendation that conflicts with existing meds is dangerous,
so this node calls drug_checker before finalizing anything.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import anthropic

from tools.calculator import calculate_dosage
from tools.drug_checker import check_drug_interactions
from tools.medical_search import search_medical_info

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are a clinical pharmacist and internal medicine specialist.

Given a diagnosis and patient profile, produce a comprehensive treatment plan:
1. First-line treatment recommendations
2. Alternative treatments if first-line is contraindicated
3. Non-pharmacological interventions (lifestyle, diet, physical)
4. Monitoring parameters (what to watch for)
5. Follow-up timeline
6. Patient education points

CRITICAL: If the patient has current medications, you MUST check for drug interactions
before recommending any new medications.

Output valid JSON:
{
  "primary_treatment": {
    "medications": [{"name": "", "dose": "", "frequency": "", "duration": ""}],
    "non_pharmacological": ["intervention1", "intervention2"]
  },
  "alternative_treatments": [{"name": "", "when_to_use": "", "notes": ""}],
  "drug_interactions_checked": true,
  "interaction_warnings": ["warning1 if any"],
  "monitoring": ["what to watch", "timeline"],
  "follow_up": "when and with whom",
  "patient_education": ["key point 1", "key point 2"],
  "lifestyle_modifications": ["change1", "change2"],
  "red_flags_for_return": ["symptom that should trigger immediate return"]
}"""

_TOOLS = [
    {
        "name": "check_drug_interactions",
        "description": "Check for interactions between a proposed new drug and the patient's current medications.",
        "input_schema": {
            "type": "object",
            "properties": {
                "new_drug": {"type": "string", "description": "Drug being considered for treatment"},
                "current_medications": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of patient's current medications",
                },
            },
            "required": ["new_drug", "current_medications"],
        },
    },
    {
        "name": "calculate_dosage",
        "description": "Calculate appropriate dosage based on patient weight/age/renal function.",
        "input_schema": {
            "type": "object",
            "properties": {
                "drug": {"type": "string"},
                "patient_age": {"type": "integer"},
                "patient_weight_kg": {"type": "number"},
                "condition": {"type": "string"},
            },
            "required": ["drug", "patient_age", "condition"],
        },
    },
    {
        "name": "search_medical_info",
        "description": "Search treatment guidelines or clinical evidence for a condition.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
            "required": ["query"],
        },
    },
]


class TreatmentAgent:

    def run(self, state: dict) -> dict:
        diagnosis = state.get("diagnosis", "")
        differentials = state.get("differential_diagnoses", [])
        symptom_analysis = state.get("symptom_analysis", "")
        age = state.get("age", "unknown")
        gender = state.get("gender", "unknown")
        history = state.get("medical_history", [])
        meds = state.get("current_medications", [])
        allergies = state.get("allergies", [])
        severity = state.get("severity_level", "medium")

        user_message = (
            f"Patient: {age}-year-old {gender}, severity: {severity}\n"
            f"Medical History: {', '.join(history) if history else 'none'}\n"
            f"Current Medications: {', '.join(meds) if meds else 'none'}\n"
            f"Allergies: {', '.join(allergies) if allergies else 'NKDA'}\n\n"
            f"Diagnosis:\n{diagnosis}\n\n"
            "Generate a complete treatment plan. "
            "Check drug interactions for any new medications you recommend."
        )

        messages: list[dict] = [{"role": "user", "content": user_message}]
        final_response = None
        interaction_results: list[str] = []

        for _ in range(6):
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
                    if block.type != "tool_use":
                        continue

                    if block.name == "check_drug_interactions":
                        result = check_drug_interactions(
                            new_drug=block.input["new_drug"],
                            current_medications=block.input.get("current_medications", meds),
                        )
                        interaction_results.append(result)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                    elif block.name == "calculate_dosage":
                        result = calculate_dosage(
                            drug=block.input["drug"],
                            patient_age=block.input.get("patient_age", age),
                            patient_weight_kg=block.input.get("patient_weight_kg"),
                            condition=block.input.get("condition", ""),
                        )
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                    elif block.name == "search_medical_info":
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

        treatment_text = _extract_text(final_response)
        interactions_summary = "\n".join(interaction_results) if interaction_results else "No interactions checked."

        return {
            "treatment_plan": treatment_text,
            "drug_interactions": interactions_summary,
            "messages": [{"role": "treatment_agent", "content": treatment_text}],
        }


def _extract_text(response: Any) -> str:
    for block in response.content:
        if hasattr(block, "text"):
            return block.text
    return ""
