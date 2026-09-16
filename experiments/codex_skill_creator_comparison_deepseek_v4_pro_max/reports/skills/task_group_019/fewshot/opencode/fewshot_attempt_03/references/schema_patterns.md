# Schema Patterns

## How to Read an Answer Template

Every task provides `input/payloads/answer_template.json`. This file is the contract. Read it first, before making any data calls.

### What the template tells you

1. **Required top-level keys** — The template lists exactly which keys must appear in the output JSON. Do not add, remove, or rename keys.
2. **Enum `allowed_values`** — Every enum field has an explicit list of allowed strings. Only these strings may appear in the output. Match case, spelling, and underscores exactly.
3. **Ordering rules** — The template specifies how to sort arrays: ascending by application_id, ascending by code alphabetically, by date-then-ID, or in operational sequence. Follow these exactly.
4. **Required lengths** — For batch tasks, the template says how many items the array must contain (matching the target count from the prompt).
5. **Empty value conventions** — Templates consistently require `[]` for empty arrays of codes/IDs. Never use `null`, `"none"`, `"N/A"`, or omit the key.
6. **Type expectations** — Integers are integers, booleans are `true`/`false`, dates are strings in YYYY-MM-DD.

### Template variations across task families

**Contractor batch templates** have:
- `application_decisions` array — one object per target application
- `summary` object — aggregate counts and ID lists
- Per-application keys: `application_id`, `determination`, `deficiency_codes`, `required_actions`, `risk_tier`, `policy_impacted`

The deficiency codes and required action codes vary by template version. Always use the current task's template — never copy codes from another task.

**Liquor staff-package templates** have:
- Single application object (not an array)
- Top-level keys: `application_id`, `recommended_posture`, `same_premises_basis_applies`, `covered_risk_codes`, `verification_gap_codes`, `standard_obligation_codes`, `location_specific_control_codes`, `first_90_day_plan`, `escalation_trigger_codes`
- `first_90_day_plan` is an array of objects with `check_code` and `timing` keys
- Risk codes, gap codes, check codes, and trigger codes vary between template versions — always read the current template

**Alcohol renewal queue templates** have:
- `queue` array — exactly queue_size entries, ranked 1..N
- `summary` object — aggregate info
- Per-queue-entry keys: `rank`, `license_no`, `facility_name`, `violation_count`, `most_recent_violation_date`, `matched_violation_ids`, `match_confidence`, `risk_tier`, `next_step_label`
- Summary keys: `queue_size`, `boundary_date`, `post_boundary_violation_ids_excluded`, `close_or_uncertain_match_license_numbers`, `board_review_license_numbers`

## Enum Matching

When a template defines `allowed_values` for a field, those are the only strings you may use. Never:

- Invent a new code that seems appropriate
- Use a code from a different task's template
- Change case (e.g., `"noise"` when the template says `"NOISE"`)
- Change underscores or separators

If data from the API suggests a condition that has no matching code in the template, map it to the closest allowed code. If no reasonable mapping exists, note it as a gap — but do not invent a code.

## Output Construction Checklist

Before writing the final JSON, verify:

1. **Top-level keys** match the template exactly (name, count, order).
2. **Array lengths** match the requirement (target count for batch tasks, queue_size for renewal tasks).
3. **Enum values** are all from the template's `allowed_values` lists.
4. **Sort order** follows the template specification for every array.
5. **Empty arrays** use `[]`, not null.
6. **Integers** are numbers, not strings.
7. **Booleans** are `true`/`false`, not `"true"`/`"false"`.
8. **Dates** are YYYY-MM-DD strings.
9. **No extra keys** beyond what the template defines.
10. **No markdown fences** around the JSON output unless the prompt explicitly asks for a wrapped format.

## Sorting Rules Summary

| Context | Sort Rule |
|---------|-----------|
| `application_decisions` array | By `application_id` ascending |
| `deficiency_codes` within an application | Alphabetically/lexically ascending |
| `required_actions` within an application | Alphabetically/lexically ascending |
| `matched_violation_ids` in renewal | By violation date ascending, then violation_id ascending |
| `covered_risk_codes`, `verification_gap_codes`, etc. | Ascending by code, remove duplicates |
| `first_90_day_plan` | In operational sequence (template-specific) |
| `high_risk_application_ids` | By application_id ascending |
| `policy_impacted_application_ids` | By application_id ascending |
| `stale_or_unverified_correspondence_ids` | By correspondence_id ascending |
| `post_boundary_violation_ids_excluded` | By violation_id ascending |
| `close_or_uncertain_match_license_numbers` | By license number ascending |
| `board_review_license_numbers` | By license number ascending |
| Renewal `queue` entries | By rank ascending (1..N) |
