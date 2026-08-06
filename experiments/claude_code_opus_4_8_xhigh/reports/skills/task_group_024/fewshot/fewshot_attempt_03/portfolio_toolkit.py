#!/usr/bin/env python3
"""
portfolio_toolkit.py -- reusable engine for the portfolio/SLA/release environment.

This module encodes ONLY the general conventions of the shared environment
(field semantics, portfolio-category classification, SLA aging math, release
readiness math). It contains no task-specific scope values and no answer values;
every task supplies its own scope as function arguments (read from that task's
prompt) and its own output shape (read from that task's answer_template.json).

Typical use at solve time:

    import portfolio_toolkit as pt
    data = pt.fetch_all()                     # reads ./environment_access.md
    res  = pt.portfolio_mix(data, scope_id="<from prompt>",
                            teams=[...], product_areas=[...], quarter="2025-Q4")
    # then format `res` into the exact keys/order the answer_template.json wants.

The three entry points -- portfolio_mix(), sla_aging(), release_readiness() --
each return a dict of computed primitives. The caller maps those primitives onto
the specific template. Nothing here prints or assumes a particular schema.
"""

import json
import re
import datetime as _dt
import urllib.request
from collections import Counter, defaultdict

# ---------------------------------------------------------------------------
# Environment access
# ---------------------------------------------------------------------------

def read_access(path="environment_access.md"):
    """Parse the Base URL and query token out of environment_access.md."""
    text = open(path).read()
    base = re.search(r"Base URL:\s*(\S+)", text)
    tok = re.search(r"X-Env-Token:\s*(\S+)", text)
    if not base:
        raise ValueError("Base URL not found in %s" % path)
    return base.group(1).rstrip("/"), (tok.group(1) if tok else None)


def _get(base, path, token=None):
    req = urllib.request.Request(base + path)
    if token:
        req.add_header("X-Env-Token", token)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_all(access_path="environment_access.md", base=None, token=None):
    """Fetch every GET collection the tasks need and return one data bundle."""
    if base is None:
        base, token = read_access(access_path)
    d = {"base": base, "token": token}
    d["work_items"] = _get(base, "/api/work-items", token).get("work_items", [])
    d["by_id"] = {w["id"]: w for w in d["work_items"]}
    d["mix_targets"] = _get(base, "/api/mix-targets", token).get("mix_targets", [])
    d["sla_policy"] = _get(base, "/api/sla-policy", token).get("sla_policy", [])
    d["releases"] = _get(base, "/api/releases", token).get("releases", [])
    d["milestones"] = _get(base, "/api/milestones", token).get("milestones", [])
    d["dependencies"] = _get(base, "/api/dependencies", token).get("dependencies", [])
    d["blockers"] = _get(base, "/api/blockers", token).get("blockers", [])
    return d


def query_sql(base, token, sql):
    """POST /api/query helper (restricted read-only SQL over work_items)."""
    body = json.dumps({"sql": sql}).encode()
    req = urllib.request.Request(base + "/api/query", data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("X-Env-Token", token)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

# ---------------------------------------------------------------------------
# Shared field conventions
# ---------------------------------------------------------------------------

# Authoritative "the work is finished" statuses. Everything else
# (Backlog, In Progress, Review, Reopened) is not-complete.
DONE_STATUSES = {"Closed", "Done", "Deployed", "Verified"}

# IMPORTANT: `mirror_status` and `legacy_category` are stale mirror/export
# fields. Never use them for truth -- use `status`, `work_type`, `labels`,
# `title`, `duplicate_of`, `closed_at`, `due_at`, `owner`, `severity`.


def is_duplicate(w):
    return w.get("status") == "Duplicate" or bool(w.get("duplicate_of"))


def is_cancelled(w):
    return w.get("status") == "Cancelled"


def is_complete(w):
    return w.get("status") in DONE_STATUSES


def _date(s):
    return _dt.date.fromisoformat(s) if s else None

# ---------------------------------------------------------------------------
# Portfolio category classification
# ---------------------------------------------------------------------------
# Four portfolio categories. When type/label/title signals point at more than
# one category, the HIGHEST-precedence category present wins (this is how the
# "conflicting signals" rule resolves). NewFeature is the lowest-precedence
# fallback used only when no other signal is present.
CATEGORY_PRECEDENCE = ["Security", "Reliability", "TechDebt", "NewFeature"]

# Keyword signals found in labels + title (case-insensitive substring match).
CATEGORY_KEYWORDS = {
    "Security":    ["security", "cve", "auth", "encryption", "compliance", "vuln"],
    "Reliability": ["reliability", "incident", "outage", "latency", "flaky"],
    "TechDebt":    ["cleanup", "refactor", "migration", "dependency", "chore",
                    "tech-debt", "techdebt"],
    "NewFeature":  ["feature", "enhancement", "rollout"],
}

# work_type -> its own category signal.
WORK_TYPE_CATEGORY = {
    "Security": "Security", "Compliance": "Security",
    "Incident": "Reliability", "Reliability": "Reliability", "Bug": "Reliability",
    "Refactor": "TechDebt", "Chore": "TechDebt", "Dependency": "TechDebt",
    "Feature": "NewFeature", "Enhancement": "NewFeature",
}

DISPLAY_ORDER = ["NewFeature", "TechDebt", "Reliability", "Security"]


def classify(w):
    """Return the portfolio category for a work item using the precedence rule."""
    blob = (" ".join(w.get("labels", []) or []) + " " + (w.get("title") or "")).lower()
    present = set()
    wt = WORK_TYPE_CATEGORY.get(w.get("work_type"))
    if wt:
        present.add(wt)
    for cat, kws in CATEGORY_KEYWORDS.items():
        if any(k in blob for k in kws):
            present.add(cat)
    for cat in CATEGORY_PRECEDENCE:
        if cat in present:
            return cat
    return "NewFeature"

# ---------------------------------------------------------------------------
# Quarter / target helpers
# ---------------------------------------------------------------------------

def quarter_range(quarter):
    """'2025-Q4' -> ('2025-10-01', '2025-12-31') inclusive ISO strings."""
    year, q = quarter.split("-Q")
    q = int(q)
    start_month = (q - 1) * 3 + 1
    start = _dt.date(int(year), start_month, 1)
    if q == 4:
        end = _dt.date(int(year), 12, 31)
    else:
        end = _dt.date(int(year), start_month + 3, 1) - _dt.timedelta(days=1)
    return start.isoformat(), end.isoformat()


def target_mix(data, scope_id):
    """Return {category: percentage_points} from the mix_targets row for scope_id."""
    row = next((r for r in data["mix_targets"] if r["scope_id"] == scope_id), None)
    if row is None:
        raise ValueError("no mix_targets row for scope_id=%r" % scope_id)
    # stored as fractions 0..1 -> percentage points
    return {
        "NewFeature": round(row["new_feature_pct"] * 100, 1),
        "TechDebt":   round(row["tech_debt_pct"] * 100, 1),
        "Reliability": round(row["reliability_pct"] * 100, 1),
        "Security":   round(row["security_pct"] * 100, 1),
    }

# ---------------------------------------------------------------------------
# TASK FAMILY A: portfolio mix review
# ---------------------------------------------------------------------------

def portfolio_mix(data, scope_id, teams, product_areas, quarter):
    """
    Count-based portfolio mix for closed work in scope, vs the target mix.

    In scope = team in `teams`, product_area in `product_areas`, closed_at inside
    the quarter. Then: duplicates and cancelled records are excluded (reported
    separately); remaining records with a DONE status are the included mix.
    """
    tset, aset = set(teams), set(product_areas)
    qstart, qend = quarter_range(quarter)

    inscope = [w for w in data["work_items"]
               if w["team"] in tset and w["product_area"] in aset
               and w.get("closed_at") and qstart <= w["closed_at"] <= qend]

    by_closed = lambda w: (w["closed_at"], w["id"])
    dup = sorted([w["id"] for w in inscope if is_duplicate(w)],
                 key=lambda i: (data["by_id"][i]["closed_at"], i))
    canc = sorted([w["id"] for w in inscope if is_cancelled(w) and not is_duplicate(w)],
                  key=lambda i: (data["by_id"][i]["closed_at"], i))
    distractors = sorted(set(dup) | set(canc),
                         key=lambda i: (data["by_id"][i]["closed_at"], i))

    included = sorted([w for w in inscope
                       if not is_duplicate(w) and not is_cancelled(w) and is_complete(w)],
                      key=by_closed)
    n = len(included)

    counts = Counter(classify(w) for w in included)
    counts = {c: counts.get(c, 0) for c in DISPLAY_ORDER}
    actual = {c: (round(counts[c] / n * 100, 1) if n else 0.0) for c in DISPLAY_ORDER}
    target = target_mix(data, scope_id)

    table = []
    for c in DISPLAY_ORDER:
        gap = round(actual[c] - target[c], 1)
        table.append({"category": c, "count": counts[c],
                      "actual_pct": actual[c], "target_pct": target[c], "gap_pct": gap})

    negatives = sorted([(r["category"], r["gap_pct"]) for r in table if r["gap_pct"] < 0],
                       key=lambda x: x[1])            # most negative first
    under_invested = [c for c, _ in negatives]

    # follow-up action (variant whose template names primary/secondary categories)
    if negatives:
        follow = {"action": "REBALANCE_CAPACITY",
                  "primary_category": negatives[0][0],
                  "secondary_category": negatives[1][0] if len(negatives) > 1 else None,
                  "rationale_code": "LARGEST_NEGATIVE_GAP"}
    else:
        follow = {"action": "MAINTAIN_CURRENT_MIX", "primary_category": None,
                  "secondary_category": None, "rationale_code": "NO_NEGATIVE_GAPS"}

    # owner_team for the largest deficit (variant whose template names owner_team): the team that
    # owns the most included work in that category; ties broken alphabetically.
    owner_team = None
    if negatives:
        deficit = negatives[0][0]
        team_counts = Counter(w["team"] for w in included if classify(w) == deficit)
        if team_counts:
            owner_team = sorted(team_counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        else:  # no items in the deficit category -> team with largest overall volume
            overall = Counter(w["team"] for w in included)
            owner_team = sorted(overall.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if overall else None

    return {
        "included_ids": [w["id"] for w in included],
        "total_included": n,
        "category_counts": counts,
        "category_percentages": actual,
        "target_pct": target,
        "table": table,                      # per category: count/actual/target/gap
        "under_invested": under_invested,
        "largest_deficit_category": negatives[0][0] if negatives else None,
        "follow_up_action": follow,
        "recommended_owner_team": owner_team,
        "excluded_duplicate_ids": dup,
        "excluded_cancelled_ids": canc,
        "excluded_distractor_ids": distractors,
    }

# ---------------------------------------------------------------------------
# TASK FAMILY B: SLA aging review
# ---------------------------------------------------------------------------

SEVERITY_BUCKETS = ["S1", "S2", "S3", "S4"]


def _age_days(w, as_of):
    end = _date(w.get("closed_at")) or as_of
    return (end - _date(w["created_at"])).days


def _days_overdue(w, as_of):
    end = _date(w.get("closed_at")) or as_of
    return (end - _date(w["due_at"])).days


def _is_overdue(w, as_of):
    cl = _date(w.get("closed_at"))
    due = _date(w.get("due_at"))
    return (cl > due) if cl else (due < as_of)   # open item overdue once due date has passed


def sla_aging(data, teams, categories, as_of, window_days):
    """
    SLA aging over the primary population.

    Population = team in `teams`, classify() in `categories`, not cancelled,
    created on/before as_of, and either still open OR closed within the recent
    window [as_of - window_days, as_of]. Duplicates (status Duplicate or
    duplicate_of set) are pulled out into clusters; the rest are primary.
    """
    as_of = _date(as_of) if isinstance(as_of, str) else as_of
    wstart = as_of - _dt.timedelta(days=window_days)
    tset, cset = set(teams), set(categories)

    primary, dups = [], []
    for w in data["work_items"]:
        if w["team"] not in tset:
            continue
        if classify(w) not in cset:
            continue
        if is_cancelled(w):
            continue
        cr = _date(w.get("created_at"))
        if cr and cr > as_of:
            continue
        cl = _date(w.get("closed_at"))
        in_pop = (cl is None) or (wstart <= cl <= as_of)
        if not in_pop:
            continue
        (dups if is_duplicate(w) else primary).append(w)

    overdue = [w for w in primary if _is_overdue(w, as_of)]

    buckets = {"0-3": 0, "4-7": 0, "8-14": 0, "15-30": 0, "31+": 0}
    for w in primary:
        a = _age_days(w, as_of)
        key = ("0-3" if a <= 3 else "4-7" if a <= 7 else "8-14" if a <= 14
               else "15-30" if a <= 30 else "31+")
        buckets[key] += 1

    team_overdue = Counter(w["team"] for w in overdue)
    sev_overdue = Counter(w["severity"] for w in overdue)

    # hotspot: (team, owner) pair with most overdue; ties -> team then owner asc.
    pair = Counter((w["team"], w.get("owner") or "UNASSIGNED") for w in overdue)
    hotspot = None
    if pair:
        (team, owner), cnt = sorted(pair.items(), key=lambda kv: (-kv[1], kv[0][0], kv[0][1]))[0]
        hotspot = {"team": team, "owner": owner, "overdue_count": cnt}

    # escalation order: severity asc (S1<S2<S3<S4), then days-overdue desc, then id asc.
    escalation = [w["id"] for w in sorted(
        overdue, key=lambda w: (int(w["severity"][1:]), -_days_overdue(w, as_of), w["id"]))]

    cmap = defaultdict(list)
    for w in dups:
        if w.get("duplicate_of"):
            cmap[w["duplicate_of"]].append(w["id"])
    clusters = [{"primary_id": k, "duplicate_ids": sorted(v)} for k, v in sorted(cmap.items())]

    n = len(primary)
    return {
        "included_primary_ids": sorted(w["id"] for w in primary),
        "overdue_primary_ids": sorted(w["id"] for w in overdue),
        "aging_bucket_counts": buckets,
        "team_overdue_counts": [{"team": t, "overdue_count": team_overdue.get(t, 0)}
                                 for t in sorted(tset)],
        "overdue_counts_by_severity": {s: sev_overdue.get(s, 0) for s in SEVERITY_BUCKETS},
        "top_hotspot": hotspot,
        "escalation_queue_ids": escalation,
        "missing_owner_ids": sorted(w["id"] for w in primary if not w.get("owner")),
        "duplicate_clusters": clusters,
        "breach_rate": round(len(overdue) / n, 3) if n else 0.0,
    }

# ---------------------------------------------------------------------------
# TASK FAMILY C: release readiness
# ---------------------------------------------------------------------------

HIGH_IMPACT = {"High", "Critical"}


def _blocker_unresolved(b):
    return b.get("resolved_at") is None and b.get("status") != "Resolved"


def release_readiness(data, release_id):
    """Release-readiness assessment built from authoritative status/blocker/dep data."""
    rel_items = [w for w in data["work_items"] if w.get("release_id") == release_id]
    ms = [m for m in data["milestones"] if m.get("release_id") == release_id]

    by_ms = defaultdict(list)
    for w in rel_items:
        if w.get("milestone_id") and not is_duplicate(w) and not is_cancelled(w):
            by_ms[w["milestone_id"]].append(w)

    milestone_completion, tot_c, tot_t = [], 0, 0
    for mid in sorted(by_ms):
        prim = by_ms[mid]
        c = sum(1 for w in prim if is_complete(w))
        t = len(prim)
        tot_c += c
        tot_t += t
        milestone_completion.append({
            "milestone_id": mid, "complete_primary": c, "primary_total": t,
            "completion_pct": round(c / t * 100, 1) if t else 0.0})
    readiness = round(tot_c / tot_t, 3) if tot_t else 0.0

    hib = [b for b in data["blockers"]
           if b.get("release_id") == release_id and b.get("severity") in HIGH_IMPACT
           and _blocker_unresolved(b)]
    blocker_cause_counts = dict(sorted(Counter(b["cause"] for b in hib).items()))
    blocked_ids = {b["work_item_id"] for b in hib}

    gating = sorted({w["id"] for w in rel_items
                     if not is_duplicate(w) and not is_cancelled(w)
                     and not is_complete(w) and w["id"] in blocked_ids})

    dep_out = defaultdict(list)
    for d in data["dependencies"]:
        dep_out[d["blocked_id"]].append(d["depends_on_id"])

    chains = []
    for g in gating:
        # depth-first: extend a chain while the tail depends on a non-complete item
        stack = [[g]]
        while stack:
            path = stack.pop()
            extended = False
            for nxt in dep_out.get(path[-1], []):
                w = data["by_id"].get(nxt)
                if w and not is_complete(w) and nxt not in path:
                    extended = True
                    newpath = path + [nxt]
                    # a completed-chain endpoint is a non-complete dependency
                    chains.append(newpath)
                    stack.append(newpath)
            _ = extended
    chains = sorted({tuple(c) for c in chains})
    chains = [list(c) for c in chains]

    has_critical_blocker = any(b.get("severity") == "Critical" for b in hib)
    if gating or chains or has_critical_blocker:
        ship = "NO_SHIP"
    elif readiness >= 1.0 and not hib:
        ship = "SHIP"
    else:
        ship = "SHIP_WITH_WATCH"

    return {
        "release_id": release_id,
        "ship_decision": ship,
        "milestone_completion": milestone_completion,
        "gating_work_item_ids": gating,
        "blocker_cause_counts": blocker_cause_counts,
        "critical_dependency_chains": chains,
        "readiness_score": readiness,
    }
