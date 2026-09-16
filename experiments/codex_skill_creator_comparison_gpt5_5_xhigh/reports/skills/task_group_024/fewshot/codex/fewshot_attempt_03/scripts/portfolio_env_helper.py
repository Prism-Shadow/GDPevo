#!/usr/bin/env python3
"""Reusable helpers for engineering portfolio task-environment JSON tasks."""

import argparse
import json
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import date, timedelta


CATEGORY_ORDER = ["NewFeature", "TechDebt", "Reliability", "Security"]
COMPLETE_STATUSES = {"Closed", "Done", "Deployed", "Verified"}
NON_PRIMARY_STATUSES = {"Duplicate", "Cancelled"}
HIGH_IMPACT_BLOCKERS = {"High", "Critical"}
SEVERITY_RANK = {"S1": 0, "S2": 1, "S3": 2, "S4": 3}

SECURITY_TERMS = {
    "security",
    "cve",
    "encryption",
    "auth",
    "consent",
    "vulnerability",
    "audit evidence",
}
STRONG_SECURITY_TERMS = SECURITY_TERMS - {"auth", "consent"}
RELIABILITY_TERMS = {
    "reliability",
    "incident",
    "outage",
    "latency",
    "flaky",
    "rehearsal",
    "crash",
}
TECH_DEBT_TERMS = {
    "tech debt",
    "tech-debt",
    "refactor",
    "cleanup",
    "migration",
    "dependency",
    "deprecate",
    "stabilize",
}
NEW_FEATURE_TERMS = {"feature", "enhancement", "rollout", "experiment", "polish", "dashboard"}


def fetch_json(base_url, path):
    url = base_url.rstrip("/") + path
    try:
        with urllib.request.urlopen(url) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"HTTP {exc.code} fetching {url}: {exc.read().decode()}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Error fetching {url}: {exc}") from exc


def parse_date(value):
    if not value:
        return None
    return date.fromisoformat(value)


def parse_csv(value):
    return [item.strip() for item in value.split(",") if item.strip()]


def quarter_bounds(quarter):
    year_text, q_text = quarter.split("-Q", 1)
    year = int(year_text)
    q = int(q_text)
    start_month = (q - 1) * 3 + 1
    start = date(year, start_month, 1)
    if q == 4:
        end = date(year, 12, 31)
    else:
        end = date(year, start_month + 3, 1) - timedelta(days=1)
    return start, end


def item_blob(item):
    labels = item.get("labels") or []
    parts = [item.get("work_type") or "", item.get("title") or "", " ".join(labels)]
    return " ".join(parts).lower()


def label_blob(item):
    return " ".join(item.get("labels") or []).lower()


def title_blob(item):
    return (item.get("title") or "").lower()


def contains_any(blob, terms):
    return any(term in blob for term in terms)


def category_for(item):
    work_type = (item.get("work_type") or "").strip()
    blob = item_blob(item)
    labels = label_blob(item)
    title = title_blob(item)
    product_area = (item.get("product_area") or "").lower()
    has_tech_debt_shape = work_type in {"Refactor", "Chore", "Dependency"} or contains_any(
        blob, TECH_DEBT_TERMS
    )
    if (
        work_type in {"Security", "Compliance"}
        or contains_any(labels, STRONG_SECURITY_TERMS)
        or contains_any(title, STRONG_SECURITY_TERMS)
        or ("consent" in labels)
        or ("consent" in title and product_area == "identity")
        or ("auth" in labels and not has_tech_debt_shape)
    ):
        return "Security"
    if work_type in {"Reliability", "Incident", "Bug"} or contains_any(blob, RELIABILITY_TERMS):
        return "Reliability"
    if work_type in {"Refactor", "Chore", "Dependency"} or contains_any(blob, TECH_DEBT_TERMS):
        return "TechDebt"
    if work_type in {"Feature", "Enhancement"} or contains_any(blob, NEW_FEATURE_TERMS):
        return "NewFeature"
    return "NewFeature"


def is_duplicate(item):
    return bool(item.get("duplicate_of")) or item.get("status") == "Duplicate"


def is_primary(item):
    return not item.get("duplicate_of") and item.get("status") not in NON_PRIMARY_STATUSES


def is_complete(item):
    return item.get("status") in COMPLETE_STATUSES


def sort_closed(items):
    return sorted(items, key=lambda item: (item.get("closed_at") or "", item.get("id") or ""))


def round1(value):
    return round(value + 0.0, 1)


def round3(value):
    return round(value + 0.0, 3)


def load_work_items(base_url):
    return fetch_json(base_url, "/api/work-items").get("work_items", [])


def load_policy(base_url):
    rows = fetch_json(base_url, "/api/sla-policy").get("sla_policy", [])
    return {row["severity"]: int(row["days_to_due"]) for row in rows}


def due_date_for(item, policy):
    due = parse_date(item.get("due_at"))
    if due:
        return due
    created = parse_date(item.get("created_at"))
    days = policy.get(item.get("severity"))
    if created and days is not None:
        return created + timedelta(days=days)
    return None


def effective_date_for(item, as_of):
    closed = parse_date(item.get("closed_at"))
    if closed and closed <= as_of:
        return closed
    return as_of


def in_recent_window_or_open(item, as_of, window_days):
    closed = parse_date(item.get("closed_at"))
    if not closed or closed > as_of:
        return True
    return as_of - timedelta(days=window_days) <= closed <= as_of


def portfolio_mix(args):
    teams = parse_csv(args.teams)
    product_areas = parse_csv(args.product_areas)
    q_start, q_end = quarter_bounds(args.quarter)
    work_items = load_work_items(args.base_url)
    targets = fetch_json(args.base_url, "/api/mix-targets").get("mix_targets", [])

    def in_scope(item):
        closed = parse_date(item.get("closed_at"))
        return (
            item.get("team") in teams
            and item.get("product_area") in product_areas
            and closed is not None
            and q_start <= closed <= q_end
        )

    scoped = [item for item in work_items if in_scope(item)]
    included = [item for item in scoped if is_primary(item) and is_complete(item)]
    duplicates = [item for item in scoped if is_duplicate(item)]
    cancelled = [item for item in scoped if item.get("status") == "Cancelled"]

    counts = {category: 0 for category in CATEGORY_ORDER}
    classified = {}
    for item in included:
        category = category_for(item)
        classified[item["id"]] = category
        counts[category] += 1

    total = len(included)
    actual_pct = {
        category: round1((counts[category] / total * 100) if total else 0.0)
        for category in CATEGORY_ORDER
    }

    target = None
    if args.scope_id:
        target = next((row for row in targets if row.get("scope_id") == args.scope_id), None)
    if target is None:
        matches = [
            row
            for row in targets
            if row.get("quarter") == args.quarter
            and all(area in (row.get("product_area") or "") for area in product_areas)
        ]
        target = matches[0] if len(matches) == 1 else None

    target_pct = {}
    if target:
        target_pct = {
            "NewFeature": round1(float(target.get("new_feature_pct", 0)) * 100),
            "TechDebt": round1(float(target.get("tech_debt_pct", 0)) * 100),
            "Reliability": round1(float(target.get("reliability_pct", 0)) * 100),
            "Security": round1(float(target.get("security_pct", 0)) * 100),
        }
    else:
        target_pct = {category: 0.0 for category in CATEGORY_ORDER}

    mix_rows = []
    for category in CATEGORY_ORDER:
        mix_rows.append(
            {
                "category": category,
                "count": counts[category],
                "actual_pct": actual_pct[category],
                "target_pct": target_pct[category],
                "gap_pct": round1(actual_pct[category] - target_pct[category]),
            }
        )

    deficits = sorted(
        [row for row in mix_rows if row["gap_pct"] < 0],
        key=lambda row: (row["gap_pct"], CATEGORY_ORDER.index(row["category"])),
    )
    primary_deficit = deficits[0]["category"] if deficits else None
    secondary_deficit = deficits[1]["category"] if len(deficits) > 1 else None

    owner_team = None
    if primary_deficit:
        team_counts = Counter(item["team"] for item in included if classified.get(item["id"]) == primary_deficit)
        if team_counts:
            team_order = {team: index for index, team in enumerate(teams)}
            owner_team = sorted(team_counts.items(), key=lambda pair: (-pair[1], team_order.get(pair[0], 999), pair[0]))[0][0]

    result = {
        "scope": {
            "scope_id": args.scope_id,
            "quarter": args.quarter,
            "teams": teams,
            "product_areas": product_areas,
            "target_scope_id": target.get("scope_id") if target else args.scope_id,
            "total_included": total,
        },
        "included_work_item_ids": [item["id"] for item in sort_closed(included)],
        "category_counts": counts,
        "category_percentages": actual_pct,
        "mix_table": mix_rows,
        "under_invested_categories": [row["category"] for row in deficits],
        "follow_up_action": {
            "action": "REBALANCE_CAPACITY" if deficits else "MAINTAIN_CURRENT_MIX",
            "primary_category": primary_deficit,
            "secondary_category": secondary_deficit,
            "rationale_code": "LARGEST_NEGATIVE_GAP" if deficits else "NO_NEGATIVE_GAPS",
            "owner_team": owner_team,
        },
        "exclusion_flags": {
            "excluded_duplicate_ids": [item["id"] for item in sort_closed(duplicates)],
            "excluded_cancelled_ids": [item["id"] for item in sort_closed(cancelled)],
            "ignored_mirror_status_and_legacy_category": True,
        },
        "excluded_distractor_ids": [item["id"] for item in sort_closed({item["id"]: item for item in duplicates + cancelled}.values())],
    }
    print(json.dumps(result, indent=2, sort_keys=False))


def sla_aging(args):
    teams = parse_csv(args.teams)
    categories = parse_csv(args.categories)
    as_of = parse_date(args.as_of)
    policy = load_policy(args.base_url)
    work_items = load_work_items(args.base_url)

    def relevant(item):
        created = parse_date(item.get("created_at"))
        return (
            item.get("team") in teams
            and category_for(item) in categories
            and created is not None
            and created <= as_of
            and in_recent_window_or_open(item, as_of, args.window_days)
        )

    scoped = [item for item in work_items if relevant(item)]
    included = [item for item in scoped if is_primary(item)]
    duplicate_records = [item for item in scoped if is_duplicate(item) and item.get("duplicate_of")]

    overdue = []
    for item in included:
        due = due_date_for(item, policy)
        effective = effective_date_for(item, as_of)
        if due and due < effective:
            overdue.append(item)

    aging_buckets = {"0-3": 0, "4-7": 0, "8-14": 0, "15-30": 0, "31+": 0}
    for item in included:
        created = parse_date(item.get("created_at"))
        if not created:
            continue
        age = max(0, (effective_date_for(item, as_of) - created).days)
        if age <= 3:
            aging_buckets["0-3"] += 1
        elif age <= 7:
            aging_buckets["4-7"] += 1
        elif age <= 14:
            aging_buckets["8-14"] += 1
        elif age <= 30:
            aging_buckets["15-30"] += 1
        else:
            aging_buckets["31+"] += 1

    team_counts = Counter(item["team"] for item in overdue)
    hotspot_counts = Counter((item.get("team"), item.get("owner") or "UNASSIGNED") for item in overdue)
    hotspot = None
    if hotspot_counts:
        (team, owner), count = sorted(hotspot_counts.items(), key=lambda pair: (-pair[1], pair[0][0], pair[0][1]))[0]
        hotspot = {"team": team, "owner": owner, "overdue_count": count}

    clusters = defaultdict(list)
    for item in duplicate_records:
        clusters[item["duplicate_of"]].append(item["id"])

    severity_counts = {severity: 0 for severity in ["S1", "S2", "S3", "S4"]}
    for item in overdue:
        severity = item.get("severity")
        if severity in severity_counts:
            severity_counts[severity] += 1

    def escalation_key(item):
        due = due_date_for(item, policy) or date.max
        priority = item.get("priority")
        return (
            SEVERITY_RANK.get(item.get("severity"), 99),
            due.isoformat(),
            priority if isinstance(priority, int) else 999,
            item.get("id") or "",
        )

    result = {
        "scope": {
            "teams": sorted(teams),
            "as_of": args.as_of,
            "recent_closed_window_days": args.window_days,
            "categories": categories,
        },
        "included_primary_ids": sorted(item["id"] for item in included),
        "overdue_primary_ids": sorted(item["id"] for item in overdue),
        "aging_bucket_counts": aging_buckets,
        "team_overdue_counts": [
            {"team": team, "overdue_count": team_counts.get(team, 0)}
            for team in sorted(teams)
        ],
        "top_hotspot": hotspot,
        "overdue_counts_by_severity": severity_counts,
        "escalation_queue_ids": [item["id"] for item in sorted(overdue, key=escalation_key)],
        "duplicate_clusters": [
            {"primary_id": primary_id, "duplicate_ids": sorted(ids)}
            for primary_id, ids in sorted(clusters.items())
        ],
        "missing_owner_ids": sorted(item["id"] for item in included if not item.get("owner")),
        "breach_rate": round3(len(overdue) / len(included)) if included else 0.0,
        "sla_breach_rate": round3(len(overdue) / len(included)) if included else 0.0,
    }
    print(json.dumps(result, indent=2, sort_keys=False))


def unresolved_high_impact(blocker):
    return (
        blocker.get("severity") in HIGH_IMPACT_BLOCKERS
        and not blocker.get("resolved_at")
        and blocker.get("status") != "Resolved"
    )


def release_readiness(args):
    detail = fetch_json(args.base_url, f"/api/releases/{args.release_id}")
    milestones = detail.get("milestones") or [
        row for row in fetch_json(args.base_url, "/api/milestones").get("milestones", [])
        if row.get("release_id") == args.release_id
    ]
    blockers = detail.get("blockers") or [
        row for row in fetch_json(args.base_url, "/api/blockers").get("blockers", [])
        if row.get("release_id") == args.release_id
    ]
    dependencies = fetch_json(args.base_url, "/api/dependencies").get("dependencies", [])
    work_items = load_work_items(args.base_url)
    by_id = {item["id"]: item for item in work_items}

    release_items = [
        item for item in work_items
        if item.get("release_id") == args.release_id and is_primary(item)
    ]
    milestone_ids = {row["id"] for row in milestones}
    milestone_items = [item for item in release_items if item.get("milestone_id") in milestone_ids]

    milestone_completion = []
    total_complete = 0
    total_primary = 0
    for milestone in sorted(milestones, key=lambda row: row["id"]):
        items = [item for item in milestone_items if item.get("milestone_id") == milestone["id"]]
        complete = sum(1 for item in items if is_complete(item))
        total = len(items)
        total_complete += complete
        total_primary += total
        milestone_completion.append(
            {
                "milestone_id": milestone["id"],
                "complete_primary": complete,
                "primary_total": total,
                "completion_pct": round1(complete / total * 100) if total else 0.0,
            }
        )

    high_blockers = [blocker for blocker in blockers if unresolved_high_impact(blocker)]
    blocker_cause_counts = dict(sorted(Counter(blocker["cause"] for blocker in high_blockers).items()))
    high_blocker_work_ids = {blocker.get("work_item_id") for blocker in high_blockers}

    deps_by_blocked = defaultdict(list)
    for dep in dependencies:
        deps_by_blocked[dep.get("blocked_id")].append(dep.get("depends_on_id"))

    chains = set()

    def walk(path):
        current = path[-1]
        for depends_on in sorted(deps_by_blocked.get(current, [])):
            if not depends_on or depends_on in path:
                continue
            dep_item = by_id.get(depends_on)
            next_path = path + [depends_on]
            if dep_item is None or not is_complete(dep_item):
                chains.add(tuple(next_path))
            else:
                walk(next_path)

    dependency_starts = [
        item for item in release_items
        if item["id"] in high_blocker_work_ids and not is_complete(item)
    ]
    for item in sorted(dependency_starts, key=lambda row: row["id"]):
        if item["id"] in deps_by_blocked:
            walk([item["id"]])

    noncomplete_release_ids = {item["id"] for item in release_items if not is_complete(item)}
    gating_ids = sorted(
        item_id for item_id in noncomplete_release_ids
        if item_id in high_blocker_work_ids or any(chain[0] == item_id for chain in chains)
    )

    readiness_score = round3(total_complete / total_primary) if total_primary else 0.0
    if gating_ids or chains:
        decision = "NO_SHIP"
    elif blocker_cause_counts or readiness_score < 1.0:
        decision = "SHIP_WITH_WATCH"
    else:
        decision = "SHIP"

    result = {
        "release_id": args.release_id,
        "ship_decision": decision,
        "milestone_completion": milestone_completion,
        "gating_work_item_ids": gating_ids,
        "blocker_cause_counts": blocker_cause_counts,
        "critical_dependency_chains": [list(chain) for chain in sorted(chains)],
        "readiness_score": readiness_score,
    }
    print(json.dumps(result, indent=2, sort_keys=False))


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    portfolio = subparsers.add_parser("portfolio-mix")
    portfolio.add_argument("--base-url", required=True)
    portfolio.add_argument("--scope-id", default=None)
    portfolio.add_argument("--quarter", required=True)
    portfolio.add_argument("--teams", required=True)
    portfolio.add_argument("--product-areas", required=True)
    portfolio.set_defaults(func=portfolio_mix)

    sla = subparsers.add_parser("sla-aging")
    sla.add_argument("--base-url", required=True)
    sla.add_argument("--teams", required=True)
    sla.add_argument("--as-of", required=True)
    sla.add_argument("--window-days", type=int, required=True)
    sla.add_argument("--categories", required=True)
    sla.set_defaults(func=sla_aging)

    release = subparsers.add_parser("release-readiness")
    release.add_argument("--base-url", required=True)
    release.add_argument("--release-id", required=True)
    release.set_defaults(func=release_readiness)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
