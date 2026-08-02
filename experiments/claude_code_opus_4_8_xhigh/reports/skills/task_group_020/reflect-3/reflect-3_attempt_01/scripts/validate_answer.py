#!/usr/bin/env python3
"""Check a candidate answer against its answer_template.json before emitting it.

    validate_answer.py <candidate.json> <answer_template.json>

Catches the mechanical failures that silently cost credit: non-integer dollars,
enum values that are not verbatim template members, percent values carrying more
decimals than allowed, missing top-level keys, and pinned-ID lists that are not
covered exactly. Exits non-zero if anything is reported.
"""
import json
import re
import sys

DOLLAR = re.compile(r"(_dollars|_usd|_amount|amount_.*|.*_value)$")
PERCENT = re.compile(r"(_pct|_percent|percent_.*)$")
MONTHS = re.compile(r"_months$")


def walk(node, path=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk(v, f"{path}.{k}" if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, f"{path}[{i}]")
    else:
        yield path, node


def leaf(path):
    return path.rsplit(".", 1)[-1].split("[")[0]


def norm(path):
    """Drop list indices so template and candidate paths compare equal."""
    return re.sub(r"\[\d+\]", "", path)


def collect_enums(template):
    """Inline enums are keyed by path; allowed_enums are keyed by field name.

    Keying inline enums by path matters: `unit` and `status` appear in several places
    in one template with *different* allowed sets, so a leaf-name index would collide
    and raise false positives.
    """
    by_path, by_name = {}, {}
    for path, val in walk(template):
        if "allowed_enums" in path.split(".") or not isinstance(val, str):
            continue
        opts = None
        if " | " in val:
            opts = [s.strip() for s in val.split("|")]
        elif val.startswith("one of:"):
            opts = [s.strip() for s in val[len("one of:"):].split(",")]
        if opts:
            # Strip a leading shape hint such as "enum risk_rating".
            by_path[norm(path)] = [o for o in opts if o]
    for key, vals in (template.get("allowed_enums") or {}).items():
        if isinstance(vals, list):
            by_name[key] = vals
    # `required_output_shape` describes rows as "enum <name>" - map those paths too.
    for path, val in walk(template.get("required_output_shape") or {}):
        if isinstance(val, str) and val.startswith("enum "):
            name = val[5:].strip()
            if name in by_name:
                by_path[norm(path)] = by_name[name]
    return by_path, by_name


def pinned_ids(template):
    out = {}
    for holder in (template, template.get("instructions") or {}):
        if not isinstance(holder, dict):
            continue
        for key, val in holder.items():
            if isinstance(val, list) and val and all(isinstance(x, str) for x in val):
                if key.startswith("possible_") or key.startswith("stable_"):
                    out[key] = val
    return out


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    cand = json.load(open(sys.argv[1]))
    tmpl = json.load(open(sys.argv[2]))
    problems = []

    required = tmpl.get("required_top_level_fields")
    required = list(required) if isinstance(required, dict) else None
    if required is None:
        skip = {"schema_name", "schema_version", "version", "language", "units",
                "allowed_enums", "instructions", "required_output_shape",
                "issue_object_fields", "summary_metrics_fields", "possible_issue_ids"}
        required = [k for k in tmpl if k not in skip and not k.startswith("possible_")]
    for key in required:
        if key not in cand:
            problems.append(f"missing top-level key: {key}")

    by_path, by_name = collect_enums(tmpl)

    for path, val in walk(cand):
        name, npath = leaf(path), norm(path)
        if isinstance(val, bool) or val is None:
            continue
        if isinstance(val, (int, float)) and DOLLAR.search(name) and not PERCENT.search(name):
            if isinstance(val, float) and not val.is_integer():
                problems.append(f"{path}: dollar value not an integer ({val})")
        if isinstance(val, (int, float)) and MONTHS.search(name):
            if isinstance(val, float) and not val.is_integer():
                problems.append(f"{path}: month value not an integer ({val})")
        if isinstance(val, str):
            # Path-specific enum wins; fall back to the by-name allowed_enums table.
            opts = by_path.get(npath) or by_name.get(name)
            if opts and val not in opts:
                problems.append(f"{path}: {val!r} not in allowed {opts}")
            if re.fullmatch(r"[A-Za-z_ ]+ \| .*", val) or val.startswith("one of:"):
                problems.append(f"{path}: template placeholder left in place ({val!r})")

    for key, ids in pinned_ids(tmpl).items():
        used = {v for _, v in walk(cand) if isinstance(v, str) and v in ids}
        missing = [i for i in ids if i not in used]
        if missing and key.startswith("stable_"):
            problems.append(f"{key}: pinned IDs never used: {', '.join(missing)}")

    units = tmpl.get("units") or {}
    m = re.search(r"(\w+) decimal", str(units.get("percent_points", "")))
    places = {"one": 1, "two": 2, "three": 3, "four": 4}.get(m.group(1)) if m else None
    if places:
        for path, val in walk(cand):
            if isinstance(val, float) and PERCENT.search(leaf(path)):
                if round(val, places) != val:
                    problems.append(f"{path}: percent needs {places} dp ({val})")

    if problems:
        print(f"{len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print("OK - no mechanical problems found")


if __name__ == "__main__":
    main()
