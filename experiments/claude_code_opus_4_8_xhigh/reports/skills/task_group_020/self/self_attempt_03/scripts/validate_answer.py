#!/usr/bin/env python3
"""Mechanical conformance check of an answer against its answer_template.json.

    python3 validate_answer.py answer.json answer_template.json [--percent-dp N] [--strict]

Catches the failure modes that actually sink these deliverables:

  * enum union placeholders left verbatim ("LOW | MEDIUM | HIGH", "one of: a, b")
  * template spec strings copied through ("string", "stable consent ID", "integer or null")
  * source casing leaking into enum fields ("High" where the template demands "HIGH")
  * skeleton example IDs never replaced (TERM_PRJ_XXX_00, stable_carveout_id)
  * non-integer / stringified currency, over-precise percentages, non-integer months
  * meta-blocks (allowed_enums, required_output_shape, ...) echoed into the answer
  * missing or extra top-level keys, duplicate IDs, empty arrays of placeholders
  * *_count fields that disagree with the length of the array they describe

Exit status: 0 clean (warnings allowed), 1 errors found, 2 bad usage.
It is deliberately heuristic — treat warnings as questions, not verdicts.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys

# Template meta-blocks that describe the answer and must never appear inside it.
META_KEYS = {
    "schema_name", "schema_version", "version", "language", "units", "allowed_enums",
    "possible_issue_ids", "required_top_level_fields", "issue_object_fields",
    "summary_metrics_fields", "required_output_shape", "instructions", "ordering",
    "stable_issue_ids", "stable_redline_ids",
}

TYPE_WORDS = {
    "string", "number", "integer", "boolean", "object", "array", "null", "true", "false",
}

# Field-name heuristics.
CURRENCY_RE = re.compile(
    r"(dollars|_usd$|amount|price|liability|revenue|exposure|escrow_amount|value)", re.I)
PERCENT_RE = re.compile(r"(percent|_pct$|_pct_|pct$)", re.I)
MONTHS_RE = re.compile(r"months", re.I)
COUNT_RE = re.compile(r"(_count$|^count$)", re.I)
NON_NUMERIC_HINT = re.compile(r"(status|basis|type|method|unit|code|id$|_ids$|name)", re.I)
# Fields whose magnitude is defined by a sibling "unit"/"basis" field, so no single
# numeric convention applies (a draft_metric.value may be percent points OR months).
POLYMORPHIC = {"value", "threshold_value", "limit_value", "numeric_value"}
PLACEHOLDER_ID_RE = re.compile(
    r"(^stable[_ ]|_00$|^TERM_PRJ_[A-Z]+_00$|^category_id$|^blocker_id$|placeholder)", re.I)

errors: list[str] = []
warnings: list[str] = []


def err(path: str, msg: str) -> None:
    errors.append(f"ERROR {path}: {msg}")


def warn(path: str, msg: str) -> None:
    warnings.append(f"WARN  {path}: {msg}")


# ---------------------------------------------------------------- template parsing

def is_spec_string(s: str) -> bool:
    """True if a template string describes a value rather than being one."""
    t = s.strip()
    if not t:
        return False
    if "|" in t and len(t.split("|")) >= 2:
        return True
    low = t.lower()
    if low.startswith("one of:") or low.startswith("array of") or low.startswith("enum "):
        return True
    if low in TYPE_WORDS:
        return True
    if re.fullmatch(r"(integer|number|string|boolean|object|array)( or null)?", low):
        return True
    if low.startswith("stable ") or low.startswith("stable_"):
        return True
    if "use an empty array" in low or "short snake_case" in low:
        return True
    if low in ("yyyy-mm-dd", "0"):
        return True
    return False


def enum_members(spec: str) -> list[str]:
    """Extract candidate enum members from a spec string."""
    t = spec.strip()
    low = t.lower()
    if low.startswith("one of:"):
        body = t.split(":", 1)[1]
        return [m.strip().strip("`'\"") for m in body.split(",") if m.strip()]
    if "|" in t:
        parts = [m.strip().strip("`'\"") for m in t.split("|")]
        # Enum members are short; a long phrase means this is prose, not a menu.
        parts = [p for p in parts if p and p.count(" ") <= 5]
        if len(parts) >= 2:
            return parts
    return []


def collect_specs(node, path: str, specs: dict[str, str]) -> None:
    """Map template leaf paths -> spec string. Array indices normalized to []."""
    if isinstance(node, dict):
        for k, v in node.items():
            collect_specs(v, f"{path}.{k}" if path else k, specs)
    elif isinstance(node, list):
        for v in node:
            collect_specs(v, f"{path}[]", specs)
    elif isinstance(node, str):
        specs.setdefault(path, node)


def collect_declared_enums(template) -> dict[str, list[str]]:
    """Field-name -> allowed values, from allowed_enums blocks and inline unions."""
    out: dict[str, list[str]] = {}

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "allowed_enums" and isinstance(v, dict):
                    for field, vals in v.items():
                        if isinstance(vals, list) and all(isinstance(x, str) for x in vals):
                            out.setdefault(field, []).extend(vals)
                else:
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(template)

    # Inline unions: merge members across every path that uses the same field name, so a
    # field spelled with slightly different menus in two places does not false-positive.
    specs: dict[str, str] = {}
    collect_specs(template, "", specs)
    inline: dict[str, list[str]] = {}
    for path, spec in specs.items():
        field = path.split(".")[-1].replace("[]", "")
        for m in enum_members(spec):
            inline.setdefault(field, [])
            if m not in inline[field]:
                inline[field].append(m)
    for field, members in inline.items():
        out.setdefault(field, members)   # explicit allowed_enums win
    return out


def collect_id_whitelist(template) -> set[str]:
    ids: set[str] = set()
    for key in ("possible_issue_ids", "stable_issue_ids", "stable_redline_ids"):
        def find(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    if k == key and isinstance(v, list):
                        ids.update(x for x in v if isinstance(x, str))
                    else:
                        find(v)
            elif isinstance(node, list):
                for v in node:
                    find(v)
        find(template)
    return ids


# ---------------------------------------------------------------- answer checks

def check_values(node, path, spec_strings, declared_enums, percent_dp, strict):
    if isinstance(node, dict):
        for k, v in node.items():
            p = f"{path}.{k}" if path else k
            if k in META_KEYS and not isinstance(v, (int, float)):
                err(p, f"template meta-block '{k}' echoed into the answer; remove it")
            check_scalar(k, v, p, spec_strings, declared_enums, percent_dp)
            check_values(v, p, spec_strings, declared_enums, percent_dp, strict)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            p = f"{path}[{i}]"
            check_values(v, p, spec_strings, declared_enums, percent_dp, strict)
            if not isinstance(v, (dict, list)):
                check_scalar(path.split(".")[-1], v, p, spec_strings, declared_enums, percent_dp)


def check_scalar(key, val, path, spec_strings, declared_enums, percent_dp):
    if isinstance(val, str):
        if is_spec_string(val):
            err(path, f"unresolved template placeholder: {val!r}")
        elif val in spec_strings:
            err(path, f"template spec string copied verbatim: {val!r}")
        elif PLACEHOLDER_ID_RE.search(val):
            err(path, f"skeleton example identifier not replaced: {val!r}")
        allowed = declared_enums.get(key)
        if allowed and val not in allowed:
            lowered = {a.lower(): a for a in allowed}
            if val.lower() in lowered:
                err(path, f"enum case mismatch: {val!r} should be {lowered[val.lower()]!r}")
            else:
                warn(path, f"value {val!r} not in declared enum for '{key}': {allowed}")
        if CURRENCY_RE.search(key or "") and re.fullmatch(r"[-$,0-9.\s]+", val or ""):
            err(path, f"currency field carries a string, expected an integer: {val!r}")

    elif isinstance(val, bool):
        return

    elif isinstance(val, (int, float)):
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            err(path, "non-finite number")
            return
        k = key or ""
        if k.lower() in POLYMORPHIC:
            return
        if NON_NUMERIC_HINT.search(k) and not COUNT_RE.search(k):
            return
        if PERCENT_RE.search(k):
            dec = decimals(val)
            if dec > percent_dp and "fully_diluted" not in k:
                warn(path, f"percent has {dec} dp, template convention is {percent_dp}")
        elif MONTHS_RE.search(k) or COUNT_RE.search(k):
            if isinstance(val, float) and not val.is_integer():
                err(path, f"{'months' if MONTHS_RE.search(k) else 'count'} must be an integer, got {val}")
        elif CURRENCY_RE.search(k):
            if isinstance(val, float) and not val.is_integer():
                err(path, f"currency must be an integer number of dollars, got {val}")


def decimals(x) -> int:
    s = repr(float(x))
    if "e" in s or "E" in s:
        return 0
    return len(s.split(".")[1].rstrip("0")) if "." in s else 0


def check_structure(answer, template):
    """Compare top-level keys when the template is a skeleton."""
    if not isinstance(template, dict) or not isinstance(answer, dict):
        return
    shape = None
    for key in ("required_output_shape", "required_top_level_fields"):
        node = template.get(key)
        if isinstance(node, dict):
            shape = node
            break
    expected = set(shape) if shape else (set(template) - META_KEYS)
    if not expected:
        return
    got = set(answer)
    for k in sorted(expected - got):
        err("<root>", f"missing top-level key '{k}'")
    for k in sorted(got - expected):
        warn("<root>", f"top-level key '{k}' is not in the template")


# Words that make a *_count a deliberate subset tally rather than a whole-array total.
SUBSET_WORDS = {
    "high", "medium", "low", "out", "missing", "excluded", "below", "exceeds",
    "required", "unresolved", "open", "distinct", "unique", "blocking",
}
GENERIC_WORDS = {"count", "total", "num", "number"}


def tokens(name: str) -> set[str]:
    return {re.sub(r"s$", "", t) for t in re.split(r"[_\W]+", name.lower()) if t}


def check_counts(answer):
    """*_count fields vs the array they most plausibly describe."""
    # Row arrays (arrays of objects) are what *_count fields normally describe. ID arrays
    # are compared only on a near-exact name match, because a count like
    # continuing_employee_count is a head count, not the length of an ID list.
    row_arrays: dict[str, int] = {}
    id_arrays: dict[str, int] = {}

    def gather(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(v, list):
                    if v and all(isinstance(x, dict) for x in v):
                        row_arrays[k] = len(v)
                    else:
                        id_arrays[k] = len(v)
                gather(v)
        elif isinstance(node, list):
            for v in node:
                gather(v)

    gather(answer)

    def visit(node, path=""):
        if isinstance(node, dict):
            for k, v in node.items():
                p = f"{path}.{k}" if path else k
                if COUNT_RE.search(k) and isinstance(v, int) and not isinstance(v, bool):
                    stem = re.sub(r"_count$", "", k)
                    stem_toks = tokens(stem) - GENERIC_WORDS
                    if stem_toks and not (stem_toks & SUBSET_WORDS):
                        for name, length in row_arrays.items():
                            arr_toks = tokens(name) - GENERIC_WORDS
                            if not (stem_toks & arr_toks) or v == length:
                                continue
                            msg = f"{k}={v} but array '{name}' has {length} entries"
                            (err if stem_toks <= arr_toks else warn)(p, msg)
                        for name, length in id_arrays.items():
                            arr_toks = tokens(name) - GENERIC_WORDS
                            if stem_toks <= arr_toks and v != length:
                                err(p, f"{k}={v} but array '{name}' has {length} entries")
                visit(v, p)
        elif isinstance(node, list):
            for v in node:
                visit(v, path)

    visit(answer)


def check_duplicate_ids(answer):
    def visit(node, path=""):
        if isinstance(node, dict):
            for k, v in node.items():
                visit(v, f"{path}.{k}" if path else k)
        elif isinstance(node, list):
            ids = [v for v in node if isinstance(v, str)]
            if ids and len(set(ids)) != len(ids):
                dupes = sorted({i for i in ids if ids.count(i) > 1})
                warn(path, f"duplicate entries: {dupes}")
            keyed = [v.get("issue_id") or v.get("term_id") or v.get("redline_id")
                     for v in node if isinstance(v, dict)]
            keyed = [k for k in keyed if k]
            if keyed and len(set(keyed)) != len(keyed):
                dupes = sorted({i for i in keyed if keyed.count(i) > 1})
                err(path, f"duplicate row identifiers: {dupes}")
            for i, v in enumerate(node):
                visit(v, f"{path}[{i}]")

    visit(answer)


def check_priority_order(answer):
    """priority_order / negotiation_priority must permute the emitted issue IDs."""
    emitted: set[str] = set()

    def gather(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in ("issue_id", "term_id") and isinstance(v, str):
                    emitted.add(v)
                gather(v)
        elif isinstance(node, list):
            for v in node:
                gather(v)

    gather(answer)
    if not emitted:
        return

    def visit(node, path=""):
        if isinstance(node, dict):
            for k, v in node.items():
                p = f"{path}.{k}" if path else k
                if k in ("priority_order",) and isinstance(v, list):
                    listed = {x for x in v if isinstance(x, str)}
                    for missing in sorted(emitted - listed):
                        warn(p, f"emitted issue '{missing}' is absent from {k}")
                    for extra in sorted(listed - emitted):
                        err(p, f"{k} references '{extra}' which is not an emitted issue")
                visit(v, p)
        elif isinstance(node, list):
            for v in node:
                visit(v, path)

    visit(answer)


def check_id_whitelist(answer, whitelist):
    if not whitelist:
        return

    def visit(node, path=""):
        if isinstance(node, dict):
            for k, v in node.items():
                p = f"{path}.{k}" if path else k
                if k in ("issue_id", "redline_id", "related_issue_id") and isinstance(v, str):
                    if v not in whitelist:
                        err(p, f"'{v}' is not in the template's stable ID list")
                visit(v, p)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                visit(v, f"{path}[{i}]")

    visit(answer)


def load(path):
    with open(path, encoding="utf-8") as fh:
        raw = fh.read()
    stripped = raw.strip()
    if not stripped.startswith(("{", "[")):
        errors.append(f"ERROR {path}: content before the JSON object (fences or prose?)")
    if stripped.startswith("```"):
        errors.append(f"ERROR {path}: markdown fences must not wrap the answer")
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as exc:
        print(f"ERROR {path}: invalid JSON — {exc}", file=sys.stderr)
        sys.exit(1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("answer")
    ap.add_argument("template")
    ap.add_argument("--percent-dp", type=int, default=2,
                    help="decimal places the template requires for percent points")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = ap.parse_args()

    answer = load(args.answer)
    template = load(args.template)

    specs: dict[str, str] = {}
    collect_specs(template, "", specs)
    spec_strings = {v for v in specs.values() if is_spec_string(v)}
    declared_enums = collect_declared_enums(template)
    whitelist = collect_id_whitelist(template)

    check_structure(answer, template)
    check_values(answer, "", spec_strings, declared_enums, args.percent_dp, args.strict)
    check_counts(answer)
    check_duplicate_ids(answer)
    check_priority_order(answer)
    check_id_whitelist(answer, whitelist)

    for line in errors:
        print(line)
    for line in warnings:
        print(line)

    n_err, n_warn = len(errors), len(warnings)
    print(f"\n{n_err} error(s), {n_warn} warning(s)")
    if n_err or (args.strict and n_warn):
        return 1
    print("Mechanical checks passed. Now verify every cited ID and amount against the "
          "workbench by hand — the validator cannot see wrong-but-well-formed values.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
