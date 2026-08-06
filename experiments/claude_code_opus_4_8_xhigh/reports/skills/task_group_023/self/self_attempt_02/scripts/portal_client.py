#!/usr/bin/env python3
"""Read-only client for the Public Health Observatory (PHO) data portal.

The portal is the SOLE authoritative evidence source for PHO registered
algorithmic-audit tasks. This client wraps the two things you need:

  1. the base URL, read from ``environment_access.md`` (or GDPEVO_ENV_BASE_URL);
  2. the bulk CSV endpoint ``/download?dataset=<name>&format=csv&<filters>``,
     which returns the FULL, un-paginated table (the HTML ``/data/*`` and
     ``/geographies/*`` pages paginate at page_size=50 and are for humans).

Everything is GET-only. Nothing here mutates the environment.

Typical use inside a task:

    from portal_client import Portal
    p = Portal()                       # auto-discovers base URL
    rows = p.fetch("state_health",     # list[dict], all columns as strings
                   measure_id="life_expectancy", year="2023")
    states = p.fetch("states")         # geography reference (fips/abbr/region/division)

Filters are exact-match on the columns the catalog lists as filterable; when in
doubt, download the whole table and filter in your own code. Values arrive as
strings — cast deliberately (FIPS keep leading zeros; treat "" as missing, never 0).

CLI:
    python3 portal_client.py catalog
    python3 portal_client.py fetch state_health measure_id=life_expectancy year=2023
    python3 portal_client.py raw /methodology?doc=release-lifecycle
"""
from __future__ import annotations

import csv
import io
import os
import re
import sys
import urllib.parse
import urllib.request

DEFAULT_ENV_FILE_CANDIDATES = (
    "environment_access.md",
    "../environment_access.md",
    "../../environment_access.md",
    "/work/environment_access.md",
)

DATASETS = (
    "states", "counties", "countries",
    "state_health", "state_socioeconomic",
    "county_health", "county_socioeconomic",
    "country_indicators", "revisions",
)


def discover_base_url() -> str:
    """Resolve the portal base URL. Env var wins; else parse environment_access.md."""
    env = os.environ.get("GDPEVO_ENV_BASE_URL")
    if env:
        return env.rstrip("/")
    for path in DEFAULT_ENV_FILE_CANDIDATES:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue
        m = re.search(r"GDPEVO_ENV_BASE_URL\s*=\s*(\S+)", text)
        if m:
            return m.group(1).rstrip("/")
    raise RuntimeError(
        "Could not resolve portal base URL: set GDPEVO_ENV_BASE_URL or place "
        "environment_access.md (with GDPEVO_ENV_BASE_URL=...) on one of: "
        + ", ".join(DEFAULT_ENV_FILE_CANDIDATES)
    )


class Portal:
    def __init__(self, base_url: str | None = None, timeout: float = 60.0):
        self.base_url = (base_url or discover_base_url()).rstrip("/")
        self.timeout = timeout

    def _get(self, path: str) -> bytes:
        url = self.base_url + path
        with urllib.request.urlopen(url, timeout=self.timeout) as resp:
            return resp.read()

    def raw(self, path: str) -> str:
        """GET any portal path (e.g. '/methodology?doc=release-lifecycle'). Returns text."""
        if not path.startswith("/"):
            path = "/" + path
        return self._get(path).decode("utf-8", errors="replace")

    def fetch(self, dataset: str, **filters: str) -> list[dict]:
        """Download a full dataset as CSV (with optional exact-match filters).

        Returns a list of dict rows with string values. Empty string means the
        cell is blank in the source — treat as MISSING, never as zero.
        """
        if dataset not in DATASETS:
            raise ValueError(
                f"Unknown dataset {dataset!r}; known: {', '.join(DATASETS)}"
            )
        params = {"dataset": dataset, "format": "csv"}
        params.update({k: str(v) for k, v in filters.items() if v is not None})
        qs = urllib.parse.urlencode(params)
        text = self._get("/download?" + qs).decode("utf-8", errors="replace")
        if "<!doctype html" in text[:200].lower():
            # portal returns an HTML error page for bad requests
            msg = re.search(r'class="error">([^<]+)<', text)
            raise RuntimeError(
                f"Portal rejected download of {dataset!r}: "
                f"{msg.group(1) if msg else 'see HTML error page'}"
            )
        return list(csv.DictReader(io.StringIO(text)))

    def catalog_text(self) -> str:
        html = self.raw("/catalog")
        html = re.sub(r"<style.*?</style>", "", html, flags=re.S)
        html = re.sub(r"<[^>]+>", " ", html)
        return re.sub(r"[ \t\n]+", " ", html).strip()


def _main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    p = Portal()
    cmd, rest = argv[0], argv[1:]
    if cmd == "catalog":
        print(p.catalog_text())
    elif cmd == "raw":
        print(p.raw(rest[0]))
    elif cmd == "fetch":
        dataset = rest[0]
        filters = dict(kv.split("=", 1) for kv in rest[1:] if "=" in kv)
        rows = p.fetch(dataset, **filters)
        w = csv.writer(sys.stdout)
        if rows:
            w.writerow(rows[0].keys())
            for r in rows:
                w.writerow(r.values())
        print(f"# {len(rows)} rows", file=sys.stderr)
    else:
        print(f"unknown command {cmd!r}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
