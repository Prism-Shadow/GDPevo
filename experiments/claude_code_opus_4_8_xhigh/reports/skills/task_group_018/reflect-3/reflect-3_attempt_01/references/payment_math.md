# Payment-plan / installment math

Deterministic rules for building an installment schedule. Do the arithmetic (use
`../scripts/installments.py`); do not estimate. All inputs come from the payment
**policy** for the jurisdiction and the **balance** owed.

## Inputs

- `total_due` = `fines_costs_balance + restitution_balance`.
  - Add an account/maintenance fee **only** if the policy explicitly flags one
    (`account_fee > 0`). Otherwise the fee is excluded and contributes 0, even if a
    counter/worksheet note carries an old fee amount.
- `monthly` = the approved monthly amount: the requested amount when it lies within
  the policy `[min_monthly, max_monthly]` band and is affordable
  (`<= disposable = income - obligations`); otherwise clamp/classify per the
  template.
- `first_due` = anchor date + policy first-due rule (a fixed number of days after
  the submission/disposition date, or "the 15th of the next month" if the policy
  says so).
- Down payment = policy value (usually 0).

## Schedule

```
full        = floor(total_due / monthly)         # count of full-value installments
remainder   = round(total_due - full * monthly, 2)
if remainder > 0:
    total_installments   = full + 1
    final_payment_amount = remainder
else:
    total_installments   = full
    final_payment_amount = monthly               # last one is a normal full payment
final_due_date        = first_due + (total_installments - 1) months   # same day-of-month
return_to_court_date  = final_due_date + policy.return_to_court_offset_days
```

Notes:
- The final partial installment is the leftover **remainder** (a small final
  payment), not a larger final payment. "full installment count" is the count of
  full-value payments; "total installments" includes the final partial one.
- Month addition keeps the same day-of-month, clamping to the month's last day when
  needed (e.g. Jan 31 + 1 month → Feb 28/29).
- `return_to_court_offset_days` is counted in **calendar days** from the final due
  date.

## Payment application order

- restitution > 0 and policy prioritizes restitution → "restitution before fines
  and costs".
- restitution == 0 → "fines/costs only" (do **not** use the restitution-priority
  value just because the policy mentions it; with nothing to apply first it is
  fines/costs only, and stating otherwise is inconsistent with a zero restitution
  balance).

## License suspension

- `suspension_start` = conviction date (unless a policy/order specifies release or
  petition date). `suspension_end` = start + months (same day-of-month clamp).

## Worked shape (structure only — plug in the task's own numbers)

Given a balance `B`, monthly `M`, first due `D0`, offset `K` days:
`full = B//M`, `rem = B - full*M`, `n = full + (1 if rem else 0)`,
`final = rem if rem else M`, `Dfinal = D0 + (n-1) months`,
`return = Dfinal + K days`. Confirm every date with the script.
