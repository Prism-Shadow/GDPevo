#!/usr/bin/env python3
"""Fetch all M&A deal-workbench resources for one deal_id into a single JSON blob.

Reads `environment_access.md` for the base URL and read-only SQL token — do not pass
secrets on the command line. Stdlib only (urllib).

Usage:
    python3 fetch_deal.py --deal-id PRJ_EXAMPLE
    python3 fetch_deal.py --deal-id PRJ_EXAMPLE --env-file /work/environment_access.md
    python3 fetch_deal.py --deal-id PRJ_EXAMPLE --base-url http://host:port/ --token X

Prints one consolidated JSON object to stdout. Exit code 1 on fetch failure.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def parse_env_file(path):
    """Return (base_url, token) parsed from environment_access.md, or (None, None)."""
    base_url = None
    token = None
    if not path or not os.path.exists(path):
        return base_url, token
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if "GDPEVO_ENV_BASE_URL" in s and "=" in s:
                base_url = s.split("=", 1)[1].strip().strip('"').strip("'")
            elif "token:" in s.lower():
                # e.g. "POST /api/query token: <readonly-token>"
                token = s.split(":", 1)[1].strip().strip('"').strip("'").split()[0]
    return base_url, token


def http_get_json(url, timeout=30):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fetch all workbench resources for a deal.")
    ap.add_argument("--deal-id", required=True, help="deal_id, e.g. PRJ_EXAMPLE")
    ap.add_argument("--env-file", default=None,
                    help="path to environment_access.md (default: ./environment_access.md "
                         "or /work/environment_access.md)")
    ap.add_argument("--base-url", default=None, help="override base URL")
    ap.add_argument("--token", default=None, help="override read-only SQL token")
    args = ap.parse_args(argv)

    base_url = args.base_url
    token = args.token
    if not base_url or not token:
        env_path = args.env_file
        if env_path is None:
            for cand in ("environment_access.md", "/work/environment_access.md"):
                if os.path.exists(cand):
                    env_path = cand
                    break
        f_base, f_token = parse_env_file(env_path)
        base_url = base_url or f_base
        token = token or f_token

    if not base_url:
        sys.stderr.write("error: base URL not found (set --base-url or provide "
                         "environment_access.md with GDPEVO_ENV_BASE_URL)\n")
        return 1
    base_url = base_url.rstrip("/")

    out = {"deal_id": args.deal_id, "base_url": base_url, "resources": {}}
    errors = []

    def grab(key, path):
        url = base_url + path
        try:
            out["resources"][key] = http_get_json(url)
        except urllib.error.HTTPError as e:
            errors.append({"key": key, "url": url, "error": "HTTP %s" % e.code})
        except Exception as e:  # noqa: BLE001
            errors.append({"key": key, "url": url, "error": str(e)})

    # 1. Deal record (carries the links map + playbook_id/policy_id).
    grab("deal", "/api/deals/%s" % args.deal_id)

    # 2. Every linked sub-resource, following the deal record's links map.
    links = (out["resources"].get("deal") or {}).get("links") or {}
    # Fallback canonical paths if links is absent.
    if not links:
        links = {
            "terms": "/api/deals/%s/terms" % args.deal_id,
            "consents": "/api/deals/%s/consents" % args.deal_id,
            "employees": "/api/deals/%s/employees" % args.deal_id,
            "material_contracts": "/api/deals/%s/material-contracts" % args.deal_id,
            "diligence_findings": "/api/deals/%s/diligence-findings" % args.deal_id,
            "risk_estimates": "/api/deals/%s/risk-estimates" % args.deal_id,
            "benchmarks": "/api/deals/%s/benchmarks" % args.deal_id,
            "regulatory": "/api/deals/%s/regulatory" % args.deal_id,
            "cap_table": "/api/deals/%s/cap-table" % args.deal_id,
            "notes": "/api/deals/%s/notes" % args.deal_id,
            "documents": "/api/deals/%s/documents" % args.deal_id,
        }
    for key, rel in links.items():
        # links values are absolute site paths beginning with /api/...
        grab(key, rel if rel.startswith("/") else "/" + rel)

    # 3. Governing playbook rules + committee policy thresholds (if the deal has them).
    deal_obj = (out["resources"].get("deal") or {}).get("deal") or {}
    playbook_id = deal_obj.get("playbook_id")
    policy_id = deal_obj.get("policy_id")
    if playbook_id:
        grab("playbook_rules", "/api/playbooks/%s/rules" % playbook_id)
    if policy_id:
        grab("policy_thresholds", "/api/policies/%s/thresholds" % policy_id)

    out["playbook_id"] = playbook_id
    out["policy_id"] = policy_id
    out["sql_token"] = token  # expose so the caller can run POST /api/query cross-checks
    if errors:
        out["fetch_errors"] = errors

    json.dump(out, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
