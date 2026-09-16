# Payment Computation Rules

## Fee Schedule Currency

Always use the portal's current fee schedule for the jurisdiction. Never carry forward amounts from:

- Older/archived worksheets
- Stale statutory tables (e.g., 2022 SOF tables)
- Draft intake cover sheets
- Previous-year fee schedules

When a local material lists an amount that differs from the portal schedule, replace the local amount with the portal amount and record a `fee_schedule` audit conflict.

## Fee Categories

Common fee categories and their treatment:

| Fee | Source | Notes |
|---|---|---|
| Fine | Judge's pronouncement in hearing notes | If judge waived fine, use 0.00 |
| Court cost | Portal fee schedule | Mandatory when case is disposed |
| Drug assessment | Portal fee schedule | Only when conviction count is a controlled-substance offense |
| Public defender user fee | Portal fee schedule | Only when counsel is `public_defender` and case is disposed |
| Crime lab fee | Portal fee schedule | Only when judge specifically ordered it (check hearing notes) |
| Restitution | Hearing notes or sentencing order | 0.00 unless specifically ordered |

### When Fees Are Zero

- **Fine**: 0.00 when judge waived the fine or no fine was announced
- **Drug assessment**: 0.00 when conviction is not a controlled-substance count
- **PD user fee**: 0.00 when counsel is `appointed_private` or `retained`
- **Crime lab fee**: 0.00 when judge did not order it (even if worksheet carries a value)
- **Restitution**: 0.00 when no restitution order exists

### When Fees Are Excluded (not posted)

A fee is excluded (0.00 and documented in `excluded_financial_items`) when:

- No portal policy or court order supports it
- No triggering event has occurred (e.g., no late payment, no returned check, no collection referral)
- The hearing record does not mention it
- Current policy explicitly disallows it

## Payment Plan Computation

### Core Formula

Given `total_due` (sum of all posted fee amounts) and `installment_amount` (monthly payment):

```
full_installment_count = floor(total_due / installment_amount)
final_payment_amount = total_due - (full_installment_count * installment_amount)
total_installments = full_installment_count + (1 if final_payment_amount > 0 else 0)
```

### Edge Cases

- **Balance divides evenly**: `final_payment_amount = 0.00`, `total_installments = full_installment_count`
- **No total_due**: `full_installment_count = 0`, `final_payment_amount = 0.00`, `total_installments = 0`
- **Installment exceeds total_due**: `full_installment_count = 1`, `final_payment_amount = 0.00`, `total_installments = 1`

### Installment Payment Verification

Verify computed values:

```
(full_installment_count * installment_amount) + final_payment_amount === total_due
```

### Date Computation

```
final_due_date = first_due_date + (total_installments - 1) months
```

Add months by incrementing the month field. When the target day does not exist in the target month (e.g., Jan 31 + 1 month), use the last day of the target month.

```
return_to_court_date = final_due_date + 2 months
```

The return-to-court date is typically 2 months after the final payment due date, same day of month.

## Budget Support Classification

When a petition includes budget data (monthly income and obligations):

```
monthly_disposable_income = monthly_income - monthly_obligations
```

Classification rules:

| Condition | Classification |
|---|---|
| `installment_amount <= monthly_disposable_income` and `installment_amount >= policy_band.minimum_monthly` | `supported_by_budget` or `supportable` |
| `installment_amount < policy_band.minimum_monthly` | `below_policy_minimum` or `unsupported_by_budget` |
| `installment_amount > policy_band.maximum_monthly` | `above_policy_maximum` |
| `monthly_disposable_income < 0` | `unsupported_by_budget` |

## Payment Application Order

When both restitution and fines/costs exist:

- If the petition explicitly requests restitution-first allocation: use `restitution_before_fines_costs`
- If only fines/costs exist (no restitution): use `fines_costs_only`
- Default unless specified otherwise: check the petition's counter note

## Account Fee Treatment

Account-management or maintenance fees appearing on counter worksheets:

1. Check the current portal payment policy for the jurisdiction.
2. If current policy excludes the fee: set `account_fee = 0.00`, document as `excluded_by_policy`.
3. If current policy includes the fee: use the policy amount, document as `included_by_policy`.
4. If a supervisor note explicitly asks for a policy check before carrying forward: default to exclusion until portal confirms otherwise.

## Return-to-Court Setting

The return-to-court date is a compliance review date, set after the payment schedule completes. Default: 2 months after `final_due_date`. The return-to-court trigger is `nonpayment` for installment plans, `none` when no plan exists.

## Down Payment

Default is 0.00 unless the petition or hearing order specifies otherwise. Never invent a down payment amount.
