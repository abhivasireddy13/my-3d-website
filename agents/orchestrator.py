"""
LangGraph orchestrator for the medical diagnostics multi-agent system.

The graph wires together four specialist agents:
  intake → symptom_analysis → diagnosis → treatment → report

LangGraph was confusing at first — the state dict is the key insight.
Every node reads from state and writes back a *partial* state update.
LangGraph merges the partial dict back in. Once that clicked, building
this was actually pretty clean.
"""

from __future__ import annotations

import operator
from typing import Annotated, List, Literal, Optional, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from agents.diagnosis_agent import DiagnosisAgent
from agents.report_generator import ReportGenerator
from agents.symptom_analyzer import SymptomAnalyzer
from agents.treatment_agent import TreatmentAgent


# ── State definition ──────────────────────────────────────────────────────────
# Annotated[List[dict], operator.add] tells LangGraph to *append* to the list
# rather than replace it. Everything else is last-writer-wins.

class PatientState(TypedDict):
    # intake
    patient_id: str
    age: int
    gender: str
    symptoms: List[str]
    symptom_description: str
    medical_history: List[str]
    current_medications: List[str]
    allergies: List[str]

    # agent outputs -- each node writes only to its own slice
    symptom_analysis: Optional[str]
    severity_level: Optional[Literal["low", "medium", "high", "emergency"]]
    diagnosis: Optional[str]
    differential_diagnoses: Optional[List[str]]
    treatment_plan: Optional[str]
    drug_interactions: Optional[str]
    final_report: Optional[str]

    # internal bookkeeping
    messages: Annotated[List[dict], operator.add]
    error: Optional[str]
    iteration_count: int


# ── Routing logic ─────────────────────────────────────────────────────────────
# Keeping routing functions here (not inside nodes) makes the graph structure
# obvious just from reading build_graph(). Nodes shouldn't know about topology.

def route_by_severity(state: PatientState) -> str:
    severity = state.get("severity_level", "medium")
    if severity == "emergency":
        return "emergency"
    return "diagnosis"


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    symptom_agent = SymptomAnalyzer()
    diagnosis_agent = DiagnosisAgent()
    treatment_agent = TreatmentAgent()
    report_agent = ReportGenerator()

    graph = StateGraph(PatientState)

    graph.add_node("symptom_analysis", symptom_agent.run)
    graph.add_node("diagnosis", diagnosis_agent.run)
    graph.add_node("treatment", treatment_agent.run)
    graph.add_node("report", report_agent.run)
    graph.add_node("emergency_report", report_agent.run_emergency)

    graph.set_entry_point("symptom_analysis")

    graph.add_conditional_edges(
        "symptom_analysis",
        route_by_severity,
        {
            "diagnosis": "diagnosis",
            "emergency": "emergency_report",
        },
    )
    graph.add_edge("diagnosis", "treatment")
    graph.add_edge("treatment", "report")
    graph.add_edge("report", END)
    graph.add_edge("emergency_report", END)

    return graph


# spent 2 days debugging the memory node -- turns out checkpointer must be passed
# at graph compile time, not at invoke() time. langgraph 0.2.x silently ignores
# a checkpointer passed to invoke(). classic footgun.
checkpointer = MemorySaver()
compiled_graph = build_graph().compile(checkpointer=checkpointer)
