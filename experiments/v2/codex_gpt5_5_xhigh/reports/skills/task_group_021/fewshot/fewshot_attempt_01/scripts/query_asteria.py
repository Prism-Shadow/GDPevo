#!/usr/bin/env python3
"""Run read-only SQL against an Asteria task environment.

Usage:
  python skill/scripts/query_asteria.py /path/to/environment_access.md \
    'select * from v_source_snapshots limit 5'
  python skill/scripts/query_asteria.py /path/to/environment_access.md \
    --objects 'select * from v_source_snapshots limit 5'
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


def read_access(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    base_match = re.search(r"^GDPEVO_ENV_BASE_URL=(\S+)\s*$", text, re.M)
    token_match = re.search(r"Authorization header:\s*Bearer\s+(\S+)", text)
    if not base_match or not token_match:
        raise SystemExit(f"Could not parse base URL and bearer token from {path}")
    return base_match.group(1).rstrip("/"), token_match.group(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("environment_access", type=Path)
    parser.add_argument("query")
    parser.add_argument("--objects", action="store_true", help="emit rows as objects")
    args = parser.parse_args()

    base_url, token = read_access(args.environment_access)
    payload = json.dumps({"query": args.query}).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/api/query",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code}: {detail}") from exc

    if args.objects and {"columns", "rows"} <= set(data):
        columns = data["columns"]
        data = {
            "row_count": data.get("row_count"),
            "rows": [dict(zip(columns, row)) for row in data["rows"]],
            "truncated": data.get("truncated"),
        }
    json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
