#!/usr/bin/env python3
"""Fetch scoped licensing records from a task environment.

The script intentionally uses only documented GET endpoints and target
identifiers supplied by the caller. It prints grouped JSON for manual analysis.
"""

import argparse
import json
import os
import sys
from collections import OrderedDict
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen


def fetch_json(base_url: str, path: str, params: Optional[Dict[str, str]] = None) -> Any:
    base = base_url.rstrip("/") + "/"
    url = urljoin(base, path.lstrip("/"))
    if params:
        url = f"{url}?{urlencode(params)}"
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GET {url} failed: HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"GET {url} failed: {exc.reason}") from exc

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"GET {url} did not return JSON: {body[:200]}") from exc

    if isinstance(data, dict) and "error" in data:
        raise RuntimeError(f"GET {url} returned error: {data['error']}")
    if isinstance(data, str) and ("unknown filter" in data or "error" in data.lower()):
        raise RuntimeError(f"GET {url} returned error: {data}")
    return data


def as_list(value: Any) -> List[Dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def fetch_many(
    base_url: str, path: str, key: str, values: List[str]
) -> OrderedDict:
    grouped = OrderedDict()
    for value in values:
        grouped[value] = as_list(fetch_json(base_url, path, {key: value}))
    return grouped


def flatten(grouped: OrderedDict) -> List[Dict[str, Any]]:
    rows = []
    for records in grouped.values():
        rows.extend(records)
    return rows


def contractor_payload(base_url: str, ids: List[str]) -> Dict[str, Any]:
    applications_by_id = fetch_many(
        base_url, "/api/contractor/applications", "application_id", ids
    )
    applications = flatten(applications_by_id)
    prior_license_ids = sorted(
        {
            str(app["prior_license_id"])
            for app in applications
            if app.get("prior_license_id")
        }
    )

    return {
        "family": "contractor",
        "policies": fetch_json(base_url, "/api/policies"),
        "applications": applications_by_id,
        "bonds": fetch_many(base_url, "/api/contractor/bonds", "application_id", ids),
        "insurance": fetch_many(
            base_url, "/api/contractor/insurance", "application_id", ids
        ),
        "license_history": fetch_many(
            base_url,
            "/api/contractor/license-history",
            "license_id",
            prior_license_ids,
        ),
        "violations": fetch_many(
            base_url, "/api/contractor/violations", "related_application_id", ids
        ),
        "correspondence": fetch_many(
            base_url, "/api/contractor/correspondence", "related_application_id", ids
        ),
        "inspections": fetch_many(
            base_url, "/api/contractor/inspections", "related_application_id", ids
        ),
    }


def liquor_payload(base_url: str, ids: List[str]) -> Dict[str, Any]:
    applications_by_id = fetch_many(
        base_url, "/api/liquor/applications", "application_id", ids
    )
    applications = flatten(applications_by_id)
    location_ids = sorted(
        {str(app["location_id"]) for app in applications if app.get("location_id")}
    )
    license_classes = sorted(
        {str(app["license_class"]) for app in applications if app.get("license_class")}
    )

    return {
        "family": "liquor",
        "policies": fetch_json(base_url, "/api/policies"),
        "applications": applications_by_id,
        "settlements": fetch_many(
            base_url, "/api/liquor/settlements", "location_id", location_ids
        ),
        "privileges": fetch_many(
            base_url, "/api/liquor/privileges", "license_class", license_classes
        ),
        "incidents": fetch_many(
            base_url, "/api/liquor/incidents", "location_id", location_ids
        ),
        "site_evidence": fetch_many(
            base_url, "/api/liquor/site-evidence", "location_id", location_ids
        ),
    }


def renewal_payload(base_url: str, ids: List[str]) -> Dict[str, Any]:
    licensees_by_no = fetch_many(base_url, "/api/alcohol/licensees", "license_no", ids)
    licensees = flatten(licensees_by_no)
    successor_ids = sorted(
        {str(row["successor_to"]) for row in licensees if row.get("successor_to")}
    )

    return {
        "family": "renewal",
        "policies": fetch_json(base_url, "/api/policies"),
        "rules": fetch_json(base_url, "/api/renewal/rules"),
        "licensees": licensees_by_no,
        "violations": fetch_many(base_url, "/api/alcohol/violations", "license_no", ids),
        "successor_violations": fetch_many(
            base_url, "/api/alcohol/violations", "license_no", successor_ids
        ),
    }


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.environ.get("TASK_ENV_BASE_URL"),
        help="Task environment base URL. Defaults to TASK_ENV_BASE_URL.",
    )
    parser.add_argument(
        "--family", required=True, choices=["contractor", "liquor", "renewal"]
    )
    parser.add_argument("--ids", nargs="+", required=True, help="Target identifiers")
    parser.add_argument("--compact", action="store_true", help="Print compact JSON")
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    if not args.base_url:
        print("Provide --base-url or TASK_ENV_BASE_URL.", file=sys.stderr)
        return 2

    if args.family == "contractor":
        payload = contractor_payload(args.base_url, args.ids)
    elif args.family == "liquor":
        payload = liquor_payload(args.base_url, args.ids)
    else:
        payload = renewal_payload(args.base_url, args.ids)

    indent = None if args.compact else 2
    print(json.dumps(payload, indent=indent, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
