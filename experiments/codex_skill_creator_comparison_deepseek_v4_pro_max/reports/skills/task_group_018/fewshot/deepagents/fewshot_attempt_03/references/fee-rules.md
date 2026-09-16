# Fee Rules and Payment Plan Math

## Fee Posting Rules

### Court Costs

Court costs are jurisdiction-specific flat amounts applied to every disposed criminal or traffic case. Verify the current amount from the portal fee schedule for the target jurisdiction. Do not assume a fixed number across jurisdictions.

### Fines

For criminal cases: take the fine amount from the judge's sentencing pronouncement in the hearing notes. If the judge waived the fine, the amount is zero.

For traffic violations: take the fine from the active fee schedule for the violation tier (e.g., speed band). The schedule provides the standard fine amount. Do not use stale schedule amounts or statutory maximum notes when a current tiered schedule exists.

### Drug / Crime-Lab Assessments

These are jurisdiction-specific assessments tied to controlled-substance convictions. Verify the current amount from the portal fee schedule. Do not carry forward an archived amount from a prior-year worksheet.

- If the charge was amended away from a lab-eligible offense to a non-lab offense (e.g., controlled substance amended to misdemeanor theft), do not post the lab assessment.
- If the judge expressly ordered the lab assessment on the record, post it even if a worksheet omitted it.

### Public Defender User Fee

Post only when counsel is classified as `public_defender`. Do not post when counsel is `appointed_private`, `retained`, or unknown. If a finance queue line includes a PD user fee but the case is reclassified to appointed-private, the user fee is excluded from the reconciled total.

### Excluded Charges

These charges must be excluded from all case totals unless the current portal payment policy or the judge's order directly supports them:

- `account_management_fee` — not automatic under most policies; verify
- `collection_fee` — requires a triggering collection referral
- `late_payment_fee` / `late_fee` — requires a missed payment
- `dmv_fee` / `dmv_reinstatement_fee` — not part of the court balance unless ordered
- `returned_check_fee` — requires a returned payment event
- `restitution` — requires a restitution order
- `court_appointed_attorney_fee` — requires a specific order
- `court_reporter_fee` — requires a specific order
- `copy` / `certification` fees — require a specific order
- `traffic_school_fee` — requires a traffic-school referral in the hearing order
- `stale_2022_standard_fine` / stale schedule amounts — overridden by current schedule
- `statutory_maximum_substitution` — unsupported when a current specific tier applies

When assembling an excluded-charges list, include every charge type that the local materials or portal policy do not support. Use reason codes:

| Reason Code | Meaning |
|-------------|---------|
| `not_current_policy` | Fee is not part of the current payment policy |
| `no_triggering_event` | No event (default, collection referral, returned check, DMV action) occurred |
| `not_in_hearing_order` | Judge did not order this fee |
| `stale_schedule` | Fee amount comes from an outdated schedule |
| `unsupported_post_disposition` | Fee is not applicable in the post-disposition context |
| `no_order_or_policy_support` | No judge's order or policy supports this item |
| `not_part_of_balance` | Item is not part of the court-ordered balance |

## Payment Plan Math

### Installment Calculation

Given total_due and monthly_payment:

```
total_installments = ceil(total_due / monthly_payment)
full_payment_count = floor(total_due / monthly_payment)
final_payment_amount = total_due - (full_payment_count * monthly_payment)
```

If total_due divides evenly by monthly_payment, final_payment_amount equals monthly_payment and full_payment_count equals total_installments.

### Date Math

- `first_due_date`: typically the 15th of the month following disposition, or as specified in the hearing notes.
- `final_due_date`: advance from `first_due_date` by `(total_installments - 1)` months on the same day of the month.
- `return_to_court_date`: typically 60 days after `final_due_date`.

When a specific first-due date or return date is provided in the local materials, use that instead.

### Budget-Based Support Classification

When a petition includes income and obligations:

1. Compute `disposable_income = monthly_income - total_monthly_obligations`.
2. Compare the requested installment amount to the policy band (minimum and maximum monthly amounts from the portal payment policy).
3. If the requested installment is within the policy band and does not exceed disposable income: `supportable` / `supported_by_budget`.
4. If below the policy minimum: `below_policy_minimum`.
5. If above the policy maximum: `above_policy_maximum`.
6. If the requested installment exceeds disposable income: `unsupported_by_budget`.

### Payment Application Order

When a petition has both fines/costs and restitution balances:

- If restitution balance is zero: `fines_costs_only`.
- If the counter note or policy specifies restitution first: `restitution_before_fines_costs`.
- Otherwise, follow the portal payment policy for the jurisdiction.

### Account Fee Treatment

Check the portal payment policy for whether an account-management or service fee is included. In most policies it is excluded unless specifically ordered. Use:

- `excluded_by_policy` when the policy does not support it.
- `included_by_policy` when the policy explicitly includes it.
- Set the account fee amount to 0.00 when excluded.

## Register Totals

When computing batch register totals:

- `disposed_case_count` / `assessed_case_count`: count of cases with fee_status `post`.
- `held_case_count` / `excluded_pending_count`: count of cases with fee_status `hold` or `do_not_post_pending`.
- Sum each fee category (fine, court_cost, assessment, user_fee, crime_lab_fee) across all posted cases.
- `grand_total` / `batch_total_due`: sum of all case_totals for posted cases.
- Unsupported charge totals are always zero in the final closeout.
