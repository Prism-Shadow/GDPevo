#!/usr/bin/env python3
"""Reusable client for GDPEVO licensing-review data services.

Reads connection details from an `environment_access.md` file (base URL, the
required auth header for POST /api/sql, and the allowed endpoint list), then
offers two helpers:

    get(path)   -> parsed JSON from a GET endpoint (list endpoints cap at 200!)
    sql(query)  -> rows from POST /api/sql (SQLite; use to bypass the 200 cap)

Nothing task-specific is hardcoded: the base URL, auth header, and token are
parsed from environment_access.md at runtime, so this works for any instance of
the family. Import it, or run it as a CLI:

    python3 licensing_client.py get /api/policies
    python3 licensing_client.py sql "SELECT * FROM contractor_bonds WHERE application_id IN ('C-...','C-...')"
"""
import json
import re
import sys
import urllib.request
from pathlib import Path


def find_env_file(start="."):
    """Locate environment_access.md by searching the cwd and parents."""
    p = Path(start).resolve()
    for base in [p, *p.parents]:
        cand = base / "environment_access.md"
        if cand.exists():
            return cand
    # last resort: common task locations
    for cand in (Path("/work/environment_access.md"), Path("environment_access.md")):
        if cand.exists():
            return cand.resolve()
    raise FileNotFoundError("environment_access.md not found")


def parse_env(env_path=None):
    """Return {base_url, header_name, header_value, endpoints[]} from the file."""
    text = Path(env_path or find_env_file()).read_text()
    base = re.search(r"BASE_URL\s*=\s*(\S+)", text)
    base_url = base.group(1).rstrip("/") if base else None
    # matches a line like: "requires header <Header-Name>: <token-value>"
    hdr = re.search(r"header\s+([A-Za-z0-9-]+)\s*:\s*(\S+)", text)
    header_name = hdr.group(1) if hdr else None
    header_value = hdr.group(2) if hdr else None
    endpoints = re.findall(r"(?:GET|POST)\s+(/\S+)", text)
    return {
        "base_url": base_url,
        "header_name": header_name,
        "header_value": header_value,
        "endpoints": endpoints,
    }


_ENV = None


def env():
    global _ENV
    if _ENV is None:
        _ENV = parse_env()
    return _ENV


def get(path):
    """GET a list/record endpoint. WARNING: list endpoints truncate at 200 rows.
    For anything that might exceed 200 (or when you need specific target IDs),
    use sql() with a WHERE filter instead."""
    e = env()
    url = e["base_url"] + (path if path.startswith("/") else "/" + path)
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.loads(r.read().decode())
    if isinstance(data, list) and len(data) == 200:
        sys.stderr.write(
            f"WARNING: GET {path} returned exactly 200 rows — likely truncated. "
            f"Use sql() to fetch the full set.\n"
        )
    return data


def sql(query):
    """POST /api/sql. Returns the list of row dicts. Default server LIMIT is 200;
    filter by your target IDs so results stay well under it, and check the raw
    'truncated' flag for large scans."""
    e = env()
    body = json.dumps({"query": query}).encode()
    req = urllib.request.Request(
        e["base_url"] + "/api/sql",
        data=body,
        headers={"Content-Type": "application/json", e["header_name"]: e["header_value"]},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.loads(r.read().decode())
    if payload.get("truncated"):
        sys.stderr.write("WARNING: SQL result truncated — tighten the filter or raise LIMIT.\n")
    return payload.get("rows", payload)


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "get":
        print(json.dumps(get(sys.argv[2]), indent=2))
    elif len(sys.argv) >= 3 and sys.argv[1] == "sql":
        print(json.dumps(sql(sys.argv[2]), indent=2))
    else:
        print(json.dumps(env(), indent=2))
