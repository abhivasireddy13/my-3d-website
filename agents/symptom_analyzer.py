"""
Symptom analysis agent — first node in the diagnostic pipeline.

Takes raw patient intake (symptoms, demographics, history) and produces:
  - structured symptom analysis
  - severity classification (low / medium / high / emergency)
  - red flag identification

Uses Claude with tool_use to optionally search for uncommon symptom clusters.
Tool calling adds latency (~1-2s per search) but catches edge cases the model
would otherwise miss from training data alone — worth it for a medical context.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import anthropic

from tools.medical_search import search_medical_info

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are a clinical symptom analysis specialist with 20+ years of experience.

Your job in this pipeline step:
1. Analyze the patient's reported symptoms systematically
2. Identify red flag symptoms that require immediate attention
3. Classify severity: low | medium | high | emergency
4. Group symptoms into likely clusters pointing to specific pathologies
5. Note anything in the medical history that changes risk profile

Severity guide:
  emergency — symptoms suggesting stroke, MI, sepsis, anaphylaxis, pulmonary embolism
  high      — symptoms needing same-day evaluation
  medium    — symptoms needing evaluation within a few days
  low       — symptoms manageable with self-care + routine follow-up

ALWAYS output valid JSON with these exact keys:
{
  "analysis": "detailed clinical reasoning",
  "severity_level": "low|medium|high|emergency",
  "red_flags": ["list", "of", "concerning", "symptoms"],
  "symptom_clusters": {"cluster_name": ["symptom1", "symptom2"]},
  "recommended_urgency": "narrative description of when to seek care"
}"""

_TOOLS = [
    {
        "name": "search_medical_info",
        "description": (
            "Search for medical literature or clinical guidelines about a symptom "
            "combination or condition. Use when the symptom pattern is unusual or "
            "you need to check current clinical guidance."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Medical search query, e.g. 'sudden onset chest pain radiating to jaw'",
                }
            },
            "required": ["query"],
        },
    }
]


class SymptomAnalyzer:

    def run(self, state: dict) -> dict:
        symptoms = state.get("symptoms", [])
        description = state.get("symptom_description", "")
        age = state.get("age", "unknown")
        gender = state.get("gender", "unknown")
        history = state.get("medical_history", [])
        meds = state.get("current_medications", [])

        user_message = (
            f"Patient: {age}-year-old {gender}\n"
            f"Reported symptoms: {', '.join(symptoms) if symptoms else 'see description'}\n"
            f"Patient description: {description}\n"
            f"Medical history: {', '.join(history) if history else 'none reported'}\n"
            f"Current medications: {', '.join(meds) if meds else 'none'}\n\n"
            "Analyze these symptoms and return structured JSON output."
        )

        messages: list[dict] = [{"role": "user", "content": user_message}]
        final_response = None

        # agentic loop -- model calls tools until it has enough info
        for iteration in range(4):
            response = _client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
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
                    if block.type == "tool_use":
                        logger.info(f"SymptomAnalyzer calling tool: {block.name}")
                        if block.name == "search_medical_info":
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

        analysis_text = _extract_text(final_response)
        severity, parsed = _parse_json_response(analysis_text)

        return {
            "symptom_analysis": analysis_text,
            "severity_level": severity,
            "messages": [
                {"role": "symptom_analyzer", "content": analysis_text, "severity": severity}
            ],
        }


def _extract_text(response: Any) -> str:
    for block in response.content:
        if hasattr(block, "text"):
            return block.text
    return ""


def _parse_json_response(text: str) -> tuple[str, dict]:
    """Extract severity from JSON response, with fallback keyword matching."""
    try:
        clean = text.strip()
        if "```json" in clean:
            clean = clean.split("```json")[1].split("```")[0].strip()
        elif "```" in clean:
            clean = clean.split("```")[1].split("```")[0].strip()

        parsed = json.loads(clean)
        severity = parsed.get("severity_level", "medium")
        if severity not in ("low", "medium", "high", "emergency"):
            severity = "medium"
        return severity, parsed

    except (json.JSONDecodeError, IndexError, KeyError):
        # fallback: keyword scan on raw text
        lower = text.lower()
        if any(w in lower for w in ["emergency", "call 911", "immediate er", "anaphylaxis"]):
            return "emergency", {}
        if any(w in lower for w in ["severe", "urgent", "high risk", "same-day"]):
            return "high", {}
        if any(w in lower for w in ["mild", "low risk", "self-care", "minor"]):
            return "low", {}
        return "medium", {}
