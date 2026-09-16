#!/usr/bin/env python3
"""Bulk-download PHO portal datasets as CSV for local analysis.

Usage:
  python3 download_portal_data.py <base_url> <output_dir>

Downloads all nine datasets referenced in the portal catalog into
<output_dir>/ as CSV files, then prints a summary of row counts.
"""

import csv
import io
import os
import sys
import urllib.request

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


def download_csv(base_url: str, dataset: str) -> str:
    """Fetch a dataset as CSV text from the portal."""
    url = f"{base_url.rstrip('/')}/download?dataset={dataset}&format=csv"
    with urllib.request.urlopen(url) as resp:
        return resp.read().decode("utf-8")


def main() -> None:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <base_url> <output_dir>", file=sys.stderr)
        sys.exit(2)

    base_url = sys.argv[1]
    output_dir = sys.argv[2]
    os.makedirs(output_dir, exist_ok=True)

    for dataset in DATASETS:
        print(f"Downloading {dataset} ...", end=" ", flush=True)
        try:
            text = download_csv(base_url, dataset)
        except Exception as exc:
            print(f"FAILED: {exc}")
            continue

        out_path = os.path.join(output_dir, f"{dataset}.csv")
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(text)

        reader = csv.reader(io.StringIO(text))
        header = next(reader)
        row_count = sum(1 for _ in reader)
        print(f"{row_count} rows, {len(header)} columns -> {out_path}")


if __name__ == "__main__":
    main()
