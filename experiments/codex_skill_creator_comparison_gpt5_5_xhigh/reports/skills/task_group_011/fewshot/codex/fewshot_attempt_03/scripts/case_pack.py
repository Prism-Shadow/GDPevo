#!/usr/bin/env python3
"""Bundle the live credit-office API objects for a branch or segment case."""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Optional


def fetch_json(base_url: str, path: str):
    url = base_url.rstrip("/") + path
    with urllib.request.urlopen(url) as response:
        return json.load(response)


def benchmark_path(version: str) -> Optional[str]:
    if not version:
        return None
    if "_" not in version:
        return f"/api/benchmarks/{version}"
    namespace, rest = version.split("_", 1)
    return f"/api/benchmarks/{namespace}/{rest.replace('_', '-')}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch a compact credit-office case bundle.")
    parser.add_argument("--base-url", default=os.environ.get("TASK_ENV_BASE_URL", "http://task-env:9011"))
    parser.add_argument("--branch", help="Branch id to fetch")
    parser.add_argument("--segment", help="Credit-union segment id to fetch")
    parser.add_argument(
        "--application",
        action="append",
        default=[],
        help="Application id to keep in selected_applications; repeatable",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print the JSON bundle")
    args = parser.parse_args()

    if bool(args.branch) == bool(args.segment):
        parser.error("choose exactly one of --branch or --segment")

    try:
        bundle = {
            "manifest": fetch_json(args.base_url, "/api/manifest"),
            "policies": fetch_json(args.base_url, "/api/policies"),
        }

        if args.branch:
            branch = fetch_json(args.base_url, f"/api/branches/{args.branch}")
            bundle["branch"] = branch
            bundle["metrics"] = fetch_json(args.base_url, f"/api/branches/{args.branch}/metrics")
            bundle["loans"] = fetch_json(args.base_url, f"/api/branches/{args.branch}/loans")
            bundle["sector_exposures"] = fetch_json(args.base_url, f"/api/branches/{args.branch}/sector-exposures")
            applications = fetch_json(args.base_url, f"/api/branches/{args.branch}/applications")
            bundle["applications"] = applications

            if args.application:
                by_id = {item["application_id"]: item for item in applications}
                missing = [app_id for app_id in args.application if app_id not in by_id]
                if missing:
                    parser.error(f"application id(s) not found: {', '.join(missing)}")
                bundle["selected_applications"] = [by_id[app_id] for app_id in args.application]

            fdic_path = benchmark_path(branch.get("fdic_benchmark_set") or bundle["manifest"]["benchmark_versions"]["fdic"])
            if fdic_path:
                bundle["fdic_benchmark"] = fetch_json(args.base_url, fdic_path)

        else:
            bundle["segment"] = fetch_json(args.base_url, f"/api/credit-union-segments/{args.segment}")
            bundle["ncua_benchmark"] = fetch_json(args.base_url, "/api/benchmarks/ncua/q1-2025")
            if args.application:
                parser.error("--application is only valid with --branch")

        json.dump(bundle, sys.stdout, indent=2 if args.pretty else None, sort_keys=False)
        if args.pretty:
            sys.stdout.write("\n")
        return 0
    except urllib.error.HTTPError as exc:
        print(f"HTTP error fetching case data: {exc}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Network error fetching case data: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
