#!/usr/bin/env python3
"""Reusable helpers for HarborCRM JSON handoff tasks."""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
from typing import Iterable


PLATFORM_ORDER = ("AUV", "ROV", "Underwater Camera")
SOURCE_PRIORITY = {
    "sponsor_form": 60,
    "partner_upload": 50,
    "exhibitor_form": 40,
    "badge_scan": 30,
    "webinar_form": 20,
    "manual_upload": 10,
}


def normalize_email(value: object) -> str:
    return str(value or "").strip().lower()


def normalize_phone(value: object) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def normalize_name(value: object) -> str:
    text = str(value or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    words = [
        word
        for word in text.split()
        if word not in {"inc", "llc", "ltd", "limited", "corp", "corporation", "co", "company"}
    ]
    return " ".join(words)


def add_days(date_text: str, days: int) -> str:
    date = _dt.date.fromisoformat(date_text)
    return (date + _dt.timedelta(days=int(days))).isoformat()


def platform_coverage(*texts: object) -> list[str]:
    blob = " ".join(str(text or "") for text in texts).lower()
    hits: set[str] = set()
    if re.search(r"\bauv\b|autonomous underwater|underwater drone", blob):
        hits.add("AUV")
    if re.search(r"\brov\b|remotely operated|inspection-class", blob):
        hits.add("ROV")
    if re.search(r"underwater camera|camera module|camera array|camera manufacturer|low-light inspection", blob):
        hits.add("Underwater Camera")
    return [platform for platform in PLATFORM_ORDER if platform in hits]


def exclusion_reason(text: object, allowed: Iterable[str] = ()) -> str | None:
    blob = str(text or "").lower()
    allowed_set = set(allowed)
    if re.search(r"distributor|dealer|reseller|sales agent|supply", blob):
        return "distributor_only" if not allowed_set or "distributor_only" in allowed_set else None
    if re.search(r"service|consult|operate|operator|rented|analytics dashboard", blob):
        return "service_only" if not allowed_set or "service_only" in allowed_set else None
    if re.search(r"sensor-only|sensor only|probe", blob):
        if "sensor_vendor_only" in allowed_set:
            return "sensor_vendor_only"
        if "sensor_only" in allowed_set:
            return "sensor_only"
        return "sensor_vendor_only" if not allowed_set else None
    if re.search(r"research|academic|university|lab\b", blob):
        return "research_only" if not allowed_set or "research_only" in allowed_set else None
    return "not_target_market" if "not_target_market" in allowed_set else None


def default_priority_tier(requested_demo: bool, interest_score: int | str | None) -> str:
    score = int(interest_score or 0)
    if requested_demo and score >= 90:
        return "A"
    if requested_demo and score >= 80:
        return "B"
    return "C"


def duplicate_key(email: object, phone: object) -> str:
    email_key = normalize_email(email)
    if email_key:
        return f"email:{email_key}"
    phone_key = normalize_phone(phone)
    if phone_key:
        return f"phone:{phone_key}"
    return ""


def dedupe_sort_key(row: dict) -> tuple[int, str, str]:
    source_score = SOURCE_PRIORITY.get(str(row.get("source_name") or ""), 0)
    captured_at = str(row.get("captured_at") or "")
    row_id = str(row.get("row_id") or "")
    return (source_score, captured_at, row_id)


def choose_duplicate_winner(rows: Iterable[dict]) -> dict:
    return max(rows, key=dedupe_sort_key)


def _main() -> None:
    parser = argparse.ArgumentParser(description="HarborCRM helper utilities")
    parser.add_argument("--email", default="")
    parser.add_argument("--phone", default="")
    parser.add_argument("--text", action="append", default=[])
    parser.add_argument("--date")
    parser.add_argument("--days", type=int, default=0)
    args = parser.parse_args()

    output = {
        "email": normalize_email(args.email),
        "phone": normalize_phone(args.phone),
        "platforms": platform_coverage(*args.text),
    }
    if args.date:
        output["date_plus_days"] = add_days(args.date, args.days)
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    _main()
