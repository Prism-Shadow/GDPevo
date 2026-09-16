#!/usr/bin/env python3
"""Fetch a synthetic clinic case bundle and related protocol metadata."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request


CASE_TYPE_PROTOCOL = {
    "acute_respiratory": "RESP-CAP-2026",
    "pediatric_head_injury": "PEDS-HEAD-2026",
    "potassium_repletion": "K-REPLETION-2026",
    "care_management": "CM-HIGH-RISK-2026",
    "observation_window": "OBS-WINDOW-2026",
}


def get_json(base_url: str, path: str) -> object:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return json.loads(response.read().decode(charset))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} for {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach {url}: {exc.reason}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Task environment base URL")
    parser.add_argument("--case-id", required=True, help="Target case identifier")
    parser.add_argument(
        "--all-protocols",
        action="store_true",
        help="Fetch every listed protocol instead of only the case-type protocol",
    )
    args = parser.parse_args()

    bundle = get_json(args.base_url, f"/api/cases/{args.case_id}")
    protocols_index = get_json(args.base_url, "/api/protocols")

    case = bundle.get("case", {}) if isinstance(bundle, dict) else {}
    protocol_ids = []
    if args.all_protocols:
        items = protocols_index.get("items", []) if isinstance(protocols_index, dict) else []
        protocol_ids = [item["protocol_id"] for item in items if "protocol_id" in item]
    else:
        case_type = case.get("case_type")
        protocol_id = CASE_TYPE_PROTOCOL.get(case_type)
        if protocol_id:
            protocol_ids = [protocol_id]

    protocols = {
        protocol_id: get_json(args.base_url, f"/api/protocols/{protocol_id}")
        for protocol_id in protocol_ids
    }

    output = {
        "case_bundle": bundle,
        "protocols_index": protocols_index,
        "protocols": protocols,
    }
    json.dump(output, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
