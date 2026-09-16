#!/usr/bin/env python3
"""Small Atlas Commerce Operations API and answer-template helper."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import urllib.error
import urllib.request
from typing import Any


def base_url(value: str | None = None) -> str:
    url = value or os.environ.get("TASK_ENV_BASE_URL") or "http://task-env:9022/"
    return url.rstrip("/")


def auth_headers() -> dict[str, str]:
    token = os.environ.get("TASK_ENV_API_TOKEN")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def request_json(method: str, path: str, body: Any = None, *, root: str | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url(root)}{path}",
        data=data,
        method=method,
        headers=auth_headers(),
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from {path}: {detail}") from exc


def load_json_or_text(path: str | None) -> Any:
    text = sys.stdin.read() if not path or path == "-" else open(path, "r", encoding="utf-8").read()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def read_sql(path: str | None) -> str:
    value = load_json_or_text(path)
    if isinstance(value, dict) and "sql" in value:
        return str(value["sql"])
    if isinstance(value, str):
        return value
    raise SystemExit("sql input must be a .sql file, stdin text, or JSON object with a sql key")


def validate(instance: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    errors: list[str] = []
    schema_type = schema.get("type")

    if schema_type == "object":
        if not isinstance(instance, dict):
            return [f"{path}: expected object"]
        required = schema.get("required", [])
        for key in required:
            if key not in instance:
                errors.append(f"{path}: missing required key {key!r}")
        additional = schema.get("additionalProperties", schema.get("additional_properties", True))
        if additional is False:
            allowed = set(schema.get("properties", {}).keys())
            for key in instance:
                if key not in allowed:
                    errors.append(f"{path}: unexpected key {key!r}")
        for key, subschema in schema.get("properties", {}).items():
            if key in instance:
                errors.extend(validate(instance[key], subschema, f"{path}.{key}"))

    elif schema_type == "array":
        if not isinstance(instance, list):
            return [f"{path}: expected array"]
        min_items = schema.get("minItems", schema.get("min_items"))
        max_items = schema.get("maxItems", schema.get("max_items"))
        if min_items is not None and len(instance) < int(min_items):
            errors.append(f"{path}: expected at least {min_items} items")
        if max_items is not None and len(instance) > int(max_items):
            errors.append(f"{path}: expected at most {max_items} items")
        if schema.get("uniqueItems", schema.get("unique_items", False)):
            seen = set()
            for item in instance:
                marker = json.dumps(item, sort_keys=True)
                if marker in seen:
                    errors.append(f"{path}: duplicate item {item!r}")
                seen.add(marker)
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(instance):
                errors.extend(validate(item, item_schema, f"{path}[{index}]"))

    elif schema_type == "integer":
        if not isinstance(instance, int) or isinstance(instance, bool):
            return [f"{path}: expected integer"]
        errors.extend(validate_number(instance, schema, path))

    elif schema_type == "number":
        if not isinstance(instance, (int, float)) or isinstance(instance, bool) or not math.isfinite(instance):
            return [f"{path}: expected finite number"]
        errors.extend(validate_number(float(instance), schema, path))

    elif schema_type == "string":
        if not isinstance(instance, str):
            return [f"{path}: expected string"]
        if "minLength" in schema and len(instance) < int(schema["minLength"]):
            errors.append(f"{path}: shorter than minLength {schema['minLength']}")
        if "enum" in schema and instance not in schema["enum"]:
            errors.append(f"{path}: expected one of {schema['enum']}, got {instance!r}")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(f"{path}: does not match pattern {schema['pattern']!r}")

    if schema_type != "string" and "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: expected one of {schema['enum']}, got {instance!r}")

    return errors


def validate_number(value: float, schema: dict[str, Any], path: str) -> list[str]:
    errors: list[str] = []
    if "minimum" in schema and value < float(schema["minimum"]):
        errors.append(f"{path}: below minimum {schema['minimum']}")
    if "maximum" in schema and value > float(schema["maximum"]):
        errors.append(f"{path}: above maximum {schema['maximum']}")
    if "multipleOf" in schema:
        step = float(schema["multipleOf"])
        quotient = value / step
        if not math.isclose(quotient, round(quotient), rel_tol=0, abs_tol=1e-7):
            errors.append(f"{path}: not a multiple of {schema['multipleOf']}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", help="Override TASK_ENV_BASE_URL")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("schema")
    sub.add_parser("dictionary")
    sub.add_parser("audit")

    sql_parser = sub.add_parser("sql")
    sql_parser.add_argument("sql_file", nargs="?", help="SQL file, JSON file with sql key, or '-' for stdin")

    tx_parser = sub.add_parser("transaction")
    tx_parser.add_argument("json_file", nargs="?", help="Transaction JSON body file or '-' for stdin")

    val_parser = sub.add_parser("validate")
    val_parser.add_argument("answer_json")
    val_parser.add_argument("template_json")

    args = parser.parse_args()

    if args.command == "schema":
        result = request_json("GET", "/api/schema", root=args.base_url)
    elif args.command == "dictionary":
        result = request_json("GET", "/api/data-dictionary", root=args.base_url)
    elif args.command == "audit":
        result = request_json("GET", "/api/correction-audit", root=args.base_url)
    elif args.command == "sql":
        result = request_json("POST", "/api/sql", {"sql": read_sql(args.sql_file)}, root=args.base_url)
    elif args.command == "transaction":
        body = load_json_or_text(args.json_file)
        if not isinstance(body, dict):
            raise SystemExit("transaction input must be a JSON object")
        result = request_json("POST", "/api/sql/transaction", body, root=args.base_url)
    elif args.command == "validate":
        with open(args.answer_json, "r", encoding="utf-8") as f:
            answer = json.load(f)
        with open(args.template_json, "r", encoding="utf-8") as f:
            template = json.load(f)
        errors = validate(answer, template)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            raise SystemExit(1)
        result = {"valid": True}
    else:
        raise AssertionError(args.command)

    json.dump(result, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
