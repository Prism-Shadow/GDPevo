#!/usr/bin/env python3
"""Helper for the licensing-environment review task family.

Reads the base URL and (optional) SQL task token from an ``environment_access.md``
file, then fetches GET endpoints or runs read-only SQL against the shared
licensing data service. Pure standard library (urllib) -- no external deps.

The task specifies WHAT to decide; this script only removes boilerplate around
fetching and filtering records. All decision logic stays in the solver.

Usage:
  # Fetch and pretty-print an endpoint
  python licensing_env.py get /api/contractor/applications

  # Fetch, then keep only rows whose <field> is one of the comma-separated ids
  python licensing_env.py filter /api/contractor/applications application_id C-XXX-001,C-XXX-002

  # Run a read-only SELECT (needs the X-Task-Token from environment_access.md)
  python licensing_env.py sql "SELECT * FROM contractor_bonds WHERE application_id='C-XXX-001'"

  # Dump every allowed endpoint's row count (quick sanity check)
  python licensing_env.py survey

Environment-file discovery order (first match wins):
  1. --env <path>            (explicit flag)
  2. $ENVIRONMENT_ACCESS_MD  (env var)
  3. ./environment_access.md, ../environment_access.md, ../../environment_access.md
"""
import json
import os
import re
import sys
import urllib.request
import urllib.error

DEFAULT_ENV_CANDIDATES = [
    "environment_access.md",
    os.path.join("..", "environment_access.md"),
    os.path.join("..", "..", "environment_access.md"),
    os.path.join("..", "..", "..", "environment_access.md"),
]


def find_env_file(explicit=None):
    if explicit:
        return explicit
    if os.environ.get("ENVIRONMENT_ACCESS_MD"):
        return os.environ["ENVIRONMENT_ACCESS_MD"]
    for c in DEFAULT_ENV_CANDIDATES:
        if os.path.isfile(c):
            return c
    raise FileNotFoundError(
        "environment_access.md not found. Pass --env <path> or set ENVIRONMENT_ACCESS_MD."
    )


def parse_env(path):
    """Return (base_url, token). token may be None if no SQL access is granted."""
    text = open(path, "r", encoding="utf-8").read()
    base = None
    m = re.search(r"GDPEVO_ENV_BASE_URL\s*=\s*(\S+)", text)
    if m:
        base = m.group(1)
    if not base:
        m = re.search(r"https?://\S+", text)
        base = m.group(0) if m else None
    if not base:
        raise ValueError("Could not find a base URL in the environment file.")
    base = base.rstrip("/")

    token = None
    m = re.search(r"X-Task-Token\s*:\s*(\S+)", text)
    if m:
        token = m.group(1)
    return base, token


def http_get(base, endpoint):
    url = base + ("" if endpoint.startswith("/") else "/") + endpoint
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def http_sql(base, token, query):
    if not token:
        raise RuntimeError(
            "No X-Task-Token in environment file; SQL is not available for this task."
        )
    url = base + "/api/sql"
    body = json.dumps({"query": query}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "X-Task-Token": token},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


# Allowed endpoints as observed; the task's own prompt is authoritative -- only
# call endpoints the prompt lists. This list is just for `survey`.
KNOWN_GET_ENDPOINTS = [
    "/api/policies",
    "/api/contractor/applications",
    "/api/contractor/bonds",
    "/api/contractor/insurance",
    "/api/contractor/license-history",
    "/api/contractor/violations",
    "/api/contractor/correspondence",
    "/api/contractor/inspections",
    "/api/liquor/applications",
    "/api/liquor/settlements",
    "/api/liquor/privileges",
    "/api/liquor/incidents",
    "/api/liquor/site-evidence",
    "/api/alcohol/licensees",
    "/api/alcohol/violations",
    "/api/renewal/rules",
]


def main(argv):
    # Pull optional --env <path>
    env_path = None
    if "--env" in argv:
        i = argv.index("--env")
        env_path = argv[i + 1]
        del argv[i : i + 2]

    if not argv:
        print(__doc__)
        return 1

    cmd = argv[0]
    base, token = parse_env(find_env_file(env_path))

    if cmd == "get":
        data = http_get(base, argv[1])
        print(json.dumps(data, indent=2, sort_keys=True))
    elif cmd == "filter":
        endpoint, field, ids = argv[1], argv[2], argv[3].split(",")
        want = set(ids)
        data = http_get(base, endpoint)
        rows = [r for r in data if str(r.get(field)) in want]
        print(json.dumps(rows, indent=2, sort_keys=True))
    elif cmd == "sql":
        print(json.dumps(http_sql(base, token, argv[1]), indent=2, sort_keys=True))
    elif cmd == "survey":
        print("base_url:", base, "| sql_token:", "yes" if token else "no")
        for ep in KNOWN_GET_ENDPOINTS:
            try:
                d = http_get(base, ep)
                n = len(d) if isinstance(d, list) else "obj"
                print(f"  {ep:38s} -> {n}")
            except urllib.error.HTTPError as e:
                print(f"  {ep:38s} -> HTTP {e.code}")
            except Exception as e:  # noqa: BLE001
                print(f"  {ep:38s} -> {type(e).__name__}")
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
