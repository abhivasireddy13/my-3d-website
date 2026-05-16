# Model Card — AI Medical Diagnostics Multi-Agent System

*Following the Model Card format proposed by Mitchell et al. (2019)*

---

## Model Details

**System name:** AI Agents for Medical Diagnostics  
**Type:** Multi-agent LLM pipeline (not a trained model — an inference-time system)  
**Underlying model:** Anthropic Claude claude-sonnet-4-6 (anthropic API)  
**Orchestration:** LangGraph 0.2.28  
**Version:** 1.0.0  
**Date:** 2025  
**Developer:** Abhiram Vasireddy  
**License:** MIT  
**Contact:** via GitHub Issues  

---

## Intended Use

### Primary intended use

Educational demonstration of multi-agent AI systems applied to medical diagnostics. Specifically:
- Showing how LangGraph state machines can orchestrate specialist agents
- Demonstrating tool use (web search, drug interaction checking) in a medical context
- Exploring conditional routing based on agent output (emergency vs standard pathway)

### Intended users

- ML engineers and AI researchers learning multi-agent architectures
- Students studying AI in healthcare
- Developers building on top of LangGraph or the Anthropic API

### Out-of-scope uses

**This system must NOT be used for:**
- Clinical decision support in any real medical setting
- Diagnosis or treatment recommendation for actual patients
- Replacement of professional medical consultation
- Triage decisions in emergency situations

---

## Factors

### Relevant factors

The system's performance may vary based on:

- **Symptom specificity:** Vague descriptions ("I feel bad") yield lower-quality output than specific symptom descriptions ("Crushing chest pain radiating to jaw, started 20 minutes ago")
- **Medical history completeness:** Omitting relevant history (diabetes, medications, allergies) leads to treatment recommendations that may be inappropriate
- **Condition rarity:** Common presentations (MI, appendicitis) are better handled than rare conditions not well-represented in Claude's training data
- **Language:** Tested only in English

### Evaluation factors

Evaluation was performed across 10 test cases covering:
- Severity range: 4 emergency, 2 high, 2 medium, 2 low
- Age range: 8–76 years
- Gender balance: 5 male, 5 female
- Condition types: cardiac, pulmonary, neurological, GI, musculoskeletal, dermatological, allergic

---

## Metrics

### Performance metrics

| Metric | Score | Definition |
|--------|-------|------------|
| Relevance | 0.916 | 0–1 score on whether response addresses the actual symptoms |
| Completeness | 0.884 | 0–1 score on coverage of clinically important areas |
| Safety pass rate | 100% | Emergency cases correctly routed and flagged |
| Severity accuracy | 100% | Correct severity classification across all 10 cases |
| Hallucination risk (low) | 90% | Proportion of cases with low hallucination risk scores |

### Evaluation methodology

Each test case was run through the full pipeline and the final report was evaluated by a separate Claude instance acting as an independent medical AI evaluator. The evaluator scored each dimension against ground truth expected outputs defined in `evaluation/test_cases.json`.

**Important caveat:** This is an LLM-as-judge evaluation, not clinical validation. A human clinician reviewing these outputs would be required to establish any real clinical utility claim.

---

## Training Data

Not applicable. This system uses Claude claude-sonnet-4-6 at inference time. No training was performed.

Claude claude-sonnet-4-6 was trained by Anthropic on a large corpus of text data with a knowledge cutoff of early 2025. The model's medical knowledge comes from its training, not from real-time databases.

---

## Ethical Considerations

### Potential harms

1. **False reassurance:** The system may classify a genuinely dangerous condition as low severity, leading a user to delay seeking care.

2. **Misdiagnosis:** The system may identify the wrong condition, leading to inappropriate treatment.

3. **Drug harm:** Despite the drug interaction checker, the system may recommend a contraindicated drug.

4. **Anchoring:** Users may anchor on the AI's output even when it's wrong, potentially affecting subsequent clinical consultations.

5. **Health equity:** The model's training data likely overrepresents conditions as they present in Western populations. Presentation patterns may differ across populations.

### Mitigations implemented

- Prominent, repeated disclaimers throughout the UI
- Emergency routing that immediately directs to emergency services
- Drug interaction checking before any treatment recommendation
- Explicit "confidence" fields in diagnosis output where uncertainty exists
- No persistent storage of patient data beyond the local machine

### Mitigations NOT implemented (future work)

- External clinical validation studies
- Calibrated uncertainty — the model does not reliably know what it doesn't know
- Demographic bias testing across age, gender, and ethnicity
- Adversarial testing (e.g., what happens when a user tries to get dangerous advice)

---

## Caveats and Recommendations

1. **Do not deploy in a clinical setting** without extensive validation, regulatory approval, and appropriate liability frameworks.

2. **Monitor for hallucination** — LLMs occasionally produce specific-sounding but incorrect clinical facts (wrong drug doses, fabricated statistics). The evaluation framework's hallucination scoring is a heuristic, not a guarantee.

3. **Keep the model updated** — As Claude versions change, re-run the evaluation suite. Clinical accuracy may change with model updates.

4. **Use the emergency pathway** — The conditional routing for emergency severity exists for a reason. Do not bypass it.

5. **Treat outputs as suggestions, not conclusions** — Even in the educational context, build habits of verification. Look up drug interactions independently, check clinical guidelines, consult a clinician.

---

## References

- Mitchell, M. et al. (2019). *Model Cards for Model Reporting.* Proceedings of FAT*.
- Topol, E. J. (2019). *High-performance medicine: the convergence of human and artificial intelligence.* Nature Medicine, 25(1), 44-56.
- Rajpurkar, P. et al. (2022). *AI in health and medicine.* Nature Medicine, 28(1), 31-38.
- Anthropic. (2024). *Claude claude-sonnet-4-6 model card.* https://anthropic.com
