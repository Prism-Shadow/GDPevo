#!/usr/bin/env python3
"""Extract the machine-checkable constraints from a task's answer_template.json.

The template files in this task family are hand-written JSON "shape" specs (their
exact key layout varies from task to task), but they consistently encode four
kinds of constraints. This walks any of them and surfaces:

  * REQUIRED KEYS   - every ``required*`` / ``*required_keys`` list
  * CONSTANTS       - ``required_value`` / ``constant`` / ``expected_value`` pins
  * ENUMS           - every ``allowed_values`` / ``allowed`` controlled vocabulary
  * ORDERINGS       - every ``ordering`` directive

Use it as a checklist before emitting the final answer: your JSON must contain
exactly the required keys, echo the constants verbatim, use only listed enum
values in the corresponding fields, and honor each ordering rule.

Usage:
    python3 template_constraints.py path/to/answer_template.json
"""
import json
import sys


def walk(node, path, out):
    if isinstance(node, dict):
        for key, val in node.items():
            here = f"{path}.{key}" if path else key
            kl = key.lower()
            if kl in ("required_value", "constant", "expected_value"):
                out["constants"].append((path or "<root>", val))
            elif kl in ("allowed_values", "allowed") and isinstance(val, list):
                out["enums"].append((path or "<root>", val))
            elif kl == "ordering" and isinstance(val, str):
                out["orderings"].append((path or "<root>", val))
            elif ("required" in kl and isinstance(val, list)
                  and all(isinstance(x, str) for x in val)):
                out["required"].append((here, val))
            walk(val, here, out)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            walk(item, f"{path}[{i}]", out)


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: template_constraints.py path/to/answer_template.json")
    with open(sys.argv[1]) as fh:
        template = json.load(fh)
    out = {"required": [], "constants": [], "enums": [], "orderings": []}
    walk(template, "", out)

    print("=== REQUIRED KEYS (your JSON must contain exactly these) ===")
    for path, vals in out["required"]:
        print(f"  {path}: {vals}")
    print("\n=== CONSTANTS (echo verbatim) ===")
    for path, val in out["constants"]:
        print(f"  {path} == {val!r}")
    print("\n=== ENUMS (use only these values in the matching field) ===")
    seen = set()
    for path, vals in out["enums"]:
        key = (path, tuple(vals))
        if key in seen:
            continue
        seen.add(key)
        print(f"  {path}: {vals}")
    print("\n=== ORDERINGS (sort lists exactly as stated) ===")
    for path, rule in out["orderings"]:
        print(f"  {path}: {rule}")


if __name__ == "__main__":
    main()
