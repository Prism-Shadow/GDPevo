#!/usr/bin/env python3
"""Fetch a JSON snapshot from the portfolio task environment.

The script uses only documented GET endpoints and stdlib modules.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ENDPOINTS = {
    "work_items": "/api/work-items",
    "mix_targets": "/api/mix-targets",
    "sla_policy": "/api/sla-policy",
    "releases": "/api/releases",
    "milestones": "/api/milestones",
    "dependencies": "/api/dependencies",
    "blockers": "/api/blockers",
}


def fetch_json(base_url: str, path: str) -> Any:
    url = base_url.rstrip("/") + path
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{url} returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{url} failed: {exc.reason}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Task environment base URL")
    parser.add_argument("--out", required=True, help="Path to write snapshot JSON")
    args = parser.parse_args()

    snapshot = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "base_url": args.base_url.rstrip("/"),
        "endpoints": {},
    }

    for name, path in ENDPOINTS.items():
        snapshot["endpoints"][name] = fetch_json(args.base_url, path)

    out_path = Path(args.out)
    out_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n")

    counts = {}
    for name, payload in snapshot["endpoints"].items():
        if isinstance(payload, dict):
            for value in payload.values():
                if isinstance(value, list):
                    counts[name] = len(value)
                    break
    print(json.dumps({"out": str(out_path), "counts": counts}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
