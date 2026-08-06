# Payment Schedule Computation

## Inputs needed

1. **total_due** = fines_and_costs_balance + restitution_balance (no unsupported fees)
2. **installment_amount** = petitioner's requested monthly, clamped to policy band
3. **policy** from /api/payment-policies: min_monthly, max_monthly, first_due_days, return_to_court_offset_days, account_fee, down_payment_required

## Classification

- `supportable`: requested amount ≥ min_monthly AND ≤ max_monthly AND disposable income can sustain it
- `below_policy_minimum`: requested < min_monthly (policy floor not met)
- `above_policy_maximum`: requested > max_monthly
- `unsupported_by_budget`: disposable income cannot sustain the payment

## Installment math

```
full_count = floor(total_due / installment_amount)
remainder  = total_due - (full_count * installment_amount)

if remainder > 0:
    total_installments = full_count + 1
    final_payment_amount = remainder
else:
    total_installments = full_count
    final_payment_amount = 0.00
```

## Date arithmetic

- **first_due_date** = submitted_date + first_due_days (from policy)
- **final_due_date** = first_due_date + (total_installments - 1) months
- **return_to_court_date** = final_due_date + return_to_court_offset_days (from policy)

## Payment application order

- If payment policy `restitution_priority` says "Restitution before fines and costs" → use `restitution_before_fines_costs`
- If not applicable (no restitution) → use `fines_costs_only`

## Account fee

- If policy `account_fee > 0` and the case type qualifies → include it
- If policy `account_fee = 0` → set `account_fee_treatment = excluded_by_policy` and `account_fee_amount = 0.00`

## Verification

- Verify: `(full_count × installment_amount) + final_payment_amount = total_due`
- Verify: `total_installments` count is correct
- Verify: return_to_court_date is after final_due_date
