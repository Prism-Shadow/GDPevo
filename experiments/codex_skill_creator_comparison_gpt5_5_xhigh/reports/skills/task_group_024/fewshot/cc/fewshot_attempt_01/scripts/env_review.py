#!/usr/bin/env python3
"""Reusable helpers for engineering portfolio environment review tasks."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path


CATEGORY_ORDER = ["NewFeature", "TechDebt", "Reliability", "Security"]
COMPLETE_STATUSES = {"closed", "done", "verified", "deployed", "complete"}
DUPLICATE_STATUSES = {"duplicate"}
CANCELLED_STATUSES = {"cancelled", "canceled"}
SEVERITY_RANK = {"S1": 1, "S2": 2, "S3": 3, "S4": 4}
HIGH_IMPACT_BLOCKERS = {"high", "critical"}

SECURITY_TERMS = {
    "security",
    "cve",
    "auth",
    "encryption",
    "compliance",
    "permission",
    "vulnerability",
}
RELIABILITY_TERMS = {
    "reliability",
    "incident",
    "outage",
    "latency",
    "flaky",
    "retry",
    "bug",
    "uptime",
    "rehearsal",
}
TECH_DEBT_TERMS = {
    "refactor",
    "migration",
    "cleanup",
    "dependency",
    "deprecate",
    "legacy",
    "chore",
    "maintenance",
    "stale-export",
}
NEW_FEATURE_TERMS = {
    "feature",
    "enhancement",
    "rollout",
    "launch",
    "customer-request",
}


def parse_env_file(path: str | None) -> tuple[str | None, str | None]:
    if not path:
        return None, None
    p = Path(path)
    if not p.exists():
        return None, None
    base_url = None
    token = None
    for raw in p.read_text().splitlines():
        line = raw.strip()
        if line.startswith("base_url:"):
            base_url = line.split(":", 1)[1].strip()
        elif line.startswith(("query_token:", "token:", "api_token:")):
            token = line.split(":", 1)[1].strip()
    return base_url, token


def get_json(base_url: str, path: str) -> dict:
    url = base_url.rstrip("/") + path
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise SystemExit(f"GET {url} failed: {exc}") from exc


def fetch_all(base_url: str) -> dict:
    payloads = {
        "work_items": get_json(base_url, "/api/work-items").get("work_items", []),
        "mix_targets": get_json(base_url, "/api/mix-targets").get("mix_targets", []),
        "sla_policy": get_json(base_url, "/api/sla-policy").get("sla_policy", []),
        "releases": get_json(base_url, "/api/releases").get("releases", []),
        "milestones": get_json(base_url, "/api/milestones").get("milestones", []),
        "dependencies": get_json(base_url, "/api/dependencies").get("dependencies", []),
        "blockers": get_json(base_url, "/api/blockers").get("blockers", []),
    }
    return payloads


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value[:10])


def quarter_bounds(quarter: str) -> tuple[date, date]:
    match = re.fullmatch(r"(\d{4})-Q([1-4])", quarter)
    if not match:
        raise SystemExit(f"Invalid quarter {quarter!r}; expected YYYY-QN")
    year = int(match.group(1))
    q = int(match.group(2))
    start_month = 3 * (q - 1) + 1
    start = date(year, start_month, 1)
    if q == 4:
        next_start = date(year + 1, 1, 1)
    else:
        next_start = date(year, start_month + 3, 1)
    return start, next_start - timedelta(days=1)


def status_value(item: dict) -> str:
    return str(item.get("status") or "").strip().lower()


def is_complete(item: dict) -> bool:
    return status_value(item) in COMPLETE_STATUSES


def is_duplicate(item: dict) -> bool:
    return bool(item.get("duplicate_of")) or status_value(item) in DUPLICATE_STATUSES


def is_cancelled(item: dict) -> bool:
    return status_value(item) in CANCELLED_STATUSES


def is_primary(item: dict) -> bool:
    return not is_duplicate(item) and not is_cancelled(item)


def text_for_category(item: dict) -> str:
    labels = item.get("labels") or []
    parts = [item.get("work_type") or "", item.get("title") or "", *labels]
    return " ".join(str(part).lower() for part in parts)


def has_term(text: str, terms: set[str]) -> bool:
    for term in terms:
        pattern = r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])"
        if re.search(pattern, text):
            return True
    return False


def classify_category(item: dict) -> str:
    text = text_for_category(item)
    work_type = str(item.get("work_type") or "").strip().lower()
    if work_type in {"security", "compliance"} or has_term(text, SECURITY_TERMS):
        return "Security"
    if work_type in {"reliability", "incident", "bug"} or has_term(text, RELIABILITY_TERMS):
        return "Reliability"
    if work_type in {"refactor", "dependency", "chore"} or has_term(text, TECH_DEBT_TERMS):
        return "TechDebt"
    if work_type in {"feature", "enhancement"} or has_term(text, NEW_FEATURE_TERMS):
        return "NewFeature"
    return "NewFeature"


def round1(value: float) -> float:
    return round(value + 0.0000000001, 1)


def round3(value: float) -> float:
    return round(value + 0.0000000001, 3)


def sort_by_closed_then_id(items: list[dict]) -> list[dict]:
    return sorted(items, key=lambda item: (item.get("closed_at") or "", item.get("id") or ""))


def pct(count: int, total: int) -> float:
    return 0.0 if total == 0 else round1((count / total) * 100.0)


def target_percentages(target: dict | None) -> dict[str, float | None]:
    if not target:
        return {category: None for category in CATEGORY_ORDER}
    return {
        "NewFeature": round1(float(target.get("new_feature_pct", 0)) * 100.0),
        "TechDebt": round1(float(target.get("tech_debt_pct", 0)) * 100.0),
        "Reliability": round1(float(target.get("reliability_pct", 0)) * 100.0),
        "Security": round1(float(target.get("security_pct", 0)) * 100.0),
    }


def choose_target(mix_targets: list[dict], scope_id: str | None, quarter: str, product_areas: list[str]) -> dict | None:
    if scope_id:
        for target in mix_targets:
            if target.get("scope_id") == scope_id:
                return target
    wanted_areas = set(product_areas)
    candidates = [target for target in mix_targets if target.get("quarter") == quarter]
    for target in candidates:
        product_area = str(target.get("product_area") or "")
        if product_area in wanted_areas:
            return target
    return None


def portfolio(args: argparse.Namespace, data: dict) -> dict:
    start, end = quarter_bounds(args.quarter)
    teams = set(args.teams)
    product_areas = set(args.product_areas)

    scoped = []
    for item in data["work_items"]:
        closed = parse_date(item.get("closed_at"))
        if not closed or closed < start or closed > end:
            continue
        if item.get("team") not in teams or item.get("product_area") not in product_areas:
            continue
        scoped.append(item)

    included = [item for item in scoped if is_primary(item) and is_complete(item)]
    included = sort_by_closed_then_id(included)
    counts = {category: 0 for category in CATEGORY_ORDER}
    category_by_id = {}
    for item in included:
        category = classify_category(item)
        category_by_id[item["id"]] = category
        counts[category] += 1

    total = len(included)
    actual = {category: pct(counts[category], total) for category in CATEGORY_ORDER}
    target = choose_target(data["mix_targets"], args.target_scope_id or args.scope_id, args.quarter, args.product_areas)
    target_pct = target_percentages(target)

    mix_rows = []
    gap_by_category = {}
    for category in CATEGORY_ORDER:
        target_value = target_pct[category]
        gap = None if target_value is None else round1(actual[category] - target_value)
        gap_by_category[category] = gap
        mix_rows.append(
            {
                "category": category,
                "count": counts[category],
                "actual_pct": actual[category],
                "target_pct": target_value,
                "gap_pct": gap,
            }
        )

    under_invested = [
        category
        for category in CATEGORY_ORDER
        if gap_by_category[category] is not None and gap_by_category[category] < 0
    ]
    under_invested.sort(key=lambda category: (gap_by_category[category], CATEGORY_ORDER.index(category)))

    duplicate_ids = [item["id"] for item in sort_by_closed_then_id([item for item in scoped if is_duplicate(item)])]
    cancelled_ids = [item["id"] for item in sort_by_closed_then_id([item for item in scoped if is_cancelled(item)])]
    other_distractors = [
        item
        for item in scoped
        if item not in included and not is_duplicate(item) and not is_cancelled(item)
    ]
    distractor_ids = [item["id"] for item in sort_by_closed_then_id([*([item for item in scoped if is_duplicate(item) or is_cancelled(item)]), *other_distractors])]

    primary = under_invested[0] if under_invested else None
    secondary = under_invested[1] if len(under_invested) > 1 else None
    action = "REBALANCE_CAPACITY" if primary else "MAINTAIN_CURRENT_MIX"
    rationale = "LARGEST_NEGATIVE_GAP" if primary else "NO_NEGATIVE_GAPS"

    owner_team = None
    if primary:
        per_team = Counter(item.get("team") for item in included if category_by_id.get(item["id"]) == primary)
        if per_team:
            owner_team = sorted(per_team.items(), key=lambda pair: (-pair[1], args.teams.index(pair[0]) if pair[0] in args.teams else 999, pair[0]))[0][0]
        elif args.teams:
            owner_team = args.teams[0]

    return {
        "scope_id": args.scope_id,
        "quarter": args.quarter,
        "teams": args.teams,
        "product_areas": args.product_areas,
        "target_scope_id": (target or {}).get("scope_id") or args.target_scope_id or args.scope_id,
        "total_included": total,
        "included_work_item_ids": [item["id"] for item in included],
        "category_by_id": category_by_id,
        "category_counts": counts,
        "category_percentages": actual,
        "mix_table": mix_rows,
        "gap_table": [
            {
                "category": row["category"],
                "target_pct": row["target_pct"],
                "actual_pct": row["actual_pct"],
                "gap_pct": row["gap_pct"],
            }
            for row in mix_rows
        ],
        "under_invested_categories": under_invested,
        "largest_deficit_category": primary,
        "follow_up_action": {
            "action": action,
            "primary_category": primary,
            "secondary_category": secondary,
            "rationale_code": rationale,
        },
        "recommended_action": {
            "action": "REBALANCE_CAPACITY" if primary else "MAINTAIN_CURRENT_MIX",
            "category": primary,
            "owner_team": owner_team,
        },
        "exclusion_flags": {
            "excluded_duplicate_ids": duplicate_ids,
            "excluded_cancelled_ids": cancelled_ids,
            "ignored_mirror_status_and_legacy_category": True,
        },
        "excluded_distractor_ids": distractor_ids,
    }


def in_sla_window(item: dict, as_of: date, window_days: int) -> bool:
    created = parse_date(item.get("created_at"))
    if not created or created > as_of:
        return False
    closed = parse_date(item.get("closed_at"))
    if closed is None or closed > as_of:
        return True
    start = as_of - timedelta(days=window_days)
    return start <= closed <= as_of


def due_date(item: dict, policy_by_severity: dict[str, int]) -> date | None:
    due = parse_date(item.get("due_at"))
    if due:
        return due
    created = parse_date(item.get("created_at"))
    severity = item.get("severity")
    if created and severity in policy_by_severity:
        return created + timedelta(days=policy_by_severity[severity])
    return None


def is_overdue(item: dict, as_of: date, policy_by_severity: dict[str, int]) -> bool:
    due = due_date(item, policy_by_severity)
    if not due or due >= as_of:
        return False
    closed = parse_date(item.get("closed_at"))
    return closed is None or closed > due


def age_bucket(item: dict, as_of: date) -> str:
    created = parse_date(item.get("created_at"))
    if not created:
        return "31+"
    closed = parse_date(item.get("closed_at"))
    end = closed if closed and closed <= as_of else as_of
    age = max(0, (end - created).days)
    if age <= 3:
        return "0-3"
    if age <= 7:
        return "4-7"
    if age <= 14:
        return "8-14"
    if age <= 30:
        return "15-30"
    return "31+"


def sla(args: argparse.Namespace, data: dict) -> dict:
    as_of = parse_date(args.as_of)
    if not as_of:
        raise SystemExit("--as-of is required")
    teams = set(args.teams)
    categories = set(args.categories)
    policy_by_severity = {
        row.get("severity"): int(row.get("days_to_due"))
        for row in data["sla_policy"]
        if row.get("severity") and row.get("days_to_due") is not None
    }

    scoped = []
    for item in data["work_items"]:
        if item.get("team") not in teams:
            continue
        if classify_category(item) not in categories:
            continue
        if not in_sla_window(item, as_of, args.recent_closed_window_days):
            continue
        scoped.append(item)

    primary = sorted([item for item in scoped if is_primary(item)], key=lambda item: item["id"])
    duplicates = [item for item in scoped if is_duplicate(item) and item.get("duplicate_of")]
    overdue = sorted(
        [item for item in primary if is_overdue(item, as_of, policy_by_severity)],
        key=lambda item: item["id"],
    )

    bucket_counts = {"0-3": 0, "4-7": 0, "8-14": 0, "15-30": 0, "31+": 0}
    for item in primary:
        bucket_counts[age_bucket(item, as_of)] += 1

    team_counts = Counter(item.get("team") for item in overdue)
    hotspot_counts = Counter((item.get("team"), item.get("owner") or "UNASSIGNED") for item in overdue)
    top_hotspot = None
    if hotspot_counts:
        (team, owner), count = sorted(hotspot_counts.items(), key=lambda pair: (-pair[1], pair[0][0], pair[0][1]))[0]
        top_hotspot = {"team": team, "owner": owner, "overdue_count": count}

    clusters: dict[str, list[str]] = defaultdict(list)
    for item in duplicates:
        clusters[item["duplicate_of"]].append(item["id"])
    duplicate_clusters = [
        {"primary_id": primary_id, "duplicate_ids": sorted(ids)}
        for primary_id, ids in sorted(clusters.items())
    ]

    severity_counts = {severity: 0 for severity in ["S1", "S2", "S3", "S4"]}
    for item in overdue:
        severity = item.get("severity")
        if severity in severity_counts:
            severity_counts[severity] += 1

    escalation = sorted(
        overdue,
        key=lambda item: (
            SEVERITY_RANK.get(item.get("severity"), 999),
            due_date(item, policy_by_severity) or date.max,
            item.get("priority") if item.get("priority") is not None else 999,
            parse_date(item.get("created_at")) or date.max,
            item["id"],
        ),
    )

    breach_rate = 0.0 if not primary else round3(len(overdue) / len(primary))
    return {
        "scope": {
            "teams": sorted(args.teams),
            "as_of": args.as_of,
            "recent_closed_window_days": args.recent_closed_window_days,
            "categories": args.categories,
        },
        "included_primary_ids": [item["id"] for item in primary],
        "overdue_primary_ids": [item["id"] for item in overdue],
        "aging_bucket_counts": bucket_counts,
        "team_overdue_counts": [
            {"team": team, "overdue_count": team_counts.get(team, 0)}
            for team in sorted(args.teams)
        ],
        "top_hotspot": top_hotspot,
        "duplicate_clusters": duplicate_clusters,
        "missing_owner_ids": sorted([item["id"] for item in primary if not item.get("owner")]),
        "overdue_counts_by_severity": severity_counts,
        "escalation_queue_ids": [item["id"] for item in escalation],
        "breach_rate": breach_rate,
        "sla_breach_rate": breach_rate,
    }


def blocker_unresolved(blocker: dict) -> bool:
    status = str(blocker.get("status") or "").strip().lower()
    return not blocker.get("resolved_at") and status not in {"resolved", "closed", "done"}


def blocker_high_impact(blocker: dict) -> bool:
    return str(blocker.get("severity") or "").strip().lower() in HIGH_IMPACT_BLOCKERS


def dependency_chains(start_id: str, dependencies_by_blocked: dict[str, list[str]], items_by_id: dict[str, dict]) -> list[list[str]]:
    chains: list[list[str]] = []

    def walk(path: list[str]) -> None:
        current = path[-1]
        for dependency_id in sorted(dependencies_by_blocked.get(current, [])):
            if dependency_id in path:
                continue
            item = items_by_id.get(dependency_id)
            if item is None or is_duplicate(item) or is_cancelled(item):
                continue
            next_path = [*path, dependency_id]
            if not is_complete(item):
                chains.append(next_path)
            else:
                walk(next_path)

    walk([start_id])
    return chains


def release(args: argparse.Namespace, data: dict) -> dict:
    release_id = args.release_id
    items_by_id = {item["id"]: item for item in data["work_items"]}
    release_items = [
        item
        for item in data["work_items"]
        if item.get("release_id") == release_id and is_primary(item)
    ]
    release_item_ids = {item["id"] for item in release_items}
    milestones = sorted(
        [milestone for milestone in data["milestones"] if milestone.get("release_id") == release_id],
        key=lambda milestone: milestone["id"],
    )

    milestone_completion = []
    for milestone in milestones:
        milestone_items = [item for item in release_items if item.get("milestone_id") == milestone["id"]]
        complete_count = sum(1 for item in milestone_items if is_complete(item))
        total = len(milestone_items)
        milestone_completion.append(
            {
                "milestone_id": milestone["id"],
                "complete_primary": complete_count,
                "primary_total": total,
                "completion_pct": pct(complete_count, total),
            }
        )

    complete_total = sum(1 for item in release_items if is_complete(item))
    primary_total = len(release_items)
    readiness_score = 0.0 if primary_total == 0 else round3(complete_total / primary_total)

    high_blockers = [
        blocker
        for blocker in data["blockers"]
        if blocker.get("release_id") == release_id and blocker_unresolved(blocker) and blocker_high_impact(blocker)
    ]
    cause_counts = Counter(blocker.get("cause") for blocker in high_blockers)
    blocker_cause_counts = {cause: cause_counts[cause] for cause in sorted(cause_counts)}

    high_blocked_noncomplete_ids = {
        blocker.get("work_item_id")
        for blocker in high_blockers
        if blocker.get("work_item_id") in release_item_ids and not is_complete(items_by_id[blocker.get("work_item_id")])
    }

    dependencies_by_blocked: dict[str, list[str]] = defaultdict(list)
    for dep in data["dependencies"]:
        blocked = dep.get("blocked_id")
        depends_on = dep.get("depends_on_id")
        if blocked and depends_on:
            dependencies_by_blocked[blocked].append(depends_on)

    chains = []
    for item in sorted([row for row in release_items if not is_complete(row)], key=lambda row: row["id"]):
        chains.extend(dependency_chains(item["id"], dependencies_by_blocked, items_by_id))
    unique_chains = sorted({tuple(chain) for chain in chains})
    critical_dependency_chains = [list(chain) for chain in unique_chains]

    dependency_gated_ids = {
        chain[0]
        for chain in critical_dependency_chains
        if chain[0] in release_item_ids and not is_complete(items_by_id[chain[0]])
    }
    gating_ids = sorted(high_blocked_noncomplete_ids | dependency_gated_ids)

    unresolved_any = [
        blocker
        for blocker in data["blockers"]
        if blocker.get("release_id") == release_id and blocker_unresolved(blocker)
    ]
    has_unresolved_critical = any(str(blocker.get("severity") or "").lower() == "critical" for blocker in unresolved_any)
    if gating_ids or critical_dependency_chains or has_unresolved_critical or readiness_score < 0.85:
        ship_decision = "NO_SHIP"
    elif unresolved_any or readiness_score < 1.0:
        ship_decision = "SHIP_WITH_WATCH"
    else:
        ship_decision = "SHIP"

    return {
        "release_id": release_id,
        "ship_decision": ship_decision,
        "milestone_completion": milestone_completion,
        "gating_work_item_ids": gating_ids,
        "blocker_cause_counts": blocker_cause_counts,
        "critical_dependency_chains": critical_dependency_chains,
        "readiness_score": readiness_score,
        "primary_total": primary_total,
        "complete_primary": complete_total,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default="environment_access.md", help="Path to environment_access.md")
    parser.add_argument("--base-url", help="Environment base URL; overrides --env-file")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("snapshot", help="Fetch and print all environment collections")

    portfolio_parser = subparsers.add_parser("portfolio", help="Compute portfolio mix summary")
    portfolio_parser.add_argument("--scope-id")
    portfolio_parser.add_argument("--quarter", required=True)
    portfolio_parser.add_argument("--teams", nargs="+", required=True)
    portfolio_parser.add_argument("--product-areas", nargs="+", required=True)
    portfolio_parser.add_argument("--target-scope-id")

    sla_parser = subparsers.add_parser("sla", help="Compute SLA aging summary")
    sla_parser.add_argument("--as-of", required=True)
    sla_parser.add_argument("--recent-closed-window-days", type=int, required=True)
    sla_parser.add_argument("--teams", nargs="+", required=True)
    sla_parser.add_argument("--categories", nargs="+", required=True)

    release_parser = subparsers.add_parser("release", help="Compute release readiness summary")
    release_parser.add_argument("--release-id", required=True)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    env_base_url, _token = parse_env_file(args.env_file)
    base_url = args.base_url or env_base_url
    if not base_url:
        parser.error("Provide --base-url or an environment access file with base_url")
    data = fetch_all(base_url)

    if args.command == "snapshot":
        result = data
    elif args.command == "portfolio":
        result = portfolio(args, data)
    elif args.command == "sla":
        result = sla(args, data)
    elif args.command == "release":
        result = release(args, data)
    else:
        parser.error(f"Unknown command {args.command}")
    print(json.dumps(result, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
