#!/usr/bin/env python3
"""
Portfolio-review environment query helper.

Provides GET and POST helpers for the shared task environment.
Import or run inline to fetch work items, mix targets, SLA policy,
releases, milestones, dependencies, and blockers.
"""

import json
import os
import sys
import urllib.request
import urllib.error

BASE_URL = os.environ.get("TASK_ENV_BASE_URL", "http://task-env:9024")
TOKEN = os.environ.get("X_ENV_TOKEN", "portfolio-readonly")


def _request(method, path, body=None):
    """Low-level HTTP request with optional JSON body."""
    url = f"{BASE_URL}{path}"
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if method == "POST" and path == "/api/query":
        req.add_header("X-Env-Token", TOKEN)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        raise RuntimeError(f"HTTP {e.code} {method} {path}: {body}") from None


def get_work_items():
    """Return all work items from GET /api/work-items."""
    return _request("GET", "/api/work-items")


def get_work_item(item_id):
    """Return a single work item by id."""
    return _request("GET", f"/api/work-items/{item_id}")


def get_mix_targets():
    """Return all mix target rows."""
    return _request("GET", "/api/mix-targets")


def get_sla_policy():
    """Return the SLA policy document."""
    return _request("GET", "/api/sla-policy")


def get_releases():
    """Return all releases."""
    return _request("GET", "/api/releases")


def get_release(release_id):
    """Return a single release by id."""
    return _request("GET", f"/api/releases/{release_id}")


def get_milestones():
    """Return all milestones."""
    return _request("GET", "/api/milestones")


def get_dependencies():
    """Return all dependency records."""
    return _request("GET", "/api/dependencies")


def get_blockers():
    """Return all blocker records."""
    return _request("GET", "/api/blockers")


def query(sql, params=None):
    """POST /api/query with a read-only SQL statement and positional params."""
    return _request("POST", "/api/query", {"sql": sql, "params": params or []})


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("work-items")
    sub.add_parser("mix-targets")
    sub.add_parser("sla-policy")
    sub.add_parser("releases")
    sub.add_parser("milestones")
    sub.add_parser("dependencies")
    sub.add_parser("blockers")

    sql_parser = sub.add_parser("query")
    sql_parser.add_argument("sql")
    sql_parser.add_argument("params", nargs="*")

    args = parser.parse_args()

    if args.cmd == "work-items":
        print(json.dumps(get_work_items(), indent=2))
    elif args.cmd == "mix-targets":
        print(json.dumps(get_mix_targets(), indent=2))
    elif args.cmd == "sla-policy":
        print(json.dumps(get_sla_policy(), indent=2))
    elif args.cmd == "releases":
        print(json.dumps(get_releases(), indent=2))
    elif args.cmd == "milestones":
        print(json.dumps(get_milestones(), indent=2))
    elif args.cmd == "dependencies":
        print(json.dumps(get_dependencies(), indent=2))
    elif args.cmd == "blockers":
        print(json.dumps(get_blockers(), indent=2))
    elif args.cmd == "query":
        result = query(args.sql, list(args.params))
        print(json.dumps(result, indent=2))
    else:
        parser.print_help()
