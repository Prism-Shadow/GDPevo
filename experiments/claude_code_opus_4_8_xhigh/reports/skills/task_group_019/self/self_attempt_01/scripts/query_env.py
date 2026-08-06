#!/usr/bin/env python3
"""Generic client for the shared licensing data service.

Reads the base URL and the X-Task-Token from an environment_access.md file
(the one staged alongside the task), then exposes two helpers:

    get(path)        -> parsed JSON for GET <base>/api/<path>
    sql(query, ...)  -> parsed JSON for POST <base>/api/sql  {"query": ...}

The SQL endpoint is SELECT-only, blocks PRAGMA / sqlite_master, and returns at
most `LIMIT` rows (default 200) per call, so pass explicit LIMIT/COUNT/WHERE.

No task-specific values are embedded here; everything comes from
environment_access.md at runtime.

CLI:
    python query_env.py get contractor/applications
    python query_env.py sql "SELECT COUNT(*) AS n FROM contractor_violations WHERE status='open'"
    python query_env.py env-file /path/to/environment_access.md get policies
"""
import json
import os
import re
import sys
import urllib.request

DEFAULT_ENV_FILES = [
    "environment_access.md",
    os.path.join("input", "environment_access.md"),
    "../environment_access.md",
    "../../environment_access.md",
]


def load_env(env_file=None):
    """Return (base_url, token) parsed from an environment_access.md file."""
    candidates = [env_file] if env_file else DEFAULT_ENV_FILES
    for path in candidates:
        if path and os.path.exists(path):
            text = open(path, encoding="utf-8").read()
            break
    else:
        raise FileNotFoundError(
            "environment_access.md not found; pass its path explicitly."
        )

    base = None
    m = re.search(r"GDPEVO_ENV_BASE_URL\s*=\s*(\S+)", text)
    if m:
        base = m.group(1)
    if not base:
        m = re.search(r"https?://\S+", text)
        base = m.group(0) if m else None
    if not base:
        raise ValueError("Could not find a base URL in the env file.")
    base = base.rstrip("/")

    token = None
    m = re.search(r"X-Task-Token\s*:?\s*(\S+)", text)
    if m:
        token = m.group(1)
    return base, token


def get(path, env_file=None):
    base, _ = load_env(env_file)
    url = base + "/api/" + path.lstrip("/").removeprefix("api/")
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp)


def sql(query, env_file=None):
    base, token = load_env(env_file)
    if not token:
        raise PermissionError(
            "No X-Task-Token in the env file; /api/sql is unavailable."
        )
    body = json.dumps({"query": query}).encode("utf-8")
    req = urllib.request.Request(
        base + "/api/sql",
        data=body,
        headers={"Content-Type": "application/json", "X-Task-Token": token},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def _main(argv):
    env_file = None
    if len(argv) >= 3 and argv[0] == "env-file":
        env_file = argv[1]
        argv = argv[2:]
    if not argv:
        print(__doc__)
        return 1
    cmd, rest = argv[0], argv[1:]
    if cmd == "get":
        print(json.dumps(get(rest[0], env_file), indent=2))
    elif cmd == "sql":
        print(json.dumps(sql(rest[0], env_file), indent=2))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
