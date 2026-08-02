#!/usr/bin/env python3
"""
Reusable helper for the engineering-portfolio analysis environment.

It fetches the shared read-only API, applies the portfolio conventions
(category classification, primary/exclusion rules, SLA due/overdue math,
release rollups) and prints the computed primitives as JSON. It does NOT
know any task's answer_template; map its output into the exact template the
task ships (field names/enums differ per task).

Usage:
  # discover base URL + token from environment_access.md (or pass --base/--token)
  python portfolio_analysis.py mix     --scope-id train_001 \
        --teams "Platform Core,Identity Services" \
        --product-areas "Atlas Backend,Identity" --quarter 2025-Q4
  python portfolio_analysis.py sla     --teams "AppSec,Identity Services" \
        --categories "Security,Reliability" --as-of 2026-01-22 --window 21
  python portfolio_analysis.py release --release-id REL-ORION-2026-02

All ordering/rounding shown here matches the observed standard answers, but
always re-read the task prompt + answer_template for the exact required shape.
"""
import argparse, json, re, sys, urllib.request
from collections import Counter, defaultdict
from datetime import date

# ---- environment access -----------------------------------------------------

def load_access(path="environment_access.md"):
    """Parse base URL + X-Env-Token out of environment_access.md."""
    base, token = None, None
    try:
        text = open(path).read()
    except OSError:
        text = ""
    m = re.search(r"Base URL:\s*(\S+)", text)
    if m:
        base = m.group(1).rstrip("/")
    m = re.search(r"X-Env-Token:\s*(\S+)", text)
    if m:
        token = m.group(1)
    return base, token


def get(base, path):
    with urllib.request.urlopen(base + path, timeout=30) as r:
        return json.load(r)


def load_all(base):
    def lst(obj):
        if isinstance(obj, list):
            return obj
        for v in obj.values():
            if isinstance(v, list):
                return v
        return []
    return {
        "work_items": lst(get(base, "/api/work-items")),
        "mix_targets": lst(get(base, "/api/mix-targets")),
        "sla_policy": lst(get(base, "/api/sla-policy")),
        "releases": lst(get(base, "/api/releases")),
        "milestones": lst(get(base, "/api/milestones")),
        "blockers": lst(get(base, "/api/blockers")),
        "dependencies": lst(get(base, "/api/dependencies")),
    }

# ---- shared conventions -----------------------------------------------------

# Statuses that mean "work is completed / closed". Everything else that is not
# an explicit exclusion is treated as still-open.
COMPLETED = {"Closed", "Verified", "Done", "Deployed"}

# Portfolio category classification.
# Signals are read from AUTHORITATIVE fields only: work_type, labels, title.
# mirror_status and legacy_category are STALE/export fields and are IGNORED.
# Precedence (risk first): Security > Reliability > TechDebt > NewFeature.
# An item takes the highest-precedence category for which ANY signal matches.
CATEGORY_RULES = [
    ("Security",    {"Security", "Compliance"},
                    {"security", "cve", "encryption", "auth", "compliance"},
                    ["security", "cve", "encryption", "auth", "compliance"]),
    ("Reliability", {"Reliability", "Incident"},
                    {"reliability", "incident", "outage", "latency", "flaky"},
                    ["reliability", "incident", "outage", "latency", "flaky"]),
    ("TechDebt",    {"Refactor", "Chore", "Dependency"},
                    {"cleanup", "refactor", "migration", "dependency", "debt"},
                    ["cleanup", "refactor", "migration", "debt"]),
    ("NewFeature",  {"Feature", "Enhancement"},
                    {"feature", "rollout", "customer-request"},
                    ["feature", "rollout"]),
]


def classify(wi):
    wt = wi.get("work_type")
    labels = set(wi.get("labels") or [])
    title = (wi.get("title") or "").lower()
    for cat, wts, labs, words in CATEGORY_RULES:
        if wt in wts or (labels & labs) or any(w in title for w in words):
            return cat
    if wt == "Bug":          # Bug with no other signal -> Reliability
        return "Reliability"
    return "NewFeature"      # last-resort default


def is_duplicate(wi):
    return wi.get("status") == "Duplicate" or bool(wi.get("duplicate_of"))


def is_cancelled(wi):
    return wi.get("status") == "Cancelled"


def is_primary(wi):
    return not is_duplicate(wi) and not is_cancelled(wi)


def is_complete(wi):
    return wi.get("status") in COMPLETED


def d(s):
    return date(int(s[:4]), int(s[5:7]), int(s[8:10])) if s else None


def quarter_of(s):
    if not s:
        return None
    y, m = int(s[:4]), int(s[5:7])
    return "%d-Q%d" % (y, (m - 1) // 3 + 1)

# ---- Family A: portfolio mix ------------------------------------------------

def mix_report(wis, mix_targets, teams, product_areas, quarter, scope_id):
    teams, product_areas = set(teams), set(product_areas)
    target = next((t for t in mix_targets if t.get("scope_id") == scope_id), None)
    included, dup, canc = [], [], []
    for x in wis:
        if x.get("team") not in teams or x.get("product_area") not in product_areas:
            continue
        if quarter_of(x.get("closed_at")) != quarter:   # closed IN the quarter
            continue
        if is_cancelled(x):
            canc.append(x["id"]); continue
        if is_duplicate(x):
            dup.append(x["id"]); continue
        if not is_complete(x):                            # only closed work
            continue
        included.append(x)
    included.sort(key=lambda x: (x["closed_at"], x["id"]))
    cats = ["NewFeature", "TechDebt", "Reliability", "Security"]
    counts = Counter(classify(x) for x in included)
    n = len(included)
    tgt_key = {"NewFeature": "new_feature_pct", "TechDebt": "tech_debt_pct",
               "Reliability": "reliability_pct", "Security": "security_pct"}
    rows = []
    for c in cats:
        actual = round(counts.get(c, 0) * 100 / n, 1) if n else 0.0
        tpct = round((target[tgt_key[c]] * 100) if target else 0.0, 1)
        rows.append({"category": c, "count": counts.get(c, 0),
                     "actual_pct": actual, "target_pct": tpct,
                     "gap_pct": round(actual - tpct, 1)})
    neg = sorted([r for r in rows if r["gap_pct"] < 0], key=lambda r: r["gap_pct"])
    return {
        "included_work_item_ids": [x["id"] for x in included],
        "total_included": n,
        "category_counts": {c: counts.get(c, 0) for c in cats},
        "category_percentages": {r["category"]: r["actual_pct"] for r in rows},
        "gap_table": rows,
        "under_invested_categories": [r["category"] for r in neg],
        "largest_deficit_category": neg[0]["category"] if neg else None,
        "second_deficit_category": neg[1]["category"] if len(neg) > 1 else None,
        "excluded_duplicate_ids": sorted(dup),
        "excluded_cancelled_ids": sorted(canc),
        # union of same-scope distractors, ordered closed_at then id
        "excluded_distractor_ids": [x["id"] for x in sorted(
            [w for w in wis if w["id"] in set(dup) | set(canc)],
            key=lambda x: (x.get("closed_at") or "", x["id"]))],
    }

# ---- Family B: SLA aging ----------------------------------------------------

SEV_ORDER = {"S1": 0, "S2": 1, "S3": 2, "S4": 3}
AGING_BUCKETS = ["0-3", "4-7", "8-14", "15-30", "31+"]


def _bucket(age):
    if age <= 3:  return "0-3"
    if age <= 7:  return "4-7"
    if age <= 14: return "8-14"
    if age <= 30: return "15-30"
    return "31+"


def sla_report(wis, teams, categories, as_of, window):
    teams, categories = set(teams), set(categories)
    a = d(as_of)
    primary, dup_map = [], defaultdict(list)
    for x in wis:
        if x.get("team") not in teams or classify(x) not in categories:
            continue
        if is_cancelled(x):
            continue
        if is_duplicate(x):
            if x.get("duplicate_of"):
                dup_map[x["duplicate_of"]].append(x["id"])
            continue
        if d(x["created_at"]) > a:                 # not yet created at snapshot
            continue
        closed = d(x.get("closed_at"))
        closed_as_of = closed is not None and closed <= a
        if closed_as_of and (a - closed).days > window:
            continue                               # closed too long ago
        primary.append(x)

    def overdue(x):
        due = d(x["due_at"])
        closed = d(x.get("closed_at"))
        if closed is not None and closed <= a:
            return closed > due                    # closed after its due date
        return a > due                             # still open past due date

    ov = [x for x in primary if overdue(x)]
    buckets = {b: 0 for b in AGING_BUCKETS}
    for x in primary:
        closed = d(x.get("closed_at"))
        ref = closed if (closed is not None and closed <= a) else a
        buckets[_bucket((ref - d(x["created_at"])).days)] += 1
    team_ov = Counter(x["team"] for x in ov)
    pair = Counter((x["team"], x.get("owner") or "UNASSIGNED") for x in ov)
    escalation = sorted(ov, key=lambda x: (SEV_ORDER.get(x["severity"], 9),
                                           x["due_at"], x["id"]))
    hotspot = None
    if pair:
        (t, o), c = pair.most_common(1)[0]
        hotspot = {"team": t, "owner": o, "overdue_count": c}
    return {
        "included_primary_ids": sorted(x["id"] for x in primary),
        "overdue_primary_ids": sorted(x["id"] for x in ov),
        "aging_bucket_counts": buckets,
        "overdue_counts_by_severity": {s: sum(1 for x in ov if x["severity"] == s)
                                        for s in ["S1", "S2", "S3", "S4"]},
        "team_overdue_counts": [{"team": t, "overdue_count": team_ov.get(t, 0)}
                                for t in sorted(teams)],
        "top_hotspot": hotspot,
        "escalation_queue_ids": [x["id"] for x in escalation],
        "missing_owner_ids": sorted(x["id"] for x in primary if not x.get("owner")),
        "duplicate_clusters": [{"primary_id": k, "duplicate_ids": sorted(v)}
                               for k, v in sorted(dup_map.items())
                               if k in {x["id"] for x in primary}],
        "breach_rate": round(len(ov) / len(primary), 3) if primary else 0.0,
    }

# ---- Family C: release readiness --------------------------------------------

HIGH_IMPACT = {"Critical", "High"}


def release_report(data, release_id):
    wis = {x["id"]: x for x in data["work_items"]}
    rel_wis = [x for x in data["work_items"] if x.get("release_id") == release_id]
    mc, tot_c, tot_p = [], 0, 0
    for m in sorted([m for m in data["milestones"]
                     if m.get("release_id") == release_id], key=lambda m: m["id"]):
        items = [x for x in data["work_items"]
                 if x.get("milestone_id") == m["id"] and is_primary(x)]
        c = sum(1 for x in items if is_complete(x))
        mc.append({"milestone_id": m["id"], "complete_primary": c,
                   "primary_total": len(items),
                   "completion_pct": round(c * 100 / len(items), 1) if items else 0.0})
        tot_c += c; tot_p += len(items)
    blk = [b for b in data["blockers"]
           if b.get("release_id") == release_id and b.get("resolved_at") is None
           and b.get("severity") in HIGH_IMPACT]
    causes = Counter(b["cause"] for b in blk)
    blocked_ids = {b["work_item_id"] for b in blk}
    gating = sorted(x["id"] for x in rel_wis
                    if is_primary(x) and not is_complete(x) and x["id"] in blocked_ids)
    adj = defaultdict(list)
    for dep in data["dependencies"]:
        adj[dep["blocked_id"]].append(dep["depends_on_id"])
    chains = []

    def dfs(node, path, seen):
        for nxt in adj.get(node, []):
            if nxt in seen:
                continue
            o = wis.get(nxt)
            if o is not None and not is_complete(o):
                chains.append(path + [nxt])          # reached a non-complete dep
            else:
                dfs(nxt, path + [nxt], seen | {nxt})  # keep tracing through complete
    for g in gating:
        dfs(g, [g], {g})
    chains = sorted(chains)
    readiness = round(tot_c / tot_p, 3) if tot_p else 0.0
    decision = "NO_SHIP" if (gating or blk or chains) else \
               ("SHIP" if readiness >= 1.0 else "SHIP_WITH_WATCH")
    return {
        "release_id": release_id,
        "ship_decision": decision,
        "milestone_completion": mc,
        "gating_work_item_ids": gating,
        "blocker_cause_counts": dict(causes),
        "critical_dependency_chains": chains,
        "readiness_score": readiness,
    }

# ---- CLI --------------------------------------------------------------------

def _csv(s):
    return [p.strip() for p in s.split(",") if p.strip()]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("family", choices=["mix", "sla", "release"])
    p.add_argument("--base"); p.add_argument("--token")
    p.add_argument("--access", default="environment_access.md")
    p.add_argument("--scope-id"); p.add_argument("--quarter")
    p.add_argument("--teams"); p.add_argument("--product-areas")
    p.add_argument("--categories"); p.add_argument("--as-of")
    p.add_argument("--window", type=int); p.add_argument("--release-id")
    a = p.parse_args(argv)

    base, token = load_access(a.access)
    base = a.base or base
    if not base:
        p.error("no base URL (pass --base or provide environment_access.md)")
    data = load_all(base)

    if a.family == "mix":
        out = mix_report(data["work_items"], data["mix_targets"],
                         _csv(a.teams), _csv(a.product_areas), a.quarter, a.scope_id)
    elif a.family == "sla":
        out = sla_report(data["work_items"], _csv(a.teams), _csv(a.categories),
                         a.as_of, a.window)
    else:
        out = release_report(data, a.release_id)
    json.dump(out, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
