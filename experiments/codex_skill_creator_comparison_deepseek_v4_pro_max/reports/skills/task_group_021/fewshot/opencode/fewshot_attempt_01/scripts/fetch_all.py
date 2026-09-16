#!/usr/bin/env python3
"""Fetch all rows from a paginated Asteria DQ Hub endpoint."""

import json
import sys
import urllib.request
import urllib.error
import urllib.parse as urlparse


def fetch_all(url, post_body=None):
    """Paginate through a GET or POST endpoint and return all rows."""
    rows = []

    while True:
        req_url = url

        if post_body is not None:
            req_data = json.dumps(post_body).encode("utf-8")
            req = urllib.request.Request(req_url, data=req_data, method="POST")
            req.add_header("Content-Type", "application/json")
        else:
            req = urllib.request.Request(req_url, method="GET")

        try:
            with urllib.request.urlopen(req) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            print(f"HTTP error {e.code}: {e.reason}", file=sys.stderr)
            sys.exit(1)
        except urllib.error.URLError as e:
            print(f"URL error: {e.reason}", file=sys.stderr)
            sys.exit(1)

        # Response can be a flat array or an object with rows/next_cursor
        if isinstance(body, list):
            rows.extend(body)
            next_cursor = resp.headers.get("X-Next-Cursor") or None
        elif isinstance(body, dict):
            batch = body.get("rows", body.get("data", []))
            rows.extend(batch)
            next_cursor = body.get("next_cursor")
        else:
            print(f"Unexpected response type: {type(body)}", file=sys.stderr)
            sys.exit(1)

        if not next_cursor:
            break

        # Prepare next request
        if post_body is not None:
            post_body["cursor"] = next_cursor
        else:
            parsed = urlparse.urlparse(url)
            params = urlparse.parse_qs(parsed.query)
            params["cursor"] = [next_cursor]
            new_query = urlparse.urlencode(params, doseq=True)
            url = urlparse.urlunparse((
                parsed.scheme, parsed.netloc, parsed.path,
                parsed.params, new_query, parsed.fragment
            ))

    return rows


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch all rows from a paginated Asteria DQ Hub endpoint"
    )
    parser.add_argument("url", help="Full endpoint URL")
    parser.add_argument(
        "--query", dest="query_file",
        help="JSON file with POST body for /api/query"
    )
    args = parser.parse_args()

    post_body = None
    if args.query_file:
        with open(args.query_file) as f:
            post_body = json.load(f)

    rows = fetch_all(args.url, post_body=post_body)
    json.dump(rows, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
