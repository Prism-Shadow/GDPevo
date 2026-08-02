#!/usr/bin/env python3
"""Thin client for the Cedar Ridge Intake Coordination Portal (task environment).

Reads the base URL from an ``environment_access.md`` file (the one shipped with
each task) and talks to the read-only portal. No third-party dependencies.

Usage:
    # Run a read-only SELECT through POST /query
    python3 portal.py sql "SELECT * FROM referrals WHERE batch_id='ORTHO-JUN-01' ORDER BY referral_id"

    # GET any allowed endpoint (leading slash optional)
    python3 portal.py get /referrals?batch_id=ORTHO-JUN-01
    python3 portal.py get /chart/P026
    python3 portal.py get /icd/S83.512A

    # List the tables / show the schema of one table
    python3 portal.py tables
    python3 portal.py schema referrals

Options:
    --env PATH   Path to environment_access.md (default: search ., .., ../..).
    --base URL   Override the base URL entirely.
    --raw        Print the raw JSON envelope instead of just the rows (sql only).

Everything is read-only. The portal only accepts SELECT statements on POST /query.
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

DEFAULT_ENV_NAMES = ["environment_access.md"]


def find_base_url(env_path=None, base_override=None):
    if base_override:
        return base_override.rstrip("/")
    candidates = []
    if env_path:
        candidates.append(env_path)
    else:
        for d in (".", "..", "../..", "../../.."):
            for name in DEFAULT_ENV_NAMES:
                candidates.append(os.path.join(d, name))
    for path in candidates:
        if path and os.path.exists(path):
            with open(path) as fh:
                for line in fh:
                    if "GDPEVO_ENV_BASE_URL" in line and "=" in line:
                        return line.split("=", 1)[1].strip().rstrip("/")
    sys.exit("Could not find GDPEVO_ENV_BASE_URL. Pass --env or --base.")


def _request(url, data=None, method="GET"):
    headers = {"Content-Type": "application/json"} if data is not None else {}
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        sys.exit(f"HTTP {e.code} for {url}\n{detail}")
    except urllib.error.URLError as e:
        sys.exit(f"Cannot reach {url}: {e}")


def run_sql(base, sql, raw=False):
    result = _request(f"{base}/query", data={"sql": sql}, method="POST")
    if raw or not isinstance(result, dict) or "rows" not in result:
        return result
    return result["rows"]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["sql", "get", "tables", "schema"])
    ap.add_argument("arg", nargs="?", default="")
    ap.add_argument("--env")
    ap.add_argument("--base")
    ap.add_argument("--raw", action="store_true")
    args = ap.parse_args()
    base = find_base_url(args.env, args.base)

    if args.command == "sql":
        if not args.arg:
            sys.exit("Provide a SELECT statement.")
        out = run_sql(base, args.arg, raw=args.raw)
    elif args.command == "get":
        path = args.arg if args.arg.startswith("/") else "/" + args.arg
        out = _request(f"{base}{path}")
    elif args.command == "tables":
        out = run_sql(base,
                      "SELECT name FROM sqlite_master WHERE type='table' "
                      "AND name NOT LIKE 'sqlite_%' ORDER BY name")
    elif args.command == "schema":
        if not args.arg:
            sys.exit("Provide a table name.")
        out = run_sql(base,
                      "SELECT sql FROM sqlite_master WHERE type='table' "
                      f"AND name='{args.arg}'")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
