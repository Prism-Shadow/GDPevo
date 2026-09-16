# Answer Template Interpretation Guide

Answer templates (`answer_template.json`) define the exact JSON schema the solver must produce. Every task provides one. This reference covers how to read and conform to them.

## Template Structure

Templates have a consistent shape:

```json
{
  "required_top_level_keys": ["task_id", "case_id", ...],
  "fields": {
    "<field_name>": {
      "type": "<type_spec>",
      "allowed_values": [...],
      "required_keys": [...],
      "ordering": "...",
      ...
    }
  }
}
```

## Type System

| Type | Meaning | Behavior |
|------|---------|----------|
| `string` | Required string value | Always include; cannot be null |
| `enum` | Single value from `allowed_values` | Pick exactly one |
| `list[enum]` | Array of enum values | Each element from `allowed_values`; omit duplicates |
| `object` | Nested JSON object | Must include all `required_keys` |
| `boolean` | `true` or `false` | Never null |
| `integer` | Whole number | No decimal places |
| `number` | Numeric value | Match `precision` if specified |
| `string_or_null` | String or `null` | Use `null` when no value applies |
| `integer_or_null` | Integer or `null` | Use `null` when no value applies |
| `enum_or_null` | Single enum value or `null` | Use `null` when not applicable |

## Ordering Rules

Most list fields use set-based ordering (order not meaningful for scoring). Exceptions noted in the template:

- `evidence_ids`: "Stable order; case identifier first when included, then clinical source identifiers." Put the case_id first, then observation IDs, imaging IDs, and protocol IDs in a consistent order.
- `matched_observation_ids`: Sort by `effective_time` ascending, then `observation_id` ascending.
- `excluded_observation_ids`: Sort by `effective_time` ascending, then `observation_id` ascending.

## Output Discipline

- Return exactly one JSON object — no markdown fences, no explanatory prose, no comments.
- Do not add extra top-level keys beyond those listed in `required_top_level_keys`.
- Every string value must be from the allowed set when `allowed_values` is specified for enum/list fields.
- For `safety_checks` booleans: set to `true` when the unsupported finding is correctly absent from the data. These are guards that confirm you did not hallucinate a finding.
- For null-able fields: use `null` only where the field specification explicitly permits it.

## Common Field Patterns

**Evidence IDs**: Collect stable identifiers for every data source that informed the decision. Always include the case ID first. Then include observation IDs, imaging IDs, and protocol IDs used.

**Safety Checks**: Boolean fields named like `no_false_loc`, `no_penicillin_or_sulfa`, `no_normal_cxr_claim`. These verify that unsupported findings were not incorrectly asserted. Set to `true` to confirm the unsupported finding was correctly absent.

**Red Flags / Absent Red Flags**: Red flags report findings that ARE present. Absent red flags report findings from a protocol-specified list that are NOT present. Only include codes that are genuinely absent (verified by checking findings, observations, and case narrative).

**Numeric Anchors**: When extracting numeric values from findings or observations, match the template's precision exactly. For blood pressure, format as `"systolic/diastolic"`. For risk scores, use two decimal places. For lab values, use one decimal place.
