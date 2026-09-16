#!/usr/bin/env python3
"""Fetch task-relevant Cedar Ridge portal rows as JSON."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request


def post_sql(base_url: str, sql: str) -> list[dict]:
    url = base_url.rstrip("/") + "/query"
    data = json.dumps({"sql": sql}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.load(response)
    if "error" in payload:
        raise RuntimeError(payload["error"])
    return payload.get("rows", [])


def quote_sql(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def in_clause(values: list[str]) -> str:
    if not values:
        return "(NULL)"
    return "(" + ",".join(quote_sql(value) for value in values) + ")"


def rows_for_ids(base_url: str, table: str, id_column: str, ids: list[str], order_by: str) -> list[dict]:
    if not ids:
        return []
    sql = f"select * from {table} where {id_column} in {in_clause(ids)} order by {order_by}"
    return post_sql(base_url, sql)


def snapshot_roster(base_url: str, target_id: str) -> dict:
    roster = post_sql(
        base_url,
        "select * from intake_rosters "
        f"where roster_id = {quote_sql(target_id)} order by patient_id",
    )
    patient_ids = sorted({row["patient_id"] for row in roster})
    return {
        "kind": "roster",
        "target_id": target_id,
        "intake_rosters": roster,
        "patients": rows_for_ids(base_url, "patients", "patient_id", patient_ids, "patient_id"),
        "coverage": rows_for_ids(base_url, "coverage", "patient_id", patient_ids, "patient_id, coverage_id"),
        "pbm": rows_for_ids(base_url, "pbm", "patient_id", patient_ids, "patient_id, pbm_id"),
        "lifestyle": rows_for_ids(base_url, "lifestyle", "patient_id", patient_ids, "patient_id"),
        "patient_pharmacy": rows_for_ids(
            base_url,
            "patient_pharmacy",
            "patient_id",
            patient_ids,
            "patient_id, preference_rank, pharmacy_id",
        ),
        "pharmacies": post_sql(base_url, "select * from pharmacies order by pharmacy_id"),
    }


def snapshot_referral_batch(base_url: str, target_id: str) -> dict:
    referrals = post_sql(
        base_url,
        "select * from referrals "
        f"where batch_id = {quote_sql(target_id)} order by referral_id",
    )
    referral_ids = sorted({row["referral_id"] for row in referrals})
    patient_ids = sorted({row["patient_id"] for row in referrals})
    icd_codes = sorted({row["icd10_code"] for row in referrals if row.get("icd10_code")})
    return {
        "kind": "referral-batch",
        "target_id": target_id,
        "referrals": referrals,
        "patients": rows_for_ids(base_url, "patients", "patient_id", patient_ids, "patient_id"),
        "icd_codes": rows_for_ids(base_url, "icd_codes", "code", icd_codes, "code"),
        "chart_artifacts": rows_for_ids(
            base_url,
            "chart_artifacts",
            "patient_id",
            patient_ids,
            "patient_id, artifact_type, artifact_id",
        ),
        "documents": rows_for_ids(
            base_url,
            "documents",
            "referral_id",
            referral_ids,
            "referral_id, doc_type, document_id",
        ),
    }


def snapshot_transfer_batch(base_url: str, target_id: str) -> dict:
    transfers = post_sql(
        base_url,
        "select * from transfer_requests "
        f"where batch_id = {quote_sql(target_id)} order by transfer_id",
    )
    transfer_ids = sorted({row["transfer_id"] for row in transfers})
    patient_ids = sorted({row["patient_id"] for row in transfers})
    dates = sorted({row["requested_start_date"] for row in transfers if row.get("requested_start_date")})
    modalities = sorted({row["modality"] for row in transfers if row.get("modality")})
    capacity = []
    if dates and modalities:
        capacity = post_sql(
            base_url,
            "select date, modality, sum(open_chairs) as open_chairs_total "
            "from facility_capacity "
            f"where date in {in_clause(dates)} and modality in {in_clause(modalities)} "
            "group by date, modality order by date, modality",
        )
    return {
        "kind": "transfer-batch",
        "target_id": target_id,
        "transfer_requests": transfers,
        "patients": rows_for_ids(base_url, "patients", "patient_id", patient_ids, "patient_id"),
        "documents": rows_for_ids(
            base_url,
            "documents",
            "transfer_id",
            transfer_ids,
            "transfer_id, doc_type, document_id",
        ),
        "facility_capacity": capacity,
    }


def snapshot_program(base_url: str, target_id: str) -> dict:
    candidates = post_sql(
        base_url,
        "select * from program_candidates "
        f"where program_code = {quote_sql(target_id)} order by patient_id",
    )
    patient_ids = sorted({row["patient_id"] for row in candidates})
    return {
        "kind": "program",
        "target_id": target_id,
        "program_candidates": candidates,
        "patients": rows_for_ids(base_url, "patients", "patient_id", patient_ids, "patient_id"),
        "clinical_history": rows_for_ids(base_url, "clinical_history", "patient_id", patient_ids, "patient_id"),
        "chart_artifacts": rows_for_ids(
            base_url,
            "chart_artifacts",
            "patient_id",
            patient_ids,
            "patient_id, artifact_type, artifact_id",
        ),
    }


SNAPSHOTTERS = {
    "roster": snapshot_roster,
    "referral-batch": snapshot_referral_batch,
    "transfer-batch": snapshot_transfer_batch,
    "program": snapshot_program,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Portal base URL, for example http://task-env:9013")
    parser.add_argument("--kind", required=True, choices=sorted(SNAPSHOTTERS))
    parser.add_argument("--id", required=True, help="Roster ID, batch ID, or program code")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        snapshot = SNAPSHOTTERS[args.kind](args.base_url, args.id)
    except (urllib.error.URLError, RuntimeError) as exc:
        print(f"portal_snapshot.py: {exc}", file=sys.stderr)
        return 1
    json.dump(snapshot, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
