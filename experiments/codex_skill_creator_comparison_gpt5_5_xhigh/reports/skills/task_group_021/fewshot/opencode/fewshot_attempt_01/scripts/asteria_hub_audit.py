#!/usr/bin/env python3
"""Compute first-pass Asteria Fleet Data Quality Hub audit answers.

This helper is intentionally data-driven: it reads the task input payloads and
the live hub, then emits JSON matching the task family it detects from the
answer template. It contains reusable reconciliation rules, not example answer
records.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import math
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def parse_env(path: Path) -> str:
    base_url = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("base_url:"):
            base_url = line.split(":", 1)[1].strip()
            break
    if not base_url:
        raise SystemExit(f"could not find base_url in {path}")
    return base_url.rstrip("/")


def parse_time(value):
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def date_part(value):
    return str(value or "")[:10]


def norm_email(value):
    text = unicodedata.normalize("NFKC", str(value or "")).strip().lower()
    if "@" not in text:
        return ""
    domain = text.rsplit("@", 1)[-1]
    return text if "." in domain else ""


def phone_digits(value):
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits if len(digits) >= 7 else ""


def norm_name(value):
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).strip().casefold().split())


def display_name(value):
    text = " ".join(unicodedata.normalize("NFKC", str(value or "")).strip().split())
    return text.title()


class Hub:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self._cache = {}

    def fetch_pages(self, endpoint: str, **params):
        key = (endpoint, tuple(sorted((k, str(v)) for k, v in params.items())))
        if key in self._cache:
            return list(self._cache[key])
        items = []
        offset = 0
        while True:
            query = {k: v for k, v in params.items() if v is not None}
            query["offset"] = offset
            url = f"{self.base_url}{endpoint}?{urllib.parse.urlencode(query)}"
            with urllib.request.urlopen(url) as resp:
                payload = json.load(resp)
            if "error" in payload:
                raise RuntimeError(f"{endpoint} returned error: {payload['error']}")
            batch = payload.get("items", [])
            items.extend(batch)
            total = int(payload.get("total", len(items)))
            limit = int(payload.get("limit", len(batch) or 100))
            if len(items) >= total or not batch:
                break
            offset += limit
        self._cache[key] = list(items)
        return items

    def snapshots(self, collection_id):
        return self.fetch_pages("/api/source-snapshots", collection=collection_id)

    def authoritative_snapshot_id(self, collection_id):
        snapshots = self.snapshots(collection_id)
        certified = [s for s in snapshots if s.get("snapshot_status") == "CERTIFIED"]
        if certified:
            certified.sort(key=lambda s: (s.get("business_cutoff") or "", s.get("ingested_at") or ""), reverse=True)
            return certified[0]["snapshot_id"]
        snapshots.sort(key=lambda s: (s.get("ingested_at") or "", s.get("snapshot_id") or ""), reverse=True)
        return snapshots[0]["snapshot_id"] if snapshots else None


class DSU:
    def __init__(self, ids):
        self.parent = {i: i for i in ids}

    def find(self, item):
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left, right):
        lroot = self.find(left)
        rroot = self.find(right)
        if lroot != rroot:
            self.parent[rroot] = lroot


def source_rankers():
    def contact_rank(source):
        if source in {"Identity Registry", "Compliance Master"}:
            return 0
        if "Registry" in source or "Compliance" in source:
            return 0
        if "Dispatch" in source or source == "CRM" or "Dealer Service" in source:
            return 1
        return 2

    def name_rank(source):
        preferred = ("HR", "Warranty", "Dealer Portal", "Partner Portal", "Marketing")
        if any(token in source for token in preferred):
            return 0
        if "Dispatch" in source or "Dealer Service" in source or source == "CRM":
            return 1
        return 2

    def depot_rank(source):
        if "HR" in source or "Compliance" in source:
            return 0
        if "Warranty" in source or "Dealer Portal" in source or "Partner Portal" in source:
            return 1
        return 2

    return contact_rank, name_rank, depot_rank


def build_contact_clusters(rows):
    ids = [r["row_id"] for r in rows]
    dsu = DSU(ids)
    by_email = collections.defaultdict(list)
    by_phone_name = collections.defaultdict(list)
    for row in rows:
        email = norm_email(row.get("email"))
        phone = phone_digits(row.get("phone"))
        name = norm_name(row.get("person_or_org_name"))
        if email:
            by_email[email].append(row["row_id"])
        if phone and name:
            by_phone_name[(phone, name)].append(row["row_id"])
    for groups in (by_email, by_phone_name):
        for members in groups.values():
            for member in members[1:]:
                dsu.union(members[0], member)

    by_id = {r["row_id"]: r for r in rows}
    grouped = collections.defaultdict(list)
    for row in rows:
        grouped[dsu.find(row["row_id"])].append(row)

    contact_rank, name_rank, depot_rank = source_rankers()
    clusters = []
    row_to_cluster = {}
    for members in grouped.values():
        members.sort(key=lambda r: r["row_id"])

        def best(field, kind):
            ranker = {"contact": contact_rank, "name": name_rank, "depot": depot_rank}[kind]
            candidates = []
            for row in members:
                raw = row.get(field)
                if field == "email":
                    value = norm_email(raw)
                    ok = bool(value)
                elif field == "phone":
                    value = phone_digits(raw)
                    ok = bool(value)
                else:
                    value = raw
                    ok = raw is not None and str(raw).strip() != ""
                if ok:
                    candidates.append(
                        (
                            ranker(row["source_system"]),
                            -int(row.get("verified_flag") or 0),
                            row.get("business_updated_at") or "",
                            row["row_id"],
                            value,
                            row,
                        )
                    )
            if not candidates:
                return "", None
            candidates.sort()
            return candidates[0][4], candidates[0][5]

        email, email_row = best("email", "contact")
        phone, phone_row = best("phone", "contact")
        consent, consent_row = best("consent_status", "contact")
        status, status_row = best("record_status", "contact")
        name, name_row = best("person_or_org_name", "name")
        city, city_row = best("city", "depot")
        region, region_row = best("region", "depot")

        master_candidates = []
        for row in members:
            master_candidates.append(
                (
                    0 if row.get("master_hint") else 1,
                    contact_rank(row["source_system"]),
                    row["row_id"],
                    row,
                )
            )
        master_candidates.sort()
        master = master_candidates[0][3]
        cluster = {
            "rows": members,
            "member_row_ids": [r["row_id"] for r in members],
            "master_id": master["row_id"],
            "canonical_name": display_name(name),
            "canonical_email": email,
            "canonical_phone_digits": phone,
            "canonical_city": str(city).strip() if city else "",
            "depot_code": str(region).strip() if region else "",
            "canonical_consent_status": str(consent or "UNKNOWN"),
            "canonical_record_status": str(status or "ACTIVE"),
            "name_source_system": name_row["source_system"] if name_row else None,
            "contact_source_system": (email_row or phone_row or {}).get("source_system"),
            "depot_source_system": (region_row or city_row or {}).get("source_system"),
            "consent_source_system": consent_row["source_system"] if consent_row else None,
        }
        clusters.append(cluster)
        for row in members:
            row_to_cluster[row["row_id"]] = cluster
    clusters.sort(key=lambda c: c["master_id"])
    return by_id, clusters, row_to_cluster


def usable_contact(cluster):
    return bool(cluster["canonical_email"] or cluster["canonical_phone_digits"])


def dispatchable(cluster):
    return (
        cluster["canonical_record_status"] == "ACTIVE"
        and usable_contact(cluster)
        and cluster["canonical_consent_status"] == "GRANTED"
    )


def outreach_code_for_cluster(cluster):
    if not usable_contact(cluster):
        return "OR-60"
    if cluster["canonical_record_status"] != "ACTIVE":
        return "OR-15"
    if cluster["canonical_consent_status"] == "GRANTED":
        return "OR-35"
    return "OR-80"


def field_code_for_clusters(clusters):
    if any(not usable_contact(c) for c in clusters):
        return "FP-75"
    if any(len(c["member_row_ids"]) > 1 for c in clusters):
        return "FP-55"
    return "FP-20"


def identity_code_for_evidence(rows, row_to_cluster):
    clusters = {id(row_to_cluster[r["row_id"]]): row_to_cluster[r["row_id"]] for r in rows}
    cluster_list = list(clusters.values())
    if len(cluster_list) == 1 and len(cluster_list[0]["member_row_ids"]) > 1:
        return "IC-70"
    if len(rows) == 1 and not usable_contact(row_to_cluster[rows[0]["row_id"]]):
        return "IC-40"
    names = {norm_name(r.get("person_or_org_name")) for r in rows if norm_name(r.get("person_or_org_name"))}
    emails = {norm_email(r.get("email")) for r in rows if norm_email(r.get("email"))}
    phones = {phone_digits(r.get("phone")) for r in rows if phone_digits(r.get("phone"))}
    if len(rows) > 1 and (len(names) == 1 or not emails or len(emails) > 1 and len(names) == 1):
        return "IC-90"
    if len(rows) > 1 and len(phones) == 1 and len(names) > 1:
        return "IC-25"
    return "IC-25"


def contested_identifier(row, rows):
    phone = phone_digits(row.get("phone"))
    hint = row.get("master_hint")
    if not phone and not hint:
        return False
    names = set()
    for other in rows:
        same_phone = phone and phone_digits(other.get("phone")) == phone
        same_hint = hint and other.get("master_hint") == hint
        if same_phone or same_hint:
            names.add(norm_name(other.get("person_or_org_name")))
    return len(names) > 1


def solve_partner_contacts(hub, scope):
    collection = scope["collection_id"]
    rows = hub.fetch_pages("/api/contacts", collection=collection)
    by_id, clusters, row_to_cluster = build_contact_clusters(rows)
    quarantine_rows = sorted(r["row_id"] for r in rows if not norm_email(r.get("email")) and not phone_digits(r.get("phone")))
    duplicate_count = sum(1 for c in clusters if len(c["member_row_ids"]) > 1)
    canonical_count = len(clusters)
    readiness = collections.Counter()
    eligible_count = 0
    for cluster in clusters:
        if cluster["canonical_record_status"] == "ACTIVE" and usable_contact(cluster):
            eligible_count += 1
            if cluster["canonical_consent_status"] == "GRANTED":
                if cluster["canonical_email"] and cluster["canonical_phone_digits"]:
                    readiness["both"] += 1
                elif cluster["canonical_email"]:
                    readiness["email_only"] += 1
                else:
                    readiness["phone_only"] += 1
            else:
                readiness["not_ready"] += 1

    focus = []
    focus_codes = []
    for item in sorted(scope["focus_clusters"], key=lambda x: x["cluster_id"]):
        cluster = row_to_cluster[item["seed_row_id"]]
        focus.append(
            {
                "cluster_id": item["cluster_id"],
                "member_row_ids": sorted(cluster["member_row_ids"]),
                "survivor_row_id": cluster["master_id"],
                "canonical_email": cluster["canonical_email"],
                "canonical_phone_digits": cluster["canonical_phone_digits"],
                "canonical_city": cluster["canonical_city"],
                "city_source_system": cluster["depot_source_system"],
            }
        )
        focus_codes.append(
            {
                "cluster_id": item["cluster_id"],
                "identity_code": identity_code_for_evidence(cluster["rows"], row_to_cluster),
                "field_provenance_code": field_code_for_clusters([cluster]),
            }
        )

    anchored = []
    for case in sorted(scope.get("control_case_anchors", []), key=lambda x: x["case_id"]):
        evidence = [by_id[rid] for rid in case["seed_row_ids"]]
        evidence_clusters = [row_to_cluster[r["row_id"]] for r in evidence]
        anchored.append(
            {
                "case_id": case["case_id"],
                "identity_code": identity_code_for_evidence(evidence, row_to_cluster),
                "outreach_code": max((outreach_code_for_cluster(c) for c in evidence_clusters), key=["OR-35", "OR-80", "OR-15", "OR-60"].index),
                "field_provenance_code": field_code_for_clusters(evidence_clusters),
            }
        )

    region_rollup = collections.Counter(c["depot_code"] for c in clusters)
    quarantine_rate = round(len(quarantine_rows) / canonical_count, 4) if canonical_count else 0
    thresholds = scope.get("status_thresholds", {})
    if quarantine_rate <= thresholds.get("pass_max_quarantine_rate", 0):
        status = "PASS"
    elif quarantine_rate <= thresholds.get("pass_with_exceptions_max_quarantine_rate", 0):
        status = "PASS_WITH_EXCEPTIONS"
    else:
        status = "HOLD"
    action = scope.get("status_action_map", {}).get(status, {"PASS": "RELEASE", "PASS_WITH_EXCEPTIONS": "REVIEW_EXCEPTIONS", "HOLD": "BLOCK_AND_REMEDIATE"}[status])
    return {
        "quality_summary": {
            "raw_row_count": len(rows),
            "canonical_entity_count": canonical_count,
            "readiness_eligible_entity_count": eligible_count,
            "duplicate_cluster_count": duplicate_count,
            "quarantine_rate": quarantine_rate,
        },
        "focus_clusters": focus,
        "quarantine_row_ids": quarantine_rows,
        "channel_readiness": {
            "both": readiness["both"],
            "email_only": readiness["email_only"],
            "phone_only": readiness["phone_only"],
            "not_ready": readiness["not_ready"],
        },
        "control_codes": {
            "focus_decisions": focus_codes,
            "anchored_cases": anchored,
            "quarantine_result": {
                "identity_code": "IC-40",
                "outreach_code": "OR-60",
                "field_provenance_code": "FP-75",
            },
            "readiness_partition": {
                "both": "OR-35",
                "email_only": "OR-35",
                "phone_only": "OR-35",
                "not_ready": "OR-80",
            },
            "inactive_exclusion": {"outreach_code": "OR-15"},
        },
        "region_rollup": [{"region": k, "canonical_entity_count": region_rollup[k]} for k in sorted(region_rollup)],
        "certification_status": {"status": status, "next_action": action},
    }


def solve_roster_contacts(hub, scope):
    collection = scope["collection_id"]
    rows = hub.fetch_pages("/api/contacts", collection=collection)
    by_id, clusters, row_to_cluster = build_contact_clusters(rows)
    quarantine_rows = sorted(r["row_id"] for r in rows if not norm_email(r.get("email")) and not phone_digits(r.get("phone")))
    duplicate_count = sum(1 for c in clusters if len(c["member_row_ids"]) > 1)
    dispatch_ids = sorted(c["master_id"] for c in clusters if dispatchable(c))
    contested = []
    for case in scope.get("identifier_watchlist", []):
        row = by_id[case["source_row_anchor"]]
        if contested_identifier(row, rows):
            contested.append(case["identifier_case_id"])

    focus = []
    for item in sorted(scope["focus_people"], key=lambda x: x["focus_person_id"]):
        cluster = row_to_cluster[item["source_row_anchor"]]
        outcome = "SINGLE_SOURCE"
        if len(cluster["member_row_ids"]) > 1:
            outcome = "FIELD_LEVEL_PRECEDENCE_APPLIED"
        elif not usable_contact(cluster):
            outcome = "NO_USABLE_CONTACT"
        focus.append(
            {
                "focus_person_id": item["focus_person_id"],
                "source_row_anchor": item["source_row_anchor"],
                "member_row_ids": sorted(cluster["member_row_ids"]),
                "master_id": cluster["master_id"],
                "canonical_name": cluster["canonical_name"],
                "canonical_email": cluster["canonical_email"],
                "canonical_phone_digits": cluster["canonical_phone_digits"],
                "canonical_city": cluster["canonical_city"],
                "depot_code": cluster["depot_code"],
                "canonical_consent_status": cluster["canonical_consent_status"],
                "canonical_record_status": cluster["canonical_record_status"],
                "name_source_system": cluster["name_source_system"],
                "contact_source_system": cluster["contact_source_system"],
                "depot_source_system": cluster["depot_source_system"],
                "consent_source_system": cluster["consent_source_system"],
                "resolution_outcome": outcome,
            }
        )

    depot_counts = collections.defaultdict(collections.Counter)
    for cluster in clusters:
        depot = cluster["depot_code"]
        depot_counts[depot]["total_person_count"] += 1
        if not usable_contact(cluster):
            depot_counts[depot]["blocked_no_contact_count"] += 1
        elif cluster["canonical_record_status"] != "ACTIVE":
            depot_counts[depot]["blocked_inactive_count"] += 1
        elif cluster["canonical_consent_status"] == "GRANTED":
            depot_counts[depot]["dispatchable_person_count"] += 1
        else:
            depot_counts[depot]["blocked_consent_count"] += 1
    readiness_by_depot = []
    for depot in sorted(depot_counts):
        counts = depot_counts[depot]
        readiness_by_depot.append(
            {
                "depot_code": depot,
                "total_person_count": counts["total_person_count"],
                "dispatchable_person_count": counts["dispatchable_person_count"],
                "blocked_consent_count": counts["blocked_consent_count"],
                "blocked_no_contact_count": counts["blocked_no_contact_count"],
                "blocked_inactive_count": counts["blocked_inactive_count"],
            }
        )

    controls = []
    for case in sorted(scope.get("policy_control_cases", []), key=lambda x: x["control_case_id"]):
        evidence = [by_id[rid] for rid in sorted(case["evidence_row_ids"])]
        evidence_clusters = [row_to_cluster[r["row_id"]] for r in evidence]
        family = case["control_family"]
        if family == "IDENTITY":
            code = identity_code_for_evidence(evidence, row_to_cluster)
        elif family == "OUTREACH":
            code = max((outreach_code_for_cluster(c) for c in evidence_clusters), key=["OR-35", "OR-80", "OR-15", "OR-60"].index)
        else:
            code = field_code_for_clusters(evidence_clusters)
        controls.append(
            {
                "control_case_id": case["control_case_id"],
                "control_family": family,
                "evidence_row_ids": sorted(case["evidence_row_ids"]),
                "control_code": code,
            }
        )

    status = "HOLD" if contested or quarantine_rows else "PASS"
    action = "BLOCK_AND_REMEDIATE" if status == "HOLD" else "RELEASE"
    return {
        "merge_summary": {
            "raw_row_count": len(rows),
            "canonical_person_count": len(clusters),
            "merged_duplicate_cluster_count": duplicate_count,
            "quarantine_row_count": len(quarantine_rows),
            "contested_identifier_cluster_count": len(contested),
            "dispatchable_person_count": len(dispatch_ids),
        },
        "focus_people": focus,
        "contested_cluster_ids": sorted(contested),
        "dispatchable_master_ids": dispatch_ids,
        "readiness_by_depot": readiness_by_depot,
        "policy_control_cases": controls,
        "release_decision": {"status": status, "action": action},
    }


def retained_logical(rows, id_field, authoritative_snapshot_id):
    grouped = collections.defaultdict(list)
    for row in rows:
        grouped[row[id_field]].append(row)
    retained = []
    duplicate_groups = []
    for stable_id, members in grouped.items():
        members.sort(
            key=lambda r: (
                0 if r.get("snapshot_id") == authoritative_snapshot_id else 1,
                0 if str(r.get("snapshot_id", "")).endswith("-certified") else 1,
                r.get("ingested_at") or "",
            )
        )
        kept = members[0]
        retained.append(kept)
        if len(members) > 1:
            duplicate_groups.append((stable_id, list(members), kept))
    retained.sort(key=lambda r: r[id_field])
    duplicate_groups.sort(key=lambda x: x[0])
    return retained, duplicate_groups


def alias_policy_code(row, cutoff_date):
    status = row.get("reference_status")
    if status == "PROVISIONAL":
        return "RB-83"
    effective = (
        status == "ACTIVE"
        and (not row.get("valid_from") or cutoff_date >= row["valid_from"])
        and (not row.get("valid_to") or cutoff_date <= row["valid_to"])
    )
    return "RB-42" if effective else "RB-17"


def active_aliases(hub, domain, on_date):
    rows = hub.fetch_pages("/api/reference/aliases", domain=domain)
    return [
        r
        for r in rows
        if r.get("reference_status") == "ACTIVE"
        and (not r.get("valid_from") or on_date >= r["valid_from"])
        and (not r.get("valid_to") or on_date <= r["valid_to"])
    ]


def match_aliases(description, aliases):
    text = unicodedata.normalize("NFKC", str(description or "")).casefold()
    raw_matches = []
    for alias in aliases:
        phrase = unicodedata.normalize("NFKC", alias["alias_text"]).casefold()
        pattern = r"(?<![\w])" + r"[-\s]+".join(re.escape(part) for part in phrase.split()) + r"(?![\w])"
        for match in re.finditer(pattern, text):
            raw_matches.append((match.start(), match.end(), len(match.group(0)), alias))
    raw_matches.sort(key=lambda m: (-m[2], m[0]))
    kept = []
    for match in raw_matches:
        overlaps = any(not (match[1] <= existing[0] or match[0] >= existing[1]) for existing in kept)
        if not overlaps:
            kept.append(match)
    values = sorted({m[3]["canonical_value"] for m in kept})
    return values, [m[3] for m in kept]


def conversion_factor(hub, kind, unit, on_date):
    for row in hub.fetch_pages("/api/reference/conversions", kind=kind):
        if row["from_unit"] == unit and (not row.get("valid_from") or on_date >= row["valid_from"]) and (not row.get("valid_to") or on_date <= row["valid_to"]):
            return float(row["factor"]), int(row.get("precision", 3))
    raise RuntimeError(f"no {kind} conversion for {unit} on {on_date}")


def fx_rate(hub, currency, on_date):
    candidates = [
        r
        for r in hub.fetch_pages("/api/reference/fx")
        if r["currency"] == currency and r["rate_date"] == on_date
    ]
    certified = [r for r in candidates if r.get("rate_status") == "CERTIFIED"]
    use = certified or candidates
    if not use:
        raise RuntimeError(f"no FX rate for {currency} on {on_date}")
    use.sort(key=lambda r: (0 if r.get("rate_status") == "CERTIFIED" else 1, r.get("published_at") or ""))
    return float(use[0]["usd_per_unit"])


def source_basis_code(row, duplicate_ids):
    if row.get("_stable_id") in duplicate_ids:
        return "SB-61"
    if str(row.get("snapshot_id", "")).endswith("-certified"):
        return "SB-24"
    return "SB-79"


def ledger_code(is_invalid, match_count, is_mismatch):
    if is_invalid:
        return "LD-53"
    if match_count == 0:
        return "LD-14"
    if match_count > 1:
        return "LD-88"
    if is_mismatch:
        return "LD-31"
    return "LD-72"


def solve_fuel(hub, scope):
    collection = scope["collection_id"]
    cutoff = scope["cutoff_at"]
    cutoff_date = date_part(cutoff)
    auth = hub.authoritative_snapshot_id(collection)
    rows = hub.fetch_pages("/api/transactions/fuel", collection=collection)
    retained, duplicate_groups = retained_logical(rows, "transaction_id", auth)
    duplicate_ids = {stable_id for stable_id, _, _ in duplicate_groups}
    for row in retained:
        row["_stable_id"] = row["transaction_id"]

    mismatch_ids = []
    zero_match_ids = []
    ambiguous_ids = []
    invalid_qty_ids = []
    valid_rows = []
    diagnostics = {}
    for row in retained:
        day = date_part(row["purchased_at"])
        values, _ = match_aliases(row.get("purchased_description"), active_aliases(hub, "fuel", day))
        invalid_qty = row.get("quantity") is None or float(row["quantity"]) <= 0
        mismatch = False
        if len(values) == 0:
            zero_match_ids.append(row["transaction_id"])
        elif len(values) > 1:
            ambiguous_ids.append(row["transaction_id"])
        elif not invalid_qty:
            recognized = values[0]
            mismatch = recognized != row.get("expected_fuel_type")
            if mismatch:
                mismatch_ids.append(row["transaction_id"])
            factor, precision = conversion_factor(hub, "volume", row["quantity_unit"], day)
            volume_l = round(float(row["quantity"]) * factor, precision)
            spend_usd = round(float(row["amount"]) * fx_rate(hub, row["currency"], day), 2)
            valid_rows.append((row, recognized, volume_l, spend_usd))
        if invalid_qty:
            invalid_qty_ids.append(row["transaction_id"])
        diagnostics[row["transaction_id"]] = {
            "invalid": invalid_qty,
            "match_count": len(values),
            "mismatch": mismatch,
        }

    quarantine_ids = set(zero_match_ids) | set(ambiguous_ids) | set(invalid_qty_ids)
    exception_ids = set(mismatch_ids) | quarantine_ids
    merchant_counts = collections.defaultdict(lambda: {"mismatch": 0, "quarantine": 0, "ids": set()})
    for row in retained:
        txid = row["transaction_id"]
        if txid in exception_ids:
            bucket = merchant_counts[row["merchant_id"]]
            bucket["ids"].add(txid)
            if txid in mismatch_ids:
                bucket["mismatch"] += 1
            if txid in quarantine_ids:
                bucket["quarantine"] += 1
    ranking = []
    for merchant, bucket in merchant_counts.items():
        ranking.append(
            {
                "merchant_id": merchant,
                "exception_count": len(bucket["ids"]),
                "mismatch_count": bucket["mismatch"],
                "quarantine_count": bucket["quarantine"],
            }
        )
    ranking.sort(key=lambda r: (-r["exception_count"], r["merchant_id"]))

    by_type = collections.defaultdict(lambda: {"count": 0, "volume": 0.0, "spend": 0.0})
    for _, recognized, volume_l, spend_usd in valid_rows:
        by_type[recognized]["count"] += 1
        by_type[recognized]["volume"] += volume_l
        by_type[recognized]["spend"] += spend_usd
    fuel_totals = [
        {
            "fuel_type": fuel_type,
            "transaction_count": data["count"],
            "volume_l": round(data["volume"], 2),
            "spend_usd": round(data["spend"], 2),
        }
        for fuel_type, data in sorted(by_type.items())
    ]

    aliases_by_id = {r["alias_id"]: r for r in hub.fetch_pages("/api/reference/aliases", domain="fuel")}
    retained_by_id = {r["transaction_id"]: r for r in retained}
    reference_decisions = [
        {"reference_id": rid, "reference_policy_code": alias_policy_code(aliases_by_id[rid], cutoff_date)}
        for rid in sorted(scope.get("reference_decision_ids", []))
    ]
    transaction_decisions = []
    for txid in sorted(scope.get("transaction_decision_ids", [])):
        row = retained_by_id[txid]
        d = diagnostics[txid]
        transaction_decisions.append(
            {
                "transaction_id": txid,
                "source_basis_code": source_basis_code(row, duplicate_ids),
                "ledger_disposition_code": ledger_code(d["invalid"], d["match_count"], d["mismatch"]),
            }
        )

    status = "HOLD" if quarantine_ids else ("PASS_WITH_EXCEPTIONS" if mismatch_ids else "PASS")
    action = {"PASS": "RELEASE", "PASS_WITH_EXCEPTIONS": "REVIEW_EXCEPTIONS", "HOLD": "BLOCK_AND_REMEDIATE"}[status]
    return {
        "audit_summary": {
            "collection_id": collection,
            "cutoff_at": cutoff,
            "authoritative_snapshot_id": auth,
            "raw_row_count": len(rows),
            "logical_transaction_count": len(retained),
            "duplicate_raw_count": len(rows) - len(retained),
            "valid_transaction_count": len(valid_rows),
            "mismatch_count": len(mismatch_ids),
            "unrecognized_count": len(zero_match_ids),
            "ambiguous_count": len(ambiguous_ids),
            "invalid_quantity_count": len(invalid_qty_ids),
            "exception_transaction_count": len(exception_ids),
            "exception_merchant_ranking": ranking[: int(scope.get("merchant_ranking_limit", 5))],
        },
        "mismatch_transaction_ids": sorted(mismatch_ids),
        "unrecognized_transaction_ids": sorted(set(zero_match_ids) | set(ambiguous_ids)),
        "normalized_totals": {
            "valid_transaction_count": len(valid_rows),
            "total_volume_l": round(sum(v[2] for v in valid_rows), 2),
            "total_spend_usd": round(sum(v[3] for v in valid_rows), 2),
            "fuel_type_totals": fuel_totals,
        },
        "focus_assets": fuel_focus_assets(scope, retained, valid_rows, set(mismatch_ids), quarantine_ids),
        "policy_decision_panel": {
            "reference_decisions": reference_decisions,
            "transaction_decisions": transaction_decisions,
        },
        "reconciliation_status": {"status": status, "action": action},
    }


def fuel_focus_assets(scope, retained, valid_rows, mismatch_ids, quarantine_ids):
    valid_by_tx = {row["transaction_id"]: (row, volume, spend) for row, _, volume, spend in valid_rows}
    retained_by_asset = collections.defaultdict(list)
    for row in retained:
        retained_by_asset[row["asset_id"]].append(row)
    output = []
    for asset_id in sorted(scope.get("focus_asset_ids", [])):
        logical = retained_by_asset.get(asset_id, [])
        valid = [valid_by_tx[r["transaction_id"]] for r in logical if r["transaction_id"] in valid_by_tx]
        output.append(
            {
                "asset_id": asset_id,
                "logical_transaction_count": len(logical),
                "valid_transaction_count": len(valid),
                "mismatch_count": sum(1 for r in logical if r["transaction_id"] in mismatch_ids),
                "quarantine_count": sum(1 for r in logical if r["transaction_id"] in quarantine_ids),
                "exception_count": sum(1 for r in logical if r["transaction_id"] in mismatch_ids or r["transaction_id"] in quarantine_ids),
                "volume_l": round(sum(v[1] for v in valid), 2),
                "spend_usd": round(sum(v[2] for v in valid), 2),
            }
        )
    return output


def solve_freight(hub, scope):
    collection = scope["collection_id"]
    cutoff = scope["cutoff_at"]
    cutoff_date = date_part(cutoff)
    auth = hub.authoritative_snapshot_id(collection)
    rows = hub.fetch_pages("/api/transactions/freight", collection=collection)
    retained, duplicate_groups = retained_logical(rows, "charge_id", auth)
    duplicate_ids = {stable_id for stable_id, _, _ in duplicate_groups}
    for row in retained:
        row["_stable_id"] = row["charge_id"]

    mismatch_ids = []
    quarantine_ids = set()
    quarantine_reasons = collections.Counter()
    valid_rows = []
    diagnostics = {}
    for row in retained:
        day = row["service_date"]
        values, _ = match_aliases(row.get("description"), active_aliases(hub, "freight", day))
        invalid_weight = row.get("billed_weight") is None or float(row["billed_weight"]) <= 0
        invalid_distance = row.get("distance") is None or float(row["distance"]) <= 0
        if len(values) == 0:
            quarantine_reasons["unrecognized_alias"] += 1
        elif len(values) > 1:
            quarantine_reasons["ambiguous_alias"] += 1
        if invalid_weight:
            quarantine_reasons["invalid_weight"] += 1
        if invalid_distance:
            quarantine_reasons["invalid_distance"] += 1
        mismatch = False
        if len(values) != 1 or invalid_weight or invalid_distance:
            quarantine_ids.add(row["charge_id"])
        else:
            service_class = values[0]
            mismatch = service_class != row.get("expected_service_class")
            if mismatch:
                mismatch_ids.append(row["charge_id"])
            weight_factor, weight_precision = conversion_factor(hub, "weight", row["weight_unit"], day)
            distance_factor, distance_precision = conversion_factor(hub, "distance", row["distance_unit"], day)
            weight = round(float(row["billed_weight"]) * weight_factor, weight_precision)
            distance = round(float(row["distance"]) * distance_factor, distance_precision)
            spend = round(float(row["amount"]) * fx_rate(hub, row["currency"], day), 2)
            valid_rows.append((row, service_class, weight, distance, spend))
        diagnostics[row["charge_id"]] = {
            "invalid": invalid_weight or invalid_distance,
            "match_count": len(values),
            "mismatch": mismatch,
        }

    by_class = collections.defaultdict(lambda: {"count": 0, "weight": 0.0, "distance": 0.0, "spend": 0.0})
    for _, service_class, weight, distance, spend in valid_rows:
        bucket = by_class[service_class]
        bucket["count"] += 1
        bucket["weight"] += weight
        bucket["distance"] += distance
        bucket["spend"] += spend
    class_totals = [
        {
            "service_class": service_class,
            "charge_count": data["count"],
            "billed_weight_kg": round(data["weight"], 2),
            "distance_km": round(data["distance"], 2),
            "spend_usd": round(data["spend"], 2),
        }
        for service_class, data in sorted(by_class.items())
    ]

    duplicate_output = [
        {
            "charge_id": charge_id,
            "raw_occurrence_count": len(members),
            "snapshot_ids": sorted({r["snapshot_id"] for r in members}),
            "retained_snapshot_id": kept["snapshot_id"],
        }
        for charge_id, members, kept in duplicate_groups
    ]

    aliases_by_id = {r["alias_id"]: r for r in hub.fetch_pages("/api/reference/aliases", domain="freight")}
    retained_by_id = {r["charge_id"]: r for r in retained}
    decision_panels = {
        "reference_rows": [
            {"alias_id": aid, "decision_code": alias_policy_code(aliases_by_id[aid], cutoff_date)}
            for aid in sorted(scope.get("reference_decision_alias_ids", []))
        ],
        "source_retention": [
            {"charge_id": cid, "decision_code": source_basis_code(retained_by_id[cid], duplicate_ids)}
            for cid in sorted(scope.get("source_decision_charge_ids", []))
        ],
        "ledger_routing": [
            {
                "charge_id": cid,
                "decision_code": ledger_code(
                    diagnostics[cid]["invalid"],
                    diagnostics[cid]["match_count"],
                    diagnostics[cid]["mismatch"],
                ),
            }
            for cid in sorted(scope.get("ledger_decision_charge_ids", []))
        ],
    }

    mismatch_set = set(mismatch_ids)
    carrier = collections.defaultdict(lambda: {"mismatch_count": 0, "mismatch_spend": 0.0, "quarantine_count": 0, "ids": set()})
    for row, _, _, _, spend in valid_rows:
        if row["charge_id"] in mismatch_set:
            bucket = carrier[row["carrier_id"]]
            bucket["mismatch_count"] += 1
            bucket["mismatch_spend"] += spend
            bucket["ids"].add(row["charge_id"])
    for row in retained:
        if row["charge_id"] in quarantine_ids:
            bucket = carrier[row["carrier_id"]]
            bucket["quarantine_count"] += 1
            bucket["ids"].add(row["charge_id"])
    ranking = []
    for carrier_id, bucket in carrier.items():
        ranking.append(
            {
                "carrier_id": carrier_id,
                "mismatch_count": bucket["mismatch_count"],
                "mismatch_spend_usd": round(bucket["mismatch_spend"], 2),
                "quarantine_count": bucket["quarantine_count"],
                "exception_count": len(bucket["ids"]),
            }
        )
    ranking.sort(key=lambda r: (-r["mismatch_spend_usd"], r["carrier_id"]))
    for idx, row in enumerate(ranking[: int(scope.get("carrier_ranking_limit", 5))], start=1):
        row["rank"] = idx
    ranking = [{"rank": r["rank"], **{k: v for k, v in r.items() if k != "rank"}} for r in ranking[: int(scope.get("carrier_ranking_limit", 5))]]

    status = "HOLD" if quarantine_ids else ("PASS_WITH_EXCEPTIONS" if mismatch_ids else "PASS")
    routing = {"PASS": "RELEASE", "PASS_WITH_EXCEPTIONS": "REVIEW_EXCEPTIONS", "HOLD": "BLOCK_AND_REMEDIATE"}[status]
    return {
        "audit_summary": {
            "collection_id": collection,
            "cutoff_at": cutoff,
            "authoritative_snapshot_id": auth,
            "raw_row_count": len(rows),
            "logical_charge_count": len(retained),
            "duplicate_raw_count": len(rows) - len(retained),
            "valid_charge_count": len(valid_rows),
            "mismatch_count": len(mismatch_ids),
            "quarantine_count": len(quarantine_ids),
            "quarantine_reason_counts": {
                "ambiguous_alias": quarantine_reasons["ambiguous_alias"],
                "invalid_distance": quarantine_reasons["invalid_distance"],
                "invalid_weight": quarantine_reasons["invalid_weight"],
                "unrecognized_alias": quarantine_reasons["unrecognized_alias"],
            },
        },
        "class_mismatch_charge_ids": sorted(mismatch_ids),
        "quarantine_charge_ids": sorted(quarantine_ids),
        "duplicate_groups": duplicate_output,
        "decision_panels": decision_panels,
        "normalized_totals": {
            "valid_charge_count": len(valid_rows),
            "total_billed_weight_kg": round(sum(v[2] for v in valid_rows), 2),
            "total_distance_km": round(sum(v[3] for v in valid_rows), 2),
            "total_spend_usd": round(sum(v[4] for v in valid_rows), 2),
            "service_class_totals": class_totals,
        },
        "carrier_ranking": ranking,
        "close_status": {"status": status, "routing": routing},
    }


def maintenance_invalid(row):
    parsed = parse_time(row.get("event_time_raw"))
    missing_timestamp = row.get("event_time_raw") in (None, "")
    invalid_timestamp = row.get("event_time_raw") not in (None, "") and parsed is None
    invalid_odometer = row.get("odometer_value") is None or float(row["odometer_value"]) <= 0
    negative_labor = row.get("labor_hours") is None or float(row["labor_hours"]) < 0
    extreme_labor = row.get("labor_hours") is not None and float(row["labor_hours"]) > 24
    return {
        "missing_timestamp": missing_timestamp,
        "invalid_timestamp": invalid_timestamp,
        "invalid_odometer": invalid_odometer,
        "negative_labor": negative_labor,
        "extreme_labor": extreme_labor,
        "any": missing_timestamp or invalid_timestamp or invalid_odometer or negative_labor or extreme_labor,
        "parsed_time": parsed,
    }


def solve_maintenance(hub, scope):
    collection = scope["collection_id"]
    as_of = scope["as_of"]
    auth = hub.authoritative_snapshot_id(collection)
    snapshots = {s["snapshot_id"]: s for s in hub.snapshots(collection)}
    rows = hub.fetch_pages("/api/maintenance/events", collection=collection)
    retained, duplicate_groups = retained_logical(rows, "event_id", auth)
    duplicate_ids = {stable_id for stable_id, _, _ in duplicate_groups}
    retained_by_id = {r["event_id"]: r for r in retained}

    issue_counts = collections.Counter()
    invalid_ids = []
    candidates_by_asset = collections.defaultdict(list)
    for row in retained:
        flags = maintenance_invalid(row)
        for key in ["missing_timestamp", "invalid_timestamp", "invalid_odometer", "negative_labor", "extreme_labor"]:
            if flags[key]:
                issue_counts[key] += 1
        if flags["any"]:
            invalid_ids.append(row["event_id"])
            continue
        factor, _ = conversion_factor(hub, "distance", row["odometer_unit"], date_part(row["event_time_raw"]))
        copy = dict(row)
        copy["_time"] = flags["parsed_time"]
        copy["_odometer_km"] = float(row["odometer_value"]) * factor
        candidates_by_asset[row["asset_id"]].append(copy)

    regression_ids = []
    reliable = []
    for asset_id, events in candidates_by_asset.items():
        events.sort(key=lambda r: (r["_time"], r["event_id"]))
        last = None
        for row in events:
            if last is not None and row["_odometer_km"] < last:
                regression_ids.append(row["event_id"])
            else:
                reliable.append(row)
                last = row["_odometer_km"]
    issue_counts["odometer_regression"] = len(regression_ids)

    reliable_by_asset = collections.defaultdict(list)
    for row in reliable:
        reliable_by_asset[row["asset_id"]].append(row)
    total_distance = 0.0
    for events in reliable_by_asset.values():
        events.sort(key=lambda r: (r["_time"], r["event_id"]))
        if len(events) >= 2:
            total_distance += events[-1]["_odometer_km"] - events[0]["_odometer_km"]

    duplicate_output = [
        {
            "logical_event_id": event_id,
            "snapshot_ids": sorted({r["snapshot_id"] for r in members}),
            "retained_event_id": kept["event_id"],
            "retained_snapshot_id": kept["snapshot_id"],
        }
        for event_id, members, kept in duplicate_groups
    ]

    rejected_by_asset = collections.Counter(retained_by_id[eid]["asset_id"] for eid in invalid_ids)
    regression_by_asset = collections.Counter(retained_by_id[eid]["asset_id"] for eid in regression_ids)
    all_assets = set(rejected_by_asset) | set(regression_by_asset)
    ranked_assets = sorted(
        all_assets,
        key=lambda a: (-(rejected_by_asset[a] + regression_by_asset[a]), -regression_by_asset[a], a),
    )[: int(scope.get("asset_risk_ranking", {}).get("limit", 5))]
    asset_ranking = [
        {
            "rank": idx,
            "asset_id": asset_id,
            "rejected_event_count": rejected_by_asset[asset_id] + regression_by_asset[asset_id],
            "regression_event_count": regression_by_asset[asset_id],
        }
        for idx, asset_id in enumerate(ranked_assets, start=1)
    ]

    invalid_set = set(invalid_ids)
    regression_set = set(regression_ids)
    panel = []
    for event_id in sorted(scope.get("event_decision_panel", {}).get("event_ids", [])):
        row = retained_by_id[event_id]
        if event_id in duplicate_ids:
            source_code = "MS-47"
        elif str(row.get("snapshot_id", "")).endswith("-certified"):
            source_code = "MS-12"
        else:
            source_code = "MS-86"
        if event_id in invalid_set:
            route = "HR-74"
        elif event_id in regression_set:
            route = "HR-19"
        else:
            route = "HR-33"
        panel.append({"event_id": event_id, "maintenance_source_code": source_code, "history_route_code": route})

    if regression_ids and "certification_gate" in scope:
        status = scope["certification_gate"]["odometer_regression_status"]
        action = scope["certification_gate"]["odometer_regression_action"]
    elif invalid_ids:
        status, action = "PASS_WITH_EXCEPTIONS", "REVIEW_EXCEPTIONS"
    else:
        status, action = "PASS", "RELEASE"

    auth_snapshot = snapshots.get(auth, {})
    return {
        "source_decision": {
            "collection_id": collection,
            "as_of": as_of,
            "authoritative_snapshot_id": auth,
            "snapshot_status": auth_snapshot.get("snapshot_status"),
            "authoritative_row_count": auth_snapshot.get("row_count", 0),
            "scoped_raw_row_count": len(rows),
        },
        "event_decision_panel": panel,
        "issue_counts": {
            "missing_timestamp": issue_counts["missing_timestamp"],
            "invalid_timestamp": issue_counts["invalid_timestamp"],
            "invalid_odometer": issue_counts["invalid_odometer"],
            "negative_labor": issue_counts["negative_labor"],
            "extreme_labor": issue_counts["extreme_labor"],
            "odometer_regression": issue_counts["odometer_regression"],
        },
        "duplicate_groups": duplicate_output,
        "invalid_event_ids": sorted(invalid_ids),
        "corrected_metrics": {
            "valid_event_count": len(retained) - len(invalid_ids) - len(regression_ids),
            "total_distance_km": round(total_distance, 2),
            "regression_asset_ids": sorted(regression_by_asset),
            "regression_event_ids": sorted(regression_ids),
        },
        "asset_risk_ranking": asset_ranking,
        "certification_status": {"status": status, "action": action},
    }


def detect_family(template):
    required = set(template.get("required", []))
    if not required and "required_top_level_keys" in template:
        required = set(template["required_top_level_keys"])
    if {"quality_summary", "focus_clusters", "channel_readiness"} <= required:
        return "partner_contacts"
    if {"merge_summary", "focus_people", "readiness_by_depot"} <= required:
        return "roster_contacts"
    if {"mismatch_transaction_ids", "focus_assets", "policy_decision_panel"} <= required:
        return "fuel"
    if {"source_decision", "event_decision_panel", "corrected_metrics"} <= required:
        return "maintenance"
    if {"class_mismatch_charge_ids", "carrier_ranking", "decision_panels"} <= required:
        return "freight"
    raise SystemExit(f"unsupported answer template family; top-level keys: {sorted(required)}")


def solve(task_dir: Path, env_path: Path):
    payload_dir = task_dir / "payloads"
    scope = read_json(payload_dir / "case_scope.json")
    template = read_json(payload_dir / "answer_template.json")
    hub = Hub(parse_env(env_path))
    family = detect_family(template)
    if family == "partner_contacts":
        return solve_partner_contacts(hub, scope)
    if family == "roster_contacts":
        return solve_roster_contacts(hub, scope)
    if family == "fuel":
        return solve_fuel(hub, scope)
    if family == "maintenance":
        return solve_maintenance(hub, scope)
    if family == "freight":
        return solve_freight(hub, scope)
    raise AssertionError(family)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", default=".", help="Directory containing prompt.txt and payloads/")
    parser.add_argument("--env", default="environment_access.md", help="Path to environment_access.md")
    parser.add_argument("--output", help="Write answer JSON to this path instead of stdout")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args(argv)

    answer = solve(Path(args.task_dir), Path(args.env))
    text = json.dumps(answer, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=False)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
