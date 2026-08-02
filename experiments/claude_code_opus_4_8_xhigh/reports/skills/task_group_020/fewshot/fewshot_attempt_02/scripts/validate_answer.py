#!/usr/bin/env python3
"""Validate a deal-workbench answer against its answer_template.json.

Catches the mechanical failures that cost points regardless of legal judgment:
unreplaced placeholders, invalid enum values, descriptor-wrapper leakage,
non-integer dollars, missing template keys, duplicate/unknown stable IDs.

Usage:
    python3 validate_answer.py answer.json path/to/answer_template.json
    python3 validate_answer.py answer.json template.json --quiet   # errors only

Exit status: 0 clean (warnings allowed), 1 errors found, 2 could not run.
This checks SHAPE, not legal correctness -- a clean run does not mean the
substantive analysis is right.
"""

import argparse
import json
import re
import sys

# Template keys that describe the output rather than being part of it.
DESCRIPTOR_KEYS = {
    "schema_name",
    "schema_version",
    "version",
    "language",
    "units",
    "instructions",
    "allowed_enums",
    "possible_issue_ids",
    "required_top_level_fields",
    "issue_object_fields",
    "summary_metrics_fields",
    "required_output_shape",
}

SHAPE_KEYS = ("required_output_shape", "required_top_level_fields")

MONEY_HINTS = (
    "_dollars",
    "_usd",
    "amount",
    "liability",
    "revenue",
    "consideration",
    "exposure",
    "collar",
    "cash",
    "price",
    "headline_value",
    "stock_value",
    "milestone_value",
)

PCT_HINTS = ("percent", "_pct", "pct_")

ID_LIST_TO_KEY = {
    "possible_issue_ids": "issue_id",
    "stable_issue_ids": "issue_id",
    "stable_redline_ids": "redline_id",
}


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.notes = []

    def err(self, path, msg):
        self.errors.append((path, msg))

    def warn(self, path, msg):
        self.warnings.append((path, msg))

    def note(self, msg):
        self.notes.append(msg)


def parse_enum_string(s):
    """Return the option list encoded in a template placeholder string, if any."""
    if not isinstance(s, str):
        return None
    txt = s.strip()
    low = txt.lower()
    if low.startswith("one of:"):
        body = txt.split(":", 1)[1]
        opts = [o.strip().strip("`'\"") for o in body.split(",")]
        return [o for o in opts if o] or None
    if "|" in txt and "://" not in txt:
        opts = [o.strip().strip("`'\"") for o in txt.split("|")]
        opts = [o for o in opts if o]
        # require plausible enum tokens, not prose sentences
        if len(opts) >= 2 and all(len(o.split()) <= 6 for o in opts):
            return opts
    return None


def walk(node, path, fn):
    fn(node, path)
    if isinstance(node, dict):
        for k, v in node.items():
            walk(v, f"{path}.{k}" if path else k, fn)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, f"{path}[{i}]", fn)


def collect_enums(template):
    """key name -> set of allowed values, gathered from every template dialect."""
    enums = {}

    def add(key, opts):
        enums.setdefault(key, set()).update(opts)

    allowed = template.get("allowed_enums")
    if isinstance(allowed, dict):
        for k, v in allowed.items():
            if isinstance(v, list):
                add(k, [str(x) for x in v])

    instr = template.get("instructions")
    if isinstance(instr, dict):
        for list_name, key in ID_LIST_TO_KEY.items():
            vals = instr.get(list_name)
            if isinstance(vals, list):
                add(key, [str(x) for x in vals])
    for list_name, key in ID_LIST_TO_KEY.items():
        vals = template.get(list_name)
        if isinstance(vals, list):
            add(key, [str(x) for x in vals])

    def visit(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                opts = parse_enum_string(v)
                if opts:
                    add(k, opts)
                # descriptor form: "enum risk_rating" / "one allowed risk_rating"
                if isinstance(v, str) and isinstance(allowed, dict):
                    for name in allowed:
                        if re.search(rf"\b(enum|allowed|one value from|one of)\b.*\b{re.escape(name)}\b", v):
                            add(k, [str(x) for x in allowed[name]])

    walk(template, "", visit)
    return {k: v for k, v in enums.items() if v}


def expected_top_level(template):
    for key in SHAPE_KEYS:
        shape = template.get(key)
        if isinstance(shape, dict):
            return set(shape.keys()), key
    top = {k for k in template if k not in DESCRIPTOR_KEYS}
    return top, None


def skeleton_required_keys(template):
    """For skeleton templates: object path signature -> keys that must be present.

    Paths are normalized so every list element shares one signature.
    """
    sig = {}

    def norm(path):
        return re.sub(r"\[\d+\]", "[]", path)

    def visit(node, path):
        if isinstance(node, dict):
            p = norm(path)
            if p not in ("", *DESCRIPTOR_KEYS):
                sig.setdefault(p, set()).update(node.keys())

    walk(template, "", visit)
    return sig


def is_money_key(k):
    kl = k.lower()
    if any(h in kl for h in PCT_HINTS):
        return False
    return any(h in kl for h in MONEY_HINTS)


def is_pct_key(k):
    kl = k.lower()
    return any(h in kl for h in PCT_HINTS)


def check_answer(answer, template, rep):
    enums = collect_enums(template)
    exp_top, shape_key = expected_top_level(template)

    # 1. descriptor wrapper leakage + top-level key agreement
    if isinstance(answer, dict):
        leaked = sorted(set(answer) & DESCRIPTOR_KEYS & set(template))
        if leaked and shape_key:
            rep.err("<root>", f"descriptor wrapper keys copied into the answer: {leaked}")
        missing = sorted(exp_top - set(answer))
        extra = sorted(set(answer) - exp_top)
        if missing:
            rep.err("<root>", f"missing required top-level keys: {missing}")
        if extra:
            rep.warn("<root>", f"top-level keys not in the template: {extra}")
    else:
        rep.err("<root>", "answer must be a JSON object")
        return

    # 2. skeleton completeness: every templated key present on each object.
    #    Some templates describe a *variant* object whose keys depend on the row's
    #    category (only the applicable subset belongs on any one row). Those are
    #    detected by looking across siblings: a key that shows up on at least one
    #    sibling is variant (warn); a key absent everywhere is a real omission.
    if shape_key is None:
        sig = skeleton_required_keys(template)

        def norm(path):
            return re.sub(r"\[\d+\]", "[]", path)

        supplied = {}

        def gather_keys(node, path):
            if isinstance(node, dict):
                p = norm(path)
                if p in sig:
                    supplied.setdefault(p, set()).update(node.keys())

        walk(answer, "", gather_keys)

        def visit(node, path):
            if isinstance(node, dict):
                p = norm(path)
                want = sig.get(p)
                if not want:
                    return
                absent = sorted(want - set(node))
                if not absent:
                    return
                seen = supplied.get(p, set())
                variant = sorted(k for k in absent if k in seen)
                never = sorted(k for k in absent if k not in seen)
                if never:
                    rep.err(path or "<root>", f"templated keys missing everywhere: {never}")
                if variant:
                    rep.warn(
                        path or "<root>",
                        f"keys omitted here but present on sibling rows: {variant} "
                        "(fine for category-dependent objects; otherwise fill them in)",
                    )

        walk(answer, "", visit)

    # 3. per-value checks
    template_strings = set()
    walk(template, "", lambda n, p: template_strings.add(n) if isinstance(n, str) else None)
    all_enum_values = {val for vals in enums.values() for val in vals}

    def allowed_for(key):
        """Enum set for a key, tolerating related_/source_/primary_ prefixes."""
        if key in enums:
            return enums[key]
        for prefix in ("related_", "source_", "primary_", "excluded_", "required_"):
            if key.startswith(prefix) and key[len(prefix):] in enums:
                return enums[key[len(prefix):]]
        return None

    def visit(node, path):
        if not isinstance(node, dict):
            return
        for k, v in node.items():
            p = f"{path}.{k}" if path else k

            if isinstance(v, str):
                # unreplaced placeholder text
                if parse_enum_string(v):
                    rep.err(p, f"placeholder enum string left in place: {v!r}")
                elif re.match(r"^(stable|string|integer|number|one |array of|enum |object )", v.strip(), re.I):
                    rep.err(p, f"placeholder description left in place: {v!r}")
                elif (
                    v in template_strings
                    and len(v) > 12
                    and v not in all_enum_values
                    and " " in v
                    and k not in ("prepared_for", "currency")
                ):
                    rep.warn(p, f"prose copied verbatim from the template: {v!r}")

                allowed = allowed_for(k)
                if allowed and v not in allowed:
                    rep.err(p, f"value {v!r} not in allowed set for {k!r}: {sorted(allowed)}")

            if isinstance(v, bool):
                continue
            if isinstance(v, (int, float)):
                if v != v or v in (float("inf"), float("-inf")):
                    rep.err(p, "non-finite number")
                elif is_money_key(k) and isinstance(v, float):
                    if v.is_integer():
                        rep.err(p, f"currency must be an integer, got float {v!r} (write {int(v)})")
                    else:
                        rep.err(p, f"currency must be an integer dollars value, got {v!r}")
                elif is_pct_key(k) and isinstance(v, float):
                    dec = len(str(v).split(".")[1].rstrip("0")) if "." in str(v) else 0
                    if dec > 4:
                        rep.warn(p, f"percent {v!r} has {dec} decimals; confirm the prompt's precision")

            if isinstance(v, list) and v and all(isinstance(x, str) for x in v):
                dupes = sorted({x for x in v if v.count(x) > 1})
                if dupes:
                    rep.warn(p, f"duplicate entries: {dupes}")
                allowed = allowed_for(k) or allowed_for(k[:-1] if k.endswith("s") else k)
                if allowed:
                    bad = [x for x in v if x not in allowed]
                    if bad and k.endswith(("_ids", "_order", "_terms", "_categories", "priority")):
                        rep.warn(p, f"entries not in the declared vocabulary for {k!r}: {bad}")

    walk(answer, "", visit)

    # 4. cross-checks that are cheap and catch real slips
    counts = {}

    def gather(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(v, list) and k not in counts:
                    counts[k] = len(v)

    walk(answer, "", gather)

    def find_ints(node, path, acc):
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(v, int) and not isinstance(v, bool) and k.endswith("_count"):
                    acc[k] = v
                find_ints(v, f"{path}.{k}", acc)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                find_ints(v, f"{path}[{i}]", acc)

    declared = {}
    find_ints(answer, "", declared)
    for cname, cval in declared.items():
        stem = cname[: -len("_count")].rstrip("s")
        for lname, lval in counts.items():
            if stem and lname.rstrip("s") == stem and lval != cval:
                rep.note(f"{cname}={cval} vs len({lname})={lval} - confirm this is intended")
                break

    rep.note(f"enum vocabularies recognized: {sorted(enums)}" if enums else "no enum vocabulary found in template")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("answer")
    ap.add_argument("template")
    ap.add_argument("--quiet", action="store_true", help="suppress warnings and notes")
    args = ap.parse_args()

    try:
        with open(args.answer, encoding="utf-8") as fh:
            answer = json.load(fh)
    except Exception as exc:  # noqa: BLE001
        print(f"FATAL: answer is not valid JSON: {exc}")
        return 2
    try:
        with open(args.template, encoding="utf-8") as fh:
            template = json.load(fh)
    except Exception as exc:  # noqa: BLE001
        print(f"FATAL: template is not valid JSON: {exc}")
        return 2

    rep = Report()
    check_answer(answer, template, rep)

    for path, msg in rep.errors:
        print(f"ERROR  {path}: {msg}")
    if not args.quiet:
        for path, msg in rep.warnings:
            print(f"WARN   {path}: {msg}")
        for msg in rep.notes:
            print(f"NOTE   {msg}")

    print(f"\n{len(rep.errors)} error(s), {len(rep.warnings)} warning(s)")
    if rep.errors:
        print("Shape check FAILED - fix the errors above before returning the answer.")
        return 1
    print("Shape check passed (does not verify legal or arithmetic correctness).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
