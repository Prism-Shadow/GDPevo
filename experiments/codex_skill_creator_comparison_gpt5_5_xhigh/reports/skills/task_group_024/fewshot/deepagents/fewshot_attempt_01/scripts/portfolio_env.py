#!/usr/bin/env python3
"""Helpers for engineering portfolio environment tasks.

This script intentionally contains reusable mechanics only: endpoint loading,
portfolio category resolution, primary/duplicate status handling, and common
calculations for portfolio mix, SLA aging, and release readiness tasks.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any


CATEGORY_ORDER = ["NewFeature", "TechDebt", "Reliability", "Security"]
TARGET_FIELDS = {
    "NewFeature": "new_feature_pct",
    "TechDebt": "tech_debt_pct",
    "Reliability": "reliability_pct",
    "Security": "security_pct",
}

COMPLETE_STATUSES = {"Closed", "Done", "Verified", "Deployed", "Complete"}
DUPLICATE_STATUSES = {"Duplicate"}
CANCELLED_STATUSES = {"Cancelled"}

SECURITY_WORK_TYPES = {"Security", "Compliance"}
RELIABILITY_WORK_TYPES = {"Reliability", "Incident"}
TECH_DEBT_WORK_TYPES = {"Refactor", "Chore", "Dependency"}
NEW_FEATURE_WORK_TYPES = {"Feature", "Enhancement"}

SECURITY_SIGNALS = {"security", "cve", "auth", "encryption", "compliance"}
RELIABILITY_SIGNALS = {"reliability", "incident", "outage", "latency", "flaky"}
TECH_DEBT_SIGNALS = {"cleanup", "refactor", "migration", "dependency", "tech-debt", "debt", "maintenance", "chore"}
NEW_FEATURE_SIGNALS = {"feature", "rollout", "enhancement", "customer-request", "new"}

SLA_BUCKETS = ["0-3", "4-7", "8-14", "15-30", "31+"]
SEVERITY_ORDER = {"S1": 0, "S2": 1, "S3": 2, "S4": 3}
BLOCKER_HIGH_IMPACT = {"High", "Critical"}


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def date_str(value: date | None) -> str | None:
    return value.isoformat() if value else None


def rounded(value: float, places: int) -> float:
    quant = Decimal("1").scaleb(-places)
    return float(Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_UP))


def pct(numerator: int, denominator: int, places: int = 1) -> float:
    if denominator == 0:
        return 0.0
    return rounded((numerator / denominator) * 100.0, places)


def rate(numerator: int, denominator: int, places: int = 3) -> float:
    if denominator == 0:
        return 0.0
    return rounded(numerator / denominator, places)


def fetch_json(base_url: str, path: str, token: str | None = None) -> dict[str, Any]:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    req = urllib.request.Request(url)
    if token:
        req.add_header("X-Env-Token", token)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GET {path} failed with HTTP {exc.code}: {body}") from exc


def load_environment(base_url: str, token: str | None = None) -> dict[str, Any]:
    return {
        "work_items": fetch_json(base_url, "/api/work-items", token).get("work_items", []),
        "mix_targets": fetch_json(base_url, "/api/mix-targets", token).get("mix_targets", []),
        "sla_policy": fetch_json(base_url, "/api/sla-policy", token).get("sla_policy", []),
        "releases": fetch_json(base_url, "/api/releases", token).get("releases", []),
        "milestones": fetch_json(base_url, "/api/milestones", token).get("milestones", []),
        "blockers": fetch_json(base_url, "/api/blockers", token).get("blockers", []),
        "dependencies": fetch_json(base_url, "/api/dependencies", token).get("dependencies", []),
    }


def normalize_token(value: str) -> str:
    return value.strip().lower()


def item_tokens(item: dict[str, Any]) -> set[str]:
    tokens: set[str] = set()
    work_type = item.get("work_type")
    if work_type:
        tokens.add(normalize_token(str(work_type)))
    for label in item.get("labels") or []:
        tokens.add(normalize_token(str(label)))
    title = str(item.get("title") or "")
    for token in re.findall(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)?", title.lower()):
        tokens.add(token)
    return tokens


def resolve_category(item: dict[str, Any]) -> str:
    """Resolve exactly one portfolio category.

    Authoritative signals are work_type, labels, and title text. Stale mirror
    fields such as legacy_category are deliberately ignored.
    """
    work_type = item.get("work_type")
    tokens = item_tokens(item)
    if work_type in SECURITY_WORK_TYPES or tokens & SECURITY_SIGNALS:
        return "Security"
    if work_type in RELIABILITY_WORK_TYPES or tokens & RELIABILITY_SIGNALS:
        return "Reliability"
    if work_type in TECH_DEBT_WORK_TYPES or tokens & TECH_DEBT_SIGNALS:
        return "TechDebt"
    if work_type in NEW_FEATURE_WORK_TYPES or tokens & NEW_FEATURE_SIGNALS:
        return "NewFeature"
    if work_type == "Bug":
        return "TechDebt"
    return "TechDebt"


def is_duplicate(item: dict[str, Any]) -> bool:
    return bool(item.get("duplicate_of")) or item.get("status") in DUPLICATE_STATUSES


def is_cancelled(item: dict[str, Any]) -> bool:
    return item.get("status") in CANCELLED_STATUSES


def is_primary(item: dict[str, Any]) -> bool:
    return not is_duplicate(item) and not is_cancelled(item)


def is_complete(item: dict[str, Any]) -> bool:
    return item.get("status") in COMPLETE_STATUSES


def quarter_bounds(quarter: str) -> tuple[date, date]:
    match = re.fullmatch(r"(\d{4})-Q([1-4])", quarter.strip())
    if not match:
        raise ValueError(f"Quarter must look like YYYY-Qn, got {quarter!r}")
    year = int(match.group(1))
    q = int(match.group(2))
    start_month = (q - 1) * 3 + 1
    start = date(year, start_month, 1)
    if q == 4:
        end = date(year, 12, 31)
    else:
        end = date(year, start_month + 3, 1) - timedelta(days=1)
    return start, end


def closed_in_range(item: dict[str, Any], start: date, end: date) -> bool:
    closed = parse_date(item.get("closed_at"))
    return bool(closed and start <= closed <= end)


def sort_by_closed_then_id(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(items, key=lambda item: (item.get("closed_at") or "", item.get("id") or ""))


def find_mix_target(data: dict[str, Any], scope_id: str | None, quarter: str, teams: list[str], product_areas: list[str]) -> dict[str, Any] | None:
    targets = data["mix_targets"]
    if scope_id:
        for target in targets:
            if target.get("scope_id") == scope_id:
                return target
    product_text = " + ".join(product_areas)
    for target in targets:
        if target.get("quarter") != quarter:
            continue
        if target.get("product_area") != product_text and target.get("product_area") not in product_areas:
            continue
        team_group = str(target.get("team_group") or "")
        if all(team in team_group for team in teams):
            return target
    return None


def portfolio_mix(data: dict[str, Any], quarter: str, teams: list[str], product_areas: list[str], target_scope_id: str | None) -> dict[str, Any]:
    start, end = quarter_bounds(quarter)
    team_set = set(teams)
    product_set = set(product_areas)

    scoped = [
        item
        for item in data["work_items"]
        if item.get("team") in team_set
        and item.get("product_area") in product_set
        and closed_in_range(item, start, end)
    ]
    included = sort_by_closed_then_id([item for item in scoped if is_primary(item) and is_complete(item)])
    duplicate_items = sort_by_closed_then_id([item for item in scoped if is_duplicate(item)])
    cancelled_items = sort_by_closed_then_id([item for item in scoped if is_cancelled(item)])

    counts = {category: 0 for category in CATEGORY_ORDER}
    by_category_team: dict[str, Counter[str]] = {category: Counter() for category in CATEGORY_ORDER}
    for item in included:
        category = resolve_category(item)
        counts[category] += 1
        by_category_team[category][item.get("team") or ""] += 1

    total = len(included)
    actual = {category: pct(counts[category], total, 1) for category in CATEGORY_ORDER}
    target = find_mix_target(data, target_scope_id, quarter, teams, product_areas)
    target_pct = {
        category: rounded(float(target.get(TARGET_FIELDS[category], 0.0)) * 100.0, 1) if target else 0.0
        for category in CATEGORY_ORDER
    }
    gaps = {category: rounded(actual[category] - target_pct[category], 1) for category in CATEGORY_ORDER}
    mix_table = [
        {
            "category": category,
            "count": counts[category],
            "actual_pct": actual[category],
            "target_pct": target_pct[category],
            "gap_pct": gaps[category],
        }
        for category in CATEGORY_ORDER
    ]
    under = sorted([category for category in CATEGORY_ORDER if gaps[category] < 0], key=lambda category: (gaps[category], CATEGORY_ORDER.index(category)))
    largest_deficit = under[0] if under else None
    owner_team = None
    if largest_deficit:
        ranked_teams = sorted(
            teams,
            key=lambda team: (-by_category_team[largest_deficit][team], teams.index(team)),
        )
        owner_team = ranked_teams[0] if ranked_teams else None

    follow_up = {
        "action": "REBALANCE_CAPACITY" if under else "MAINTAIN_CURRENT_MIX",
        "primary_category": under[0] if under else None,
        "secondary_category": under[1] if len(under) > 1 else None,
        "rationale_code": "LARGEST_NEGATIVE_GAP" if under else "NO_NEGATIVE_GAPS",
    }

    return {
        "quarter": quarter,
        "teams": teams,
        "product_areas": product_areas,
        "target_scope_id": target.get("scope_id") if target else target_scope_id,
        "total_included": total,
        "included_work_item_ids": [item["id"] for item in included],
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
        "under_invested_categories": under,
        "largest_deficit_category": largest_deficit,
        "recommended_owner_team": owner_team,
        "follow_up_action": follow_up,
        "excluded_duplicate_ids": [item["id"] for item in duplicate_items],
        "excluded_cancelled_ids": [item["id"] for item in cancelled_items],
        "excluded_distractor_ids": [item["id"] for item in sort_by_closed_then_id(duplicate_items + cancelled_items)],
        "ignored_mirror_status_and_legacy_category": True,
    }


def item_in_sla_population(item: dict[str, Any], as_of: date, window_days: int) -> bool:
    created = parse_date(item.get("created_at"))
    if created and created > as_of:
        return False
    closed = parse_date(item.get("closed_at"))
    if not closed or closed > as_of:
        return True
    return as_of - timedelta(days=window_days) <= closed <= as_of


def due_date(item: dict[str, Any], sla_policy: dict[str, int]) -> date | None:
    due = parse_date(item.get("due_at"))
    if due:
        return due
    created = parse_date(item.get("created_at"))
    severity = item.get("severity")
    if created and severity in sla_policy:
        return created + timedelta(days=sla_policy[severity])
    return None


def is_overdue(item: dict[str, Any], as_of: date, sla_policy: dict[str, int]) -> bool:
    due = due_date(item, sla_policy)
    if not due:
        return False
    closed = parse_date(item.get("closed_at"))
    if closed and closed <= as_of and is_complete(item):
        return closed > due
    return due < as_of


def age_days(item: dict[str, Any], as_of: date) -> int:
    created = parse_date(item.get("created_at"))
    if not created:
        return 0
    closed = parse_date(item.get("closed_at"))
    end = closed if closed and closed <= as_of else as_of
    return max((end - created).days, 0)


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


def duplicate_clusters(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for item in items:
        primary_id = item.get("duplicate_of")
        if primary_id:
            grouped[str(primary_id)].append(str(item["id"]))
    return [
        {"primary_id": primary_id, "duplicate_ids": sorted(ids)}
        for primary_id, ids in sorted(grouped.items())
    ]


def sla_aging(data: dict[str, Any], teams: list[str], categories: list[str], as_of_text: str, window_days: int) -> dict[str, Any]:
    as_of = date.fromisoformat(as_of_text)
    team_set = set(teams)
    category_set = set(categories)
    sla_policy = {row["severity"]: int(row["days_to_due"]) for row in data["sla_policy"]}

    scoped = [
        item
        for item in data["work_items"]
        if item.get("team") in team_set
        and resolve_category(item) in category_set
        and item_in_sla_population(item, as_of, window_days)
    ]
    included = sorted([item for item in scoped if is_primary(item)], key=lambda item: item["id"])
    duplicates = [item for item in scoped if is_duplicate(item)]
    overdue = [item for item in included if is_overdue(item, as_of, sla_policy)]

    buckets = {bucket: 0 for bucket in SLA_BUCKETS}
    for item in included:
        buckets[age_bucket(age_days(item, as_of))] += 1

    overdue_by_team = Counter(item.get("team") or "" for item in overdue)
    team_counts = [{"team": team, "overdue_count": overdue_by_team[team]} for team in sorted(teams)]

    hotspot_counts = Counter((item.get("team") or "", item.get("owner") or "UNASSIGNED") for item in overdue)
    if hotspot_counts:
        (hotspot_team, hotspot_owner), hotspot_count = sorted(
            hotspot_counts.items(),
            key=lambda entry: (-entry[1], entry[0][0], entry[0][1]),
        )[0]
    else:
        hotspot_team, hotspot_owner, hotspot_count = None, None, 0

    severity_counts = {severity: 0 for severity in SEVERITY_ORDER}
    for item in overdue:
        severity = item.get("severity")
        if severity in severity_counts:
            severity_counts[severity] += 1

    escalation = sorted(
        overdue,
        key=lambda item: (
            SEVERITY_ORDER.get(item.get("severity"), 99),
            date_str(due_date(item, sla_policy)) or "",
            int(item.get("priority") or 99),
            item.get("id") or "",
        ),
    )

    return {
        "scope": {
            "teams": sorted(teams),
            "as_of": as_of_text,
            "recent_closed_window_days": window_days,
            "categories": categories,
        },
        "included_primary_ids": [item["id"] for item in included],
        "overdue_primary_ids": [item["id"] for item in sorted(overdue, key=lambda item: item["id"])],
        "aging_bucket_counts": buckets,
        "team_overdue_counts": team_counts,
        "top_hotspot": {
            "team": hotspot_team,
            "owner": hotspot_owner,
            "overdue_count": hotspot_count,
        },
        "duplicate_clusters": duplicate_clusters(duplicates),
        "missing_owner_ids": [item["id"] for item in included if not item.get("owner")],
        "overdue_counts_by_severity": severity_counts,
        "escalation_queue_ids": [item["id"] for item in escalation],
        "breach_rate": rate(len(overdue), len(included), 3),
        "sla_breach_rate": rate(len(overdue), len(included), 3),
    }


def unresolved_blocker(blocker: dict[str, Any]) -> bool:
    return blocker.get("resolved_at") is None and blocker.get("status") != "Resolved"


def release_readiness(data: dict[str, Any], release_id: str) -> dict[str, Any]:
    by_id = {item["id"]: item for item in data["work_items"]}
    release_items = [item for item in data["work_items"] if item.get("release_id") == release_id and is_primary(item)]
    milestones = sorted([row for row in data["milestones"] if row.get("release_id") == release_id], key=lambda row: row["id"])

    milestone_completion = []
    total_primary = 0
    total_complete = 0
    for milestone in milestones:
        items = [item for item in release_items if item.get("milestone_id") == milestone["id"]]
        complete = sum(1 for item in items if is_complete(item))
        total = len(items)
        total_complete += complete
        total_primary += total
        milestone_completion.append(
            {
                "milestone_id": milestone["id"],
                "complete_primary": complete,
                "primary_total": total,
                "completion_pct": pct(complete, total, 1),
            }
        )

    high_blockers = [
        blocker
        for blocker in data["blockers"]
        if blocker.get("release_id") == release_id
        and unresolved_blocker(blocker)
        and blocker.get("severity") in BLOCKER_HIGH_IMPACT
    ]
    blocker_cause_counts = dict(sorted(Counter(blocker["cause"] for blocker in high_blockers).items()))

    non_complete_release_ids = {item["id"] for item in release_items if not is_complete(item)}
    blocker_gates = {
        blocker["work_item_id"]
        for blocker in high_blockers
        if blocker.get("work_item_id") in non_complete_release_ids
    }

    edges: dict[str, list[str]] = defaultdict(list)
    for dep in data["dependencies"]:
        edges[str(dep["blocked_id"])].append(str(dep["depends_on_id"]))
    for blocked_id in edges:
        edges[blocked_id].sort()

    chains: list[list[str]] = []

    def visit(start_id: str, current_id: str, path: list[str], seen: set[str]) -> None:
        for depends_on in edges.get(current_id, []):
            if depends_on in seen:
                continue
            item = by_id.get(depends_on)
            new_path = path + [depends_on]
            if item and is_primary(item) and not is_complete(item):
                chains.append(new_path)
                continue
            if item:
                visit(start_id, depends_on, new_path, seen | {depends_on})

    for item_id in sorted(non_complete_release_ids):
        visit(item_id, item_id, [item_id], {item_id})

    chains = sorted(chains)
    dependency_gates = {chain[0] for chain in chains}
    gating_ids = sorted(blocker_gates | dependency_gates)

    any_unresolved = any(
        blocker.get("release_id") == release_id and unresolved_blocker(blocker)
        for blocker in data["blockers"]
    )
    readiness_score = rate(total_complete, total_primary, 3)
    if high_blockers or chains:
        decision = "NO_SHIP"
    elif readiness_score < 1.0 or any_unresolved:
        decision = "SHIP_WITH_WATCH"
    else:
        decision = "SHIP"

    return {
        "release_id": release_id,
        "ship_decision": decision,
        "milestone_completion": milestone_completion,
        "gating_work_item_ids": gating_ids,
        "blocker_cause_counts": blocker_cause_counts,
        "critical_dependency_chains": chains,
        "readiness_score": readiness_score,
    }


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-url", default=os.environ.get("TASK_ENV_BASE_URL"), help="Environment base URL")
    parser.add_argument("--token", default=os.environ.get("TASK_ENV_TOKEN"), help="Optional X-Env-Token")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    portfolio_parser = subparsers.add_parser("portfolio", help="Draft portfolio mix calculations")
    add_common_args(portfolio_parser)
    portfolio_parser.add_argument("--quarter", required=True)
    portfolio_parser.add_argument("--team", action="append", required=True, dest="teams")
    portfolio_parser.add_argument("--product-area", action="append", required=True, dest="product_areas")
    portfolio_parser.add_argument("--target-scope-id")

    sla_parser = subparsers.add_parser("sla", help="Draft SLA aging calculations")
    add_common_args(sla_parser)
    sla_parser.add_argument("--team", action="append", required=True, dest="teams")
    sla_parser.add_argument("--category", action="append", required=True, dest="categories")
    sla_parser.add_argument("--as-of", required=True)
    sla_parser.add_argument("--recent-closed-window-days", type=int, required=True)

    release_parser = subparsers.add_parser("release", help="Draft release readiness calculations")
    add_common_args(release_parser)
    release_parser.add_argument("--release-id", required=True)

    args = parser.parse_args(argv)
    if not args.base_url:
        parser.error("--base-url is required unless TASK_ENV_BASE_URL is set")

    data = load_environment(args.base_url, args.token)
    if args.command == "portfolio":
        output = portfolio_mix(data, args.quarter, args.teams, args.product_areas, args.target_scope_id)
    elif args.command == "sla":
        output = sla_aging(data, args.teams, args.categories, args.as_of, args.recent_closed_window_days)
    elif args.command == "release":
        output = release_readiness(data, args.release_id)
    else:
        parser.error(f"unknown command {args.command}")

    print(json.dumps(output, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
