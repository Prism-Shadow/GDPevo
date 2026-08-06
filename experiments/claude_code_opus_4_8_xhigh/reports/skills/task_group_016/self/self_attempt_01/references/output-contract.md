# Output contract — pre-submit checklist

The response is machine-graded against `answer_template.json`. Verify every item
before emitting.

## Structure
- [ ] Output is **exactly one JSON object** — no markdown, no code fences, no prose
      before or after, no comments.
- [ ] All `required_top_level_keys` are present.
- [ ] **No extra top-level keys** beyond what the template lists (some templates
      ignore extras, but do not rely on it).
- [ ] Nested objects contain exactly their `required_keys`.

## Types & values
- [ ] Every `enum` value is drawn from that field's `allowed_values` (exact string).
- [ ] Lists use each allowed code at most once; use `[]` (not `null`) for
      "nothing applies", unless the field is explicitly nullable.
- [ ] `null` appears **only** where the spec permits (`*_or_null`, `["string",
      "null"]`, `nullable: true`).
- [ ] Booleans are real JSON booleans; integers are integers, numbers are numbers.

## Numbers, units, time
- [ ] Numeric precision matches the spec (e.g. one decimal place for mmol/L,
      two for a probability risk_score, whole hours/days for integers).
- [ ] Units are as specified; do not append unit strings to numeric fields.
- [ ] Timestamps are ISO-8601 UTC with a trailing `Z`.
- [ ] `current_time` / review time comes from the case `findings`, not the wall
      clock; scheduled/follow-up times are computed relative to it per protocol.

## Ordering
- [ ] Fields whose template says "normalized as a set" / "order not meaningful" may
      be any order but must be deduplicated.
- [ ] Fields with an explicit sort (e.g. `effective_time` asc then `observation_id`
      asc; "case id first then sources"; "descending relevance") follow it exactly.

## Content integrity
- [ ] `case_id` / `task_id` match the template's `required_value` /
      `expected_constant` when present.
- [ ] `patient_id` is the real id from the case record (not a distractor
      `PAT-D20xx`).
- [ ] All scored fields trace to filtered `final` evidence + the live protocol body;
      no invented thresholds or unshown findings.
- [ ] `evidence_ids` contains only ids you actually used, in the required order.
- [ ] Safety-check / provenance booleans truthfully describe the emitted answer
      (compliance = `true`).
