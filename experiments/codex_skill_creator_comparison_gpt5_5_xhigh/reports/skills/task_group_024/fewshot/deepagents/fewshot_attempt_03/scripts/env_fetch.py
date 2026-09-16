#!/usr/bin/env python3
"""Fetch and normalize the engineering portfolio task environment.

The script intentionally uses only Python standard-library modules so it is
portable in restricted solver workspaces.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


COMPLETE_STATUSES = {"Closed", "Done", "Verified", "Deployed"}
NON_COMPLETE_STATUSES = {"Backlog", "In Progress", "Review", "Blocked", "Reopened"}
SEVERITY_ORDER = {"S1": 0, "S2": 1, "S3": 2, "S4": 3}
CATEGORY_ORDER = ["NewFeature", "TechDebt", "Reliability", "Security"]


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def round_pct(value: float, digits: int = 1) -> float:
    return round(value + 0.0, digits)


def quarter_bounds(quarter: str) -> tuple[date, date]:
    year_text, q_text = quarter.split("-Q", 1)
    year = int(year_text)
    q = int(q_text)
    starts = {1: (1, 1), 2: (4, 1), 3: (7, 1), 4: (10, 1)}
    ends = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}
    if q not in starts:
        raise ValueError(f"Invalid quarter: {quarter}")
    sm, sd = starts[q]
    em, ed = ends[q]
    return date(year, sm, sd), date(year, em, ed)


def is_duplicate(item: dict[str, Any]) -> bool:
    return item.get("status") == "Duplicate" or item.get("duplicate_of") is not None


def is_cancelled(item: dict[str, Any]) -> bool:
    return item.get("status") == "Cancelled"


def is_primary(item: dict[str, Any]) -> bool:
    return not is_duplicate(item) and not is_cancelled(item)


def is_complete(item: dict[str, Any]) -> bool:
    return item.get("status") in COMPLETE_STATUSES


def text_blob(item: dict[str, Any]) -> str:
    labels = " ".join(str(x) for x in item.get("labels") or [])
    parts = [str(item.get("work_type") or ""), labels, str(item.get("title") or "")]
    return " ".join(parts).lower()


def classify_portfolio_category(item: dict[str, Any]) -> str:
    """Classify one work item into the four portfolio categories."""

    work_type = str(item.get("work_type") or "").lower()
    labels = {str(x).lower() for x in item.get("labels") or []}
    blob = text_blob(item)

    strong_security = {"security", "cve", "encryption", "compliance"}
    reliability = {"reliability", "incident", "outage", "latency", "flaky"}
    tech_debt = {"refactor", "cleanup", "migration", "dependency"}
    feature = {"feature", "rollout", "experiment", "launch", "customer-request"}

    has_strong_security = (
        work_type in {"security", "compliance"}
        or any(term in labels for term in strong_security)
        or any(term in blob for term in strong_security)
    )
    has_reliability = (
        work_type in {"reliability", "incident"}
        or (work_type == "bug" and any(term in blob for term in reliability))
        or any(term in labels for term in reliability)
        or any(term in blob for term in reliability)
    )
    has_tech_debt = (
        work_type in {"refactor", "chore", "dependency"}
        or any(term in labels for term in tech_debt)
        or any(term in blob for term in tech_debt)
    )
    weak_auth_security = "auth" in labels or " auth " in f" {blob} "
    has_feature = (
        work_type in {"feature", "enhancement"}
        or any(term in labels for term in feature)
        or any(term in blob for term in feature)
    )

    if has_strong_security:
        return "Security"
    if has_reliability:
        return "Reliability"
    if has_tech_debt:
        return "TechDebt"
    if weak_auth_security:
        return "Security"
    if has_feature:
        return "NewFeature"

    legacy = str(item.get("legacy_category") or "").lower()
    if legacy in {"security"}:
        return "Security"
    if legacy in {"quality", "bug", "incident"}:
        return "Reliability"
    if legacy in {"maintenance", "tech-debt", "admin"}:
        return "TechDebt"
    if legacy in {"new", "feature"}:
        return "NewFeature"
    return "NewFeature"


def age_bucket(age_days: int) -> str:
    if age_days <= 3:
        return "0-3"
    if age_days <= 7:
        return "4-7"
    if age_days <= 14:
        return "8-14"
    if age_days <= 30:
        return "15-30"
    return "31+"


def item_age_bucket(item: dict[str, Any], as_of: date) -> str:
    created = parse_date(item.get("created_at"))
    if created is None:
        raise ValueError(f"Missing created_at for {item.get('id')}")
    closed = parse_date(item.get("closed_at"))
    end = min(closed, as_of) if closed else as_of
    return age_bucket((end - created).days)


def is_overdue(item: dict[str, Any], as_of: date) -> bool:
    due = parse_date(item.get("due_at"))
    if due is None:
        return False
    closed = parse_date(item.get("closed_at"))
    if closed:
        return closed > due
    return due < as_of


def recent_window_start(as_of: date, days: int) -> date:
    return as_of - timedelta(days=days)


def fetch_json(base_url: str, path: str) -> Any:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=20) as response:
        return json.load(response)


def fetch_item(base_url: str, item_id: str) -> dict[str, Any]:
    data = fetch_json(base_url, f"/api/work-items/{item_id}")
    return data.get("work_item", data)


def fetch_endpoint(base_url: str, path: str) -> Any:
    try:
        return fetch_json(base_url, path)
    except HTTPError as exc:
        return {"error": exc.code, "path": path, "reason": exc.reason}


def fetch_environment(base_url: str) -> dict[str, Any]:
    return {
        "work_items": fetch_endpoint(base_url, "/api/work-items"),
        "mix_targets": fetch_endpoint(base_url, "/api/mix-targets"),
        "sla_policy": fetch_endpoint(base_url, "/api/sla-policy"),
        "releases": fetch_endpoint(base_url, "/api/releases"),
        "milestones": fetch_endpoint(base_url, "/api/milestones"),
        "dependencies": fetch_endpoint(base_url, "/api/dependencies"),
        "blockers": fetch_endpoint(base_url, "/api/blockers"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Task environment base URL")
    parser.add_argument("--out", help="Write JSON output to this file")
    parser.add_argument("--ids", nargs="*", help="Fetch only these work item IDs")
    args = parser.parse_args()

    if args.ids:
        payload = {"work_items": [fetch_item(args.base_url, item_id) for item_id in args.ids]}
    else:
        payload = fetch_environment(args.base_url)

    text = json.dumps(payload, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n")
    else:
        print(text)


if __name__ == "__main__":
    main()
