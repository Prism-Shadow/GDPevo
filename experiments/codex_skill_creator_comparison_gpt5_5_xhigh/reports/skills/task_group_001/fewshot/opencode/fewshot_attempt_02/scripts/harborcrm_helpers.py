#!/usr/bin/env python3
"""Small helpers for HarborCRM JSON handoff tasks."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from typing import Any


PLATFORM_ORDER = ["AUV", "ROV", "Underwater Camera"]
SOURCE_RANK = {
    "partner_upload": 6,
    "sponsor_form": 5,
    "exhibitor_form": 4,
    "badge_scan": 3,
    "webinar_form": 2,
    "manual_upload": 1,
}


def normalize_email(value: Any) -> str:
    return str(value or "").strip().lower()


def normalize_phone(value: Any) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def company_key(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"&", " and ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    words = [
        w
        for w in text.split()
        if w
        not in {
            "inc",
            "incorporated",
            "llc",
            "ltd",
            "limited",
            "corp",
            "corporation",
            "co",
            "company",
            "mfg",
            "manufacturing",
        }
    ]
    return " ".join(words)


def classify_platforms(description: Any) -> list[str]:
    text = str(description or "").lower()
    found: list[str] = []
    if re.search(r"\bauvs?\b|autonomous underwater|autonomous .*scout|underwater drone", text):
        found.append("AUV")
    if re.search(r"\brovs?\b|remotely operated|inspection-class|inspection robot|pen-cleaning|tethered", text):
        found.append("ROV")
    if re.search(r"underwater camera|camera module|camera array|low-light inspection|camera systems?", text):
        found.append("Underwater Camera")
    return [platform for platform in PLATFORM_ORDER if platform in found]


def exclusion_reason(description: Any, allowed: set[str] | None = None) -> str | None:
    text = str(description or "").lower()
    candidates: list[str] = []
    if re.search(r"distributor|reseller|dealer|sales agent", text):
        candidates.append("distributor_only")
    if re.search(r"consult|service|operates? rented|analytics dashboard|no hardware", text):
        candidates.append("service_only")
    if re.search(r"sensor-only|probe-only|sensor only|probes? for integration", text):
        candidates.extend(["sensor_vendor_only", "sensor_only"])
    if re.search(r"research|university|lab-only|student", text):
        candidates.append("research_only")
    candidates.append("not_target_market")
    for candidate in candidates:
        if allowed is None or candidate in allowed:
            return candidate
    return None


def classify_exhibitor(record: dict[str, Any], allowed_reasons: set[str] | None = None) -> dict[str, Any]:
    description = record.get("description", "")
    reason = exclusion_reason(description, allowed_reasons)
    platforms = classify_platforms(description)
    if reason in {"distributor_only", "service_only", "sensor_vendor_only", "sensor_only", "research_only"}:
        platforms = []
    elif platforms:
        reason = None
    return {
        "company_id": record.get("company_id"),
        "company_name": record.get("company_name"),
        "qualified": bool(platforms),
        "platforms": platforms,
        "exclusion_reason": reason,
    }


def duplicate_key(row: dict[str, Any]) -> str:
    email = normalize_email(row.get("email"))
    if email:
        return f"email:{email}"
    phone = normalize_phone(row.get("phone"))
    if phone:
        return f"phone:{phone}"
    return ""


def winner_sort_key(row: dict[str, Any]) -> tuple[int, str, str]:
    return (
        SOURCE_RANK.get(str(row.get("source_name") or ""), 0),
        str(row.get("captured_at") or ""),
        str(row.get("row_id") or ""),
    )


def read_stdin_json() -> Any:
    return json.load(sys.stdin)


def print_json(value: Any) -> None:
    json.dump(value, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")


def fetch_json(base_url: str, path: str) -> Any:
    base = base_url.rstrip("/")
    target = path if path.startswith("http://") or path.startswith("https://") else f"{base}/{path.lstrip('/')}"
    request = urllib.request.Request(target, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise SystemExit(f"GET {target} failed with HTTP {exc.code}: {body}") from exc


def cmd_fetch(args: argparse.Namespace) -> None:
    result = {path: fetch_json(args.base_url, path) for path in args.paths}
    print_json(result)


def cmd_normalize_contacts(_: argparse.Namespace) -> None:
    rows = read_stdin_json()
    if isinstance(rows, dict):
        rows = [rows]
    output = []
    for row in rows:
        item = dict(row)
        item["normalized_email"] = normalize_email(row.get("email"))
        item["normalized_phone"] = normalize_phone(row.get("phone"))
        item["duplicate_key"] = duplicate_key(row)
        output.append(item)
    print_json(output)


def cmd_classify_exhibitors(args: argparse.Namespace) -> None:
    rows = read_stdin_json()
    allowed = set(args.allowed_reason or []) or None
    print_json([classify_exhibitor(row, allowed) for row in rows])


def cmd_pick_duplicate_winners(_: argparse.Namespace) -> None:
    rows = read_stdin_json()
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        key = duplicate_key(row)
        if key:
            groups.setdefault(key, []).append(row)
    result = []
    for key, members in sorted(groups.items()):
        if len(members) < 2:
            continue
        winner = max(members, key=winner_sort_key)
        removed = sorted(str(row.get("row_id")) for row in members if row is not winner)
        result.append({"key": key, "winner_row_id": winner.get("row_id"), "removed_row_ids": removed})
    print_json(result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HarborCRM task helper utilities")
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser("fetch", help="Fetch one or more JSON API paths")
    fetch.add_argument("base_url")
    fetch.add_argument("paths", nargs="+")
    fetch.set_defaults(func=cmd_fetch)

    norm = sub.add_parser("normalize-contacts", help="Normalize email/phone fields from JSON rows on stdin")
    norm.set_defaults(func=cmd_normalize_contacts)

    classify = sub.add_parser("classify-exhibitors", help="Classify exhibitor platform coverage from JSON rows on stdin")
    classify.add_argument("--allowed-reason", action="append", help="Allowed exclusion reason enum; repeat as needed")
    classify.set_defaults(func=cmd_classify_exhibitors)

    dupes = sub.add_parser("pick-duplicate-winners", help="Summarize duplicate keys and preferred winners from rows on stdin")
    dupes.set_defaults(func=cmd_pick_duplicate_winners)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
