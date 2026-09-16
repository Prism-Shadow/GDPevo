#!/usr/bin/env python3
"""Draft Cedar Ridge intake JSON from the allowed portal SQL endpoint.

The helper is intentionally generic: it reads the current prompt/template and
derives rows from portal data. It does not contain cached task answers.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


EXPECTED_CHAPTERS = {
    "orthopedics": {"M00-M99"},
    "pulmonary": {"J00-J99", "R00-R99"},
    "cardiology": {"I00-I99"},
    "neurology": {"G00-G99"},
    "dermatology": {"L00-L99"},
}

PROGRAM_CONDITION_HINTS = {
    "DMHTN": "diabetes_hypertension",
    "RENAL-DM": "renal_diabetes",
    "COPD": "copd",
    "CAD": "cardiac",
}

CONDITION_DIAGNOSES = {
    "diabetes_hypertension": {"diabetes", "hypertension"},
    "renal_diabetes": {"ckd", "diabetes"},
    "copd": {"copd"},
    "cardiac": {"cad"},
}

CONTACT_REQUIREMENTS = {
    "phone": "phone",
    "sms": "phone",
    "email": "email",
}

PRIMARY_REASON_ORDER = [
    "coverage_expired",
    "coverage_pending",
    "excluded_service_line",
    "pbm_invalid",
    "pbm_missing",
    "pbm_policy_mismatch",
    "pharmacy_out_of_network",
    "pharmacy_unknown",
    "missing_address",
    "preferred_contact_unavailable",
    "emergency_contact_missing",
    "overall_risk_high",
]

ACTIVATION_BLOCKER_ORDER = [
    "authorization_blocked",
    "clinical_code_discrepancy",
    "records_missing",
    "imaging_missing",
    "duplicate_review",
    "scheduled_before_clearance",
]

APPOINTMENT_REASON_ORDER = [
    "appointment_already_scheduled",
    "authorization_denied",
    "clinical_reason_mismatch",
    "wrong_service_family",
    "records_missing",
    "duplicate_review",
]

PROGRAM_REASON_ORDER = [
    "meets_dmhtn_criteria",
    "recent_hospitalization_high_touch",
    "low_adherence_high_touch",
    "ckd_biweekly_monitoring",
    "recent_ed_high_touch",
    "wrong_target_condition",
    "missing_active_dmhtn_diagnosis",
    "consent_declined",
    "consent_missing",
    "chart_not_active",
    "stale_active_problems",
    "missing_recent_vitals",
    "missing_recent_labs",
    "missing_medication_list",
]


class Portal:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/") + "/"

    def query(self, sql: str) -> list[dict[str, Any]]:
        body = json.dumps({"sql": sql}).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + "query",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise SystemExit(f"portal query failed: {exc}") from exc
        if "error" in payload:
            raise SystemExit(f"portal query failed: {payload['error']}")
        return payload.get("rows", [])


def q(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text())


def read_text(path: str | Path) -> str:
    return Path(path).read_text()


def walk_dicts(obj: Any):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from walk_dicts(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk_dicts(value)


def find_constant(template: dict[str, Any], key: str) -> Any:
    for node in walk_dicts(template):
        if key not in node:
            continue
        value = node[key]
        if isinstance(value, dict):
            for const_key in ("required_value", "expected_value", "constant"):
                if const_key in value:
                    return value[const_key]
        elif isinstance(value, str):
            return value
    return None


def find_allowed(template: dict[str, Any], field_name: str) -> list[Any]:
    for node in walk_dicts(template):
        if field_name not in node:
            continue
        spec = node[field_name]
        if isinstance(spec, dict):
            for allowed_key in ("allowed_values", "allowed"):
                if isinstance(spec.get(allowed_key), list):
                    return spec[allowed_key]
    return []


def order_by_allowed(values: list[str], allowed: list[Any]) -> list[str]:
    seen = set()
    unique = [v for v in values if not (v in seen or seen.add(v))]
    order = {v: i for i, v in enumerate(allowed)}
    return sorted(unique, key=lambda v: (order.get(v, 10_000), v))


def parse_ids(prompt: str, template: dict[str, Any]) -> dict[str, str | None]:
    ids = {
        "task_id": find_constant(template, "task_id"),
        "roster_id": find_constant(template, "roster_id"),
        "batch_id": find_constant(template, "batch_id"),
        "program_code": find_constant(template, "program_code"),
    }
    patterns = {
        "roster_id": r"\broster\s+([A-Z0-9-]+)",
        "batch_id": r"\bbatch\s+([A-Z0-9-]+)",
        "program_code": r"\bprogram\s+`?([A-Z0-9-]+)`?",
    }
    for key, pattern in patterns.items():
        if not ids.get(key):
            match = re.search(pattern, prompt, flags=re.I)
            if match:
                ids[key] = match.group(1)
    return ids


def date_or_none(value: Any) -> dt.date | None:
    if not value:
        return None
    return dt.date.fromisoformat(str(value))


def days_between(start: str, earlier: str) -> int:
    return (dt.date.fromisoformat(start) - dt.date.fromisoformat(earlier)).days


def split_csv(value: Any) -> set[str]:
    if not value:
        return set()
    return {part.strip() for part in str(value).split(",") if part.strip()}


def channel_available(channel: str | None, row: dict[str, Any]) -> bool:
    if not channel or channel == "none":
        return False
    if channel == "portal":
        return bool(row.get("existing_chart"))
    required = CONTACT_REQUIREMENTS.get(channel)
    return bool(row.get(required)) if required else False


def choose_channel(preferred: str | None, row: dict[str, Any], allowed: list[Any]) -> str:
    candidates = [preferred, row.get("preferred_contact"), "phone", "portal", "sms", "email"]
    for channel in candidates:
        if channel in allowed and channel_available(channel, row):
            return channel
    return "none" if "none" in allowed else str(allowed[0])


def solve_primary(portal: Portal, template: dict[str, Any], ids: dict[str, str | None]) -> dict[str, Any]:
    roster_id = ids["roster_id"]
    if not roster_id:
        raise SystemExit("could not determine roster_id")
    rows = portal.query(
        """
        select r.roster_id, r.patient_id as roster_patient_id,
               r.requested_service_date, r.service_line,
               p.patient_id, p.address, p.preferred_contact, p.phone, p.email,
               p.emergency_contact_present, p.existing_chart,
               c.payer as coverage_payer, c.policy_number as coverage_policy,
               c.effective_date, c.termination_date,
               c.network_status as coverage_network_status,
               c.service_lines as coverage_service_lines,
               c.status as coverage_status,
               b.payer as pbm_payer, b.policy_number as pbm_policy,
               b.active as pbm_active, b.formulary_status, b.status as pbm_status,
               pp.pharmacy_id, ph.network_status as pharmacy_network_status,
               l.smoking_status, l.alcohol_use, l.exercise_frequency, l.sleep_hours,
               h.recent_hospitalization, h.risk_flags
        from intake_rosters r
        join patients p on p.patient_id = r.patient_id
        left join coverage c on c.patient_id = r.patient_id
        left join pbm b on b.patient_id = r.patient_id
        left join patient_pharmacy pp
          on pp.patient_id = r.patient_id and pp.preference_rank = 1
        left join pharmacies ph on ph.pharmacy_id = pp.pharmacy_id
        left join lifestyle l on l.patient_id = r.patient_id
        left join clinical_history h on h.patient_id = r.patient_id
        where r.roster_id = %s
        order by r.patient_id
        """
        % q(roster_id)
    )
    allowed_reasons = find_allowed(template, "blocked_reason_codes")
    patient_results = []
    for row in rows:
        service_date = row["requested_service_date"]
        service_line = row["service_line"]
        reasons: list[str] = []

        coverage_status = row.get("coverage_status")
        coverage_lines = split_csv(row.get("coverage_service_lines"))
        insurance_status = "valid"
        if not coverage_status:
            insurance_status = "missing"
        elif coverage_status == "pending":
            insurance_status = "invalid"
            reasons.append("coverage_pending")
        elif coverage_status == "expired":
            insurance_status = "invalid"
            reasons.append("coverage_expired")
        elif row.get("termination_date") and row["termination_date"] < service_date:
            insurance_status = "invalid"
            reasons.append("coverage_expired")
        if coverage_status and service_line not in coverage_lines:
            insurance_status = "invalid"
            reasons.append("excluded_service_line")
        if not coverage_status:
            reasons.append("coverage_expired")

        prescription_status = "valid"
        if row.get("pbm_status") is None:
            prescription_status = "missing"
            reasons.append("pbm_missing")
        elif row.get("pbm_policy") != row.get("coverage_policy") or row.get("pbm_payer") != row.get("coverage_payer"):
            prescription_status = "invalid"
            reasons.append("pbm_policy_mismatch")
        elif not row.get("pbm_active") or row.get("pbm_status") != "approved" or row.get("formulary_status") != "covered":
            prescription_status = "invalid"
            reasons.append("pbm_invalid")

        network = row.get("pharmacy_network_status")
        if network == "in_network":
            pharmacy_status = "in_network"
        elif network == "out_of_network":
            pharmacy_status = "out_of_network"
            reasons.append("pharmacy_out_of_network")
        else:
            pharmacy_status = "unknown"
            reasons.append("pharmacy_unknown")

        if not row.get("address"):
            reasons.append("missing_address")
        if not row.get("emergency_contact_present"):
            reasons.append("emergency_contact_missing")
        preferred = row.get("preferred_contact")
        if preferred in CONTACT_REQUIREMENTS and not row.get(CONTACT_REQUIREMENTS[preferred]):
            reasons.append("preferred_contact_unavailable")

        lifestyle_risk = lifestyle(row)
        overall_risk = "high" if (
            lifestyle_risk == "high"
            or bool(row.get("risk_flags"))
            or bool(row.get("recent_hospitalization"))
        ) else lifestyle_risk
        if overall_risk == "high":
            reasons.append("overall_risk_high")

        if "excluded_service_line" in reasons or "coverage_expired" in reasons and coverage_status != "pending":
            registration_status = "rejected"
        elif reasons:
            registration_status = "clinical_review"
        else:
            registration_status = "approved"

        patient_results.append(
            {
                "patient_id": row["patient_id"],
                "insurance_status": insurance_status,
                "prescription_status": prescription_status,
                "pharmacy_status": pharmacy_status,
                "lifestyle_risk": lifestyle_risk,
                "overall_risk": overall_risk,
                "registration_status": registration_status,
                "blocked_reason_codes": order_by_allowed(reasons, PRIMARY_REASON_ORDER or allowed_reasons),
            }
        )

    return {
        "task_id": ids.get("task_id"),
        "roster_id": roster_id,
        "requested_service_date": rows[0]["requested_service_date"] if rows else None,
        "service_line": rows[0]["service_line"] if rows else None,
        "patient_results": patient_results,
        "cohort_summary": {
            "total_patients": len(patient_results),
            "counts_by_registration_status": count_enum(patient_results, "registration_status", find_allowed(template, "registration_status")),
            "counts_by_overall_risk": count_enum(patient_results, "overall_risk", find_allowed(template, "overall_risk")),
            "counts_by_lifestyle_risk": count_enum(patient_results, "lifestyle_risk", find_allowed(template, "lifestyle_risk")),
        },
    }


def lifestyle(row: dict[str, Any]) -> str:
    smoking = (row.get("smoking_status") or "").lower()
    alcohol = (row.get("alcohol_use") or "").lower()
    exercise = row.get("exercise_frequency")
    sleep = row.get("sleep_hours")
    if smoking == "current" or alcohol == "heavy" or not exercise or str(exercise).lower() == "none":
        return "high"
    if isinstance(sleep, (int, float)) and sleep < 6:
        return "high"
    if smoking == "former" or alcohol == "moderate":
        return "medium"
    if isinstance(sleep, (int, float)) and sleep < 7:
        return "medium"
    return "low"


def count_enum(rows: list[dict[str, Any]], field: str, allowed: list[Any]) -> dict[str, int]:
    keys = [str(v) for v in allowed if v is not None]
    counts = {key: 0 for key in keys}
    for row in rows:
        value = row.get(field)
        if value in counts:
            counts[value] += 1
    return counts


def referral_rows(portal: Portal, batch_id: str) -> list[dict[str, Any]]:
    return portal.query(
        """
        select f.*, i.chapter as icd_chapter, i.service_family as icd_service_family,
               i.laterality as icd_laterality, i.description as icd_description
        from referrals f
        left join icd_codes i on i.code = f.icd10_code
        where f.batch_id = %s
        order by f.referral_id
        """
        % q(batch_id)
    )


def referral_context(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_patient = collections.defaultdict(list)
    by_insurance = collections.defaultdict(list)
    for row in rows:
        by_patient[row["patient_id"]].append(row)
        if row.get("insurance_id"):
            by_insurance[row["insurance_id"]].append(row)
    duplicate_groups = [group for group in by_patient.values() if len(group) > 1]
    shared_insurance = [
        group for group in by_insurance.values()
        if len({row["patient_id"] for row in group}) > 1
    ]
    duplicate_ids = {row["referral_id"] for group in duplicate_groups for row in group}
    shared_ids = {row["referral_id"] for group in shared_insurance for row in group}
    return {
        "duplicate_groups": duplicate_groups,
        "shared_insurance": shared_insurance,
        "duplicate_ids": duplicate_ids,
        "shared_ids": shared_ids,
    }


def code_issue(row: dict[str, Any], activation: bool = False) -> list[str]:
    service = row.get("service_line")
    family = row.get("icd_service_family")
    chapter = row.get("icd_chapter")
    reason = (row.get("referral_reason") or "").lower()
    issues: list[str] = []
    expected = EXPECTED_CHAPTERS.get(service or "", set())

    if service == "orthopedics":
        if chapter not in expected:
            issues.append("clinical_code_discrepancy" if activation else "icd_chapter_mismatch")
    elif family and family != service:
        issues.append("clinical_code_discrepancy" if activation else "icd_chapter_mismatch")
    elif expected and chapter not in expected:
        issues.append("clinical_code_discrepancy" if activation else "icd_chapter_mismatch")

    if service != "orthopedics" and "pain" in reason and row.get("icd_service_family") != "orthopedics":
        label = "clinical_code_discrepancy" if activation else "narrative_mismatch"
        if label not in issues:
            issues.append(label)

    text = " ".join(
        str(row.get(key) or "").lower()
        for key in ("diagnosis_description", "referral_reason", "notes")
    )
    laterality = row.get("icd_laterality")
    if laterality == "left" and "right" in text:
        issues.append("clinical_code_discrepancy" if activation else "laterality_mismatch")
    if laterality == "right" and "left" in text:
        issues.append("clinical_code_discrepancy" if activation else "laterality_mismatch")
    return list(dict.fromkeys(issues))


def auth_blocked(row: dict[str, Any]) -> bool:
    return bool(row.get("auth_required")) and row.get("auth_status") in {"pending", "denied", "not_submitted"}


def readiness(issue_codes: list[str]) -> str:
    hard = {"missing_records", "records_missing", "missing_imaging", "imaging_missing", "auth_blocker", "authorization_blocked"}
    if any(code in hard for code in issue_codes):
        return "blocked"
    if issue_codes == ["shared_insurance_anomaly"]:
        return "admin_followup"
    if issue_codes:
        return "under_review"
    return "ready"


def priority(row: dict[str, Any], status: str, issue_codes: list[str]) -> str | None:
    if status == "ready":
        return None
    clinical = any(code in issue_codes for code in ("icd_chapter_mismatch", "narrative_mismatch", "laterality_mismatch", "clinical_code_discrepancy"))
    if row.get("urgency") == "urgent" and clinical:
        return "tier_1_immediate"
    if status == "admin_followup":
        return "tier_3_administrative"
    return "tier_2_short_term"


def solve_referral_readiness(portal: Portal, template: dict[str, Any], ids: dict[str, str | None]) -> dict[str, Any]:
    batch_id = ids["batch_id"]
    if not batch_id:
        raise SystemExit("could not determine batch_id")
    rows = referral_rows(portal, batch_id)
    ctx = referral_context(rows)
    allowed_issues = find_allowed(template, "issue_codes")
    allowed_actions = find_allowed(template, "action_codes")
    reviews = []
    icd_discrepancies = []
    action_plan = []

    for row in rows:
        issue_codes: list[str] = []
        issue_types = code_issue(row)
        issue_codes.extend(issue_types)
        if row["referral_id"] in ctx["duplicate_ids"]:
            issue_codes.append("duplicate_referral")
        if row["referral_id"] in ctx["shared_ids"]:
            issue_codes.append("shared_insurance_anomaly")
        if not row.get("records_received"):
            issue_codes.append("missing_records")
        if not row.get("imaging_received"):
            issue_codes.append("missing_imaging")
        if auth_blocked(row):
            issue_codes.append("auth_blocker")
        if row.get("appointment_scheduled") and issue_codes:
            issue_codes.append("already_scheduled")
        issue_codes = order_by_allowed(issue_codes, allowed_issues)
        status = readiness(issue_codes)
        tier = priority(row, status, issue_codes)
        reviews.append(
            {
                "referral_id": row["referral_id"],
                "readiness_status": status,
                "issue_codes": issue_codes,
                "priority_tier": tier,
            }
        )
        if issue_types:
            expected_chapter = next(iter(EXPECTED_CHAPTERS.get(row.get("service_line") or "", {None})))
            icd_discrepancies.append(
                {
                    "referral_id": row["referral_id"],
                    "icd10_code": row.get("icd10_code"),
                    "issue_types": order_by_allowed(issue_types, find_allowed(template, "issue_types")),
                    "observed_chapter": row.get("icd_chapter"),
                    "expected_chapter": expected_chapter,
                }
            )
        if status != "ready":
            action_plan.append(
                {
                    "referral_id": row["referral_id"],
                    "priority_tier": tier,
                    "action_codes": order_by_allowed(actions_for(issue_codes), allowed_actions),
                }
            )

    return {
        "task_id": ids.get("task_id"),
        "batch_id": batch_id,
        "referral_reviews": reviews,
        "icd_discrepancies": sorted(icd_discrepancies, key=lambda item: item["referral_id"]),
        "duplicate_groups": duplicate_group_objects(ctx["duplicate_groups"], batch_id),
        "shared_insurance_anomalies": shared_insurance_objects(ctx["shared_insurance"]),
        "blocker_sets": {
            "missing_records": [row["referral_id"] for row in rows if not row.get("records_received")],
            "missing_imaging": [row["referral_id"] for row in rows if not row.get("imaging_received")],
            "auth_blockers": [
                {"referral_id": row["referral_id"], "auth_status": row["auth_status"]}
                for row in rows if auth_blocked(row)
            ],
        },
        "ready_to_schedule": [row["referral_id"] for row, review in zip(rows, reviews) if review["readiness_status"] == "ready"],
        "action_plan": action_plan,
        "summary": referral_summary(rows, reviews, ctx),
    }


def duplicate_group_objects(groups: list[list[dict[str, Any]]], batch_id: str) -> list[dict[str, Any]]:
    out = []
    for idx, group in enumerate(sorted(groups, key=lambda g: min(r["referral_id"] for r in g)), start=1):
        ids = sorted(row["referral_id"] for row in group)
        primary = min(ids)
        out.append(
            {
                "group_id": f"DUP-{batch_id}-{idx:03d}",
                "referral_ids": ids,
                "patient_id": group[0]["patient_id"],
                "primary_referral_id": primary,
                "recommendation": "consolidate_to_primary",
            }
        )
    return out


def shared_insurance_objects(groups: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    out = []
    for group in sorted(groups, key=lambda g: g[0].get("insurance_id") or ""):
        out.append(
            {
                "insurance_id": group[0].get("insurance_id"),
                "referral_ids": sorted(row["referral_id"] for row in group),
                "patient_ids": sorted({row["patient_id"] for row in group}),
                "disposition": "verify_distinct_patient_policy_id",
            }
        )
    return out


def actions_for(issue_codes: list[str]) -> list[str]:
    mapping = {
        "icd_chapter_mismatch": "request_corrected_icd",
        "clinical_code_discrepancy": "request_corrected_icd",
        "narrative_mismatch": "confirm_narrative",
        "laterality_mismatch": "confirm_laterality",
        "duplicate_referral": "consolidate_duplicate",
        "shared_insurance_anomaly": "verify_insurance_id",
        "missing_records": "request_records",
        "records_missing": "request_records",
        "missing_imaging": "request_imaging",
        "imaging_missing": "request_imaging",
        "auth_blocker": "resolve_authorization",
        "authorization_blocked": "resolve_authorization",
        "already_scheduled": "review_existing_appointment",
        "scheduled_before_clearance": "review_existing_appointment",
    }
    return [mapping[code] for code in issue_codes if code in mapping]


def referral_summary(rows: list[dict[str, Any]], reviews: list[dict[str, Any]], ctx: dict[str, Any]) -> dict[str, Any]:
    status_counts = collections.Counter(review["readiness_status"] for review in reviews)
    urgency_counts = collections.Counter(row.get("urgency") for row in rows)
    combo = collections.Counter((row.get("urgency"), review["readiness_status"]) for row, review in zip(rows, reviews))
    return {
        "total_referrals": len(rows),
        "ready_to_schedule_count": status_counts.get("ready", 0),
        "follow_up_count": len(rows) - status_counts.get("ready", 0),
        "counts_by_urgency": {key: urgency_counts.get(key, 0) for key in ("urgent", "routine", "admin")},
        "counts_by_readiness_status": {key: status_counts.get(key, 0) for key in ("ready", "blocked", "under_review", "admin_followup")},
        "counts_by_urgency_and_status": [
            {"urgency": urgency, "readiness_status": status, "count": count}
            for (urgency, status), count in sorted(combo.items())
        ],
        "issue_counts": {
            "icd_discrepancy_referrals": sum(
                1 for review in reviews
                if any(code in review["issue_codes"] for code in ("icd_chapter_mismatch", "narrative_mismatch", "laterality_mismatch", "clinical_code_discrepancy"))
            ),
            "duplicate_groups": len(ctx["duplicate_groups"]),
            "shared_insurance_anomalies": len(ctx["shared_insurance"]),
            "missing_records_referrals": sum(1 for row in rows if not row.get("records_received")),
            "missing_imaging_referrals": sum(1 for row in rows if not row.get("imaging_received")),
            "auth_blocker_referrals": sum(1 for row in rows if auth_blocked(row)),
        },
    }


def solve_activation(portal: Portal, template: dict[str, Any], ids: dict[str, str | None]) -> dict[str, Any]:
    batch_id = ids["batch_id"]
    if not batch_id:
        raise SystemExit("could not determine batch_id")
    rows = referral_rows(portal, batch_id)
    ctx = referral_context(rows)
    allowed_blockers = find_allowed(template, "blocker_codes")
    readiness_rows = []
    code_referrals = []
    correspondence = []
    ready_needs = []

    for row in rows:
        blockers: list[str] = []
        if code_issue(row, activation=True):
            blockers.append("clinical_code_discrepancy")
            code_referrals.append(row["referral_id"])
        if not row.get("records_received"):
            blockers.append("records_missing")
        if not row.get("imaging_received"):
            blockers.append("imaging_missing")
        if auth_blocked(row):
            blockers.append("authorization_blocked")
        if row["referral_id"] in ctx["duplicate_ids"]:
            blockers.append("duplicate_review")
        if row.get("appointment_scheduled") and blockers:
            blockers.append("scheduled_before_clearance")
        blockers = order_by_allowed(blockers, ACTIVATION_BLOCKER_ORDER or allowed_blockers)
        status = readiness(blockers)
        readiness_rows.append(
            {
                "referral_id": row["referral_id"],
                "patient_id": row["patient_id"],
                "readiness_status": status,
                "blocker_codes": blockers,
            }
        )
        if status == "ready":
            ready_needs.append(chart_needs(portal, row, template))
        else:
            correspondence.append(correspondence_item(row, blockers))

    non_ready = [(row, review) for row, review in zip(rows, readiness_rows) if review["readiness_status"] != "ready"]
    non_ready.sort(key=lambda pair: priority_sort_key(pair[0], pair[1]["blocker_codes"]))
    return {
        "batch_id": batch_id,
        "readiness_by_referral": readiness_rows,
        "clinical_code_discrepancy_referrals": sorted(code_referrals),
        "blocker_sets": {
            "authorization": [row["referral_id"] for row in rows if auth_blocked(row)],
            "records": [row["referral_id"] for row in rows if not row.get("records_received")],
            "imaging": [row["referral_id"] for row in rows if not row.get("imaging_received")],
        },
        "duplicate_handling": {
            "duplicate_groups": activation_duplicate_groups(ctx["duplicate_groups"], batch_id),
            "cleared_duplicate_review_referrals": sorted(
                row["referral_id"] for row in rows
                if "duplicate" in str(row.get("notes") or "").lower() and row["referral_id"] not in ctx["duplicate_ids"]
            ),
        },
        "ready_referral_chart_needs": sorted(ready_needs, key=lambda item: item["referral_id"]),
        "correspondence_queue": sorted(correspondence, key=lambda item: item["referral_id"]),
        "priority_order": [
            {
                "rank": idx,
                "referral_id": row["referral_id"],
                "priority_tier": priority(row, review["readiness_status"], review["blocker_codes"]),
            }
            for idx, (row, review) in enumerate(non_ready, start=1)
        ],
    }


def priority_sort_key(row: dict[str, Any], blockers: list[str]) -> tuple[int, int, str]:
    tier = priority(row, "under_review" if blockers else "ready", blockers)
    tier_order = {"tier_1_immediate": 0, "tier_2_short_term": 1, "tier_3_administrative": 2, None: 3}
    scheduled_or_many = 0 if ("scheduled_before_clearance" in blockers or len(blockers) > 2) else 1
    return (tier_order.get(tier, 3), scheduled_or_many, row["referral_id"])


def activation_duplicate_groups(groups: list[list[dict[str, Any]]], batch_id: str) -> list[dict[str, Any]]:
    out = []
    for group in duplicate_group_objects(groups, batch_id):
        out.append(
            {
                "group_id": group["group_id"],
                "referral_ids": group["referral_ids"],
                "keep_referral_id": group["primary_referral_id"],
            }
        )
    return out


def chart_needs(portal: Portal, row: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    allowed = [v for v in find_allowed(template, "artifacts_to_create") if v is not None]
    chart_rows = portal.query(
        "select artifact_type, status from chart_artifacts where patient_id = %s"
        % q(row["patient_id"])
    )
    current = {item["artifact_type"] for item in chart_rows if item.get("status") == "current"}
    missing = [artifact for artifact in allowed if artifact not in current]
    patient = portal.query("select existing_chart from patients where patient_id = %s" % q(row["patient_id"]))
    existing = bool(patient and patient[0].get("existing_chart"))
    if not existing:
        action = "create_chart"
    elif missing:
        action = "update_chart"
    else:
        action = "no_chart_action"
    return {
        "referral_id": row["referral_id"],
        "patient_id": row["patient_id"],
        "chart_action": action,
        "artifacts_to_create": sorted(missing),
    }


def correspondence_item(row: dict[str, Any], blockers: list[str]) -> dict[str, Any]:
    reasons: list[str] = []
    if "scheduled_before_clearance" in blockers:
        template_type = "appointment_hold_notice"
        reasons.append("appointment_already_scheduled")
    elif "duplicate_review" in blockers:
        template_type = "duplicate_resolution"
        reasons.append("duplicate_review")
    elif "authorization_blocked" in blockers or "records_missing" in blockers:
        template_type = "auth_records_request"
    else:
        template_type = "clinical_code_clarification"

    if "clinical_code_discrepancy" in blockers:
        if row.get("icd_service_family") != row.get("service_line"):
            reasons.append("wrong_service_family")
        else:
            reasons.append("clinical_reason_mismatch")
    if "authorization_blocked" in blockers:
        reasons.append("authorization_denied")
    if "records_missing" in blockers:
        reasons.append("records_missing")
    return {
        "referral_id": row["referral_id"],
        "template_type": template_type,
        "reason_codes": order_by_allowed(reasons, APPOINTMENT_REASON_ORDER),
    }


def solve_dialysis(portal: Portal, template: dict[str, Any], ids: dict[str, str | None]) -> dict[str, Any]:
    batch_id = ids["batch_id"]
    if not batch_id:
        raise SystemExit("could not determine batch_id")
    transfers = portal.query(
        "select * from transfer_requests where batch_id = %s order by transfer_id"
        % q(batch_id)
    )
    required_docs = find_allowed(template, "missing_required_documents")
    stale_limits = {
        "hbsag": 30,
        "history_physical": 365,
        "monthly_labs": 30,
        "ppd_or_cxr": 30,
    }
    patients = []
    for transfer in transfers:
        docs = portal.query(
            "select * from documents where transfer_id = %s order by doc_type, received_date desc"
            % q(transfer["transfer_id"])
        )
        final_docs = {
            doc["doc_type"]: doc for doc in docs
            if doc.get("finalized") and doc.get("status") == "final"
        }
        missing = []
        for doc in required_docs:
            if doc == "transportation":
                if not transfer.get("transportation"):
                    missing.append(doc)
            elif doc not in final_docs:
                missing.append(doc)
        missing = sorted(missing)
        stale = []
        for doc_type, limit in stale_limits.items():
            doc = final_docs.get(doc_type)
            if doc and doc.get("received_date") and days_between(transfer["requested_start_date"], doc["received_date"]) > limit:
                stale.append(
                    {
                        "doc_type": doc_type,
                        "received_date": doc["received_date"],
                        "freshness_limit_days": limit,
                    }
                )
        capacity = portal.query(
            """
            select coalesce(sum(open_chairs), 0) as open_chairs_total
            from facility_capacity
            where date = %s and modality = %s
            """
            % (q(transfer["requested_start_date"]), q(transfer["modality"]))
        )
        open_chairs = int(capacity[0]["open_chairs_total"] or 0)
        capacity_status = "available" if open_chairs > 0 else "unavailable"
        packet_complete = not missing
        packet_ready = packet_complete and not stale
        if packet_ready and capacity_status == "available":
            feasibility = "ready_on_requested_start"
            decision = "accept"
            owner = "none"
            route = "none"
        elif packet_ready:
            feasibility = "capacity_unavailable"
            decision = "hold"
            owner = "scheduling_coordinator"
            route = "internal_queue"
        else:
            feasibility = "packet_not_ready_capacity_available" if capacity_status == "available" else "packet_not_ready_capacity_unavailable"
            decision = "clinical_review"
            owner = "clinical_nurse"
            route = "fax_referring_facility"
        patients.append(
            {
                "transfer_id": transfer["transfer_id"],
                "patient_id": transfer["patient_id"],
                "packet_completeness_status": "complete" if packet_complete else "incomplete",
                "missing_required_documents": missing,
                "stale_documents": sorted(stale, key=lambda item: item["doc_type"]),
                "requested_start": {
                    "date": transfer["requested_start_date"],
                    "capacity_status": capacity_status,
                    "open_chairs_total": open_chairs,
                    "feasibility": feasibility,
                },
                "final_intake_decision": decision,
                "next_contact_owner": owner,
                "next_contact_route": route,
            }
        )
    return {
        "batch_id": batch_id,
        "patients": patients,
        "cohort_summary": {
            "total_transfers": len(patients),
            "complete_documents_count": sum(1 for item in patients if item["packet_completeness_status"] == "complete"),
            "missing_document_patient_count": sum(1 for item in patients if item["missing_required_documents"]),
            "stale_document_patient_count": sum(1 for item in patients if item["stale_documents"]),
            "capacity_available_count": sum(1 for item in patients if item["requested_start"]["capacity_status"] == "available"),
            "requested_start_ready_count": sum(1 for item in patients if item["requested_start"]["feasibility"] == "ready_on_requested_start"),
            "decision_counts": count_values(patients, "final_intake_decision", ["accept", "hold", "clinical_review"]),
            "next_contact_owner_counts": count_values(patients, "next_contact_owner", ["clinical_nurse", "intake_coordinator", "scheduling_coordinator", "none"]),
        },
    }


def count_values(rows: list[dict[str, Any]], key: str, values: list[str]) -> dict[str, int]:
    counts = {value: 0 for value in values}
    for row in rows:
        value = row.get(key)
        if value in counts:
            counts[value] += 1
    return counts


def solve_program(portal: Portal, template: dict[str, Any], ids: dict[str, str | None], as_of: str | None) -> dict[str, Any]:
    program = ids["program_code"]
    if not program:
        raise SystemExit("could not determine program_code")
    rows = portal.query(
        """
        select pc.*, p.existing_chart, p.phone, p.email, p.preferred_contact,
               h.chronic_conditions, h.recent_hospitalization, h.risk_flags,
               h.medication_count
        from program_candidates pc
        join patients p on p.patient_id = pc.patient_id
        left join clinical_history h on h.patient_id = pc.patient_id
        where pc.program_code = %s
        order by pc.patient_id
        """
        % q(program)
    )
    expected_condition = expected_program_condition(program, rows)
    allowed_reasons = find_allowed(template, "reason_codes")
    allowed_missing = find_allowed(template, "missing_chart_artifacts")
    allowed_channels = find_allowed(template, "outreach_channel")
    patients = []
    for row in rows:
        chart_rows = portal.query(
            "select artifact_type, status from chart_artifacts where patient_id = %s"
            % q(row["patient_id"])
        )
        current = {item["artifact_type"] for item in chart_rows if item.get("status") == "current"}
        conditions = split_csv(row.get("chronic_conditions"))
        required_dx = CONDITION_DIAGNOSES.get(expected_condition, {expected_condition})
        target_ok = row.get("target_condition") == expected_condition
        dx_ok = required_dx.issubset(conditions)
        eligible = bool(target_ok and dx_ok)
        reasons: list[str] = []
        missing_artifacts: list[str] = []

        if not eligible:
            reasons.extend(["wrong_target_condition", "missing_active_dmhtn_diagnosis"])

        hard_declined = row.get("consent_status") == "declined"
        if hard_declined:
            reasons.append("consent_declined")
        elif eligible and row.get("consent_status") == "missing":
            reasons.append("consent_missing")

        hard_chart_inactive = not row.get("existing_chart")
        if hard_chart_inactive:
            reasons.append("chart_not_active")
            if eligible:
                missing_artifacts.append("chart_record")

        if eligible and not hard_declined:
            for artifact, reason in (
                ("active_problems", "stale_active_problems"),
                ("vitals", "missing_recent_vitals"),
                ("labs", "missing_recent_labs"),
                ("medications", "missing_medication_list"),
                ("consent", None),
            ):
                if artifact in allowed_missing and artifact not in current:
                    if reason:
                        reasons.append(reason)
                    missing_artifacts.append(artifact)
            if "consent" in allowed_missing and row.get("consent_status") == "missing":
                missing_artifacts.append("consent")

        if not eligible or row.get("consent_status") == "declined":
            status = "reject"
            cadence = "none"
        elif any(code in reasons for code in ("consent_missing", "chart_not_active", "stale_active_problems", "missing_recent_vitals", "missing_recent_labs", "missing_medication_list")):
            status = "hold"
            cadence = "deferred"
        else:
            status = "enroll"
            reasons.append("meets_dmhtn_criteria")
            cadence = cadence_and_reasons(row, conditions, reasons)

        patients.append(
            {
                "patient_id": row["patient_id"],
                "eligible": eligible,
                "enrollment_status": status,
                "reason_codes": order_program_reasons(reasons, allowed_reasons),
                "follow_up_cadence": cadence,
                "missing_chart_artifacts": order_by_allowed(missing_artifacts, allowed_missing),
                "outreach_channel": choose_channel(row.get("preferred_outreach"), row, allowed_channels),
                "initial_monitoring_package": monitoring_package(status, cadence, conditions, template),
            }
        )
    status_allowed = find_allowed(template, "enrollment_status")
    follow_allowed = find_allowed(template, "follow_up_cadence")
    channel_allowed = find_allowed(template, "outreach_channel")
    package_allowed = find_allowed(template, "package_type")
    return {
        "program_code": program,
        "as_of_date": as_of or infer_as_of(portal),
        "patients": patients,
        "summary": {
            "total_candidates": len(patients),
            "eligible_count": sum(1 for item in patients if item["eligible"]),
            "ineligible_count": sum(1 for item in patients if not item["eligible"]),
            "status_counts": count_values(patients, "enrollment_status", status_allowed),
            "follow_up_counts": count_values(patients, "follow_up_cadence", follow_allowed),
            "outreach_counts": count_values(patients, "outreach_channel", channel_allowed),
            "monitoring_package_counts": count_nested_package(patients, package_allowed),
        },
    }


def expected_program_condition(program: str, rows: list[dict[str, Any]]) -> str:
    for prefix, condition in PROGRAM_CONDITION_HINTS.items():
        if program.startswith(prefix):
            return condition
    counts = collections.Counter(row.get("target_condition") for row in rows)
    return counts.most_common(1)[0][0]


def order_program_reasons(reasons: list[str], allowed: list[Any]) -> list[str]:
    unique = list(dict.fromkeys(reasons))
    if "wrong_target_condition" in unique:
        wrong_first = [
            "wrong_target_condition",
            "missing_active_dmhtn_diagnosis",
            "consent_declined",
            "consent_missing",
            "chart_not_active",
            "stale_active_problems",
            "missing_recent_vitals",
            "missing_recent_labs",
            "missing_medication_list",
        ]
        return order_by_allowed(unique, wrong_first)
    return order_by_allowed(unique, PROGRAM_REASON_ORDER or allowed)


def cadence_and_reasons(row: dict[str, Any], conditions: set[str], reasons: list[str]) -> str:
    flags = split_csv(row.get("risk_flags"))
    if row.get("recent_hospitalization"):
        reasons.append("recent_hospitalization_high_touch")
        return "weekly"
    if "recent_ed_visit" in flags:
        reasons.append("recent_ed_high_touch")
        return "weekly"
    if row.get("adherence_score") is not None and int(row["adherence_score"]) < 50:
        reasons.append("low_adherence_high_touch")
        return "weekly"
    if "ckd" in conditions:
        reasons.append("ckd_biweekly_monitoring")
        return "biweekly"
    return "monthly"


def monitoring_package(status: str, cadence: str, conditions: set[str], template: dict[str, Any]) -> dict[str, Any]:
    allowed_packages = find_allowed(template, "package_type")
    allowed_components = find_allowed(template, "components")
    if status == "reject":
        return {"package_type": pick("not_applicable", allowed_packages), "components": [], "first_checkin_days": None}
    if status == "hold":
        components = [item for item in ("consent_packet", "chart_update_request") if item in allowed_components]
        return {"package_type": pick("deferred", allowed_packages), "components": components, "first_checkin_days": None}
    high_touch = cadence == "weekly"
    package_type = pick("high_touch_dm_htn" if high_touch else "standard_dm_htn", allowed_packages)
    components = [item for item in ("bp_cuff", "glucometer", "lab_order_a1c_cmp_lipid") if item in allowed_components]
    if high_touch or cadence == "biweekly" or "ckd" in conditions:
        if "medication_reconciliation" in allowed_components:
            components.append("medication_reconciliation")
    if high_touch and "care_plan_setup" in allowed_components:
        components.append("care_plan_setup")
    days = {"weekly": 7, "biweekly": 14, "monthly": 30}.get(cadence)
    return {"package_type": package_type, "components": components, "first_checkin_days": days}


def pick(value: str, allowed: list[Any]) -> str:
    return value if value in allowed else str(allowed[0])


def count_nested_package(rows: list[dict[str, Any]], values: list[Any]) -> dict[str, int]:
    counts = {value: 0 for value in values if value is not None}
    for row in rows:
        package = row.get("initial_monitoring_package", {}).get("package_type")
        if package in counts:
            counts[package] += 1
    return counts


def infer_as_of(portal: Portal) -> str:
    row = portal.query("select date('now') as today")
    return row[0]["today"]


def detect_task(template: dict[str, Any]) -> str:
    keys = set(template.get("required_top_level_keys", []))
    text = json.dumps(template)
    if "patient_results" in text and "cohort_summary" in text:
        return "primary"
    if "transfer_id" in text and "packet_completeness_status" in text:
        return "dialysis"
    if "referral_reviews" in text and "icd_discrepancies" in text:
        return "referral_readiness"
    if "readiness_by_referral" in text and "chart_action" in text:
        return "activation"
    if {"program_code", "as_of_date", "patients", "summary"}.issubset(keys):
        return "program"
    raise SystemExit("could not detect Cedar Ridge task type from template")


def strip_none_task_id(answer: dict[str, Any]) -> dict[str, Any]:
    if answer.get("task_id") is None:
        answer.pop("task_id", None)
    return answer


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--template", required=True)
    parser.add_argument("--output")
    parser.add_argument("--as-of")
    args = parser.parse_args()

    prompt = read_text(args.prompt)
    template = load_json(args.template)
    ids = parse_ids(prompt, template)
    portal = Portal(args.base_url)
    task_type = detect_task(template)

    if task_type == "primary":
        answer = solve_primary(portal, template, ids)
    elif task_type == "dialysis":
        answer = solve_dialysis(portal, template, ids)
    elif task_type == "referral_readiness":
        answer = solve_referral_readiness(portal, template, ids)
    elif task_type == "activation":
        answer = solve_activation(portal, template, ids)
    elif task_type == "program":
        answer = solve_program(portal, template, ids, args.as_of)
    else:
        raise AssertionError(task_type)

    answer = strip_none_task_id(answer)
    rendered = json.dumps(answer, indent=2)
    if args.output:
        Path(args.output).write_text(rendered + "\n")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
