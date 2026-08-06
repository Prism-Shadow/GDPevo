#!/usr/bin/env python3
"""Minimal read-only client for the portfolio environment.

Reads the base URL and query token from an environment_access.md file (never hardcode
them). Use it to GET a resource or run a read-only SQL SELECT against POST /api/query.

    python3 query.py --env /path/to/environment_access.md get /api/work-items
    python3 query.py --env /path/to/environment_access.md sql "SELECT team, COUNT(*) FROM work_items GROUP BY team"

Prints JSON to stdout. Optional and unopinionated: plain curl/requests work equally well.
"""
import argparse
import json
import re
import sys
import urllib.request


def parse_env(path):
    """Extract base URL and X-Env-Token from environment_access.md."""
    text = open(path, encoding="utf-8").read()
    base = re.search(r"Base URL:\s*(\S+)", text)
    token = re.search(r"X-Env-Token:\s*(\S+)", text)
    if not base:
        sys.exit("could not find 'Base URL:' in " + path)
    return base.group(1).rstrip("/"), (token.group(1) if token else None)


def get(base, path):
    with urllib.request.urlopen(base + path, timeout=15) as r:
        return json.load(r)


def sql(base, token, statement):
    if not token:
        sys.exit("POST /api/query needs a token, but none was found in environment_access.md")
    body = json.dumps({"sql": statement}).encode()
    req = urllib.request.Request(
        base + "/api/query",
        data=body,
        headers={"X-Env-Token": token, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", default="environment_access.md",
                    help="path to environment_access.md (default: ./environment_access.md)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("get"); g.add_argument("path")
    s = sub.add_parser("sql"); s.add_argument("statement")
    args = ap.parse_args()

    base, token = parse_env(args.env)
    if args.cmd == "get":
        out = get(base, args.path)
    else:
        out = sql(base, token, args.statement)
    json.dump(out, sys.stdout, indent=2, sort_keys=True)
    print()


if __name__ == "__main__":
    main()
