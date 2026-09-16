#!/usr/bin/env python3
"""Compute reusable portfolio, SLA, and release summaries from the task API."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from typing import Any, Iterable


CATEGORY_ORDER = ["NewFeature", "TechDebt", "Reliability", "Security"]
COMPLETE_STATUSES = {"Closed", "Done", "Deployed", "Verified"}
EXCLUDED_STATUSES = {"Duplicate", "Cancelled"}
SEVERITY_ORDER = {"S1": 0, "S2": 1, "S3": 2, "S4": 3}
HIGH_IMPACT_BLOCKERS = {"High", "Critical"}
CRITICAL_DEPENDENCY_RELATIONS = {
    "blocks-release-readiness",
    "validation-required",
    "security-review-required",
    "audit-evidence-required",
    "implementation-dependency",
}

SECURITY_TERMS = {
    "security",
    "cve",
    "auth",
    "encryption",
    "compliance",
}
SECURITY_TYPES = {"Security", "Compliance"}

RELIABILITY_TERMS = {
    "reliability",
    "incident",
    "outage",
    "latency",
    "flaky",
}
RELIABILITY_TYPES = {"Reliability", "Incident", "Bug"}

TECH_DEBT_TERMS = {
    "tech debt",
    "tech-debt",
    "refactor",
    "cleanup",
    "migration",
    "dependency",
    "chore",
}
TECH_DEBT_TYPES = {"Refactor", "Chore", "Dependency"}

FEATURE_TERMS = {
    "feature",
    "rollout",
    "customer request",
    "customer-request",
    "new",
}
FEATURE_TYPES = {"Feature", "Enhancement"}


def parse_date(value: str | None) -> dt.date | None:
    if not value:
        return None
    return dt.date.fromisoformat(value)


def rounded(value: float, places: int) -> float:
    return round(value + 0.0, places)


def fetch_json(base_url: str, path: str) -> Any:
    url = base_url.rstrip("/") + path
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise SystemExit(f"failed to fetch {url}: {exc}") from exc


def unwrap(data: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(data, dict) and key in data:
        return list(data[key])
    if isinstance(data, list):
        return list(data)
    raise SystemExit(f"unexpected API response for {key}")


def load_data(base_url: str) -> dict[str, list[dict[str, Any]]]:
    return {
        "work_items": unwrap(fetch_json(base_url, "/api/work-items"), "work_items"),
        "mix_targets": unwrap(fetch_json(base_url, "/api/mix-targets"), "mix_targets"),
        "sla_policy": unwrap(fetch_json(base_url, "/api/sla-policy"), "sla_policy"),
        "releases": unwrap(fetch_json(base_url, "/api/releases"), "releases"),
        "milestones": unwrap(fetch_json(base_url, "/api/milestones"), "milestones"),
        "dependencies": unwrap(fetch_json(base_url, "/api/dependencies"), "dependencies"),
        "blockers": unwrap(fetch_json(base_url, "/api/blockers"), "blockers"),
    }


def item_text(item: dict[str, Any]) -> str:
    labels = item.get("labels") or []
    if isinstance(labels, str):
        try:
            labels = json.loads(labels)
        except json.JSONDecodeError:
            labels = [labels]
    parts = [item.get("work_type") or "", item.get("title") or "", *labels]
    return " ".join(str(part) for part in parts if part is not None).lower()


def normalized_text(item: dict[str, Any]) -> tuple[str, set[str]]:
    text = item_text(item)
    normalized = re.sub(r"[^a-z0-9]+", " ", text)
    return normalized, set(normalized.split())


def has_term(item: dict[str, Any], terms: Iterable[str]) -> bool:
    normalized, tokens = normalized_text(item)
    for term in terms:
        clean = re.sub(r"[^a-z0-9]+", " ", term.lower()).strip()
        if not clean:
            continue
        if " " in clean:
            if clean in normalized:
                return True
        elif clean in tokens:
            return True
    return False


def classify(item: dict[str, Any]) -> str:
    work_type = item.get("work_type")
    if work_type in SECURITY_TYPES or has_term(item, SECURITY_TERMS):
        return "Security"
    if work_type in RELIABILITY_TYPES or has_term(item, RELIABILITY_TERMS):
        return "Reliability"
    if work_type in TECH_DEBT_TYPES or has_term(item, TECH_DEBT_TERMS):
        return "TechDebt"
    if work_type in FEATURE_TYPES or has_term(item, FEATURE_TERMS):
        return "NewFeature"
    return "TechDebt"


def is_duplicate_or_cancelled(item: dict[str, Any]) -> bool:
    return item.get("status") in EXCLUDED_STATUSES or bool(item.get("duplicate_of"))


def is_complete(item: dict[str, Any]) -> bool:
    return item.get("status") in COMPLETE_STATUSES


def quarter_bounds(quarter: str) -> tuple[dt.date, dt.date]:
    match = re.fullmatch(r"(\d{4})-Q([1-4])", quarter)
    if not match:
        raise SystemExit(f"invalid quarter: {quarter}")
    year = int(match.group(1))
    quarter_num = int(match.group(2))
    start_month = 1 + (quarter_num - 1) * 3
    start = dt.date(year, start_month, 1)
    if quarter_num == 4:
        end = dt.date(year + 1, 1, 1)
    else:
        end = dt.date(year, start_month + 3, 1)
    return start, end


def split_scope_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split("+") if part.strip()]


def find_mix_target(data: dict[str, list[dict[str, Any]]], scope_id: str | None) -> dict[str, Any] | None:
    if not scope_id:
        return None
    matches = [target for target in data["mix_targets"] if target.get("scope_id") == scope_id]
    return matches[0] if matches else None


def target_percentages(target: dict[str, Any] | None) -> dict[str, float]:
    if not target:
        return {category: 0.0 for category in CATEGORY_ORDER}
    return {
        "NewFeature": rounded(float(target.get("new_feature_pct", 0.0)) * 100, 1),
        "TechDebt": rounded(float(target.get("tech_debt_pct", 0.0)) * 100, 1),
        "Reliability": rounded(float(target.get("reliability_pct", 0.0)) * 100, 1),
        "Security": rounded(float(target.get("security_pct", 0.0)) * 100, 1),
    }


def portfolio_mix(args: argparse.Namespace) -> dict[str, Any]:
    data = load_data(args.base_url)
    target = find_mix_target(data, args.scope_id)
    teams = args.team or split_scope_list((target or {}).get("team_group"))
    product_areas = args.product_area or split_scope_list((target or {}).get("product_area"))
    start, end = quarter_bounds(args.quarter)

    scoped: list[dict[str, Any]] = []
    for item in data["work_items"]:
        closed = parse_date(item.get("closed_at"))
        if not closed or not (start <= closed < end):
            continue
        if teams and item.get("team") not in teams:
            continue
        if product_areas and item.get("product_area") not in product_areas:
            continue
        scoped.append(item)

    included = [
        item
        for item in scoped
        if not is_duplicate_or_cancelled(item) and is_complete(item)
    ]
    included.sort(key=lambda item: (item.get("closed_at") or "", item.get("id") or ""))

    counts = {category: 0 for category in CATEGORY_ORDER}
    item_categories: dict[str, str] = {}
    for item in included:
        category = classify(item)
        item_categories[item["id"]] = category
        counts[category] += 1

    total = len(included)
    actual = {
        category: rounded((counts[category] / total * 100) if total else 0.0, 1)
        for category in CATEGORY_ORDER
    }
    target_pct = target_percentages(target)
    mix_table = [
        {
            "category": category,
            "count": counts[category],
            "actual_pct": actual[category],
            "target_pct": target_pct[category],
            "gap_pct": rounded(actual[category] - target_pct[category], 1),
        }
        for category in CATEGORY_ORDER
    ]
    deficits = [row for row in mix_table if row["gap_pct"] < 0]
    deficits.sort(key=lambda row: (row["gap_pct"], CATEGORY_ORDER.index(row["category"])))
    largest_deficit = deficits[0]["category"] if deficits else None

    duplicate_ids = sorted(
        [
            item["id"]
            for item in scoped
            if item.get("status") == "Duplicate" or item.get("duplicate_of")
        ],
        key=lambda item_id: next(
            ((item.get("closed_at") or "", item.get("id") or "") for item in scoped if item["id"] == item_id),
            ("", item_id),
        ),
    )
    cancelled_ids = sorted(
        [item["id"] for item in scoped if item.get("status") == "Cancelled"],
        key=lambda item_id: next(
            ((item.get("closed_at") or "", item.get("id") or "") for item in scoped if item["id"] == item_id),
            ("", item_id),
        ),
    )
    distractor_ids = sorted(
        set(duplicate_ids + cancelled_ids),
        key=lambda item_id: next(
            ((item.get("closed_at") or "", item.get("id") or "") for item in scoped if item["id"] == item_id),
            ("", item_id),
        ),
    )

    owner_team = None
    if largest_deficit:
        team_counts = Counter(
            item["team"] for item in included if item_categories.get(item["id"]) == largest_deficit
        )
        if team_counts:
            owner_team = sorted(team_counts.items(), key=lambda pair: (-pair[1], pair[0]))[0][0]
        elif teams:
            totals = Counter(item["team"] for item in included)
            owner_team = sorted(teams, key=lambda team: (totals.get(team, 0), team))[0]

    secondary = deficits[1]["category"] if len(deficits) > 1 else None
    return {
        "scope": {
            "scope_id": args.scope_id,
            "quarter": args.quarter,
            "teams": teams,
            "product_areas": product_areas,
            "target_scope_id": (target or {}).get("scope_id"),
            "total_included": total,
        },
        "included_work_item_ids": [item["id"] for item in included],
        "item_categories": item_categories,
        "category_counts": counts,
        "category_percentages": actual,
        "mix_table": mix_table,
        "gap_table": [
            {
                "category": row["category"],
                "target_pct": row["target_pct"],
                "actual_pct": row["actual_pct"],
                "gap_pct": row["gap_pct"],
            }
            for row in mix_table
        ],
        "under_invested_categories": [row["category"] for row in deficits],
        "largest_deficit_category": largest_deficit,
        "follow_up_action": {
            "action": "REBALANCE_CAPACITY" if deficits else "MAINTAIN_CURRENT_MIX",
            "primary_category": largest_deficit,
            "secondary_category": secondary,
            "rationale_code": "LARGEST_NEGATIVE_GAP" if deficits else "NO_NEGATIVE_GAPS",
        },
        "recommended_action": {
            "action": "REBALANCE_CAPACITY" if deficits else "MAINTAIN_CURRENT_MIX",
            "category": largest_deficit,
            "owner_team": owner_team,
        },
        "exclusion_flags": {
            "excluded_duplicate_ids": duplicate_ids,
            "excluded_cancelled_ids": cancelled_ids,
            "ignored_mirror_status_and_legacy_category": True,
        },
        "excluded_distractor_ids": distractor_ids,
    }


def in_sla_window(item: dict[str, Any], as_of: dt.date, window_days: int) -> bool:
    created = parse_date(item.get("created_at"))
    closed = parse_date(item.get("closed_at"))
    if not created or created > as_of:
        return False
    if closed is None or closed > as_of:
        return True
    return as_of - dt.timedelta(days=window_days) <= closed <= as_of


def elapsed_days(item: dict[str, Any], as_of: dt.date) -> int:
    created = parse_date(item.get("created_at"))
    if created is None:
        return 0
    closed = parse_date(item.get("closed_at"))
    end = closed if closed is not None and closed <= as_of else as_of
    return (end - created).days


def aging_bucket(days: int) -> str:
    if days <= 3:
        return "0-3"
    if days <= 7:
        return "4-7"
    if days <= 14:
        return "8-14"
    if days <= 30:
        return "15-30"
    return "31+"


def is_overdue(item: dict[str, Any], as_of: dt.date) -> bool:
    due = parse_date(item.get("due_at"))
    if due is None:
        return False
    closed = parse_date(item.get("closed_at"))
    if closed is not None and closed <= as_of:
        return closed > due
    return as_of > due


def sla_aging(args: argparse.Namespace) -> dict[str, Any]:
    data = load_data(args.base_url)
    as_of = parse_date(args.as_of)
    if as_of is None:
        raise SystemExit("--as-of is required")
    teams = args.team or []
    categories = args.category or ["Security", "Reliability"]

    scoped: list[dict[str, Any]] = []
    for item in data["work_items"]:
        if teams and item.get("team") not in teams:
            continue
        if not in_sla_window(item, as_of, args.recent_closed_window_days):
            continue
        if classify(item) not in categories:
            continue
        scoped.append(item)

    included = [
        item for item in scoped if not is_duplicate_or_cancelled(item)
    ]
    included.sort(key=lambda item: item.get("id") or "")
    included_ids = {item["id"] for item in included}
    overdue = [item for item in included if is_overdue(item, as_of)]
    overdue.sort(key=lambda item: item.get("id") or "")

    buckets = {"0-3": 0, "4-7": 0, "8-14": 0, "15-30": 0, "31+": 0}
    for item in included:
        buckets[aging_bucket(elapsed_days(item, as_of))] += 1

    team_overdue = [
        {
            "team": team,
            "overdue_count": sum(1 for item in overdue if item.get("team") == team),
        }
        for team in sorted(teams or {item.get("team") for item in included})
    ]

    hotspot_counts: Counter[tuple[str, str]] = Counter()
    for item in overdue:
        hotspot_counts[(item.get("team") or "", item.get("owner") or "UNASSIGNED")] += 1
    if hotspot_counts:
        (hot_team, hot_owner), hot_count = sorted(
            hotspot_counts.items(),
            key=lambda pair: (-pair[1], pair[0][0], pair[0][1]),
        )[0]
        hotspot = {"team": hot_team, "owner": hot_owner, "overdue_count": hot_count}
    else:
        hotspot = {"team": None, "owner": None, "overdue_count": 0}

    clusters: dict[str, list[str]] = defaultdict(list)
    for item in scoped:
        duplicate_of = item.get("duplicate_of")
        if duplicate_of and duplicate_of in included_ids:
            clusters[duplicate_of].append(item["id"])
    duplicate_clusters = [
        {"primary_id": primary_id, "duplicate_ids": sorted(ids)}
        for primary_id, ids in sorted(clusters.items())
    ]

    overdue_by_severity = {severity: 0 for severity in ["S1", "S2", "S3", "S4"]}
    for item in overdue:
        severity = item.get("severity")
        if severity in overdue_by_severity:
            overdue_by_severity[severity] += 1

    escalation = sorted(
        overdue,
        key=lambda item: (
            SEVERITY_ORDER.get(item.get("severity"), 99),
            item.get("due_at") or "",
            item.get("id") or "",
        ),
    )

    breach_rate = rounded((len(overdue) / len(included)) if included else 0.0, 3)
    return {
        "scope": {
            "teams": teams,
            "as_of": args.as_of,
            "recent_closed_window_days": args.recent_closed_window_days,
            "categories": categories,
            "sla_categories": categories,
        },
        "included_primary_ids": [item["id"] for item in included],
        "overdue_primary_ids": [item["id"] for item in overdue],
        "aging_bucket_counts": buckets,
        "team_overdue_counts": team_overdue,
        "top_hotspot": hotspot,
        "duplicate_clusters": duplicate_clusters,
        "missing_owner_ids": sorted(item["id"] for item in included if not item.get("owner")),
        "overdue_counts_by_severity": overdue_by_severity,
        "escalation_queue_ids": [item["id"] for item in escalation],
        "breach_rate": breach_rate,
        "sla_breach_rate": breach_rate,
    }


def release_readiness(args: argparse.Namespace) -> dict[str, Any]:
    data = load_data(args.base_url)
    work_by_id = {item["id"]: item for item in data["work_items"]}
    release_items = [
        item
        for item in data["work_items"]
        if item.get("release_id") == args.release_id and not is_duplicate_or_cancelled(item)
    ]
    release_item_ids = {item["id"] for item in release_items}
    milestones = sorted(
        [milestone for milestone in data["milestones"] if milestone.get("release_id") == args.release_id],
        key=lambda milestone: milestone.get("id") or "",
    )

    milestone_completion = []
    total_primary = 0
    total_complete = 0
    for milestone in milestones:
        items = [item for item in release_items if item.get("milestone_id") == milestone.get("id")]
        complete = sum(1 for item in items if is_complete(item))
        total = len(items)
        total_primary += total
        total_complete += complete
        milestone_completion.append(
            {
                "milestone_id": milestone["id"],
                "complete_primary": complete,
                "primary_total": total,
                "completion_pct": rounded((complete / total * 100) if total else 0.0, 1),
            }
        )

    unresolved_blockers = [
        blocker
        for blocker in data["blockers"]
        if blocker.get("release_id") == args.release_id
        and not blocker.get("resolved_at")
        and blocker.get("status") != "Resolved"
    ]
    high_blockers = [
        blocker for blocker in unresolved_blockers if blocker.get("severity") in HIGH_IMPACT_BLOCKERS
    ]
    blocker_cause_counts = dict(sorted(Counter(blocker.get("cause") for blocker in high_blockers).items()))

    gating_ids = sorted(
        {
            blocker["work_item_id"]
            for blocker in high_blockers
            if blocker.get("work_item_id") in release_item_ids
            and not is_complete(work_by_id[blocker["work_item_id"]])
        }
    )

    non_complete_release_ids = {
        item["id"] for item in release_items if not is_complete(item)
    }
    deps_by_blocked: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for dep in data["dependencies"]:
        if dep.get("relation") in CRITICAL_DEPENDENCY_RELATIONS:
            deps_by_blocked[dep.get("blocked_id")].append(dep)

    chains: set[tuple[str, ...]] = set()
    for start_id in sorted(non_complete_release_ids):
        for dep in sorted(deps_by_blocked.get(start_id, []), key=lambda row: row.get("depends_on_id") or ""):
            depends_on_id = dep.get("depends_on_id")
            target = work_by_id.get(depends_on_id)
            if not target or is_duplicate_or_cancelled(target):
                continue
            if not is_complete(target):
                chains.add((start_id, depends_on_id))

    critical_dependency_chains = [list(chain) for chain in sorted(chains)]
    readiness_score = rounded((total_complete / total_primary) if total_primary else 0.0, 3)
    if gating_ids or critical_dependency_chains or readiness_score < 0.8:
        ship_decision = "NO_SHIP"
    elif readiness_score < 1.0 or unresolved_blockers:
        ship_decision = "SHIP_WITH_WATCH"
    else:
        ship_decision = "SHIP"

    return {
        "release_id": args.release_id,
        "ship_decision": ship_decision,
        "milestone_completion": milestone_completion,
        "gating_work_item_ids": gating_ids,
        "blocker_cause_counts": blocker_cause_counts,
        "critical_dependency_chains": critical_dependency_chains,
        "readiness_score": readiness_score,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    portfolio = subparsers.add_parser("portfolio-mix")
    portfolio.add_argument("--base-url", required=True)
    portfolio.add_argument("--scope-id")
    portfolio.add_argument("--quarter", required=True)
    portfolio.add_argument("--team", action="append")
    portfolio.add_argument("--product-area", action="append")
    portfolio.set_defaults(func=portfolio_mix)

    sla = subparsers.add_parser("sla-aging")
    sla.add_argument("--base-url", required=True)
    sla.add_argument("--as-of", required=True)
    sla.add_argument("--recent-closed-window-days", type=int, required=True)
    sla.add_argument("--team", action="append")
    sla.add_argument("--category", action="append")
    sla.set_defaults(func=sla_aging)

    release = subparsers.add_parser("release-readiness")
    release.add_argument("--base-url", required=True)
    release.add_argument("--release-id", required=True)
    release.set_defaults(func=release_readiness)

    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = args.func(args)
    print(json.dumps(result, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
