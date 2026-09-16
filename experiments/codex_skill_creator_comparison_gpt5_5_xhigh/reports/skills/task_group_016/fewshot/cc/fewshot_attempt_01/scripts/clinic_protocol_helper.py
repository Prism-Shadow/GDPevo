#!/usr/bin/env python3
"""Draft protocol-bound JSON for synthetic clinic runtime tasks.

This stdlib-only helper fetches the target case and applies reusable protocol
rules inferred from the staged examples. Treat its output as a draft: inspect
the live protocol, the template, and the prompt before final submission.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def fetch_json(base_url: str, path: str) -> dict[str, Any]:
    base = base_url.rstrip("/")
    url = f"{base}{path}"
    try:
        with urlopen(url, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise SystemExit(f"failed to fetch {url}: {exc}") from exc


def load_template(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    try:
        return json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"failed to read template {path}: {exc}") from exc


def text(value: Any) -> str:
    return "" if value is None else str(value).lower()


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def iso_z(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def next_morning_8(current: str | None) -> str | None:
    dt = parse_time(current)
    if not dt:
        return None
    nxt = (dt.astimezone(timezone.utc) + timedelta(days=1)).date()
    return f"{nxt.isoformat()}T08:00:00Z"


def field_map(case: dict[str, Any]) -> dict[str, str]:
    return {
        item.get("finding_key", ""): item.get("finding_value", "")
        for item in case.get("findings", [])
        if item.get("finding_key")
    }


def finding_source(case: dict[str, Any], key: str) -> str | None:
    for item in case.get("findings", []):
        if item.get("finding_key") == key:
            return item.get("source_id")
    return None


def observations(
    case: dict[str, Any],
    *,
    code: str | None = None,
    status: str | None = None,
    patient_id: str | None = None,
) -> list[dict[str, Any]]:
    rows = case.get("observations", [])
    if code is not None:
        rows = [r for r in rows if r.get("code") == code]
    if status is not None:
        rows = [r for r in rows if r.get("status") == status]
    if patient_id is not None:
        rows = [r for r in rows if r.get("patient_id") == patient_id]
    return rows


def latest(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    return sorted(rows, key=lambda r: (r.get("effective_time") or "", r.get("observation_id") or ""))[-1]


def active_allergy_classes(case: dict[str, Any]) -> list[str]:
    classes: set[str] = set()
    for allergy in case.get("allergies", []):
        if allergy.get("status") != "active":
            continue
        name = text(allergy.get("allergen"))
        if "penicillin" in name or "amoxicillin" in name:
            classes.add("penicillin")
        if "sulfa" in name or "sulfonamide" in name:
            classes.add("sulfonamide")
        if any(term in name for term in ["macrolide", "azithro", "clarithro", "erythro"]):
            classes.add("macrolide")
        if any(term in name for term in ["tetracycline", "doxy"]):
            classes.add("tetracycline")
    order = ["penicillin", "sulfonamide", "macrolide", "tetracycline"]
    return [item for item in order if item in classes]


def active_problem_text(case: dict[str, Any]) -> str:
    return " ".join(
        text(p.get("name")) + " " + text(p.get("code"))
        for p in case.get("problems", [])
        if p.get("status") == "active"
    )


def active_med_count(case: dict[str, Any]) -> int:
    registry = case.get("care_registry") or {}
    if registry.get("medication_count") is not None:
        return int(registry["medication_count"])
    return sum(1 for med in case.get("medications", []) if med.get("status") == "active")


def current_time(case: dict[str, Any]) -> str | None:
    return field_map(case).get("current_time")


def case_patient_id(case: dict[str, Any]) -> str | None:
    return (case.get("case") or {}).get("patient_id") or (case.get("patient") or {}).get("patient_id")


def evidence_case_first(case_id: str, *ids: str | None) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in [case_id, *ids]:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def build_respiratory(case: dict[str, Any], task_id: str, case_id: str) -> dict[str, Any]:
    patient_id = case_patient_id(case)
    findings = field_map(case)
    obs = case.get("observations", [])
    final_obs = [o for o in obs if o.get("status") == "final"]
    spo2_values = [
        float(o["value_number"])
        for o in final_obs
        if o.get("code") in {"59408-5", "PULSE_OX_RECHECK"} and o.get("value_number") is not None
    ]
    min_spo2 = min(spo2_values) if spo2_values else None
    rr = latest([o for o in final_obs if o.get("code") == "9279-1"])
    sbp = latest([o for o in final_obs if o.get("code") == "8480-6"])
    rr_value = float(rr["value_number"]) if rr and rr.get("value_number") is not None else None
    sbp_value = float(sbp["value_number"]) if sbp and sbp.get("value_number") is not None else None
    cxr_text = " ".join(text(i.get("impression")) for i in case.get("imaging", []))
    cxr_text += " " + " ".join(text(o.get("value_text")) for o in final_obs if o.get("code") == "CXR-2V")
    pneumonia = any(term in cxr_text for term in ["consolidation", "infiltrate", "airspace"])
    confusion = "absent" not in text(findings.get("confusion")) and bool(findings.get("confusion"))
    multilobar = "multilobar" in cxr_text and "no multilobar" not in cxr_text
    high = bool(
        (min_spo2 is not None and min_spo2 < 90)
        or (rr_value is not None and rr_value >= 30)
        or (sbp_value is not None and sbp_value < 90)
        or confusion
        or multilobar
    )

    red_flags: list[str] = []
    if min_spo2 is not None and min_spo2 < 90:
        red_flags.append("hypoxemia_below_90")
    elif min_spo2 is not None and 92 <= min_spo2 <= 93:
        red_flags.append("hypoxemia_92_93")
    if "absent" not in text(findings.get("pleuritic_chest_pain")) and findings.get("pleuritic_chest_pain"):
        red_flags.append("pleuritic_chest_pain")
    if rr_value is not None and rr_value >= 30:
        red_flags.append("respiratory_distress")
    if confusion:
        red_flags.append("confusion")
    if "hemoptysis" in " ".join(text(v) for v in findings.values()):
        red_flags.append("hemoptysis")
    if "persistent" in text(findings.get("fever")):
        red_flags.append("persistent_fever")

    tests = ["CXR-2V", "SARS_FLU_RSV_PCR"]
    if min_spo2 is not None and min_spo2 <= 93:
        tests.append("PULSE_OX_RECHECK")
    if high:
        tests.append("CBC_BASIC")

    allergies = active_allergy_classes(case)
    if high:
        med = {
            "antibiotic_strategy": "defer_antibiotic_selection_to_ed",
            "medication": None,
            "dose": None,
            "route": None,
            "frequency": None,
            "duration_days": None,
            "avoid_allergens": allergies,
        }
    elif pneumonia:
        if "tetracycline" not in allergies and ("penicillin" in allergies or "sulfonamide" in allergies):
            med = {
                "antibiotic_strategy": "doxycycline_outpatient",
                "medication": "doxycycline",
                "dose": "100 mg",
                "route": "PO",
                "frequency": "BID",
                "duration_days": 5,
                "avoid_allergens": allergies,
            }
        else:
            med = {
                "antibiotic_strategy": "standard_outpatient_beta_lactam_plus_macrolide",
                "medication": "amoxicillin-clavulanate plus azithromycin",
                "dose": "standard outpatient CAP dosing",
                "route": "PO",
                "frequency": "per protocol",
                "duration_days": 5,
                "avoid_allergens": allergies,
            }
    else:
        med = {
            "antibiotic_strategy": "supportive_care_no_antibiotic",
            "medication": None,
            "dose": None,
            "route": None,
            "frequency": None,
            "duration_days": None,
            "avoid_allergens": allergies,
        }

    img_id = (case.get("imaging") or [{}])[0].get("imaging_id")
    spo2_id = (latest([o for o in final_obs if o.get("code") in {"59408-5", "PULSE_OX_RECHECK"}]) or {}).get("observation_id")
    return {
        "task_id": task_id,
        "case_id": case_id,
        "patient_id": patient_id,
        "primary_assessment": "community_acquired_pneumonia" if pneumonia else "viral_upper_respiratory_infection",
        "risk_level": "high" if high else ("moderate" if red_flags else "low"),
        "disposition": "ed_transfer" if high else "outpatient_close_followup",
        "red_flags": dedupe(red_flags),
        "recommended_tests": dedupe(tests),
        "medication_plan": med,
        "stabilization_actions": ["supplemental_oxygen", "urgent_ed_transfer"] if high else [],
        "follow_up": {"timeframe_hours": 0 if high else 48, "route": "emergency_department" if high else "primary_care_recheck"},
        "return_precautions": [
            "chest_pain",
            "confusion",
            "hemoptysis",
            "hypoxia",
            "persistent_fever",
            "worsening_shortness_of_breath",
        ],
        "evidence_ids": evidence_case_first(case_id, img_id, spo2_id),
        "safety_checks": {
            "no_penicillin_or_sulfa": not any(a in {"penicillin", "sulfonamide"} for a in allergies) or med["antibiotic_strategy"] != "standard_outpatient_beta_lactam_plus_macrolide",
            "no_normal_cxr_claim": True,
            "no_clear_lungs_claim": True,
        },
    }


def build_head(case: dict[str, Any], task_id: str, case_id: str) -> dict[str, Any]:
    patient_id = case_patient_id(case)
    findings = field_map(case)
    all_text = " ".join(text(v) for v in findings.values())
    final_obs = [o for o in case.get("observations", []) if o.get("status") == "final"]
    gcs_obs = latest([o for o in final_obs if o.get("code") == "9269-2"])
    gcs = float(gcs_obs["value_number"]) if gcs_obs and gcs_obs.get("value_number") is not None else 15
    vomit_obs = latest([o for o in final_obs if o.get("code") == "HEAD-VOMIT-COUNT"])
    vomit_count = float(vomit_obs["value_number"]) if vomit_obs and vomit_obs.get("value_number") is not None else None
    loc_obs = latest([o for o in final_obs if o.get("code") == "HEAD-LOC-SECONDS"])
    loc_seconds = float(loc_obs["value_number"]) if loc_obs and loc_obs.get("value_number") is not None else None
    neuro = latest([o for o in final_obs if o.get("code") == "NEURO-COORD"])
    neuro_text = text(neuro.get("value_text")) if neuro else ""

    repeated_vomiting = (vomit_count is not None and vomit_count >= 2) or "repeated vomiting" in all_text
    loc_present = (loc_seconds is not None and loc_seconds > 0) or ("loss of consciousness" in all_text and "absent" not in text(findings.get("loss_of_consciousness")))
    focal_weakness = "focal weakness" in all_text and "no focal weakness" not in all_text
    seizure = "seizure" in all_text and "no seizure" not in all_text and "absent" not in text(findings.get("seizure"))
    worsening_headache = "worsening" in text(findings.get("headache")) or "severe headache" in all_text
    basilar = "basilar" in all_text
    photophobia = "photophobia" in all_text and "absent" not in text(findings.get("photophobia"))
    urgent = bool(gcs < 15 or repeated_vomiting or seizure or focal_weakness or worsening_headache or basilar or (loc_seconds or 0) >= 60)

    red_flags: list[str] = []
    if findings.get("mechanism") or "fall" in all_text or "impact" in all_text:
        red_flags.append("head_impact")
    if "mild" in text(findings.get("nausea")):
        red_flags.append("mild_nausea")
    if neuro and "mild" in neuro_text and not focal_weakness:
        red_flags.append("coordination_symptom_observe")
    if loc_present:
        red_flags.append("loss_of_consciousness")
    if repeated_vomiting:
        red_flags.append("repeated_vomiting")
    if seizure:
        red_flags.append("seizure")
    if focal_weakness:
        red_flags.append("focal_weakness")
    if worsening_headache:
        red_flags.append("worsening_headache")
    if basilar:
        red_flags.append("basilar_skull_signs")
    if photophobia:
        red_flags.append("photophobia")

    absent: list[str] = []
    if not loc_present and (loc_seconds == 0 or "absent" in text(findings.get("loss_of_consciousness"))):
        absent.append("loss_of_consciousness")
    if not repeated_vomiting and (vomit_count == 0 or "absent" in text(findings.get("vomiting"))):
        absent.append("repeated_vomiting")
    if not seizure and ("no seizure" in all_text or "absent" in text(findings.get("seizure"))):
        absent.append("seizure")
    if not focal_weakness and "no focal weakness" in all_text:
        absent.append("focal_weakness")
    if not worsening_headache and "worsening headache absent" in all_text:
        absent.append("worsening_headache")
    if not basilar and "basilar skull signs absent" in all_text:
        absent.append("basilar_skull_signs")
    if not photophobia and "photophobia absent" in all_text:
        absent.append("photophobia")

    symptomatic = any(flag in red_flags for flag in ["mild_nausea", "coordination_symptom_observe", "loss_of_consciousness", "photophobia"])
    if urgent:
        primary = "severe_head_injury"
    elif symptomatic and not loc_present:
        primary = "mild_traumatic_brain_injury_without_loss_of_consciousness"
    elif symptomatic:
        primary = "pediatric_head_injury_with_concussion_features"
    else:
        primary = "minor_head_injury_no_concussion_features"

    restrictions = ["normal_activity_as_tolerated"]
    if symptomatic or urgent:
        restrictions = [
            "relative_cognitive_physical_rest",
            "return_to_learn_accommodations",
            "no_high_risk_sports_until_cleared",
            "no_driving_until_cleared" if urgent else "no_driving_until_symptom_free",
        ]

    return {
        "task_id": task_id,
        "case_id": case_id,
        "patient_id": patient_id,
        "primary_assessment": primary,
        "risk_tier": "high" if urgent else ("intermediate" if symptomatic else "low"),
        "disposition": "ed_evaluation_ct_consideration" if urgent else "home_observation_with_followup",
        "imaging_recommendation": "urgent_ct" if urgent else "no_immediate_ct",
        "red_flags": dedupe(red_flags),
        "absent_red_flags": dedupe(absent),
        "restrictions": restrictions,
        "follow_up": {
            "timeframe_hours": 24 if urgent else (48 if symptomatic else 0),
            "route": "emergency_department" if urgent else ("primary_care_or_concussion_recheck" if symptomatic else "return_if_worse_only"),
        },
        "evidence_ids": evidence_case_first(case_id, gcs_obs.get("observation_id") if gcs_obs else None, neuro.get("observation_id") if neuro else None),
        "safety_checks": {
            "no_false_loc": not loc_present or "loss_of_consciousness" in red_flags,
            "no_false_vomiting": not repeated_vomiting or "repeated_vomiting" in red_flags,
            "no_false_photophobia": not photophobia or "photophobia" in red_flags,
        },
    }


def build_potassium(case: dict[str, Any], task_id: str, case_id: str) -> dict[str, Any]:
    patient_id = case_patient_id(case)
    ks = observations(case, code="K", status="final", patient_id=patient_id)
    k = latest(ks)
    if not k:
        raise SystemExit("no final serum potassium observation found for target patient")
    value = float(k["value_number"])
    findings = field_map(case)
    problems = active_problem_text(case)
    egfr_obs = latest(observations(case, code="33914-3", status="final", patient_id=patient_id))
    egfr_value = int(round(float(egfr_obs["value_number"]))) if egfr_obs and egfr_obs.get("value_number") is not None else None
    ecg = latest(observations(case, code="ECG-SUMMARY", status="final", patient_id=patient_id))
    ecg_text = text(ecg.get("value_text")) if ecg else text(findings.get("ecg"))
    symptom_text = text(findings.get("symptoms"))
    dialysis = "dialysis" in problems or "esrd" in problems
    arrhythmia_symptoms = any(term in symptom_text for term in ["palpitations", "syncope", "arrhythmia", "severe weakness"]) and "no " not in symptom_text
    ecg_abnormal = bool(ecg_text and "normal" not in ecg_text)
    severe_renal = egfr_value is not None and egfr_value < 30
    urgent = value < 3.0 or dialysis or arrhythmia_symptoms or ecg_abnormal or severe_renal
    replacement = value < 3.5

    if urgent and replacement:
        plan = "urgent_escalation"
        oral_dose = None
        med = {"ndc": None, "medication": None, "route": "per_urgent_protocol", "frequency": "per_urgent_protocol", "status": "defer_to_urgent_clinician"}
        urgent_actions = ["urgent_clinician_notification", "ekg_now", "telemetry_or_ed_evaluation"]
        follow = {"loinc": "2823-3", "scheduled_time": None}
    elif replacement:
        plan = "routine_oral_repletion"
        oral_dose = int(round(((3.5 - value) / 0.1) * 10 / 10) * 10)
        med = {"ndc": "40032-917-01", "medication": "potassium chloride oral", "route": "PO", "frequency": "once", "status": "recommended"}
        urgent_actions = []
        follow = {"loinc": "2823-3", "scheduled_time": next_morning_8(current_time(case))}
    else:
        plan = "no_replacement"
        oral_dose = None
        med = {"ndc": None, "medication": None, "route": None, "frequency": None, "status": "not_recommended"}
        urgent_actions = []
        follow = {"loinc": None, "scheduled_time": None}

    evidence = [k.get("observation_id")]
    if egfr_obs:
        evidence.append(egfr_obs.get("observation_id"))
    if urgent and ecg:
        evidence.append(ecg.get("observation_id"))

    return {
        "task_id": task_id,
        "case_id": case_id,
        "patient_id": patient_id,
        "current_time": current_time(case),
        "latest_potassium": {
            "observation_id": k.get("observation_id"),
            "value_mmol_l": round(value, 1),
            "effective_time": k.get("effective_time"),
        },
        "replacement_required": replacement,
        "potassium_plan": plan,
        "oral_dose_mEq": oral_dose,
        "medication_order": med,
        "follow_up_lab": follow,
        "urgent_actions": urgent_actions,
        "contraindications": {
            "dialysis_dependent": dialysis,
            "arrhythmia_symptoms": arrhythmia_symptoms,
            "egfr": egfr_value,
        },
        "evidence_ids": dedupe([x for x in evidence if x]),
    }


def build_care_management(case: dict[str, Any], task_id: str, case_id: str) -> dict[str, Any]:
    patient_id = case_patient_id(case)
    registry = case.get("care_registry") or {}
    findings = field_map(case)
    problems = active_problem_text(case)
    final_obs = [o for o in case.get("observations", []) if o.get("status") == "final"]
    risk_score = float(registry.get("risk_score") or findings.get("registry_risk_score") or 0)
    a1c = latest([o for o in final_obs if o.get("code") == "4548-4"])
    phos = latest([o for o in final_obs if o.get("code") == "2777-1"])
    sbp = latest([o for o in final_obs if o.get("code") == "8480-6"])
    dbp = latest([o for o in final_obs if o.get("code") == "8462-4"])
    phq9 = latest([o for o in final_obs if o.get("code") == "PHQ-9"])
    med_count = active_med_count(case)
    bp = None
    if sbp and dbp and sbp.get("value_number") is not None and dbp.get("value_number") is not None:
        bp = f"{int(round(float(sbp['value_number'])) )}/{int(round(float(dbp['value_number'])) )}"

    priority: list[str] = []
    if a1c and float(a1c.get("value_number") or 0) >= 9:
        priority.append("uncontrolled_diabetes")
    if "end stage renal" in problems or "n18.6" in problems or "dialysis" in problems:
        priority.append("esrd_on_hemodialysis")
    elif "stage 4" in problems or "n18.4" in problems:
        priority.append("chronic_kidney_disease_stage_4")
    if "heart failure" in problems and "volume overload" in " ".join(text(v) for v in findings.values()):
        priority.append("hfpEF_post_volume_overload")
    elif "heart failure" in problems and registry.get("recent_admission_date"):
        priority.append("heart_failure_recent_admission")
    if phos and float(phos.get("value_number") or 0) > 5:
        priority.append("hyperphosphatemia")
    if "hypertension" in problems or (sbp and float(sbp.get("value_number") or 0) >= 140):
        priority.append("hypertension")
    if med_count >= 10:
        priority.append("polypharmacy")

    sdoh_domains = {text(s.get("domain")) for s in case.get("sdoh", []) if s.get("severity") in {"moderate", "severe"}}
    referrals: list[str] = []
    if "dialysis" in problems or registry.get("dialysis_schedule"):
        referrals.append("dialysis_care_coordination")
    if med_count >= 10 or any("insulin" in text(m.get("name")) for m in case.get("medications", [])):
        referrals.append("pharmacist")
    if len(sdoh_domains) >= 1:
        referrals.append("social_worker")
    if "transportation" in sdoh_domains:
        referrals.append("transportation_benefits")

    member_needed: list[str] = []
    if "transportation" in sdoh_domains:
        member_needed.append("transportation_barrier")
    if "financial" in sdoh_domains:
        member_needed.append("financial_medication_barrier")
    if "dialysis_fatigue" in findings:
        member_needed.append("dialysis_fatigue")

    escalations: list[str] = []
    if "dialysis" in problems or "volume overload" in " ".join(text(v) for v in findings.values()):
        escalations.append("missed_dialysis_or_volume_overload")
    if phq9:
        escalations.append("phq9_increase_or_item9_positive")
    if sbp and float(sbp.get("value_number") or 0) >= 180:
        escalations.append("hypertensive_urgency")

    chart_facts = ["risk_score"]
    if a1c:
        chart_facts.append("hba1c_percent")
    if phos:
        chart_facts.append("phosphorus_mg_dl")
    if med_count:
        chart_facts.append("active_medication_count")
    if sbp and float(sbp.get("value_number") or 0) >= 180:
        chart_facts.append("blood_pressure")

    return {
        "task_id": task_id,
        "case_id": case_id,
        "patient_id": patient_id,
        "risk_tier": "high" if risk_score >= 0.75 else ("moderate" if risk_score >= 0.4 else "low"),
        "program": "complex_care_management" if risk_score >= 0.75 and len(priority) >= 3 else ("routine_case_management" if risk_score >= 0.4 else "not_eligible"),
        "priority_problems": dedupe(priority),
        "numeric_anchors": {
            "risk_score": round(risk_score, 2),
            "hba1c_percent": round(float(a1c.get("value_number")), 1) if a1c else None,
            "phosphorus_mg_dl": round(float(phos.get("value_number")), 1) if phos else None,
            "blood_pressure": bp,
            "active_medication_count": med_count,
        },
        "referrals": dedupe(referrals),
        "outreach_stance": "permission_based_plain_language" if "permission" in text(findings.get("outreach_posture")) or "reluctant" in " ".join(text(v) for v in findings.values()) else "standard_scripted_outreach",
        "care_plan_minima": {
            "min_problem_count": 3 if risk_score >= 0.75 else 1,
            "weekly_follow_up": risk_score >= 0.75,
            "requires_member_stated_priority": risk_score >= 0.75,
            "min_disciplines": 2 if risk_score >= 0.75 else 1,
        },
        "escalation_conditions": dedupe(escalations),
        "source_provenance": {
            "chart_facts": dedupe(chart_facts),
            "member_disclosure_needed": dedupe(member_needed),
        },
    }


def build_observation_window(case: dict[str, Any], task_id: str, case_id: str) -> dict[str, Any]:
    patient_id = case_patient_id(case)
    findings = field_map(case)
    target_code = findings.get("target_code") or "K"
    start_s = findings.get("window_start")
    end_s = findings.get("window_end")
    start = parse_time(start_s)
    end = parse_time(end_s)
    if not start or not end:
        raise SystemExit("window_start/window_end missing or invalid")

    same_patient = [o for o in case.get("observations", []) if o.get("patient_id") == patient_id]

    def in_window(obs: dict[str, Any]) -> bool:
        dt = parse_time(obs.get("effective_time"))
        return bool(dt and start <= dt < end)

    matched = [
        o for o in same_patient
        if o.get("code") == target_code and o.get("status") == "final" and in_window(o)
    ]
    matched = sort_obs(matched)
    excluded = [
        o for o in same_patient
        if not (o.get("code") == target_code and o.get("status") == "final" and in_window(o))
        and (o.get("code") == target_code or in_window(o))
    ]
    excluded = sort_obs(excluded)
    latest_final = matched[-1] if matched else None
    value = float(latest_final["value_number"]) if latest_final and latest_final.get("value_number") is not None else None
    if value is None:
        gate = "no_final_lab_in_window"
        repeat = {"recommended": True, "scheduled_time": next_morning_8(end_s)}
    elif value < 3.0:
        gate = "recent_final_critical_or_urgent"
        repeat = {"recommended": True, "scheduled_time": next_morning_8(end_s)}
    elif value < 3.5:
        gate = "recent_final_low_repletion_needed"
        repeat = {"recommended": True, "scheduled_time": next_morning_8(end_s)}
    else:
        gate = "satisfies_recent_final_normal"
        repeat = {"recommended": False, "scheduled_time": None}

    return {
        "task_id": task_id,
        "case_id": case_id,
        "patient_id": patient_id,
        "window": {"from": start_s, "to": end_s},
        "target_code": target_code,
        "lab_found": bool(matched),
        "matched_observation_ids": [o.get("observation_id") for o in matched],
        "excluded_observation_ids": [o.get("observation_id") for o in excluded],
        "latest_final": None if latest_final is None else {
            "observation_id": latest_final.get("observation_id"),
            "value_mmol_l": round(value, 1) if value is not None else None,
            "effective_time": latest_final.get("effective_time"),
        },
        "protocol_gate": gate,
        "repeat_lab": repeat,
    }


def sort_obs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda r: (r.get("effective_time") or "", r.get("observation_id") or ""))


def dedupe(items: list[Any]) -> list[Any]:
    seen: set[Any] = set()
    out: list[Any] = []
    for item in items:
        if item is None or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def required_keys(template: dict[str, Any]) -> list[str]:
    for key in ["required_top_level_keys", "required_keys"]:
        if isinstance(template.get(key), list):
            return [str(item) for item in template[key]]
    return []


def expected_from_template(template: dict[str, Any], field: str) -> str | None:
    for section in ["fields", "field_specification"]:
        spec = (template.get(section) or {}).get(field) or {}
        for name in ["expected_constant", "required_value"]:
            if spec.get(name):
                return str(spec[name])
    return None


def infer_task_id(template: dict[str, Any], template_path: str | None, explicit: str | None) -> str:
    if explicit:
        return explicit
    value = expected_from_template(template, "task_id")
    if value:
        return value
    if template_path:
        match = re.search(r"(?:train|test)_\d+", template_path)
        if match:
            return match.group(0)
    return "task"


def filter_to_template(answer: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    keys = required_keys(template)
    if not keys:
        return answer
    return {key: answer.get(key) for key in keys}


def build_answer(case: dict[str, Any], task_id: str, case_id: str) -> dict[str, Any]:
    case_type = (case.get("case") or {}).get("case_type")
    if case_type == "acute_respiratory":
        return build_respiratory(case, task_id, case_id)
    if case_type == "pediatric_head_injury":
        return build_head(case, task_id, case_id)
    if case_type == "potassium_repletion":
        return build_potassium(case, task_id, case_id)
    if case_type == "care_management":
        return build_care_management(case, task_id, case_id)
    if case_type == "observation_window":
        return build_observation_window(case, task_id, case_id)
    raise SystemExit(f"unsupported case_type: {case_type}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--template")
    parser.add_argument("--task-id")
    args = parser.parse_args()

    template = load_template(args.template)
    task_id = infer_task_id(template, args.template, args.task_id)
    case = fetch_json(args.base_url, f"/api/cases/{args.case_id}")
    answer = build_answer(case, task_id, args.case_id)
    answer = filter_to_template(answer, template)
    json.dump(answer, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
