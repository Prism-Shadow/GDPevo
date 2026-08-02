#!/usr/bin/env python3
"""Thin client for the portfolio environment.

Reads the base URL and the POST /api/query auth token out of an
``environment_access.md`` file (whatever the running task provides) so no
endpoint or token is hard-coded here.

Usage
-----
    python3 portfolio_api.py [--access PATH] get /api/work-items
    python3 portfolio_api.py [--access PATH] get /api/releases/<release_id>
    python3 portfolio_api.py [--access PATH] sql "SELECT id, status FROM work_items LIMIT 5"

``--access`` defaults to ./environment_access.md, then ../environment_access.md.
Output is the raw JSON returned by the environment (pretty-printed).
"""
import argparse
import json
import os
import re
import sys
import urllib.request


def load_access(path=None):
    """Return (base_url, token) parsed from an environment_access.md file."""
    candidates = [path] if path else []
    candidates += ["environment_access.md", "../environment_access.md",
                   os.path.join(os.getcwd(), "environment_access.md")]
    for cand in candidates:
        if cand and os.path.exists(cand):
            text = open(cand, encoding="utf-8").read()
            base = re.search(r"Base URL:\s*(\S+)", text)
            token = re.search(r"X-Env-Token:\s*(\S+)", text)
            if not base:
                raise SystemExit(f"No 'Base URL:' found in {cand}")
            return base.group(1).rstrip("/"), (token.group(1) if token else None)
    raise SystemExit("environment_access.md not found; pass --access PATH")


def _request(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {},
                                 method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def do_get(base, token, path):
    return _request(base + "/" + path.lstrip("/"))


def do_sql(base, token, sql):
    if not token:
        raise SystemExit("POST /api/query needs a token but none was parsed.")
    body = json.dumps({"sql": sql}).encode("utf-8")
    headers = {"Content-Type": "application/json", "X-Env-Token": token}
    return _request(base + "/api/query", data=body, headers=headers)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--access", help="path to environment_access.md")
    ap.add_argument("mode", choices=["get", "sql"])
    ap.add_argument("target", help="endpoint path (get) or SQL string (sql)")
    args = ap.parse_args(argv)

    base, token = load_access(args.access)
    result = (do_get if args.mode == "get" else do_sql)(base, token, args.target)
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
