# Schema Conformance Checklist

Run this against your draft JSON before returning it. The `answer_template.json` for the task is the source of truth; this checklist generalizes the rules that recur across templates.

## Top level
- [ ] Object contains exactly the `required_top_level_keys` — no more, no less (unless the template explicitly says extra keys are ignored; even then, prefer exact).
- [ ] `task_id` and `case_id` match the template's `expected_constant` / `required_value` when one is given; otherwise use the task's `task_id` and the prompt's `case_id` verbatim.
- [ ] `patient_id` is the stable identifier fetched from the runtime (from the case record), not invented.

## Enums and constants
- [ ] Every enum field's value is one of its listed `allowed_values`.
- [ ] Every `required_value` / `expected_constant` matches verbatim (case, punctuation, underscores).
- [ ] No prose where an enum is required (e.g. risk level, disposition, plan, gate).

## Lists
- [ ] Each list's ordering follows THAT template's rule:
  - "set" / "no semantic ordering" → order doesn't matter, but omit duplicates.
  - "stable order, case identifier first" → case id first, then clinical source ids.
  - "descending relevance" → most relevant evidence first.
  - "sort by effective_time ascending, then observation_id ascending" → literal sort.
- [ ] Each selected code appears at most once where the template says so.
- [ ] Empty list used (not omitted, not null) when nothing applies and the field is required.

## Objects / nested
- [ ] Nested objects contain their `required_keys`.
- [ ] Nullable sub-objects (e.g. `latest_final`) are present and populated when the guard condition holds (`required_when`), else null/absent per the spec.

## Nulls
- [ ] `null` used only where the spec permits (`string_or_null`, `integer_or_null`, `enum_or_null`, nullable objects, `"type": ["string","null"]`).
- [ ] No null where a value is required.

## Numeric precision
- [ ] mmol/L values → one decimal place.
- [ ] HbA1c (percent), phosphorus (mg/dL) → one decimal place.
- [ ] Probability risk score → two decimal places.
- [ ] `timeframe_hours`, `duration_days`, counts, eGFR → whole integers.
- [ ] Units implied by field name; do not append units into the value.

## Timestamps
- [ ] ISO-8601 UTC with trailing `Z` wherever a timestamp is required (`current_time`, `effective_time`, `scheduled_time`, window `from`/`to`).
- [ ] Window `from` is inclusive, `to` is exclusive (per observation-window templates).

## Safety checks
- [ ] Every required safety-check boolean is present.
- [ ] Each boolean is true-to-evidence: a `no_false_*` / `no_*_claim` check is `true` only if the answer makes no such unsupported claim; `false` if it does. When in doubt, fix the claim rather than the boolean.

## Output shape
- [ ] Exactly one JSON object.
- [ ] No markdown fences, no comments, no trailing prose, no explanatory text outside the object.
- [ ] Valid JSON (trailing commas, quoting, brackets all clean).
