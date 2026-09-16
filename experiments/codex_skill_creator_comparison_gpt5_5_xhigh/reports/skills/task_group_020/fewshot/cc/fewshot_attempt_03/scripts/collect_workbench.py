#!/usr/bin/env python3
"""Collect deal-workbench API records for one M&A task.

The script is intentionally generic: pass the base URL and current deal ID from
the task prompt. It writes one JSON file containing successful responses and
HTTP errors so the solver can reason from all available sources.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
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


def fetch_json(base_url: str, path: str) -> dict[str, Any]:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
            if not raw.strip():
                return {"ok": True, "url": url, "data": None}
            return {"ok": True, "url": url, "data": json.loads(raw)}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "url": url, "status": exc.code, "error": body[:2000]}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"ok": False, "url": url, "error": str(exc)}


def find_ids(obj: Any, suffix: str) -> list[str]:
    found: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_lower = key.lower()
            if key_lower.endswith(suffix) and isinstance(value, str):
                found.append(value)
            else:
                found.extend(find_ids(value, suffix))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(find_ids(item, suffix))
    return sorted(set(found))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Task environment base URL")
    parser.add_argument("--deal-id", required=True, help="Current deal ID")
    parser.add_argument("--playbook-id", help="Applicable playbook ID, if known")
    parser.add_argument("--policy-id", help="Applicable policy ID, if known")
    parser.add_argument("--out", default="workbench_sources.json", help="Output JSON path")
    args = parser.parse_args()

    sources: dict[str, Any] = {
        "deal_id": args.deal_id,
        "deal": fetch_json(args.base_url, f"/api/deals/{args.deal_id}"),
        "deal_endpoints": {},
        "playbook_rules": {},
        "policy_thresholds": {},
    }

    for endpoint in DEAL_ENDPOINTS:
        sources["deal_endpoints"][endpoint] = fetch_json(
            args.base_url, f"/api/deals/{args.deal_id}/{endpoint}"
        )

    deal_data = sources["deal"].get("data") if sources["deal"].get("ok") else None
    playbook_ids = set([args.playbook_id] if args.playbook_id else [])
    policy_ids = set([args.policy_id] if args.policy_id else [])
    playbook_ids.update(find_ids(deal_data, "playbook_id"))
    policy_ids.update(find_ids(deal_data, "policy_id"))

    for playbook_id in sorted(playbook_ids):
        if playbook_id:
            sources["playbook_rules"][playbook_id] = fetch_json(
                args.base_url, f"/api/playbooks/{playbook_id}/rules"
            )

    for policy_id in sorted(policy_ids):
        if policy_id:
            sources["policy_thresholds"][policy_id] = fetch_json(
                args.base_url, f"/api/policies/{policy_id}/thresholds"
            )

    output_path = Path(args.out)
    output_path.write_text(json.dumps(sources, indent=2, sort_keys=True) + "\n")
    print(str(output_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
