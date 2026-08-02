#!/usr/bin/env python3
"""Generic fetch/parse helpers for the Public Health Observatory portal.

Reusable across all PHO registered-algorithmic-audit tasks. Contains NO task-specific
values: the base URL is read from environment_access.md, and dataset/filter/selection
choices are passed in by the caller from the analysis_request.json being solved.

CLI:
    python portal_fetch.py <dataset> [--filter k=v ...] [--out file.csv]
    python portal_fetch.py --catalog
    python portal_fetch.py --methodology

Library:
    rows = fetch_rows("state_health", state_abbr="CA", year="2024")
    gov  = select_governing_release(rows, key=("state_abbr","year","measure_id",
             "value_type","source_type"), status_field="release_status",
             final_value="FINAL", revision_field="revision",
             released_at_field="released_at", tiebreak_field="observation_id")
"""
import csv
import io
import re
import sys
import urllib.parse
import urllib.request

VALID_DATASETS = {
    "states", "counties", "countries", "state_health", "state_socioeconomic",
    "county_health", "county_socioeconomic", "country_indicators", "revisions",
}


def base_url(env_path="environment_access.md"):
    """Read GDPEVO_ENV_BASE_URL from environment_access.md (network access file)."""
    for candidate in (env_path, "/work/environment_access.md", "environment_access.md"):
        try:
            with open(candidate) as fh:
                text = fh.read()
            break
        except OSError:
            continue
    else:
        raise SystemExit("environment_access.md not found; it holds the portal base URL")
    m = re.search(r"GDPEVO_ENV_BASE_URL\s*=\s*(\S+)", text)
    if not m:
        raise SystemExit("GDPEVO_ENV_BASE_URL not found in environment_access.md")
    return m.group(1).rstrip("/")


def _get(url, timeout=60):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def fetch_csv(dataset, **filters):
    """Return the raw CSV text for a dataset via /download?...&format=csv."""
    if dataset not in VALID_DATASETS:
        raise ValueError(f"unknown dataset {dataset!r}; valid: {sorted(VALID_DATASETS)}")
    params = {"dataset": dataset, "format": "csv"}
    params.update({k: v for k, v in filters.items() if v is not None})
    url = f"{base_url()}/download?" + urllib.parse.urlencode(params)
    text = _get(url)
    if "Invalid request" in text[:600] or "Unknown dataset" in text[:600]:
        raise RuntimeError(f"portal rejected request: {url}\n{text[:300]}")
    return text


def fetch_rows(dataset, **filters):
    """Return dataset rows as a list of dicts (all values as strings, as published)."""
    return list(csv.DictReader(io.StringIO(fetch_csv(dataset, **filters))))


def select_governing_release(
    rows, key, status_field="release_status", final_value="FINAL",
    revision_field="revision", released_at_field="released_at", tiebreak_field=None,
):
    """Collapse rows to one governing record per logical cell.

    Rule (matches the portal methodology): among rows sharing ``key``, prefer
    ``final_value`` over any other status; among finals pick the highest
    ``revision``, then latest ``released_at``, then the max ``tiebreak_field``.
    ``rows`` should already be filtered to the declared value_type/source_type/etc.
    """
    def rank(r):
        is_final = 1 if r.get(status_field) == final_value else 0
        try:
            rev = int(r.get(revision_field) or -1)
        except (TypeError, ValueError):
            rev = -1
        released = r.get(released_at_field) or ""
        tb = r.get(tiebreak_field) or "" if tiebreak_field else ""
        return (is_final, rev, released, tb)

    best = {}
    for r in rows:
        k = tuple(r.get(f) for f in key)
        if k not in best or rank(r) > rank(best[k]):
            best[k] = r
    return list(best.values())


def is_available(row, value_field="value", suppression_field="suppression_flag",
                 invalid_quality_flags=()):
    """True if a published value is usable (never zero-fill missing/suppressed)."""
    if str(row.get(suppression_field, "0")) == "1":
        return False
    v = row.get(value_field)
    if v is None or str(v).strip() == "":
        return False
    if row.get("quality_flag") in set(invalid_quality_flags):
        return False
    return True


def _print_stripped(html):
    text = re.sub(r"<[^>]+>", " ", html)
    print(re.sub(r"[ \t]+", " ", text))


def main(argv):
    if not argv:
        print(__doc__)
        return 0
    if argv[0] == "--catalog":
        _print_stripped(_get(base_url() + "/catalog"))
        return 0
    if argv[0] == "--methodology":
        _print_stripped(_get(base_url() + "/methodology"))
        return 0
    dataset = argv[0]
    filters, out = {}, None
    i = 1
    while i < len(argv):
        if argv[i] == "--filter" and i + 1 < len(argv):
            k, _, v = argv[i + 1].partition("=")
            filters[k] = v
            i += 2
        elif argv[i] == "--out" and i + 1 < len(argv):
            out = argv[i + 1]
            i += 2
        else:
            i += 1
    csv_text = fetch_csv(dataset, **filters)
    if out:
        with open(out, "w") as fh:
            fh.write(csv_text)
        print(f"wrote {out} ({csv_text.count(chr(10))} lines)")
    else:
        sys.stdout.write(csv_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
