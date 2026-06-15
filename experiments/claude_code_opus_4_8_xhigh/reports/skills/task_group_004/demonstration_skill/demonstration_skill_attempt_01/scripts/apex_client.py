#!/usr/bin/env python3
"""ApexCloud Retention Operations API client + canonical metric helpers.

Encodes the data-sourcing rules from SKILL.md so each metric is pulled the way the
gold answers expect. This is a STARTING POINT, not a turnkey solver: always confirm
the per-task answer_template.json and adjust windows / fields as needed.

Quick CLI smoke test:
    python3 scripts/apex_client.py acct_northstar_finance 2026-04 2026-06 2026-06-30
prints current_arr / latest_nps / clean_ticket_count / overdue_balance for one
account so you can eyeball that the rules are wired correctly.
"""
import csv
import io
import json
import sys
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8074"


# ---------------------------------------------------------------- raw fetch
def _get(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return json.loads(r.read().decode())


def _get_csv(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return list(csv.DictReader(io.StringIO(r.read().decode())))


def accounts():
    return _get("/api/accounts")["accounts"]


def account(account_id):
    return _get("/api/accounts/%s" % account_id)


def metrics(account_id, start_month, end_month):
    """Monthly rows. start/end are 'YYYY-MM'."""
    q = urllib.parse.urlencode({"start": start_month, "end": end_month})
    return _get("/api/accounts/%s/metrics?%s" % (account_id, q))["metrics"]


def tickets(account_id, start_date, end_date):
    q = urllib.parse.urlencode({"start": start_date, "end": end_date})
    return _get("/api/accounts/%s/tickets?%s" % (account_id, q))["tickets"]


def nps(account_id, start_date, end_date):
    q = urllib.parse.urlencode({"start": start_date, "end": end_date})
    return _get("/api/accounts/%s/nps?%s" % (account_id, q))["nps_responses"]


def billing_snapshots(account_id=None, as_of=None):
    params = {}
    if account_id:
        params["account_id"] = account_id
    if as_of:
        params["as_of"] = as_of
    q = ("?" + urllib.parse.urlencode(params)) if params else ""
    return _get("/api/billing/snapshots" + q)["snapshots"]


def ar_aging(as_of, region=None):
    params = {"as_of": as_of}
    if region:
        params["region"] = region
    return _get("/api/finance/ar-aging?" + urllib.parse.urlencode(params))["ar_aging"]


def opportunities(start_date, end_date, region=None):
    params = {"start": start_date, "end": end_date}
    if region:
        params["region"] = region
    return _get("/api/opportunities?" + urllib.parse.urlencode(params))["opportunities"]


def hr_summary(quarter, region=None):
    params = {"quarter": quarter}
    if region:
        params["region"] = region
    return _get("/api/hr/summary?" + urllib.parse.urlencode(params))["hr_summary"]


def event_performance(event, quarter):
    q = urllib.parse.urlencode({"event": event, "quarter": quarter})
    return _get("/api/events/performance?" + q)["event_performance"]


def churn_csv(which):
    """which in {'train','validation','candidates'}."""
    return _get_csv("/exports/churn/%s.csv" % which)


# ---------------------------------------------------------------- canonical metrics
def current_arr(account_id, as_of):
    """Latest POSTED billing snapshot whose as_of == the quarter-end date.

    Query with the exact quarter-end date; the API matches as_of exactly.
    Falls back to the latest posted snapshot at-or-before as_of if the exact-date
    query is empty (defensive; the exact-date query is the documented path).
    """
    snaps = billing_snapshots(account_id=account_id, as_of=as_of)
    posted = [s for s in snaps if s.get("posted")]
    if posted:
        return round(posted[0]["billing_arr"], 2)
    alls = [s for s in billing_snapshots(account_id=account_id)
            if s.get("posted") and s["as_of"] <= as_of]
    if not alls:
        return None
    alls.sort(key=lambda s: s["as_of"])
    return round(alls[-1]["billing_arr"], 2)


def is_clean_ticket(t):
    """Hygiene rule: drop spam, duplicate, and cancelled tickets."""
    return not (t.get("is_spam") or t.get("is_duplicate") or t.get("status") == "cancelled")


def clean_ticket_count(account_id, start_date, end_date):
    return sum(1 for t in tickets(account_id, start_date, end_date) if is_clean_ticket(t))


def latest_nps(account_id, start_date, end_date):
    """Most recent non-retracted response score, else None."""
    valid = [r for r in nps(account_id, start_date, end_date) if not r.get("retracted")]
    if not valid:
        return None
    valid.sort(key=lambda r: r["response_date"])
    return valid[-1]["score"]


def overdue_balance_from_row(row):
    """Older aging buckets only: 61_90 + 90_plus."""
    return round(row.get("61_90", 0.0) + row.get("90_plus", 0.0), 2)


def overdue_balance(account_id_or_legal_name, as_of, ar_rows=None):
    """Overdue balance for one customer. Pass either the CRM account_id (matched by
    aging_id) or the exact A/R customer_name."""
    rows = ar_rows if ar_rows is not None else ar_aging(as_of)
    for r in rows:
        if (account_id_or_legal_name in r.get("aging_id", "")
                or r.get("customer_name") == account_id_or_legal_name):
            return overdue_balance_from_row(r)
    return 0.0


def expansion_pipeline(account_id, start_date, end_date, opps=None):
    """Sum of OPEN opportunity amounts (close_date in window) for an account."""
    rows = opps if opps is not None else opportunities(start_date, end_date)
    return round(sum(o["amount"] for o in rows
                     if o.get("account_id") == account_id and o.get("state") == "open"), 2)


def link_ar_to_crm(customer_name, legal_to_id):
    """Exact customer_name -> CRM legal_name match. Returns account_id or None."""
    return legal_to_id.get(customer_name)


def legal_name_index():
    """Map CRM legal_name -> account_id for A/R linking."""
    return {a["legal_name"]: a["account_id"] for a in accounts()}


# ---------------------------------------------------------------- reason-code signals
def reason_signals(account_id, start_month, end_month, start_date, end_date,
                   as_of, assessment_date, ar_rows=None, opps=None):
    """Compute the boolean reason-code signals for one account. Thresholds match the
    rules verified in SKILL.md; treat near-threshold results as edge cases."""
    from datetime import date
    acct = account(account_id)
    ms = metrics(account_id, start_month, end_month)
    sla = [m["sla_compliance"] for m in ms if m.get("sla_compliance") is not None]
    usage = [m["product_usage"] for m in ms if m.get("product_usage") is not None]
    ln = latest_nps(account_id, start_date, end_date)
    od = overdue_balance(account_id, as_of, ar_rows=ar_rows)
    exp = expansion_pipeline(account_id, start_date, end_date, opps=opps)

    def days_to_renewal():
        try:
            y, m, d = map(int, acct["renewal_date"].split("-"))
            ay, am, ad = map(int, assessment_date.split("-"))
            return (date(y, m, d) - date(ay, am, ad)).days
        except Exception:
            return None

    dtr = days_to_renewal()
    usage_decline = bool(usage) and usage[-1] < usage[0]  # softest signal; verify monthly
    return {
        "overdue_receivable": od > 0,
        "clean_billings": od == 0,
        "renewal_window": dtr is not None and 0 <= dtr <= 90,
        "nps_drop": ln is not None and ln < 50,
        "sla_degradation": bool(sla) and min(sla) < 95,
        "usage_decline": usage_decline,
        "low_tenure_high_churn": acct.get("contract_tenure_months", 999) <= 18,
        "expansion_offset": exp > 0,
        "_facts": {"latest_nps": ln, "overdue_balance": od, "expansion_pipeline": exp,
                   "days_to_renewal": dtr, "min_sla": min(sla) if sla else None,
                   "tenure": acct.get("contract_tenure_months"),
                   "segment": acct.get("segment"), "renewal_date": acct.get("renewal_date")},
    }


def primary_action(signals):
    """First matching rule wins (see SKILL §4)."""
    f = signals["_facts"]
    if f["overdue_balance"] and f["overdue_balance"] > 0:
        return "collections_followup"
    technical = signals["nps_drop"] or signals["usage_decline"] or (
        f["min_sla"] is not None and f["min_sla"] < 90)
    if technical:
        return "technical_recovery"
    if signals["renewal_window"]:
        return "renewal_save"
    return "no_action"


if __name__ == "__main__":
    if len(sys.argv) >= 5:
        aid, sm, em, asof = sys.argv[1:5]
        sd, ed = asof[:4] + "-" + sm[5:] + "-01", asof  # rough window
        print("account:", aid)
        print("current_arr:", current_arr(aid, asof))
        print("latest_nps:", latest_nps(aid, sd, ed))
        print("clean_ticket_count:", clean_ticket_count(aid, sd, ed))
        print("overdue_balance:", overdue_balance(aid, asof))
        sig = reason_signals(aid, sm, em, sd, ed, asof, asof)
        print("reason signals:", {k: v for k, v in sig.items() if v is True})
        print("primary_action:", primary_action(sig))
    else:
        print(json.dumps(_get("/api/health"), indent=2))
