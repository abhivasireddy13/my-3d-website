"""
Drug interaction checker.

Uses the openFDA API (free, no key needed) as primary source.
Falls back to a hardcoded table of the most dangerous common interactions
if openFDA is unavailable or returns nothing useful.

I looked at DrugBank and RxNorm APIs — both require registration or paid plans.
openFDA is maintained by the US government and updated regularly from FDA labeling data.
The endpoint we care about: https://api.fda.gov/drug/label.json

Limitation: openFDA has drug labels, not a structured interaction database.
We parse the "drug_interactions" section of labels, which is unstructured text.
A production system would use a proper interaction database like Lexicomp or Micromedex.
"""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

OPENFDA_BASE = "https://api.fda.gov/drug/label.json"

# Hardcoded critical interactions table — these are the ones that kill people
# Source: FDA MedWatch, clinical pharmacology references
# Format: frozenset({drug_a, drug_b}) -> severity + description
_CRITICAL_INTERACTIONS: dict[frozenset, dict] = {
    frozenset({"warfarin", "aspirin"}): {
        "severity": "HIGH",
        "description": "Increased bleeding risk. Combination increases anticoagulation significantly.",
    },
    frozenset({"warfarin", "ibuprofen"}): {
        "severity": "HIGH",
        "description": "NSAIDs displace warfarin from protein binding, elevating INR. Risk of serious hemorrhage.",
    },
    frozenset({"ssri", "maoi"}): {
        "severity": "CONTRAINDICATED",
        "description": "Risk of serotonin syndrome — potentially fatal. Minimum 14-day washout required.",
    },
    frozenset({"metformin", "contrast dye"}): {
        "severity": "HIGH",
        "description": "Hold metformin 48h before contrast procedures. Risk of lactic acidosis.",
    },
    frozenset({"statins", "gemfibrozil"}): {
        "severity": "HIGH",
        "description": "Markedly increased statin levels. Risk of rhabdomyolysis.",
    },
    frozenset({"clopidogrel", "omeprazole"}): {
        "severity": "MODERATE",
        "description": "Omeprazole inhibits CYP2C19, reducing clopidogrel activation by ~45%.",
    },
    frozenset({"ace inhibitor", "potassium"}): {
        "severity": "MODERATE",
        "description": "ACE inhibitors reduce potassium excretion. Risk of hyperkalemia with supplementation.",
    },
    frozenset({"sildenafil", "nitrates"}): {
        "severity": "CONTRAINDICATED",
        "description": "Severe hypotension. Absolute contraindication — do not use together.",
    },
    frozenset({"digoxin", "amiodarone"}): {
        "severity": "HIGH",
        "description": "Amiodarone increases digoxin levels by ~70%. Requires dose reduction and monitoring.",
    },
    frozenset({"lithium", "nsaids"}): {
        "severity": "HIGH",
        "description": "NSAIDs reduce renal lithium clearance, raising plasma levels. Risk of toxicity.",
    },
}


def _normalize(drug: str) -> str:
    return drug.lower().strip()


def _check_hardcoded(new_drug: str, current_meds: list[str]) -> list[dict]:
    """Check against the hardcoded critical interaction table."""
    new_norm = _normalize(new_drug)
    findings = []

    for interaction_pair, details in _CRITICAL_INTERACTIONS.items():
        pair_list = list(interaction_pair)
        # check if new drug matches one side and any current med matches the other
        for d1, d2 in [(pair_list[0], pair_list[1]), (pair_list[1], pair_list[0])]:
            if d1 in new_norm or new_norm in d1:
                for med in current_meds:
                    med_norm = _normalize(med)
                    if d2 in med_norm or med_norm in d2:
                        findings.append({
                            "drug_pair": f"{new_drug} + {med}",
                            "severity": details["severity"],
                            "description": details["description"],
                            "source": "FDA clinical pharmacology reference",
                        })

    return findings


def _query_openfda(drug_name: str) -> str:
    """Fetch drug interaction text from openFDA label database."""
    try:
        encoded = urllib.parse.quote(f'"{drug_name}"')
        url = f"{OPENFDA_BASE}?search=openfda.generic_name:{encoded}&limit=1"

        req = urllib.request.Request(url, headers={"User-Agent": "MedicalDiagnosticAgent/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())

        results = data.get("results", [])
        if not results:
            return ""

        label = results[0]
        # drug_interactions field contains the unstructured interaction text from the label
        interactions = label.get("drug_interactions", [])
        return " ".join(interactions)[:2000] if interactions else ""

    except Exception as e:
        logger.warning(f"openFDA query failed for {drug_name!r}: {e}")
        return ""


def check_drug_interactions(new_drug: str, current_medications: list[str]) -> str:
    """
    Check for interactions between a new drug and the patient's current medications.
    Returns a formatted string describing any interactions found.
    """
    if not current_medications:
        return f"No current medications to check against {new_drug}."

    findings = _check_hardcoded(new_drug, current_medications)

    # also query openFDA for the new drug's label
    fda_text = _query_openfda(new_drug)
    if fda_text:
        # check if any current med name appears in the interaction text
        for med in current_medications:
            med_norm = _normalize(med)
            if med_norm in fda_text.lower():
                findings.append({
                    "drug_pair": f"{new_drug} + {med}",
                    "severity": "MODERATE (from FDA label)",
                    "description": f"FDA label for {new_drug} mentions {med} in drug interactions section.",
                    "source": "openFDA drug label",
                })

    if not findings:
        return (
            f"No known critical interactions found between {new_drug} "
            f"and current medications: {', '.join(current_medications)}. "
            "Note: This check covers common interactions only — always verify with a pharmacist."
        )

    lines = [f"⚠️ Drug Interaction Check: {new_drug} vs current medications\n"]
    for f in findings:
        lines.append(
            f"  [{f['severity']}] {f['drug_pair']}\n"
            f"  → {f['description']}\n"
            f"  Source: {f['source']}\n"
        )

    lines.append("Consult a pharmacist or physician before prescribing.")
    return "\n".join(lines)
