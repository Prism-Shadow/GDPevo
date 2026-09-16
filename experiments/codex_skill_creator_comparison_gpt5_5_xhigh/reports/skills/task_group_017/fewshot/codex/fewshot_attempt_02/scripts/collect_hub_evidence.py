#!/usr/bin/env python3
"""Collect matter-scoped Investigation Review Hub evidence for JSON answers."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


TABLE_ENDPOINTS = {
    "matters": "/api/matters",
    "subpoena_categories": "/api/subpoena-categories",
    "production_stats": "/api/productions",
    "custodian_sources": "/api/custodian-sources",
    "review_documents": "/api/documents/search",
    "privilege_entries": "/api/privilege-log",
    "qc_findings": "/api/qc-findings",
    "retention_events": "/api/retention-events",
    "remediation_actions": "/api/remediation-actions",
}

ORDER_COLUMNS = {
    "matters": "matter_id",
    "subpoena_categories": "category_code",
    "production_stats": "category_code, batch_id",
    "custodian_sources": "source_id",
    "review_documents": "doc_id",
    "privilege_entries": "entry_id",
    "qc_findings": "finding_id",
    "retention_events": "event_id",
    "remediation_actions": "action_id",
}

ID_FIELDS = (
    "matter_id",
    "category_code",
    "batch_id",
    "source_id",
    "doc_id",
    "entry_id",
    "finding_id",
    "event_id",
    "action_id",
    "source_ref",
    "target_ref",
)

SIGNAL_WORDS = {
    "active_system_loss",
    "archive_available",
    "auto_purged",
    "board_materials",
    "business_only",
    "collection_gap",
    "deleted_channel",
    "disclosure",
    "destroyed",
    "erased",
    "incomplete_log",
    "missing_required_record",
    "miscoded_nonresponsive",
    "miscoded_privileged",
    "not_collected",
    "over_designated",
    "personal_device",
    "personal_email",
    "personal_source",
    "post_hold_loss",
    "post_hold_partial_recovery",
    "post_subpoena",
    "privilege_miscoding",
    "remediation_source",
    "responsive_miscoding",
    "should_exist_missing",
    "source_lost",
    "source_missing",
    "third_party",
    "waiver",
    "zero_claim",
}

NOISE_WORDS = {
    "alias",
    "duplicate",
    "family_member",
    "family_mismatch",
    "load_file_cleanup",
    "metadata_gap",
    "near_duplicate",
    "routine",
    "sampling_review",
}

SOURCE_SIGNAL_WORDS = {
    "archive_available",
    "board_materials",
    "collection_gap",
    "deleted_channel",
    "personal_device",
    "personal_email",
    "personal_source",
    "post_subpoena",
    "remediation_source",
}

ROUTINE_SOURCE_WORDS = {
    "metadata_gap",
    "routine",
    "scope_exception",
}


def read_text(path: Path) -> str:
    try:
        return path.read_text()
    except FileNotFoundError:
        return ""


def read_json(path: Path):
    with path.open() as handle:
        return json.load(handle)


def iter_values(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from iter_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from iter_values(item)
    else:
        yield value


def find_matter_id(prompt: str, payloads: dict[str, object]) -> str:
    for payload in payloads.values():
        if isinstance(payload, dict):
            direct = payload.get("matter_id")
            if isinstance(direct, str) and direct.startswith("MTR-"):
                return direct
    for value in iter_values(payloads):
        if isinstance(value, str):
            match = re.search(r"\bMTR-[A-Z0-9-]+\b", value)
            if match:
                return match.group(0)
    match = re.search(r"\bMTR-[A-Z0-9-]+\b", prompt)
    if match:
        return match.group(0)
    raise SystemExit("Could not infer matter_id from prompt or payloads.")


def find_base_url(input_dir: Path, explicit: str | None) -> str:
    candidates = [
        explicit,
        os.environ.get("TASK_ENV_BASE_URL"),
        os.environ.get("REVIEW_HUB_BASE_URL"),
    ]
    for parent in [input_dir, *input_dir.parents]:
        env_access = parent / "environment_access.md"
        if env_access.exists():
            text = read_text(env_access)
            match = re.search(r"base_url:\s*(\S+)", text)
            if match:
                candidates.append(match.group(1))
                break
    for value in candidates:
        if value and value != "<TASK_ENV_BASE_URL>":
            return value.rstrip("/") + "/"
    raise SystemExit("Pass --base-url or set TASK_ENV_BASE_URL.")


def find_api_key(prompt: str, payloads: dict[str, object], explicit: str | None) -> str | None:
    if explicit:
        return explicit
    for value in [os.environ.get("REVIEW_HUB_API_KEY"), prompt, json.dumps(payloads)]:
        if not value:
            continue
        match = re.search(r"review-key-[A-Za-z0-9-]+", value)
        if match:
            return match.group(0)
    return "review-key-017"


def request_json(method: str, url: str, body: object | None = None, api_key: str | None = None):
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if api_key:
        headers["X-API-Key"] = api_key
    request = Request(url, data=data, headers=headers, method=method)
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode())


def get_json(base_url: str, path: str, params: dict[str, str] | None = None):
    url = base_url.rstrip("/") + path
    if params:
        url += "?" + urlencode(params)
    return request_json("GET", url)


def query_table(base_url: str, api_key: str | None, table: str, matter_id: str):
    order_by = ORDER_COLUMNS.get(table, "1")
    sql = f"select * from {table} where matter_id = ? order by {order_by}"
    payload = {"sql": sql, "params": [matter_id]}
    return request_json("POST", base_url.rstrip("/") + "/api/query", payload, api_key)


def endpoint_table(base_url: str, table: str, matter_id: str):
    path = TABLE_ENDPOINTS[table]
    data = get_json(base_url, path, {"matter_id": matter_id})
    rows = data.get("rows", []) if isinstance(data, dict) else []
    return [row for row in rows if row.get("matter_id") == matter_id]


def normalize_tokens(value) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, list):
        raw = " ".join(str(item) for item in value)
    elif isinstance(value, dict):
        raw = json.dumps(value)
    else:
        text = str(value)
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                raw = " ".join(str(item) for item in parsed)
            else:
                raw = text
        except json.JSONDecodeError:
            raw = text
    return {token for token in re.split(r"[^a-z0-9_]+", raw.lower()) if token}


def row_tokens(row: dict) -> set[str]:
    tokens: set[str] = set()
    for value in row.values():
        tokens |= normalize_tokens(value)
    return tokens


def field_tokens(row: dict, field: str) -> set[str]:
    return normalize_tokens(row.get(field))


def is_material_candidate(table: str, row: dict) -> bool:
    tokens = row_tokens(row)
    issue_tags = field_tokens(row, "issue_tags")
    notes = field_tokens(row, "notes")
    source_type = str(row.get("source_type", "")).lower()
    source_label = str(row.get("source_label", "")).lower()
    status = str(row.get("status", "")).lower()
    issue_type = str(row.get("issue_type", "")).lower()
    action_id = str(row.get("action_id", "")).lower()

    if table == "retention_events":
        if status in {"post_hold_loss", "post_hold_partial_recovery", "auto_purged"}:
            return True
        if status == "policy_destroyed_pre_hold":
            return "remediated" not in notes
        if status in {"should_exist_missing", "system_loss"}:
            if {"remediated", "unresolved"} <= notes:
                return False
            if {"no", "unresolved", "impact"} <= notes:
                return False
            return bool({"missing", "lost", "active", "requires", "auto"} & notes)
        return False
    if table == "custodian_sources":
        if status in {"lost", "destroyed"}:
            return True
        source_text = f"{source_type} {source_label}"
        personal_source = any(
            word in source_text
            for word in ("personal", "phone", "sms", "signal", "gmail", "laptop", "mobile")
        )
        if status in {"not_collected", "partial_collection"}:
            if issue_tags & SOURCE_SIGNAL_WORDS:
                return True
            if personal_source and not (issue_tags & ROUTINE_SOURCE_WORDS):
                return True
            return False
        return bool({"archive_available", "remediation_source"} & issue_tags)
    if table == "review_documents":
        if tokens & SIGNAL_WORDS:
            return True
        return False
    if table == "privilege_entries":
        return issue_type not in {"", "clean", "family_mismatch"} or row.get("third_party") in {1, True}
    if table == "qc_findings":
        if issue_type in {"metadata_gap", "near_duplicate", "duplicate_overlay", "family_break"}:
            return bool(tokens & SIGNAL_WORDS)
        return issue_type not in {"", "clean"}
    if table == "remediation_actions":
        return "noise" not in action_id and issue_type not in NOISE_WORDS
    if table == "production_stats":
        return status in {"supplement_pending", "rolling_review", "not_produced"} or bool(row.get("zero_claim_reason"))
    return False


def row_ids(row: dict) -> set[str]:
    ids: set[str] = set()
    for field in ID_FIELDS:
        value = row.get(field)
        if isinstance(value, str) and value:
            ids.add(value)
    return ids


def build_links(tables: dict[str, list[dict]]) -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = {}
    for table, rows in tables.items():
        for row in rows:
            for stable_id in row_ids(row):
                index.setdefault(stable_id, []).append({"table": table, "row": row})

    links: dict[str, list[dict]] = {}
    for table, rows in tables.items():
        for row in rows:
            anchors = row_ids(row)
            primary = next(iter(sorted(anchors)), None)
            if not primary:
                continue
            refs = []
            for field in ("source_ref", "target_ref"):
                ref = row.get(field)
                if isinstance(ref, str) and ref in index:
                    for target in index[ref]:
                        refs.append({"via": field, "ref": ref, "table": target["table"]})
            if refs:
                links[primary] = refs
    return links


def load_inputs(input_dir: Path):
    prompt = read_text(input_dir / "prompt.txt")
    payload_dir = input_dir / "payloads"
    payloads: dict[str, object] = {}
    if payload_dir.exists():
        for path in sorted(payload_dir.glob("*.json")):
            payloads[path.name] = read_json(path)
    return prompt, payloads


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", default="input", help="Task input directory containing prompt.txt and payloads/")
    parser.add_argument("--base-url", help="Investigation Review Hub base URL")
    parser.add_argument("--api-key", help="API key for POST /api/query")
    parser.add_argument("--output", help="Write JSON evidence to this path instead of stdout")
    args = parser.parse_args()

    input_dir = Path(args.input_dir).resolve()
    prompt, payloads = load_inputs(input_dir)
    matter_id = find_matter_id(prompt, payloads)
    base_url = find_base_url(input_dir, args.base_url)
    api_key = find_api_key(prompt, payloads, args.api_key)

    warnings: list[str] = []
    schema = get_json(base_url, "/api/schema")
    available_tables = {
        table["table"]
        for table in schema.get("tables", [])
        if isinstance(table, dict) and table.get("table") in TABLE_ENDPOINTS
    }

    tables: dict[str, list[dict]] = {}
    for table in sorted(available_tables):
        try:
            result = query_table(base_url, api_key, table, matter_id)
            rows = result.get("rows", []) if isinstance(result, dict) else []
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            warnings.append(f"SQL query failed for {table}; used GET fallback: {exc}")
            rows = endpoint_table(base_url, table, matter_id)
        tables[table] = rows

    candidates = {
        table: [row for row in rows if is_material_candidate(table, row)]
        for table, rows in tables.items()
    }

    output = {
        "matter_id": matter_id,
        "input_dir": str(input_dir),
        "payload_files": sorted(payloads),
        "schema_tables": sorted(available_tables),
        "table_counts": {table: len(rows) for table, rows in tables.items()},
        "collection_warnings": warnings,
        "prompt": prompt,
        "payloads": payloads,
        "tables": tables,
        "material_candidates": candidates,
        "record_links": build_links(tables),
    }

    text = json.dumps(output, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
