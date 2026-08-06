#!/usr/bin/env python3
"""Check a drafted answer against its answer_template.json (and optionally the deal bundle).

Catches the failure modes that silently cost points: enum values that are not on
the allowed list, dollar figures emitted as floats or strings, percentages with
the wrong precision, count fields that disagree with the arrays they summarise,
and record IDs that do not exist in the workbench.

Usage:
    python3 validate_answer.py answer.json input/payloads/answer_template.json
    python3 validate_answer.py answer.json template.json --bundle bundle.json
    python3 validate_answer.py answer.json template.json --percent-decimals 1
"""

import argparse
import json
import re
import sys

# Template keys that describe the schema rather than mirror the output shape.
META_KEYS = {
    "schema_name", "schema_version", "version", "language", "units",
    "allowed_enums", "instructions", "possible_issue_ids",
    "required_top_level_fields", "issue_object_fields", "summary_metrics_fields",
    "required_output_shape", "stable_issue_ids", "stable_redline_ids",
}
SHAPE_KEYS = ("required_output_shape", "required_top_level_fields")

MONEY_RE = re.compile(r"(_dollars|_usd|_amount|amount_)", re.I)
MONEY_EXACT = {"amount", "headline_value", "upfront_cash", "stock_value",
               "milestone_value", "collar_amount", "threshold_amount",
               "annual_revenue", "pto_liability", "pto_liability_total"}
# "low"/"high" are money only inside an exposure block; elsewhere (benchmarks)
# they are percents or months.
MONEY_IN_CONTEXT = {"low": "exposure", "high": "exposure"}
PERCENT_RE = re.compile(r"(_pct|_percent|percent_points|_percent_points)$", re.I)
ID_PREFIX_RE = re.compile(r"^(TERM|CNS|MAT|EMP|RSK|FND|BM|DOC|NOTE|REG|PB|POL|PRJ)_")
# A *record* id embeds the deal id and a numeric suffix (CNS_PRJ_X_01). Templates
# also invite coined ids for synthetic blockers (REG_HSR, EMP_SERVICE_CREDIT);
# those are legitimate and must not be reported as hallucinations.
RECORD_ID_RE = re.compile(
    r"^(TERM|CNS|MAT|EMP|RSK|FND|BM|DOC|NOTE)_(PRJ_[A-Z0-9]+)_\d+$")

problems = []
warnings = []


def note(bucket, path, msg):
    bucket.append(f"{path}: {msg}")


# --------------------------------------------------------------------------
# enum extraction
# --------------------------------------------------------------------------
def parse_inline_enum(text):
    """Pull an allowed-value list out of a template placeholder string."""
    if not isinstance(text, str):
        return None
    s = text.strip()

    m = re.search(r"one of\s*:\s*(.+)$", s, re.I)
    if m:
        vals = [v.strip().strip("`'\"") for v in m.group(1).split(",")]
        return [v for v in vals if v] or None

    # "A | B | C" — only when every branch looks like a literal token.
    if "|" in s and "one of" not in s.lower():
        vals = [v.strip() for v in s.split("|")]
        if len(vals) >= 2 and all(
            v and len(v) < 60 and re.fullmatch(r"[A-Za-z0-9_\- .]+", v) for v in vals
        ):
            return vals
    return None


def resolve_enum(text, global_enums):
    """Return the allowed-value list a template placeholder implies, if any."""
    if not isinstance(text, str):
        return None
    s = text.strip()
    # direct reference: "risk_rating", "enum issue_status"
    m = re.fullmatch(r"(?:enum\s+)?([a-z_]+)", s)
    if m and m.group(1) in global_enums:
        return global_enums[m.group(1)]
    vals = parse_inline_enum(s)
    if vals:
        return vals
    # descriptive reference: "one value from possible_issue_ids",
    # "one allowed business_outcome"
    for name, allowed in global_enums.items():
        if re.search(rf"\b{re.escape(name)}s?\b", s):
            return allowed
    return None


def collect_enum_paths(node, path, global_enums, out, by_leaf):
    """Map answer paths -> allowed values, and record leaf-name candidates too.

    Templates come in two styles: some mirror the output shape, others merely
    describe it (a flat "issue_object_fields" block). Path mapping handles the
    first, leaf-name mapping the second.
    """
    if isinstance(node, dict):
        for k, v in node.items():
            collect_enum_paths(v, f"{path}.{k}" if path else k,
                               global_enums, out, by_leaf)
    elif isinstance(node, list):
        for v in node:
            collect_enum_paths(v, f"{path}[]", global_enums, out, by_leaf)
    elif isinstance(node, str):
        vals = resolve_enum(node, global_enums)
        if vals:
            out[path] = vals
            by_leaf.setdefault(path.split(".")[-1].replace("[]", ""),
                               set()).add(tuple(vals))


def build_shape(template):
    for key in SHAPE_KEYS:
        if isinstance(template.get(key), dict):
            return template[key]
    return {k: v for k, v in template.items() if k not in META_KEYS}


# --------------------------------------------------------------------------
# answer walk
# --------------------------------------------------------------------------
def walk(node, path, enum_paths, leaf_enums, percent_decimals):
    if isinstance(node, dict):
        for k, v in node.items():
            walk(v, f"{path}.{k}" if path else k,
                 enum_paths, leaf_enums, percent_decimals)
        check_counts(node, path)
        return
    if isinstance(node, list):
        for v in node:
            walk(v, f"{path}[]", enum_paths, leaf_enums, percent_decimals)
        return

    leaf = path.split(".")[-1].replace("[]", "")

    if node is None:
        return

    # enum conformance: exact path first, then unambiguous leaf name
    allowed = enum_paths.get(path) or leaf_enums.get(leaf)
    if allowed and isinstance(node, str) and node not in allowed:
        note(problems, path, f"value {node!r} not in allowed {sorted(allowed)}")

    # money must be a plain integer
    if isinstance(node, bool):
        return
    is_money = MONEY_RE.search(leaf) or leaf in MONEY_EXACT
    if leaf in MONEY_IN_CONTEXT:
        is_money = MONEY_IN_CONTEXT[leaf] in path
    if is_money:
        if isinstance(node, float) and not node.is_integer():
            note(problems, path, f"currency {node} is fractional; emit integer dollars")
        elif isinstance(node, float):
            note(problems, path, f"currency {node} is a float; emit {int(node)} as an int")
        elif isinstance(node, str) and re.fullmatch(r"-?[\d,._]+", node):
            note(problems, path, f"currency {node!r} is a string; emit a bare integer")

    # percent precision (percent_decimals maps leaf name -> allowance, "" = default)
    if PERCENT_RE.search(leaf) and isinstance(node, (int, float)):
        allowance = percent_decimals.get(leaf, percent_decimals[""])
        dec = len(str(node).split(".")[1]) if "." in str(node) else 0
        if dec > allowance:
            note(problems, path,
                 f"percent {node} has {dec} decimals; allowed {allowance}")

    # months should be whole numbers
    if leaf.endswith("_months") and isinstance(node, float) and not node.is_integer():
        note(problems, path, f"months {node} must be an integer")


def check_counts(obj, path):
    """A *_count field should equal the length of the array it summarises."""
    for k, v in obj.items():
        if not (k.endswith("_count") and isinstance(v, int)):
            continue
        stem = k[: -len("_count")]
        for cand in (stem, stem + "s", stem + "_ids", stem + "es"):
            arr = obj.get(cand)
            if isinstance(arr, list) and len(arr) != v:
                note(warnings, f"{path}.{k}" if path else k,
                     f"= {v} but sibling '{cand}' has {len(arr)} entries")


# --------------------------------------------------------------------------
# ID cross-check
# --------------------------------------------------------------------------
def collect_ids(node, acc):
    if isinstance(node, dict):
        for v in node.values():
            collect_ids(v, acc)
    elif isinstance(node, list):
        for v in node:
            collect_ids(v, acc)
    elif isinstance(node, str) and ID_PREFIX_RE.match(node):
        acc.add(node)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("answer")
    ap.add_argument("template")
    ap.add_argument("--bundle", help="bundle from fetch_deal.py, to verify record IDs")
    ap.add_argument("--percent-decimals", default="2",
                    help="max decimals for percent fields; per-field overrides allowed, "
                         "e.g. --percent-decimals '1,fully_diluted_pct=4'")
    args = ap.parse_args()

    percent_decimals = {"": 2}
    for part in str(args.percent_decimals).split(","):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            field, val = part.split("=", 1)
            percent_decimals[field.strip()] = int(val)
        else:
            percent_decimals[""] = int(part)

    try:
        with open(args.answer) as fh:
            answer = json.load(fh)
    except json.JSONDecodeError as exc:
        sys.exit(f"FAIL: answer is not valid JSON -> {exc}")
    with open(args.template) as fh:
        template = json.load(fh)

    global_enums = {k: v for k, v in (template.get("allowed_enums") or {}).items()
                    if isinstance(v, list)}
    # a bare list of stable ids is also an allowed-value set
    for key in ("possible_issue_ids", "stable_issue_ids", "stable_redline_ids"):
        for src in (template, template.get("instructions") or {}):
            if isinstance(src, dict) and isinstance(src.get(key), list):
                global_enums[key] = src[key]

    shape = build_shape(template)
    enum_paths, by_leaf = {}, {}
    collect_enum_paths(shape, "", global_enums, enum_paths, by_leaf)
    # Descriptive side-blocks (issue_object_fields, ...) contribute leaf names only.
    for key in ("issue_object_fields", "summary_metrics_fields"):
        if isinstance(template.get(key), dict):
            collect_enum_paths(template[key], "", global_enums, {}, by_leaf)
    # A leaf name is only safe to check when it maps to one distinct enum.
    leaf_enums = {k: set(next(iter(v))) for k, v in by_leaf.items() if len(v) == 1}

    # top-level key comparison (only when the template mirrors the output)
    tmpl_top = set(shape.keys())
    ans_top = set(answer.keys()) if isinstance(answer, dict) else set()
    missing = tmpl_top - ans_top
    extra = ans_top - tmpl_top
    if missing:
        note(problems, "<top-level>", f"missing required keys: {sorted(missing)}")
    if extra:
        note(warnings, "<top-level>", f"keys not in template: {sorted(extra)}")

    walk(answer, "", enum_paths, leaf_enums, percent_decimals)

    # stable-id enums applied by convention to *issue_id / *redline_id fields
    for name, field in (("possible_issue_ids", "issue_id"),
                        ("stable_issue_ids", "issue_id"),
                        ("stable_redline_ids", "redline_id")):
        allowed = global_enums.get(name)
        if not allowed:
            continue
        for path, val in iter_leaves(answer, ""):
            if path.split(".")[-1].replace("[]", "") == field and val not in allowed:
                note(problems, path, f"{val!r} not in {name} {allowed}")

    if args.bundle:
        with open(args.bundle) as fh:
            bundle = json.load(fh)
        known = set()
        collect_ids(bundle, known)
        used = set()
        collect_ids(answer, used)
        unknown = {u for u in used - known if RECORD_ID_RE.match(u)}
        if unknown:
            note(problems, "<ids>", f"not present in the deal bundle: {sorted(unknown)}")
        coined = {u for u in used - known if not RECORD_ID_RE.match(u)}
        if coined:
            note(warnings, "<ids>",
                 f"coined (not workbench records) - fine if the template asks for "
                 f"synthetic ids: {sorted(coined)}")

    print(f"answer   : {args.answer}")
    print(f"template : {args.template}")
    print(f"enum-checked paths: {len(enum_paths)}  leaf-name enums: {len(leaf_enums)}")
    for w in warnings:
        print(f"  WARN  {w}")
    for p in problems:
        print(f"  FAIL  {p}")
    if problems:
        print(f"\n{len(problems)} problem(s), {len(warnings)} warning(s)")
        sys.exit(1)
    print(f"\nOK - no blocking problems ({len(warnings)} warning(s))")


def iter_leaves(node, path):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from iter_leaves(v, f"{path}.{k}" if path else k)
    elif isinstance(node, list):
        for v in node:
            yield from iter_leaves(v, f"{path}[]")
    elif isinstance(node, str):
        yield path, node


if __name__ == "__main__":
    main()
