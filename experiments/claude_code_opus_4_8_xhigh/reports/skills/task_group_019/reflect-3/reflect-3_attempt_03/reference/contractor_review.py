"""Family A - contractor batch eligibility review (reference implementation).

Usage:
    from contractor_review import solve
    answer = solve(client, template, ["C-XXX-001", ...], review_date="2025-07-18")

`client` is an env_client.EnvClient; `template` is the parsed
answer_template.json (used only to pick the exact code spellings this task
expects). `review_date` may be None when the prompt gives no date.

Only the structural logic is authoritative; determination/risk/policy_impacted
follow the rules documented in SKILL.md.
"""
import json


# For each semantic condition, list candidate code spellings most-preferred
# first; solve() keeps whichever one actually appears in the template.
DEF_CANDIDATES = {
    "no_bond": ["bond_cancelled", "no_active_bond"],
    "bond_short": ["bond_shortfall"],
    "ins_expired": ["insurance_expired"],
    "ins_not_current": ["insurance_not_current", "insurance_pending"],
    "ins_short": ["insurance_shortfall"],
    "endorse": ["endorsement_not_verified", "endorsement_missing", "endorsement_pending"],
    "endorse_missing": ["endorsement_missing", "endorsement_not_verified"],
    "endorse_pending": ["endorsement_pending", "endorsement_not_verified"],
    "experience": ["experience_shortfall"],
    "suspension": ["active_suspension"],
    "serious": ["open_serious_violation", "unresolved_serious_complaint"],
    "minor": ["open_minor_violation"],
    "doc_gap": ["inspection_doc_gap"],
    "safety": ["inspection_safety_recheck"],
}
ACT_CANDIDATES = {
    "no_bond": ["obtain_current_bond", "file_active_bond"],
    "bond_short": ["increase_bond_amount", "increase_bond"],
    "ins_expired": ["renew_insurance", "provide_current_insurance"],
    "ins_not_current": ["provide_current_insurance", "verify_insurance_binding"],
    "ins_short": ["increase_insurance_amount", "increase_insurance"],
    "endorse": ["verify_endorsement", "obtain_required_endorsement"],
    "endorse_missing": ["obtain_required_endorsement", "verify_endorsement"],
    "endorse_pending": ["verify_pending_endorsement", "verify_endorsement"],
    "experience": ["submit_experience_evidence", "document_experience"],
    "suspension": ["board_review_suspension", "clear_suspension"],
    "serious": ["resolve_serious_violation", "resolve_complaint"],
    "minor": ["resolve_minor_violation_review"],
    "doc_gap": ["clear_document_gap"],
    "safety": ["complete_safety_recheck"],
    "board": ["board_review"],
}


def _find_allowed(node, field):
    """Recursively find the allowed_values list nested under key `field`."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == field and isinstance(v, dict) and "allowed_values" in v:
                return v["allowed_values"]
            r = _find_allowed(v, field)
            if r is not None:
                return r
    elif isinstance(node, list):
        for it in node:
            r = _find_allowed(it, field)
            if r is not None:
                return r
    return None


def _picker(allowed, candidates):
    allowed = set(allowed or [])
    def pick(key):
        for c in candidates[key]:
            if c in allowed:
                return c
        return None
    return pick


def _policy_index(client):
    idx = {}
    for p in client.sql("SELECT rule_code, title, effective_date, details_json "
                        "FROM policies WHERE family='contractor'"):
        d = json.loads(p["details_json"])
        d["_title"] = p["title"]
        idx[p["rule_code"]] = d
    return idx


def _policy_for(app, pidx):
    want = "%s %s application standards" % (app["trade"], app["requested_class"])
    for d in pidx.values():
        if d.get("_title") == want:
            return d
    return None


def _legacy(pidx):
    for rc, d in pidx.items():
        if "minimum_bond_reduction" in d or "endorsement_required_for_specialty" in d:
            return d
    return {}


def solve(client, template, app_ids, review_date=None):
    app_ids = sorted(app_ids)
    q = client.inlist(app_ids)
    apps = {a["application_id"]: a for a in
            client.sql("SELECT * FROM contractor_applications WHERE application_id IN " + q)}
    plids = [a["prior_license_id"] for a in apps.values() if a.get("prior_license_id")]
    bonds = client.sql("SELECT * FROM contractor_bonds WHERE application_id IN " + q)
    ins = client.sql("SELECT * FROM contractor_insurance WHERE application_id IN " + q)
    corr = client.sql("SELECT * FROM contractor_correspondence WHERE related_application_id IN " + q)
    insp = client.sql("SELECT * FROM contractor_inspections WHERE related_application_id IN " + q)
    vcond = "related_application_id IN " + q
    if plids:
        vcond += " OR license_id IN " + client.inlist(plids)
    viol = client.sql("SELECT * FROM contractor_violations WHERE " + vcond)
    hist = client.sql("SELECT * FROM contractor_license_history WHERE license_id IN "
                      + client.inlist(plids)) if plids else []

    pidx = _policy_index(client)
    legacy = _legacy(pidx)
    dpick = _picker(_find_allowed(template, "deficiency_codes"), DEF_CANDIDATES)
    apick = _picker(_find_allowed(template, "required_actions"), ACT_CANDIDATES)

    decisions = []
    stale = set()
    for aid in app_ids:
        a = apps[aid]
        pol = _policy_for(a, pidx)
        plid = a.get("prior_license_id")
        defs, acts = set(), set()
        pi = False

        def flag(key, extra_action=None):
            dc = dpick(key)
            if dc:
                defs.add(dc)
            ac = apick(key)
            if ac:
                acts.add(ac)
            if extra_action:
                ea = apick(extra_action)
                if ea:
                    acts.add(ea)

        # bond
        abonds = [b for b in bonds if b["application_id"] == aid]
        active_b = [b for b in abonds if b["status"] == "active" and not b["cancel_date"]]
        if active_b:
            cur = max(active_b, key=lambda b: b["effective_date"])
            if pol and cur["amount"] < pol["minimum_bond"]:
                flag("bond_short")
                if pol["minimum_bond"] - legacy.get("minimum_bond_reduction", 0) <= cur["amount"]:
                    pi = True
        else:
            flag("no_bond")

        # insurance
        ains = [i for i in ins if i["application_id"] == aid]
        if review_date:
            current = [i for i in ains if i["status"] == "active" and i["expiration_date"] >= review_date]
        else:
            current = [i for i in ains if i["status"] == "active"]
        if current:
            cur = max(current, key=lambda i: i["expiration_date"])
            if pol and cur["amount"] < pol["minimum_insurance"]:
                flag("ins_short")
        else:
            pending = [i for i in ains if i["status"] == "pending"]
            lapsed = [i for i in ains if i["status"] == "active"]
            if pending or lapsed:
                flag("ins_not_current")
            else:
                flag("ins_expired")

        # endorsement
        if pol and pol.get("required_endorsement"):
            es = a["endorsement_status"]
            if es not in ("verified", "not_required"):
                if es == "missing":
                    flag("endorse_missing")
                elif es == "pending":
                    flag("endorse_pending")
                else:
                    flag("endorse")
                if a["requested_class"] == "Specialty" and not legacy.get("endorsement_required_for_specialty", True):
                    pi = True

        # experience
        if pol and a["years_experience"] < pol["minimum_years_experience"]:
            flag("experience")

        # suspension  (hard block)
        suspended = any(h["license_id"] == plid and h["status"] == "suspended" for h in hist) if plid else False
        if suspended:
            flag("suspension", extra_action="board")

        # open violations (serious = hard block)
        def linked(v):
            return v["related_application_id"] == aid or (plid and v["license_id"] == plid)
        serious = False
        for v in viol:
            if linked(v) and v["status"] == "open":
                if v["severity"] == "serious":
                    serious = True
                    flag("serious", extra_action="board")
                elif v["severity"] == "minor":
                    flag("minor")

        # inspections (only if the template carries these codes)
        for ip in insp:
            if ip["related_application_id"] == aid:
                if ip["finding_code"] == "DOC_GAP":
                    flag("doc_gap")
                elif ip["finding_code"] == "SAFETY_RECHECK":
                    flag("safety")

        # stale / unverified correspondence  (include distractor rows)
        for c in corr:
            if c["related_application_id"] == aid:
                note = (c.get("notes") or "").lower()
                if c.get("verified_by_agency", 0) == 0 or "stale" in note or "predates" in note:
                    stale.add(c["correspondence_id"])

        hard_block = serious or suspended
        determination = "DENY" if hard_block else ("HOLD" if defs else "APPROVE")
        risk = "high" if hard_block else ("medium" if defs else "low")

        decisions.append({
            "application_id": aid,
            "determination": determination,
            "deficiency_codes": sorted(defs),
            "required_actions": sorted(acts),
            "risk_tier": risk,
            "policy_impacted": pi,
        })

    summary = {
        "approve_count": sum(d["determination"] == "APPROVE" for d in decisions),
        "hold_count": sum(d["determination"] == "HOLD" for d in decisions),
        "deny_count": sum(d["determination"] == "DENY" for d in decisions),
        "high_risk_application_ids": sorted(d["application_id"] for d in decisions if d["risk_tier"] == "high"),
        "policy_impacted_application_ids": sorted(d["application_id"] for d in decisions if d["policy_impacted"]),
        "stale_or_unverified_correspondence_ids": sorted(stale),
    }
    return {"application_decisions": decisions, "summary": summary}
