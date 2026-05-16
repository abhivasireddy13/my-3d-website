"""
Streamlit UI for the Medical Diagnostics Multi-Agent System.

Run: streamlit run app.py
Requires: ANTHROPIC_API_KEY environment variable set.

Design notes:
- st.status() blocks give real "thinking" feedback while agents run.
  Without this the UI just freezes for 30+ seconds which feels broken.
- Patient form is intentionally simple — the symptom description free text
  is where most of the interesting signal comes from anyway.
- Results are streamed section-by-section as each agent finishes.
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Optional

import streamlit as st

# ── Page config must be first Streamlit call ──────────────────────────────────
st.set_page_config(
    page_title="Medical Diagnostics Agent",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── API key check ─────────────────────────────────────────────────────────────
if not os.getenv("ANTHROPIC_API_KEY"):
    st.error(
        "**ANTHROPIC_API_KEY not set.**\n\n"
        "Set it in your environment before running:\n"
        "```\nexport ANTHROPIC_API_KEY=sk-ant-...\nstreamlit run app.py\n```"
    )
    st.stop()

# ── Common symptoms for multi-select ─────────────────────────────────────────
SYMPTOM_LIST = [
    "Chest pain", "Shortness of breath", "Palpitations",
    "Headache", "Dizziness", "Fainting / near-fainting",
    "Fever", "Chills", "Night sweats", "Fatigue",
    "Nausea", "Vomiting", "Diarrhea", "Abdominal pain", "Loss of appetite",
    "Cough", "Wheezing", "Sore throat", "Runny nose",
    "Back pain", "Joint pain", "Muscle aches",
    "Rash / skin changes", "Swelling (legs/ankles)", "Swelling (face/throat)",
    "Frequent urination", "Painful urination", "Blood in urine",
    "Vision changes", "Hearing changes", "Numbness / tingling",
    "Arm or leg weakness", "Difficulty speaking", "Confusion",
    "Anxiety / mood changes", "Sleep problems", "Weight changes",
]

MEDICAL_CONDITIONS = [
    "Hypertension", "Type 2 Diabetes", "Type 1 Diabetes",
    "Heart disease / CAD", "Heart failure", "Atrial fibrillation",
    "COPD", "Asthma", "Sleep apnea",
    "Hypothyroidism", "Hyperthyroidism",
    "Kidney disease (CKD)", "Liver disease",
    "Stroke / TIA (prior)", "Epilepsy",
    "Depression", "Anxiety disorder",
    "Rheumatoid arthritis", "Lupus", "Fibromyalgia",
    "Cancer (specify in description)", "HIV/AIDS",
    "Osteoporosis", "Anemia",
]

SEVERITY_COLORS = {
    "low": "#28a745",
    "medium": "#ffc107",
    "high": "#fd7e14",
    "emergency": "#dc3545",
}

SEVERITY_ICONS = {
    "low": "✅",
    "medium": "⚠️",
    "high": "🔴",
    "emergency": "🚨",
}


# ── Session state initialization ──────────────────────────────────────────────
def _init_session():
    defaults = {
        "results": None,
        "patient_id": str(uuid.uuid4())[:8],
        "run_count": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_session()


# ── Header ────────────────────────────────────────────────────────────────────
st.title("🏥 Medical Diagnostics Multi-Agent System")
st.markdown(
    """
> **⚠️ DISCLAIMER:** This system is built for **educational and research purposes only**.
> It does **not** constitute medical advice and must **never** be used for clinical decisions.
> Always consult a qualified healthcare provider for diagnosis and treatment.

*Powered by Claude claude-sonnet-4-6 · Built with LangGraph · [View on GitHub](https://github.com/abhivasireddy13/AI-Agents-for-Medical-Diagnostics)*
"""
)
st.divider()


# ── Sidebar: Patient Intake Form ──────────────────────────────────────────────
with st.sidebar:
    st.header("Patient Intake Form")
    st.caption(f"Session ID: {st.session_state.patient_id}")

    st.subheader("Demographics")
    col_a, col_b = st.columns(2)
    with col_a:
        age = st.number_input("Age", min_value=1, max_value=120, value=35, step=1)
    with col_b:
        gender = st.selectbox("Gender", ["Male", "Female", "Non-binary", "Prefer not to say"])

    st.subheader("Symptoms")
    selected_symptoms = st.multiselect(
        "Select symptoms (multi-select):",
        options=SYMPTOM_LIST,
        default=[],
        placeholder="Choose from list...",
    )

    symptom_description = st.text_area(
        "Describe your symptoms in detail:",
        placeholder=(
            "e.g., Started 2 days ago. Chest pain radiates to left arm. "
            "Worse on exertion. Rate it 7/10. Also noticed shortness of breath."
        ),
        height=140,
    )

    st.subheader("Medical History")
    selected_conditions = st.multiselect(
        "Existing conditions:",
        options=MEDICAL_CONDITIONS,
        default=[],
    )
    extra_history = st.text_input(
        "Other conditions (not in list):",
        placeholder="e.g., Celiac disease, migraines...",
    )
    medical_history = selected_conditions + ([extra_history] if extra_history.strip() else [])

    st.subheader("Medications & Allergies")
    meds_input = st.text_area(
        "Current medications (one per line):",
        placeholder="e.g.,\nMetformin 500mg\nLisinopril 10mg\nAtorvastatin 20mg",
        height=100,
    )
    allergies_input = st.text_input(
        "Known allergies:",
        placeholder="e.g., Penicillin, Sulfa, Shellfish",
    )

    medications = [m.strip() for m in meds_input.splitlines() if m.strip()]
    allergies = [a.strip() for a in allergies_input.split(",") if a.strip()]

    st.divider()
    analyze_btn = st.button(
        "🔍 Analyze",
        type="primary",
        use_container_width=True,
        disabled=not (selected_symptoms or symptom_description.strip()),
    )

    if not (selected_symptoms or symptom_description.strip()):
        st.caption("Add symptoms above to enable analysis.")


# ── Main panel ────────────────────────────────────────────────────────────────
main_col, info_col = st.columns([3, 1])

with info_col:
    st.subheader("How it works")
    st.markdown(
        """
**Agent Pipeline:**

1. **Symptom Analyzer**
   → Classifies severity, identifies red flags

2. **Diagnosis Agent**
   → Differential diagnosis with reasoning

3. **Treatment Agent**
   → Treatment plan + drug interaction check

4. **Report Generator**
   → Synthesized clinical report

Each agent can search medical literature and call clinical tools before responding.
        """
    )

    st.subheader("Run History")
    if st.session_state.run_count > 0:
        st.metric("Analyses run", st.session_state.run_count)
    else:
        st.caption("No analyses yet this session.")

with main_col:

    if analyze_btn:
        # ── Validate inputs ───────────────────────────────────────────────────
        if not selected_symptoms and not symptom_description.strip():
            st.warning("Please select or describe at least one symptom.")
            st.stop()

        # ── Build initial state ───────────────────────────────────────────────
        from agents.orchestrator import compiled_graph

        patient_id = f"{st.session_state.patient_id}_{st.session_state.run_count}"

        initial_state = {
            "patient_id": patient_id,
            "age": int(age),
            "gender": gender.lower(),
            "symptoms": selected_symptoms,
            "symptom_description": symptom_description.strip(),
            "medical_history": medical_history,
            "current_medications": medications,
            "allergies": allergies,
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
        result_state = {}

        # ── Run the agent pipeline with live status updates ───────────────────
        st.subheader("Running Agent Pipeline")

        with st.status("Starting analysis...", expanded=True) as status:

            st.write("📋 **Intake complete.** Routing to Symptom Analyzer...")
            time.sleep(0.3)

            # We run the graph and collect partial results node by node
            # using stream() so we can show progress without blocking the entire UI
            node_outputs = {}

            for chunk in compiled_graph.stream(initial_state, config=config, stream_mode="values"):
                node_outputs.update(chunk)

                if chunk.get("symptom_analysis") and "symptom_analysis" not in result_state:
                    result_state["symptom_analysis"] = chunk["symptom_analysis"]
                    sev = chunk.get("severity_level", "unknown")
                    sev_icon = SEVERITY_ICONS.get(sev, "ℹ️")
                    st.write(f"✅ **Symptom Analyzer complete.** Severity: {sev_icon} `{sev.upper()}`")

                if chunk.get("diagnosis") and "diagnosis" not in result_state:
                    result_state["diagnosis"] = chunk["diagnosis"]
                    diffs = chunk.get("differential_diagnoses", [])
                    st.write(f"✅ **Diagnosis Agent complete.** {len(diffs)} differential(s) identified.")

                if chunk.get("treatment_plan") and "treatment_plan" not in result_state:
                    result_state["treatment_plan"] = chunk["treatment_plan"]
                    interactions = chunk.get("drug_interactions", "")
                    interaction_note = " Drug interaction check run." if interactions else ""
                    st.write(f"✅ **Treatment Agent complete.**{interaction_note}")

                if chunk.get("final_report") and "final_report" not in result_state:
                    result_state["final_report"] = chunk["final_report"]
                    st.write("✅ **Report Generator complete.** Final report ready.")

            # merge final state
            final_result = {**initial_state, **node_outputs, **result_state}
            st.session_state.results = final_result
            st.session_state.run_count += 1

            severity = final_result.get("severity_level", "unknown")
            if severity == "emergency":
                status.update(label="🚨 EMERGENCY — Immediate action required!", state="error")
            elif severity == "high":
                status.update(label="🔴 Analysis complete — High severity, prompt care needed", state="error")
            else:
                status.update(label="✅ Analysis complete", state="complete")

    # ── Display results ───────────────────────────────────────────────────────
    if st.session_state.results:
        res = st.session_state.results
        severity = res.get("severity_level", "unknown")
        sev_color = SEVERITY_COLORS.get(severity, "#6c757d")
        sev_icon = SEVERITY_ICONS.get(severity, "ℹ️")

        # severity badge
        st.markdown(
            f"""
<div style="background:{sev_color};color:white;padding:12px 20px;border-radius:8px;
            font-size:1.2em;font-weight:bold;margin-bottom:16px">
  {sev_icon} Severity Assessment: {severity.upper()}
</div>
""",
            unsafe_allow_html=True,
        )

        if severity == "emergency":
            st.error(
                "🚨 **EMERGENCY CONDITIONS DETECTED.** "
                "Call emergency services (911 / local emergency number) immediately. "
                "Do not drive yourself to the hospital."
            )

        # final report
        final_report = res.get("final_report", "")
        if final_report:
            st.subheader("Clinical Report")
            st.markdown(final_report)

        st.divider()

        # expandable detail sections for each agent's raw output
        with st.expander("📊 Symptom Analysis (raw)", expanded=False):
            st.markdown(res.get("symptom_analysis", "No analysis available."))

        with st.expander("🔬 Diagnosis Details (raw)", expanded=False):
            st.markdown(res.get("diagnosis", "No diagnosis output available."))
            diffs = res.get("differential_diagnoses", [])
            if diffs:
                st.markdown("**Differentials identified:**")
                for d in diffs:
                    st.markdown(f"- {d}")

        with st.expander("💊 Treatment Plan (raw)", expanded=False):
            st.markdown(res.get("treatment_plan", "No treatment plan available."))

        with st.expander("⚠️ Drug Interaction Check", expanded=(severity in ["high", "emergency"])):
            interactions = res.get("drug_interactions", "")
            if interactions and "No current medications" not in interactions:
                st.warning(interactions)
            else:
                st.success(interactions or "No medications provided for interaction check.")

        with st.expander("🔄 Agent Message Log", expanded=False):
            messages = res.get("messages", [])
            if messages:
                for msg in messages:
                    role = msg.get("role", "unknown").replace("_", " ").title()
                    content = msg.get("content", "")[:500]
                    st.caption(f"**{role}:** {content}...")
            else:
                st.caption("No messages logged.")

        st.divider()

        # download button
        report_text = final_report or "No report generated."
        st.download_button(
            label="📄 Download Report",
            data=report_text,
            file_name=f"medical_report_{patient_id}.md",
            mime="text/markdown",
        )

        if st.button("🔄 New Analysis"):
            st.session_state.results = None
            st.session_state.patient_id = str(uuid.uuid4())[:8]
            st.rerun()

    elif not analyze_btn:
        st.info(
            "👈 Fill in the patient intake form on the left and click **Analyze** to run the full diagnostic pipeline."
        )
        st.markdown(
            """
### What this system does

This project demonstrates a multi-agent AI diagnostic assistant built with **LangGraph** and **Claude claude-sonnet-4-6**.

The system routes a patient intake form through four specialist agents:

| Agent | Role |
|-------|------|
| Symptom Analyzer | Classifies severity, identifies red flags, searches medical literature |
| Diagnosis Agent | Differential diagnosis with ICD-10 codes and clinical reasoning |
| Treatment Agent | Evidence-based treatment plan with drug interaction checking |
| Report Generator | Synthesized clinical report in readable format |

**Technologies:** LangGraph · Anthropic Claude API · DuckDuckGo medical search · openFDA drug database · Streamlit
            """
        )
