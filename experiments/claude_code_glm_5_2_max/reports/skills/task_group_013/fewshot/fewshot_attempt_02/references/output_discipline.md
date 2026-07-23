# Output Discipline — Assembly & Validation

The final answer is a single JSON object that conforms to the task's `answer_template.json`. These rules govern assembly and the pre-submission check.

## Keys

- Emit **every** required top-level key and every required item key, even when empty.
- Do **not** emit keys the template does not define. Extra keys fail conformance.
- For fields with `required_value` / `expected_value` / `constant` (e.g. `task_id`, `roster_id`, `batch_id`, `program_code`), reproduce the exact value from the template — do not recompute it.

## Controlled vocabulary

- Emit only strings that appear in the template's `allowed_values` for that field. Never invent tokens, never free-text.
- When the template lists `allowed_values`, the value must be one of them. Booleans use `true`/`false`; integers are bare numbers.

## Ordering

Sort every list exactly as the template's `ordering` specifies:

- "ascending by patient_id / referral_id / transfer_id / group_id / insurance_id" → ascending string sort of that id.
- "alphabetical by code / doc_type / artifact enum string" → ascending alphabetical.
- "ascending group_id" / "ascending referral_id then …" → sort by the named key(s).
- "unordered set" / "order is not meaningful" → still emit a deterministic order (ascending) for reproducibility.
- "highest priority first" / "rank from 1" → by priority, with `rank` 1..N.
- "urgency then readiness_status" → sort by urgency, then readiness_status.
- When a template specifies an ordering for a count-breakdown **list** (e.g. urgency×status), include only non-zero combinations unless the template says otherwise.

## Counts

- All counts are **integers** (bare JSON numbers, not strings).
- Include every key in the template's count-key set, even when the count is 0. Do not drop zero-valued keys.
- Reconcile: a status/risk/cadence count map's values sum to `total_patients` / `total_transfers` / `total_candidates` / `total_referrals` where the template implies a partition. `ready_to_schedule_count` + `follow_up_count` should match the referral total where applicable.
- `total_*` equals the length of the corresponding item list — verify by counting the list, not by assuming.

## Null and empty

- Use `null` where the template allows `enum_or_null` / `integer_or_null` and the value does not apply (e.g. `priority_tier` for a ready referral, `first_checkin_days` for a deferred/not-applicable package).
- Use `[]` for list fields with no members (e.g. `blocked_reason_codes` for an approved patient, `missing_required_documents` for a complete packet, `duplicate_groups` when none).
- Never omit a required key to represent "none"; use the template's `none` / `not_applicable` / `unknown` / `missing` token, or `null`/`[]` as the schema permits.

## IDs and dates

- IDs are uppercase, exactly as the portal returns them (patient ids `P###`, referral ids `REF####`, transfer ids `TR####`, insurance ids `INS-P###`). Do not reformat or re-case.
- Dates are `YYYY-MM-DD` strings.

## Final response

- Return the JSON object **only**: no prose, no explanation, no markdown code fence, no trailing commentary.
- The object must be valid JSON (parseable). Booleans and numbers are unquoted.

## Pre-submission validation checklist

Run this before returning. Each must hold:

1. **Top-level keys** — every required top-level key present; no extra keys.
2. **Item keys** — every required item key present on every item; no extra item keys.
3. **Constants** — every `required_value`/`expected_value`/`constant` field matches the template exactly.
4. **Controlled vocab** — every enum/string value is in the template's `allowed_values` (or required value) for that field.
5. **Ordering** — every list sorted per the template's `ordering` rule.
6. **Coverage** — the item list covers exactly the target entities the prompt names (every required patient/referral/transfer/candidate id present; no extras; no duplicates).
7. **Counts** — every count is an integer; every count-key present (including zeros); `total_*` equals the item list length; partition sums reconcile.
8. **Null/empty** — `null` used only where permitted; `[]` used for empty lists; required keys never omitted.
9. **Internal consistency** — e.g. `ready_to_schedule` equals the referrals with `readiness_status=ready`; `clinical_code_discrepancy_referrals` equals referrals whose blocker/issue set contains the code-discrepancy token; `blocked_reason_codes` includes `overall_risk_high` whenever `overall_risk=high`; duplicate-group `referral_ids` are also flagged `duplicate_referral`/`duplicate_review` in their reviews.
10. **Prose-free** — output is a single JSON object with no surrounding text.
