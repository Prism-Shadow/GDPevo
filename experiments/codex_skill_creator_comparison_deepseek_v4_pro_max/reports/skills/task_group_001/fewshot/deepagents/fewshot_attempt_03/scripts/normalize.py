#!/usr/bin/env python3
"""
HarborCRM contact field normalization utility.

Normalizes email addresses (lowercase, trim) and phone numbers (digits only)
for consistent deduplication and CRM matching across all HarborCRM task types.

Usage:
  echo '{"email":" User@Example.Com ","phone":"+1 (415) 555-0188"}' | python normalize.py
  python normalize.py '{"email":" User@Example.Com ","phone":"+1 (415) 555-0188"}'
"""
import re
import sys
import json


def normalize_email(email):
    """Normalize email: lowercase, trim whitespace. Empty string for None/empty."""
    if email is None:
        return ""
    return email.strip().lower()


def normalize_phone(phone):
    """Normalize phone: extract digits only. Empty string if no digits found."""
    if phone is None:
        return ""
    digits = re.sub(r"\D", "", phone.strip())
    return digits


def main():
    if len(sys.argv) > 1:
        data = json.loads(sys.argv[1])
    else:
        data = json.load(sys.stdin)

    result = {}
    if "email" in data:
        result["email"] = normalize_email(data["email"])
    elif "emails" in data:
        result["emails"] = [normalize_email(e) for e in data["emails"]]
    if "phone" in data:
        result["phone"] = normalize_phone(data["phone"])
    elif "phones" in data:
        result["phones"] = [normalize_phone(p) for p in data["phones"]]

    print(json.dumps(result))


if __name__ == "__main__":
    main()
