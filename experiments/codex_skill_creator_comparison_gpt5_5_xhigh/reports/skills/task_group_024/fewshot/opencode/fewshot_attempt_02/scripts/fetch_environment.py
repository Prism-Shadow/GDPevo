#!/usr/bin/env python3
"""Fetch standard task-environment REST collections for offline inspection."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin


ENDPOINTS = {
    "work_items": "/api/work-items",
    "mix_targets": "/api/mix-targets",
    "sla_policy": "/api/sla-policy",
    "releases": "/api/releases",
    "milestones": "/api/milestones",
    "dependencies": "/api/dependencies",
    "blockers": "/api/blockers",
}


def fetch_json(base_url: str, path: str, token: str | None) -> object:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    if token:
        request.add_header("X-Env-Token", token)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Task environment base URL")
    parser.add_argument("--out", required=True, help="Output directory for fetched JSON")
    parser.add_argument("--token", default=None, help="Optional X-Env-Token")
    parser.add_argument("--release-id", default=None, help="Optional release ID to fetch")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    failures: list[str] = []
    for name, endpoint in ENDPOINTS.items():
        try:
            write_json(out_dir / f"{name}.json", fetch_json(args.base_url, endpoint, args.token))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            failures.append(f"{endpoint}: {exc}")

    if args.release_id:
        endpoint = f"/api/releases/{args.release_id}"
        try:
            write_json(out_dir / "release_detail.json", fetch_json(args.base_url, endpoint, args.token))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            failures.append(f"{endpoint}: {exc}")

    if failures:
        for failure in failures:
            print(f"fetch failed: {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
