"""Canonicalization helpers tuned to the Asteria hub data shapes.

Transferable across all Asteria Fleet Data Quality Hub tasks. The hub exposes
contact/transaction/event fields with intentional format noise: emails vary in
case/whitespace, phones carry spurious country codes and punctuation, names vary
in case/whitespace. The canonical forms below match the ones the hub's
authoritative / verified source rows already use.

No task-specific data, no credentials, no hub access.
"""
import re
import unicodedata

# Sentinel values the hub uses to mean "missing" for email/phone/name/city.
PLACEHOLDER = {"", "null", "none", "n/a", "na", "n.a.", "-", "n.a", "NULL", "None", "N/A"}


def _clean(v):
    """NFKC-normalize + strip; treat placeholder sentinels as missing."""
    if v is None:
        return None
    s = unicodedata.normalize("NFKC", str(v)).strip()
    return None if s.lower() in PLACEHOLDER else s


def norm_email(raw):
    """Lowercase, trimmed, NFKC email — or None if absent/placeholder."""
    s = _clean(raw)
    return None if s is None else s.lower()


def phone_digits(raw):
    """Canonical 10-digit phone, stripping spurious leading country codes
    (+1/+44/+21/0) from 11-digit forms. None if absent/placeholder."""
    s = _clean(raw)
    if s is None:
        return None
    d = re.sub(r"[^0-9]", "", s)
    for cc in ("1", "44", "21", "0"):
        if len(d) == 11 and d.startswith(cc) and cc != "0":
            d2 = d[1:]
            if len(d2) == 10:
                d = d2
                break
        elif d.startswith("0") and len(d) == 11:
            d = d[1:]
            break
    return d if d else None


def norm_name(raw):
    """Whitespace-collapsed, title-cased name — or None."""
    s = _clean(raw)
    if s is None:
        return None
    s = re.sub(r"\s+", " ", s)
    return s.title()


def norm_city(raw):
    """Trimmed, NFKC city/region/token — or None."""
    return _clean(raw)


def email_token(raw):
    """Stable identity token = trailing integer in the local-part of a clean
    `@example-fleet.com` email (e.g. 'sofia.smith.0' -> '0'). Returns None for
    placeholder emails or for `.part.NNN` / `.fiel.NNN` `@mail.example` decoys
    (their domain is not @example-fleet.com, so they correctly do NOT share a
    token with a clean person). See SKILL.md §5 Contacts step 1."""
    e = norm_email(raw)
    if e is None or "@example-fleet.com" not in e:
        return None
    local = e.split("@")[0]
    m = re.search(r"(\d+)$", local)
    return m.group(1) if m else None


def is_usable_contact(email_raw, phone_raw):
    """True when a row/cluster has at least one usable contact channel."""
    return bool(norm_email(email_raw) or phone_digits(phone_raw))
