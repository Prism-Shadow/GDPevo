# Answer-contract checker

How to validate that `answer.json` exactly conforms to `answer_template.json` before you finish. The goal: one JSON object whose key set equals the template's `required` set, with correct types, precision, enums, patterns, array sizes/order, and no extra keys or commentary.

## Static checks
1. **Parses as a single JSON object.** `python3 -c "import json,sys; json.load(open('answer.json'))"` must succeed and return a `dict`. No leading BOM, no trailing prose, no array wrapper.
2. **Key set equality.** Compare `set(answer.keys())` to `set(template['required'])`. Both must be equal. Template `additionalProperties: false` makes any extra key a failure; a missing required key is a failure.
3. **Per-field rules** from `template['properties'][field]`:
   - `type: integer` → `isinstance(v, int)` and not `bool`. `type: number` → `int` or `float`. `type: string` → `isinstance(v, str)`.
   - `minimum`/`maximum` → inclusive bounds check.
   - `multipleOf` (e.g. `0.0001`, `0.01`) → `abs(round(v/a)*a - v) < 1e-9`.
   - `enum` → `v in enum`.
   - `pattern` (e.g. `^ORD-[0-9]{6}$`) → `re.match(pattern, v)` full-match.
   - `minItems`/`maxItems` → length bounds; `uniqueItems` → `len(set(...)) == len(...)`.
   - Nested objects: recurse into `properties` with their own `required`/`additionalProperties: false`.
4. **Ordering.** Where the template carries an `order`/`ordering`/description note (e.g. "ascending", "rate asc then region asc"), assert the sequence satisfies it on the unrounded/computed basis where the note implies it.
5. **No nested arrays where forbidden.** Some templates carry an `x-list-ordering: "No arrays are permitted in this output."` (write tasks) — assert no array-typed fields at all.

## Programmatic validator (skeleton)
A minimal validator you can drop into the workspace. It assumes the standard JSON-Schema subset these templates use (object/array/string/number/integer with `required`, `additionalProperties`, `enum`, `pattern`, `minimum`, `maximum`, `multipleOf`, `minItems`, `maxItems`, `uniqueItems`).

```python
import json, re, sys

def check(answer, schema, path="root"):
    errs = []
    if schema.get("type") == "object":
        if not isinstance(answer, dict):
            return [f"{path}: expected object"]
        req = schema.get("required", [])
        for k in req:
            if k not in answer:
                errs.append(f"{path}: missing required '{k}'")
        if schema.get("additionalProperties") is False:
            allowed = set(schema.get("properties", {}).keys())
            for k in answer:
                if k not in allowed:
                    errs.append(f"{path}: extra property '{k}'")
        for k, sub in schema.get("properties", {}).items():
            if k in answer:
                errs += check(answer[k], sub, f"{path}.{k}")
    elif schema.get("type") == "array":
        if not isinstance(answer, list):
            return [f"{path}: expected array"]
        if "minItems" in schema and len(answer) < schema["minItems"]:
            errs.append(f"{path}: minItems {schema['minItems']}")
        if "maxItems" in schema and len(answer) > schema["maxItems"]:
            errs.append(f"{path}: maxItems {schema['maxItems']}")
        if schema.get("uniqueItems") and len(set(map(json.dumps, answer))) != len(answer):
            errs.append(f"{path}: not unique")
        for i, item in enumerate(answer):
            errs += check(item, schema.get("items", {}), f"{path}[{i}]")
    elif schema.get("type") == "integer":
        if isinstance(answer, bool) or not isinstance(answer, int):
            errs.append(f"{path}: expected integer")
    elif schema.get("type") == "number":
        if isinstance(answer, bool) or not isinstance(answer, (int, float)):
            errs.append(f"{path}: expected number")
    elif schema.get("type") == "string":
        if not isinstance(answer, str):
            errs.append(f"{path}: expected string")
    # constraints on scalars
    if isinstance(answer, (int, float)) and not isinstance(answer, bool):
        if "minimum" in schema and answer < schema["minimum"]:
            errs.append(f"{path}: below minimum {schema['minimum']}")
        if "maximum" in schema and answer > schema["maximum"]:
            errs.append(f"{path}: above maximum {schema['maximum']}")
        if "multipleOf" in schema:
            a = schema["multipleOf"]
            if abs(round(answer / a) * a - answer) > 1e-9:
                errs.append(f"{path}: not multipleOf {a}")
    if "enum" in schema and answer not in schema["enum"]:
        errs.append(f"{path}: '{answer}' not in enum {schema['enum']}")
    if "pattern" in schema and isinstance(answer, str):
        if not re.fullmatch(schema["pattern"], answer):
            errs.append(f"{path}: '{answer}' fails pattern {schema['pattern']}")
    return errs

if __name__ == "__main__":
    answer = json.load(open("answer.json"))
    template = json.load(open("input/payloads/answer_template.json"))
    errs = check(answer, template)
    if errs:
        print("\n".join(errs)); sys.exit(1)
    print("OK")
```

Note: some templates use `snake_case` keys and `camelCase` keys inconsistently across files. Match the **template's** key casing exactly; do not normalize.

## Ordering checks (semantic, beyond the validator)
The validator above checks structure. Order is semantic:
- After loading `answer.json`, re-assert each ordered array against its rule by recomputing the sort keys from the live data (or from the values already present where the rule depends only on them, e.g. ID ascending).
- For "top-N by metric desc, then id asc", re-derive the metric ordering from data whenever the metric is not carried in the output (e.g. `worst_warehouse_regions` carries its own rate, but `top_three_employee_ids` carries only IDs — re-derive UPH from the database to assert the order).

## Final
Run the validator; if it prints `OK` and your semantic ordering checks pass, and you've reconciled aggregates, `answer.json` is contract-conformant. If any check fails, fix the underlying query/value — do not patch the JSON to pass the checker without the data agreeing.
