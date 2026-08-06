#!/usr/bin/env python3
"""Fetch allowed M&A deal workbench records for one deal ID."""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request


DEAL_ENDPOINTS = [
    "",
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


def read_access(path):
    data = {}
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            match = re.match(r"^([A-Z0-9_]+)=(.*)$", line.strip())
            if match:
                data[match.group(1)] = match.group(2)
    base_url = data.get("GDPEVO_ENV_BASE_URL")
    token = data.get("QUERY_TOKEN")
    if not base_url:
        raise SystemExit(f"Missing GDPEVO_ENV_BASE_URL in {path}")
    return base_url.rstrip("/"), token


def request_json(url, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


def post_query(base_url, token, sql):
    body = json.dumps({"token": token, "sql": sql}).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/api/query",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


def maybe_id(record, key):
    if isinstance(record, dict):
        return record.get(key)
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("deal_id")
    parser.add_argument("--env-file", default="environment_access.md")
    parser.add_argument("--playbook-id")
    parser.add_argument("--policy-id")
    parser.add_argument("--include-sql-schema", action="store_true")
    args = parser.parse_args()

    base_url, token = read_access(args.env_file)
    output = {"deal_id": args.deal_id, "records": {}, "errors": {}}

    for suffix in DEAL_ENDPOINTS:
        path = f"/api/deals/{args.deal_id}" + (f"/{suffix}" if suffix else "")
        key = "deal" if suffix == "" else suffix.replace("-", "_")
        try:
            output["records"][key] = request_json(f"{base_url}{path}", token)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            output["errors"][key] = str(exc)

    deal_record = output["records"].get("deal", {}).get("deal", {})
    playbook_id = args.playbook_id or maybe_id(deal_record, "playbook_id")
    policy_id = args.policy_id or maybe_id(deal_record, "policy_id")

    if playbook_id:
        try:
            output["records"]["playbook_rules"] = request_json(
                f"{base_url}/api/playbooks/{playbook_id}/rules", token
            )
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            output["errors"]["playbook_rules"] = str(exc)

    if policy_id:
        try:
            output["records"]["policy_thresholds"] = request_json(
                f"{base_url}/api/policies/{policy_id}/thresholds", token
            )
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            output["errors"]["policy_thresholds"] = str(exc)

    if args.include_sql_schema:
        if not token:
            output["errors"]["sql_schema"] = "No QUERY_TOKEN in environment access file"
        else:
            sql = "select name from sqlite_master where type='table' order by name"
            try:
                output["records"]["sql_schema"] = post_query(base_url, token, sql)
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
                output["errors"]["sql_schema"] = str(exc)

    json.dump(output, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
