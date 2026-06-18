#!/usr/bin/env python3
"""Sanity-check a ProcureOps answer JSON before you emit it.

Usage:
    python scripts/validate_answer.py <answer.json> [<answer_template.json>]

It is a lint, not a grader: it checks the JSON parses, that money-looking
numbers are rounded to <= 2 decimals, that fields the template marks "sorted
ascending"/"alphabetical" are actually sorted, and (if a template is given)
that the template's required top-level keys are present. It cannot know the
correct values — that is on you. Warnings are advisory; read them and decide.
"""
import json
import re
import sys
from decimal import Decimal


def load(path):
    with open(path) as f:
        return json.load(f)


def decimals(x):
    s = format(Decimal(str(x)), "f")
    return len(s.split(".")[1]) if "." in s else 0


MONEY_HINT = re.compile(
    r"(amount|total|value|balance|subtotal|tax|freight|headroom|budget|"
    r"committed|price|impact|releasable|held|cap)",
    re.I,
)
QTY_PCT_HINT = re.compile(r"(pct|percent|ratio)", re.I)


def walk(node, path, warns):
    if isinstance(node, dict):
        for k, v in node.items():
            walk(v, f"{path}.{k}", warns)
    elif isinstance(node, list):
        # flag obviously-unsorted string id lists (advisory only)
        strs = [x for x in node if isinstance(x, str)]
        if len(strs) == len(node) and len(strs) > 1 and strs != sorted(strs):
            warns.append(f"[order?] {path} is a string list but not sorted "
                         f"ascending — sort it if the template says so.")
        for i, v in enumerate(node):
            walk(v, f"{path}[{i}]", warns)
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        leaf = path.split(".")[-1].split("[")[0]
        if MONEY_HINT.search(leaf) and not QTY_PCT_HINT.search(leaf):
            if decimals(node) > 2:
                warns.append(f"[money] {path} = {node} has >2 decimals; "
                             f"round to cents.")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    try:
        ans = load(sys.argv[1])
    except json.JSONDecodeError as e:
        print(f"FAIL: answer is not valid JSON: {e}")
        sys.exit(2)

    warns = []
    walk(ans, "$", warns)

    if len(sys.argv) >= 3:
        try:
            tmpl = load(sys.argv[2])
        except Exception:
            tmpl = None
        if isinstance(tmpl, dict):
            req = tmpl.get("required_top_level_keys") or tmpl.get(
                "top_level_required_keys")
            if req and isinstance(ans, dict):
                missing = [k for k in req if k not in ans]
                if missing:
                    warns.append(f"[keys] missing required top-level keys: "
                                 f"{missing}")

    if warns:
        print(f"{len(warns)} advisory warning(s):")
        for w in warns:
            print("  " + w)
    else:
        print("OK: JSON parses, money looks rounded, id lists look sorted.")


if __name__ == "__main__":
    main()
