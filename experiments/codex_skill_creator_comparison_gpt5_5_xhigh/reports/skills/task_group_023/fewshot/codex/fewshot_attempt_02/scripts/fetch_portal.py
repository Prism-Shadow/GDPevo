#!/usr/bin/env python3
"""Download Public Health Observatory CSV datasets from an allowed portal."""

from __future__ import annotations

import argparse
import csv
import sys
import urllib.parse
import urllib.request
from pathlib import Path


DATASETS = {
    "states",
    "counties",
    "countries",
    "state_health",
    "state_socioeconomic",
    "county_health",
    "county_socioeconomic",
    "country_indicators",
    "revisions",
}


def normalize_base_url(raw: str) -> str:
    base = raw.strip()
    if not base:
        raise ValueError("base URL is empty")
    if not base.endswith("/"):
        base += "/"
    return base


def download_dataset(base_url: str, dataset: str, out_dir: Path) -> Path:
    if dataset not in DATASETS:
        allowed = ", ".join(sorted(DATASETS))
        raise ValueError(f"unknown dataset {dataset!r}; allowed: {allowed}")
    out_dir.mkdir(parents=True, exist_ok=True)
    query = urllib.parse.urlencode({"dataset": dataset, "format": "csv"})
    url = urllib.parse.urljoin(normalize_base_url(base_url), f"download?{query}")
    out_path = out_dir / f"{dataset}.csv"
    with urllib.request.urlopen(url, timeout=60) as response:
        body = response.read()
    out_path.write_bytes(body)
    return out_path


def count_rows(path: Path) -> int:
    with path.open(newline="") as f:
        reader = csv.reader(f)
        next(reader, None)
        return sum(1 for _ in reader)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Task environment base URL")
    parser.add_argument(
        "--dataset",
        action="append",
        choices=sorted(DATASETS),
        help="Dataset to download; repeatable. Defaults to all datasets.",
    )
    parser.add_argument("--out-dir", default="pho_portal_csv", help="Output directory")
    parser.add_argument("--list", action="store_true", help="List supported datasets and exit")
    args = parser.parse_args(argv)

    if args.list:
        for name in sorted(DATASETS):
            print(name)
        return 0

    out_dir = Path(args.out_dir)
    datasets = args.dataset or sorted(DATASETS)
    for dataset in datasets:
        path = download_dataset(args.base_url, dataset, out_dir)
        print(f"{dataset}: {path} ({count_rows(path)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
