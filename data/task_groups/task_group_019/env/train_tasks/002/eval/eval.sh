#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -eq 0 ]]; then
  set -- "$SCRIPT_DIR/../output/answer.json"
elif [[ $# -ne 1 ]]; then
  printf '{"score":0.0,"error":"usage: eval.sh <prediction.json>","points":[]}\n'
  exit 0
fi

python3 - "$1" <<'PY'
import json
import sys
from pathlib import Path

prediction_path = Path(sys.argv[1])

EXPECTED = {
    "application_id": "AA-2026-0003",
    "premises_id": "PM-2026-003",
    "review_month": "2026-02",
    "recommendation": "REQUEST_FOLLOWUP",
    "risk_assessment": {
        "same_premises_basis": "SAME_ADDRESS_OVERLAP",
        "prior_incident_level": "HIGH",
        "incident_count": 5,
        "unresolved_incident_count": 3,
        "high_severity_incident_count": 1,
        "settlement_posture": "PRIOR_WARNING_WITH_CONTROLS",
        "control_coverage": "STANDARD_ONLY",
        "overall_risk": "ELEVATED",
    },
    "verification_gaps": [
        "AGE_VERIFICATION_CONTROL_NOT_IN_CURRENT_RESTRICTIONS",
        "LATE_NIGHT_SECURITY_CONTROL_NOT_IN_CURRENT_RESTRICTIONS",
        "PENDING_POLICE_CALL_DISPOSITIONS",
        "SECURITY_PLAN_LAPSE_DISPOSITION_MISSING",
    ],
    "inspection_controls": {
        "standard_obligations": [
            {"control_code": "FOOD_SERVICE", "source": "PROPOSED_STANDARD_OBLIGATION", "evidence_required": "menu and receipts"},
            {"control_code": "INCIDENT_REPORT", "source": "ALL_LICENSE_STANDARD", "evidence_required": "incident report log"},
            {"control_code": "PUBLIC_RECORDS", "source": "ALL_LICENSE_STANDARD", "evidence_required": "records binder"},
            {"control_code": "RTL_DISPLAY", "source": "LICENSE_TYPE_STANDARD", "evidence_required": "photo evidence"},
            {"control_code": "RTL_SALES", "source": "LICENSE_TYPE_STANDARD", "evidence_required": "sales audit"},
            {"control_code": "RTL_STAFF", "source": "LICENSE_TYPE_STANDARD", "evidence_required": "training roster"},
        ],
        "location_specific_restrictions": [
            {"control_code": "AGE_CHECK", "status": "FOLLOWUP_REQUIRED_BEFORE_ISSUE", "evidence_required": "device audit", "first_90_day_focus": "DEVICE_AUDIT"},
            {"control_code": "NO_AFTER_MIDNIGHT_SERVICE", "status": "FOLLOWUP_REQUIRED_BEFORE_ISSUE", "evidence_required": "service log", "first_90_day_focus": "SERVICE_LOG_REVIEW"},
            {"control_code": "SECURITY_LOG", "status": "FOLLOWUP_REQUIRED_BEFORE_ISSUE", "evidence_required": "weekly log", "first_90_day_focus": "WEEKLY_LOG_REVIEW"},
        ],
    },
    "review_month_comparison": {
        "review_month_application_count": 13,
        "restricted_reviews_with_location_specific_controls_count": 7,
        "target_current_location_specific_control_count": 0,
        "target_has_location_specific_controls": False,
        "application_ids_with_location_specific_controls": [
            "AA-2026-0005",
            "AA-2026-0011",
            "AA-2026-0015",
            "AA-2026-0020",
            "AA-2026-0035",
            "AA-2026-0040",
            "AA-2026-0045",
        ],
    },
}

POINTS = [
    ("SP1", "Correct target IDs, review month, and final recommendation.", 3),
    ("SP2", "Correct same-premises, settlement, incident-level, and overall risk classifications.", 2),
    ("SP3", "Correct incident, unresolved-disposition, and high-severity counts.", 2),
    ("SP4", "Correct standard-only control coverage and February comparison context.", 2),
    ("SP5", "Correct verification-gap set.", 2),
    ("SP6", "Correct standard-obligation controls with sources and evidence.", 2),
    ("SP7", "Correct location-specific restriction follow-up controls and first-90-day focus.", 3),
]


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def obj_map(items, key):
    if not isinstance(items, list):
        return None
    out = {}
    for item in items:
        if not isinstance(item, dict) or key not in item:
            return None
        out[item[key]] = item
    return out


def string_set(value):
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return set(value)


def get(dct, *keys):
    cur = dct
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


try:
    pred = load_json(prediction_path)
except Exception as exc:
    result = {
        "score": 0.0,
        "error": f"invalid_json: {exc}",
        "points": [
            {"id": pid, "description": desc, "weight": weight, "passed": False}
            for pid, desc, weight in POINTS
        ],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    sys.exit(0)

exp = EXPECTED

checks = []
checks.append(
    pred.get("application_id") == exp["application_id"]
    and pred.get("premises_id") == exp["premises_id"]
    and pred.get("review_month") == exp["review_month"]
    and pred.get("recommendation") == exp["recommendation"]
)

checks.append(
    get(pred, "risk_assessment", "same_premises_basis") == exp["risk_assessment"]["same_premises_basis"]
    and get(pred, "risk_assessment", "settlement_posture") == exp["risk_assessment"]["settlement_posture"]
    and get(pred, "risk_assessment", "prior_incident_level") == exp["risk_assessment"]["prior_incident_level"]
    and get(pred, "risk_assessment", "overall_risk") == exp["risk_assessment"]["overall_risk"]
)

checks.append(
    get(pred, "risk_assessment", "incident_count") == exp["risk_assessment"]["incident_count"]
    and get(pred, "risk_assessment", "unresolved_incident_count") == exp["risk_assessment"]["unresolved_incident_count"]
    and get(pred, "risk_assessment", "high_severity_incident_count") == exp["risk_assessment"]["high_severity_incident_count"]
)

pred_comp = pred.get("review_month_comparison", {})
exp_comp = exp["review_month_comparison"]
checks.append(
    get(pred, "risk_assessment", "control_coverage") == exp["risk_assessment"]["control_coverage"]
    and pred_comp.get("review_month_application_count") == exp_comp["review_month_application_count"]
    and pred_comp.get("restricted_reviews_with_location_specific_controls_count") == exp_comp["restricted_reviews_with_location_specific_controls_count"]
    and pred_comp.get("target_current_location_specific_control_count") == exp_comp["target_current_location_specific_control_count"]
    and pred_comp.get("target_has_location_specific_controls") == exp_comp["target_has_location_specific_controls"]
    and string_set(pred_comp.get("application_ids_with_location_specific_controls")) == set(exp_comp["application_ids_with_location_specific_controls"])
)

checks.append(string_set(pred.get("verification_gaps")) == set(exp["verification_gaps"]))

pred_standard = obj_map(get(pred, "inspection_controls", "standard_obligations"), "control_code")
exp_standard = obj_map(exp["inspection_controls"]["standard_obligations"], "control_code")
checks.append(pred_standard == exp_standard)

pred_location = obj_map(get(pred, "inspection_controls", "location_specific_restrictions"), "control_code")
exp_location = obj_map(exp["inspection_controls"]["location_specific_restrictions"], "control_code")
checks.append(pred_location == exp_location)

point_results = []
earned = 0
total = sum(weight for _, _, weight in POINTS)
for (pid, desc, weight), passed in zip(POINTS, checks):
    if passed:
        earned += weight
    point_results.append(
        {
            "id": pid,
            "description": desc,
            "weight": weight,
            "passed": bool(passed),
            "score_contribution": (weight / total) if passed else 0.0,
        }
    )

print(
    json.dumps(
        {
            "score": earned / total,
            "earned_weight": earned,
            "total_weight": total,
            "points": point_results,
        },
        indent=2,
        sort_keys=True,
    )
)
PY
