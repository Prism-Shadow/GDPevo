#!/usr/bin/env python3
"""
Reference calculators for Crescent Finance Ops management-reporting tasks.

These are verified against the standard answers for the five task families:
  1. Branch close package          (finance/records)
  2. Current-year compensation     (compensation/rate-book + rosters)
  3. Theatre weekly payroll        (payroll/rate-book + productions)
  4. Regional reporting view       (finance/records)
  5. Board compensation forecast   (compensation/rate-book + rosters + scenarios)

Adapt the request parameters (branch/region/ensemble/scenario/production ids,
periods, years) to the specific task. ALWAYS pull live data from the API; never
hardcode entity values from these comments or from any memo.

Rounding: use HALF-UP (r2 / r4 below), NOT Python's default banker's round().
Currency -> 2 decimals. Percent/ratio fields -> FRACTION at 4 decimals (0.0895,
not 8.95).
"""
import json
import urllib.request
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict

BASE = "http://127.0.0.1:8028"  # read base_url from payloads/environment_access.json


def get(path):
    return json.load(urllib.request.urlopen(BASE + path))


def r2(x):
    return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def r4(x):
    return float(Decimal(str(x)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


# ---------------------------------------------------------------------------
# FINANCE (tasks 1 and 4)
# ---------------------------------------------------------------------------
# Income-statement line composition (account -> line). Read /api/finance/accounts
# to confirm category membership; these are the verified mappings.
REVENUE_ACCTS = ["product_revenue", "service_revenue"]
COGS_ACCTS = ["direct_materials_cogs", "direct_labor_cogs"]
SGA_ACCTS = ["sales_sga", "admin_sga", "occupancy_sga"]
ALLOC_ACCTS = ["shared_service_allocations"]


def load_finance():
    """Returns (B, region_of) where B[branch][account] = {period: value}."""
    recs = get("/api/finance/records")
    B = defaultdict(dict)
    region_of = {}
    for r in recs:
        B[r["branch_id"]][r["account"]] = r["values"]
        region_of[r["branch_id"]] = r["region_id"]
    return B, region_of


def fy_periods(fy, period_map):
    """List of M-periods belonging to a fiscal year, using the live period-map."""
    return [p["period"] for p in period_map if p["fiscal_year"] == fy]


def asum(B, branch, account, periods):
    vals = B[branch].get(account, {})
    return sum(vals.get(p, 0) for p in periods)


def line(B, branch, accounts, periods):
    return sum(asum(B, branch, a, periods) for a in accounts)


def income_statement(B, branches, periods):
    """branches may be one branch or a region's branch list (rollup = simple sum)."""
    if isinstance(branches, str):
        branches = [branches]
    rev = sum(line(B, b, REVENUE_ACCTS, periods) for b in branches)
    cogs = sum(line(B, b, COGS_ACCTS, periods) for b in branches)
    sga = sum(line(B, b, SGA_ACCTS, periods) for b in branches)
    alloc = sum(line(B, b, ALLOC_ACCTS, periods) for b in branches)
    gross = rev - cogs
    ebitda = gross - sga - alloc
    return dict(revenue=rev, cogs=cogs, gross_margin=gross, sga=sga,
                allocations=alloc, ebitda=ebitda)


def arpu(B, branches, periods):
    """FY revenue / SUM of monthly active_customers over the FY (sum, not avg)."""
    if isinstance(branches, str):
        branches = [branches]
    rev = sum(line(B, b, REVENUE_ACCTS, periods) for b in branches)
    cust = sum(asum(B, b, "active_customers", periods) for b in branches)
    return rev / cust


def sales_per_labor_headcount(B, branches, periods):
    """FY revenue / SUM of monthly labor_headcount over the FY (sum, not avg)."""
    if isinstance(branches, str):
        branches = [branches]
    rev = sum(line(B, b, REVENUE_ACCTS, periods) for b in branches)
    lh = sum(asum(B, b, "labor_headcount", periods) for b in branches)
    return rev / lh


# ---------------------------------------------------------------------------
# COMPENSATION (tasks 2 and 5)
# ---------------------------------------------------------------------------
def seniority_weekly(bands, years):
    for b in bands:
        lo, hi = b["min_years"], b["max_years"]
        if years >= lo and (hi is None or years <= hi):
            return b["weekly_amount"]
    return 0.0


def comp_year(roster, rate_book, scale, sen_mult=1.0, over_mult=1.0,
              title_mult=1.0, add_years=0):
    """Returns (quarter_totals, pay_type_totals) for one year (raw, unrounded).

    scale        = minimum weekly scale for the year (escalated for forecasts)
    *_mult       = cumulative (compounded) escalators for the year
    add_years    = years of service to add before seniority banding
                   (0=current, 1=year_plus_1, 2=year_plus_2)
    """
    title_pct = rate_book["title_premium_pct"]
    bands = rate_book["seniority_weekly"]
    pts = rate_book["pay_types"]
    qt = {"Q1": 0.0, "Q2": 0.0, "Q3": 0.0, "Q4": 0.0}
    ptt = {k: 0.0 for k in pts}
    for e in roster:
        years = e["years_of_service"] + add_years
        wq = e["weeks_by_quarter"]
        title = e.get("title")
        combined = e.get("combined_overscale_includes_title", False)
        over_wk = e.get("overscale_weekly", 0.0) * over_mult
        sen_wk = seniority_weekly(bands, years) * sen_mult
        # title premium only if titled AND overscale does not already absorb it
        tprem_wk = scale * title_pct[title] * title_mult if (title and not combined) else 0.0
        for qk in ("Q1", "Q2", "Q3", "Q4"):
            w = wq.get(qk, 0)
            qt[qk] += w * (scale + tprem_wk + sen_wk + over_wk)
            ptt["Minimum Weekly Scale"] += w * scale
            ptt["Titled Position Premium"] += w * tprem_wk
            ptt["Seniority"] += w * sen_wk
            ptt["Overscale"] += w * over_wk
    return qt, ptt


def annual_total(qt):
    """Sum of the FOUR ROUNDED quarter totals (not raw-sum-then-round)."""
    return r2(sum(r2(v) for v in qt.values()))


def comp_counts(roster):
    combined = sum(1 for e in roster if e.get("combined_overscale_includes_title"))
    partial = sum(1 for e in roster
                  if any(e["weeks_by_quarter"].get(x, 0) != 13
                         for x in ("Q1", "Q2", "Q3", "Q4")))
    return combined, partial


# ---------------------------------------------------------------------------
# PAYROLL (task 3)
# ---------------------------------------------------------------------------
def category_of(service_type):
    if service_type == "Rehearsal":
        return "rehearsal"
    if service_type == "Audit":
        return "audit"
    if service_type == "Performance":
        return "performance"
    if "Sound Check" in service_type:
        return "sound_check"
    return service_type.lower()


def base_service_pay(svc, rates):
    st = svc["service_type"]
    if st == "Rehearsal":
        # hourly with a 3-hour minimum call
        return max(svc["duration_hours"], 3.0) * rates["Rehearsal"]
    return rates[st]  # Performance / Audit / Sound Check are per-service


def payroll_week(prod, rate_book):
    rates = rate_book["service_rates"]
    prem = rate_book["premium_pct"]
    guarantee = rate_book["weekly_guarantee"]
    sched = {s["service_id"]: s for s in prod["schedule"]}

    cat_raw = defaultdict(float)
    per = []
    for m in prod["roster"]:
        cats = defaultdict(float)
        base = 0.0
        sub_adj = 0.0
        is_sub = m.get("substitute")
        for sid in m["assigned_service_ids"]:
            svc = sched[sid]
            st = svc["service_type"]
            bp = base_service_pay(svc, rates)
            if is_sub and st == "Performance":
                # substitute paid 1.5x performance; the +0.5 is reported separately
                cats["performance"] += bp * 1.5
                base += bp * 1.5
                sub_adj += bp * 0.5
            else:
                cats[category_of(st)] += bp
                base += bp
        if sub_adj:
            cats["substitute_adjustment"] += sub_adj
        # doubles: 25% first extra instrument, +10% each additional
        d = m.get("doubles", 0)
        dpct = (prem["first_double"] if d >= 1 else 0.0)
        if d >= 2:
            dpct += prem["additional_double"] * (d - 1)
        # other premiums (all on base service pay, before vacation)
        ppct = 0.0
        if m.get("electronic"):
            ppct += prem["electronic"]
        if m.get("principal") or m.get("lead"):
            ppct += prem["principal_or_lead"]
        if m.get("quartet"):
            ppct += prem["quartet"]
        doubles_amt = base * dpct
        premium_amt = base * ppct
        if doubles_amt:
            cats["doubles"] += doubles_amt
        if premium_amt:
            cats["premium"] += premium_amt
        # vacation: 4% of base service pay + premiums, if eligible
        if m.get("vacation_eligible"):
            cats["vacation"] += (base + doubles_amt + premium_amt) * prem["vacation"]
        # guarantee: regular (non-substitute) players, top-up to weekly_guarantee
        # measured against BASE service pay (premiums/vacation excluded)
        if not is_sub:
            ga = guarantee - base
            if ga > 0:
                cats["guarantee_adjustment"] += ga
        total = r2(sum(cats.values()))  # round the RAW category sum once
        per.append({
            "musician_id": m["musician_id"],
            "name": m["name"],
            "total": total,
            "categories": {k: r2(v) for k, v in cats.items() if r2(v) != 0},
        })
        for k, v in cats.items():
            cat_raw[k] += v

    per.sort(key=lambda p: p["musician_id"])
    category_totals = {k: r2(v) for k, v in cat_raw.items()}
    weekly_total = r2(sum(p["total"] for p in per))
    service_counts = defaultdict(int)
    for s in prod["schedule"]:
        service_counts[s["service_type"]] += 1
    top = max(per, key=lambda p: p["total"])["musician_id"]
    return per, category_totals, weekly_total, dict(service_counts), top


def conflict_flags(prod, rate_book):
    th = rate_book["conflict_thresholds"]
    limits = rate_book["service_time_limits"]
    flags = set()
    for s in prod["schedule"]:
        st = s["service_type"]
        if st == "Rehearsal":
            if s["start_time"] < th["rehearsal_earliest_start"]:
                flags.add("REHEARSAL_EARLY_START")
            if s["end_time"] > th["rehearsal_latest_end"]:
                flags.add("REHEARSAL_LATE_END")
        if st in limits and s["duration_hours"] > limits[st]:
            flags.add("SERVICE_OVER_TIME_LIMIT")
        if "Sound Check" in st:
            expected = 1.0 if st.startswith("1hr") else 2.0
            if abs(s["duration_hours"] - expected) > 1e-9:
                flags.add("SOUND_CHECK_DURATION_MISMATCH")
    return sorted(flags)
