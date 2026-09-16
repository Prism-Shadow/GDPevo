#!/usr/bin/env python3
"""Collect filtered Cedar Ridge portal context for intake tasks.

This helper fetches source data only. It does not derive final statuses or
produce an answer JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


def _base(url: str) -> str:
    return url.rstrip("/")


def _get(base_url: str, path: str) -> Any:
    with urllib.request.urlopen(_base(base_url) + path, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_sql(base_url: str, sql: str) -> Any:
    data = json.dumps({"sql": sql}).encode("utf-8")
    request = urllib.request.Request(
        _base(base_url) + "/query",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _in(values: set[str]) -> str:
    return "(" + ", ".join(_quote(value) for value in sorted(values)) + ")"


def _rows(result: Any) -> list[dict[str, Any]]:
    if isinstance(result, dict) and isinstance(result.get("rows"), list):
        return result["rows"]
    return []


def _append_ids(rows: list[dict[str, Any]], field: str, target: set[str]) -> None:
    for row in rows:
        value = row.get(field)
        if value:
            target.add(str(value))


def collect(args: argparse.Namespace) -> dict[str, Any]:
    out: dict[str, Any] = {
        "base_url": _base(args.base_url),
        "selectors": {
            "roster_ids": sorted(args.roster_id),
            "batch_ids": sorted(args.batch_id),
            "program_codes": sorted(args.program_code),
            "patient_ids": sorted(args.patient_id),
            "referral_ids": sorted(args.referral_id),
            "transfer_ids": sorted(args.transfer_id),
        },
        "sql": {},
        "rest": {},
    }

    patient_ids = set(args.patient_id)
    referral_ids = set(args.referral_id)
    transfer_ids = set(args.transfer_id)
    icd_codes = set()
    capacity_dates = set()
    modalities = set()

    if args.roster_id:
        result = _post_sql(
            args.base_url,
            "select * from intake_rosters "
            f"where roster_id in {_in(set(args.roster_id))} "
            "order by roster_id, patient_id",
        )
        rows = _rows(result)
        out["sql"]["intake_rosters"] = result
        _append_ids(rows, "patient_id", patient_ids)

    if args.batch_id:
        batch_filter = _in(set(args.batch_id))
        referrals = _post_sql(
            args.base_url,
            "select * from referrals "
            f"where batch_id in {batch_filter} order by batch_id, referral_id",
        )
        referral_rows = _rows(referrals)
        out["sql"]["referrals"] = referrals
        _append_ids(referral_rows, "patient_id", patient_ids)
        _append_ids(referral_rows, "referral_id", referral_ids)
        _append_ids(referral_rows, "icd10_code", icd_codes)

        transfers = _post_sql(
            args.base_url,
            "select * from transfer_requests "
            f"where batch_id in {batch_filter} order by batch_id, transfer_id",
        )
        transfer_rows = _rows(transfers)
        out["sql"]["transfer_requests"] = transfers
        _append_ids(transfer_rows, "patient_id", patient_ids)
        _append_ids(transfer_rows, "transfer_id", transfer_ids)
        _append_ids(transfer_rows, "requested_start_date", capacity_dates)
        _append_ids(transfer_rows, "modality", modalities)

    for program_code in args.program_code:
        encoded = urllib.parse.quote(program_code, safe="")
        result = _get(args.base_url, f"/programs/{encoded}/candidates")
        out["rest"][f"program_candidates:{program_code}"] = result
        for candidate in result.get("candidates", []):
            patient_id = candidate.get("patient_id")
            if patient_id:
                patient_ids.add(str(patient_id))

    if referral_ids:
        docs = _post_sql(
            args.base_url,
            "select * from documents "
            f"where referral_id in {_in(referral_ids)} "
            "order by referral_id, doc_type, document_id",
        )
        out["sql"]["referral_documents"] = docs

    if transfer_ids:
        docs = _post_sql(
            args.base_url,
            "select * from documents "
            f"where transfer_id in {_in(transfer_ids)} "
            "order by transfer_id, doc_type, document_id",
        )
        out["sql"]["transfer_documents"] = docs

    if patient_ids:
        out["sql"]["patients"] = _post_sql(
            args.base_url,
            f"select * from patients where patient_id in {_in(patient_ids)} "
            "order by patient_id",
        )
        out["sql"]["coverage"] = _post_sql(
            args.base_url,
            f"select * from coverage where patient_id in {_in(patient_ids)} "
            "order by patient_id, coverage_id",
        )
        out["sql"]["pbm"] = _post_sql(
            args.base_url,
            f"select * from pbm where patient_id in {_in(patient_ids)} "
            "order by patient_id, pbm_id",
        )
        out["sql"]["lifestyle"] = _post_sql(
            args.base_url,
            f"select * from lifestyle where patient_id in {_in(patient_ids)} "
            "order by patient_id",
        )
        out["sql"]["patient_pharmacy"] = _post_sql(
            args.base_url,
            "select pp.*, ph.network_status, ph.name from patient_pharmacy pp "
            "join pharmacies ph on ph.pharmacy_id = pp.pharmacy_id "
            f"where pp.patient_id in {_in(patient_ids)} "
            "order by pp.patient_id, pp.preference_rank",
        )
        out["sql"]["clinical_history"] = _post_sql(
            args.base_url,
            f"select * from clinical_history where patient_id in {_in(patient_ids)} "
            "order by patient_id",
        )
        out["sql"]["chart_artifacts"] = _post_sql(
            args.base_url,
            f"select * from chart_artifacts where patient_id in {_in(patient_ids)} "
            "order by patient_id, artifact_type, artifact_id",
        )
        charts: dict[str, Any] = {}
        for patient_id in sorted(patient_ids):
            charts[patient_id] = _get(args.base_url, f"/chart/{urllib.parse.quote(patient_id, safe='')}")
        out["rest"]["charts"] = charts

    if icd_codes:
        out["sql"]["icd_codes"] = _post_sql(
            args.base_url,
            f"select * from icd_codes where code in {_in(icd_codes)} order by code",
        )

    if capacity_dates and modalities:
        out["sql"]["facility_capacity"] = _post_sql(
            args.base_url,
            "select * from facility_capacity "
            f"where date in {_in(capacity_dates)} and modality in {_in(modalities)} "
            "order by date, modality, location_id",
        )

    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--roster-id", action="append", default=[])
    parser.add_argument("--batch-id", action="append", default=[])
    parser.add_argument("--program-code", action="append", default=[])
    parser.add_argument("--patient-id", action="append", default=[])
    parser.add_argument("--referral-id", action="append", default=[])
    parser.add_argument("--transfer-id", action="append", default=[])
    parser.add_argument("--out")
    args = parser.parse_args()

    try:
        data = collect(args)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"collect_portal_context.py: {exc}", file=sys.stderr)
        return 1

    rendered = json.dumps(data, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(rendered + "\n")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
