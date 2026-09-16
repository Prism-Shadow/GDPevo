#!/usr/bin/env python3
"""Fetch read-only synthetic clinic context for protocol JSON tasks."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


def parse_environment_access(path: Path) -> tuple[str, list[str]]:
    base_url = ""
    get_paths: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("base_url:"):
            base_url = line.split(":", 1)[1].strip()
        match = re.match(r"-\s+GET\s+(\S+)", line)
        if match:
            get_paths.append(match.group(1))
    if not base_url:
        raise SystemExit(f"Missing base_url in {path}")
    return base_url, get_paths


def fetch_json(base_url: str, path: str, timeout: float) -> tuple[Any | None, str | None]:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return None, f"{path}: HTTP {exc.code}"
    except urllib.error.URLError as exc:
        return None, f"{path}: {exc.reason}"
    except TimeoutError:
        return None, f"{path}: timeout"
    try:
        return json.loads(body), None
    except json.JSONDecodeError:
        return {"_text": body}, None


def iter_values(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from iter_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_values(child)


def first_identifier(data: Any, names: set[str]) -> str | None:
    for item in iter_values(data):
        for key, value in item.items():
            if key in names and isinstance(value, str) and value:
                return value.split("/")[-1]
    return None


def find_record(data: Any, names: set[str], identifier: str) -> Any | None:
    for item in iter_values(data):
        for key, value in item.items():
            if key in names and isinstance(value, str) and value.split("/")[-1] == identifier:
                return item
    return None


def collect_identifiers(data: Any, names: set[str]) -> set[str]:
    found: set[str] = set()
    for item in iter_values(data):
        for key, value in item.items():
            if key in names:
                if isinstance(value, str) and value:
                    found.add(value.split("/")[-1])
                elif isinstance(value, list):
                    for entry in value:
                        if isinstance(entry, str) and entry:
                            found.add(entry.split("/")[-1])
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", required=True, type=Path, help="Path to environment_access.md")
    parser.add_argument("--case", required=True, help="Target case identifier")
    parser.add_argument("--out", type=Path, help="Write fetched context JSON to this path")
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout in seconds")
    args = parser.parse_args()

    base_url, allowed_gets = parse_environment_access(args.env)
    fetched: dict[str, Any] = {}
    errors: list[str] = []

    def remember(path: str, data: Any | None, error: str | None) -> None:
        if error:
            errors.append(error)
        else:
            fetched[path] = data

    plain_paths = [path for path in allowed_gets if "{" not in path and "}" not in path]
    for path in plain_paths:
        data, error = fetch_json(base_url, path, args.timeout)
        remember(path, data, error)

    case_path = "/api/cases/{case_id}"
    if case_path in allowed_gets:
        data, error = fetch_json(base_url, f"/api/cases/{urllib.parse.quote(args.case)}", args.timeout)
        remember(f"/api/cases/{args.case}", data, error)

    case_data = fetched.get(f"/api/cases/{args.case}")
    if case_data is None:
        case_data = find_record(
            fetched.get("/api/cases"),
            {"id", "case_id", "caseId", "case"},
            args.case,
        )
    patient_id = first_identifier(
        case_data,
        {"patient_id", "patientId", "patient", "subject", "subject_id", "member_id"},
    )

    if patient_id and "/api/patients/{patient_id}" in allowed_gets:
        data, error = fetch_json(base_url, f"/api/patients/{urllib.parse.quote(patient_id)}", args.timeout)
        remember(f"/api/patients/{patient_id}", data, error)

    protocol_ids = collect_identifiers(
        fetched,
        {"protocol_id", "protocolId", "protocol", "protocols", "guideline_id", "guidelineId"},
    )
    if "/api/protocols/{protocol_id}" in allowed_gets:
        for protocol_id in sorted(protocol_ids):
            data, error = fetch_json(
                base_url,
                f"/api/protocols/{urllib.parse.quote(protocol_id)}",
                args.timeout,
            )
            remember(f"/api/protocols/{protocol_id}", data, error)

    output = {
        "base_url": base_url,
        "case_id": args.case,
        "patient_id": patient_id,
        "allowed_get_endpoints": allowed_gets,
        "fetched": fetched,
        "fetch_errors": errors,
    }

    text = json.dumps(output, indent=2, sort_keys=True)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0 if fetched else 2


if __name__ == "__main__":
    sys.exit(main())
