# Output contract — serialization rules

The `answer_template.json` is authoritative for the specific task; these are the conventions
that repeat across the family. Re-read the live template each run — keys, enums, and ordering
can differ from task to task.

## Global rules

- **JSON only.** Return exactly one JSON object, no markdown fences, comments, or prose.
- **Keys.** Include every `required_top_level_field` / `top_level_required_key`. When the
  template says `additional_fields_allowed: false` (or `additional_properties` is not
  allowed), emit no extra keys. When extras are "allowed but not evaluated," still prefer the
  minimal exact shape.
- **Enums.** Every enum-typed field (and every list-of-enum item) must be one of the template's
  listed `choices` — never a synonym or a raw environment status string.
- **Null vs empty.** Use `null` (not `""`, not `[]`) only where the template says a value may
  be absent (e.g. a missing modifier, a non-applicable deadline). Use `[]` for an empty list
  where the template expects a list.
- **Numbers.** Honor the stated precision: currency to two decimals (cents), ratios to the
  stated precision (e.g. 4). Apply units before rounding a line amount.
- **Dates.** ISO 8601 `YYYY-MM-DD`. Date math (appeal windows, effective-date containment)
  uses the payload's `reporting_date`/`request_date` as "today."

## Ordering rules seen in these templates

- Document id lists (`evidence_documents`, `excluded_documents`): ascending `document_id`.
- `approved_cpt` / CPT lists: ascending CPT/HCPCS code.
- Medication lists: alphabetical by lowercase medication name.
- Segment lists (`below_threshold_segments`, assistance `missing_fields`, etc.): alphabetical
  by enum/field value.
- Claim `lines`: source claim-line order (`line_number`).
- Finance `rows`: the exact order of `finance_memo.queue_row_ids`.
- `unresolved_criteria` / criterion-id lists: ascending criterion id.
- Packet items: operational order — payer-appeal items before assistance items; gap lists put
  appeal-evidence gaps before assistance-information gaps.

## `basis_audit` (identical block in every template)

Object with exactly four keys.

`source_precedence` — one enum value naming the governing rule, chosen by family:

| Family | `source_precedence` |
| --- | --- |
| UM nurse determination / prior auth | `current_clinical_records_over_stale_export` |
| Pharmacy appeal + assistance | `payer_appeal_before_manufacturer_assistance` |
| Payment-integrity repricing | `effective_benchmark_by_plan_modifier_and_date` |
| Peer-to-peer close-out | `new_patient_specific_p2p_information` |
| Finance margin queue | `margin_threshold_then_charge_sensitivity` |
| Appeal-deadline-driven triage | `appeal_deadline_then_clinical_then_payment_integrity` |

`controlling_record_ids` — the environment record ids that directly determine the result, in
operational evidence order (current documents / the effective benchmark id / the graded
criteria / the disposition record — authorization, appeal, p2p, or below-threshold rows).

`exception_record_ids` — the gap/exception records, in gap order: **criteria or route gaps
first, then stale or excluded records** (missing-evidence criteria, then stale/expired/
excluded document or schedule ids, charge-sensitive rows).

`precedence_record_order` — `controlling_record_ids` and `exception_record_ids` merged and
re-sorted by source-precedence priority, highest first.

Use only real ids returned by the environment; never fabricate an id.

## Pre-return checklist

1. All required keys present; no disallowed extras.
2. Every enum value is in the template's choice list.
3. Every list obeys its ordering rule.
4. Numbers at required precision; currency to cents; units applied before rounding.
5. `null`/`[]` used exactly where the template allows absence.
6. `basis_audit` has all four keys with real record ids and the correct `source_precedence`.
7. No `-TE-` / `-D-` distractor rows leaked into the answer.
