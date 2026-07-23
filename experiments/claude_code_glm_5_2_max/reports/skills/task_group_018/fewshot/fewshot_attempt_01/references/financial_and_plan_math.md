# Financial and Payment-Plan Math

Exact arithmetic for the numbers a closeout package must produce. Compute every value; never copy a batch/worksheet total, which usually still contains stale or unsupported lines.

## Currency and precision
- All money values are numbers in USD, rounded to **two decimals** (e.g. `150.00`, `0.00`).
- Use `0.00` for excluded/empty/zero amounts — not `0`, not `null` (unless the template explicitly allows `null` on a money field, which is rare).
- Compute with full precision, round only the final emitted value. Prefer amounts that already terminate at two decimals (the schedules and plans do).

## Amount due at disposition

```
amount_due = supported_fine
           + supported_court_cost
           + supported_assessment(drug/crime-lab, if CS conviction)
           + supported_public_defender_user_fee (if PD and not waived; exclude if appointed-private/retained)
           + supported_county_surcharge (if any)
```

- Each term must come from the current fee schedule effective on the disposition date, or from a signed order. Terms with no support contribute `0.00` and are listed in the exclusion section with a reason code.
- `unsupported_charge_total_included` = sum of any unsupported amounts you *kept* in the balance. Correct reconciliation keeps this at `0.00` (everything stale/unsupported is excluded, not retained).
- `total_due` / `case_total` / `grand_total` = sum of the supported items for that scope.

## Register / batch totals
- Sum **only posted matters**. Held/excluded matters contribute zero to every total.
- `assessed_case_count` / `disposed_case_count` = matters posted. `held_case_count` / `excluded_pending_count` = matters held/excluded. Their sum = total target matters.
- Each fee-code total (fine_total, court_cost_total, assessment_total, user_fee_total, crime_lab_fee_total) = sum of that fee code across posted cases only.
- `grand_total` / `batch_total_due` = sum of all posted case totals. Recompute from items; do not trust the worksheet's `queued_total`.

## Payment-plan installment math (monthly interval)

Given corrected `amount_due`, approved `monthly_payment` M, `first_due_date`, and a candidate/approved `return_to_court_date`:

```
full_payment_count  = floor(amount_due / M)        # whole installments of size M
remainder           = amount_due - full_payment_count * M
if remainder > 0:
    final_payment_amount = remainder                # a smaller last installment
    total_installments    = full_payment_count + 1
else:
    final_payment_amount = M                        # ends evenly
    total_installments    = full_payment_count
```

- `down_payment` = policy/approved down payment, often `0.00`. If a down payment is paid, subtract it from `amount_due` before computing installments.
- `first_due_date` = the approved/policy first due date (policy `first_due_days` after disposition, or the petition's candidate date, mapping to the policy's usual "15th of next month" convention when the notes say so).
- `final_due_date` = the date of the last installment. For a monthly interval, advance from `first_due_date` by `(total_installments - 1)` calendar months (same day-of-month; the last installment date is the final one).
- `return_to_court_date` = the candidate return date given in the materials, or disposition date + `return_to_court_offset_days` from policy. `return_to_court_trigger` = `nonpayment` (or the trigger the policy names). `return_to_court_time` = policy/court standing time if given (e.g. `09:00`).

Worked shape (illustrative, not task values): amount_due = A, M = approved monthly.
- full = ⌊A/M⌋, remainder = A − full·M.
- If remainder>0: total = full+1, final payment = remainder.
- If remainder=0: total = full, final payment = M.
- final_due_date = first_due_date advanced by (total−1) months.

## Deferred / single-installment plans
For a deferred-payment classification (one due date, no monthly stream), set `interval` to the schema's deferred token (e.g. `deferred_single_due`) and a single installment: `total_installments = 1`, `regular_installment_amount` / `final_payment_amount` = the full amount due, `first_due_date == final_due_date`.

## Budget support classification

From the petition/budget payload: `monthly_income`, `monthly_obligations` (sum of rent/utilities/food/transportation/medical/etc.), `monthly_disposable_income = monthly_income − monthly_obligations`, and the policy band `[min_monthly, max_monthly]`.

Classify the **approved monthly amount** M:
- Within `[min_monthly, max_monthly]` **and** M ≤ disposable income → `supported` / `supported_by_budget` / `supportable`.
- M < `min_monthly` → `below_policy_minimum`.
- M > `max_monthly` → `above_policy_maximum`.
- M > disposable income (can't afford even though within band) → `unsupported_by_budget` / `needs_judge_review`.
- Record `selected_installment_amount` = M and the policy band.

## Payment application order (when restitution exists)
- No restitution → `fines_costs_only`.
- Restitution present + petitioner requests restitution-first **and** policy permits → `restitution_before_fines_costs`.
- Otherwise follow the policy's restitution-priority field (`restitution_before_fines_costs` or `fines_costs_before_restitution`).
- Restitution balance is part of `total_due` (= restitution + fines_and_costs) when it has an order; a restitution line with no order is excluded.

## Due-date advancement note
"All money" advances month-by-month on the same day-of-month. When the same day-of-month doesn't exist in the target month (e.g. the 31st in a 30-day month), this environment's calendars are arranged so the standard same-day cadence is intended — advance to the same numeric day and keep the day-of-month the source notes used (e.g. the 15th stays the 15th). Do not add stray extra months; the installment count formula above fixes the total, and `final_due_date` is exactly `first_due_date + (total_installments − 1)` months.
