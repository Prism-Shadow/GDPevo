#!/usr/bin/env python3
"""
ApexCloud Retention Operations - reusable helpers for the risk model and the
canonical data-source conventions. Import these functions or adapt them; they
encode the rules that produce the deterministic expected outputs.

Usage sketch:
    from retention_model import ApexClient, build_account_signals, risk_score, \
        risk_level, primary_action, reason_codes
    c = ApexClient("http://127.0.0.1:8074")
    sig = build_account_signals(c, "acct_x", assessment="2026-06-30",
                                months=["2026-04","2026-05","2026-06"],
                                ar_as_of="2026-06-30", quarter="2026-Q2")
    s = risk_score(sig); lvl = risk_level(s)

Nothing here is task-specific (no account lists, no per-account numbers).
"""
import csv
import io
import json
import urllib.request
from datetime import date


# ---------------------------------------------------------------- HTTP client
class ApexClient:
    def __init__(self, base):
        self.base = base.rstrip("/")

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=30) as r:
            return json.loads(r.read().decode())

    def get_csv(self, path):
        with urllib.request.urlopen(self.base + path, timeout=30) as r:
            return list(csv.DictReader(io.StringIO(r.read().decode())))


def _d(s):
    y, m, dd = map(int, s.split("-"))
    return date(y, m, dd)


# ---------------------------------------------------------- canonical sources
def current_arr(client, account_id, as_of):
    """Billing snapshot billing_arr as-of the assessment date (NOT contract/crm)."""
    snaps = client.get(f"/api/billing/snapshots?as_of={as_of}").get("snapshots", [])
    for s in snaps:
        if s["account_id"] == account_id:
            return round(s["billing_arr"], 2)
    return None


def latest_valid_nps(client, account_id, start, end):
    """Latest non-retracted /nps score; returns (latest, earlier_scores).
    Skips -1 sentinels. Returns (None, []) if no valid response."""
    resp = client.get(
        f"/api/accounts/{account_id}/nps?start={start}&end={end}"
    ).get("nps_responses", [])
    valid = [r for r in resp if not r.get("retracted") and r.get("score", -1) != -1]
    valid.sort(key=lambda r: r["response_date"])
    scores = [r["score"] for r in valid]
    return (scores[-1] if scores else None, scores[:-1])


def clean_tickets(client, account_id, start, end):
    """Tickets that are not spam, not duplicate, not cancelled (open counts)."""
    tk = client.get(
        f"/api/accounts/{account_id}/tickets?start={start}&end={end}"
    ).get("tickets", [])
    return [t for t in tk
            if not t["is_spam"] and not t["is_duplicate"] and t["status"] != "cancelled"]


def overdue_older(ar_row):
    """Older-bucket overdue = 61_90 + 90_plus ONLY (not full non-current)."""
    return round(ar_row.get("61_90", 0) + ar_row.get("90_plus", 0), 2)


def ar_index(client, as_of):
    """Map aging_id -> row. aging_id == AR-<account_id>-<quarter>."""
    rows = client.get(f"/api/finance/ar-aging?as_of={as_of}").get("ar_aging", [])
    return {r["aging_id"]: r for r in rows}


def sla_misses(clean):
    """Returns (fr_miss, res_miss): any clean ticket missing that SLA dimension."""
    fr = any(not t["first_response_sla_met"] for t in clean)
    res = any(not t["resolution_sla_met"] for t in clean)
    return fr, res


def qbr_sla_pct(clean):
    """QBR monthly SLA % = first_response_sla_met ratio over clean tickets (1 dp)."""
    if not clean:
        return None
    met = sum(1 for t in clean if t["first_response_sla_met"])
    return round(100 * met / len(clean), 1)


def q_open_expansion(client, account_id, q_start, q_end):
    """Sum of open opp amounts with close_date inside the quarter window."""
    opps = client.get(
        f"/api/opportunities?start={q_start}&end={q_end}"
    ).get("opportunities", [])
    return round(sum(o["amount"] for o in opps
                     if o["account_id"] == account_id and o["state"] == "open"
                     and q_start <= o["close_date"] <= q_end), 2)


# ------------------------------------------------------------ signal assembly
def build_account_signals(client, account_id, assessment, months, ar_as_of, quarter,
                          q_start=None, q_end=None):
    acct = client.get(f"/api/accounts/{account_id}")
    mt = client.get(
        f"/api/accounts/{account_id}/metrics?start={months[0]}&end={months[-1]}"
    )["metrics"]
    by_month = {m["month"]: m for m in mt}
    start = months[0] + "-01"
    end = months[-1] + "-28"  # any end inside the last month works for date-range filters
    clean = clean_tickets(client, account_id, start, end)
    fr_miss, res_miss = sla_misses(clean)
    latest_nps, earlier = latest_valid_nps(client, account_id, start, end)
    ar = ar_index(client, ar_as_of).get(f"AR-{account_id}-{quarter}", {})
    usage_latest = by_month.get(months[-1], {}).get("product_usage")
    sig = dict(
        account_id=account_id,
        segment=acct.get("segment"),
        lifecycle=acct.get("lifecycle_status"),
        tenure=acct.get("contract_tenure_months"),
        days_to_renewal=(_d(acct["renewal_date"]) - _d(assessment)).days,
        overdue_older=overdue_older(ar),
        latest_nps=latest_nps,
        earlier_nps=earlier,
        sla_miss_fr=fr_miss,
        sla_miss_res=res_miss,
        usage_latest=usage_latest,
        current_arr=current_arr(client, account_id, assessment),
    )
    if q_start and q_end:
        sig["expansion"] = q_open_expansion(client, account_id, q_start, q_end)
    return sig


# ----------------------------------------------------------------- the model
def flags(sig):
    nps = sig["latest_nps"]
    earlier = sig["earlier_nps"] or []
    nps_drop = (nps is not None and
                (nps < 40 or (nps < 50 and (not earlier or nps <= min(earlier)))))
    return dict(
        renewal_window=0 <= sig["days_to_renewal"] <= 90,
        overdue_receivable=sig["overdue_older"] > 0,
        nps_drop=bool(nps_drop),
        sla_degradation=sig["sla_miss_fr"] or sig["sla_miss_res"],
        usage_decline=sig["usage_latest"] is not None and sig["usage_latest"] < 65,
        low_tenure_high_churn=sig["tenure"] is not None and sig["tenure"] <= 18,
    )


def risk_score(sig):
    f = flags(sig)
    s = 0
    s += 25 if f["renewal_window"] else 0
    s += 20 if f["overdue_receivable"] else 0
    s += 10 if f["nps_drop"] else 0
    s += 15 if f["sla_degradation"] else 0
    s += 15 if f["usage_decline"] else 0
    if f["low_tenure_high_churn"]:
        s += 15 if sig["tenure"] <= 12 else 10
    if sig["lifecycle"] in ("renewal_risk", "paused", "implementation"):
        s += 5 if sig["lifecycle"] == "renewal_risk" else 0  # renewal_risk confirmed +5
    return min(s, 100)


def risk_level(score):
    if score >= 70:
        return "critical"
    if score >= 45:
        return "high"
    if score >= 30:
        return "medium"
    return "low"


def primary_action(sig, level, is_board=False):
    if is_board and level == "low":
        return "no_action"
    if sig["overdue_older"] > 0:
        return "collections_followup"
    if sig["sla_miss_fr"]:
        return "technical_recovery"
    f = flags(sig)
    if sig["sla_miss_res"] and (f["nps_drop"] or f["usage_decline"]):
        return "technical_recovery"
    if f["renewal_window"]:
        return "renewal_save"
    if sig["sla_miss_res"]:
        return "technical_recovery"
    return "nurture_monitor"


REASON_ORDER = ["renewal_window", "overdue_receivable", "nps_drop", "sla_degradation",
                "usage_decline", "low_tenure_high_churn"]


def reason_codes(sig, is_board=False):
    f = flags(sig)
    codes = [k for k in REASON_ORDER if f[k]]
    exp = sig.get("expansion", 0) or 0
    if is_board:
        if exp > 0:
            codes.append("expansion_offset")
    else:
        if sig["overdue_older"] == 0:
            codes.append("clean_billings")
        elif exp > 0:
            codes.append("expansion_offset")
    return codes


def order_accounts(records):
    """records: list of dicts with 'risk_score' and 'current_arr'. Sort risk desc, arr desc."""
    return sorted(records, key=lambda r: (-r["risk_score"], -(r["current_arr"] or 0)))


# ------------------------------------------------------------------ churn map
def churn_outreach(row):
    """Returns (outreach_action, reason_code) for a candidate CSV row."""
    if row.get("InvoicePastDue") == "Yes":
        return "collections_followup", "overdue_receivable"
    if int(row["tenure"]) <= 18:
        return "renewal_save", "low_tenure_high_churn"
    if float(row["UsageTrendPct"]) < 0:
        return "renewal_save", "usage_decline"
    if int(row["NPSLast"]) < 30:
        return "technical_recovery", "nps_drop"
    return "nurture_monitor", "clean_billings"


if __name__ == "__main__":
    import sys
    print("retention_model helpers loaded. Import and use; see references/risk_model.md.",
          file=sys.stderr)
