# Payment Plan Installment Arithmetic

When the answer template requires payment schedule fields (total_installments,
full_payment_count, final_payment_amount, final_due_date, return_to_court_date),
compute them using these formulas.

## Core Arithmetic

Given:
- total_due — the total balance to be paid through installments
- monthly_payment — the approved monthly installment amount
- down_payment — any upfront down payment (0.00 if none)
- first_due_date — the first payment due date
- payment_interval — monthly, biweekly, or weekly

Compute:

1. **remaining_after_down** = total_due - down_payment

2. **full_payment_count** = floor(remaining_after_down / monthly_payment)
   — the number of full installment payments at the full monthly amount.

3. **final_payment_amount** = remaining_after_down - (full_payment_count ×
   monthly_payment) — the remainder. If the remainder is 0, the final
   installment equals the monthly amount and total_installments equals
   full_payment_count with no separate final payment.

4. When remainder > 0:
   **total_installments** = full_payment_count + 1
5. When remainder == 0:
   **total_installments** = full_payment_count
   **final_payment_amount** = monthly_payment (or omit if template allows)

6. **final_due_date** = advance first_due_date by (total_installments - 1)
   months (for monthly interval). Use the same day-of-month as first_due_date;
   if the day exceeds the last day of the target month, use the last day of
   that month.

## Return-to-Court Date

The return_to_court_date is typically set after the final payment date:
- If the payment policy has a return_to_court_offset_days, add that many days
  to final_due_date.
- If the answer template provides candidate return dates, prefer those.
- If neither is available, use a reasonable offset (typically 30-60 days after
  final_due_date).

## Budget Support Classification

When the answer template requires budget review:

1. **monthly_disposable_income** = monthly_income - monthly_obligations

2. Compare selected_installment_amount to the payment policy band:
   - If selected_installment_amount is within [min_monthly, max_monthly] AND
     monthly_disposable_income >= selected_installment_amount:
     → supported_by_budget or supportable
   - If selected_installment_amount < min_monthly:
     → below_policy_minimum
   - If selected_installment_amount > max_monthly:
     → above_policy_maximum
   - If monthly_disposable_income < selected_installment_amount:
     → unsupported_by_budget

3. The approved_monthly_amount should be the minimum of:
   - The petitioner's requested amount
   - The policy max_monthly
   - The monthly_disposable_income
   But not below the policy min_monthly unless the budget genuinely
   cannot support the minimum.

## Payment Application Order

When restitution and fines/costs both exist:
- Check the payment policy restitution_priority field.
- If the policy says "Restitution before fines and costs", use
  restitution_before_fines_costs.
- If there is no restitution balance, use fines_costs_only.

## Trailing Remainder Examples

These examples use abstract amounts to illustrate the formula. Substitute the
actual total_due and installment_amount for each matter.

**Example A — remainder exists:**
total_due = 1200.00, installment = 70.00
- 1200 / 70 = 17 remainder 10
- full_payment_count = 17
- 17 × 70 = 1190
- final_payment_amount = 1200 - 1190 = 10.00
- total_installments = 18

**Example B — larger remainder:**
total_due = 1100.00, installment = 45.00
- 1100 / 45 = 24 remainder 20
- full_payment_count = 24
- 24 × 45 = 1080
- final_payment_amount = 1100 - 1080 = 20.00
- total_installments = 25

**Example C — exact division (no remainder):**
total_due = 900.00, installment = 75.00
- 900 / 75 = 12 exactly
- full_payment_count = 12
- final_payment_amount = 75.00 (same as monthly)
- total_installments = 12
