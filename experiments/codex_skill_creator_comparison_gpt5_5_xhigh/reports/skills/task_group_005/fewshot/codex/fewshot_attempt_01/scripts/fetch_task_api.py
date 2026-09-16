#!/usr/bin/env python3
"""Fetch paginated records from a runner-provided task JSON API."""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def parse_filter(raw):
    if "=" not in raw:
        raise argparse.ArgumentTypeError("filters must be key=value")
    key, value = raw.split("=", 1)
    key = key.strip()
    if not key:
        raise argparse.ArgumentTypeError("filter key cannot be empty")
    return key, value


def normalize_base_url(value):
    if not value:
        raise SystemExit("TASK_ENV_BASE_URL is not set; pass --base-url")
    return value.rstrip("/") + "/"


def build_url(base_url, endpoint, params):
    endpoint = endpoint.lstrip("/")
    query = urllib.parse.urlencode(params, doseq=True)
    url = urllib.parse.urljoin(base_url, endpoint)
    if query:
        url = f"{url}?{query}"
    return url


def get_json(url):
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} for {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Request failed for {url}: {exc}") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Non-JSON response from {url}: {raw[:500]}") from exc


def fetch_endpoint(base_url, endpoint, filters, limit, no_paginate):
    params = dict(filters)
    if no_paginate:
        return get_json(build_url(base_url, endpoint, params))

    offset = 0
    records = []
    first_payload = None
    while True:
        page_params = dict(params)
        page_params["limit"] = str(limit)
        page_params["offset"] = str(offset)
        payload = get_json(build_url(base_url, endpoint, page_params))
        if first_payload is None:
            first_payload = payload

        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            return payload
        records.extend(data)

        total = payload.get("total")
        count = payload.get("count", len(data))
        if total is None:
            if not data or count < limit:
                break
        elif len(records) >= int(total):
            break
        if not data:
            break
        offset += len(data)

    result = dict(first_payload or {})
    result["data"] = records
    result["count"] = len(records)
    result["offset"] = 0
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("endpoint", help="Endpoint path, such as /api/claims")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("TASK_ENV_BASE_URL"),
        help="Task API base URL. Defaults to TASK_ENV_BASE_URL.",
    )
    parser.add_argument(
        "--filter",
        action="append",
        default=[],
        type=parse_filter,
        help="Exact-match query parameter, as key=value. Repeat as needed.",
    )
    parser.add_argument("--limit", type=int, default=100, help="Page size for list endpoints.")
    parser.add_argument("--no-paginate", action="store_true", help="Fetch one response only.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()

    if args.limit <= 0:
        raise SystemExit("--limit must be positive")

    base_url = normalize_base_url(args.base_url)
    payload = fetch_endpoint(base_url, args.endpoint, args.filter, args.limit, args.no_paginate)
    json.dump(payload, sys.stdout, indent=2 if args.pretty else None, sort_keys=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
