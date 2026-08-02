#!/usr/bin/env python3
"""Validate a candidate answer against the task's answer template.

    python3 check_answer.py <answer_template.json> <candidate.json>

Catches the mechanical failures that cost points before anything is submitted:
leftover template placeholders, unknown or missing keys, enum violations,
non-integer currency values, and count fields that disagree with the arrays they
summarize. Exits non-zero when anything is reported.

Templates in this family come in two shapes and both are handled:
  * literal skeletons, whose keys mirror the required answer shape; and
  * spec documents, whose keys describe the answer (``required_*_fields``,
    ``allowed_enums``, ``possible_*_ids``, ``stable_*_ids``, ``required_output_shape``).
"""

import json
import re
import sys

PLACEHOLDER = re.compile(r"^\s*[\w .\-/()]+(\s*\|\s*[\w .\-/()]+)+\s*$")
ENUMISH = re.compile(r"^one of:\s*(.+)$", re.I)
CURRENCY_HINT = re.compile(r"(dollars|_usd|amount|liability|headline_value|price|fee|"
                           r"shortfall|revenue|cost)", re.I)
COUNT_HINT = re.compile(r"_count$|^count$")

problems = []


def report(path, message):
    problems.append(f"{path or '<root>'}: {message}")


def walk(node, path=""):
    """Yield (path, value) for every scalar and container in a JSON document."""
    yield path, node
    if isinstance(node, dict):
        for key, value in node.items():
            yield from walk(value, f"{path}.{key}" if path else key)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from walk(value, f"{path}[{index}]")


def collect_enums(template):
    """Map field name -> allowed values, from every place a template declares them."""
    enums = {}

    def add(field, values):
        values = [v for v in values if isinstance(v, str) and v]
        if values:
            enums.setdefault(field, set()).update(values)

    allowed = template.get("allowed_enums")
    if isinstance(allowed, dict):
        for field, values in allowed.items():
            if isinstance(values, list):
                add(field, values)

    for path, value in walk(template):
        if not isinstance(value, str) or not path:
            continue
        field = path.split(".")[-1].split("[")[0]
        match = ENUMISH.match(value.strip())
        if match:
            add(field, [v.strip() for v in match.group(1).split(",")])
        elif PLACEHOLDER.match(value) and "|" in value:
            add(field, [v.strip() for v in value.split("|")])
    return enums


def collect_id_pools(template):
    """Closed ID lists the answer is expected to draw from."""
    pools = {}
    for path, value in walk(template):
        key = path.split(".")[-1]
        if isinstance(value, list) and re.search(r"(possible|stable|allowed)_\w*ids$", key):
            if all(isinstance(v, str) for v in value) and value:
                pools[key] = set(value)
    return pools


def template_top_level_keys(template):
    """Best-effort set of keys the answer itself should carry."""
    for spec_key in ("required_output_shape", "required_top_level_fields"):
        spec = template.get(spec_key)
        if isinstance(spec, dict):
            return set(spec)
    meta = {"schema_name", "schema_version", "version", "language", "units",
            "allowed_enums", "instructions", "required_output_shape",
            "required_top_level_fields", "issue_object_fields",
            "summary_metrics_fields"}
    keys = {k for k in template if not k.startswith("possible_") and k not in meta}
    return keys or None


def check_placeholders(candidate):
    for path, value in walk(candidate):
        if isinstance(value, str) and (PLACEHOLDER.match(value) or ENUMISH.match(value)):
            report(path, f"unresolved template placeholder {value!r}")


def check_keys(template, candidate):
    expected = template_top_level_keys(template)
    if not expected or not isinstance(candidate, dict):
        return
    for key in sorted(expected - set(candidate)):
        report(key, "required top-level key missing from answer")
    for key in sorted(set(candidate) - expected):
        report(key, "top-level key not present in the template")


def check_enums(enums, candidate):
    for path, value in walk(candidate):
        if not isinstance(value, str) or not path:
            continue
        field = path.split(".")[-1].split("[")[0]
        allowed = enums.get(field)
        if allowed and value not in allowed:
            report(path, f"{value!r} is not an allowed value for {field} "
                         f"({', '.join(sorted(allowed))})")


def check_id_pools(pools, candidate):
    flat = {v for _, v in walk(candidate) if isinstance(v, str)}
    for name, pool in pools.items():
        unused = pool - flat
        if unused:
            report(name, "declared IDs never used in the answer: "
                         + ", ".join(sorted(unused)))


def check_currency_integers(candidate):
    for path, value in walk(candidate):
        field = path.split(".")[-1].split("[")[0]
        if isinstance(value, float) and CURRENCY_HINT.search(field):
            if not value.is_integer():
                report(path, f"currency-like field holds non-integer {value!r}")


# A count qualified by one of these is a filtered subtotal, not the length of an array.
FILTER_WORDS = {"high", "medium", "low", "out", "in", "missing", "draft", "below",
                "exceeds", "policy", "quantified", "excluded", "included"}
# Too generic to establish that a count and an array describe the same thing.
WEAK_TOKENS = {"required", "total", "all", "stable", "source", "id", "ids", "count"}


def tokens(name):
    return {t.rstrip("s") for t in re.split(r"[^a-z]+", name.lower()) if t}


def check_counts(candidate):
    """A total *_count field should equal the length of the array it summarizes."""
    root_arrays = {k: v for k, v in candidate.items()
                   if isinstance(candidate, dict) and isinstance(v, list)}
    for path, node in walk(candidate):
        if not isinstance(node, dict):
            continue
        arrays = dict(root_arrays)
        arrays.update({k: v for k, v in node.items() if isinstance(v, list)})
        for key, value in node.items():
            if not (isinstance(value, int) and not isinstance(value, bool)):
                continue
            if not COUNT_HINT.search(key):
                continue
            stem = tokens(COUNT_HINT.sub("", key))
            if stem & FILTER_WORDS:
                continue
            strong = stem - WEAK_TOKENS
            for name, array in sorted(arrays.items()):
                # ID lists routinely count a different unit than the count field
                # beside them (groups vs people), so they are not comparable.
                if name.endswith("_ids"):
                    continue
                if strong & (tokens(name) - WEAK_TOKENS):
                    if len(array) != value:
                        where = f"{path}.{key}" if path else key
                        report(where, f"{value} does not match len({name}) == {len(array)}")
                    break


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    with open(sys.argv[1]) as handle:
        template = json.load(handle)
    with open(sys.argv[2]) as handle:
        candidate = json.load(handle)

    check_placeholders(candidate)
    check_keys(template, candidate)
    check_enums(collect_enums(template), candidate)
    check_id_pools(collect_id_pools(template), candidate)
    check_currency_integers(candidate)
    check_counts(candidate)

    if problems:
        print(f"{len(problems)} issue(s) found:")
        for problem in problems:
            print("  -", problem)
        return 1
    print("No mechanical problems found. Verify derived amounts and aggregates by hand.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
