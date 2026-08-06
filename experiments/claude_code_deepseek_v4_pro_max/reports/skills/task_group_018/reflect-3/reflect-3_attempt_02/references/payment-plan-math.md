# Payment Plan Computation

## Standard Installment Plan

Given:
- `T` = total due (fines + costs + assessments + fees, excluding restitution)
- `M` = court-approved monthly payment amount
- `D` = disposition date (or petition submission date for post-disposition plans)
- `O` = policy's `first_due_days` offset
- `R` = policy's `return_to_court_offset_days`

Compute:
1. **first_due_date** = D + O days
2. **full_installment_count** = floor(T / M)
3. **final_payment_amount** = T − (full_installment_count × M)
   - If final_payment_amount = 0: plan pays evenly, final_payment_amount = M, total_installments = full_installment_count
   - If final_payment_amount > 0: total_installments = full_installment_count + 1
4. **final_due_date** = first_due_date + (total_installments − 1) months
5. **return_to_court_date** = petition_submission_date + R days (or derived per policy)

## Budget Review Classification

Given:
- `I` = monthly income
- `O_bl` = monthly obligations
- `D_sp` = I − O_bl (monthly disposable income)
- `M_app` = approved monthly payment
- `M_min` = policy minimum monthly
- `M_max` = policy maximum monthly

Classification:
- `supported_by_budget`: M_app ≥ M_min AND M_app ≤ M_max AND M_app ≤ D_sp
- `below_policy_minimum`: M_app < M_min
- `above_policy_maximum`: M_app > M_max
- `unsupported_by_budget`: M_app > D_sp (even if within policy band)

## Restitution Handling

When restitution is present:
- Track restitution balance separately from fines_and_costs
- Apply the jurisdiction's payment priority:
  - `restitution_before_fines_costs`: first payments go to restitution, remainder to fines/costs
  - `fines_costs_before_restitution`: reverse order
- Restitution due date may differ from fines/costs schedule
