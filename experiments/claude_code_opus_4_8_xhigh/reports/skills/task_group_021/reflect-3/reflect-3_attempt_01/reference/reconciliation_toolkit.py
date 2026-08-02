"""
Reusable, connection-agnostic helpers for Asteria Fleet Data Quality Hub tasks.

Pure functions only: no network calls, no hard-coded endpoints/credentials, no answer values.
Fetch rows however the task's access file specifies, hand plain dict rows to these helpers.
Row = a dict with the logical-view column names (see reference/data_model.md).
"""
import re
import unicodedata
from collections import defaultdict, Counter

SENTINELS = {"", "n/a", "none", "null", "nat"}

# ---------- text / contact normalization ----------
def normalize_email(e):
    """NFKC -> strip -> lowercase; None for blanks/sentinels/non-emails."""
    if e is None:
        return None
    e = unicodedata.normalize("NFKC", str(e)).strip().lower()
    if e in SENTINELS:
        return None
    return e if "@" in e else None

def normalize_phone(p):
    """Digits only; None if no digits or a sentinel."""
    if p is None:
        return None
    if str(p).strip().lower() in SENTINELS:
        return None
    d = re.sub(r"\D", "", str(p))
    return d or None

def display_name(name):
    """Unicode-preserving, trimmed, Title-Cased display name."""
    s = unicodedata.normalize("NFKC", str(name or "")).strip()
    return " ".join(w.capitalize() for w in s.split())

def has_usable_contact(row, email_field="email", phone_field="phone"):
    return normalize_email(row.get(email_field)) is not None or \
           normalize_phone(row.get(phone_field)) is not None

# ---------- reference-alias category matching (word boundary + maximal span) ----------
def active_valid(alias, on_date):
    """alias: dict(reference_status, valid_from, valid_to). on_date: 'YYYY-MM-DD'."""
    if alias.get("reference_status") != "ACTIVE":
        return False
    vf, vt = alias.get("valid_from"), alias.get("valid_to")
    if vf and on_date < vf:
        return False
    if vt and on_date > vt:
        return False
    return True

def canonical_categories(description, aliases, on_date):
    """
    Return set of distinct canonical_value matches for `description`.
    Word-boundary matches only; drop any match contained inside a longer match (maximal span).
    len==1 recognized; ==0 unrecognized; >1 ambiguous.
    aliases: iterable of dict(alias_text, canonical_value, reference_status, valid_from, valid_to)
    """
    if not description:
        return set()
    s = str(description).lower()
    spans = []
    for a in aliases:
        if not active_valid(a, on_date):
            continue
        t = str(a["alias_text"]).lower()
        for m in re.finditer(r"\b" + re.escape(t) + r"\b", s):
            spans.append((m.start(), m.end(), a["canonical_value"]))
    maximal = [m for m in spans
               if not any(n is not m and n[0] <= m[0] and m[1] <= n[1] and (n[1]-n[0]) > (m[1]-m[0])
                          for n in spans)]
    return {c for _, _, c in maximal}

# ---------- units & fx ----------
def convert_unit(value, from_unit, conversions, kind):
    """conversions: iterable of dict(kind, from_unit, factor). Returns value*factor or None."""
    if value is None:
        return None
    for c in conversions:
        if c["kind"] == kind and c["from_unit"] == from_unit:
            return value * c["factor"]
    return None

def build_fx_index(fx_rows):
    """(currency, rate_date) -> {rate_status: usd_per_unit}."""
    idx = {}
    for f in fx_rows:
        idx.setdefault((f["currency"], f["rate_date"]), {})[f["rate_status"]] = f["usd_per_unit"]
    return idx

def usd_amount(amount, currency, business_datetime, fx_index):
    """Prefer CERTIFIED rate for the row's date; USD==1.0; None if no rate."""
    if amount is None:
        return None
    if currency == "USD":
        return amount
    entry = fx_index.get((currency, str(business_datetime)[:10]))
    if not entry:
        return None
    rate = entry.get("CERTIFIED", entry.get("PROVISIONAL"))
    return None if rate is None else amount * rate

# ---------- identity resolution (contacts) ----------
def cluster_by_email(rows):
    """
    Returns (clusters, quarantined):
      clusters = list[list[row]] of usable rows sharing a normalized email;
      quarantined = list[row] with no usable contact (each its own record).
    Do NOT merge on shared phone or common name (guard false merges elsewhere).
    """
    by_email, quarantined = defaultdict(list), []
    for r in rows:
        e = normalize_email(r.get("email"))
        if e is None and normalize_phone(r.get("phone")) is None:
            quarantined.append(r)
        elif e is not None:
            by_email[e].append(r)
        else:
            quarantined.append(r)  # phone-only rows: no shared-key merge available
    return list(by_email.values()), quarantined

def shared_identifier_people(rows, key_fn):
    """Map key -> set of person-cluster ids sharing it (to detect contested/shared phones)."""
    idx = defaultdict(set)
    for pid, members in rows:
        for m in members:
            k = key_fn(m)
            if k:
                idx[k].add(pid)
    return idx

# ---------- survivorship & field-level precedence ----------
def pick_field(members, source_order, getter):
    """First non-empty value following source_order precedence; returns (value, source_system)."""
    by_src = {m["source_system"]: m for m in members}
    for s in source_order:
        if s in by_src:
            v = getter(by_src[s])
            if v not in (None, ""):
                return v, s
    for m in members:
        v = getter(m)
        if v not in (None, ""):
            return v, m["source_system"]
    return "", members[0]["source_system"]

def master_row(members, master_hint_field="master_hint"):
    """The golden row: prefer the one carrying a master_hint, then verified, then latest update."""
    def key(m):
        return (1 if m.get(master_hint_field) else 0,
                m.get("verified_flag") or 0,
                m.get("business_updated_at") or "")
    return max(members, key=key)

# ---------- misc ----------
def round2(x):
    return None if x is None else round(x + 1e-9, 2)

def summarize(counter_dict, keys):
    """Ordered dict of counts filling missing keys with 0 (for enum-complete rollups)."""
    return {k: counter_dict.get(k, 0) for k in keys}
