"""Minimal YAML helper for the staged skill validator.

This shim supports the tiny frontmatter dictionaries used in SKILL.md.
It is not a general YAML parser.
"""

from __future__ import annotations

import ast


class YAMLError(Exception):
    pass


def _parse_scalar(value):
    value = value.strip()
    if not value:
        return ""
    if value.startswith('"') and value.endswith('"'):
        return ast.literal_eval(value)
    if value.startswith("'") and value.endswith("'"):
        return ast.literal_eval(value)
    if value.lower() == "null" or value == "~":
        return None
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def safe_load(text):
    if text is None:
        return None
    if not isinstance(text, str):
        raise YAMLError("safe_load expects a string")
    result = {}
    current_key = None
    current_value_lines = []

    def flush():
        nonlocal current_key, current_value_lines
        if current_key is None:
            return
        raw_value = "\n".join(current_value_lines)
        result[current_key] = _parse_scalar(raw_value)
        current_key = None
        current_value_lines = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith(" ") or line.startswith("\t"):
            if current_key is None:
                raise YAMLError("Unexpected indentation")
            current_value_lines.append(line.lstrip())
            continue
        flush()
        if ":" not in line:
            raise YAMLError(f"Invalid line: {line}")
        key, value = line.split(":", 1)
        key = key.strip()
        if not key:
            raise YAMLError("Empty key")
        current_key = key
        current_value_lines = [value.lstrip()]
    flush()
    return result
