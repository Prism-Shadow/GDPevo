#!/usr/bin/env python3
"""Run a read-only SQL query against the task environment portfolio database.

Usage:
    python query_portfolio.py <sql_file.sql>
    echo "SELECT ..." | python query_portfolio.py --stdin

Reads environment_access.md from the workspace for the base URL and token.
"""

import json
import os
import sys
import urllib.request
from pathlib import Path


def find_env_access():
    for root in ["/work", "."]:
        p = Path(root) / "environment_access.md"
        if p.exists():
            return p
    for p in Path("/work").rglob("environment_access.md"):
        return p
    raise FileNotFoundError("environment_access.md not found in workspace")


def parse_env_access(path):
    text = path.read_text()
    base_url = None
    token = None
    for line in text.splitlines():
        if base_url is None:
            import re
            m = re.search(r'https?://[^\s\n]+', line)
            if m:
                base_url = m.group(0).rstrip("/")
        if token is None and "X-Env-Token:" in line:
            import re
            m = re.search(r'X-Env-Token:\s*(\S+)', line)
            if m:
                token = m.group(1)
    if not base_url:
        raise ValueError("Could not find base URL in environment_access.md")
    if not token:
        raise ValueError("Could not find X-Env-Token in environment_access.md")
    return base_url, token


def main():
    sql = ""
    if "--stdin" in sys.argv or len(sys.argv) == 1:
        sql = sys.stdin.read().strip()
    else:
        sql_file = Path(sys.argv[1])
        if not sql_file.exists():
            print(f"ERROR: file not found: {sql_file}", file=sys.stderr)
            sys.exit(1)
        sql = sql_file.read_text().strip()

    if not sql:
        print("ERROR: empty SQL query", file=sys.stderr)
        sys.exit(1)

    env_path = find_env_access()
    base_url, token = parse_env_access(env_path)

    url = f"{base_url}/api/query"
    body = json.dumps({"sql": sql, "params": []}).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Env-Token": token,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            json.dump(result, sys.stdout, indent=2)
            sys.stdout.write("\n")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
