#!/usr/bin/env python3
"""Check an answer JSON against the contract in its answer_template.json.

    validate_answer.py answer.json answer_template.json

Reports, without being authoritative about business content:
  * values outside an enum vocabulary the template declares
  * IDs outside a fixed stable-ID vocabulary
  * template placeholder text copied through unreplaced
  * non-integer currency / dollar fields
  * malformed dates in *_date fields
  * summary counts that disagree with the arrays they describe
  * top-level keys the template declares but the answer omits

Exit code 1 if any ERROR is reported; WARNs do not fail.
"""

import json
import re
import sys

PIPE = re.compile(r"^\s*[A-Za-z0-9_][A-Za-z0-9_ .\-]*(\s*\|\s*[A-Za-z0-9_][A-Za-z0-9_ .\-]*)+\s*$")
ONE_OF = re.compile(r"one of:\s*(.+)$", re.I)
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MONEY = re.compile(r"(_dollars|_usd|_amount|amount_|_value|pto_liability|headline)", re.I)
PLACEHOLDER = re.compile(
    r"^(string|stable |one of|integer|number|array|object|enum |YYYY|TERM_[A-Z_]*_00|"
    r"category_id|stable_[a-z_]+)", re.I)

errors, warns = [], []


def err(m):
    errors.append(m)


def warn(m):
    warns.append(m)


def walk(node, path=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk(v, "{}.{}".format(path, k) if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, "{}[{}]".format(path, i))
    else:
        yield path, node


def generalize(path):
    """answer.issues[3].risk_rating -> issues[].risk_rating"""
    return re.sub(r"\[\d+\]", "[]", path)


def template_enums(tpl):
    """field-shape -> allowed values, keyed by generalized leaf path and by leaf name."""
    by_path, by_name = {}, {}
    for path, val in walk(tpl):
        if not isinstance(val, str):
            continue
        vals = None
        if PIPE.match(val):
            vals = [v.strip() for v in val.split("|")]
        else:
            m = ONE_OF.search(val)
            if m:
                vals = [v.strip() for v in re.split(r",\s*", m.group(1)) if v.strip()]
        if vals:
            by_path[generalize(path)] = vals
            by_name.setdefault(path.split(".")[-1].split("[")[0], set()).update(vals)

    # explicit blocks: {"allowed_enums": {"risk_rating": [...]}}
    def scan(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in ("allowed_enums", "enums") and isinstance(v, dict):
                    for name, vals in v.items():
                        if isinstance(vals, list):
                            by_name.setdefault(name, set()).update(
                                x for x in vals if isinstance(x, str))
                scan(v)
        elif isinstance(node, list):
            for v in node:
                scan(v)
    scan(tpl)
    return by_path, by_name


def template_vocabs(tpl):
    """Fixed stable-ID vocabularies: {vocab key: set(values)}."""
    out = {}

    def scan(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if (isinstance(v, list) and v and all(isinstance(x, str) for x in v)
                        and re.search(r"stable_|possible_|_ids$", k, re.I)):
                    out[k] = set(v)
                scan(v)
        elif isinstance(node, list):
            for v in node:
                scan(v)
    scan(tpl)
    return out


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    with open(sys.argv[1]) as fh:
        try:
            ans = json.load(fh)
        except json.JSONDecodeError as e:
            print("ERROR  answer is not valid JSON: {}".format(e))
            return 1
    with open(sys.argv[2]) as fh:
        tpl = json.load(fh)

    by_path, by_name = template_enums(tpl)
    vocabs = template_vocabs(tpl)
    all_vocab_values = set().union(*vocabs.values()) if vocabs else set()

    for path, val in walk(ans):
        gpath, leaf = generalize(path), path.split(".")[-1].split("[")[0]

        if isinstance(val, str):
            allowed = by_path.get(gpath) or (
                sorted(by_name[leaf]) if leaf in by_name else None)
            if allowed and val not in allowed:
                err("{} = {!r} not in [{}]".format(path, val, ", ".join(allowed)))
            if PLACEHOLDER.match(val) and val not in (allowed or []):
                err("{} = {!r} looks like unreplaced template placeholder text"
                    .format(path, val))
            if re.search(r"_id$|_ids\[|blocker_id|issue_id|redline_id", path) and all_vocab_values:
                for vkey, vset in vocabs.items():
                    stem = re.sub(r"^(stable_|possible_)|_ids?$", "", vkey, flags=re.I)
                    if stem and stem.rstrip("s") in leaf and val not in vset:
                        err("{} = {!r} not in fixed vocabulary {}".format(path, val, vkey))
            if leaf.endswith("_date") or leaf in ("signing_date", "meeting_date"):
                if not DATE.match(val):
                    err("{} = {!r} is not YYYY-MM-DD".format(path, val))

        if isinstance(val, float) and MONEY.search(leaf) and not val.is_integer():
            err("{} = {} must be an integer dollar amount".format(path, val))
        if isinstance(val, bool):
            continue
        if isinstance(val, (int, float)) and "percent" in leaf and abs(val) > 100:
            warn("{} = {} exceeds 100 percent points — check the unit".format(path, val))

    # summary counts vs the arrays they describe
    def find_arrays(node, path="", acc=None):
        acc = {} if acc is None else acc
        if isinstance(node, dict):
            for k, v in node.items():
                p = "{}.{}".format(path, k) if path else k
                if isinstance(v, list):
                    acc[k] = len(v)
                find_arrays(v, p, acc)
        return acc

    arrays = find_arrays(ans)
    for path, val in walk(ans):
        leaf = path.split(".")[-1]
        if not isinstance(val, int) or isinstance(val, bool):
            continue
        m = re.match(r"(.+?)_count$", leaf)
        if not m:
            continue
        stem = m.group(1)
        for aname, alen in arrays.items():
            if stem.rstrip("s") in aname.rstrip("s") and alen != val and alen:
                warn("{} = {} but array {!r} has {} entries".format(path, val, aname, alen))
                break

    if isinstance(tpl, dict) and isinstance(ans, dict):
        declared = tpl.get("required_top_level_fields") or tpl.get("required_output_shape")
        expected = set(declared) if isinstance(declared, dict) else {
            k for k in tpl
            if not re.match(r"schema_name|schema_version|version|instructions|"
                            r"allowed_enums|possible_|required_|units|language|"
                            r"summary_metrics_fields|issue_object_fields", k)}
        for k in sorted(expected - set(ans)):
            err("missing top-level field {!r}".format(k))

    for m in errors:
        print("ERROR  " + m)
    for m in warns:
        print("WARN   " + m)
    if not errors and not warns:
        print("OK  no contract violations detected "
              "(business correctness still needs review)")
    print("\n{} error(s), {} warning(s)".format(len(errors), len(warns)))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
