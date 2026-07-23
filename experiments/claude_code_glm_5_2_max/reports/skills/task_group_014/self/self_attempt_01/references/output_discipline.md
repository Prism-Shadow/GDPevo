# Output Discipline

The answer is **one JSON object**. Nothing else is acceptable: no markdown fences, no leading/trailing prose, no comments, no arrays wrapping the object, no "here is the answer:" preamble.

## Match the template exactly

- Open `input/payloads/answer_template.json`. It is the contract.
- Emit every key in `required_top_level_fields` / `top_level_required_keys` / `required_top_level_keys` (template phrasing varies). Omit none.
- Most templates set `additional_fields_allowed: false` (or "additional_properties": not allowed). Do **not** add extra fields. If a template says additional properties are allowed but not evaluated, still avoid extras.
- Use the template's exact key names (snake_case as written).

## Enum fields

Every enum field lists its allowed `choices`. Pick exactly one value from that list. Common enum vocabularies:
- recommendation: `approve`, `pend_for_information`, `escalate_to_md`, `deny`, `partial_approval`
- final_status: `approved`, `pended`, `md_review_required`, `denied`, `partially_approved`, `appeal_overturned`, `appeal_upheld`
- criterion result: `met`, `not_met`, `unclear`, `not_applicable` (some templates add `partial`)
- disposition (claim lines): `correct_upward`, `correct_downward`, `no_change`, `deny_line`

If the evidence supports a value not in the enum, choose the closest allowed value and let `basis_audit.exception_record_ids` carry the nuance — never invent an enum value.

## Ordering rules (per template)

- `evidence_documents`, `excluded_documents`: ascending `document_id`.
- `approved_cpt`: ascending CPT code.
- `lines` (claim repricing): claim-line order — ascending `line_number` from the source claim.
- `rows` (margin queue): **the exact order of `task_context.finance_memo.queue_row_ids`** — do not re-sort.
- `unresolved_criteria`: ascending criterion ID.
- `below_threshold_segments`, `charge_sensitive_segments`, `documented_failures`, `undocumented_or_insufficient_failures`, `assistance.missing_fields`: alphabetical by value/id, unless the template says otherwise.
- `missing_pet_factors`: the order shown in the template's `choices`.
- `required_packet_items`: "payer appeal items before assistance items" (operational packet order).
- `missing_packet_items`: "appeal evidence gaps before assistance information gaps".
- `basis_audit` lists: see `references/basis_audit.md` (operational evidence order; gap-before-stale order; precedence order).

## Null handling

- Use JSON `null` for an absent modifier on a claim line — **not** an empty string.
- Use `null` for `internal_appeal_deadline` when no deadline applies.
- Do not use `null` for a required enum or a required date that does apply — derive the real value.

## Numeric precision

- Currency: USD, rounded to **2 decimals** (`paid_amount`, `correct_allowed_amount`, `recovery_amount`, `paid_total`, `correct_allowed_total`, `margin`, `total_cost`, `gap_to_120pct`). Use JSON numbers, not strings.
- Ratios: rounded to **4 decimals** (`revenue_to_cost_ratio`, `threshold_revenue_to_cost_ratio`).
- Units: integers (`approved_units`, `units`, `requested_units`).
- Rounding direction: standard round-half-up to the stated precision. Apply units before rounding line amounts (`correct_allowed_amount` = benchmark `allowed_amount` × `units`, then round).
- `recovery_amount` sign: positive when the corrected allowed is greater than paid (underpayment / `correct_upward`); negative when overpaid (`correct_downward`). The total `recovery_amount` is the sum of line recovery amounts (or the underpayment amount when corrected > paid, per template).

## Dates

- Calendar dates: ISO 8601 `YYYY-MM-DD`.
- Periods: `YYYY-MM`.
- Deadline math: add the plan's internal appeal window (in days, from the task memo) to the final adverse determination date; keep the result in `YYYY-MM-DD`.

## Final self-check before emitting

1. Every required top-level key present? Extra fields removed?
2. Every enum value drawn from the template's choices?
3. Every list ordered per the template's stated ordering rule?
4. Modifiers / inapplicable deadlines are `null`, not `""`?
5. Currency → 2 dp, ratios → 4 dp, units integer?
6. `basis_audit` has all four keys with the domain-correct `source_precedence`?
7. Output is a bare JSON object — no prose, no fences?
