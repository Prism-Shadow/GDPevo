# Fee Resolution

## Overview

Fee resolution matches case-level financial obligations to the active fee
schedule for the jurisdiction. The portal `/api/fee-schedules` endpoint
returns all records for a jurisdiction, including stale/archived ones.
Only active records apply.

## Determining which fees apply

### Step 1: Query the fee schedule

Call `/api/fee-schedules?jurisdiction_code=<CODE>`. Parse every record.

### Step 2: Filter by date

A fee record is active for a case with disposition_date D if and only if:

```
record.effective_date <= D AND (record.end_date IS NULL OR record.end_date > D)
```

Discard any record whose end_date has passed. These are stale/historical
records kept only for audit reference.

### Step 3: Match by fee type and case facts

| fee_type | Applies when |
|---|---|
| `court_cost` | Always for a criminal conviction. Post once per case. |
| `standard_fine` | Traffic violation. Match by `violation_code`. |
| `county_surcharge` | Traffic violation. Post once per citation. |
| `assessment` | Conviction triggers the assessment (drug assessment -> controlled substance; lab fee -> controlled substance). |
| `user_fee` | Public Defender User Fee. Post only when counsel_type is `public_defender`. |
| `account_fee` | Post only when the payment policy for this jurisdiction has a non-zero `account_fee`. |
| `miscellaneous` | Copy/certification fees. Do NOT post unless the hearing order explicitly orders them. |
| `stale_local_fee` | Never post. These are archival records only. |

### Step 4: Handle stale amounts

If a local worksheet or finance queue quotes an amount that matches a stale
(end_date < disposition_date) fee record, do not use that amount. Find the
active record for the same fee_type/jurisdiction and use its amount instead.

Record this correction as a fee_schedule audit finding. In the audit finding:
- `conflicted_value` describes what the local source had
- `corrected_value` describes the active-schedule amount
- `resolution_source` is `use_fee_schedule`

### Step 5: Handle missing fees

If the hearing notes or statute require a fee (e.g., judge says "do not forget
the lab assessment on the controlled-substance conviction") but the local
worksheet omitted it, add it from the active schedule. Flag as
`lab_fee_worksheet_omitted` or the nearest appropriate audit flag.

### Step 6: Assemble fee items

For each case being posted to the register, list every applicable fee:

- `fine`: from the hearing notes fine amount or portal charge fine_amount
- `court_cost`: from the active fee schedule
- `assessment` (e.g. `drug_assessment`, `crime_lab_fee`): from the active schedule
- `user_fee` (e.g. `public_defender_user_fee`): from the active schedule, only when counsel is public defender

Case total = sum of all posted fee items.

## Unsupported and excluded charges

Every fee or charge that appears in local materials but is NOT supported by
the active portal fee schedule or hearing order must be explicitly listed as
excluded. Common examples:

| Charge | Reason to exclude |
|---|---|
| Stale standard fine (old SOF table) | `stale_schedule` |
| Statutory maximum substitution | `unsupported_post_disposition` (use the active schedule fine, not the statutory maximum) |
| Account management fee | `not_current_policy` (when policy account_fee is 0) |
| Late payment fee, collection fee, DMV fee | `no_triggering_event` (no late payment, default, or referral has occurred) |
| Traffic school fee | `not_in_hearing_order` |
| Restitution | `no_order_or_policy_support` (when no restitution order exists) |
| Court-appointed attorney fee, court reporter fee | `no_order_or_policy_support` |
| DMV reinstatement fee | `not_part_of_balance` |

The `excluded_charges` or `excluded_financial_items` section in the answer
template governs the exact format.

## Payment policy and installment math

When the answer requires a payment schedule, use the payment policy from
`/api/payment-policies` for the jurisdiction.

### First due date

```
first_due_date = disposition_date + policy.first_due_days
```

If local materials provide a specific candidate date (e.g., from a petition),
use it if it aligns with the policy. If the policy says "15th of the next
month after disposition," compute the 15th of the month following the
disposition month.

### Installment math

Given total_due T and monthly installment M:

```
full_payment_count = floor(T / M)
final_payment_amount = T - (full_payment_count * M)
total_installments = full_payment_count + (1 if final_payment_amount > 0 else 0)
final_due_date = first_due_date + (total_installments - 1) months
```

When final_payment_amount is 0, the last full payment is the final payment.
Adjust total_installments accordingly.

### Return-to-court date

```
return_to_court_date = final_due_date + policy.return_to_court_offset_days
```

## Budget review

When a petition includes income and obligation data:

1. `monthly_disposable_income = monthly_income - total_monthly_obligations`
2. Compare the requested monthly amount against:
   - `policy.min_monthly` (floor)
   - `policy.max_monthly` (ceiling)
   - `monthly_disposable_income` (affordability)

Classification rules:
- Request within [min_monthly, max_monthly] AND <= disposable_income -> `supported_by_budget` / `supportable`
- Request > max_monthly -> `above_policy_maximum`
- Request < min_monthly -> `below_policy_minimum`
- Request > disposable_income -> `unsupported_by_budget` / `needs_judge_review`

## Restitution priority

When the payment policy says "Restitution before fines and costs":
- `payment_application_order` is `restitution_before_fines_costs`
- The total_due includes restitution_balance + fines_costs_balance
- Payments apply to restitution first

When the policy says "Not applicable" or there is no restitution:
- `payment_application_order` is `fines_costs_only` or `fines_costs_before_restitution`
- total_due = fines_costs_balance only

## Account fee treatment

Check policy.account_fee:
- 0.0 -> `excluded_by_policy`. Set account_fee_amount to 0.00, do not include
  in total_due.
- > 0.0 -> `included_by_policy`. Add to total_due.

Counter worksheets may carry old account-fee notes. Always override with the
policy value.

## Fee amount zeroing

For cases excluded from the register (pending, no final order, continued):
- Set all fee amounts to 0.00
- Set total_due to 0.00
- Set fee_status to `do_not_post_pending` or the template equivalent
