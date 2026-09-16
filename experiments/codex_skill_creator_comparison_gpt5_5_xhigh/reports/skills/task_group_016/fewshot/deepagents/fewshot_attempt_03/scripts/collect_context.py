#!/usr/bin/env python3
"""Fetch a synthetic clinic case bundle and matching protocol.

This helper uses only stdlib HTTP and performs read-only GET requests.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request


PROTOCOL_BY_CASE_TYPE = {
    "acute_respiratory": "RESP-CAP-2026",
    "pediatric_head_injury": "PEDS-HEAD-2026",
    "potassium_repletion": "K-REPLETION-2026",
    "care_management": "CM-HIGH-RISK-2026",
    "observation_window": "OBS-WINDOW-2026",
}


def get_json(base_url: str, path: str) -> object:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"GET {url} failed: HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"GET {url} failed: {exc.reason}") from exc


def case_type_from_bundle(bundle: object) -> str | None:
    if not isinstance(bundle, dict):
        return None
    case = bundle.get("case")
    if isinstance(case, dict):
        case_type = case.get("case_type")
        if isinstance(case_type, str):
            return case_type
    case_type = bundle.get("case_type")
    return case_type if isinstance(case_type, str) else None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch a case bundle and matching protocol from the clinic runtime."
    )
    parser.add_argument("--base-url", required=True, help="Runtime base URL")
    parser.add_argument("--case-id", required=True, help="Target case identifier")
    parser.add_argument(
        "--protocol-id",
        help="Override protocol id when the case type mapping is insufficient",
    )
    args = parser.parse_args()

    bundle = get_json(args.base_url, f"/api/cases/{args.case_id}")
    protocol_id = args.protocol_id
    if not protocol_id:
        case_type = case_type_from_bundle(bundle)
        protocol_id = PROTOCOL_BY_CASE_TYPE.get(case_type or "")

    protocol = None
    if protocol_id:
        protocol = get_json(args.base_url, f"/api/protocols/{protocol_id}")

    print(
        json.dumps(
            {
                "case_id": args.case_id,
                "protocol_id": protocol_id,
                "case_bundle": bundle,
                "protocol": protocol,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
