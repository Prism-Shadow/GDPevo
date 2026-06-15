"""
Crescent Finance Ops helper library (validated against train answers 001-005).

Import the pieces you need, or copy the relevant formulas inline. Every function
here was reverse-engineered from the live read-only API and confirmed to reproduce
the standard answers exactly. Read SKILL.md for the business reasoning behind each rule.

Rounding: ALWAYS round-half-up (not Python banker's rounding). Use r2/r4 below.
Aggregate first, round once at the very end of a metric -- never round intermediate
per-row values before summing.
"""
import json
import urllib.request
from collections import defaultdict, Counter
from decimal import Decimal, ROUND_HALF_UP

BASE_URL = "http://127.0.0.1:8028"  # confirm against payloads/environment_access.json


def get(path, base=BASE_URL):
    with urllib.request.urlopen(base + path, timeout=20) as r:
        return json.load(r)


def r2(x):
    """Currency: round half-up to 2 decimals, return float."""
    return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def r4(x):
    """Decimal percent / ratio: a FRACTION rounded half-up to 4 decimals.
    8.95% -> 0.0895 (NOT 8.95). Compute as (new-old)/old, then r4()."""
    return float(Decimal(str(x)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


# ---------------------------------------------------------------------------
# FINANCE (tasks: branch close report, regional view)
# ---------------------------------------------------------------------------
ACCT_BY_CAT = {
    "revenue": ["product_revenue", "service_revenue"],
    "cogs": ["direct_materials_cogs", "direct_labor_cogs"],
    "sga": ["sales_sga", "admin_sga", "occupancy_sga"],
    "allocations": ["shared_service_allocations"],
}


def finance_setup(base=BASE_URL):
    records = get("/api/finance/records", base)
    branches = get("/api/finance/branches", base)
    pmap = get("/api/finance/period-map", base)
    fy_periods = defaultdict(list)
    for p in pmap:
        fy_periods[p["fiscal_year"]].append(p["period"])
    idx = {(r["branch_id"], r["account"]): r["values"] for r in records}
    reg_branches = defaultdict(list)
    for b in branches:
        reg_branches[b["region_id"]].append(b["branch_id"])
    return dict(records=records, branches=branches, pmap=pmap,
                fy_periods=dict(fy_periods), idx=idx, reg_branches=dict(reg_branches))


def acct_sum(idx, branch, account, periods):
    v = idx.get((branch, account), {})
    return sum(v.get(p, 0.0) for p in periods)


def cat_sum(idx, branch, cat, periods):
    return sum(acct_sum(idx, branch, a, periods) for a in ACCT_BY_CAT[cat])


def income_statement(idx, branch, periods):
    rev = cat_sum(idx, branch, "revenue", periods)
    cogs = cat_sum(idx, branch, "cogs", periods)
    sga = cat_sum(idx, branch, "sga", periods)
    alloc = cat_sum(idx, branch, "allocations", periods)
    gm = rev - cogs
    ebitda = gm - sga - alloc
    return dict(revenue=rev, cogs=cogs, gross_margin=gm, sga=sga,
                allocations=alloc, ebitda=ebitda)


def region_income_statement(idx, reg_branches, region, periods):
    agg = dict(revenue=0.0, cogs=0.0, gross_margin=0.0, sga=0.0, allocations=0.0, ebitda=0.0)
    for b in reg_branches[region]:
        i = income_statement(idx, b, periods)
        for k in agg:
            agg[k] += i[k]
    return agg


def arpu(idx, branch, periods):
    """FY revenue / sum(active_customers over the FY months)."""
    rev = cat_sum(idx, branch, "revenue", periods)
    ac = acct_sum(idx, branch, "active_customers", periods)
    return rev / ac if ac else 0.0


def sales_per_labor_headcount(idx, branch, periods):
    """FY revenue / sum(labor_headcount over the FY months). Region version: sum both numerator
    (region revenue) and denominator (region labor_headcount) across branches, then divide."""
    rev = cat_sum(idx, branch, "revenue", periods)
    lh = acct_sum(idx, branch, "labor_headcount", periods)
    return rev / lh if lh else 0.0


# ---------------------------------------------------------------------------
# COMPENSATION (tasks: current-year summary, board forecast)
# ---------------------------------------------------------------------------
def comp_setup(base=BASE_URL):
    rb = get("/api/compensation/rate-book", base)
    return rb


def seniority_weekly(rate_book, years):
    for band in rate_book["seniority_weekly"]:
        lo, hi = band["min_years"], band["max_years"]
        if years >= lo and (hi is None or years <= hi):
            return band["weekly_amount"]
    return 0.0


def comp_year_totals(roster, rate_book, mws, title_mult, sen_scale, os_scale, years_add):
    """Return (paytype_totals, quarter_totals) summed over the roster for ONE year.
    Pass mws=base scale, scales=1.0 and years_add=0 for the CURRENT year.
    For forecasts, escalate scales (compounded) and years_add per SKILL.md."""
    tp_pct = rate_book["title_premium_pct"]
    pay_types = rate_book["pay_types"]
    QS = ["Q1", "Q2", "Q3", "Q4"]
    pt = {p: 0.0 for p in pay_types}
    qt = {q: 0.0 for q in QS}
    for e in roster:
        yrs = e["years_of_service"] + years_add
        sw = seniority_weekly(rate_book, yrs) * sen_scale
        combined = e.get("combined_overscale_includes_title", False)
        title_amt_per_week = 0.0
        if not combined and e.get("title"):
            title_amt_per_week = mws * tp_pct.get(e["title"], 0.0) * title_mult
        os_per_week = e.get("overscale_weekly", 0.0) * os_scale
        for q in QS:
            w = e["weeks_by_quarter"].get(q, 0)
            pt["Minimum Weekly Scale"] += mws * w
            pt["Titled Position Premium"] += title_amt_per_week * w
            pt["Seniority"] += sw * w
            pt["Overscale"] += os_per_week * w
            qt[q] += (mws + title_amt_per_week + sw + os_per_week) * w
    return pt, qt


def comp_annual_total(quarter_totals):
    """Annual total = SUM OF THE 2-DECIMAL-ROUNDED QUARTER TOTALS, not r2 of the raw sum.
    These differ by a cent in some forecast years (e.g. y+1). Match the answer convention."""
    return r2(sum(r2(v) for v in quarter_totals.values()))


def comp_counts(roster, standard_quarter_weeks=13):
    combined = sum(1 for e in roster if e.get("combined_overscale_includes_title"))
    partial = sum(1 for e in roster
                  if any(w != standard_quarter_weeks for w in e["weeks_by_quarter"].values()))
    return combined, partial


# ---------------------------------------------------------------------------
# PAYROLL (task: theatre weekly payroll / CBA control)
# ---------------------------------------------------------------------------
def payroll_setup(base=BASE_URL):
    return get("/api/payroll/rate-book", base)


def _cat_for(stype):
    if stype == "Performance":
        return "performance"
    if stype == "Audit":
        return "audit"
    if stype == "Rehearsal":
        return "rehearsal"
    if "Sound Check" in stype:
        return "sound_check"
    return None


def _base_pay(rate_book, stype, dur):
    if stype == "Rehearsal":
        return rate_book["service_rates"]["Rehearsal"] * max(dur, 3.0)  # 3-hr minimum call
    return rate_book["service_rates"][stype]  # per service


def payroll_weekly(production, rate_book):
    """Reproduces the weekly payroll package. Returns the full result dict.
    Validated to reproduce train answer 003 exactly."""
    rates = rate_book["service_rates"]
    prem = rate_book["premium_pct"]
    wk_guar = rate_book["weekly_guarantee"]
    limits = rate_book["service_time_limits"]
    thr = rate_book["conflict_thresholds"]
    sched = {s["service_id"]: s for s in production["schedule"]}

    per_mus = []
    cat_tot = defaultdict(float)
    for m in production["roster"]:
        cats = defaultdict(float)
        perf_base = 0.0
        for sid in m["assigned_service_ids"]:
            s = sched[sid]
            bp = _base_pay(rate_book, s["service_type"], s["duration_hours"])
            c = _cat_for(s["service_type"])
            cats[c] += bp
            if c == "performance":
                perf_base += bp
        # SUBSTITUTE: performance category gets +0.5x of perf base, AND a separate
        # substitute_adjustment line = +0.5x of perf base.
        if m.get("substitute") and perf_base > 0:
            cats["performance"] += perf_base * 0.5
            cats["substitute_adjustment"] += perf_base * 0.5
        # premium base = base service pay AFTER any substitute uplift to performance
        premium_base = sum(cats[k] for k in ("performance", "audit", "rehearsal", "sound_check"))
        pct = 0.0
        if m.get("lead") or m.get("principal"):
            pct += prem["principal_or_lead"]
        if m.get("quartet"):
            pct += prem["quartet"]
        if m.get("electronic"):
            pct += prem["electronic"]
        premium_amt = premium_base * pct
        if premium_amt:
            cats["premium"] += premium_amt
        dbl = m.get("doubles", 0)
        if dbl > 0:
            dpct = prem["first_double"] + prem["additional_double"] * (dbl - 1)
            cats["doubles"] += premium_base * dpct
        if m.get("vacation_eligible"):
            vbase = premium_base + cats.get("premium", 0.0) + cats.get("doubles", 0.0)
            cats["vacation"] += prem["vacation"] * vbase
        # guarantee: only guaranteed regular players (NON-substitute) when base service pay < guarantee
        if not m.get("substitute") and premium_base < wk_guar:
            cats["guarantee_adjustment"] += wk_guar - premium_base
        total = sum(cats.values())
        per_mus.append({
            "musician_id": m["musician_id"],
            "name": m["name"],
            "categories": {k: r2(v) for k, v in cats.items() if abs(v) > 1e-9},
            "total": r2(total),
        })
        for k, v in cats.items():
            cat_tot[k] += v

    per_mus.sort(key=lambda x: x["musician_id"])
    weekly = sum(x["total"] for x in per_mus)
    svc_counts = dict(Counter(s["service_type"] for s in production["schedule"]))

    def tmin(t):
        h, mn = t.split(":")
        return int(h) * 60 + int(mn)

    sc_expected = {"1hr Sound Check": 1.0, "2hr Sound Check": 2.0}
    flags = set()
    for s in production["schedule"]:
        st = s["service_type"]
        if st == "Rehearsal":
            if tmin(s["start_time"]) < tmin(thr["rehearsal_earliest_start"]):
                flags.add("REHEARSAL_EARLY_START")
            if tmin(s["end_time"]) > tmin(thr["rehearsal_latest_end"]):
                flags.add("REHEARSAL_LATE_END")
        lim = limits.get(st)
        if lim is not None and s["duration_hours"] > lim:
            flags.add("SERVICE_OVER_TIME_LIMIT")
        if "Sound Check" in st and abs(s["duration_hours"] - sc_expected[st]) > 1e-9:
            flags.add("SOUND_CHECK_DURATION_MISMATCH")

    return {
        "production_id": production["production_id"],
        "service_counts": svc_counts,
        "category_totals": {k: r2(v) for k, v in sorted(cat_tot.items())},
        "weekly_total": r2(weekly),
        "conflict_flags": sorted(flags),
        "per_musician": per_mus,
        "top_paid_musician_id": max(per_mus, key=lambda x: x["total"])["musician_id"],
    }
