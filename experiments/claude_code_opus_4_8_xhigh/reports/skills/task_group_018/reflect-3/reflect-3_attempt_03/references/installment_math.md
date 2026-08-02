# Installment schedule — value-free computation pattern

Use this when a payment policy governs an installment / extended-payment order.
All inputs come from the task's petition/intake materials and the jurisdiction's
**payment-policy** record. No task-specific numbers are baked in here.

## Inputs

- `total_due` = `fines_costs_balance` + `restitution_balance` + `account_fee_applied`
  - `account_fee_applied` is the amount **current policy** supports (frequently 0;
    a fee noted only on an old worksheet/footer is excluded → 0).
  - Restitution **is** included in `total_due`.
- `monthly` = approved monthly amount
  - Approve the requested amount when it is within the policy `[min_monthly,
    max_monthly]` band **and** ≤ disposable income (`income − obligations`).
    Otherwise classify as below-minimum / above-maximum / unsupported-by-budget
    and set the amount per the template's rule.
- `first_due_days`, `return_to_court_offset_days` — from the policy row.
- `base_date` = the petition submission / order date.

## Amount breakdown

```
full_installments = floor(total_due / monthly)
remainder         = round(total_due - full_installments * monthly, 2)

if remainder > 0:
    total_installments   = full_installments + 1
    final_payment_amount = remainder
else:
    total_installments   = full_installments
    final_payment_amount = monthly     # divides evenly; last payment is a full one
```

- `regular_installment_amount` = `monthly`.
- The template may ask for both a "full installment count" and a "total payment
  count": full = `full_installments`, total = `total_installments`.

## Date breakdown

```
first_due_date      = base_date + first_due_days            # calendar days
final_due_date      = first_due_date + (total_installments - 1) months   # same day-of-month
return_to_court_date = final_due_date + return_to_court_offset_days       # calendar days
```

- Installments recur monthly on the same day-of-month as `first_due_date`.
- `first_due_days` and `return_to_court_offset_days` are **day** offsets; the
  step between installments is in **months**.
- Reproduce dates deterministically (do not rely on today's date).

## Payment application order

- restitution > 0 and policy is restitution-first → `restitution_before_fines_costs`
- restitution == 0 → `fines_costs_only`
- (only use a fines-before-restitution value if the policy explicitly says so)

## Sanity checks

- `full_installments * monthly + final_payment_amount == total_due`.
- If a candidate first-due / return-to-court date is supplied anywhere in the
  materials, your formulas should reproduce it exactly; if not, re-check whether
  `total_due` should include restitution and whether the base date is the
  submission date.
