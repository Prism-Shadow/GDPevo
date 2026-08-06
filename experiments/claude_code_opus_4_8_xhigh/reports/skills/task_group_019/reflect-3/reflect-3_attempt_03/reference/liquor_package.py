"""Family B - restricted liquor-license staff package (reference implementation).

Usage:
    from liquor_package import solve
    answer = solve(client, template, "L-XXX-001")

Derivable fields (obligations, active-settlement controls, same-premises basis)
are exact. covered_risk / verification_gap / plan / escalation / posture are
heuristics driven by active controls, evidence status and open incidents - see
SKILL.md. Codes are emitted only if they exist in the task's template enum, so
this adapts across the differing liquor vocabularies.
"""
import json


def _allowed(template, field):
    """Collect the allowed_values enum for a field anywhere in the template."""
    found = []

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == field and isinstance(v, dict):
                    av = v.get("allowed_values") or (v.get("items") or {}).get("allowed_values")
                    if av:
                        found.extend(av)
                walk(v)
        elif isinstance(node, list):
            for it in node:
                walk(it)
    walk(template)
    return set(found)


def _first(allowed, *cands):
    for c in cands:
        if c in allowed:
            return c
    return None


def solve(client, template, app_id):
    il = client.inlist
    app = client.sql("SELECT * FROM liquor_applications WHERE application_id=" + il([app_id]))[0]
    loc, lc = app["location_id"], app["license_class"]
    sett = client.sql("SELECT * FROM liquor_settlements WHERE location_id=" + il([loc]))
    inc = client.sql("SELECT * FROM liquor_incidents WHERE location_id=" + il([loc]))
    ev = client.sql("SELECT * FROM liquor_site_evidence WHERE location_id=" + il([loc]))
    priv = client.sql("SELECT * FROM liquor_privileges WHERE license_class=" + il([lc]))
    for s in sett:
        s["ctrl"] = json.loads(s["controls_json"])
    active = [s for s in sett if s["ctrl"].get("active")]

    covered_enum = _allowed(template, "covered_risk_codes")
    gap_enum = _allowed(template, "verification_gap_codes")
    esc_enum = _allowed(template, "escalation_trigger_codes")
    check_enum = _allowed(template, "check_code")

    # --- derivable ---
    std_oblig = sorted({p["obligation_code"] for p in priv if p["standard_required"] == 1})
    loc_controls = sorted({c for s in active for c in s["ctrl"].get("controls", [])})
    same_premises = any(s["basis_code"] == "SAME_PREMISES" for s in active)

    # --- covered risks: active controls -> risk (pick spelling from enum) ---
    CTRL_RISK = {"NOISE": ["NOISE"], "PATIO": ["PATIO_BOUNDARY", "PATIO"],
                 "HOURS": ["AFTER_HOURS"], "CCTV": ["CAMERA_COVERAGE"],
                 "ID_CHECK": ["ID_CHECK"], "FOOD_SERVICE": ["FOOD_SERVICE_GAP"],
                 "SECURITY": ["PUBLIC_SAFETY", "ASSAULT"]}
    covered = set()
    for c in loc_controls:
        code = _first(covered_enum, *CTRL_RISK.get(c, []))
        if code:
            covered.add(code)
    if same_premises:
        sp = _first(covered_enum, "SAME_PREMISES")
        if sp:
            covered.add(sp)
    covered = sorted(covered)

    # --- verification gaps ---
    by_code = {}
    for e in ev:
        by_code.setdefault(e["evidence_code"], []).append(e)

    def has(code, status):
        return any(e["status"] == status for e in by_code.get(code, []))

    def present(code):
        return code in by_code

    def latest(code):
        rows = by_code.get(code, [])
        return max(rows, key=lambda e: e["evidence_date"]) if rows else None

    gaps = set()

    def addgap(*cands):
        c = _first(gap_enum, *cands)
        if c:
            gaps.add(c)

    if has("CONTROL_SIGNAGE", "conflicting"):
        addgap("CONTROL_SIGNAGE_CONFLICTING")
    lcs = latest("CONTROL_SIGNAGE")
    if loc_controls and (lcs is None or lcs["status"] in ("missing", "stale")):
        addgap("CONTROL_SIGNAGE_CURRENT_MISSING", "control_signage_missing")
    if has("FLOOR_PLAN", "conflicting"):
        addgap("FLOOR_PLAN_CONFLICTING", "floor_plan_conflicting")
    if has("FLOOR_PLAN", "stale"):
        addgap("FLOOR_PLAN_STALE")
    for e in by_code.get("POLICE_MEMO", []):
        note = (e.get("notes") or "").lower()
        if e["status"] == "conflicting":
            addgap("POLICE_MEMO_CONFLICTING")
        if "old" in note or "identity" in note or "name" in note:
            addgap("police_memo_identity_note")
    if has("NEIGHBOR_NOTICE", "missing"):
        addgap("NEIGHBOR_NOTICE_MISSING", "neighbor_notice_missing")
    if has("SITE_PHOTO", "missing"):
        addgap("SITE_PHOTO_MISSING", "site_photo_missing")
    if has("TAX_CLEARANCE", "missing"):
        addgap("TAX_CLEARANCE_MISSING")
    # expected-but-absent evidence (camera / food service emphasis)
    if not present("CCTV") and not present("CAMERA"):
        addgap("camera_evidence_missing")
    if "FOOD_SERVICE" in std_oblig and not present("FOOD_SERVICE"):
        addgap("food_service_evidence_missing")
    if any(i["status"] in ("open", "referred") for i in inc):
        addgap("OPEN_INCIDENT_FOLLOW_UP")
    if any(i["risk_code"] == "TAX_HOLD" and i["status"] in ("open", "referred") for i in inc):
        addgap("tax_hold_unresolved")
    if any(s["basis_code"] == "NOISE" for s in active) or any(i["risk_code"] == "AFTER_HOURS" for i in inc):
        addgap("late_night_monitoring_needed")
    gaps = sorted(gaps)

    # --- escalation triggers ---
    esc = set()

    def adde(*cands):
        c = _first(esc_enum, *cands)
        if c:
            esc.add(c)

    if any(g in gaps for g in ("CONTROL_SIGNAGE_CURRENT_MISSING", "CONTROL_SIGNAGE_CONFLICTING", "control_signage_missing")):
        adde("CONTROL_SIGNAGE_NOT_VERIFIED")
    if "camera_evidence_missing" in gaps:
        adde("missing_camera_coverage")
    if "food_service_evidence_missing" in gaps:
        adde("food_service_not_available")
    if "tax_hold_unresolved" in gaps:
        adde("open_tax_hold_uncleared")
    if any(i["risk_code"] == "MINOR_SALE" and i["status"] in ("open", "referred") for i in inc):
        adde("REFERRED_MINOR_SALE_UNRESOLVED", "minor_sale")
    if any(i["risk_code"] == "ASSAULT" and i["status"] in ("open", "referred") for i in inc):
        adde("unreported_violent_incident")
    if any(i["severity"] == "high" and i["status"] in ("open", "referred") for i in inc):
        adde("MAJOR_INCIDENT_REPORTED")
    if "NOISE" in loc_controls or "PATIO" in loc_controls:
        adde("noise_or_patio_breach")
    esc = sorted(esc)

    # --- posture ---
    if any(i["severity"] == "high" and i["status"] in ("open", "referred") for i in inc):
        posture = "deny"
    elif gaps:
        posture = "request_follow_up"
    else:
        posture = "issue_restricted"

    # --- first 90 day plan ---
    plan = []
    seen = set()

    def addcheck(cands, timing):
        c = _first(check_enum, *cands)
        if c and (c, timing) not in seen:
            seen.add((c, timing))
            plan.append({"check_code": c, "timing": timing})

    if any(g in gaps for g in ("camera_evidence_missing",)):
        addcheck(["camera_export_test", "security_cctv_walkthrough"], "first_30_days")
    if "tax_hold_unresolved" in gaps:
        addcheck(["tax_clearance_review", "tax_clearance_check"], "first_30_days")
    if any(g in gaps for g in ("CONTROL_SIGNAGE_CURRENT_MISSING", "CONTROL_SIGNAGE_CONFLICTING", "control_signage_missing")):
        addcheck(["control_signage_recheck", "control_signage_review"], "first_30_days")
    if any(g in gaps for g in ("POLICE_MEMO_CONFLICTING", "police_memo_identity_note")):
        addcheck(["police_memo_follow_up"], "first_30_days")
    if "FOOD_SERVICE" in std_oblig:
        addcheck(["food_service_check", "food_service_service_area_check"], "days_31_60")
    if "NOISE" in loc_controls or "PATIO" in loc_controls:
        addcheck(["noise_patio_boundary_check", "noise_log_review", "patio_boundary_check"], "days_31_60")
    if "late_night_monitoring_needed" in gaps:
        addcheck(["late_night_closing_visit", "after_hours_visit"], "days_31_60")
    if "ID_CHECK" in std_oblig:
        addcheck(["id_check_observation"], "days_61_90")
    if any(i["status"] in ("open", "referred") for i in inc):
        addcheck(["incident_log_review"], "days_61_90")
    # sort per the common template rule (ascending by check_code)
    plan = sorted(plan, key=lambda p: p["check_code"])

    return {
        "application_id": app_id,
        "recommended_posture": posture,
        "same_premises_basis_applies": same_premises,
        "covered_risk_codes": covered,
        "verification_gap_codes": gaps,
        "standard_obligation_codes": std_oblig,
        "location_specific_control_codes": loc_controls,
        "first_90_day_plan": plan,
        "escalation_trigger_codes": esc,
    }
