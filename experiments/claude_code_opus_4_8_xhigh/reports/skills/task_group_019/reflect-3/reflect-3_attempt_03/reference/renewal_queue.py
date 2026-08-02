"""Family C - alcohol renewal manual-review queue (reference implementation).

Usage:
    from renewal_queue import solve
    answer = solve(client, license_prefix="AL-XXX-0", boundary="2025-04-10", size=10)

Matching, boundary filtering, distractor handling, counts/dates/id-lists and the
summary are authoritative. risk_tier / next_step_label / rank ordering follow the
consistent-heuristic scheme in SKILL.md.
"""
UNRESOLVED = {"open", "pending"}


def _invdate(d):
    if not d:
        return 0
    y, m, dd = d.split("-")
    return -(int(y) * 10000 + int(m) * 100 + int(dd))


def solve(client, license_prefix, boundary, size):
    il = client.inlist
    targets = {t["license_no"]: t for t in client.sql(
        "SELECT * FROM alcohol_licensees WHERE license_no LIKE '" + license_prefix + "%'")}
    tlnos = sorted(targets)
    preds = [t["successor_to"] for t in targets.values() if t.get("successor_to")]
    rows = client.sql("SELECT * FROM alcohol_violations WHERE license_no IN " + il(tlnos + preds))
    by_lic = {}
    for v in rows:
        by_lic.setdefault(v["license_no"], []).append(v)

    post_excluded = []
    entries = []
    for ln in tlnos:
        t = targets[ln]
        matched = []
        uncertain = False
        for v in by_lic.get(ln, []):
            (matched if v["violation_date"] <= boundary else post_excluded).append(
                v if v["violation_date"] <= boundary else v["violation_id"])
        succ = t.get("successor_to")
        if succ and succ in by_lic:
            for v in by_lic[succ]:
                if v["violation_date"] <= boundary:
                    matched.append(v)
                    uncertain = True
                else:
                    post_excluded.append(v["violation_id"])

        ordered = sorted(matched, key=lambda v: (v["violation_date"], v["violation_id"]))
        serious_unresolved = any(v["severity"] == "serious" and v["disposition"] in UNRESOLVED for v in matched)
        unpaid = any((v.get("fine_balance") or 0) > 0 and v["disposition"] in UNRESOLVED for v in matched)
        alert = any(v.get("alert_flag") == 1 for v in matched)

        if serious_unresolved:
            nxt, risk = "board_review", "high"
        elif unpaid:
            nxt, risk = "manual_fine_check", "high"
        elif alert:
            nxt, risk = "manual_ALERT_check", "medium"
        else:
            nxt, risk = "additional_record_check", "medium" if uncertain else "low"

        entries.append({
            "license_no": ln,
            "facility_name": t["facility_name"],
            "violation_count": len(matched),
            "most_recent_violation_date": max((v["violation_date"] for v in matched), default=None),
            "matched_violation_ids": [v["violation_id"] for v in ordered],
            "match_confidence": "uncertain" if uncertain else "exact",
            "risk_tier": risk,
            "next_step_label": nxt,
        })

    order = {"board_review": 0, "manual_fine_check": 1, "manual_ALERT_check": 2, "additional_record_check": 3}
    entries.sort(key=lambda e: (order[e["next_step_label"]],
                                _invdate(e["most_recent_violation_date"]),
                                e["license_no"]))
    queue = []
    for i, e in enumerate(entries[:size], 1):
        queue.append({"rank": i, **{k: e[k] for k in (
            "license_no", "facility_name", "violation_count", "most_recent_violation_date",
            "matched_violation_ids", "match_confidence", "risk_tier", "next_step_label")}})

    summary = {
        "queue_size": len(queue),
        "boundary_date": boundary,
        "post_boundary_violation_ids_excluded": sorted(set(post_excluded)),
        "close_or_uncertain_match_license_numbers": sorted(
            e["license_no"] for e in entries if e["match_confidence"] in ("close_address", "uncertain")),
        "board_review_license_numbers": sorted(
            e["license_no"] for e in entries if e["next_step_label"] == "board_review"),
    }
    return {"queue": queue, "summary": summary}
