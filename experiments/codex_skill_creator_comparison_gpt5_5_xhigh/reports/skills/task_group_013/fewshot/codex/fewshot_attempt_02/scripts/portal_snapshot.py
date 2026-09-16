#!/usr/bin/env python3
"""
Collect a focused Cedar Ridge portal snapshot for intake JSON tasks.

This script uses only the task portal HTTP API. It requires no third-party
packages and prints one JSON object to stdout.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict


def normalize_base_url(raw: str) -> str:
    base = raw.strip()
    if not base:
        raise SystemExit("base URL is required")
    return base.rstrip("/") + "/"


def request_json(base_url: str, path: str, method: str = "GET", payload=None):
    url = urllib.parse.urljoin(base_url, path.lstrip("/"))
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise SystemExit(f"{method} {url} failed: HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"{method} {url} failed: {exc}") from exc
    return json.loads(body)


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_in(values) -> str:
    values = [v for v in values if v]
    if not values:
        return "('')"
    return "(" + ",".join(sql_literal(v) for v in values) + ")"


def query(base_url: str, sql: str):
    return request_json(base_url, "/query", method="POST", payload={"sql": sql})


def add_unique(target: OrderedDict, values):
    for value in values:
        if value:
            target[value] = True


def rows(result):
    return result.get("rows", []) if isinstance(result, dict) else []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Task environment base URL")
    parser.add_argument("--schema", action="store_true", help="Include SQLite table schema")
    parser.add_argument("--roster-id", action="append", default=[], help="Intake roster ID")
    parser.add_argument("--referral-batch-id", action="append", default=[], help="Referral batch ID")
    parser.add_argument("--transfer-batch-id", action="append", default=[], help="Dialysis transfer batch ID")
    parser.add_argument("--program-code", action="append", default=[], help="Program code")
    parser.add_argument("--patient-id", action="append", default=[], help="Explicit patient ID")
    args = parser.parse_args()

    base_url = normalize_base_url(args.base_url)
    patient_ids = OrderedDict((pid, True) for pid in args.patient_id)
    referral_ids = OrderedDict()
    transfer_ids = OrderedDict()
    icd_codes = OrderedDict()
    capacity_dates = OrderedDict()
    modalities = OrderedDict()

    snapshot = {
        "source_base_url": base_url,
        "rosters": {},
        "referral_batches": {},
        "transfer_batches": {},
        "programs": {},
        "patients": {},
        "charts": {},
        "lookup_tables": {},
    }

    if args.schema:
        snapshot["schema"] = query(
            base_url,
            "select name, sql from sqlite_master where type = 'table' order by name",
        )

    for roster_id in args.roster_id:
        result = query(
            base_url,
            "select * from intake_rosters "
            f"where roster_id = {sql_literal(roster_id)} "
            "order by patient_id",
        )
        snapshot["rosters"][roster_id] = result
        add_unique(patient_ids, (row.get("patient_id") for row in rows(result)))

    for batch_id in args.referral_batch_id:
        result = query(
            base_url,
            "select * from referrals "
            f"where batch_id = {sql_literal(batch_id)} "
            "order by referral_id",
        )
        batch_rows = rows(result)
        snapshot["referral_batches"][batch_id] = result
        add_unique(patient_ids, (row.get("patient_id") for row in batch_rows))
        add_unique(referral_ids, (row.get("referral_id") for row in batch_rows))
        add_unique(icd_codes, (row.get("icd10_code") for row in batch_rows))

    for batch_id in args.transfer_batch_id:
        result = query(
            base_url,
            "select * from transfer_requests "
            f"where batch_id = {sql_literal(batch_id)} "
            "order by transfer_id",
        )
        batch_rows = rows(result)
        snapshot["transfer_batches"][batch_id] = result
        add_unique(patient_ids, (row.get("patient_id") for row in batch_rows))
        add_unique(transfer_ids, (row.get("transfer_id") for row in batch_rows))
        add_unique(capacity_dates, (row.get("requested_start_date") for row in batch_rows))
        add_unique(modalities, (row.get("modality") for row in batch_rows))

    for program_code in args.program_code:
        program = request_json(base_url, f"/programs/{urllib.parse.quote(program_code)}/candidates")
        snapshot["programs"][program_code] = program
        add_unique(patient_ids, (row.get("patient_id") for row in program.get("candidates", [])))

    if patient_ids:
        patient_list = list(patient_ids)
        for patient_id in patient_list:
            snapshot["patients"][patient_id] = request_json(
                base_url,
                f"/patients/{urllib.parse.quote(patient_id)}",
            )
            snapshot["charts"][patient_id] = request_json(
                base_url,
                f"/chart/{urllib.parse.quote(patient_id)}",
            )

        patient_filter = sql_in(patient_list)
        snapshot["lookup_tables"]["coverage"] = query(
            base_url,
            "select * from coverage "
            f"where patient_id in {patient_filter} order by patient_id, coverage_id",
        )
        snapshot["lookup_tables"]["pbm"] = query(
            base_url,
            "select * from pbm "
            f"where patient_id in {patient_filter} order by patient_id, pbm_id",
        )
        snapshot["lookup_tables"]["lifestyle"] = query(
            base_url,
            "select * from lifestyle "
            f"where patient_id in {patient_filter} order by patient_id",
        )
        snapshot["lookup_tables"]["clinical_history"] = query(
            base_url,
            "select * from clinical_history "
            f"where patient_id in {patient_filter} order by patient_id",
        )
        snapshot["lookup_tables"]["chart_artifacts"] = query(
            base_url,
            "select * from chart_artifacts "
            f"where patient_id in {patient_filter} order by patient_id, artifact_type",
        )
        snapshot["lookup_tables"]["patient_pharmacy"] = query(
            base_url,
            "select pp.*, ph.network_status, ph.name as pharmacy_name "
            "from patient_pharmacy pp join pharmacies ph on ph.pharmacy_id = pp.pharmacy_id "
            f"where pp.patient_id in {patient_filter} "
            "order by pp.patient_id, pp.preference_rank",
        )

    if referral_ids:
        snapshot["lookup_tables"]["referral_documents"] = query(
            base_url,
            "select * from documents "
            f"where referral_id in {sql_in(list(referral_ids))} "
            "order by referral_id, doc_type, received_date desc",
        )

    if transfer_ids:
        snapshot["lookup_tables"]["transfer_documents"] = query(
            base_url,
            "select * from documents "
            f"where transfer_id in {sql_in(list(transfer_ids))} "
            "order by transfer_id, doc_type, received_date desc",
        )

    if capacity_dates:
        date_filter = sql_in(list(capacity_dates))
        modality_filter = sql_in(list(modalities))
        snapshot["lookup_tables"]["capacity"] = query(
            base_url,
            "select * from facility_capacity "
            f"where date in {date_filter} and modality in {modality_filter} "
            "order by date, modality, location_id",
        )

    if icd_codes:
        snapshot["lookup_tables"]["icd"] = {
            code: request_json(base_url, f"/icd/{urllib.parse.quote(code)}")
            for code in icd_codes
        }

    snapshot["lookup_tables"]["pharmacies"] = request_json(base_url, "/pharmacies")
    json.dump(snapshot, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
