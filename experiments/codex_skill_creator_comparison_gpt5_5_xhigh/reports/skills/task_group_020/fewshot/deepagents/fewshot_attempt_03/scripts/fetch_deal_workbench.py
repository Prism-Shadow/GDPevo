#!/usr/bin/env python3
"""Fetch scoped M&A deal workbench records for JSON-answer tasks."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


DEAL_ENDPOINTS = [
    "terms",
    "documents",
    "benchmarks",
    "risk-estimates",
    "cap-table",
    "consents",
    "employees",
    "material-contracts",
    "regulatory",
    "diligence-findings",
    "notes",
]


def _get_json(base_url: str, path: str) -> tuple[int, Any]:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
            if not body:
                return response.status, None
            return response.status, json.loads(body)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return exc.code, None
        raise


def _derive_id(record: Any, candidates: list[str]) -> str | None:
    if not isinstance(record, dict):
        return None
    for key in candidates:
        value = record.get(key)
        if isinstance(value, str) and value:
            return value
    for value in record.values():
        if isinstance(value, dict):
            found = _derive_id(value, candidates)
            if found:
                return found
    return None


def fetch_bundle(
    base_url: str,
    deal_id: str,
    playbook_id: str | None,
    policy_id: str | None,
    include_empty: bool,
) -> dict[str, Any]:
    status, deal = _get_json(base_url, f"/api/deals/{deal_id}")
    if status != 200 or deal is None:
        raise RuntimeError(f"deal not found or unavailable: {deal_id}")

    bundle: dict[str, Any] = {"deal_id": deal_id, "deal": deal, "deal_endpoints": {}}

    for endpoint in DEAL_ENDPOINTS:
        status, data = _get_json(base_url, f"/api/deals/{deal_id}/{endpoint}")
        if status == 200 or include_empty:
            bundle["deal_endpoints"][endpoint] = data

    chosen_playbook = playbook_id or _derive_id(
        deal,
        [
            "playbook_id",
            "buyer_playbook_id",
            "seller_playbook_id",
            "applicable_playbook_id",
        ],
    )
    chosen_policy = policy_id or _derive_id(
        deal,
        ["policy_id", "committee_policy_id", "applicable_policy_id"],
    )

    if chosen_playbook:
        status, data = _get_json(base_url, f"/api/playbooks/{chosen_playbook}/rules")
        if status == 200 or include_empty:
            bundle["playbook_id"] = chosen_playbook
            bundle["playbook_rules"] = data

    if chosen_policy:
        status, data = _get_json(base_url, f"/api/policies/{chosen_policy}/thresholds")
        if status == 200 or include_empty:
            bundle["policy_id"] = chosen_policy
            bundle["policy_thresholds"] = data

    return bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Task environment base URL")
    parser.add_argument("--deal-id", required=True, help="Workbench deal ID")
    parser.add_argument("--playbook-id", help="Optional playbook ID to fetch")
    parser.add_argument("--policy-id", help="Optional policy ID to fetch")
    parser.add_argument(
        "--include-empty",
        action="store_true",
        help="Include endpoints that return 404 or empty records",
    )
    args = parser.parse_args()

    try:
        bundle = fetch_bundle(
            args.base_url,
            args.deal_id,
            args.playbook_id,
            args.policy_id,
            args.include_empty,
        )
    except Exception as exc:  # pragma: no cover - CLI error path
        print(f"error: {exc}", file=sys.stderr)
        return 1

    json.dump(bundle, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
