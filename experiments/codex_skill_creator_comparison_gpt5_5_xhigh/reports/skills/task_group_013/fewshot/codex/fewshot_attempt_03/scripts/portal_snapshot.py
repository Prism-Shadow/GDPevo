#!/usr/bin/env python3
"""Fetch Cedar Ridge portal records from allowed GET endpoints and /query."""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request


def normalize_base_url(raw):
    return raw.rstrip("/") + "/"


def sql_literal(value):
    return "'" + value.replace("'", "''") + "'"


def request_json(base_url, path, method="GET", payload=None):
    url = urllib.parse.urljoin(base_url, path.lstrip("/"))
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} for {path}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Request failed for {path}: {exc}") from exc


def query(base_url, sql):
    return request_json(base_url, "/query", method="POST", payload={"sql": sql})


def rows_from_query(result):
    rows = result.get("rows")
    return rows if isinstance(rows, list) else []


def in_clause(values):
    values = sorted({value for value in values if value})
    if not values:
        return None
    return ", ".join(sql_literal(value) for value in values)


def add_related_for_referrals(base_url, output, referrals):
    referral_ids = [row.get("referral_id") for row in referrals]
    patient_ids = [row.get("patient_id") for row in referrals]
    icd_codes = [row.get("icd10_code") for row in referrals]
    insurance_ids = [row.get("insurance_id") for row in referrals]

    output["referral_details"] = {
        rid: request_json(base_url, f"/referrals/{urllib.parse.quote(rid)}")
        for rid in sorted(set(referral_ids))
        if rid
    }

    patient_clause = in_clause(patient_ids)
    referral_clause = in_clause(referral_ids)
    icd_clause = in_clause(icd_codes)
    insurance_clause = in_clause(insurance_ids)

    if patient_clause:
        output["patients_sql"] = query(
            base_url,
            f"select * from patients where patient_id in ({patient_clause}) order by patient_id",
        )
        output["chart_artifacts_sql"] = query(
            base_url,
            f"select * from chart_artifacts where patient_id in ({patient_clause}) order by patient_id, artifact_type",
        )
        output["clinical_history_sql"] = query(
            base_url,
            f"select * from clinical_history where patient_id in ({patient_clause}) order by patient_id",
        )
    if referral_clause:
        output["documents_sql"] = query(
            base_url,
            f"select * from documents where referral_id in ({referral_clause}) order by referral_id, doc_type, received_date",
        )
    if icd_clause:
        output["icd_sql"] = query(
            base_url,
            f"select * from icd_codes where code in ({icd_clause}) order by code",
        )
    if insurance_clause:
        output["shared_insurance_sql"] = query(
            base_url,
            f"select insurance_id, patient_id, referral_id from referrals where insurance_id in ({insurance_clause}) order by insurance_id, patient_id, referral_id",
        )


def add_related_for_roster(base_url, output, roster_rows):
    patient_ids = [row.get("patient_id") for row in roster_rows]
    patient_clause = in_clause(patient_ids)
    if not patient_clause:
        return
    output["patients_sql"] = query(
        base_url,
        f"select * from patients where patient_id in ({patient_clause}) order by patient_id",
    )
    output["coverage_sql"] = query(
        base_url,
        f"select * from coverage where patient_id in ({patient_clause}) order by patient_id, effective_date",
    )
    output["pbm_sql"] = query(
        base_url,
        f"select * from pbm where patient_id in ({patient_clause}) order by patient_id, pbm_id",
    )
    output["lifestyle_sql"] = query(
        base_url,
        f"select * from lifestyle where patient_id in ({patient_clause}) order by patient_id",
    )
    output["pharmacy_sql"] = query(
        base_url,
        "select pp.patient_id, pp.preference_rank, p.* "
        "from patient_pharmacy pp join pharmacies p on p.pharmacy_id = pp.pharmacy_id "
        f"where pp.patient_id in ({patient_clause}) "
        "order by pp.patient_id, pp.preference_rank",
    )


def add_related_for_transfers(base_url, output, transfers):
    transfer_ids = [row.get("transfer_id") for row in transfers]
    patient_ids = [row.get("patient_id") for row in transfers]
    modalities = [row.get("modality") for row in transfers]
    dates = [row.get("requested_start_date") for row in transfers]
    transfer_clause = in_clause(transfer_ids)
    patient_clause = in_clause(patient_ids)
    modality_clause = in_clause(modalities)
    date_clause = in_clause(dates)

    output["transfer_details"] = {
        tid: request_json(base_url, f"/transfers/{urllib.parse.quote(tid)}")
        for tid in sorted(set(transfer_ids))
        if tid
    }

    if transfer_clause:
        output["documents_sql"] = query(
            base_url,
            f"select * from documents where transfer_id in ({transfer_clause}) order by transfer_id, doc_type, received_date",
        )
    if patient_clause:
        output["patients_sql"] = query(
            base_url,
            f"select * from patients where patient_id in ({patient_clause}) order by patient_id",
        )
    if modality_clause and date_clause:
        output["capacity_sql"] = query(
            base_url,
            "select * from facility_capacity "
            f"where modality in ({modality_clause}) and date in ({date_clause}) "
            "order by date, modality, location_id",
        )


def add_related_for_program(base_url, output, candidates):
    patient_ids = [row.get("patient_id") for row in candidates]
    patient_clause = in_clause(patient_ids)
    if not patient_clause:
        return
    output["charts"] = {
        pid: request_json(base_url, f"/chart/{urllib.parse.quote(pid)}")
        for pid in sorted(set(patient_ids))
        if pid
    }
    output["patients_sql"] = query(
        base_url,
        f"select * from patients where patient_id in ({patient_clause}) order by patient_id",
    )
    output["chart_artifacts_sql"] = query(
        base_url,
        f"select * from chart_artifacts where patient_id in ({patient_clause}) order by patient_id, artifact_type",
    )
    output["clinical_history_sql"] = query(
        base_url,
        f"select * from clinical_history where patient_id in ({patient_clause}) order by patient_id",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", help="Task environment base URL")
    parser.add_argument("--get", action="append", default=[], help="Allowed GET path, repeatable")
    parser.add_argument("--sql", action="append", default=[], help="SQL query for POST /query, repeatable")
    parser.add_argument("--patient", action="append", default=[], help="Patient ID to fetch")
    parser.add_argument("--referral", action="append", default=[], help="Referral ID to fetch")
    parser.add_argument("--transfer", action="append", default=[], help="Transfer ID to fetch")
    parser.add_argument("--batch", help="Referral batch ID to snapshot with SQL")
    parser.add_argument("--transfer-batch", help="Transfer request batch ID to snapshot with SQL")
    parser.add_argument("--roster", help="Intake roster ID to snapshot with SQL")
    parser.add_argument("--program", help="Program code to snapshot")
    parser.add_argument("--include-related", action="store_true", help="Fetch related rows for batch, roster, transfer, or program snapshots")
    parser.add_argument("--out", help="Write JSON to this file instead of stdout")
    parser.add_argument("--indent", type=int, default=2)
    args = parser.parse_args()

    base_url = normalize_base_url(args.base_url)
    output = {"base_url": base_url}

    if args.get:
        output["get"] = {
            path: request_json(base_url, path)
            for path in args.get
        }

    if args.patient:
        output["patients"] = {
            pid: request_json(base_url, f"/patients/{urllib.parse.quote(pid)}")
            for pid in args.patient
        }

    if args.referral:
        output["referrals"] = {
            rid: request_json(base_url, f"/referrals/{urllib.parse.quote(rid)}")
            for rid in args.referral
        }

    if args.transfer:
        output["transfers"] = {
            tid: request_json(base_url, f"/transfers/{urllib.parse.quote(tid)}")
            for tid in args.transfer
        }

    if args.sql:
        output["sql"] = [
            {"sql": sql, "result": query(base_url, sql)}
            for sql in args.sql
        ]

    if args.batch:
        result = query(
            base_url,
            f"select * from referrals where batch_id = {sql_literal(args.batch)} order by referral_id",
        )
        output["batch_referrals_sql"] = result
        if args.include_related:
            add_related_for_referrals(base_url, output, rows_from_query(result))

    if args.transfer_batch:
        result = query(
            base_url,
            f"select * from transfer_requests where batch_id = {sql_literal(args.transfer_batch)} order by transfer_id",
        )
        output["transfer_batch_sql"] = result
        if args.include_related:
            add_related_for_transfers(base_url, output, rows_from_query(result))

    if args.roster:
        result = query(
            base_url,
            f"select * from intake_rosters where roster_id = {sql_literal(args.roster)} order by patient_id",
        )
        output["roster_sql"] = result
        if args.include_related:
            add_related_for_roster(base_url, output, rows_from_query(result))

    if args.program:
        result = request_json(base_url, f"/programs/{urllib.parse.quote(args.program)}/candidates")
        output["program_candidates"] = result
        if args.include_related:
            add_related_for_program(base_url, output, result.get("candidates", []))

    for transfer_id in args.transfer:
        if args.include_related:
            detail = request_json(base_url, f"/transfers/{urllib.parse.quote(transfer_id)}")
            add_related_for_transfers(base_url, output, [detail.get("transfer", detail)])

    rendered = json.dumps(output, indent=args.indent, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(rendered + "\n")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
