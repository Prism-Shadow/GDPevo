# Output Contract Checklist

Run this against `answer_template.json` before returning any result. The template is the law; the evaluator checks the object against it.

## Required keys
- [ ] Every key in `required_top_level_keys` / `required_keys` is present.
- [ ] No extra top-level keys (unless the template explicitly says extras are ignored).
- [ ] No nested required key is missing.

## Expected constants
- [ ] Fields with `expected_constant` / `required_value` echo that value exactly (e.g. task id, case id).

## Enums
- [ ] Every enum field's value is drawn from its `allowed_values` list — no paraphrasing, no inventing.
- [ ] Null-tolerant enums (`enum_or_null`) use `null` or an allowed value, nothing else.

## Null rules
- [ ] `*_or_null` / nullable fields are `null` exactly when not applicable, and a real value otherwise.
- [ ] `null` is never used where a real value is required, and a placeholder string is never used where `null` is expected.

## Numeric precision & units
- [ ] Each numeric field is at the stated precision (e.g. one decimal place, two decimals, integer, whole hours).
- [ ] ISO-8601 timestamps use the stated format (UTC with trailing `Z` where required).
- [ ] Formatted strings (e.g. `systolic/diastolic`) follow the stated format.

## Lists
- [ ] Set-like lists: no duplicates.
- [ ] Ordered lists: sorted per their ordering rule (e.g. ascending `effective_time` then `observation_id`; or descending relevance; or case-id-first stable order).
- [ ] Empty lists used where the template says (e.g. no stabilization actions) — not padded with low-acuity items.

## Evidence & provenance
- [ ] `evidence_ids` contain only real identifiers returned by the runtime.
- [ ] Provenance/source-group keys drawn from the template's enumerated sets; chart-facts vs member-disclosure kept distinct as the template requires.

## Safety checks (truthful, not defaulted)
- [ ] Each "no false X" / "no Y claim" boolean matches the rest of the object: `true` only if the answer does not assert the forbidden thing; `false` if it does.
- [ ] Allergy/contraindication checks reflect the actual `allergies`/contraindication screen.

## Output shape
- [ ] Exactly one JSON object.
- [ ] No markdown, no code fences, no comments, no prose, no trailing text.
- [ ] Recomputed from the live runtime + protocol for this case — no task-specific values imported from any other task.
