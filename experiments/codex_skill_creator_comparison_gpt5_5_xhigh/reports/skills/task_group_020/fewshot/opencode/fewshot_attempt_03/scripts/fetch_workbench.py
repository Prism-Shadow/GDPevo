#!/usr/bin/env python3
"""Fetch the standard M&A deal workbench records for one deal ID."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


STANDARD_ENDPOINTS = {
    "terms": "/api/deals/{deal_id}/terms",
    "documents": "/api/deals/{deal_id}/documents",
    "benchmarks": "/api/deals/{deal_id}/benchmarks",
    "risk_estimates": "/api/deals/{deal_id}/risk-estimates",
    "cap_table": "/api/deals/{deal_id}/cap-table",
    "consents": "/api/deals/{deal_id}/consents",
    "employees": "/api/deals/{deal_id}/employees",
    "material_contracts": "/api/deals/{deal_id}/material-contracts",
    "regulatory": "/api/deals/{deal_id}/regulatory",
    "diligence_findings": "/api/deals/{deal_id}/diligence-findings",
    "notes": "/api/deals/{deal_id}/notes",
}


def normalize_base_url(base_url: str) -> str:
    base_url = base_url.strip()
    if not base_url:
        raise ValueError("base URL is empty")
    return base_url if base_url.endswith("/") else base_url + "/"


def get_json(base_url: str, path: str) -> object:
    url = urllib.parse.urljoin(base_url, path.lstrip("/"))
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=20) as response:
        data = response.read().decode("utf-8")
    return json.loads(data)


def fetch_bundle(base_url: str, deal_id: str) -> dict:
    base_url = normalize_base_url(base_url)
    bundle: dict = {
        "deal_id": deal_id,
        "base_url": base_url,
        "errors": [],
    }

    deal_payload = get_json(base_url, f"/api/deals/{deal_id}")
    if isinstance(deal_payload, dict) and "deal" in deal_payload:
        deal = deal_payload["deal"]
    else:
        deal = deal_payload
    bundle["deal"] = deal

    for name, path_template in STANDARD_ENDPOINTS.items():
        path = path_template.format(deal_id=urllib.parse.quote(deal_id, safe=""))
        try:
            bundle[name] = get_json(base_url, path)
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
            bundle["errors"].append({"endpoint": name, "error": str(exc)})

    if isinstance(deal, dict):
        playbook_id = deal.get("playbook_id")
        policy_id = deal.get("policy_id")
        if playbook_id:
            try:
                quoted = urllib.parse.quote(str(playbook_id), safe="")
                bundle["playbook_rules"] = get_json(base_url, f"/api/playbooks/{quoted}/rules")
            except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
                bundle["errors"].append({"endpoint": "playbook_rules", "error": str(exc)})
        if policy_id:
            try:
                quoted = urllib.parse.quote(str(policy_id), safe="")
                bundle["policy_thresholds"] = get_json(base_url, f"/api/policies/{quoted}/thresholds")
            except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
                bundle["errors"].append({"endpoint": "policy_thresholds", "error": str(exc)})

    return bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("deal_id", help="Deal ID to fetch, for example PRJ_EXAMPLE")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("TASK_ENV_BASE_URL", "http://task-env:9020/"),
        help="Task environment base URL",
    )
    parser.add_argument("--output", help="Optional file path for the JSON bundle")
    args = parser.parse_args()

    try:
        bundle = fetch_bundle(args.base_url, args.deal_id)
    except Exception as exc:  # noqa: BLE001 - command-line helper should report any fatal fetch error.
        print(f"fetch_workbench.py: {exc}", file=sys.stderr)
        return 1

    text = json.dumps(bundle, indent=2, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.write("\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
