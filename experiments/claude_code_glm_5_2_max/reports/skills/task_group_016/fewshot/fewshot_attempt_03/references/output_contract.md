# The Output Contract: obeying answer_template.json

`input/payloads/answer_template.json` is a strict schema. The evaluator checks
keys, enum membership, types, ordering, precision, and nullability. Work through
it methodically.

## Top level

- Emit exactly the keys in `required_top_level_keys` (plus only those the
  template says are ignored). Missing or extra top-level keys fail.
- Some templates name a `format` / `output_rules` / `output_type` key stating
  "single JSON object, no markdown/comments/extra keys" — honor it literally.

## Field types

- `enum` / `list[enum]` / `array` of `enum` items — value(s) must come from
  `allowed_values`. This is the most common failure mode: inventing a value not
  in the set. If no allowed value fits, choose the closest `no_*` / `defer_*` /
  `not_recommended` / `not_eligible` option rather than a free-form string.
- `string`, `integer`, `number` — match the scalar type.
- `string_or_null`, `integer_or_null`, `["string","null"]`, `nullable: true` —
  use `null` only where the spec permits; otherwise the typed value.
- `boolean` — literal `true`/`false`.
- `object` with `required_keys` — include every required sub-key.

## Required vs. conditional

- `expected_constant` / `required_value` — copy that literal exactly (common for
  `task_id` and `case_id`).
- `required_when: "lab_found is true"` — include the nested object only when the
  condition holds; otherwise use `null` (if nullable) or omit per the spec.

## Ordering

Read each list's `ordering` / `ordering_rule`:

- "No semantic ordering; normalized as a set" — order is irrelevant, but emit
  each value at most once (dedupe).
- "case identifier first, then clinical source identifiers" — `case_id` then
  evidence ids, in that leading position.
- "descending relevance" — most-decisive evidence first.
- "Sort by effective_time ascending, then observation_id ascending" — literal
  two-key sort.
- "Sort by clinical action sequence" — order the urgent actions in the sequence
  they would be performed.
- "Use each code at most once" — dedupe even if order is free.

## Precision and units

- One decimal place: lab values in mmol/L, HbA1c %, phosphorus mg/dL.
- Two decimals: probability / risk scores.
- Integers: counts, `timeframe_hours`, `duration_days`, `min_disciplines`,
  `oral_dose_mEq`.
- Units are descriptive; emit the raw number (or `integer`) unless the field is
  a formatted string (e.g. blood pressure `"systolic/diastolic"`).
- Timestamps: ISO-8601 UTC with trailing `Z`. Use `null` only where the field
  explicitly permits it (e.g. `scheduled_time` when no lab is scheduled).

## Null discipline

`null` is allowed only on fields whose type union includes null. Filling an
un-actioned medication plan? Use the strategy enum (e.g.
`supportive_care_no_antibiotic` / `defer_antibiotic_selection_to_ed`) and set
`medication`, `dose`, `route`, `frequency`, `duration_days` to `null` — but only
because each of those sub-fields is `*_or_null`. On fields that are plain
`string`/`integer`, never use `null`.

## Final self-check

Walk the template once more against your draft: every required key present? no
disallowed extra keys? every enum value in its allowed set? every type correct?
every list ordered per its rule? nulls only where permitted? numbers at the
right precision? Then strip everything but the JSON object.
