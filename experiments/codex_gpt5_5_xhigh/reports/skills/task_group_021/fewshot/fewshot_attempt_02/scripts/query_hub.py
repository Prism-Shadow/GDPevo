#!/usr/bin/env python3
import argparse
import json
import re
import sys
import urllib.error
import urllib.request


def read_access(path):
    text = open(path, "r", encoding="utf-8").read()
    base_match = re.search(r"GDPEVO_ENV_BASE_URL=([^\s]+)", text)
    token_match = re.search(r"Authorization header:\s*Bearer\s+([^\s]+)", text)
    if not base_match or not token_match:
        raise SystemExit(f"Could not parse base URL and bearer token from {path}")
    return base_match.group(1).rstrip("/") + "/", token_match.group(1)


def main():
    parser = argparse.ArgumentParser(description="Run a read-only Asteria hub SQL query.")
    parser.add_argument("query", nargs="?", help="SQL query text. Omit when using --file.")
    parser.add_argument("--file", "-f", help="Read SQL from this file.")
    parser.add_argument("--env", default="environment_access.md", help="Path to environment_access.md.")
    args = parser.parse_args()

    if args.file:
        sql = open(args.file, "r", encoding="utf-8").read()
    elif args.query:
        sql = args.query
    else:
        sql = sys.stdin.read()
    sql = sql.strip()
    if not sql:
        raise SystemExit("No SQL query provided")

    base_url, token = read_access(args.env)
    body = json.dumps({"query": sql}).encode("utf-8")
    req = urllib.request.Request(
        base_url + "api/query",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.load(resp)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code}: {detail}") from exc

    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
