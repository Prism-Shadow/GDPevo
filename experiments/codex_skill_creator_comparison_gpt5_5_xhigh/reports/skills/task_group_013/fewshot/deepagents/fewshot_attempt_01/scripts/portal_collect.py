#!/usr/bin/env python3
"""Collect Cedar Ridge portal evidence for intake JSON tasks."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request


CORE_TABLES = [
    "patients",
    "intake_rosters",
    "coverage",
    "pbm",
    "patient_pharmacy",
    "pharmacies",
    "lifestyle",
    "clinical_history",
    "referrals",
    "documents",
    "transfer_requests",
    "facility_capacity",
    "program_candidates",
    "chart_artifacts",
    "icd_codes",
]


def normalize_base(url: str) -> str:
    return url.rstrip("/")


def get_json(base_url: str, path: str) -> object:
    url = normalize_base(base_url) + path
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def post_sql(base_url: str, sql: str) -> object:
    url = normalize_base(base_url) + "/query"
    body = json.dumps({"sql": sql}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def quote_sql(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def rows(result: object) -> list[dict]:
    if isinstance(result, dict) and isinstance(result.get("rows"), list):
        return result["rows"]
    return []


def split_ids(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.replace(",", " ").split() if item.strip()]


def collect_schema(base_url: str) -> dict:
    return {table: post_sql(base_url, f"pragma table_info({table})") for table in CORE_TABLES}


def collect_patients(base_url: str, patient_ids: list[str]) -> dict:
    return {patient_id: get_json(base_url, f"/patients/{urllib.parse.quote(patient_id)}") for patient_id in patient_ids}


def collect_charts(base_url: str, patient_ids: list[str]) -> dict:
    return {patient_id: get_json(base_url, f"/chart/{urllib.parse.quote(patient_id)}") for patient_id in patient_ids}


def collect_roster(base_url: str, roster_id: str, patient_ids: list[str]) -> dict:
    roster_rows = rows(
        post_sql(
            base_url,
            "select * from intake_rosters "
            f"where roster_id = {quote_sql(roster_id)} order by patient_id",
        )
    )
    ids = patient_ids or [row["patient_id"] for row in roster_rows]
    return {
        "roster_id": roster_id,
        "roster_rows": roster_rows,
        "patients": collect_patients(base_url, ids),
        "pharmacies": get_json(base_url, "/pharmacies"),
    }


def collect_referral_batch(base_url: str, batch_id: str) -> dict:
    referral_rows = rows(
        post_sql(
            base_url,
            "select * from referrals "
            f"where batch_id = {quote_sql(batch_id)} order by referral_id",
        )
    )
    patient_ids = sorted({row["patient_id"] for row in referral_rows})
    referral_ids = [row["referral_id"] for row in referral_rows]
    details = {
        referral_id: get_json(base_url, f"/referrals/{urllib.parse.quote(referral_id)}")
        for referral_id in referral_ids
    }
    insurance_groups: dict[str, list[dict]] = {}
    patient_groups: dict[str, list[dict]] = {}
    for row in referral_rows:
        insurance_groups.setdefault(row.get("insurance_id"), []).append(row)
        patient_groups.setdefault(row.get("patient_id"), []).append(row)
    return {
        "batch_id": batch_id,
        "referrals": referral_rows,
        "details": details,
        "charts": collect_charts(base_url, patient_ids),
        "same_patient_groups": {
            key: value for key, value in patient_groups.items() if key and len(value) > 1
        },
        "shared_insurance_groups": {
            key: value
            for key, value in insurance_groups.items()
            if key and len({row["patient_id"] for row in value}) > 1
        },
    }


def collect_transfer_batch(base_url: str, batch_id: str) -> dict:
    transfer_rows = rows(
        post_sql(
            base_url,
            "select * from transfer_requests "
            f"where batch_id = {quote_sql(batch_id)} order by transfer_id",
        )
    )
    transfer_ids = [row["transfer_id"] for row in transfer_rows]
    patient_ids = sorted({row["patient_id"] for row in transfer_rows})
    quoted_ids = ", ".join(quote_sql(value) for value in transfer_ids) or "''"
    details = {
        transfer_id: get_json(base_url, f"/transfers/{urllib.parse.quote(transfer_id)}")
        for transfer_id in transfer_ids
    }
    return {
        "batch_id": batch_id,
        "transfers": transfer_rows,
        "details": details,
        "patients": collect_patients(base_url, patient_ids),
        "documents": rows(
            post_sql(
                base_url,
                "select * from documents "
                f"where transfer_id in ({quoted_ids}) order by transfer_id, doc_type, received_date",
            )
        ),
        "capacity_dates": rows(
            post_sql(
                base_url,
                "select date, modality, sum(open_chairs) as open_chairs_total "
                "from facility_capacity group by date, modality order by date, modality",
            )
        ),
    }


def collect_program(base_url: str, program_code: str) -> dict:
    program = get_json(base_url, f"/programs/{urllib.parse.quote(program_code)}/candidates")
    candidates = program.get("candidates", []) if isinstance(program, dict) else []
    patient_ids = sorted({row["patient_id"] for row in candidates})
    return {
        "program_code": program_code,
        "candidate_response": program,
        "charts": collect_charts(base_url, patient_ids),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Portal base URL")
    parser.add_argument("--schema", action="store_true", help="Include core table schemas")
    parser.add_argument("--roster", help="Roster id for new-patient access tasks")
    parser.add_argument("--patient-ids", help="Comma or space separated patient ids for roster mode")
    parser.add_argument("--referral-batch", help="Referral batch id")
    parser.add_argument("--transfer-batch", help="Transfer batch id")
    parser.add_argument("--program", help="Program code")
    args = parser.parse_args()

    output: dict[str, object] = {}
    try:
        if args.schema:
            output["schema"] = collect_schema(args.base_url)
        if args.roster:
            output["roster"] = collect_roster(
                args.base_url,
                args.roster,
                split_ids(args.patient_ids),
            )
        if args.referral_batch:
            output["referral_batch"] = collect_referral_batch(args.base_url, args.referral_batch)
        if args.transfer_batch:
            output["transfer_batch"] = collect_transfer_batch(args.base_url, args.transfer_batch)
        if args.program:
            output["program"] = collect_program(args.base_url, args.program)
    except urllib.error.HTTPError as exc:
        print(f"HTTP error {exc.code}: {exc.read().decode('utf-8', errors='replace')}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Network error: {exc}", file=sys.stderr)
        return 1

    json.dump(output, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
