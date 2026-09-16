#!/usr/bin/env python3
"""Fetch a JSON context bundle for one M&A deal workbench matter."""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone


DEAL_ENDPOINTS = [
    ("deal", "/api/deals/{deal_id}"),
    ("terms", "/api/deals/{deal_id}/terms"),
    ("documents", "/api/deals/{deal_id}/documents"),
    ("benchmarks", "/api/deals/{deal_id}/benchmarks"),
    ("risk_estimates", "/api/deals/{deal_id}/risk-estimates"),
    ("cap_table", "/api/deals/{deal_id}/cap-table"),
    ("consents", "/api/deals/{deal_id}/consents"),
    ("employees", "/api/deals/{deal_id}/employees"),
    ("material_contracts", "/api/deals/{deal_id}/material-contracts"),
    ("regulatory", "/api/deals/{deal_id}/regulatory"),
    ("diligence_findings", "/api/deals/{deal_id}/diligence-findings"),
    ("notes", "/api/deals/{deal_id}/notes"),
]


def build_url(base_url, path):
    return urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def get_json(base_url, path, timeout):
    url = build_url(base_url, path)
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {"_missing": True, "_status": 404, "_path": path}
        raise
    return json.loads(body)


def nested_deal(payload):
    if not isinstance(payload, dict):
        return {}
    deal = payload.get("deal")
    return deal if isinstance(deal, dict) else payload


def main():
    parser = argparse.ArgumentParser(
        description="Fetch standard deal workbench API records for one explicit deal id."
    )
    parser.add_argument("--base-url", default=os.environ.get("TASK_ENV_BASE_URL"))
    parser.add_argument("--deal-id", required=True)
    parser.add_argument("--playbook-id", default=None)
    parser.add_argument("--policy-id", default=None)
    parser.add_argument("--output", default="-")
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    if not args.base_url:
        print("Provide --base-url or set TASK_ENV_BASE_URL.", file=sys.stderr)
        return 2

    deal_id = urllib.parse.quote(args.deal_id, safe="")
    bundle = {
        "deal_id": args.deal_id,
        "base_url": args.base_url,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "responses": {},
    }

    for key, path_template in DEAL_ENDPOINTS:
        path = path_template.format(deal_id=deal_id)
        bundle["responses"][key] = get_json(args.base_url, path, args.timeout)

    deal = nested_deal(bundle["responses"].get("deal", {}))
    playbook_id = args.playbook_id or deal.get("playbook_id")
    policy_id = args.policy_id or deal.get("policy_id")

    if playbook_id:
        playbook_path = "/api/playbooks/{}/rules".format(
            urllib.parse.quote(str(playbook_id), safe="")
        )
        bundle["responses"]["playbook_rules"] = get_json(
            args.base_url, playbook_path, args.timeout
        )

    if policy_id:
        policy_path = "/api/policies/{}/thresholds".format(
            urllib.parse.quote(str(policy_id), safe="")
        )
        bundle["responses"]["policy_thresholds"] = get_json(
            args.base_url, policy_path, args.timeout
        )

    text = json.dumps(bundle, indent=2, sort_keys=True)
    if args.output == "-":
        print(text)
    else:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
