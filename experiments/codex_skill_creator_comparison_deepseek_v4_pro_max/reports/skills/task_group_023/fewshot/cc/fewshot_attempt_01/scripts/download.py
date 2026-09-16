#!/usr/bin/env python3
"""Download PHO portal datasets as CSV.

Usage:
  python3 download.py <base_url> <dataset_name> [output_path]

  python3 download.py http://task-env:9023 state_health /tmp/state_health.csv

If output_path is omitted, prints CSV to stdout.

Valid dataset names:
  states, counties, countries, state_health, state_socioeconomic,
  county_health, county_socioeconomic, country_indicators, revisions
"""

import sys
import urllib.request
import urllib.error

def main():
    if len(sys.argv) < 3:
        print("Usage: download.py <base_url> <dataset> [output_path]", file=sys.stderr)
        sys.exit(1)

    base_url = sys.argv[1].rstrip("/")
    dataset = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else None

    valid_datasets = {
        "states", "counties", "countries",
        "state_health", "state_socioeconomic",
        "county_health", "county_socioeconomic",
        "country_indicators", "revisions"
    }

    if dataset not in valid_datasets:
        print(f"Unknown dataset: {dataset}", file=sys.stderr)
        print(f"Valid: {', '.join(sorted(valid_datasets))}", file=sys.stderr)
        sys.exit(1)

    url = f"{base_url}/download?dataset={dataset}&format=csv"

    try:
        with urllib.request.urlopen(url) as resp:
            content = resp.read()
            if output_path:
                with open(output_path, "wb") as f:
                    f.write(content)
                print(f"Written {len(content)} bytes to {output_path}", file=sys.stderr)
            else:
                sys.stdout.buffer.write(content)
    except urllib.error.URLError as e:
        print(f"Request failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
