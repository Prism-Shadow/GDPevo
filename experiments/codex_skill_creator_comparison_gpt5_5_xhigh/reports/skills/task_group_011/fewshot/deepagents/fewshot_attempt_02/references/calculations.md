# Credit Office Calculations

## Public API order

1. Read `TASK_ENV_BASE_URL` from the runner.
2. Use only the public endpoints listed in the staged environment note.
3. Pull the latest branch metrics row, the relevant branch detail, the branch loans or applications, the branch sector exposures, the policies document, and the benchmark table named by the prompt.

## Universal handling

- Use exact arithmetic when possible, then round only for the final JSON.
- Currency fields: 2 decimals.
- Ratios and percentages: use the template precision.
- Basis-point variances: ratio difference multiplied by 10,000.
- Sort `loan_id`, `application_id`, and other IDs lexicographically unless the template defines another order.

## Branch rating migration

- Regrade loans whose current rating meets the prompt floor.
- Final rating is the worst numeric rating from the available objective factors.
- If no objective factor applies, keep the current rating.

### Policy thresholds

- DSCR: `>= 1.5 -> 3`, `>= 1.25 -> 4`, `>= 1.05 -> 5`, `>= 1.0 -> 6`, `< 1.0 -> 7`.
- LTV: `<= 0.65 -> 3`, `<= 0.75 -> 4`, `<= 0.85 -> 5`, `<= 1.0 -> 6`, `> 1.0 -> 7`.
- Delinquency: `30 Days Past Due -> 4`, `60 Days Past Due -> 5`, `90+ Days Past Due -> 7`, `Nonaccrual -> 8`.

### Migration outputs

- `final_rating_exposure_totals`: group by final rating, sort ascending by rating.
- `migration_from_current_rating_3`: keep only loans whose current rating is 3, group by final rating, sort ascending by final rating, and sort loan IDs inside each group.
- Material downgrade: final rating minus current rating is at least the policy notch threshold.
- `top_problem_credit`: choose the highest final rating, then highest exposure.
- NPA benchmark: use `nonperforming_loans` as exposure, `total_loans_outstanding` as the denominator, and compare the branch ratio to the benchmark ratio.

## Watch-list stress

- Adverse population starts at the prompt’s minimum current rating.
- Use the policy stress formula `stressed_dscr = dscr / 1.18` for watch-list stress.
- Breach threshold is `1.0`.
- Queue order is descending exposure, then ascending loan ID.
- `projected_loss` is true when the facts support a loss-grade outcome, especially underwater collateral or nonaccrual severity.
- Map severe workout actions by severity:
  - `Watch` or similar but still current: `watchlist`
  - severe adverse with payment stress: `special_assets`
  - projected loss or nonaccrual: `partial_chargeoff_review`

### Severe bucket counts

- Group by `current_rating` and `payment_status`.
- Sort by rating first, then payment status text.

## CDFI factor scoring

Use the policy bands exactly.

- `debt_to_asset`: `< 0.40 -> 0`, `0.40-0.60 -> 2`, `0.60-0.80 -> 4`, `> 0.80 -> 6`.
- `ltv`: same bands as `debt_to_asset`.
- `fico`: `> 720 -> 0`, `680-720 -> 1`, `580-679 -> 3`, `< 580 -> 5`.
- `liquidity_months`: `> 12 -> 0`, `6-12 -> 1`, `3-6 -> 3`, `< 3 -> 5`.

Classify the sum of available factor scores as:

- `Prime`: 0-5
- `Desirable`: 6-9
- `Satisfactory`: 10-13
- `Watch`: 14-18
- `Doubtful`: 19+

Use `Projected Loss` when the prompt or facts indicate underwater collateral and loss-grade review, even if the raw score is otherwise borderline.

## Lending allocation

- `lending_capacity_q1` comes from the branch record.
- `gross_approved_amount` is the sum of approved and conditionally approved request amounts.
- `committed_capacity_amount` is the bank-funded amount after guarantees or participation.
- `remaining_capacity = lending_capacity_q1 - committed_capacity_amount`.
- `priority_ranking` includes only approved and conditionally approved applications, ordered from strongest selected fit to weakest selected fit.

### Decision rubric

- Approve high-fit, within-capacity requests with no material policy issue.
- Use `conditional_approve` when mitigation cures the issue.
- Use `defer` for stronger credits that are not selected because of concentration, FDIC pressure, or sequencing.
- Use `decline` when the request fails policy or cannot fit the remaining allocation.

### Common decline reasons

- `capacity_limit`: allocation cannot support the request or its bank-funded share.
- `sector_breach`: approval would worsen a sector concentration breach.
- `weak_dscr`: base or stressed coverage is below the policy floor.
- `high_ltv`: leverage is above tolerance.
- `low_fico`: FICO is below the floor.
- `recent_bankruptcy`: bankruptcy recency is adverse.
- `startup_risk`: operating history is too short without enough mitigation.
- `underwater_collateral`: collateral is loss-grade or above 1.0 LTV.
- `policy_floor_missing`: required checklist item is missing.
- `documentation_gap`: required documents are incomplete.
- `fdic_adverse_variance`: benchmark underperformance is part of the rationale.
- `ncua_peer_weakness`: peer comparison is weak enough to affect the decision.

### Concentration math

- Use the latest `total_loans_outstanding` as the base denominator for current concentration.
- For post-approval concentration, add the selected gross approval amount to the denominator.
- Compare the post-approval ratio to the branch `cre_policy_limit_pct` or sector ceiling from sector exposures.
- For a participation request, solve the retained amount `x` from:

  `current_sector_exposure + x <= sector_limit * (current_total_loans + other_committed_bank_exposure + x)`

- `bank_capacity_used` is the retained bank exposure after participation or the bank-funded share after an SBA guaranty.

## Competing CRE

- Use the published CRE weights:
  - capacity `0.45`
  - capital `0.03`
  - character `0.05`
  - collateral_exposure `0.36`
  - conditions `0.11`
- Build each component score from the evidence in the prompt:
  - capacity from stressed DSCR coverage
  - capital from debt-to-asset
  - character from guarantor strength, FICO, seasoning, delinquencies, and bankruptcy history
  - collateral_exposure from LTV
  - conditions from concentration and benchmark pressure
- Lower weighted score is better.
- Class bands: `approve_quality` at or below 2.0, `conditional` at or below 3.0, `weak` above 3.0.
- For the unselected request, use only the reason codes allowed by the template.

## Credit-union segment posture

- Use the state benchmark row exactly as reported by the NCUA table.
- Compare North Carolina or the target state to the U.S. row and the peer median.
- Pick peer states in ascending state code order.
- Use `continue_approving` when external conditions are routine.
- Use `continue_with_tighter_conditions` when capacity exists but external risk or control issues are weaker.
- Use `temporarily_pause` only when capacity is unavailable or the prompt says to stop until metrics recover.

### Controls and escalations

- Keep the required checklist gates from the prompt or minimum checklist.
- Add operating controls for insurance, lien perfection, benchmark monitoring, delinquency watch, underwriting review, and capacity exceptions when the facts justify them.
- Escalation triggers:
  - 90 bps delinquency or worse: `credit_risk_manager`
  - missing insurance or lien exception: `operations_control_manager`
  - capacity exception or overrun: `lending_committee_chair`
  - state delinquency gap widening by 25 bps: `credit_risk_manager`
