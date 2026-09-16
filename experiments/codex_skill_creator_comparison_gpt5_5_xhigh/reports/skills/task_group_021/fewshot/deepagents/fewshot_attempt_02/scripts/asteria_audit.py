#!/usr/bin/env python3
"""Fetch and classify Asteria Fleet Data Quality Hub records.

This helper is intentionally collection-agnostic. It fetches public hub data,
applies the recurring reconciliation rules, and emits intermediate classified
records that a solver can map into the current answer_template.json.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


ENDPOINTS = {
    "contacts": "/api/contacts",
    "fuel": "/api/transactions/fuel",
    "freight": "/api/transactions/freight",
    "maintenance": "/api/maintenance/events",
}

ID_FIELDS = {
    "fuel": "transaction_id",
    "freight": "charge_id",
    "maintenance": "event_id",
}

REFERENCE_DOMAIN = {"fuel": "fuel", "freight": "freight"}

CONTACT_SOURCE_PRIORITY = {
    "contact": [
        "Identity Registry",
        "Compliance Master",
        "CRM",
        "Dispatch",
        "Dealer Service",
        "Dealer Portal",
        "Partner Portal",
        "Warranty Claims",
        "HR Directory",
    ],
    "name_region": [
        "HR Directory",
        "Warranty Claims",
        "Dealer Portal",
        "Partner Portal",
        "CRM",
        "Dispatch",
        "Identity Registry",
        "Compliance Master",
        "Dealer Service",
    ],
}


def q(value: Decimal, places: int) -> Decimal:
    quant = Decimal("1") if places == 0 else Decimal("0." + "0" * (places - 1) + "1")
    return value.quantize(quant, rounding=ROUND_HALF_UP)


def as_number(value: Decimal, places: int) -> int | float:
    rounded = q(value, places)
    if places == 0:
        return int(rounded)
    return float(f"{rounded:.{places}f}")


def norm_text(value: object) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).strip().lower()


def norm_email(value: object) -> str:
    email = norm_text(value)
    return email if "@" in email else ""


def phone_digits(value: object) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def date_part(value: str) -> str:
    return (value or "")[:10]


def load_base_url(args: argparse.Namespace) -> str:
    if args.base_url:
        return args.base_url.rstrip("/")
    env_path = Path(args.env)
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("base_url:"):
                return line.split(":", 1)[1].strip().rstrip("/")
    raise SystemExit("Provide --base-url or an environment_access.md with base_url.")


def get_json(base_url: str, path: str, params: dict[str, object] | None = None) -> dict:
    url = base_url + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url) as response:
        data = json.load(response)
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(f"{path} returned error: {data['error']}")
    return data


def fetch_all(base_url: str, path: str, params: dict[str, object] | None = None) -> list[dict]:
    params = dict(params or {})
    out: list[dict] = []
    offset = 0
    while True:
        page_params = dict(params)
        page_params.setdefault("limit", 500)
        page_params["offset"] = offset
        data = get_json(base_url, path, page_params)
        items = data.get("items", [])
        out.extend(items)
        limit = int(data.get("limit") or len(items) or 500)
        total = int(data.get("total") or len(out))
        offset += limit
        if offset >= total:
            return out


def effective_reference(row: dict, business_date: str) -> bool:
    if row.get("reference_status") != "ACTIVE":
        return False
    if row.get("valid_from") and business_date < row["valid_from"]:
        return False
    if row.get("valid_to") and business_date > row["valid_to"]:
        return False
    return True


def alias_matches(description: str, aliases: list[dict], business_date: str) -> list[dict]:
    text = norm_text(description)
    hits: list[tuple[int, int, dict]] = []
    for alias in aliases:
        if not effective_reference(alias, business_date):
            continue
        phrase = norm_text(alias.get("alias_text"))
        pattern = r"(?<![a-z0-9])" + re.escape(phrase).replace(r"\ ", r"\s+") + r"(?![a-z0-9])"
        for match in re.finditer(pattern, text):
            hits.append((match.start(), match.end(), alias))

    kept: list[tuple[int, int, dict]] = []
    for hit in hits:
        start, end, _ = hit
        contained = any(
            other_start <= start
            and other_end >= end
            and (other_end - other_start) > (end - start)
            for other_start, other_end, _ in hits
        )
        if not contained:
            kept.append(hit)
    return [hit[2] for hit in kept]


def classify_reference_row(row: dict, as_of_date: str) -> str:
    if row.get("reference_status") == "PROVISIONAL":
        return "RB-83"
    if not effective_reference(row, as_of_date):
        return "RB-17"
    return "RB-42"


def snapshots(base_url: str, collection: str) -> list[dict]:
    return fetch_all(base_url, "/api/source-snapshots", {"collection": collection})


def authoritative_snapshot(snap_rows: list[dict]) -> dict:
    certified = [row for row in snap_rows if row.get("snapshot_status") == "CERTIFIED"]
    pool = certified or snap_rows
    return sorted(pool, key=lambda row: (int(row.get("row_count") or 0), row.get("snapshot_id") or ""), reverse=True)[0]


def retain_logical_rows(records: list[dict], id_field: str, snap_rows: list[dict]) -> tuple[dict[str, dict], list[dict], dict[str, str]]:
    status_by_snapshot = {row["snapshot_id"]: row.get("snapshot_status") for row in snap_rows}
    auth_id = authoritative_snapshot(snap_rows)["snapshot_id"]
    grouped: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        grouped[record[id_field]].append(record)

    retained: dict[str, dict] = {}
    duplicates: list[dict] = []
    source_codes: dict[str, str] = {}
    for logical_id, rows in grouped.items():
        chosen = next((row for row in rows if row.get("snapshot_id") == auth_id), None)
        if chosen is None:
            certified = [row for row in rows if status_by_snapshot.get(row.get("snapshot_id")) == "CERTIFIED"]
            pool = certified or rows
            chosen = sorted(
                pool,
                key=lambda row: (
                    row.get("business_updated_at") or "",
                    row.get("ingested_at") or "",
                    row.get("snapshot_id") or "",
                ),
                reverse=True,
            )[0]
        retained[logical_id] = chosen
        if len(rows) > 1:
            source_codes[logical_id] = "SB-61"
            duplicates.append(
                {
                    "logical_id": logical_id,
                    "raw_occurrence_count": len(rows),
                    "snapshot_ids": sorted({row["snapshot_id"] for row in rows}),
                    "retained_snapshot_id": chosen["snapshot_id"],
                }
            )
        elif status_by_snapshot.get(chosen.get("snapshot_id")) == "CERTIFIED":
            source_codes[logical_id] = "SB-24"
        else:
            source_codes[logical_id] = "SB-79"
    return retained, sorted(duplicates, key=lambda row: row["logical_id"]), source_codes


def conversion_factors(base_url: str) -> dict[tuple[str, str, str], tuple[Decimal, int]]:
    factors: dict[tuple[str, str, str], tuple[Decimal, int]] = {}
    for kind in ["volume", "weight", "distance"]:
        for row in fetch_all(base_url, "/api/reference/conversions", {"kind": kind}):
            factors[(kind, row["from_unit"], row["to_unit"])] = (Decimal(str(row["factor"])), int(row["precision"]))
    return factors


def convert(factors: dict[tuple[str, str, str], tuple[Decimal, int]], kind: str, value: object, from_unit: str, to_unit: str) -> Decimal:
    factor, precision = factors[(kind, from_unit, to_unit)]
    return q(Decimal(str(value)) * factor, precision)


def fx_rates(base_url: str) -> dict[tuple[str, str], Decimal]:
    rates: dict[tuple[str, str], Decimal] = {}
    for row in fetch_all(base_url, "/api/reference/fx"):
        if row.get("rate_status") == "CERTIFIED":
            rates[(row["rate_date"], row["currency"])] = Decimal(str(row["usd_per_unit"]))
    return rates


def usd_amount(rates: dict[tuple[str, str], Decimal], amount: object, currency: str, business_date: str) -> Decimal:
    return q(Decimal(str(amount)) * rates[(business_date, currency)], 2)


def ledger_disposition(alias_state: str, invalid_measure: bool, mismatch: bool) -> str:
    if invalid_measure:
        return "LD-53"
    if alias_state == "unrecognized":
        return "LD-14"
    if alias_state == "ambiguous":
        return "LD-88"
    if mismatch:
        return "LD-31"
    return "LD-72"


def classify_ledger(base_url: str, family: str, collection: str) -> dict:
    id_field = ID_FIELDS[family]
    endpoint = ENDPOINTS[family]
    date_field = "purchased_at" if family == "fuel" else "service_date"
    description_field = "purchased_description" if family == "fuel" else "description"
    expected_field = "expected_fuel_type" if family == "fuel" else "expected_service_class"
    value_name = "fuel_type" if family == "fuel" else "service_class"

    records = fetch_all(base_url, endpoint, {"collection": collection})
    snap_rows = snapshots(base_url, collection)
    retained, duplicate_rows, source_codes = retain_logical_rows(records, id_field, snap_rows)
    aliases = fetch_all(base_url, "/api/reference/aliases", {"domain": REFERENCE_DOMAIN[family]})
    rates = fx_rates(base_url)
    factors = conversion_factors(base_url)

    classified: list[dict] = []
    reason_counter: Counter[str] = Counter()
    totals: dict[str, dict[str, Decimal | int]] = defaultdict(lambda: defaultdict(Decimal))
    valid_count = 0
    mismatch_count = 0
    quarantine_count = 0

    for logical_id, row in sorted(retained.items()):
        business_date = date_part(row[date_field])
        matched_aliases = alias_matches(row[description_field], aliases, business_date)
        canonical_values = sorted({alias["canonical_value"] for alias in matched_aliases})
        if len(canonical_values) == 0:
            alias_state = "unrecognized"
        elif len(canonical_values) > 1:
            alias_state = "ambiguous"
        else:
            alias_state = "recognized"
        recognized = canonical_values[0] if alias_state == "recognized" else None

        quarantine_reasons: list[str] = []
        normalized: dict[str, float] = {}
        if alias_state == "unrecognized":
            quarantine_reasons.append("unrecognized_alias")
        elif alias_state == "ambiguous":
            quarantine_reasons.append("ambiguous_alias")

        if family == "fuel":
            invalid_quantity = row.get("quantity") is None or Decimal(str(row["quantity"])) <= 0
            if invalid_quantity:
                quarantine_reasons.append("invalid_quantity")
            if not quarantine_reasons:
                volume_l = convert(factors, "volume", row["quantity"], row["quantity_unit"], "L")
                spend_usd = usd_amount(rates, row["amount"], row["currency"], business_date)
                normalized = {"volume_l": as_number(volume_l, 3), "spend_usd": as_number(spend_usd, 2)}
                totals[recognized]["volume_l"] += volume_l
                totals[recognized]["spend_usd"] += spend_usd
                totals[recognized]["count"] += 1
        else:
            invalid_weight = row.get("billed_weight") is None or Decimal(str(row["billed_weight"])) <= 0
            invalid_distance = row.get("distance") is None or Decimal(str(row["distance"])) <= 0
            if invalid_weight:
                quarantine_reasons.append("invalid_weight")
            if invalid_distance:
                quarantine_reasons.append("invalid_distance")
            if not quarantine_reasons:
                weight_kg = convert(factors, "weight", row["billed_weight"], row["weight_unit"], "KG")
                distance_km = convert(factors, "distance", row["distance"], row["distance_unit"], "KM")
                spend_usd = usd_amount(rates, row["amount"], row["currency"], business_date)
                normalized = {
                    "billed_weight_kg": as_number(weight_kg, 3),
                    "distance_km": as_number(distance_km, 3),
                    "spend_usd": as_number(spend_usd, 2),
                }
                totals[recognized]["billed_weight_kg"] += weight_kg
                totals[recognized]["distance_km"] += distance_km
                totals[recognized]["spend_usd"] += spend_usd
                totals[recognized]["count"] += 1

        mismatch = not quarantine_reasons and recognized != row.get(expected_field)
        if mismatch:
            mismatch_count += 1
        if quarantine_reasons:
            quarantine_count += 1
            reason_counter.update(quarantine_reasons)
        else:
            valid_count += 1

        code = ledger_disposition(alias_state, any(reason.startswith("invalid_") for reason in quarantine_reasons), mismatch)
        classified.append(
            {
                id_field: logical_id,
                "snapshot_id": row["snapshot_id"],
                "source_basis_code": source_codes[logical_id],
                "expected_value": row.get(expected_field),
                f"recognized_{value_name}": recognized,
                "alias_state": alias_state,
                "matched_alias_ids": sorted({alias["alias_id"] for alias in matched_aliases}),
                "quarantine_reasons": quarantine_reasons,
                "is_valid": not quarantine_reasons,
                "is_mismatch": mismatch,
                "ledger_disposition_code": code,
                **normalized,
                "asset_id": row.get("asset_id"),
                "merchant_id": row.get("merchant_id"),
                "carrier_id": row.get("carrier_id"),
                "business_date": business_date,
            }
        )

    reference_date = max(date_part(row[date_field]) for row in retained.values())
    reference_decisions = [
        {
            "alias_id": row["alias_id"],
            "decision_code": classify_reference_row(row, reference_date),
            "reference_status": row["reference_status"],
            "valid_from": row["valid_from"],
            "valid_to": row["valid_to"],
        }
        for row in sorted(aliases, key=lambda item: item["alias_id"])
    ]

    total_fields: dict[str, float | int | list] = {"valid_count": valid_count}
    if family == "fuel":
        total_fields["total_volume_l"] = as_number(sum((row["volume_l"] for row in totals.values()), Decimal(0)), 2)
        total_fields["total_spend_usd"] = as_number(sum((row["spend_usd"] for row in totals.values()), Decimal(0)), 2)
        total_fields["by_value"] = [
            {
                value_name: key,
                "count": int(value["count"]),
                "volume_l": as_number(value["volume_l"], 2),
                "spend_usd": as_number(value["spend_usd"], 2),
            }
            for key, value in sorted(totals.items())
        ]
    else:
        total_fields["total_billed_weight_kg"] = as_number(sum((row["billed_weight_kg"] for row in totals.values()), Decimal(0)), 2)
        total_fields["total_distance_km"] = as_number(sum((row["distance_km"] for row in totals.values()), Decimal(0)), 2)
        total_fields["total_spend_usd"] = as_number(sum((row["spend_usd"] for row in totals.values()), Decimal(0)), 2)
        total_fields["by_value"] = [
            {
                value_name: key,
                "count": int(value["count"]),
                "billed_weight_kg": as_number(value["billed_weight_kg"], 2),
                "distance_km": as_number(value["distance_km"], 2),
                "spend_usd": as_number(value["spend_usd"], 2),
            }
            for key, value in sorted(totals.items())
        ]

    return {
        "collection_id": collection,
        "family": family,
        "authoritative_snapshot_id": authoritative_snapshot(snap_rows)["snapshot_id"],
        "raw_row_count": len(records),
        "logical_count": len(retained),
        "duplicate_raw_count": len(records) - len(retained),
        "duplicate_groups": duplicate_rows,
        "valid_count": valid_count,
        "mismatch_count": mismatch_count,
        "quarantine_count": quarantine_count,
        "quarantine_reason_counts": dict(sorted(reason_counter.items())),
        "normalized_totals": total_fields,
        "reference_decisions": reference_decisions,
        "classified_records": classified,
    }


def parse_timestamp(value: object) -> bool:
    if not value:
        return False
    try:
        datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def maintenance_source_code(row: dict, duplicate_ids: set[str], snapshot_status: dict[str, str]) -> str:
    if row["event_id"] in duplicate_ids:
        return "MS-47"
    if snapshot_status.get(row["snapshot_id"]) == "CERTIFIED":
        return "MS-12"
    return "MS-86"


def classify_maintenance(base_url: str, collection: str) -> dict:
    records = fetch_all(base_url, ENDPOINTS["maintenance"], {"collection": collection})
    snap_rows = snapshots(base_url, collection)
    retained, duplicate_rows, _ = retain_logical_rows(records, "event_id", snap_rows)
    duplicate_ids = {row["logical_id"] for row in duplicate_rows}
    snapshot_status = {row["snapshot_id"]: row["snapshot_status"] for row in snap_rows}
    factors = conversion_factors(base_url)

    invalid_ids: set[str] = set()
    issue_counts: Counter[str] = Counter()
    event_rows: list[dict] = []
    valid_for_sequence: list[dict] = []
    for event_id, row in sorted(retained.items()):
        flags: list[str] = []
        if not row.get("event_time_raw"):
            flags.append("missing_timestamp")
        elif not parse_timestamp(row.get("event_time_raw")):
            flags.append("invalid_timestamp")
        if row.get("odometer_value") is None or Decimal(str(row["odometer_value"])) <= 0:
            flags.append("invalid_odometer")
        if row.get("labor_hours") is None or Decimal(str(row["labor_hours"])) < 0:
            flags.append("negative_labor")
        elif Decimal(str(row["labor_hours"])) > 24:
            flags.append("extreme_labor")
        issue_counts.update(flags)
        if flags:
            invalid_ids.add(event_id)
        else:
            odometer_km = convert(factors, "distance", row["odometer_value"], row["odometer_unit"], "KM")
            row = dict(row)
            row["odometer_km"] = odometer_km
            valid_for_sequence.append(row)
        event_rows.append(
            {
                "event_id": event_id,
                "snapshot_id": row["snapshot_id"],
                "maintenance_source_code": maintenance_source_code(row, duplicate_ids, snapshot_status),
                "issue_flags": flags,
            }
        )

    by_asset: dict[str, list[dict]] = defaultdict(list)
    for row in valid_for_sequence:
        by_asset[row["asset_id"]].append(row)
    regression_ids: set[str] = set()
    regression_assets: set[str] = set()
    for asset_id, rows in by_asset.items():
        ordered = sorted(rows, key=lambda row: (row["event_time_raw"], row["event_id"]))
        for previous, current in zip(ordered, ordered[1:]):
            if current["odometer_km"] < previous["odometer_km"]:
                regression_ids.add(current["event_id"])
                regression_assets.add(asset_id)

    reliable_by_asset: dict[str, list[dict]] = defaultdict(list)
    for row in valid_for_sequence:
        if row["event_id"] not in regression_ids:
            reliable_by_asset[row["asset_id"]].append(row)
    total_distance = Decimal(0)
    for rows in reliable_by_asset.values():
        ordered = sorted(rows, key=lambda row: (row["event_time_raw"], row["event_id"]))
        if ordered:
            total_distance += ordered[-1]["odometer_km"] - ordered[0]["odometer_km"]

    rejected_by_asset = Counter(row["asset_id"] for row in retained.values() if row["event_id"] in invalid_ids)
    regression_by_asset = Counter(row["asset_id"] for row in retained.values() if row["event_id"] in regression_ids)
    risk_rows = [
        {
            "asset_id": asset_id,
            "rejected_event_count": rejected_by_asset[asset_id],
            "regression_event_count": regression_by_asset[asset_id],
        }
        for asset_id in sorted(set(rejected_by_asset) | set(regression_by_asset))
    ]
    risk_rows.sort(key=lambda row: (-row["rejected_event_count"], -row["regression_event_count"], row["asset_id"]))
    for rank, row in enumerate(risk_rows, start=1):
        row["rank"] = rank

    route_by_event = {}
    for row in event_rows:
        event_id = row["event_id"]
        if event_id in invalid_ids:
            route_by_event[event_id] = "HR-74"
        elif event_id in regression_ids:
            route_by_event[event_id] = "HR-19"
        else:
            route_by_event[event_id] = "HR-33"
        row["history_route_code"] = route_by_event[event_id]

    return {
        "collection_id": collection,
        "authoritative_snapshot_id": authoritative_snapshot(snap_rows)["snapshot_id"],
        "snapshot_status": authoritative_snapshot(snap_rows).get("snapshot_status"),
        "authoritative_row_count": authoritative_snapshot(snap_rows).get("row_count"),
        "scoped_raw_row_count": len(records),
        "duplicate_groups": duplicate_rows,
        "issue_counts": {
            **{key: issue_counts.get(key, 0) for key in ["missing_timestamp", "invalid_timestamp", "invalid_odometer", "negative_labor", "extreme_labor"]},
            "odometer_regression": len(regression_ids),
        },
        "invalid_event_ids": sorted(invalid_ids),
        "regression_event_ids": sorted(regression_ids),
        "regression_asset_ids": sorted(regression_assets),
        "valid_event_count": len(retained) - len(invalid_ids) - len(regression_ids),
        "total_distance_km": as_number(total_distance, 2),
        "asset_risk_ranking": risk_rows,
        "classified_events": event_rows,
    }


def union_find(values: list[str]) -> tuple[dict[str, str], callable]:
    parent = {value: value for value in values}

    def find(value: str) -> str:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(a: str, b: str) -> None:
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[max(root_a, root_b)] = min(root_a, root_b)

    return parent, union


def source_rank(row: dict, priority_name: str) -> tuple[int, int, str, str]:
    priority = CONTACT_SOURCE_PRIORITY[priority_name]
    source = row.get("source_system") or ""
    rank = priority.index(source) if source in priority else len(priority)
    return (rank, -int(row.get("verified_flag") or 0), row.get("business_updated_at") or "", row.get("row_id") or "")


def choose_contact_field(rows: list[dict], field: str, priority_name: str) -> tuple[object, str]:
    candidates = [row for row in rows if row.get(field) not in (None, "")]
    if not candidates:
        return "", ""
    chosen = sorted(candidates, key=lambda row: source_rank(row, priority_name))[0]
    value = chosen[field]
    if field == "email":
        value = norm_email(value)
    elif field == "phone":
        value = phone_digits(value)
    elif field == "person_or_org_name":
        value = " ".join(str(value).strip().split())
        if value.isupper():
            value = value.title()
    return value, chosen.get("source_system") or ""


def classify_contacts(base_url: str, collection: str) -> dict:
    records = fetch_all(base_url, ENDPOINTS["contacts"], {"collection": collection})
    ids = [row["row_id"] for row in records]
    parent, union = union_find(ids)
    by_email: dict[str, list[str]] = defaultdict(list)
    by_phone_name: dict[tuple[str, str], list[str]] = defaultdict(list)
    no_contact_rows: list[str] = []

    for row in records:
        email = norm_email(row.get("email"))
        phone = phone_digits(row.get("phone"))
        name = norm_text(row.get("person_or_org_name"))
        if email:
            by_email[email].append(row["row_id"])
        if phone and name:
            by_phone_name[(phone, name)].append(row["row_id"])
        if not email and not phone:
            no_contact_rows.append(row["row_id"])

    for bucket in list(by_email.values()) + list(by_phone_name.values()):
        for other_id in bucket[1:]:
            union(bucket[0], other_id)

    def find(value: str) -> str:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    groups: dict[str, list[dict]] = defaultdict(list)
    for row in records:
        groups[find(row["row_id"])].append(row)

    canonical_groups: list[dict] = []
    for rows in groups.values():
        rows = sorted(rows, key=lambda row: row["row_id"])
        master_candidates = [row for row in rows if row.get("master_hint")]
        if master_candidates:
            master = sorted(master_candidates, key=lambda row: source_rank(row, "contact"))[0]
        else:
            master = sorted(rows, key=lambda row: source_rank(row, "contact"))[0]
        name, name_source = choose_contact_field(rows, "person_or_org_name", "name_region")
        email, contact_source_email = choose_contact_field(rows, "email", "contact")
        phone, contact_source_phone = choose_contact_field(rows, "phone", "contact")
        city, city_source = choose_contact_field(rows, "city", "contact")
        region, depot_source = choose_contact_field(rows, "region", "name_region")
        consent, consent_source = choose_contact_field(rows, "consent_status", "contact")
        status, status_source = choose_contact_field(rows, "record_status", "contact")
        has_contact = bool(email or phone)
        if not has_contact:
            outreach_code = "OR-60"
            resolution = "NO_USABLE_CONTACT"
            identity_code = "IC-40"
            provenance_code = "FP-75"
        elif status == "INACTIVE":
            outreach_code = "OR-15"
            resolution = "SINGLE_SOURCE" if len(rows) == 1 else "FIELD_LEVEL_PRECEDENCE_APPLIED"
            identity_code = "IC-70" if len(rows) > 1 else "IC-25"
            provenance_code = "FP-55" if len(rows) > 1 else "FP-20"
        elif consent == "GRANTED":
            outreach_code = "OR-35"
            resolution = "SINGLE_SOURCE" if len(rows) == 1 else "FIELD_LEVEL_PRECEDENCE_APPLIED"
            identity_code = "IC-70" if len(rows) > 1 else "IC-25"
            provenance_code = "FP-55" if len(rows) > 1 else "FP-20"
        else:
            outreach_code = "OR-80"
            resolution = "SINGLE_SOURCE" if len(rows) == 1 else "FIELD_LEVEL_PRECEDENCE_APPLIED"
            identity_code = "IC-70" if len(rows) > 1 else "IC-25"
            provenance_code = "FP-55" if len(rows) > 1 else "FP-20"
        canonical_groups.append(
            {
                "member_row_ids": [row["row_id"] for row in rows],
                "master_id": master["row_id"],
                "canonical_name": name,
                "canonical_email": email,
                "canonical_phone_digits": phone,
                "canonical_city": city,
                "region": region,
                "canonical_consent_status": consent,
                "canonical_record_status": status,
                "name_source_system": name_source,
                "contact_source_system": contact_source_email or contact_source_phone,
                "city_source_system": city_source,
                "depot_source_system": depot_source,
                "consent_source_system": consent_source,
                "status_source_system": status_source,
                "resolution_outcome": resolution,
                "identity_code": identity_code,
                "outreach_code": outreach_code,
                "field_provenance_code": provenance_code,
            }
        )

    readiness = Counter()
    readiness_by_region: dict[str, Counter] = defaultdict(Counter)
    dispatchable_master_ids: list[str] = []
    for group in canonical_groups:
        has_email = bool(group["canonical_email"])
        has_phone = bool(group["canonical_phone_digits"])
        region = group["region"]
        if not has_email and not has_phone:
            disposition = "blocked_no_contact"
        elif group["canonical_record_status"] == "INACTIVE":
            disposition = "blocked_inactive"
        elif group["canonical_consent_status"] != "GRANTED":
            disposition = "blocked_consent"
        else:
            disposition = "dispatchable"
            dispatchable_master_ids.append(group["master_id"])
        readiness_by_region[region]["total_person_count"] += 1
        readiness_by_region[region][disposition] += 1
        if disposition == "dispatchable":
            if has_email and has_phone:
                readiness["both"] += 1
            elif has_email:
                readiness["email_only"] += 1
            elif has_phone:
                readiness["phone_only"] += 1
        elif disposition != "blocked_inactive" and (has_email or has_phone):
            readiness["not_ready"] += 1

    return {
        "collection_id": collection,
        "raw_row_count": len(records),
        "canonical_person_count": len(canonical_groups),
        "merged_duplicate_cluster_count": sum(1 for group in canonical_groups if len(group["member_row_ids"]) > 1),
        "quarantine_row_count": len(no_contact_rows),
        "quarantine_row_ids": sorted(no_contact_rows),
        "dispatchable_master_ids": sorted(dispatchable_master_ids),
        "channel_readiness": {key: readiness.get(key, 0) for key in ["both", "email_only", "phone_only", "not_ready"]},
        "readiness_by_region": [
            {
                "region": region,
                "total_person_count": counts["total_person_count"],
                "dispatchable_person_count": counts["dispatchable"],
                "blocked_consent_count": counts["blocked_consent"],
                "blocked_no_contact_count": counts["blocked_no_contact"],
                "blocked_inactive_count": counts["blocked_inactive"],
            }
            for region, counts in sorted(readiness_by_region.items())
        ],
        "canonical_groups": sorted(canonical_groups, key=lambda group: group["member_row_ids"][0]),
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url")
    parser.add_argument("--env", default="environment_access.md")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch")
    fetch_parser.add_argument("--family", choices=sorted(ENDPOINTS), required=True)
    fetch_parser.add_argument("--collection", required=True)

    ledger_parser = subparsers.add_parser("classify-ledger")
    ledger_parser.add_argument("--family", choices=["fuel", "freight"], required=True)
    ledger_parser.add_argument("--collection", required=True)

    contact_parser = subparsers.add_parser("classify-contacts")
    contact_parser.add_argument("--collection", required=True)

    maintenance_parser = subparsers.add_parser("classify-maintenance")
    maintenance_parser.add_argument("--collection", required=True)

    args = parser.parse_args(argv)
    base_url = load_base_url(args)
    if args.command == "fetch":
        result = {
            "collection_id": args.collection,
            "family": args.family,
            "snapshots": snapshots(base_url, args.collection),
            "records": fetch_all(base_url, ENDPOINTS[args.family], {"collection": args.collection}),
        }
    elif args.command == "classify-ledger":
        result = classify_ledger(base_url, args.family, args.collection)
    elif args.command == "classify-contacts":
        result = classify_contacts(base_url, args.collection)
    elif args.command == "classify-maintenance":
        result = classify_maintenance(base_url, args.collection)
    else:
        raise AssertionError(args.command)
    json.dump(result, sys.stdout, indent=2, sort_keys=True, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
