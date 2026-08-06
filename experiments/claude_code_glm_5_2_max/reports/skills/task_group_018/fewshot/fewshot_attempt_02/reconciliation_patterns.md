# Closeout Reconciliation Patterns Reference

This file catalogs the recurring reconciliation patterns observed across court closeout tasks. Use it as a decision guide when resolving conflicts between local materials and portal records.

## Conflict Resolution Hierarchy

When sources disagree, resolve in this priority order (highest wins):

1. **Signed court order** — a judgment, sentencing order, or disposition order that has been signed by the judge.
2. **Hearing notes / bench notes** — the judge's stated intent on the record, as recorded by the courtroom clerk.
3. **Audit / corroboration memo** — a post-hearing memo that identifies known errors in the finance queue.
4. **Portal / CMS data** — the Court Operations Portal record (cases, charges, fee schedules, payment policies).
5. **Finance queue extract** — the financial import batch, known to carry stale or draft values.
6. **Draft worksheets** — the lowest-priority source; these often contain preliminary figures not yet approved.

## Counsel Classification Rules

| Local label | Resolution | Fee impact |
|---|---|---|
| "PD" or "Public Defender" + matching portal record | `public_defender` | PD user fee may apply |
| "PD" but hearing notes/corroboration say appointed private | `appointed_private` | No PD user fee |
| "RET" or "Retained" | `retained` | No PD user fee |
| "APD" on calendar, but judge clarified appointed private | `appointed_private` | No PD user fee |
| Unknown / not stated | Verify via portal before classifying | Hold PD user fee until resolved |

## Identity Reconciliation

- **Name spelling**: CMS/portal spelling controls unless the hearing notes record a bench correction.
- **DOB**: Portal DOB overrides finance-queue DOB. If DOB is genuinely missing from all sources, use `"TBD from case file"` and set identity_action to `use_placeholder_verify` or `verify_before_entry`.
- **Never borrow** a DOB from a similarly named defendant in a different case.

## Fee Schedule Reconciliation

- Finance queue amounts labeled "archived," "old," or referencing a prior year are **stale**. Replace with the current portal fee schedule amount for the same fee code and jurisdiction.
- When the audit memo flags a fee schedule issue, query `GET /api/fee-schedules` with the current jurisdiction and year to get the authoritative amount.
- Drug/crime lab assessment amounts are particularly prone to stale-Year carry-forward; always verify against the current schedule for the disposition year.

## Departure Status Rules

- A draft sentence worksheet may label a sentence as a "departures" (durational or dispositional) before the judge has ruled.
- If hearing notes state the judge called it "top of the range" or "no separate departure finding," the departure status is `no_departure` or `none`.
- Misdemeanor convictions typically use `not_evaluated_misdemeanor` or `not_applicable` unless a departure was explicitly entered.
- Pending/continued cases use `not_entered_pending` or `not_applicable`.

## Held / Deferred / Excluded Case Rules

A case must be held or excluded from the disposed register when **any** of these conditions is true:

1. The judge did **not** sign the sentencing/disposition order.
2. The matter was **continued** for status or further proceedings.
3. No plea was accepted or no sentence was pronounced.
4. A required verification (identity, counsel, fee) is incomplete and the template requires holding.

For held/excluded cases:

- Set case status to `deferred`, `pending`, or `pending_exclude`.
- Set fee status to `hold` or `do_not_post_pending`.
- Set all financial amounts to zero.
- Record the next status check date if known (e.g., the continued-to hearing date).
- Set `financial_posting_allowed` to `false`.

## Payment Plan Arithmetic

Given: total_due, installment_amount, first_due_date, policy_return_to_court_offset_months.

```
full_installment_count = floor(total_due / installment_amount)
remainder = total_due - (full_installment_count × installment_amount)
if remainder > 0:
    final_payment_amount = remainder
    total_installments = full_installment_count + 1
else:
    final_payment_amount = installment_amount
    total_installments = full_installment_count
final_due_date = first_due_date + (total_installments - 1) months
return_to_court_date = final_due_date + return_to_court_offset_months
```

Validate: `full_installment_count × installment_amount + final_payment_amount == total_due`.

## Placeholder Protocol

When a form field is required but the value is unknown from all available sources:

- Value: `"TBD from case file"` (exact string; do not vary).
- Catalog in the answer's placeholder section with:
  - `field`: dot-path to the field (e.g., `cc1379.driver_license_number`, `defendant.ssn`).
  - `value`: `"TBD from case file"`.
  - `reason_code`: one of `missing_identifier`, `missing_contact`, `missing_office_detail`, `missing_party_detail` (or as defined by the answer template enums).
- Sort placeholders by field name ascending.

## Excluded Financial Items

Items that commonly appear in local worksheets but must be excluded unless supported by an explicit order or current policy:

| Item | Typical reason for exclusion |
|---|---|
| Restitution | `no_order_or_policy_support` — no restitution order in the sentencing intake |
| Account-management / maintenance fee | `no_order_or_policy_support` or `not_current_policy` — not automatic in current policy |
| Late payment fee | `no_triggering_event` — no default or late event occurred |
| Collection/referral fee | `no_triggering_event` — no collection referral made |
| DMV notice / reinstatement fee | `no_triggering_event` or `not_part_of_balance` — no DMV trigger or not a balance component |
| Court-appointed attorney fee | `no_order_or_policy_support` — no order supports it |
| Court reporter fee | `no_order_or_policy_support` — not ordered |
| Traffic school fee | `not_in_hearing_order` — no traffic school directive |
| Stale standard fine amount | `stale_schedule` — replaced by current fee schedule |
| Statutory maximum substitution | `unsupported_post_disposition` — not the applicable fine amount |
| Payment-plan service charge | `not_current_policy` — obsolete footer reference not in current form revision |

## Register / Batch Totals

- Total each fee category across **disposed/assessed cases only** (exclude held cases).
- Grand total = sum of all individual fee amounts across assessed cases.
- Count: separate disposed vs. held/excluded counts.
- Verify: `grand_total == sum of all case_total values in fee_entries where fee_status allows posting`.
