#!/usr/bin/env python3
"""Fetch standard M&A workbench records for one deal using only stdlib."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


DEAL_ENDPOINTS = [
    "terms",
    "documents",
    "benchmarks",
    "risk-estimates",
    "cap-table",
    "consents",
    "employees",
    "material-contracts",
    "regulatory",
    "diligence-findings",
    "notes",
]


def read_base_from_environment_access() -> str | None:
    path = Path("environment_access.md")
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("base_url:"):
            return line.split(":", 1)[1].strip()
    return None


def normalize_base_url(value: str) -> str:
    return value.rstrip("/") + "/"


def get_json(base_url: str, path: str) -> tuple[Any | None, str | None]:
    url = urljoin(base_url, path.lstrip("/"))
    req = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode("utf-8")), None
    except HTTPError as exc:
        return None, f"HTTP {exc.code} for {path}"
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        return None, f"{type(exc).__name__}: {exc}"


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deal-id", required=True, help="Exact deal ID, for example PRJ_...")
    parser.add_argument("--base-url", default=None, help="Workbench base URL")
    parser.add_argument("--out", default=None, help="Output directory")
    parser.add_argument("--playbook-id", default=None, help="Optional playbook ID override")
    parser.add_argument("--policy-id", default=None, help="Optional policy ID override")
    args = parser.parse_args()

    base_url = (
        args.base_url
        or os.environ.get("TASK_ENV_BASE_URL")
        or os.environ.get("WORKBENCH_BASE_URL")
        or read_base_from_environment_access()
        or "http://task-env:9020/"
    )
    base_url = normalize_base_url(base_url)

    out_dir = Path(args.out or f"/tmp/workbench-{args.deal_id}")
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "base_url": base_url,
        "deal_id": args.deal_id,
        "files": {},
        "errors": {},
    }

    deal_data, error = get_json(base_url, f"/api/deals/{args.deal_id}")
    if error:
        manifest["errors"]["deal"] = error
        write_json(out_dir / "manifest.json", manifest)
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return 1

    write_json(out_dir / "deal.json", deal_data)
    manifest["files"]["deal"] = str(out_dir / "deal.json")

    deal_record = deal_data.get("deal", deal_data) if isinstance(deal_data, dict) else {}
    playbook_id = args.playbook_id or deal_record.get("playbook_id")
    policy_id = args.policy_id or deal_record.get("policy_id")

    for endpoint in DEAL_ENDPOINTS:
        data, error = get_json(base_url, f"/api/deals/{args.deal_id}/{endpoint}")
        key = endpoint.replace("-", "_")
        if error:
            manifest["errors"][key] = error
            continue
        filename = out_dir / f"{key}.json"
        write_json(filename, data)
        manifest["files"][key] = str(filename)

    if playbook_id:
        data, error = get_json(base_url, f"/api/playbooks/{playbook_id}/rules")
        if error:
            manifest["errors"]["playbook_rules"] = error
        else:
            filename = out_dir / "playbook_rules.json"
            write_json(filename, data)
            manifest["files"]["playbook_rules"] = str(filename)
            manifest["playbook_id"] = playbook_id

    if policy_id:
        data, error = get_json(base_url, f"/api/policies/{policy_id}/thresholds")
        if error:
            manifest["errors"]["policy_thresholds"] = error
        else:
            filename = out_dir / "policy_thresholds.json"
            write_json(filename, data)
            manifest["files"]["policy_thresholds"] = str(filename)
            manifest["policy_id"] = policy_id

    write_json(out_dir / "manifest.json", manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0 if not manifest["errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
