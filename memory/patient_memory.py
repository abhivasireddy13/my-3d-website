"""
Patient memory management.

LangGraph's MemorySaver handles within-session state automatically via the
thread_id mechanism. This module adds on-disk persistence for patient histories
across sessions — separate from the graph's checkpointer.

Two kinds of storage here:
  1. Session memory  — LangGraph handles this (MemorySaver in orchestrator.py)
  2. Patient history — JSON files on disk, one per patient_id

The session/history distinction matters: the graph checkpointer stores the full
state graph at each step (for resumption), while patient history just stores
the final summary of each visit. Don't conflate them.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_HISTORY_DIR = Path("memory/patient_histories")
_HISTORY_DIR.mkdir(parents=True, exist_ok=True)


# ── Per-patient history ───────────────────────────────────────────────────────

def _history_path(patient_id: str) -> Path:
    safe_id = "".join(c for c in patient_id if c.isalnum() or c in "-_")
    return _HISTORY_DIR / f"{safe_id}.json"


def load_patient_history(patient_id: str) -> dict:
    """Load stored history for a patient. Returns empty structure if not found."""
    path = _history_path(patient_id)
    if not path.exists():
        return {
            "patient_id": patient_id,
            "visits": [],
            "known_conditions": [],
            "known_medications": [],
            "known_allergies": [],
        }

    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to load history for {patient_id}: {e}")
        return {"patient_id": patient_id, "visits": [], "known_conditions": [], "known_medications": [], "known_allergies": []}


def save_visit(patient_id: str, state: dict) -> None:
    """
    Persist a completed visit to the patient's history file.
    Called at the end of each diagnostic session.
    """
    history = load_patient_history(patient_id)

    visit = {
        "timestamp": datetime.utcnow().isoformat(),
        "symptoms": state.get("symptoms", []),
        "symptom_description": state.get("symptom_description", ""),
        "severity": state.get("severity_level"),
        "diagnosis_summary": _truncate(state.get("diagnosis", ""), 500),
        "treatment_summary": _truncate(state.get("treatment_plan", ""), 500),
        "session_id": state.get("patient_id", patient_id),
    }

    history["visits"].append(visit)

    # accumulate known data across visits — deduplicate
    new_meds = state.get("current_medications", [])
    new_allergies = state.get("allergies", [])

    history["known_medications"] = _merge_unique(history["known_medications"], new_meds)
    history["known_allergies"] = _merge_unique(history["known_allergies"], new_allergies)

    path = _history_path(patient_id)
    try:
        with open(path, "w") as f:
            json.dump(history, f, indent=2)
        logger.info(f"Saved visit for patient {patient_id}")
    except IOError as e:
        logger.error(f"Failed to save visit for {patient_id}: {e}")


def get_visit_summary(patient_id: str, last_n: int = 3) -> str:
    """
    Return a formatted summary of the patient's recent visits.
    Used to prime agents with patient context on return visits.
    """
    history = load_patient_history(patient_id)
    visits = history.get("visits", [])

    if not visits:
        return f"No previous visits found for patient {patient_id}."

    recent = visits[-last_n:]
    lines = [f"Patient {patient_id} — {len(visits)} visit(s) on record\n"]

    known_meds = history.get("known_medications", [])
    known_allergies = history.get("known_allergies", [])

    if known_meds:
        lines.append(f"Known medications: {', '.join(known_meds)}")
    if known_allergies:
        lines.append(f"Known allergies: {', '.join(known_allergies)}")

    lines.append(f"\nLast {len(recent)} visit(s):")
    for v in reversed(recent):
        ts = v.get("timestamp", "unknown date")
        sev = v.get("severity", "?")
        syms = ", ".join(v.get("symptoms", []))[:100]
        dx_sum = v.get("diagnosis_summary", "")[:200]
        lines.append(f"\n  [{ts}] Severity: {sev} | Symptoms: {syms}")
        if dx_sum:
            lines.append(f"  Diagnosis: {dx_sum}")

    return "\n".join(lines)


def list_patients() -> list[str]:
    """Return list of all stored patient IDs."""
    return [p.stem for p in _HISTORY_DIR.glob("*.json")]


# ── In-session conversation buffer ────────────────────────────────────────────
# Thin wrapper around a list — LangGraph manages the actual state,
# this is just a helper for the Streamlit UI to display conversation history.

class ConversationBuffer:
    def __init__(self, max_turns: int = 50):
        self._turns: list[dict] = []
        self._max = max_turns

    def add(self, role: str, content: str, metadata: Optional[dict] = None) -> None:
        self._turns.append({
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        })
        if len(self._turns) > self._max:
            self._turns = self._turns[-self._max:]

    def get_all(self) -> list[dict]:
        return list(self._turns)

    def clear(self) -> None:
        self._turns.clear()

    def format_for_display(self) -> str:
        lines = []
        for t in self._turns:
            role = t["role"].replace("_", " ").title()
            lines.append(f"**{role}:** {t['content'][:300]}...")
        return "\n\n".join(lines)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _truncate(text: str, max_len: int) -> str:
    return text[:max_len] + "..." if len(text) > max_len else text


def _merge_unique(existing: list, new_items: list) -> list:
    seen = {x.lower().strip() for x in existing}
    merged = list(existing)
    for item in new_items:
        if item.lower().strip() not in seen:
            merged.append(item)
            seen.add(item.lower().strip())
    return merged
