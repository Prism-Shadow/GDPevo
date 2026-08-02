#!/usr/bin/env python3
"""Check a drafted answer against its answer_template.json before you submit.

Usage:
    python3 validate_answer.py answer.json path/to/answer_template.json \
        [--percent-decimals 2]

Catches the failure modes that cost points on these tasks:
  * template placeholder text ("string", "stable consent ID", "LOW | MEDIUM | HIGH")
    copied through into the answer
  * enum values outside the template's allowed vocabulary
  * identifiers outside a template's declared stable-ID list
  * non-integer dollar amounts, or percents with too many decimals
  * required fields declared by the template but missing from an object

Exit status is 1 when any ERROR is reported. WARNs are judgment calls: read them,
then decide. The script validates form, never business logic - it cannot tell you
whether you picked the right issues or the right numbers.
"""

import argparse
import json
import re
import sys

# Matched against the full JSON path, so `exposure.low` counts as currency
# while a bare `draft_metric.value` (which may be percent points) does not.
MONEY_HINT = re.compile(
    r"(dollars|_usd|amount|liability|revenue|exposure|price|cash)", re.I)
PCT_HINT = re.compile(r"(percent|_pct)", re.I)
# Template text that reads like a field descriptor rather than a fixed constant.
DESCRIPTOR_WORD = re.compile(
    r"\b(name|id|ids|string|integer|number|array|object|enum|stable)\b", re.I)
MONTH_HINT = re.compile(r"(months|_days|count|shares|rank|size)$", re.I)
ID_HINT = re.compile(r"(_id|_ids)$", re.I)
DATE_KEY = re.compile(r"date$", re.I)
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Template prose that must never survive into an answer.
PLACEHOLDER_PAT = re.compile(
    r"(^|\s)(one of:|stable\s|string$|integer$|number$|array of|object$"
    r"|YYYY-MM-DD|enum\s|or null$)", re.I)

errors, warnings = [], []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def walk(node, path="$"):
    """Yield (path, key, value) for every leaf and container in a JSON tree."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield f"{path}.{k}", k, v
            yield from walk(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield f"{path}[{i}]", None, v
            yield from walk(v, f"{path}[{i}]")


def split_enum(spec):
    """'LOW | MEDIUM | HIGH' or 'one of: a, b, c' -> vocabulary list."""
    if not isinstance(spec, str):
        return None
    s = spec.strip()
    m = re.match(r"^one of:\s*(.+)$", s, re.I)
    if m:
        vals = [v.strip() for v in re.split(r"[,|]", m.group(1))]
        return [v for v in vals if v and " " not in v.strip("_")]
    if "|" in s and "\n" not in s:
        vals = [v.strip() for v in s.split("|")]
        if all(vals) and all(len(v) < 60 for v in vals):
            return vals
    return None


def collect_template(tpl):
    """Extract enum vocabularies, stable-ID lists, and required field names."""
    enums = {}          # key name -> allowed values
    id_vocab = {}       # declaring key name -> declared identifiers
    required = {}       # descriptor-block name -> [field names]
    placeholders = set()

    for path, key, val in walk(tpl):
        if isinstance(val, str):
            placeholders.add(val.strip())
            vocab = split_enum(val)
            if vocab and key:
                enums.setdefault(key, set()).update(vocab)
        if isinstance(val, list) and val and all(isinstance(x, str) for x in val):
            # allowed_enums.<name>: [...] and possible_*/stable_* id lists
            parent = path.rsplit(".", 1)[0]
            if parent.endswith("allowed_enums") and key:
                enums.setdefault(key, set()).update(val)
            elif key and re.search(r"(possible|stable)_", key):
                id_vocab.setdefault(key, set()).update(val)
        if isinstance(val, dict) and key and (
                key.endswith("_fields") or key.startswith("required_")):
            names = [k for k, v in val.items()
                     if isinstance(v, (str, list, dict))]
            if names:
                required[key] = names
    return enums, id_vocab, required, placeholders


def vocab_for_key(key, id_vocab):
    """Match an answer key to the ID list that governs it, or None.

    'issue_id' -> 'possible_issue_ids'; 'related_issue_id' -> 'stable_issue_ids'
    via suffix backoff. 'source_record_ids' matches nothing, so it is not
    policed - the template never declared a vocabulary for those.
    """
    stem = re.sub(r"s$", "", key)
    parts = stem.split("_")
    for start in range(len(parts) - 1):        # require >=2 parts, never bare 'id'
        suffix = "_".join(parts[start:])
        for vkey, values in id_vocab.items():
            if suffix in vkey:
                return vkey, values
    return None


def decimals(x):
    s = repr(float(x))
    if "e" in s or "E" in s:
        return 0
    return len(s.split(".")[1].rstrip("0")) if "." in s else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("answer")
    ap.add_argument("template")
    ap.add_argument(
        "--percent-decimals", action="append", default=[],
        help="max decimal places for percents: '2' for the default, or "
             "'fully_diluted_pct=4' to override one key. Repeatable.")
    args = ap.parse_args()

    pct_default, pct_by_key = 2, {}
    for spec in args.percent_decimals:
        if "=" in spec:
            k, _, v = spec.partition("=")
            pct_by_key[k.strip()] = int(v)
        else:
            pct_default = int(spec)

    raw = open(args.answer).read()
    try:
        ans = json.loads(raw)
    except json.JSONDecodeError as exc:
        sys.exit(f"ERROR: answer is not valid JSON: {exc}")
    if raw.lstrip()[:1] not in "{[":
        err("answer file has content before the JSON value")

    tpl = json.load(open(args.template))
    enums, id_vocab, required, placeholders = collect_template(tpl)
    # Any value the template itself sanctions somewhere is never a placeholder.
    sanctioned = set()
    for vals in enums.values():
        sanctioned.update(vals)
    for vals in id_vocab.values():
        sanctioned.update(vals)

    seen_keys = set()
    for path, key, val in walk(ans):
        if key:
            seen_keys.add(key)

        if isinstance(val, str):
            if PLACEHOLDER_PAT.search(val) or "|" in val and len(val) < 90:
                err(f"{path}: template placeholder text left in answer: {val!r}")
            elif (val.strip() in placeholders and " " in val.strip()
                    and val.strip() not in sanctioned
                    and DESCRIPTOR_WORD.search(val.strip())):
                warn(f"{path}: value equals template descriptor text: {val!r}")
            if DATE_KEY.search(key or "") and not ISO_DATE.match(val):
                err(f"{path}: date not in YYYY-MM-DD form: {val!r}")

        if key and key in enums and val is not None:
            vocab = enums[key]
            vals = val if isinstance(val, list) else [val]
            for v in vals:
                if isinstance(v, str) and v not in vocab:
                    err(f"{path}: {v!r} not in allowed {key} values "
                        f"{sorted(vocab)}")

        if key and ID_HINT.search(key) and id_vocab:
            match = vocab_for_key(key, id_vocab)
            if match:
                vkey, allowed = match
                vals = val if isinstance(val, list) else [val]
                for v in vals:
                    if isinstance(v, str) and v not in allowed:
                        err(f"{path}: {v!r} is not in the template's "
                            f"{vkey} list")

        if isinstance(val, bool) or val is None or not isinstance(
                val, (int, float)):
            continue
        if PCT_HINT.search(path):
            limit = pct_by_key.get(key, pct_default)
            if decimals(val) > limit:
                err(f"{path}: percent {val} exceeds {limit} decimal places "
                    f"(override with --percent-decimals {key}=N)")
        elif MONEY_HINT.search(path):
            if isinstance(val, float) and not val.is_integer():
                err(f"{path}: currency must be integer dollars, got {val}")
        elif MONTH_HINT.search(key or ""):
            if isinstance(val, float) and not val.is_integer():
                err(f"{path}: {key} must be an integer, got {val}")

    for block, names in required.items():
        for name in names:
            if name not in seen_keys:
                warn(f"template block {block!r} declares field {name!r}, "
                     f"which does not appear anywhere in the answer")

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
