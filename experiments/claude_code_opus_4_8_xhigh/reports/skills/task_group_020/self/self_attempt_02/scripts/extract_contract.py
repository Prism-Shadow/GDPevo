#!/usr/bin/env python3
"""Extract the machine-checkable contract from an answer_template.json.

Templates express their rules in several styles:
  * an "allowed_enums" / "possible_*" block mapping a name to a list
  * inline pipe strings, e.g. "LOW | MEDIUM | HIGH"
  * inline prose, e.g. "one of: a, b, c"
  * stable-ID lists, e.g. "stable_issue_ids": [...]
  * unit declarations, e.g. "currency": "integer USD"

This prints all of them plus the required field tree, so the contract is visible
in one place before you start building the answer.

    extract_contract.py <answer_template.json>
"""

import json
import re
import sys

PIPE = re.compile(r"^\s*[A-Za-z0-9_][A-Za-z0-9_ .\-]*(\s*\|\s*[A-Za-z0-9_][A-Za-z0-9_ .\-]*)+\s*$")
ONE_OF = re.compile(r"one of:\s*(.+)$", re.I)
UNIT_HINT = re.compile(
    r"integer|decimal|percent|month|YYYY|round|two decimal|one decimal|four decimal|whole",
    re.I)
ENUM_BLOCK = re.compile(r"allowed_enums|possible_|stable_|_ids$|^enums$", re.I)


def walk(node, path=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk(v, "{}.{}".format(path, k) if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, "{}[{}]".format(path, i))
    else:
        yield path, node


def collect_id_lists(node, path="", out=None):
    """Lists of plain strings under a vocabulary-ish key are fixed vocabularies."""
    out = {} if out is None else out
    if isinstance(node, dict):
        for k, v in node.items():
            p = "{}.{}".format(path, k) if path else k
            if isinstance(v, list) and v and all(isinstance(x, str) for x in v):
                if ENUM_BLOCK.search(k) or len(v) > 2:
                    out[p] = v
            collect_id_lists(v, p, out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            collect_id_lists(v, "{}[{}]".format(path, i), out)
    return out


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    with open(sys.argv[1]) as fh:
        tpl = json.load(fh)

    enums, units, notes = {}, {}, {}
    for path, val in walk(tpl):
        if not isinstance(val, str):
            continue
        if PIPE.match(val):
            enums[path] = [v.strip() for v in val.split("|")]
        else:
            m = ONE_OF.search(val)
            if m:
                enums[path] = [v.strip() for v in re.split(r",\s*", m.group(1)) if v.strip()]
            elif UNIT_HINT.search(val):
                units[path] = val
            elif len(val) < 200 and val:
                notes[path] = val

    print("=" * 72)
    print("ENUM VOCABULARIES  (copy values verbatim)")
    print("=" * 72)
    for p in sorted(enums):
        print("  {}\n      {}".format(p, " | ".join(enums[p])))
    if not enums:
        print("  (none inline — check the fixed vocabularies below)")

    print()
    print("=" * 72)
    print("FIXED VOCABULARIES / STABLE ID LISTS")
    print("=" * 72)
    vocab = collect_id_lists(tpl)
    for p in sorted(vocab):
        print("  {}  ({} values)".format(p, len(vocab[p])))
        for v in vocab[p]:
            print("      - {}".format(v))

    print()
    print("=" * 72)
    print("UNIT / FORMAT DECLARATIONS")
    print("=" * 72)
    for p in sorted(units):
        print("  {:<52} {}".format(p, units[p]))
    if not units:
        print("  (none — take units from the prompt)")

    print()
    print("=" * 72)
    print("FIELD TREE  (leaf -> placeholder)")
    print("=" * 72)
    for path, val in walk(tpl):
        shown = val if isinstance(val, str) and len(val) <= 60 else (
            "<{}>".format(type(val).__name__) if not isinstance(val, str)
            else val[:57] + "...")
        print("  {:<58} {}".format(path, shown))

    print()
    print("REMINDERS")
    print("  - emit one object per fixed stable ID, not one per record found")
    print("  - null is a real value where the template allows it; do not use 0")
    print("  - counts in summary blocks must agree with the arrays they describe")
    print("  - return the JSON object alone, with no surrounding prose")
    return 0


if __name__ == "__main__":
    sys.exit(main())
