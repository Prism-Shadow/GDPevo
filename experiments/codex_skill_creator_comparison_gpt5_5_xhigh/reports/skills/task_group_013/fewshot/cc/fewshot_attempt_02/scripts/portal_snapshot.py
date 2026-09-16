#!/usr/bin/env python3
"""Fetch scoped Cedar Ridge portal snapshots for intake JSON tasks."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict


def base_url(value: str) -> str:
    return value.rstrip("/")


def read_json(url: str, payload: dict | None = None) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if payload is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} for {url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach {url}: {exc}") from exc


def get_json(root: str, path: str) -> dict:
    quoted = "/".join(urllib.parse.quote(part, safe="") for part in path.strip("/").split("/"))
    return read_json(f"{root}/{quoted}")


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_in(values: list[str]) -> str:
    if not values:
        return "('')"
    return "(" + ",".join(sql_literal(value) for value in values) + ")"


def query(root: str, sql: str) -> dict:
    return read_json(f"{root}/query", {"sql": sql})


def rows(result: dict) -> list[dict]:
    return result.get("rows", [])


def print_json(data: dict) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def duplicate_candidates(referrals: list[dict]) -> dict:
    by_patient: dict[str, list[str]] = defaultdict(list)
    by_insurance: dict[str, list[dict]] = defaultdict(list)
    for referral in referrals:
        by_patient[str(referral.get("patient_id"))].append(referral["referral_id"])
        insurance_id = referral.get("insurance_id")
        if insurance_id:
            by_insurance[str(insurance_id)].append(referral)

    same_patient = [
        {"patient_id": patient_id, "referral_ids": sorted(ids)}
        for patient_id, ids in sorted(by_patient.items())
        if len(ids) > 1
    ]
    shared_insurance = []
    for insurance_id, group in sorted(by_insurance.items()):
        patient_ids = sorted({str(item.get("patient_id")) for item in group})
        if len(group) > 1:
            shared_insurance.append(
                {
                    "insurance_id": insurance_id,
                    "patient_ids": patient_ids,
                    "referral_ids": sorted(str(item["referral_id"]) for item in group),
                    "distinct_patient_count": len(patient_ids),
                }
            )
    return {"same_patient_referrals": same_patient, "shared_insurance_ids": shared_insurance}


def command_roster(args: argparse.Namespace) -> dict:
    root = base_url(args.base_url)
    roster_id = args.roster_id
    patient_filter = ""
    if args.patients:
        patient_filter = f" and patient_id in {sql_in(args.patients)}"
    roster_rows = rows(
        query(
            root,
            "select roster_id,patient_id,requested_service_date,service_line,source_note "
            f"from intake_rosters where roster_id={sql_literal(roster_id)}{patient_filter} "
            "order by patient_id",
        )
    )
    patient_ids = [row["patient_id"] for row in roster_rows]
    patients = {patient_id: get_json(root, f"/patients/{patient_id}") for patient_id in patient_ids}
    return {"kind": "roster", "roster_id": roster_id, "roster": roster_rows, "patients": patients}


def command_referral_batch(args: argparse.Namespace) -> dict:
    root = base_url(args.base_url)
    batch_id = args.batch_id
    referral_rows = rows(
        query(
            root,
            "select referral_id,batch_id,service_line,date_received,patient_id,payer,insurance_id,"
            "referring_physician,referring_practice,referring_phone,referring_fax,icd10_code,"
            "diagnosis_description,referral_reason,urgency,records_received,imaging_received,"
            "auth_required,auth_status,appointment_scheduled,appointment_date,assigned_physician,notes "
            f"from referrals where batch_id={sql_literal(batch_id)} order by referral_id",
        )
    )
    referral_ids = [row["referral_id"] for row in referral_rows]
    patient_ids = sorted({row["patient_id"] for row in referral_rows})
    codes = sorted({row["icd10_code"] for row in referral_rows if row.get("icd10_code")})
    docs = []
    if referral_ids:
        docs = rows(
            query(
                root,
                "select referral_id,patient_id,doc_type,status,finalized,received_date,content_tag,notes "
                f"from documents where referral_id in {sql_in(referral_ids)} order by referral_id,doc_type",
            )
        )
    icd = {}
    for code in codes:
        icd[code] = get_json(root, f"/icd/{code}").get("icd")
    charts = {}
    if args.charts:
        charts = {patient_id: get_json(root, f"/chart/{patient_id}") for patient_id in patient_ids}
    return {
        "kind": "referral_batch",
        "batch_id": batch_id,
        "referrals": referral_rows,
        "documents": docs,
        "icd_by_code": icd,
        "duplicate_candidates": duplicate_candidates(referral_rows),
        "charts_by_patient": charts,
    }


def command_transfer_batch(args: argparse.Namespace) -> dict:
    root = base_url(args.base_url)
    batch_id = args.batch_id
    transfer_rows = rows(
        query(
            root,
            "select transfer_id,batch_id,patient_id,referring_facility,requested_start_date,"
            "requested_end_date,modality,days_requested,chair_window,transportation,status_note "
            f"from transfer_requests where batch_id={sql_literal(batch_id)} order by transfer_id",
        )
    )
    transfer_ids = [row["transfer_id"] for row in transfer_rows]
    docs = []
    if transfer_ids:
        docs = rows(
            query(
                root,
                "select transfer_id,patient_id,doc_type,status,finalized,received_date,service_date,content_tag,notes "
                f"from documents where transfer_id in {sql_in(transfer_ids)} order by transfer_id,doc_type",
            )
        )
    capacity_by_start = []
    if transfer_rows:
        pairs = sorted({(row["requested_start_date"], row["modality"]) for row in transfer_rows})
        clauses = [f"(date={sql_literal(date)} and modality={sql_literal(modality)})" for date, modality in pairs]
        capacity_by_start = rows(
            query(
                root,
                "select date,modality,sum(open_chairs) as open_chairs_total "
                "from facility_capacity where "
                + " or ".join(clauses)
                + " group by date,modality order by date,modality",
            )
        )
    patients = {row["patient_id"]: get_json(root, f"/patients/{row['patient_id']}") for row in transfer_rows}
    return {
        "kind": "transfer_batch",
        "batch_id": batch_id,
        "transfers": transfer_rows,
        "documents": docs,
        "capacity_by_requested_start": capacity_by_start,
        "patients": patients,
    }


def command_program(args: argparse.Namespace) -> dict:
    root = base_url(args.base_url)
    program_code = args.program_code
    candidates_payload = get_json(root, f"/programs/{program_code}/candidates")
    candidates = candidates_payload.get("candidates", [])
    patient_ids = [candidate["patient_id"] for candidate in candidates]
    charts = {patient_id: get_json(root, f"/chart/{patient_id}") for patient_id in patient_ids}
    return {
        "kind": "program",
        "program_code": program_code,
        "candidates_payload": candidates_payload,
        "charts_by_patient": charts,
    }


def command_ids(args: argparse.Namespace, kind: str) -> dict:
    root = base_url(args.base_url)
    path_by_kind = {
        "patient": "patients",
        "referral": "referrals",
        "transfer": "transfers",
        "chart": "chart",
    }
    root_path = path_by_kind[kind]
    return {
        "kind": kind,
        "records": {record_id: get_json(root, f"/{root_path}/{record_id}") for record_id in args.ids},
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Task environment base URL, for example http://task-env:9013")
    sub = parser.add_subparsers(dest="command", required=True)

    roster = sub.add_parser("roster", help="Fetch a roster and patient bundles")
    roster.add_argument("roster_id")
    roster.add_argument("--patients", nargs="*", help="Optional patient IDs to limit within the roster")

    referrals = sub.add_parser("referral-batch", help="Fetch referrals, ICD, docs, duplicate candidates, and optional charts")
    referrals.add_argument("batch_id")
    referrals.add_argument("--charts", action="store_true", help="Also fetch /chart for each referral patient")

    transfers = sub.add_parser("transfer-batch", help="Fetch transfer requests, packet docs, capacity, and patients")
    transfers.add_argument("batch_id")

    program = sub.add_parser("program", help="Fetch program candidates and charts")
    program.add_argument("program_code")

    for name in ("patient", "referral", "transfer", "chart"):
        item = sub.add_parser(name, help=f"Fetch one or more {name} records")
        item.add_argument("ids", nargs="+")

    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "roster":
        data = command_roster(args)
    elif args.command == "referral-batch":
        data = command_referral_batch(args)
    elif args.command == "transfer-batch":
        data = command_transfer_batch(args)
    elif args.command == "program":
        data = command_program(args)
    elif args.command in {"patient", "referral", "transfer", "chart"}:
        data = command_ids(args, args.command)
    else:
        parser.error("unknown command")
    print_json(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
