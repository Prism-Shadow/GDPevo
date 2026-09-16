#!/usr/bin/env python3
"""Collect case-scoped clinic runtime context for protocol JSON tasks."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


CASE_TYPE_PROTOCOL_HINTS = {
    "acute_respiratory": ["respiratory", "cap"],
    "pediatric_head_injury": ["head", "injury"],
    "potassium_repletion": ["potassium"],
    "observation_window": ["observation", "window"],
    "care_management": ["care", "management"],
}


def read_base_url(path: Path) -> str:
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("base_url:"):
            return line.split(":", 1)[1].strip()
    raise SystemExit(f"Could not find base_url in {path}")


def get_json(base_url: str, endpoint: str) -> object:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", endpoint.lstrip("/"))
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} for {url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Failed to fetch {url}: {exc}") from exc
    return json.loads(data)


def protocol_matches(case_type: str, item: dict) -> bool:
    haystack = " ".join(
        str(item.get(key, "")) for key in ("protocol_id", "title", "version")
    ).lower()
    hints = CASE_TYPE_PROTOCOL_HINTS.get(case_type, [])
    return all(hint in haystack for hint in hints[:1]) or any(
        hint in haystack for hint in hints
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--base-url")
    parser.add_argument(
        "--environment-access",
        default="environment_access.md",
        help="Path to environment_access.md when --base-url is omitted.",
    )
    parser.add_argument(
        "--protocol-id",
        action="append",
        default=[],
        help="Protocol id to fetch. May be repeated. If omitted, infer from case type.",
    )
    parser.add_argument("--output", help="Write JSON here instead of stdout.")
    args = parser.parse_args()

    base_url = args.base_url or read_base_url(Path(args.environment_access))
    case_bundle = get_json(base_url, f"/api/cases/{args.case_id}")
    case = case_bundle.get("case", {}) if isinstance(case_bundle, dict) else {}
    case_type = str(case.get("case_type", ""))

    protocols_index = get_json(base_url, "/api/protocols")
    protocol_items = (
        protocols_index.get("items", [])
        if isinstance(protocols_index, dict)
        else []
    )

    protocol_ids = list(args.protocol_id)
    if not protocol_ids:
        protocol_ids = [
            item["protocol_id"]
            for item in protocol_items
            if isinstance(item, dict)
            and item.get("protocol_id")
            and protocol_matches(case_type, item)
        ]

    protocol_details = [
        get_json(base_url, f"/api/protocols/{protocol_id}")
        for protocol_id in dict.fromkeys(protocol_ids)
    ]

    result = {
        "case_id": args.case_id,
        "case_type": case_type,
        "case_bundle": case_bundle,
        "protocols": protocol_details,
    }
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
