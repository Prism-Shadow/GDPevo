# Answer Template Format

Answer templates define the exact JSON schema that a clinical decision-support response must conform to. They are provided as `answer_template.json` in the task payloads.

## Structure

A template is a single JSON object with these top-level elements:

### Header fields

| Field | Description |
|-------|-------------|
| `template_name` | Human-readable label for the template (not always present). |
| `schema_name` | Alternative label for the schema (not always present). |
| `version` / `schema_version` | Template version string. |
| `required_top_level_keys` | Array of strings — every key the output object must contain. |
| `output_rule` / `output_rules` / `output_type` | Rules governing output format. Always: return exactly one JSON object, no markdown, no extra keys. |
| `format` | Often `"Return a single JSON object. Do not include markdown, comments, or extra top-level keys."` |

### Fields

The `fields` object maps each required key to its type specification. Each field spec can contain:

| Attribute | Description |
|-----------|-------------|
| `type` | `"string"`, `"number"`, `"integer"`, `"boolean"`, `"enum"`, `"object"`, `"array"`, `"list"`, `"list[enum]"`, `"list[string]"`, or a union like `["string", "null"]` or `["integer", "null"]`. |
| `enum` with `allowed_values` | The exhaustive set of allowed string values. **Never use a value outside this list.** |
| `required` | Whether the field is mandatory. |
| `description` | What the field represents. |

For object-typed fields, a nested `fields` or `properties` block specifies sub-keys. Nested objects may have their own `required_keys` list.

For array-typed fields, `items` (or `item_type`) defines the element type and its constraints.

### Ordering rules

Most list fields carry an ordering annotation like:

> "No semantic ordering is required; evaluators normalize this as a set."

This means the list order does not affect scoring — evaluators compare as unordered sets. For fields that DO require ordering (e.g., `evidence_ids` sometimes, or `matched_observation_ids` sorted by `effective_time` ascending), the template specifies the ordering rule explicitly.

### Numeric precision

Numeric fields define their precision inline or in a top-level `numeric_precision` block:

- `"precision": "one decimal place"` — the value must have exactly one digit after the decimal (e.g., `3.8`, not `3.80` or `3`)
- `"precision": "two decimal places"` — exactly two decimal digits (e.g., `0.85`)
- `"precision": "whole days"` / `"type": "integer"` — no decimal part (e.g., `7`, not `7.0`)
- `"unit"` — the unit annotation (e.g., `"mmol/L"`, `"mEq"`, `"hours"`, `"days"`, `"percent"`, `"mg/dL"`)

### Null handling

Fields that permit `null` declare it in their type as `["string", "null"]`, `["integer", "null"]`, or use `"nullable": true`. A field typed as `"string"` without a null alternative must never be null. Common null patterns:

- Medication fields (`medication`, `dose`, `ndc`) are null when no medication is recommended
- `latest_final` is null when `lab_found` is false
- `scheduled_time` is null when no follow-up lab is recommended

### Constant fields

Some templates include `required_value` or `expected_constant` on fields like `task_id` or `case_id`. These are fixed strings that must be echoed exactly in the output.

### Safety checks

Safety-check objects contain boolean fields typically named `no_*` or `no_false_*`. These are assertions:

- `true` = the unsafe finding or unsupported claim is **absent** (safe)
- `false` = the finding or claim **is present** (unsafe, or the claim is actually supported)

## Conformance rules

1. **Every required key must appear.** Missing a key from `required_top_level_keys` is a schema violation.
2. **No extra keys.** The output must not include keys beyond those the template defines at each level.
3. **Enum values must be from the allowed set.** Use only the strings in `allowed_values`. If no value perfectly matches the clinical picture, pick the closest one.
4. **Types must match.** A field typed as `"integer"` must be a JSON number with no fractional part. A field typed as `"string"` must be a JSON string.
5. **Nested required keys must be present.** If a nested object has a `required_keys` list, every key in that list must appear in the output object.
6. **Numeric precision must be honored.** Follow the `precision` and `unit` specifications.
7. **Null only where permitted.** Do not use `null` for fields typed as non-nullable.
8. **Output must be exactly one JSON object.** No markdown fences (` ```json `), no leading/trailing text, no comments, no explanatory prose.
