#!/usr/bin/env python3
"""Download authorized PHO portal CSV datasets into a local snapshot directory."""

from __future__ import annotations

import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path


DATASETS = [
    "states",
    "counties",
    "countries",
    "state_health",
    "state_socioeconomic",
    "county_health",
    "county_socioeconomic",
    "country_indicators",
    "revisions",
]


def fetch_csv(base_url: str, dataset: str) -> str:
    base = base_url.rstrip("/") + "/"
    query = urllib.parse.urlencode({"dataset": dataset, "format": "csv"})
    url = urllib.parse.urljoin(base, "download") + "?" + query
    with urllib.request.urlopen(url, timeout=60) as response:
        body = response.read().decode("utf-8")
    if not body.startswith("\ufeff"):
        return body
    return body.lstrip("\ufeff")


def count_rows(csv_text: str) -> tuple[int, list[str]]:
    reader = csv.reader(csv_text.splitlines())
    try:
        header = next(reader)
    except StopIteration:
        return 0, []
    return sum(1 for _ in reader), header


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: pho_snapshot.py <base_url> <output_dir>", file=sys.stderr)
        return 2

    base_url = argv[1]
    out_dir = Path(argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "base_url": base_url,
        "created_at_unix": int(time.time()),
        "datasets": {},
    }

    for dataset in DATASETS:
        csv_text = fetch_csv(base_url, dataset)
        row_count, columns = count_rows(csv_text)
        path = out_dir / f"{dataset}.csv"
        path.write_text(csv_text, encoding="utf-8", newline="")
        manifest["datasets"][dataset] = {
            "path": path.name,
            "row_count": row_count,
            "columns": columns,
        }

    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
