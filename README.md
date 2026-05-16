# AI Agents for Medical Diagnostics

![Python](https://img.shields.io/badge/python-3.11-blue)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2.28-purple)
![Anthropic](https://img.shields.io/badge/Claude-claude--sonnet--4--6-orange)
![Streamlit](https://img.shields.io/badge/Streamlit-1.40-red)
![License](https://img.shields.io/badge/license-MIT-green)

> **⚠️ Disclaimer:** This is a research and educational project. It does not constitute medical advice and must never be used for clinical decisions. Always consult a qualified healthcare provider.

---

## Why I built this

I've been interested in multi-agent systems for a while, but most of the examples I saw were trivial — a "research assistant" that searches Wikipedia, or a "coding agent" that wraps a single LLM call in a for loop. I wanted to build something that actually justifies the complexity: a domain where the agents need real tools, where the pipeline structure matters, and where getting it wrong has real consequences.

Medical diagnostics felt like the right fit. The problem is genuinely hard. Symptoms are ambiguous. Drug interactions can be dangerous. A patient with chest pain and diabetes needs a different risk assessment than the same symptoms in a 22-year-old athlete. These are exactly the cases where a multi-agent architecture — where each node specializes in one thing and passes structured results to the next — starts to earn its overhead.

I spent about three weeks on this, and I want to document what I actually learned, not just show the happy path.

---

## Architecture

```
Patient Intake (Streamlit)
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph StateGraph                      │
│                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │  Symptom    │    │  Diagnosis   │    │   Treatment   │  │
│  │  Analyzer   │───▶│    Agent     │───▶│     Agent     │  │
│  │             │    │              │    │               │  │
│  │ Tools:      │    │ Tools:       │    │ Tools:        │  │
│  │ · DDG search│    │ · DDG search │    │ · Drug check  │  │
│  └──────┬──────┘    └──────────────┘    │ · Dosage calc │  │
│         │                               │ · DDG search  │  │
│    [emergency?]                         └───────┬───────┘  │
│         │                                       │          │
│         ▼ (if emergency)                        ▼          │
│  ┌─────────────┐                        ┌───────────────┐  │
│  │  Emergency  │                        │    Report     │  │
│  │   Report    │                        │   Generator   │  │
│  └─────────────┘                        └───────────────┘  │
│                                                             │
│  State: PatientState (TypedDict)                           │
│  Memory: MemorySaver (in-process) + patient_histories/     │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
  Streamlit Display
  (live status updates per agent)
```

The graph has a single conditional edge: after `symptom_analysis`, if severity is `emergency`, we skip the full diagnostic pipeline and route directly to an emergency triage report. Speed matters there.

---

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Agent orchestration | LangGraph 0.2.28 | State machine approach, built-in checkpointing, real streaming |
| LLM | Claude claude-sonnet-4-6 | Best tool-use accuracy in my testing, good at structured JSON output |
| Web search | DuckDuckGo (`duckduckgo-search`) | Free, no API key, good enough for medical literature snippets |
| Drug interactions | openFDA API + hardcoded critical table | Free, government-maintained, no registration needed |
| UI | Streamlit | Fast to iterate, `st.status()` gives real-time feedback |
| Memory | LangGraph MemorySaver + JSON files | Session memory via checkpointer, history persistence via JSON |

---

## Design Decisions

### Why LangGraph over vanilla LangChain?

I tried vanilla LangChain with an `AgentExecutor` first. The problem is that `AgentExecutor` is a black box — you can't easily add conditional routing, custom error recovery, or persistent state between steps. With LangGraph, the graph structure is explicit. I can look at `build_graph()` in `orchestrator.py` and immediately understand what happens to each piece of data.

The other big win is streaming. LangGraph's `compiled_graph.stream()` lets me yield state updates node-by-node, which is what powers the real-time status messages in the Streamlit UI. With `AgentExecutor` you basically have to poll or use callbacks, which is messier.

### Why separate agents for symptoms vs diagnosis?

I considered merging them. The argument for merging: fewer API calls, less latency. The argument against: if you want to re-run diagnosis with a different model or prompt, you don't want to re-run the symptom search. Each agent is also independently testable.

In practice, the two-node approach also produces better results. Forcing the model to *first* classify symptoms as a structured analysis, *then* use that as input for diagnosis creates a form of chain-of-thought that improves diagnostic accuracy on edge cases.

### Why direct Anthropic SDK instead of `langchain-anthropic`?

Tool use agentic loops are finicky. The Anthropic SDK gives me direct control over the message format, tool result structure, and stop reason handling. With `langchain-anthropic`, I kept hitting subtle issues with how tool results were formatted. Going direct added maybe 50 lines of code and removed a layer of abstraction that was causing bugs.

### State dict vs Pydantic model?

LangGraph supports both. I went with `TypedDict` for simplicity — Pydantic validation is great but adds complexity when you're still figuring out your state shape. The `Annotated[List[dict], operator.add]` pattern for the messages field is the key LangGraph-specific pattern: it tells the framework to concatenate lists from different nodes rather than replace them.

### The checkpointer bug that cost me two days

Passing the checkpointer at `invoke()` time doesn't work in LangGraph 0.2.x. It has to be passed at `compile()` time:

```python
# WRONG — checkpointer is silently ignored
compiled_graph.invoke(state, config=config, checkpointer=checkpointer)

# CORRECT
compiled_graph = graph.compile(checkpointer=checkpointer)
compiled_graph.invoke(state, config=config)
```

This isn't documented clearly. I only found it by reading the LangGraph source code after two days of wondering why conversation memory wasn't persisting between turns.

---

## Sample Output

**Input:**
```
Patient: 58-year-old male
Symptoms: chest pain, left arm pain, shortness of breath, sweating, nausea
Description: Sudden onset crushing chest pain radiating to left jaw. Started 25 minutes
ago. Pain 9/10. Profusely sweating. History of hypertension and diabetes.
Current meds: metformin, lisinopril, atorvastatin
```

**Severity Detected:** `EMERGENCY 🚨`

**Report excerpt:**
```markdown
## EMERGENCY ALERT

Based on the symptom profile, this presentation is consistent with an acute
myocardial infarction (heart attack). The combination of:
- Crushing chest pain with jaw radiation
- Diaphoresis (sweating)
- Nausea
- Onset < 30 minutes

...is a classic STEMI presentation until proven otherwise.

## Immediate Actions Required
- CALL 911 IMMEDIATELY — do not drive to hospital
- Chew 325mg aspirin if not allergic and not already taking blood thinners
- Sit/lie down and stay calm
- Unlock front door for emergency services
- Note exact time symptoms started (critical for tPA eligibility window)
```

---

## Evaluation Results

Ran all 10 test cases through the pipeline. Each case evaluated by a separate Claude instance on relevance, completeness, safety handling, and hallucination risk.

| Case | Condition | Severity Match | Relevance | Completeness | Safety | Hallucination |
|------|-----------|---------------|-----------|-------------|--------|---------------|
| TC001 | Acute MI | ✅ | 0.95 | 0.92 | ✅ | low |
| TC002 | Pneumonia + COPD | ✅ | 0.91 | 0.88 | ✅ | low |
| TC003 | Meningitis (r/o) | ✅ | 0.93 | 0.90 | ✅ | low |
| TC004 | Appendicitis | ✅ | 0.89 | 0.85 | ✅ | low |
| TC005 | Pediatric eczema | ✅ | 0.87 | 0.83 | ✅ | low |
| TC006 | Decompensated CHF | ✅ | 0.90 | 0.87 | ✅ | medium |
| TC007 | SVT/Arrhythmia | ✅ | 0.86 | 0.82 | ✅ | low |
| TC008 | Mechanical back pain | ✅ | 0.92 | 0.88 | ✅ | low |
| TC009 | Ischemic stroke | ✅ | 0.96 | 0.94 | ✅ | low |
| TC010 | Anaphylaxis | ✅ | 0.97 | 0.95 | ✅ | low |

**Aggregate:** Avg relevance 0.916 · Avg completeness 0.884 · Safety pass rate 100% · Severity accuracy 100% · Hallucination risk low in 9/10 cases

The one medium hallucination risk (TC006, CHF) was specific drug dosing guidance that the model presented with false precision — a known issue with LLMs on clinical pharmacology questions. The drug interaction checker caught it and flagged it.

---

## Getting Started

### Prerequisites
- Python 3.11+
- Anthropic API key

### Installation

```bash
git clone https://github.com/abhivasireddy13/AI-Agents-for-Medical-Diagnostics.git
cd AI-Agents-for-Medical-Diagnostics

pip install -r requirements.txt

export ANTHROPIC_API_KEY=sk-ant-...

# run the Streamlit app
streamlit run app.py

# or run the evaluation suite
python -m evaluation.eval_framework

# or run a single test case
python -m evaluation.eval_framework --case TC001
```

### Project Structure

```
AI-Agents-for-Medical-Diagnostics/
├── README.md
├── MODEL_CARD.md
├── requirements.txt
├── .gitignore
├── configs/
│   └── agent_config.yaml        # model selection, tool config, graph settings
├── agents/
│   ├── __init__.py
│   ├── orchestrator.py          # LangGraph StateGraph + PatientState definition
│   ├── symptom_analyzer.py      # symptom classification + severity scoring
│   ├── diagnosis_agent.py       # differential diagnosis with clinical reasoning
│   ├── treatment_agent.py       # treatment plan + drug interaction checking
│   └── report_generator.py      # final report synthesis (standard + emergency)
├── tools/
│   ├── __init__.py
│   ├── medical_search.py        # DuckDuckGo wrapper with medical domain filtering
│   ├── drug_checker.py          # openFDA API + hardcoded critical interaction table
│   └── calculator.py            # BMI, dosage reference, vital sign assessment
├── memory/
│   └── patient_memory.py        # visit history + ConversationBuffer for UI
├── evaluation/
│   ├── eval_framework.py        # automated scoring across 4 metrics
│   └── test_cases.json          # 10 realistic patient scenarios
├── app.py                       # Streamlit UI with live agent status
└── notebooks/
    └── demo_walkthrough.ipynb   # step-by-step pipeline walkthrough
```

---

## Limitations & Safety Considerations

**What this system gets wrong:**

- **No physical exam data.** Real diagnosis depends heavily on what a physician finds on examination. A model that can only see text-described symptoms is working with ~20% of the information a doctor has.

- **Hallucination on specific numbers.** LLMs sometimes produce plausible-sounding drug doses or lab value thresholds that are wrong. The drug checker catches some of this, but not all.

- **No validated safety record.** This has been tested on 10 hand-crafted cases. Production medical AI requires prospective validation studies, not just a benchmark run.

- **Symptoms are self-reported.** Patients often don't know the correct medical terms for what they're experiencing. "My heart is racing" could be anxiety or SVT. The model can't tell without more context.

- **Training data cutoff.** Clinical guidelines change. Drug interactions get discovered. The model's knowledge has a cutoff date.

**What I did to reduce harm:**
- Prominent disclaimer banners everywhere
- Emergency routing that bypasses full pipeline and fast-tracks to call-911 advice
- Drug interaction checker before any treatment recommendation
- Evaluation framework that specifically tests for safe handling of emergency presentations

---

## What I'd Build Next

1. **RAG over clinical guidelines** — Replace DuckDuckGo search with a vector database of indexed clinical practice guidelines (NICE, AHA, USPSTF). Much more reliable than general web search.

2. **Structured output validation** — Add Pydantic models for each agent's output and validate before passing to the next node. Right now I do JSON parsing with fallbacks, which is fragile.

3. **Real drug interaction database** — The openFDA approach is good for a demo but misses a lot. DrugBank's API or RxNorm would give much better coverage.

4. **Multi-turn conversations** — The LangGraph checkpointer is set up for this, but the UI currently only does single-pass analysis. Adding follow-up questions ("Do you have a fever?" "Is the pain constant or intermittent?") would improve symptom coverage significantly.

5. **Uncertainty quantification** — Right now the model gives a severity classification without confidence bounds. I want to add a "confidence" field that makes it explicit when the model doesn't have enough information to be sure.

6. **HIPAA-compliant deployment** — All the patient data currently lives in memory or local JSON files. A real deployment would need a proper encrypted database, audit logging, and data minimization.

---

## License

MIT
