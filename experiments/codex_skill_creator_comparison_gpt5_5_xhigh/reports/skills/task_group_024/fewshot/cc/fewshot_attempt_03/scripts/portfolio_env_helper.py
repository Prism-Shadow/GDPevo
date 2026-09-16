#!/usr/bin/env python3
"""Helper calculations for engineering portfolio task environments."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta


CATEGORY_ORDER = ["NewFeature", "TechDebt", "Reliability", "Security"]
COMPLETE_STATUSES = {"closed", "done", "verified", "deployed", "complete", "completed"}
EXCLUDED_STATUSES = {"duplicate", "cancelled", "canceled"}
SEVERITY_ORDER = {"S1": 0, "S2": 1, "S3": 2, "S4": 3}

SECURITY_SIGNALS = {
    "security",
    "cve",
    "auth",
    "encryption",
    "compliance",
    "audit",
    "vulnerability",
}
RELIABILITY_SIGNALS = {"reliability", "incident", "outage", "latency", "flaky", "bug"}
TECH_DEBT_SIGNALS = {
    "tech debt",
    "tech-debt",
    "techdebt",
    "refactor",
    "cleanup",
    "migration",
    "chore",
    "dependency",
    "deprecate",
    "maintenance",
}
FEATURE_SIGNALS = {"feature", "enhancement", "rollout", "launch", "experiment", "new"}
CRITICAL_RELATION_MARKERS = (
    "blocks-release-readiness",
    "security-review",
    "validation",
    "audit-evidence",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    mix = sub.add_parser("portfolio-mix")
    add_base(mix)
    mix.add_argument("--scope-id", required=True)
    mix.add_argument("--quarter", required=True)
    mix.add_argument("--teams", nargs="+", required=True)
    mix.add_argument("--product-areas", nargs="+", required=True)

    sla = sub.add_parser("sla-aging")
    add_base(sla)
    sla.add_argument("--as-of", required=True)
    sla.add_argument("--recent-closed-window-days", type=int, required=True)
    sla.add_argument("--teams", nargs="+", required=True)
    sla.add_argument("--categories", nargs="+", required=True)

    release = sub.add_parser("release-readiness")
    add_base(release)
    release.add_argument("--release-id", required=True)

    return parser.parse_args()


def add_base(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-url", required=True, help="Task environment base URL")


def main() -> int:
    args = parse_args()
    base_url = args.base_url.rstrip("/")
    if args.command == "portfolio-mix":
        result = portfolio_mix(base_url, args.scope_id, args.quarter, args.teams, args.product_areas)
    elif args.command == "sla-aging":
        result = sla_aging(
            base_url,
            args.as_of,
            args.recent_closed_window_days,
            args.teams,
            args.categories,
        )
    elif args.command == "release-readiness":
        result = release_readiness(base_url, args.release_id)
    else:
        raise AssertionError(args.command)
    json.dump(result, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


def get_json(base_url: str, path: str, params: dict[str, object] | None = None) -> dict:
    query = ""
    if params:
        query = "?" + urllib.parse.urlencode(params, doseq=True)
    url = f"{base_url}{path}{query}"
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


def get_work_items(base_url: str, params: dict[str, object] | None = None) -> list[dict]:
    payload = get_json(base_url, "/api/work-items", params)
    return payload.get("work_items", [])


def get_work_item(base_url: str, item_id: str) -> dict | None:
    try:
        return get_json(base_url, f"/api/work-items/{urllib.parse.quote(item_id)}").get("work_item")
    except Exception:
        return None


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def quarter_bounds(quarter: str) -> tuple[date, date]:
    year_text, q_text = quarter.split("-Q", 1)
    year = int(year_text)
    quarter_num = int(q_text)
    start_month = (quarter_num - 1) * 3 + 1
    start = date(year, start_month, 1)
    if quarter_num == 4:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, start_month + 3, 1)
    return start, end


def norm(value: object) -> str:
    return str(value or "").strip().lower()


def status_of(item: dict) -> str:
    return norm(item.get("status"))


def is_complete(item: dict) -> bool:
    return status_of(item) in COMPLETE_STATUSES


def is_excluded_record(item: dict) -> bool:
    return bool(item.get("duplicate_of")) or status_of(item) in EXCLUDED_STATUSES


def is_primary(item: dict) -> bool:
    return not is_excluded_record(item)


def signal_text(item: dict) -> str:
    parts = [item.get("work_type"), item.get("title")]
    parts.extend(item.get("labels") or [])
    return " ".join(norm(part) for part in parts)


def has_signal(text: str, signals: set[str]) -> bool:
    return any(signal in text for signal in signals)


def classify_category(item: dict) -> str:
    text = signal_text(item)
    if has_signal(text, SECURITY_SIGNALS):
        return "Security"
    if has_signal(text, RELIABILITY_SIGNALS):
        return "Reliability"
    if has_signal(text, TECH_DEBT_SIGNALS):
        return "TechDebt"
    if has_signal(text, FEATURE_SIGNALS):
        return "NewFeature"
    return "NewFeature"


def sort_by_closed_then_id(item: dict) -> tuple[str, str]:
    return (item.get("closed_at") or "", item.get("id") or "")


def pct(numerator: int, denominator: int, digits: int = 1) -> float:
    if denominator == 0:
        return round(0.0, digits)
    return round((numerator / denominator) * 100.0, digits)


def ratio(numerator: int, denominator: int, digits: int = 3) -> float:
    if denominator == 0:
        return round(0.0, digits)
    return round(numerator / denominator, digits)


def target_pct(value: object) -> float:
    number = float(value)
    if abs(number) <= 1.0:
        number *= 100.0
    return round(number, 1)


def portfolio_mix(
    base_url: str,
    scope_id: str,
    quarter: str,
    teams: list[str],
    product_areas: list[str],
) -> dict:
    team_set = set(teams)
    area_set = set(product_areas)
    start, end = quarter_bounds(quarter)
    items = get_work_items(base_url)

    same_scope = [
        item
        for item in items
        if item.get("team") in team_set
        and item.get("product_area") in area_set
        and date_in_range(parse_date(item.get("closed_at")), start, end)
    ]
    included = sorted(
        [item for item in same_scope if is_primary(item) and is_complete(item)],
        key=sort_by_closed_then_id,
    )
    duplicate_ids = [item["id"] for item in sorted(same_scope, key=sort_by_closed_then_id) if item.get("duplicate_of") or status_of(item) == "duplicate"]
    cancelled_ids = [item["id"] for item in sorted(same_scope, key=sort_by_closed_then_id) if status_of(item) in {"cancelled", "canceled"}]

    counts = {category: 0 for category in CATEGORY_ORDER}
    team_category_counts: dict[str, Counter] = {team: Counter() for team in teams}
    for item in included:
        category = classify_category(item)
        counts[category] += 1
        team_category_counts.setdefault(item.get("team"), Counter())[category] += 1

    target = find_mix_target(base_url, scope_id)
    total = len(included)
    actuals = {category: pct(counts[category], total, 1) for category in CATEGORY_ORDER}
    targets = {
        "NewFeature": target_pct(target.get("new_feature_pct", 0.0)),
        "TechDebt": target_pct(target.get("tech_debt_pct", 0.0)),
        "Reliability": target_pct(target.get("reliability_pct", 0.0)),
        "Security": target_pct(target.get("security_pct", 0.0)),
    }
    mix_table = []
    for category in CATEGORY_ORDER:
        gap = round(actuals[category] - targets[category], 1)
        mix_table.append(
            {
                "category": category,
                "count": counts[category],
                "actual_pct": actuals[category],
                "target_pct": targets[category],
                "gap_pct": gap,
            }
        )

    deficits = [row for row in mix_table if row["gap_pct"] < 0]
    deficits.sort(key=lambda row: (row["gap_pct"], CATEGORY_ORDER.index(row["category"])))
    primary = deficits[0]["category"] if deficits else None
    secondary = deficits[1]["category"] if len(deficits) > 1 else None

    return {
        "scope_id": scope_id,
        "quarter": quarter,
        "teams": teams,
        "product_areas": product_areas,
        "target_scope_id": scope_id,
        "total_included": total,
        "included_work_item_ids": [item["id"] for item in included],
        "category_counts": counts,
        "category_percentages": actuals,
        "gap_table": [
            {
                "category": row["category"],
                "target_pct": row["target_pct"],
                "actual_pct": row["actual_pct"],
                "gap_pct": row["gap_pct"],
            }
            for row in mix_table
        ],
        "mix_table": mix_table,
        "under_invested_categories": [row["category"] for row in deficits],
        "follow_up_action": {
            "action": "REBALANCE_CAPACITY" if primary else "MAINTAIN_CURRENT_MIX",
            "primary_category": primary,
            "secondary_category": secondary,
            "rationale_code": "LARGEST_NEGATIVE_GAP" if primary else "NO_NEGATIVE_GAPS",
        },
        "recommended_action": {
            "action": "REBALANCE_CAPACITY" if primary else "MAINTAIN_CURRENT_MIX",
            "category": primary,
            "owner_team": suggested_owner_team(primary, teams, team_category_counts) if primary else None,
        },
        "exclusions": {
            "excluded_duplicate_ids": duplicate_ids,
            "excluded_cancelled_ids": cancelled_ids,
            "excluded_distractor_ids": sorted(set(duplicate_ids + cancelled_ids), key=lambda item_id: next((sort_by_closed_then_id(item) for item in same_scope if item.get("id") == item_id), ("", item_id))),
        },
    }


def date_in_range(value: date | None, start: date, end: date) -> bool:
    return value is not None and start <= value < end


def find_mix_target(base_url: str, scope_id: str) -> dict:
    payload = get_json(base_url, "/api/mix-targets", {"scope_id": scope_id})
    targets = payload.get("mix_targets", [])
    for target in targets:
        if target.get("scope_id") == scope_id:
            return target
    if len(targets) == 1:
        return targets[0]
    raise SystemExit(f"No mix target found for scope_id={scope_id!r}")


def suggested_owner_team(category: str | None, teams: list[str], counts: dict[str, Counter]) -> str | None:
    if not category:
        return None
    ranked = sorted(teams, key=lambda team: (-counts.get(team, Counter()).get(category, 0), teams.index(team)))
    return ranked[0] if ranked else None


def sla_aging(
    base_url: str,
    as_of_text: str,
    recent_closed_window_days: int,
    teams: list[str],
    categories: list[str],
) -> dict:
    as_of = parse_date(as_of_text)
    if as_of is None:
        raise SystemExit("Invalid --as-of date")
    team_set = set(teams)
    category_set = set(categories)
    closed_start = as_of - timedelta(days=recent_closed_window_days)
    items = get_work_items(base_url)

    relevant = [
        item
        for item in items
        if item.get("team") in team_set and classify_category(item) in category_set
    ]
    included = []
    for item in relevant:
        if not is_primary(item):
            continue
        created_at = parse_date(item.get("created_at"))
        if created_at is not None and created_at > as_of:
            continue
        closed_at = parse_date(item.get("closed_at"))
        if not is_complete(item) or (closed_at is not None and closed_start <= closed_at <= as_of):
            included.append(item)
    included.sort(key=lambda item: item.get("id") or "")
    included_ids = {item["id"] for item in included}

    overdue = [item for item in included if is_overdue(item, as_of)]
    overdue.sort(key=lambda item: item.get("id") or "")

    age_buckets = {"0-3": 0, "4-7": 0, "8-14": 0, "15-30": 0, "31+": 0}
    for item in included:
        age_buckets[age_bucket(age_days(item, as_of))] += 1

    team_overdue = Counter(item.get("team") for item in overdue)
    hotspot_counts = Counter((item.get("team"), item.get("owner") or "UNASSIGNED") for item in overdue)
    hotspot = None
    if hotspot_counts:
        (team, owner), count = sorted(hotspot_counts.items(), key=lambda pair: (-pair[1], pair[0][0] or "", pair[0][1] or ""))[0]
        hotspot = {"team": team, "owner": owner, "overdue_count": count}

    duplicate_clusters = build_duplicate_clusters(relevant, included_ids)
    severity_counts = {severity: 0 for severity in ["S1", "S2", "S3", "S4"]}
    for item in overdue:
        severity = item.get("severity")
        if severity in severity_counts:
            severity_counts[severity] += 1

    return {
        "scope": {
            "teams": teams,
            "as_of": as_of_text,
            "recent_closed_window_days": recent_closed_window_days,
            "categories": categories,
        },
        "included_primary_ids": [item["id"] for item in included],
        "overdue_primary_ids": [item["id"] for item in overdue],
        "aging_bucket_counts": age_buckets,
        "team_overdue_counts": [
            {"team": team, "overdue_count": team_overdue.get(team, 0)}
            for team in sorted(teams)
        ],
        "top_hotspot": hotspot,
        "overdue_counts_by_severity": severity_counts,
        "escalation_queue_ids": [item["id"] for item in sorted(overdue, key=escalation_key)],
        "duplicate_clusters": duplicate_clusters,
        "missing_owner_ids": sorted(item["id"] for item in included if not item.get("owner")),
        "breach_rate": ratio(len(overdue), len(included), 3),
        "sla_breach_rate": ratio(len(overdue), len(included), 3),
    }


def is_overdue(item: dict, as_of: date) -> bool:
    due_at = parse_date(item.get("due_at"))
    if due_at is None:
        return False
    closed_at = parse_date(item.get("closed_at"))
    if is_complete(item) and closed_at is not None:
        return closed_at > due_at
    return as_of > due_at


def age_days(item: dict, as_of: date) -> int:
    created_at = parse_date(item.get("created_at"))
    if created_at is None:
        return 0
    closed_at = parse_date(item.get("closed_at"))
    end = closed_at if is_complete(item) and closed_at is not None else as_of
    return max((end - created_at).days, 0)


def age_bucket(days: int) -> str:
    if days <= 3:
        return "0-3"
    if days <= 7:
        return "4-7"
    if days <= 14:
        return "8-14"
    if days <= 30:
        return "15-30"
    return "31+"


def build_duplicate_clusters(items: list[dict], included_ids: set[str]) -> list[dict]:
    clusters: dict[str, list[str]] = defaultdict(list)
    for item in items:
        primary_id = item.get("duplicate_of")
        if primary_id and primary_id in included_ids:
            clusters[primary_id].append(item["id"])
    return [
        {"primary_id": primary_id, "duplicate_ids": sorted(duplicate_ids)}
        for primary_id, duplicate_ids in sorted(clusters.items())
    ]


def escalation_key(item: dict) -> tuple[int, str, int, str]:
    return (
        SEVERITY_ORDER.get(str(item.get("severity")), 99),
        item.get("due_at") or "",
        int(item.get("priority") or 99),
        item.get("id") or "",
    )


def release_readiness(base_url: str, release_id: str) -> dict:
    release_payload = get_json(base_url, f"/api/releases/{urllib.parse.quote(release_id)}")
    work_items = get_work_items(base_url, {"release_id": release_id})
    milestones = get_json(base_url, "/api/milestones", {"release_id": release_id}).get("milestones", [])
    blockers = get_json(base_url, "/api/blockers", {"release_id": release_id}).get("blockers", [])
    dependencies = get_json(base_url, "/api/dependencies", {"release_id": release_id}).get("dependencies", [])

    primary = [item for item in work_items if item.get("release_id") == release_id and is_primary(item)]
    primary_by_id = {item["id"]: item for item in primary}
    complete = [item for item in primary if is_complete(item)]

    milestone_ids = sorted({m.get("id") for m in milestones if m.get("id")} | {item.get("milestone_id") for item in primary if item.get("milestone_id")})
    milestone_completion = []
    for milestone_id in milestone_ids:
        scoped = [item for item in primary if item.get("milestone_id") == milestone_id]
        done = [item for item in scoped if is_complete(item)]
        milestone_completion.append(
            {
                "milestone_id": milestone_id,
                "complete_primary": len(done),
                "primary_total": len(scoped),
                "completion_pct": pct(len(done), len(scoped), 1),
            }
        )

    high_blockers = [blocker for blocker in blockers if is_unresolved_high_impact_blocker(blocker)]
    blocker_cause_counts = dict(sorted(Counter(blocker.get("cause") for blocker in high_blockers).items()))
    noncomplete_ids = {item["id"] for item in primary if not is_complete(item)}
    blocker_gates = {
        blocker.get("work_item_id")
        for blocker in high_blockers
        if blocker.get("work_item_id") in noncomplete_ids
    }
    dependency_chains = critical_dependency_chains(base_url, release_id, dependencies, primary_by_id, noncomplete_ids)
    dependency_gates = {chain[0] for chain in dependency_chains if chain}
    gating_ids = sorted((blocker_gates | dependency_gates) & noncomplete_ids)
    readiness = ratio(len(complete), len(primary), 3)

    return {
        "release_id": release_id,
        "release": release_payload.get("release", {}),
        "ship_decision": ship_decision(gating_ids, dependency_chains, high_blockers, readiness),
        "milestone_completion": milestone_completion,
        "gating_work_item_ids": gating_ids,
        "blocker_cause_counts": blocker_cause_counts,
        "critical_dependency_chains": dependency_chains,
        "readiness_score": readiness,
    }


def is_unresolved_high_impact_blocker(blocker: dict) -> bool:
    status = norm(blocker.get("status"))
    resolved = blocker.get("resolved_at")
    severity = norm(blocker.get("severity"))
    return not resolved and status not in {"resolved", "closed", "done"} and severity in {"high", "critical"}


def is_critical_relation(relation: object) -> bool:
    text = norm(relation)
    return any(marker in text for marker in CRITICAL_RELATION_MARKERS)


def critical_dependency_chains(
    base_url: str,
    release_id: str,
    dependencies: list[dict],
    primary_by_id: dict[str, dict],
    noncomplete_ids: set[str],
) -> list[list[str]]:
    graph: dict[str, list[str]] = defaultdict(list)
    for dep in dependencies:
        if is_critical_relation(dep.get("relation")):
            graph[dep.get("blocked_id")].append(dep.get("depends_on_id"))

    chains: set[tuple[str, ...]] = set()
    for start_id in sorted(noncomplete_ids):
        walk_dependency_graph(base_url, release_id, graph, primary_by_id, start_id, [start_id], chains)
    return [list(chain) for chain in sorted(chains)]


def walk_dependency_graph(
    base_url: str,
    release_id: str,
    graph: dict[str, list[str]],
    primary_by_id: dict[str, dict],
    current_id: str,
    path: list[str],
    chains: set[tuple[str, ...]],
) -> None:
    if len(path) > 8:
        return
    for next_id in sorted(filter(None, graph.get(current_id, []))):
        if next_id in path:
            continue
        item = primary_by_id.get(next_id)
        if item is None:
            item = get_work_item(base_url, next_id)
        next_path = path + [next_id]
        if item and is_primary(item) and not is_complete(item):
            chains.add(tuple(next_path))
        elif item:
            walk_dependency_graph(base_url, release_id, graph, primary_by_id, next_id, next_path, chains)


def ship_decision(gating_ids: list[str], dependency_chains: list[list[str]], blockers: list[dict], readiness: float) -> str:
    has_critical_blocker = any(norm(blocker.get("severity")) == "critical" for blocker in blockers)
    if gating_ids or dependency_chains or has_critical_blocker:
        return "NO_SHIP"
    if readiness < 1.0 or blockers:
        return "SHIP_WITH_WATCH"
    return "SHIP"


if __name__ == "__main__":
    raise SystemExit(main())
