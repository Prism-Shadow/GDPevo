# Reading answer_template.json

Every clinic protocol task includes an `input/payloads/answer_template.json`
that defines the exact output contract. The template is the definitive authority
on output shape — read it before any API call.

## Top-level structure

Templates always declare:

- **required_top_level_keys** — array of key names that must exist in your output.
  Missing a key will fail evaluation.
- **output_rules** or a note about extra keys — many templates explicitly forbid
  extra top-level keys beyond those listed.

## Field specification patterns

Each required key gets a field definition. Common type declarations:

| Type declaration | JSON type to produce |
|---|---|
| `"string"` | String |
| `"integer"` | Integer (whole number) |
| `"number"` | Float/decimal |
| `"boolean"` | `true` or `false` |
| `"object"` | Nested JSON object |
| `"list"` or `"array"` | JSON array |
| `["string", "null"]` | String or null — null only when no value applies |
| `["integer", "null"]` | Integer or null |

### Enum fields

Fields with `type: "enum"` come with an `allowed_values` array. Every string
value in your output must be an exact member of this list. Never invent new enum
values, paraphrase existing ones, or change casing.

Nested enum fields may declare `type: "enum_or_null"` — these accept null when
the clinical situation makes the field inapplicable.

### List fields

List fields have an `items` sub-specification with their own `allowed_values`.
Each item must be from that allowed set. Key rules:

- Each value appears at most once (no duplicates).
- Include only values the clinical data supports; empty lists (`[]`) are fine
  when nothing applies.
- Ordering rules are explicit: "no semantic ordering" means any order is
  accepted; "sort ascending" means sort by the stated axis.

### Object fields

Objects declare `required_keys` and nested `fields`. Every required key must
appear. Each nested field follows the same type rules as top-level fields.

### Numeric precision

Some templates include a `numeric_precision` section. Follow it exactly:

- "one decimal place" — always use one decimal (e.g. `3.2`, not `3.20`)
- "two decimal places" — always use two decimals (e.g. `0.84`)
- "whole days" — integer only
- "whole hours" — integer only

### Constant fields

Fields with `required_value` or `expected_constant` must be set to the exact
string specified — they identify the task rather than varying per case.

## Null handling

Null is meaningful only when the schema permits it. Conventions:

- Medication name, dose, frequency, NDC → null when no medication is recommended
- Follow-up lab `scheduled_time` → null when no follow-up lab is needed
- Numeric fields (like eGFR) → null only when explicitly nullable
- Stabilization actions → `[]` (empty list), never null
- Lists → `[]`, never null

## Verification checklist

Before finalizing output, confirm:

1. Every required_top_level_key is present
2. No extra top-level keys beyond the template definition
3. Every string value appears exactly in the corresponding `allowed_values`
4. Every nested object contains all `required_keys`
5. Null appears only in explicitly nullable fields
6. Numbers match the stated precision
7. List items are unique (no duplicates)
8. Timestamps use ISO-8601 UTC with trailing `Z`
9. No markdown fences, commentary, or trailing text — raw JSON only
