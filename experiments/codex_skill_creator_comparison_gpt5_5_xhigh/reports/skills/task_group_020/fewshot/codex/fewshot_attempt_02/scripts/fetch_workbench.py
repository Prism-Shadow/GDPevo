#!/usr/bin/env python3
"""Fetch common M&A deal workbench records for a single deal.

The script intentionally performs only read-style collection. It does not infer
legal conclusions or bake in any deal-specific values.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


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


def make_url(base_url: str, path: str) -> str:
    return urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def fetch_json(base_url: str, path: str) -> tuple[Any | None, str | None]:
    request = Request(make_url(base_url, path), headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        return None, f"{path}: HTTP {exc.code}"
    except URLError as exc:
        return None, f"{path}: {exc.reason}"
    except TimeoutError:
        return None, f"{path}: request timed out"

    if not body.strip():
        return None, None
    try:
        return json.loads(body), None
    except json.JSONDecodeError as exc:
        return None, f"{path}: invalid JSON at byte {exc.pos}"


def collect_related_ids(value: Any, needle: str) -> list[str]:
    found: list[str] = []

    def walk(node: Any, key_hint: str = "") -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                walk(child, str(key).lower())
        elif isinstance(node, list):
            for child in node:
                walk(child, key_hint)
        elif isinstance(node, str):
            lowered = key_hint.lower()
            if needle in lowered and node not in found:
                found.append(node)

    walk(value)
    return found


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch common records from an M&A deal workbench."
    )
    parser.add_argument("base_url", help="Task environment base URL")
    parser.add_argument("deal_id", help="Deal ID from the prompt")
    parser.add_argument(
        "--playbook-id",
        action="append",
        default=[],
        help="Playbook ID to fetch rules for; repeat if needed",
    )
    parser.add_argument(
        "--policy-id",
        action="append",
        default=[],
        help="Policy ID to fetch thresholds for; repeat if needed",
    )
    parser.add_argument(
        "--no-infer-related",
        action="store_true",
        help="Do not infer playbook or policy IDs from the deal record",
    )
    parser.add_argument(
        "--output",
        help="Write JSON to this path instead of stdout",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result: dict[str, Any] = {
        "deal_id": args.deal_id,
        "records": {},
        "errors": [],
    }

    deal, error = fetch_json(args.base_url, f"/api/deals/{args.deal_id}")
    if error:
        result["errors"].append(error)
    result["records"]["deal"] = deal

    for endpoint in DEAL_ENDPOINTS:
        data, error = fetch_json(args.base_url, f"/api/deals/{args.deal_id}/{endpoint}")
        if error:
            result["errors"].append(error)
        result["records"][endpoint] = data

    playbook_ids = list(dict.fromkeys(args.playbook_id))
    policy_ids = list(dict.fromkeys(args.policy_id))
    if deal is not None and not args.no_infer_related:
        for item in collect_related_ids(deal, "playbook"):
            if item not in playbook_ids:
                playbook_ids.append(item)
        for item in collect_related_ids(deal, "policy"):
            if item not in policy_ids:
                policy_ids.append(item)

    playbooks, error = fetch_json(args.base_url, "/api/playbooks")
    if error:
        result["errors"].append(error)
    result["records"]["playbooks"] = playbooks

    policies, error = fetch_json(args.base_url, "/api/policies")
    if error:
        result["errors"].append(error)
    result["records"]["policies"] = policies

    result["records"]["playbook_rules"] = {}
    for playbook_id in playbook_ids:
        data, error = fetch_json(args.base_url, f"/api/playbooks/{playbook_id}/rules")
        if error:
            result["errors"].append(error)
        result["records"]["playbook_rules"][playbook_id] = data

    result["records"]["policy_thresholds"] = {}
    for policy_id in policy_ids:
        data, error = fetch_json(args.base_url, f"/api/policies/{policy_id}/thresholds")
        if error:
            result["errors"].append(error)
        result["records"]["policy_thresholds"][policy_id] = data

    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(rendered + "\n")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
