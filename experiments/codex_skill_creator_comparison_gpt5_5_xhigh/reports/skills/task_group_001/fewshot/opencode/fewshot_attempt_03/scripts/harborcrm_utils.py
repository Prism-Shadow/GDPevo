#!/usr/bin/env python3
"""Generic helpers for HarborCRM reconciliation tasks."""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
import urllib.parse
import urllib.request
from typing import Any, Iterable


PLATFORM_ORDER = ["AUV", "ROV", "Underwater Camera"]

SOURCE_PRIORITY = {
    "partner_upload": 60,
    "sponsor_form": 55,
    "exhibitor_form": 55,
    "badge_scan": 50,
    "webinar_form": 40,
    "manual_upload": 30,
}


def normalize_email(value: Any) -> str:
    return str(value or "").strip().lower()


def normalize_phone(value: Any) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def normalize_name(value: Any) -> str:
    text = str(value or "").strip().lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def add_days(date_string: str, days: int) -> str:
    base = _dt.date.fromisoformat(date_string)
    return (base + _dt.timedelta(days=int(days))).isoformat()


def fetch_json(base_url: str, path: str) -> Any:
    base = base_url.rstrip("/") + "/"
    url = urllib.parse.urljoin(base, path.lstrip("/"))
    with urllib.request.urlopen(url, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def email_domain(email: Any) -> str:
    email_text = normalize_email(email)
    if "@" not in email_text:
        return ""
    return email_text.rsplit("@", 1)[1]


def website_domain(url_or_domain: Any) -> str:
    text = str(url_or_domain or "").strip().lower()
    if not text:
        return ""
    parsed = urllib.parse.urlparse(text if "://" in text else "https://" + text)
    domain = parsed.netloc or parsed.path
    if domain.startswith("www."):
        domain = domain[4:]
    return domain.rstrip("/")


def sorted_platforms(platforms: Iterable[str]) -> list[str]:
    present = {p for p in platforms if p in PLATFORM_ORDER}
    return [p for p in PLATFORM_ORDER if p in present]


def infer_platforms(*texts: Any) -> list[str]:
    text = " ".join(str(t or "") for t in texts).lower()
    platforms: set[str] = set()
    if re.search(r"\bauv\b|autonomous underwater|autonomous .*drone|subsurface drone", text):
        platforms.add("AUV")
    if re.search(r"\brov\b|remotely operated|inspection rov|cleaning rov", text):
        platforms.add("ROV")
    if re.search(r"underwater camera|camera module|camera array|low-light inspection|camera manufacturer", text):
        platforms.add("Underwater Camera")
    return sorted_platforms(platforms)


def classify_exclusion(*texts: Any) -> str:
    text = " ".join(str(t or "") for t in texts).lower()
    if re.search(r"distributor|dealer|reseller|sales agent|supply", text):
        return "distributor_only"
    if re.search(r"consult|service|operator|rented|dashboard|analytics", text):
        return "service_only"
    if re.search(r"sensor-only|sensor only|probe|salinity|oxygen sensor", text):
        return "sensor_vendor_only"
    if re.search(r"research|university|college|lab\b", text):
        return "research_only"
    return "not_target_market"


def priority_tier(requested_demo: Any, interest_score: Any) -> str:
    score = int(interest_score or 0)
    demo = bool(requested_demo)
    if demo and score >= 90:
        return "A"
    if demo and score >= 80:
        return "B"
    return "C"


def duplicate_key(row: dict[str, Any]) -> str:
    email = normalize_email(row.get("email"))
    if email:
        return "email:" + email
    phone = normalize_phone(row.get("phone"))
    if phone:
        return "phone:" + phone
    return ""


def row_quality(row: dict[str, Any]) -> tuple[int, int, str, str]:
    completeness = int(bool(normalize_email(row.get("email")))) + int(bool(normalize_phone(row.get("phone"))))
    source_score = SOURCE_PRIORITY.get(str(row.get("source_name") or ""), 0)
    captured_at = str(row.get("captured_at") or "")
    row_id = str(row.get("row_id") or "")
    return (completeness, source_score, captured_at, row_id)


def select_duplicate_winner(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("rows must not be empty")
    return max(rows, key=row_quality)


def top_level_keys_from_template(template: dict[str, Any]) -> list[str]:
    if isinstance(template.get("required_top_level_keys"), list):
        return list(template["required_top_level_keys"])
    ignored = {"description", "task_id", "schema_name", "schema_version", "fields", "field_spec", "field_definitions", "ordering_rules", "numeric_precision", "response_rules"}
    keys = [key for key in template.keys() if key not in ignored]
    return keys


def check_top_level(answer_path: str, template_path: str) -> int:
    with open(answer_path, "r", encoding="utf-8") as f:
        answer = json.load(f)
    with open(template_path, "r", encoding="utf-8") as f:
        template = json.load(f)
    expected = top_level_keys_from_template(template)
    actual = list(answer.keys())
    missing = [key for key in expected if key not in answer]
    extra = [key for key in actual if key not in expected]
    result = {"expected_top_level_keys": expected, "actual_top_level_keys": actual, "missing": missing, "extra": extra}
    print(json.dumps(result, indent=2))
    return 1 if missing or extra else 0


def cmd_fetch(args: argparse.Namespace) -> int:
    output = {path: fetch_json(args.base_url, path) for path in args.paths}
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


def cmd_normalize(args: argparse.Namespace) -> int:
    result: dict[str, Any] = {}
    if args.email is not None:
        result["email"] = normalize_email(args.email)
        result["email_domain"] = email_domain(args.email)
    if args.phone is not None:
        result["phone"] = normalize_phone(args.phone)
    if args.website is not None:
        result["website_domain"] = website_domain(args.website)
    if args.date is not None:
        result["date_plus_days"] = add_days(args.date, args.days or 0)
    if args.text:
        result["platforms"] = infer_platforms(*args.text)
        result["exclusion_reason"] = classify_exclusion(*args.text)
    print(json.dumps(result, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HarborCRM reconciliation helpers")
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser("fetch", help="Fetch JSON from one or more API paths")
    fetch.add_argument("base_url")
    fetch.add_argument("paths", nargs="+")
    fetch.set_defaults(func=cmd_fetch)

    normalize = sub.add_parser("normalize", help="Normalize contact facts or infer simple classifications")
    normalize.add_argument("--email")
    normalize.add_argument("--phone")
    normalize.add_argument("--website")
    normalize.add_argument("--date")
    normalize.add_argument("--days", type=int, default=0)
    normalize.add_argument("--text", action="append", default=[])
    normalize.set_defaults(func=cmd_normalize)

    check = sub.add_parser("check", help="Check answer top-level keys against a template")
    check.add_argument("answer_json")
    check.add_argument("template_json")
    check.set_defaults(func=lambda args: check_top_level(args.answer_json, args.template_json))
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
