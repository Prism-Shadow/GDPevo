#!/usr/bin/env python3
"""Check a workbench answer against its answer_template.json before emitting it.

Usage:
    python3 validate_answer.py answer.json path/to/answer_template.json [--bundle DEAL_bundle.json]

Reports ERROR (fix before emitting) and WARN (verify by hand). Exits non-zero on
any ERROR. The checks are structural, not semantic - a clean run does not mean
the legal analysis is right, only that the envelope conforms.

Checks:
  1. answer is one valid JSON object
  2. leftover template placeholders ("A | B", "one of: ...", "stable ... id", "string",
     "YYYY-MM-DD", example IDs ending _00)
  3. template meta-keys leaked into the answer
  4. enum values are drawn from the template's allowed lists
  5. currency/count/month fields are integers; percents look like points
  6. *_count fields reconcile with same-named arrays; totals reconcile with components
  7. IDs referenced exist in the deal bundle and belong to the target deal (with --bundle)
"""

import argparse
import json
import re
import sys

META_KEYS = {
    "schema_name", "schema_version", "version", "instructions", "allowed_enums",
    "required_output_shape", "required_top_level_fields", "issue_object_fields",
    "summary_metrics_fields", "possible_issue_ids", "stable_issue_ids",
    "stable_redline_ids", "units", "language", "ordering",
}

PLACEHOLDER_PATTERNS = [
    (re.compile(r"^\s*[A-Za-z_][\w .-]*(\s*\|\s*[\w .-]+)+\s*$"), "unreplaced pipe-enum placeholder"),
    (re.compile(r"one of\s*:", re.I), "unreplaced 'one of:' placeholder"),
    (re.compile(r"^\s*stable\b", re.I), "unreplaced descriptive placeholder"),
    (re.compile(r"^\s*(the|a)\b.*\b(id|ids|name|group|class)\s*$", re.I), "unreplaced descriptive placeholder"),
    (re.compile(r"^(string|integer|number|boolean|object|array)( or null)?$", re.I), "unreplaced type name"),
    (re.compile(r"^\s*(YYYY-MM-DD|USD integer dollars|English only)\s*$"), "unreplaced format literal"),
    (re.compile(r"_00$"), "example ID from the template"),
    (re.compile(r"^\s*(TBD|N/?A|unknown|placeholder|category_id|stable_\w+)\s*$", re.I), "placeholder value"),
]

CURRENCY_HINT = re.compile(r"(_dollars|_usd|_amount|amount_|_value|liability|revenue|exposure|_cash|price)", re.I)
COUNT_HINT = re.compile(r"(_count|count_|^count$|sample_size|_rank|_size)", re.I)
MONTH_HINT = re.compile(r"_months$|^months$", re.I)
PCT_HINT = re.compile(r"(_pct$|_percent$|percent_|_percent_points$)", re.I)
ID_HINT = re.compile(r"(^|_)(id|ids)$", re.I)

errors, warnings = [], []


def err(path, msg):
    errors.append(f"ERROR {path}: {msg}")


def warn(path, msg):
    warnings.append(f"WARN  {path}: {msg}")


def walk(node, path="$"):
    """Yield (path, key, value) for every scalar leaf."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, f"{path}[{i}]")
    else:
        yield path, path.split(".")[-1].split("[")[0], node


def norm_path(path):
    """$.a.b[3].c -> $.a.b[].c so template and answer paths line up."""
    return re.sub(r"\[\d+\]", "[]", path)


def collect_enums(template):
    """Allowed-value lists from the template.

    Returns (by_path, by_field, named_lists, all_values). Path-scoped lookups are
    exact; the field-name index is the fallback for descriptor templates where the
    answer's real paths don't exist in the template.
    """
    by_path, by_field, named, global_vals = {}, {}, {}, set()

    def clean(values):
        return {v.strip() for v in values if isinstance(v, str) and v.strip()}

    def add(path, field, values):
        vals = clean(values)
        if not vals:
            return
        if path:
            by_path.setdefault(norm_path(path), set()).update(vals)
        if field:
            by_field.setdefault(field, set()).update(vals)
        global_vals.update(vals)

    def rec(node, path="$", key=None):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "allowed_enums" and isinstance(v, dict):
                    for ek, ev in v.items():
                        if isinstance(ev, list):
                            named[ek] = clean(ev)
                            add(None, ek, ev)
                    continue
                if k in ("possible_issue_ids", "stable_issue_ids") and isinstance(v, list):
                    named[k] = clean(v)
                    add(None, "issue_id", v)
                    continue
                if k == "stable_redline_ids" and isinstance(v, list):
                    named[k] = clean(v)
                    add(None, "redline_id", v)
                    continue
                rec(v, f"{path}.{k}", k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                rec(v, f"{path}[{i}]", key)
        elif isinstance(node, str) and key:
            if "|" in node and not node.startswith("http"):
                add(path, key, node.split("|"))
            m = re.match(r"\s*one of\s*:\s*(.+)$", node, re.I)
            if m:
                add(path, key, re.split(r"[,;]", m.group(1)))
            m2 = re.match(r"\s*enum\s+(\w+)\s*$", node)
            if m2 and m2.group(1) in named:
                add(path, key, named[m2.group(1)])

    rec(template)
    # Second pass: "enum <name>" references may appear before the named list is seen.
    def rec2(node, path="$", key=None):
        if isinstance(node, dict):
            for k, v in node.items():
                rec2(v, f"{path}.{k}", k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                rec2(v, f"{path}[{i}]", key)
        elif isinstance(node, str) and key:
            m = re.match(r"\s*enum\s+(\w+)\s*$", node)
            if m and m.group(1) in named:
                add(path, key, named[m.group(1)])

    rec2(template)
    return by_path, by_field, named, global_vals


def collect_nullable(template):
    """Field names the template marks as nullable (value null, or '... or null')."""
    nullable = set()

    def rec(node, key=None):
        if isinstance(node, dict):
            for k, v in node.items():
                if v is None:
                    nullable.add(k)
                elif isinstance(v, str) and re.search(r"\bor null\b|\bnullable\b", v, re.I):
                    nullable.add(k)
                else:
                    rec(v, k)
        elif isinstance(node, list):
            for v in node:
                if v is None and key:
                    nullable.add(key)
                else:
                    rec(v, key)

    rec(template)
    return nullable


def collect_ids(bundle):
    ids = set()
    if not bundle:
        return ids
    if bundle.get("deal_id"):
        ids.add(bundle["deal_id"])
    for value in bundle.values():
        if isinstance(value, list):
            for row in value:
                if isinstance(row, dict):
                    for k, v in row.items():
                        if k != "deal_id" and k.endswith("_id") and isinstance(v, str):
                            ids.add(v)
        elif isinstance(value, dict):
            for k, v in value.items():
                if k != "deal_id" and k.endswith("_id") and isinstance(v, str):
                    ids.add(v)
    return ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("answer")
    ap.add_argument("template")
    ap.add_argument("--bundle", help="deal bundle from fetch_deal.py, to check ID provenance")
    ap.add_argument("--show-nulls", action="store_true",
                    help="report every null, including ones the template allows")
    args = ap.parse_args()
    null_ok = 0

    raw = open(args.answer, encoding="utf-8").read()
    if raw.lstrip().startswith("```"):
        err("$", "answer starts with a markdown fence - emit bare JSON")
    try:
        answer = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"ERROR $: answer is not valid JSON: {exc}")
        sys.exit(1)
    if not isinstance(answer, dict):
        err("$", "answer must be a single JSON object")

    template = json.load(open(args.template, encoding="utf-8"))
    nullable_fields = collect_nullable(template)
    bundle = json.load(open(args.bundle, encoding="utf-8")) if args.bundle else None
    known_ids = collect_ids(bundle)
    target_deal = (bundle or {}).get("deal_id")

    # --- meta-key leakage
    for k in answer:
        if k in META_KEYS:
            err(f"$.{k}", "template meta-key must not appear in the answer")

    enums_by_path, enums_by_field, _named, all_enum_values = collect_enums(template)

    # --- leaf checks
    for path, key, value in walk(answer):
        if isinstance(value, str):
            placeholder = False
            for pattern, label in PLACEHOLDER_PATTERNS:
                if pattern.search(value.strip()):
                    err(path, f"{label}: {value!r}")
                    placeholder = True
                    break
            if placeholder:
                continue
            allowed = enums_by_path.get(norm_path(path)) or enums_by_field.get(key)
            if allowed and value not in allowed:
                near = {a.lower(): a for a in allowed}
                if value.lower() in near:
                    err(path, f"enum casing: {value!r} should be {near[value.lower()]!r}")
                else:
                    err(path, f"{value!r} not in allowed values for {key}: {sorted(allowed)}")
            if key in ("risk_rating", "overall_risk_rating") and value in ("High", "Medium", "Low", "low", "medium"):
                err(path, f"source casing {value!r} - templates use uppercase risk ratings")
            if (ID_HINT.search(key) and known_ids and value not in known_ids
                    and key not in ("task_id", "schema_name", "policy_id", "playbook_id")):
                if all_enum_values and value in all_enum_values:
                    pass  # template-supplied ID vocabulary
                elif target_deal and value.startswith(("TERM_", "CNS_", "MAT_", "EMP_", "FND_",
                                                       "RSK_", "BM_", "NOTE_", "DOC_")):
                    err(path, f"ID {value!r} is not in the {target_deal} bundle")
                else:
                    warn(path, f"ID {value!r} not found in the deal bundle - confirm it is real")
        elif isinstance(value, bool):
            continue
        elif isinstance(value, (int, float)):
            if CURRENCY_HINT.search(key) and isinstance(value, float) and value != int(value):
                err(path, f"currency-like field must be an integer: {value}")
            if COUNT_HINT.search(key) and isinstance(value, float) and value != int(value):
                err(path, f"count-like field must be an integer: {value}")
            if MONTH_HINT.search(key) and isinstance(value, float) and value != int(value):
                err(path, f"month field must be an integer: {value}")
            if PCT_HINT.search(key) and isinstance(value, (int, float)) and 0 < abs(value) < 1:
                warn(path, f"percent field is {value} - if this came from a fraction "
                           "(cap-table style), convert to percent points")
            if PCT_HINT.search(key) and isinstance(value, float):
                if len(str(value).split(".")[-1]) > 4:
                    warn(path, f"percent {value} has more decimals than any template asks for")
        elif value is None:
            if key in nullable_fields and not args.show_nulls:
                null_ok += 1
            else:
                warn(path, "null, but the template does not mark this field nullable"
                           " - use a real value or the field's not-found enum")

    # --- aggregate reconciliation
    arrays = {}

    def index_arrays(node, path="$"):
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(v, list):
                    arrays[k] = (f"{path}.{k}", v)
                index_arrays(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                index_arrays(v, f"{path}[{i}]")

    index_arrays(answer)

    def scalars(node, out=None):
        out = {} if out is None else out
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    out.setdefault(k, []).append(v)
                else:
                    scalars(v, out)
        elif isinstance(node, list):
            for v in node:
                scalars(v, out)
        return out

    flat = scalars(answer)
    for field, values in flat.items():
        m = re.match(r"^(.*?)_?count$", field) or re.match(r"^count_(.*)$", field)
        if not m or len(values) != 1:
            continue
        stem = (m.group(1) or "").strip("_")
        for arr_name, (arr_path, arr) in arrays.items():
            base = arr_name.rstrip("s")
            if stem and (stem in arr_name or arr_name.rstrip("s") in stem or base in stem):
                if values[0] != len(arr):
                    warn(f"$.{field}", f"{field}={values[0]} but {arr_path} has {len(arr)} items"
                                       " - confirm the metric counts something else")
                break

    # --- risk tally reconciliation
    ratings = [v for p, k, v in walk(answer)
               if k in ("risk_rating", "overall_risk_rating") and isinstance(v, str)]
    tallies = {k: v for k, v in flat.items()
               if k in ("high_risk_count", "medium_risk_count", "low_risk_count") and len(v) == 1}
    for name, level in (("high_risk_count", "HIGH"), ("medium_risk_count", "MEDIUM"),
                        ("low_risk_count", "LOW")):
        if name in tallies:
            actual = sum(1 for r in ratings if r == level)
            if tallies[name][0] != actual:
                warn(f"$.{name}", f"{name}={tallies[name][0]} but {actual} {level} ratings appear"
                                  " - confirm which rows the metric covers")

    for line in errors:
        print(line)
    for line in warnings:
        print(line)
    if null_ok:
        print(f"note: {null_ok} null value(s) in template-nullable fields "
              "(re-run with --show-nulls to list them)")
    if not errors and not warnings:
        print("OK: no structural problems found (semantics still need your own review)")
    elif not errors:
        print(f"\n{len(warnings)} warning(s), no errors.")
    else:
        print(f"\n{len(errors)} error(s), {len(warnings)} warning(s).")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
