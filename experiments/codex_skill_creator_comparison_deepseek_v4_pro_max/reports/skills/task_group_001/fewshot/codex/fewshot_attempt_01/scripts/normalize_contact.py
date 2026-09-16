#!/usr/bin/env python3
"""
Deterministic contact normalizer for HarborCRM.

Usage:
    python3 normalize_contact.py --email " jane.doe@example.com " --phone "(415) 555-0188"

    echo '{"email":"JOHN.SMITH@generic.example","phone":"+1 206 555 0177"}' | python3 normalize_contact.py --stdin
"""

import argparse
import json
import re
import sys


def normalize_email(raw):
    if raw is None:
        return ""
    trimmed = str(raw).strip()
    if not trimmed:
        return ""
    return trimmed.lower()


def normalize_phone(raw):
    if raw is None:
        return ""
    digits = re.sub(r"[^0-9]", "", str(raw))
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits


def normalize(raw_email, raw_phone):
    return {
        "email": normalize_email(raw_email),
        "phone": normalize_phone(raw_phone),
    }


def main():
    parser = argparse.ArgumentParser(description="Normalize a contact email and phone.")
    parser.add_argument("--email", default=None, help="Raw email string")
    parser.add_argument("--phone", default=None, help="Raw phone string")
    parser.add_argument("--stdin", action="store_true",
                        help="Read JSON object from stdin with keys email and phone")
    args = parser.parse_args()

    if args.stdin:
        data = json.load(sys.stdin)
        result = normalize(data.get("email"), data.get("phone"))
    else:
        result = normalize(args.email, args.phone)

    print(json.dumps(result))


if __name__ == "__main__":
    main()
