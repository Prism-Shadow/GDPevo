#!/usr/bin/env python3
"""Reusable calculations for the shared engineering portfolio environment."""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import sys
import urllib.error
import urllib.request


CATEGORY_ORDER = ["NewFeature", "TechDebt", "Reliability", "Security"]
COMPLETE_STATUSES = {"Closed", "Done", "Verified", "Deployed"}
EXCLUDED_STATUSES = {"Duplicate", "Cancelled"}
HIGH_IMPACT_BLOCKERS = {"High", "Critical"}
RESOLVED_BLOCKER_STATUSES = {"Resolved", "Closed", "Done"}
SEVERITY_RANK = {"S1": 1, "S2": 2, "S3": 3, "S4": 4}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--base-url", required=True, help="Task environment base URL")

    portfolio = subparsers.add_parser("portfolio", parents=[common])
    portfolio.add_argument("--quarter", required=True)
    portfolio.add_argument("--teams", required=True, help="Comma-separated team names")
    portfolio.add_argument("--product-areas", required=True, help="Comma-separated product areas")
    portfolio.add_argument("--scope-id", help="Mix-target scope_id")

    sla = subparsers.add_parser("sla", parents=[common])
    sla.add_argument("--teams", required=True, help="Comma-separated team names")
    sla.add_argument("--as-of", required=True, help="YYYY-MM-DD")
    sla.add_argument("--window-days", required=True, type=int)
    sla.add_argument("--categories", default="Reliability,Security")

    release = subparsers.add_parser("release", parents=[common])
    release.add_argument("--release-id", required=True)

    return parser.parse_args()


def split_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def parse_date(value: str | None) -> dt.date | None:
    if not value:
        return None
    return dt.date.fromisoformat(value)


def round1(value: float) -> float:
    return round(value + 0.0000000001, 1)


def round3(value: float) -> float:
    return round(value + 0.0000000001, 3)


def fetch_json(base_url: str, path: str) -> dict:
    url = base_url.rstrip("/") + path
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise SystemExit(f"Failed to fetch {url}: {exc}") from exc


def load_work_items(base_url: str) -> list[dict]:
    return fetch_json(base_url, "/api/work-items").get("work_items", [])


def quarter_bounds(quarter: str) -> tuple[dt.date, dt.date]:
    year_text, quarter_text = quarter.split("-Q", 1)
    year = int(year_text)
    q_num = int(quarter_text)
    start_month = (q_num - 1) * 3 + 1
    start = dt.date(year, start_month, 1)
    if q_num == 4:
        end = dt.date(year, 12, 31)
    else:
        end = dt.date(year, start_month + 3, 1) - dt.timedelta(days=1)
    return start, end


def lower_text(item: dict) -> str:
    parts = [
        item.get("work_type") or "",
        item.get("title") or "",
        item.get("product_area") or "",
        item.get("team") or "",
        " ".join(item.get("labels") or []),
    ]
    return " ".join(parts).lower()


def signal_text(item: dict) -> str:
    parts = [
        item.get("work_type") or "",
        item.get("title") or "",
        " ".join(item.get("labels") or []),
    ]
    return " ".join(parts).lower()


def has_any(text: str, tokens: set[str]) -> bool:
    return any(token in text for token in tokens)


def portfolio_category(item: dict) -> str:
    work_type = (item.get("work_type") or "").strip()
    text = lower_text(item)

    strong_security_types = {"Security", "Compliance"}
    strong_reliability_types = {"Incident", "Reliability", "Bug"}
    tech_debt_types = {"Refactor", "Dependency", "Chore"}
    feature_like = work_type in {"Feature", "Enhancement"} or has_any(text, {"feature", "rollout"})

    if work_type in strong_security_types or has_any(
        text,
        {"security", "cve", "compliance", "appsec"},
    ):
        return "Security"

    if work_type in strong_reliability_types or has_any(
        text,
        {"reliability", "incident", "outage", "latency", "flaky"},
    ):
        return "Reliability"

    if (
        work_type in tech_debt_types
        or has_any(text, {"refactor", "dependency", "deprecate"})
        or (has_any(text, {"cleanup", "migration"}) and not feature_like)
    ):
        return "TechDebt"

    if has_any(text, {"identity", "auth", "encryption", "consent"}):
        return "Security"

    if feature_like:
        return "NewFeature"

    return "TechDebt"


def sla_category(item: dict) -> str | None:
    work_type = (item.get("work_type") or "").strip()
    text = signal_text(item)

    if work_type in {"Security", "Compliance"} or has_any(
        text,
        {"security", "cve", "compliance", "auth", "encryption"},
    ):
        return "Security"

    if work_type in {"Incident", "Reliability", "Bug"} or has_any(
        text,
        {"reliability", "incident", "outage", "latency", "flaky"},
    ):
        return "Reliability"

    return None


def is_primary(item: dict) -> bool:
    return item.get("status") not in EXCLUDED_STATUSES and not item.get("duplicate_of")


def is_complete(item: dict) -> bool:
    return item.get("status") in COMPLETE_STATUSES


def portfolio(base_url: str, quarter: str, teams: list[str], product_areas: list[str], scope_id: str | None) -> dict:
    work_items = load_work_items(base_url)
    start, end = quarter_bounds(quarter)
    team_set = set(teams)
    area_set = set(product_areas)

    scoped = []
    for item in work_items:
        closed_at = parse_date(item.get("closed_at"))
        if not closed_at or not (start <= closed_at <= end):
            continue
        if item.get("team") not in team_set or item.get("product_area") not in area_set:
            continue
        scoped.append(item)

    included = [item for item in scoped if is_primary(item)]
    included.sort(key=lambda item: (item.get("closed_at") or "", item.get("id") or ""))

    counts = {category: 0 for category in CATEGORY_ORDER}
    by_category_team: dict[str, collections.Counter] = {
        category: collections.Counter() for category in CATEGORY_ORDER
    }
    for item in included:
        category = portfolio_category(item)
        counts[category] += 1
        by_category_team[category][item.get("team") or ""] += 1

    total = len(included)
    actual = {
        category: round1((counts[category] / total * 100.0) if total else 0.0)
        for category in CATEGORY_ORDER
    }

    target = None
    if scope_id:
        for row in fetch_json(base_url, "/api/mix-targets").get("mix_targets", []):
            if row.get("scope_id") == scope_id:
                target = row
                break

    target_pct = {}
    if target:
        target_pct = {
            "NewFeature": round1(float(target.get("new_feature_pct", 0.0)) * 100.0),
            "TechDebt": round1(float(target.get("tech_debt_pct", 0.0)) * 100.0),
            "Reliability": round1(float(target.get("reliability_pct", 0.0)) * 100.0),
            "Security": round1(float(target.get("security_pct", 0.0)) * 100.0),
        }

    rows = []
    under = []
    for category in CATEGORY_ORDER:
        target_value = target_pct.get(category, 0.0)
        gap = round1(actual[category] - target_value)
        rows.append(
            {
                "category": category,
                "count": counts[category],
                "actual_pct": actual[category],
                "target_pct": target_value,
                "gap_pct": gap,
            }
        )
        if gap < 0:
            under.append((category, gap))
    under.sort(key=lambda pair: (pair[1], CATEGORY_ORDER.index(pair[0])))

    duplicate_ids = sorted(
        item.get("id") for item in scoped if item.get("status") == "Duplicate" or item.get("duplicate_of")
    )
    cancelled_ids = sorted(item.get("id") for item in scoped if item.get("status") == "Cancelled")
    distractor_ids = sorted(
        set(duplicate_ids + cancelled_ids),
        key=lambda item_id: next(
            ((item.get("closed_at") or "", item.get("id") or "") for item in scoped if item.get("id") == item_id),
            ("", item_id),
        ),
    )

    return {
        "scope": {
            "quarter": quarter,
            "teams": teams,
            "product_areas": product_areas,
            "target_scope_id": scope_id,
            "total_included": total,
        },
        "included_work_item_ids": [item.get("id") for item in included],
        "category_counts": counts,
        "category_percentages": actual,
        "mix_rows": rows,
        "under_invested_categories": [category for category, _gap in under],
        "largest_deficit_category": under[0][0] if under else None,
        "by_category_team": {
            category: dict(sorted(counter.items()))
            for category, counter in by_category_team.items()
            if counter
        },
        "excluded_duplicate_ids": duplicate_ids,
        "excluded_cancelled_ids": cancelled_ids,
        "excluded_distractor_ids": distractor_ids,
        "ignored_mirror_status_and_legacy_category": True,
    }


def sla_temporal_in_scope(item: dict, as_of: dt.date, window_days: int) -> bool:
    created_at = parse_date(item.get("created_at"))
    if not created_at or created_at > as_of:
        return False
    closed_at = parse_date(item.get("closed_at"))
    if closed_at:
        if closed_at > as_of:
            return False
        return (as_of - closed_at).days <= window_days
    return True


def item_age_days(item: dict, as_of: dt.date) -> int:
    created_at = parse_date(item.get("created_at"))
    closed_at = parse_date(item.get("closed_at"))
    end = closed_at if closed_at and closed_at <= as_of else as_of
    if not created_at:
        return 0
    return max((end - created_at).days, 0)


def overdue(item: dict, as_of: dt.date) -> bool:
    due_at = parse_date(item.get("due_at"))
    if not due_at:
        return False
    closed_at = parse_date(item.get("closed_at"))
    end = closed_at if closed_at and closed_at <= as_of else as_of
    return due_at < end


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


def late_days(item: dict, as_of: dt.date) -> int:
    due_at = parse_date(item.get("due_at"))
    if not due_at:
        return 0
    closed_at = parse_date(item.get("closed_at"))
    end = closed_at if closed_at and closed_at <= as_of else as_of
    return max((end - due_at).days, 0)


def build_duplicate_clusters(items: list[dict]) -> list[dict]:
    clusters: dict[str, list[str]] = collections.defaultdict(list)
    for item in items:
        primary_id = item.get("duplicate_of")
        if primary_id:
            clusters[primary_id].append(item.get("id"))
    return [
        {"primary_id": primary_id, "duplicate_ids": sorted(ids)}
        for primary_id, ids in sorted(clusters.items())
    ]


def sla(base_url: str, teams: list[str], as_of_text: str, window_days: int, categories: list[str]) -> dict:
    as_of = parse_date(as_of_text)
    if as_of is None:
        raise SystemExit("--as-of must be YYYY-MM-DD")

    team_set = set(teams)
    category_set = set(categories)
    scoped = []
    for item in load_work_items(base_url):
        if item.get("team") not in team_set:
            continue
        if not sla_temporal_in_scope(item, as_of, window_days):
            continue
        if item.get("status") == "Cancelled":
            continue
        if sla_category(item) not in category_set:
            continue
        scoped.append(item)

    primary = sorted([item for item in scoped if is_primary(item)], key=lambda item: item.get("id") or "")
    overdue_items = [item for item in primary if overdue(item, as_of)]
    overdue_sorted = sorted(overdue_items, key=lambda item: item.get("id") or "")

    bucket_counts = {bucket: 0 for bucket in ["0-3", "4-7", "8-14", "15-30", "31+"]}
    for item in primary:
        bucket_counts[age_bucket(item_age_days(item, as_of))] += 1

    team_counts = []
    for team in sorted(teams):
        team_counts.append(
            {
                "team": team,
                "overdue_count": sum(1 for item in overdue_items if item.get("team") == team),
            }
        )

    hotspot_counter: collections.Counter[tuple[str, str]] = collections.Counter()
    for item in overdue_items:
        owner = item.get("owner") or "UNASSIGNED"
        hotspot_counter[(item.get("team") or "", owner)] += 1
    if hotspot_counter:
        (team, owner), count = sorted(
            hotspot_counter.items(),
            key=lambda pair: (-pair[1], pair[0][0], pair[0][1]),
        )[0]
        top_hotspot = {"team": team, "owner": owner, "overdue_count": count}
    else:
        top_hotspot = {"team": None, "owner": None, "overdue_count": 0}

    severity_counts = {severity: 0 for severity in ["S1", "S2", "S3", "S4"]}
    for item in overdue_items:
        severity = item.get("severity")
        if severity in severity_counts:
            severity_counts[severity] += 1

    escalation = sorted(
        overdue_items,
        key=lambda item: (
            SEVERITY_RANK.get(item.get("severity"), 99),
            -late_days(item, as_of),
            int(item.get("priority") or 99),
            item.get("due_at") or "",
            item.get("id") or "",
        ),
    )

    return {
        "scope": {
            "teams": teams,
            "as_of": as_of_text,
            "recent_closed_window_days": window_days,
            "categories": categories,
        },
        "included_primary_ids": [item.get("id") for item in primary],
        "overdue_primary_ids": [item.get("id") for item in overdue_sorted],
        "aging_bucket_counts": bucket_counts,
        "team_overdue_counts": team_counts,
        "top_hotspot": top_hotspot,
        "overdue_counts_by_severity": severity_counts,
        "escalation_queue_ids": [item.get("id") for item in escalation],
        "missing_owner_ids": sorted(item.get("id") for item in primary if not item.get("owner")),
        "duplicate_clusters": build_duplicate_clusters([item for item in scoped if not is_primary(item)]),
        "breach_rate": round3(len(overdue_items) / len(primary)) if primary else 0.0,
        "sla_breach_rate": round3(len(overdue_items) / len(primary)) if primary else 0.0,
    }


def unresolved_blocker(blocker: dict) -> bool:
    if blocker.get("resolved_at"):
        return False
    return blocker.get("status") not in RESOLVED_BLOCKER_STATUSES


def release_readiness(base_url: str, release_id: str) -> dict:
    release_detail = fetch_json(base_url, f"/api/releases/{release_id}")
    milestones = release_detail.get("milestones") or [
        milestone
        for milestone in fetch_json(base_url, "/api/milestones").get("milestones", [])
        if milestone.get("release_id") == release_id
    ]
    blockers = release_detail.get("blockers") or [
        blocker
        for blocker in fetch_json(base_url, "/api/blockers").get("blockers", [])
        if blocker.get("release_id") == release_id
    ]
    dependencies = fetch_json(base_url, "/api/dependencies").get("dependencies", [])
    work_items = load_work_items(base_url)
    by_id = {item.get("id"): item for item in work_items}

    release_items = [
        item for item in work_items if item.get("release_id") == release_id and is_primary(item)
    ]
    release_items.sort(key=lambda item: item.get("id") or "")

    milestone_rows = []
    for milestone in sorted(milestones, key=lambda row: row.get("id") or ""):
        milestone_items = [
            item for item in release_items if item.get("milestone_id") == milestone.get("id")
        ]
        total = len(milestone_items)
        complete = sum(1 for item in milestone_items if is_complete(item))
        milestone_rows.append(
            {
                "milestone_id": milestone.get("id"),
                "complete_primary": complete,
                "primary_total": total,
                "completion_pct": round1((complete / total * 100.0) if total else 0.0),
            }
        )

    high_blockers = [
        blocker
        for blocker in blockers
        if unresolved_blocker(blocker) and blocker.get("severity") in HIGH_IMPACT_BLOCKERS
    ]
    cause_counts = dict(sorted(collections.Counter(blocker.get("cause") for blocker in high_blockers).items()))
    primary_release_ids = {item.get("id") for item in release_items}
    non_complete_release_ids = {
        item.get("id") for item in release_items if not is_complete(item)
    }
    gating_ids = sorted(
        {
            blocker.get("work_item_id")
            for blocker in high_blockers
            if blocker.get("work_item_id") in non_complete_release_ids
        }
    )

    dep_graph: dict[str, list[str]] = collections.defaultdict(list)
    for dependency in dependencies:
        dep_graph[dependency.get("blocked_id")].append(dependency.get("depends_on_id"))
    for values in dep_graph.values():
        values.sort()

    chains = []
    for start_id in sorted(non_complete_release_ids):
        stack = [(start_id, [start_id])]
        while stack:
            current_id, path = stack.pop()
            for next_id in dep_graph.get(current_id, []):
                if not next_id or next_id in path:
                    continue
                next_item = by_id.get(next_id)
                if next_item and (next_item.get("status") in EXCLUDED_STATUSES or next_item.get("duplicate_of")):
                    continue
                next_path = path + [next_id]
                if next_item and not is_complete(next_item):
                    chains.append(next_path)
                elif next_item:
                    stack.append((next_id, next_path))

    unique_chains = sorted({tuple(chain) for chain in chains})
    complete_count = sum(1 for item in release_items if is_complete(item))
    total = len(release_items)
    readiness_score = round3(complete_count / total) if total else 0.0

    unresolved_lower = [
        blocker
        for blocker in blockers
        if unresolved_blocker(blocker) and blocker.get("severity") not in HIGH_IMPACT_BLOCKERS
    ]
    if gating_ids or unique_chains:
        decision = "NO_SHIP"
    elif unresolved_lower or readiness_score < 1.0:
        decision = "SHIP_WITH_WATCH"
    else:
        decision = "SHIP"

    return {
        "release_id": release_id,
        "ship_decision": decision,
        "milestone_completion": milestone_rows,
        "gating_work_item_ids": gating_ids,
        "blocker_cause_counts": cause_counts,
        "critical_dependency_chains": [list(chain) for chain in unique_chains],
        "readiness_score": readiness_score,
        "primary_release_work_item_ids": [item.get("id") for item in release_items],
        "non_complete_primary_release_ids": sorted(non_complete_release_ids),
        "unresolved_lower_impact_blocker_ids": sorted(
            blocker.get("id") for blocker in unresolved_lower if blocker.get("id")
        ),
    }


def main() -> None:
    args = parse_args()
    if args.command == "portfolio":
        result = portfolio(
            args.base_url,
            args.quarter,
            split_csv(args.teams),
            split_csv(args.product_areas),
            args.scope_id,
        )
    elif args.command == "sla":
        result = sla(
            args.base_url,
            split_csv(args.teams),
            args.as_of,
            args.window_days,
            split_csv(args.categories),
        )
    else:
        result = release_readiness(args.base_url, args.release_id)

    json.dump(result, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
