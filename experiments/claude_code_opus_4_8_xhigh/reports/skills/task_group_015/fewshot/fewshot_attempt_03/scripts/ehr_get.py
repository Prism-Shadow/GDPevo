#!/usr/bin/env python3
"""Generic read-only helper for the EHR quality-governance environment.

Resolves the base URL from an ``environment_access.md`` file (the
``GDPEVO_ENV_BASE_URL`` line, overridable with $GDPEVO_ENV_BASE_URL) and issues a
GET against an endpoint path, printing the JSON response. Contains no task- or
answer-specific values; it is pure plumbing so a case can be solved from live data.

Usage:
    python3 ehr_get.py /api/patients/P-00000
    python3 ehr_get.py /api/referrals
    python3 ehr_get.py --env /path/to/environment_access.md /api/icd10/A00.0

Exit status is non-zero on transport errors; an HTTP 404 is printed as
{"_http_status": 404} so callers can treat "not found" as a signal.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def resolve_base_url(env_file):
    env = os.environ.get("GDPEVO_ENV_BASE_URL")
    if env:
        return env.rstrip("/")
    if env_file and os.path.exists(env_file):
        with open(env_file, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("GDPEVO_ENV_BASE_URL"):
                    return line.split("=", 1)[1].strip().rstrip("/")
    raise SystemExit(
        "Could not resolve base URL: set $GDPEVO_ENV_BASE_URL or point --env at "
        "an environment_access.md containing a GDPEVO_ENV_BASE_URL= line."
    )


def get(base_url, path, timeout):
    url = base_url + ("" if path.startswith("/") else "/") + path
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # 404 is a meaningful "not found" signal, not a fatal error.
        return {"_http_status": exc.code, "_url": url}


def main():
    ap = argparse.ArgumentParser(description="GET one EHR API endpoint as JSON.")
    ap.add_argument("path", help="Endpoint path, e.g. /api/patients/P-00000")
    ap.add_argument("--env", default="environment_access.md",
                    help="Path to environment_access.md (default: ./environment_access.md)")
    ap.add_argument("--timeout", type=float, default=15.0)
    args = ap.parse_args()

    base = resolve_base_url(args.env)
    data = get(base, args.path, args.timeout)
    json.dump(data, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
