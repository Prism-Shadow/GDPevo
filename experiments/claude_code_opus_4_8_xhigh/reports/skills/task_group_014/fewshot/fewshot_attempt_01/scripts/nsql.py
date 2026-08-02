#!/usr/bin/env python3
"""Run a read-only SQL query against the Northstar payer-operations environment.

The environment exposes POST /sql/query which accepts only SELECT / WITH /
PRAGMA table_info statements and returns {"columns", "rows", "row_count", ...}.

Usage:
    python3 nsql.py "SELECT * FROM cases WHERE case_id='CASE-X'"
    python3 nsql.py --base http://task-env:9014 --token pa-review-token-014 "PRAGMA table_info(cases)"

Base URL resolution:  --base  >  $GDPEVO_ENV_BASE_URL
Token resolution:     --token >  $NS_TOKEN  >  $GDPEVO_SQL_TOKEN
(Read base URL and bearer token from the task's task_context.json /
environment_access.md; nothing is hard-coded.)

Prints the rows as pretty JSON (or the full response with --raw).
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("sql", help="A SELECT / WITH / PRAGMA table_info statement")
    ap.add_argument("--base", default=os.environ.get("GDPEVO_ENV_BASE_URL", ""),
                    help="Environment base URL (default: $GDPEVO_ENV_BASE_URL)")
    ap.add_argument("--token", default=os.environ.get("NS_TOKEN")
                    or os.environ.get("GDPEVO_SQL_TOKEN", ""),
                    help="Bearer token (default: $NS_TOKEN or $GDPEVO_SQL_TOKEN)")
    ap.add_argument("--raw", action="store_true",
                    help="Print the full JSON response instead of just rows")
    ap.add_argument("--timeout", type=float, default=30.0)
    args = ap.parse_args()

    if not args.base:
        print("error: no base URL (pass --base or set GDPEVO_ENV_BASE_URL)",
              file=sys.stderr)
        return 2
    url = args.base.rstrip("/") + "/sql/query"
    body = json.dumps({"sql": args.sql}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if args.token:
        req.add_header("Authorization", "Bearer " + args.token)

    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        print(f"HTTP {e.code}: {detail}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"connection error: {e.reason}", file=sys.stderr)
        return 1

    if args.raw or "rows" not in payload:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        if payload.get("limited"):
            print(f"# WARNING: results truncated at max_rows="
                  f"{payload.get('max_rows')} — add a tighter WHERE filter",
                  file=sys.stderr)
        print(json.dumps(payload["rows"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
