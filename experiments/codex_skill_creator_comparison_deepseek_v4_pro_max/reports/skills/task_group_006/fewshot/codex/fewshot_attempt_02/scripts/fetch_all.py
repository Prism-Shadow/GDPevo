#!/usr/bin/env python3
"""
Fetch all ProcureOps endpoints and write JSON to stdout or a directory.

Usage:
  python3 fetch_all.py <BASE_URL> [--outdir <dir>]

If --outdir is given, writes one .json file per endpoint. Otherwise prints a
single JSON object with endpoint-name keys to stdout.
"""
import json
import sys
import urllib.request
from pathlib import Path

ENDPOINTS = [
    "manifest",
    "suppliers",
    "items",
    "programs",
    "contracts",
    "purchase_requisitions",
    "purchase_orders",
    "receipts",
    "ap/invoices",
    "ap/payments",
    "approvals",
    "budget_snapshots",
    "vendor_risk_events",
]


def fetch_json(url):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def main():
    if len(sys.argv) < 2:
        print("Usage: fetch_all.py <BASE_URL> [--outdir <dir>]", file=sys.stderr)
        sys.exit(1)

    base = sys.argv[1].rstrip("/")
    outdir = None

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--outdir" and i + 1 < len(args):
            outdir = Path(args[i + 1])
            i += 2
        else:
            i += 1

    if outdir:
        outdir.mkdir(parents=True, exist_ok=True)

    data = {}
    for ep in ENDPOINTS:
        url = f"{base}/{ep}"
        safe_name = ep.replace("/", "_")
        try:
            result = fetch_json(url)
        except Exception as exc:
            print(f"[WARN] {ep} failed: {exc}", file=sys.stderr)
            result = None

        if outdir:
            fpath = outdir / f"{safe_name}.json"
            fpath.write_text(json.dumps(result, indent=2))
            print(f"[OK] Wrote {fpath}", file=sys.stderr)
        else:
            data[safe_name] = result

    if not outdir:
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
