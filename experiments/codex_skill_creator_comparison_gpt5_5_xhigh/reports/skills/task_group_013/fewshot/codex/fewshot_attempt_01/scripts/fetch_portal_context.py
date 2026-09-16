#!/usr/bin/env python3
"""Fetch targeted Cedar Ridge portal context for JSON intake tasks."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional
import urllib.error
import urllib.parse
import urllib.request


def normalize_base_url(raw: str) -> str:
    base = raw.strip()
    if not base:
        raise ValueError("base URL is required")
    return base.rstrip("/") + "/"


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def request_json(url: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def query(base_url: str, sql: str) -> dict:
    result = request_json(urllib.parse.urljoin(base_url, "query"), {"sql": sql})
    if "error" in result:
        raise RuntimeError(result["error"])
    return result


def add_schema(out: dict, base_url: str) -> None:
    out["schema"] = query(
        base_url,
        """
        select m.name as table_name, p.cid, p.name as column_name, p.type
        from sqlite_master m
        join pragma_table_info(m.name) p
        where m.type = 'table'
        order by m.name, p.cid
        """,
    )


def add_roster(out: dict, base_url: str, roster_id: str) -> None:
    rid = sql_literal(roster_id)
    rosters = out.setdefault("rosters", {})
    rosters[roster_id] = query(
        base_url,
        f"""
        select r.roster_id, r.patient_id, r.requested_service_date, r.service_line,
               p.address, p.phone, p.email, p.existing_chart, p.preferred_contact,
               p.emergency_contact_present,
               c.status as coverage_status, c.effective_date, c.termination_date,
               c.network_status as coverage_network, c.service_lines,
               pbm.active as pbm_active, pbm.formulary_status, pbm.specialty_required,
               pbm.status as pbm_status,
               pp.pharmacy_id, ph.network_status as pharmacy_network,
               l.smoking_status, l.alcohol_use, l.exercise_frequency, l.sleep_hours
        from intake_rosters r
        left join patients p on p.patient_id = r.patient_id
        left join coverage c on c.patient_id = r.patient_id
        left join pbm on pbm.patient_id = r.patient_id
        left join patient_pharmacy pp on pp.patient_id = r.patient_id and pp.preference_rank = 1
        left join pharmacies ph on ph.pharmacy_id = pp.pharmacy_id
        left join lifestyle l on l.patient_id = r.patient_id
        where r.roster_id = {rid}
        order by r.patient_id
        """,
    )


def add_referral_batch(out: dict, base_url: str, batch_id: str) -> None:
    bid = sql_literal(batch_id)
    batches = out.setdefault("referral_batches", {})
    batch: dict = {}
    batches[batch_id] = batch
    batch["referrals"] = query(
        base_url,
        f"""
        select r.*, i.description as icd_description, i.chapter as icd_chapter,
               i.service_family as icd_service_family, i.laterality as icd_laterality
        from referrals r
        left join icd_codes i on i.code = r.icd10_code
        where r.batch_id = {bid}
        order by r.referral_id
        """,
    )
    batch["documents"] = query(
        base_url,
        f"""
        select d.*
        from documents d
        where d.referral_id in (select referral_id from referrals where batch_id = {bid})
        order by d.referral_id, d.doc_type, d.received_date
        """,
    )
    batch["patients"] = query(
        base_url,
        f"""
        select p.*
        from patients p
        where p.patient_id in (select patient_id from referrals where batch_id = {bid})
        order by p.patient_id
        """,
    )
    batch["chart_artifacts"] = query(
        base_url,
        f"""
        select ca.*
        from chart_artifacts ca
        where ca.patient_id in (select patient_id from referrals where batch_id = {bid})
        order by ca.patient_id, ca.artifact_type
        """,
    )


def add_transfer_batch(out: dict, base_url: str, batch_id: str) -> None:
    bid = sql_literal(batch_id)
    batches = out.setdefault("transfer_batches", {})
    batch: dict = {}
    batches[batch_id] = batch
    batch["transfers"] = query(
        base_url,
        f"""
        select *
        from transfer_requests
        where batch_id = {bid}
        order by transfer_id
        """,
    )
    batch["documents"] = query(
        base_url,
        f"""
        select d.*
        from documents d
        where d.transfer_id in (select transfer_id from transfer_requests where batch_id = {bid})
        order by d.transfer_id, d.doc_type, d.received_date
        """,
    )
    batch["capacity"] = query(
        base_url,
        f"""
        select fc.*
        from facility_capacity fc
        where fc.modality in (select distinct modality from transfer_requests where batch_id = {bid})
          and fc.date between
              (select min(requested_start_date) from transfer_requests where batch_id = {bid})
              and
              (select max(requested_start_date) from transfer_requests where batch_id = {bid})
        order by fc.date, fc.location_id
        """,
    )


def add_program(out: dict, base_url: str, program_code: str) -> None:
    code = sql_literal(program_code)
    programs = out.setdefault("programs", {})
    program: dict = {}
    programs[program_code] = program
    program["candidates"] = query(
        base_url,
        f"""
        select pc.*, p.phone, p.email, p.existing_chart, p.preferred_contact,
               ch.chronic_conditions, ch.surgeries, ch.medication_count,
               ch.allergy_count, ch.recent_hospitalization, ch.risk_flags
        from program_candidates pc
        left join patients p on p.patient_id = pc.patient_id
        left join clinical_history ch on ch.patient_id = pc.patient_id
        where pc.program_code = {code}
        order by pc.patient_id
        """,
    )
    program["chart_artifacts"] = query(
        base_url,
        f"""
        select ca.*
        from chart_artifacts ca
        where ca.patient_id in (select patient_id from program_candidates where program_code = {code})
        order by ca.patient_id, ca.artifact_type
        """,
    )


def add_patients(out: dict, base_url: str, patient_ids: List[str]) -> None:
    if not patient_ids:
        return
    ids = ", ".join(sql_literal(patient_id) for patient_id in patient_ids)
    out["patients"] = query(
        base_url,
        f"""
        select p.*, ch.chronic_conditions, ch.risk_flags
        from patients p
        left join clinical_history ch on ch.patient_id = p.patient_id
        where p.patient_id in ({ids})
        order by p.patient_id
        """,
    )
    out["patient_chart_artifacts"] = query(
        base_url,
        f"""
        select *
        from chart_artifacts
        where patient_id in ({ids})
        order by patient_id, artifact_type
        """,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Portal base URL")
    parser.add_argument("--schema", action="store_true", help="Include table schema")
    parser.add_argument("--roster", action="append", default=[], help="Roster ID to fetch")
    parser.add_argument("--referral-batch", action="append", default=[], help="Referral batch ID to fetch")
    parser.add_argument("--transfer-batch", action="append", default=[], help="Transfer batch ID to fetch")
    parser.add_argument("--program", action="append", default=[], help="Program code to fetch")
    parser.add_argument("--patient", action="append", default=[], help="Patient ID to fetch")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        base_url = normalize_base_url(args.base_url)
        out: dict = {"base_url": base_url}
        if args.schema:
            add_schema(out, base_url)
        for roster_id in args.roster:
            add_roster(out, base_url, roster_id)
        for batch_id in args.referral_batch:
            add_referral_batch(out, base_url, batch_id)
        for batch_id in args.transfer_batch:
            add_transfer_batch(out, base_url, batch_id)
        for program_code in args.program:
            add_program(out, base_url, program_code)
        add_patients(out, base_url, args.patient)
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0
    except (urllib.error.URLError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
