# Case Workflow

Use this reference when the prompt asks for a committee-ready JSON package from the credit office API.

## Endpoint Map

- Always fetch `GET /api/manifest` and `GET /api/policies` first.
- Branch cases usually need:
  - `GET /api/branches/{branch_id}`
  - `GET /api/branches/{branch_id}/metrics`
  - `GET /api/branches/{branch_id}/loans`
  - `GET /api/branches/{branch_id}/sector-exposures`
  - `GET /api/branches/{branch_id}/applications`
  - FDIC benchmark from `/api/benchmarks/fdic/q4-2024`
- Segment cases usually need:
  - `GET /api/credit-union-segments/{segment_id}`
  - `GET /api/benchmarks/ncua/q1-2025`

## Shared Calculations

- Branch NPA ratio = `nonperforming_loans / total_loans_outstanding`
- FDIC variance ratio = `branch_npa_ratio - fdic_benchmark_ratio`
- bps = `ratio * 10000`
- CRE exposure = sum of branch loans where `loan_type == "CRE"`
- Existing CRE concentration = `existing_cre_exposure / total_loans_outstanding`
- Selected post-approval CRE concentration = `(existing_cre_exposure + selected_requested_amount) / (total_loans_outstanding + selected_requested_amount)`
- Post-approval sector concentration = `(current_sector_exposure + approved_amount_for_that_sector) / (total_loans_outstanding + gross_approved_amount)`
- Watch-list stress = `dscr / (1 + 0.18)`
- Dual CRE stress = `dscr * 0.85 / (1 + 0.18)`
- CDFI factor score = sum of the available objective-factor scores; missing fields count as 0

## Branch Regrade Rules

- Regrade population: loans at or below the prompt threshold, commonly `current_rating >= 3`.
- Final rating: worst numeric rating from the DSCR, LTV, and delinquency factor ratings.
- Material downgrade: notch drop that meets `policy.risk_rating.material_downgrade_notches`.
- Follow-up coverage: group the loans that need action after regrade and keep the action ladder severity-consistent.

## Sorting Rules

- Sort application decisions by `application_id` ascending.
- Sort regrade and downgrade lists by `loan_id` ascending.
- Sort workout queues by exposure descending, then `loan_id` ascending.
- Sort severe-bucket summaries by `current_rating` ascending, then `payment_status`.
- Sort peer states by state code ascending.

## Action Ladder

- `monitor` for light follow-up
- `watchlist` for moderate adverse credits
- `special_assets` for 90+ DPD or watch-class credits
- `workout` for more severe recovery work
- `partial_chargeoff_review` for projected-loss or nonaccrual credits
- `legal_referral` for the most severe recovery cases
