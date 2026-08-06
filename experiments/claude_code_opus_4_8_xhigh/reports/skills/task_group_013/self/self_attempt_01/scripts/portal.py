#!/usr/bin/env python3
"""Thin, decision-free client for the Cedar Ridge Intake Coordination Portal.

Resolves the base URL from environment_access.md (or GDPEVO_ENV_BASE_URL) and
wraps GET requests and the read-only POST /query SQL endpoint. It contains no
task logic and returns raw JSON — the decision rules live in the skill, not here.

Usage:
    python portal.py health
    python portal.py get /referrals --params batch_id=ORTHO-JUN-01 limit=100
    python portal.py get /referrals/REF0001
    python portal.py get /chart/P001
    python portal.py sql "SELECT * FROM intake_rosters WHERE roster_id='NPI-JUN-01'"

Base URL resolution order:
    1) --base-url CLI flag
    2) $GDPEVO_ENV_BASE_URL
    3) GDPEVO_ENV_BASE_URL=... line in ./environment_access.md or ../environment_access.md
"""
import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request


def resolve_base_url(cli_base=None):
    if cli_base:
        return cli_base.rstrip("/")
    env = os.environ.get("GDPEVO_ENV_BASE_URL")
    if env:
        return env.rstrip("/")
    for path in ("environment_access.md", "../environment_access.md",
                 "../../environment_access.md"):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                m = re.search(r"GDPEVO_ENV_BASE_URL\s*=\s*(\S+)", fh.read())
                if m:
                    return m.group(1).rstrip("/")
        except OSError:
            continue
    raise SystemExit("Could not resolve base URL: pass --base-url or set "
                     "GDPEVO_ENV_BASE_URL / provide environment_access.md")


def _request(url, data=None, timeout=15):
    headers = {"Accept": "application/json"}
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers,
                                 method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def do_get(base, path, params):
    q = ""
    if params:
        pairs = dict(p.split("=", 1) for p in params)
        q = "?" + urllib.parse.urlencode(pairs)
    if not path.startswith("/"):
        path = "/" + path
    return _request(base + path + q)


def do_sql(base, sql):
    return _request(base + "/query", data={"sql": sql})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("health")
    g = sub.add_parser("get")
    g.add_argument("path")
    g.add_argument("--params", nargs="*", default=[], help="key=value pairs")
    s = sub.add_parser("sql")
    s.add_argument("statement")
    args = ap.parse_args(argv)

    base = resolve_base_url(args.base_url)
    if args.cmd == "health":
        out = do_get(base, "/health", [])
    elif args.cmd == "get":
        out = do_get(base, args.path, args.params)
    elif args.cmd == "sql":
        out = do_sql(base, args.statement)
    else:  # pragma: no cover
        ap.error("unknown command")
    json.dump(out, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
