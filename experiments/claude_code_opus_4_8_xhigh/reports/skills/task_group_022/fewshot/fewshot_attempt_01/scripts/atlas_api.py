#!/usr/bin/env python3
"""Thin, dependency-free client for the Atlas Commerce Operations workplace API.

The base URL and bearer token are read from an `environment_access.md` file
(the one shipped with the task). Nothing about any specific task, table, or
answer is hard-coded here: this is a transport helper only. Discover the actual
schema and field semantics at run time via the `schema` and `dict` commands.

Usage:
  atlas_api.py schema                 # GET /api/schema (table/column structure)
  atlas_api.py dict                   # GET /api/data-dictionary (field semantics)
  atlas_api.py sql "SELECT ..."       # POST /api/sql  (read-only analysis)
  atlas_api.py sql -                  # read the SQL from stdin
  atlas_api.py audit k=v [k=v ...]    # GET /api/correction-audit with query params
  atlas_api.py tx path/to/body.json   # POST /api/sql/transaction (body from file)
  atlas_api.py tx -                   # POST /api/sql/transaction (body from stdin)

Environment file is located by (in order):
  1. $ATLAS_ENV_FILE if set
  2. ./environment_access.md, then walking up parent directories.

Request-body rules learned from the live service (keep them in mind):
  * POST /api/sql accepts EXACTLY {"sql": "<one statement>"}. Any extra key
    (e.g. "limit") is rejected with {"error":"invalid request"}.
  * Auth is mandatory; missing/blank token -> 401 {"error":"unauthorized"}.
  * A read query that references a table/column the validator does not know
    returns {"error":"query rejected"}. That usually means a name typo or that
    you have not consulted /api/schema yet -- it is NOT a transport failure.
  * The /api/sql/transaction body shape is defined by /api/data-dictionary for
    the specific task; this helper passes your JSON through unchanged so you
    control it exactly.

Exit status is non-zero when the HTTP layer errors or the JSON payload contains
an {"error": ...} field, so it composes in shell pipelines.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def find_env_file():
    override = os.environ.get("ATLAS_ENV_FILE")
    if override:
        return override
    d = os.getcwd()
    while True:
        cand = os.path.join(d, "environment_access.md")
        if os.path.isfile(cand):
            return cand
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    raise SystemExit(
        "environment_access.md not found; set $ATLAS_ENV_FILE to its path."
    )


def load_env():
    """Parse base URL and bearer token from environment_access.md."""
    path = find_env_file()
    base = token = None
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            s = line.strip()
            low = s.lower()
            if low.startswith("base url"):
                base = s.split(":", 1)[1].strip()
            elif low.startswith("authorization"):
                val = s.split(":", 1)[1].strip()
                token = val[len("bearer"):].strip() if low.split(":", 1)[1].strip().lower().startswith("bearer") else val
    if not base or not token:
        raise SystemExit(f"Could not parse Base URL / Authorization from {path}")
    return base.rstrip("/"), token


def _request(method, url, token, body=None):
    data = None
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            status = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        status = e.code
    except urllib.error.URLError as e:
        raise SystemExit(f"network error contacting {url}: {e}")
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        print(raw)
        raise SystemExit(f"non-JSON response (HTTP {status}) from {url}")
    print(json.dumps(payload, indent=2))
    if status >= 400 or (isinstance(payload, dict) and "error" in payload):
        sys.exit(2)
    return payload


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    cmd, rest = argv[0], argv[1:]
    base, token = load_env()

    if cmd == "schema":
        _request("GET", f"{base}/api/schema", token)
    elif cmd in ("dict", "data-dictionary"):
        _request("GET", f"{base}/api/data-dictionary", token)
    elif cmd == "sql":
        if not rest:
            raise SystemExit('usage: atlas_api.py sql "<SELECT ...>" | sql -')
        sql = sys.stdin.read() if rest[0] == "-" else rest[0]
        _request("POST", f"{base}/api/sql", token, body={"sql": sql.strip()})
    elif cmd == "audit":
        qs = {}
        for kv in rest:
            if "=" not in kv:
                raise SystemExit(f"audit params must be key=value, got: {kv}")
            k, v = kv.split("=", 1)
            qs[k] = v
        url = f"{base}/api/correction-audit"
        if qs:
            url += "?" + urllib.parse.urlencode(qs)
        _request("GET", url, token)
    elif cmd == "tx":
        if not rest:
            raise SystemExit("usage: atlas_api.py tx <body.json> | tx -")
        raw = sys.stdin.read() if rest[0] == "-" else open(rest[0], encoding="utf-8").read()
        try:
            body = json.loads(raw)
        except json.JSONDecodeError as e:
            raise SystemExit(f"transaction body is not valid JSON: {e}")
        _request("POST", f"{base}/api/sql/transaction", token, body=body)
    else:
        raise SystemExit(f"unknown command: {cmd}\n{__doc__}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
