#!/usr/bin/env python3
"""Fetch Asteria hub JSON endpoints or run a read-only query.

This helper is intentionally generic. Read environment_access.md first, then
pass the base URL and credentials through flags or environment variables.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


LIST_KEYS = ("items", "data", "records", "rows", "results")
NEXT_KEYS = ("next", "next_url", "nextUrl")
CURSOR_KEYS = ("next_cursor", "nextCursor")


def parse_key_value(raw):
    if "=" not in raw:
        raise argparse.ArgumentTypeError(f"Expected key=value, got {raw!r}")
    key, value = raw.split("=", 1)
    if not key:
        raise argparse.ArgumentTypeError("Key cannot be empty")
    return key, value


def parse_header(raw):
    if ":" not in raw:
        raise argparse.ArgumentTypeError(f"Expected Header: value, got {raw!r}")
    key, value = raw.split(":", 1)
    return key.strip(), value.strip()


def build_headers(args):
    headers = {"Accept": "application/json"}
    token = args.bearer or os.environ.get("TASK_ENV_BEARER") or os.environ.get("TASK_ENV_TOKEN")
    query_token = os.environ.get("TASK_ENV_QUERY_TOKEN")
    api_key = args.api_key or os.environ.get("TASK_ENV_API_KEY")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    elif query_token:
        headers["Authorization"] = f"Bearer {query_token}"
    if api_key:
        headers["X-API-Key"] = api_key
    for key, value in args.header:
        headers[key] = value
    return headers


def join_url(base_url, path):
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return base_url.rstrip("/") + "/" + path.lstrip("/")


def add_params(url, params):
    if not params:
        return url
    parsed = urllib.parse.urlsplit(url)
    existing = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    query = urllib.parse.urlencode(existing + params)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, query, parsed.fragment))


def request_json(url, headers, method="GET", body=None):
    data = None
    req_headers = dict(headers)
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from {url}\n{detail}") from exc
    return json.loads(payload)


def page_items(obj):
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for key in LIST_KEYS:
            value = obj.get(key)
            if isinstance(value, list):
                return value
    return None


def next_url(obj):
    if not isinstance(obj, dict):
        return None
    for key in NEXT_KEYS:
        value = obj.get(key)
        if value:
            return value
    links = obj.get("links")
    if isinstance(links, dict) and links.get("next"):
        return links["next"]
    return None


def next_cursor(obj):
    if not isinstance(obj, dict):
        return None
    for key in CURSOR_KEYS:
        value = obj.get(key)
        if value:
            return value
    pagination = obj.get("pagination")
    if isinstance(pagination, dict):
        for key in CURSOR_KEYS:
            value = pagination.get(key)
            if value:
                return value
    return None


def dump_get(args, headers):
    base_url = args.base_url or os.environ.get("TASK_ENV_BASE_URL")
    if not base_url and not args.path.startswith(("http://", "https://")):
        raise SystemExit("Provide --base-url or TASK_ENV_BASE_URL")
    url = add_params(join_url(base_url or "", args.path), args.param)
    pages = []
    items = []
    seen_urls = set()

    for page_index in range(args.max_pages):
        if url in seen_urls:
            raise SystemExit(f"Pagination loop detected at {url}")
        seen_urls.add(url)
        obj = request_json(url, headers)
        pages.append(obj)
        extracted = page_items(obj)
        if extracted is not None:
            items.extend(extracted)

        nxt = next_url(obj)
        if nxt:
            url = join_url(base_url or "", nxt)
            continue
        cursor = next_cursor(obj)
        if cursor:
            url = add_params(join_url(base_url or "", args.path), args.param + [(args.cursor_param, cursor)])
            continue
        break
    else:
        raise SystemExit(f"Stopped after --max-pages={args.max_pages}")

    if args.items_only:
        json.dump(items, sys.stdout, ensure_ascii=False, indent=2)
    elif items:
        json.dump({"page_count": len(pages), "item_count": len(items), "items": items}, sys.stdout, ensure_ascii=False, indent=2)
    else:
        json.dump(pages[0] if len(pages) == 1 else {"page_count": len(pages), "pages": pages}, sys.stdout, ensure_ascii=False, indent=2)
    print()


def dump_query(args, headers):
    base_url = args.base_url or os.environ.get("TASK_ENV_BASE_URL")
    if not base_url:
        raise SystemExit("Provide --base-url or TASK_ENV_BASE_URL")
    if args.sql_file:
        with open(args.sql_file, "r", encoding="utf-8") as handle:
            sql = handle.read()
    else:
        sql = args.sql
    if not sql:
        raise SystemExit("Provide --sql or --sql-file for query mode")
    body = {args.query_key: sql}
    for key, value in args.body:
        body[key] = value
    obj = request_json(join_url(base_url, args.query_path), headers, method="POST", body=body)
    json.dump(obj, sys.stdout, ensure_ascii=False, indent=2)
    print()


def main():
    parser = argparse.ArgumentParser(description="Fetch Asteria hub JSON data.")
    parser.add_argument("--base-url", help="Hub base URL; defaults to TASK_ENV_BASE_URL")
    parser.add_argument("--bearer", help="Bearer token, if required")
    parser.add_argument("--api-key", help="API key, if required")
    parser.add_argument("--header", action="append", default=[], type=parse_header, help="Extra HTTP header as 'Name: value'")
    sub = parser.add_subparsers(dest="mode", required=True)

    get = sub.add_parser("get", help="GET an endpoint, following common pagination shapes")
    get.add_argument("path", help="Endpoint path or absolute URL")
    get.add_argument("--param", action="append", default=[], type=parse_key_value, help="Query parameter as key=value")
    get.add_argument("--cursor-param", default="cursor", help="Cursor query parameter name")
    get.add_argument("--max-pages", type=int, default=200)
    get.add_argument("--items-only", action="store_true")

    query = sub.add_parser("query", help="POST a read-only query")
    query.add_argument("--query-path", default="/api/query")
    query.add_argument("--query-key", default="query", help="JSON body key for the SQL/query text")
    query.add_argument("--sql")
    query.add_argument("--sql-file")
    query.add_argument("--body", action="append", default=[], type=parse_key_value, help="Extra JSON body key=value")

    args = parser.parse_args()
    headers = build_headers(args)
    if args.mode == "get":
        dump_get(args, headers)
    else:
        dump_query(args, headers)


if __name__ == "__main__":
    main()
