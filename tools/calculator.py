"""
Medical calculators — BMI, dosage estimation, vital sign assessment.

These are deterministic calculations that don't need an LLM.
Offloading them to a tool keeps the LLM focused on reasoning,
not arithmetic — which LLMs are notoriously bad at anyway.
"""

from __future__ import annotations

from typing import Optional


# ── BMI ───────────────────────────────────────────────────────────────────────

def calculate_bmi(weight_kg: float, height_cm: float) -> dict:
    """Calculate BMI and return classification using WHO categories."""
    if height_cm <= 0 or weight_kg <= 0:
        return {"error": "Invalid height or weight values"}

    height_m = height_cm / 100.0
    bmi = weight_kg / (height_m ** 2)
    bmi = round(bmi, 1)

    if bmi < 18.5:
        category = "Underweight"
        note = "Nutritional assessment recommended"
    elif bmi < 25.0:
        category = "Normal weight"
        note = "Maintain current lifestyle"
    elif bmi < 30.0:
        category = "Overweight"
        note = "Lifestyle modification recommended"
    elif bmi < 35.0:
        category = "Obese (Class I)"
        note = "Weight management intervention recommended"
    elif bmi < 40.0:
        category = "Obese (Class II)"
        note = "Structured weight loss program recommended"
    else:
        category = "Obese (Class III)"
        note = "Multidisciplinary obesity treatment recommended"

    return {
        "bmi": bmi,
        "category": category,
        "note": note,
        "weight_kg": weight_kg,
        "height_cm": height_cm,
    }


# ── Vital sign assessment ─────────────────────────────────────────────────────

def assess_vitals(
    heart_rate: Optional[int] = None,
    systolic_bp: Optional[int] = None,
    diastolic_bp: Optional[int] = None,
    temperature_c: Optional[float] = None,
    respiratory_rate: Optional[int] = None,
    spo2: Optional[float] = None,
    age: Optional[int] = None,
) -> str:
    """
    Assess vital signs and flag abnormalities.
    Returns a formatted string with findings.
    """
    findings = []
    alerts = []

    if heart_rate is not None:
        if heart_rate < 50:
            alerts.append(f"⚠️ Bradycardia: HR {heart_rate} bpm")
        elif heart_rate > 100:
            if heart_rate > 150:
                alerts.append(f"🚨 Severe tachycardia: HR {heart_rate} bpm")
            else:
                alerts.append(f"⚠️ Tachycardia: HR {heart_rate} bpm")
        else:
            findings.append(f"HR {heart_rate} bpm (normal)")

    if systolic_bp is not None and diastolic_bp is not None:
        if systolic_bp >= 180 or diastolic_bp >= 120:
            alerts.append(f"🚨 Hypertensive crisis: {systolic_bp}/{diastolic_bp} mmHg")
        elif systolic_bp >= 140 or diastolic_bp >= 90:
            alerts.append(f"⚠️ Hypertension: {systolic_bp}/{diastolic_bp} mmHg")
        elif systolic_bp < 90:
            alerts.append(f"🚨 Hypotension: {systolic_bp}/{diastolic_bp} mmHg")
        else:
            findings.append(f"BP {systolic_bp}/{diastolic_bp} mmHg (normal)")

    if temperature_c is not None:
        if temperature_c >= 39.5:
            alerts.append(f"🚨 High fever: {temperature_c}°C")
        elif temperature_c >= 38.0:
            alerts.append(f"⚠️ Fever: {temperature_c}°C")
        elif temperature_c < 36.0:
            alerts.append(f"⚠️ Hypothermia: {temperature_c}°C")
        else:
            findings.append(f"Temp {temperature_c}°C (normal)")

    if respiratory_rate is not None:
        if respiratory_rate > 20:
            alerts.append(f"⚠️ Tachypnea: RR {respiratory_rate}/min")
        elif respiratory_rate < 12:
            alerts.append(f"⚠️ Bradypnea: RR {respiratory_rate}/min")
        else:
            findings.append(f"RR {respiratory_rate}/min (normal)")

    if spo2 is not None:
        if spo2 < 90:
            alerts.append(f"🚨 Critical hypoxemia: SpO2 {spo2}%")
        elif spo2 < 94:
            alerts.append(f"⚠️ Hypoxemia: SpO2 {spo2}%")
        else:
            findings.append(f"SpO2 {spo2}% (normal)")

    output_lines = []
    if alerts:
        output_lines.append("VITAL SIGN ALERTS:")
        output_lines.extend(alerts)
    if findings:
        output_lines.append("Normal values: " + " | ".join(findings))

    return "\n".join(output_lines) if output_lines else "No vital signs provided."


# ── Dosage estimation ─────────────────────────────────────────────────────────
# These are rough reference values — NOT prescribing recommendations.
# A real system would use a proper drug database with weight-based dosing algorithms.

_DOSAGE_REFERENCE: dict[str, dict] = {
    "amoxicillin": {
        "adult": "500mg every 8h or 875mg every 12h (oral)",
        "pediatric": "25–45 mg/kg/day divided every 8–12h",
        "renal_note": "Reduce dose if GFR < 30",
        "max_daily": "3g (adult)",
    },
    "ibuprofen": {
        "adult": "400–800mg every 6–8h with food",
        "pediatric": "5–10 mg/kg/dose every 6–8h (max 40 mg/kg/day)",
        "renal_note": "Avoid if GFR < 30. Use with caution in elderly.",
        "max_daily": "3200mg (adult)",
    },
    "metformin": {
        "adult": "Start 500mg twice daily with meals; titrate to 2000mg/day",
        "pediatric": "Not indicated under 10 years",
        "renal_note": "Contraindicated if eGFR < 30. Hold before contrast procedures.",
        "max_daily": "2550mg",
    },
    "lisinopril": {
        "adult": "Start 5–10mg once daily; titrate to 20–40mg",
        "pediatric": "0.07 mg/kg once daily (max 5mg starter dose)",
        "renal_note": "Start at lower dose. Monitor potassium and creatinine.",
        "max_daily": "40mg",
    },
    "omeprazole": {
        "adult": "20–40mg once daily before meals",
        "pediatric": "0.7–3.3 mg/kg/day",
        "renal_note": "No adjustment needed",
        "max_daily": "40mg (standard), 80mg (severe GERD)",
    },
    "prednisone": {
        "adult": "Varies widely by indication (5–60mg/day)",
        "pediatric": "1–2 mg/kg/day (max 40mg)",
        "renal_note": "No significant adjustment needed",
        "max_daily": "Indication-dependent",
    },
}


def calculate_dosage(
    drug: str,
    patient_age: int,
    patient_weight_kg: Optional[float] = None,
    condition: str = "",
) -> str:
    """
    Return reference dosage information for a drug given patient parameters.
    This is reference data, not a prescription.
    """
    drug_norm = drug.lower().strip()
    ref = _DOSAGE_REFERENCE.get(drug_norm)

    if ref is None:
        return (
            f"No reference dosage data for '{drug}' in this system. "
            "Consult clinical pharmacology references (e.g., Lexicomp, Micromedex) "
            "or a pharmacist for accurate dosing."
        )

    is_pediatric = patient_age < 18
    dose_info = ref["pediatric"] if is_pediatric else ref["adult"]

    weight_note = ""
    if patient_weight_kg and is_pediatric and "mg/kg" in dose_info:
        # very rough calculation for informational purposes only
        low_dose = patient_weight_kg * 5
        high_dose = patient_weight_kg * 10
        weight_note = f"\nEstimated range for {patient_weight_kg}kg: {low_dose:.0f}–{high_dose:.0f}mg/day (verify with prescriber)"

    return (
        f"Reference dosing for {drug} | Patient age: {patient_age}y\n"
        f"Dose: {dose_info}\n"
        f"Renal considerations: {ref['renal_note']}\n"
        f"Max daily: {ref['max_daily']}"
        f"{weight_note}\n"
        f"⚠️ These are reference values only. Prescribing decisions require clinical judgment."
    )
