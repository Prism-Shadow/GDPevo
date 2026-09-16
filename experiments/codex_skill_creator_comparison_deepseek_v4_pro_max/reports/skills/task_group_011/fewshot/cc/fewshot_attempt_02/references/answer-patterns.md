# Answer Patterns

This document captures reusable patterns from the train answers. It does
not reproduce task-specific final values, but describes how rules map
into the JSON structure expected by answer templates.

## Pattern: Rating Migration Review

When the task asks for a portfolio regrade of loans at or above a rating
floor:

### Portfolio regrade population

Filter loans where `current_rating >= target_current_rating_min`.
Count them and sum their outstanding balances for `target_loan_count`
and `target_exposure`.

### Re-derive ratings

For every loan in the population, compute `final_rating` using the
dominant-factor rule. Even if the re-derived rating equals the current
rating, record it; the exercise covers the whole population, not just
those that changed.

### Final rating exposure totals

Group loans by `final_rating`. For each group, report `loan_count`
and the sum of `exposure` (the `outstanding_balance` field). Sort
ascending by `final_rating`.

### Migration from current_rating 3

Filter the regrade population to loans whose `current_rating` was exactly 3.
Group by `final_rating`, include `loan_count`, `exposure`, and the sorted
`loan_ids`. Sort ascending by `final_rating`.

### Watch-list action coverage

Assign a `recommended_action` to every loan that needs follow-up:
- Loans that did not migrate (final == current and performing): `monitor`
- Loans that downgraded to 6: `watchlist`
- Loans that downgraded to 7: `special_assets`
- Loans at rating 8 or Nonaccrual: `partial_chargeoff_review`

Group by action, include `loan_count`, `exposure`, `loan_ids`. Sort
ascending by action.

A loan is "covered" if its action is not `monitor`. Count `covered_loan_count`
and `covered_exposure` accordingly.

### NPA benchmark

Use the most recent quarter's branch metrics. The benchmark metric is
the one that most closely matches the branch's loan composition.
Compute ratios and variance as described in the policy translation.

### Material downgrades

For every loan where `final_rating - current_rating >= 2`, list it with
`loan_id`, `current_rating`, `final_rating`, `downgrade_notches`, and
`exposure`. Sort ascending by `loan_id`.

### Top problem credit

Select the single worst credit: highest `final_rating`, then highest
`exposure`, then worst `payment_status`. Report it with the `recommended_action`
for that severity level.

## Pattern: Lending Allocation Package

When the task asks for allocation decisions on pending applications:

### Lending capacity

`lending_capacity_q1` comes from the branch detail endpoint.

### Application evaluation

For each application, evaluate against policy floors:
- DSCR minimum: typically 1.25 for C&I and CRE, 1.15 for SBA
- LTV maximum: typically 0.80; above 0.95 is an automatic decline for most types
- FICO minimum: typically 580
- Startup risk: `years_in_business < 2.0` is a decline trigger for non-SBA
- Bankruptcy: `bankruptcy_months_ago` not null and <= 36 is a decline trigger
- Documentation: `documentation_complete == 0` means incomplete docs -> decline

### Decision flow

1. Can the branch afford it? (remaining capacity check)
2. Does it pass all policy floors?
3. Does the sector concentration allow it?
4. Assign `approve`, `conditional_approve` (with conditions), or `decline`.

`approved_amount`: the requested amount for full approvals, possibly
reduced for conditional approvals. `bank_capacity_used`: for participation
cases, the bank-retained portion; otherwise the approved amount.

### Priority ranking

Sort approved/conditionally-approved applications by credit quality.
Rank applications by: highest DSCR first, then lowest LTV, then largest
relationship deposit balance.

### Concentration flags

For each sector where an application would cause or worsen a concentration
breach, flag it. The flag is `true` when `post_approval_pct > limit_pct`.
Assign `handling` based on the policy's allowed mitigations.

### Decline reasons

For each declined application, assign the most specific reason codes that
apply. Use only codes from the template's `reason_code_enum`.

### Post-approval concentrations

After all decisions, compute for each sector: existing exposure + approved
amounts in that sector, divided by total loans outstanding. Compare to
limit_pct. Report all sectors that have exposure (not just flagged ones).

## Pattern: Credit Union Segment Posture

When the task asks for a segment posture recommendation:

### Posture

Choose from `continue_approving`, `continue_with_tighter_conditions`, or
`temporarily_pause`. The choice depends on:
- `risk_tolerance` from the segment endpoint
- State metrics relative to national and peer benchmarks
- `internal_context` (staffing, control issues, recent delinquency)
- `notes` from the segment endpoint

When risk_tolerance is "moderate" and external risk is weaker than peers
but capacity is available, the posture is `continue_with_tighter_conditions`.

### State metrics

Pull the target state's row from the NCUA benchmark data. Values are integers exactly as
reported.

### Peer comparison

Compute the median of peer state metric values. Compare the target state to US and the target state
to peer median for each of four metrics. Use `"higher"`, `"lower"`, or
`"equal"`.

### Controls

`required_checklist_gates`: the segment's `minimum_checklist`, possibly
subsetted to relevant gates.

`added_operating_controls`: derived from the internal context and notes.
When there are control issues (e.g. missed insurance binder follow-ups),
add `pre_close_insurance_binder_verification` and `lien_perfection_prior_to_funding`.
When external risk is elevated, add `quarterly_state_benchmark_monitoring`
and `monthly_segment_delinquency_watch`. When a staffing constraint exists,
add `senior_underwriter_second_review`.

### Escalation triggers

Create trigger entries with stable trigger IDs (`ET001`, `ET002`, etc.).
Each has a `condition` from the template's allowed choices and an `owner`.
Map conditions to owners based on responsibility: credit risk conditions
-> `credit_risk_manager`, operational conditions -> `operations_control_manager`,
capacity/exception conditions -> `lending_committee_chair`.

### Interpretation

`capacity_status`: based on `quarterly_capacity` vs current outstanding.
`external_risk_status`: based on peer comparison results.
`risk_tolerance`: from the segment endpoint.
`committee_message`: the template's message that best matches the combination.

## Pattern: Watch-List Stress

When the task asks for watch-list stress on adversely rated loans:

### Population

Filter loans where `current_rating >= adverse_rating_min` (typically 6).

### CDFI risk classes

For each loan in the population, compute the four factor scores (FICO, LTV,
debt-to-asset, liquidity months), sum them, and assign a risk class.

### DSCR stress

For each loan in the population that has a `dscr` value, compute the +200bp
stressed DSCR and compare to the breach threshold. The `shock_label` is
`"+200bp"`.

### Workout queue

Sort the population by descending `exposure`, then ascending `loan_id`.
For each loan, assign a `recommended_action` based on risk class, payment
status, and stress breach:

- Projected Loss -> `partial_chargeoff_review`, `projected_loss: true`
- Nonaccrual -> `partial_chargeoff_review`
- 90+ Days Past Due -> `special_assets`
- Watch risk class with breached stress -> `special_assets`
- Desirable or better, performing -> `watchlist`
- Moderate risk, not severely delinquent -> `watchlist`

`projected_loss` is `true` only for Projected Loss risk class.

### Severe bucket counts

For the adverse population, group by `current_rating` and `payment_status`.
Count loans and sum exposure. Sort ascending by `current_rating`, then
`payment_status`.

## Pattern: Competing CRE Decision

When the task asks to compare two specific CRE applications:

### Weighted CDFI scores

For each application, compute the CRE weighted score from the five C factors.
Map to score class. Note: `conditions` factor checks that `loan_type == "CRE"`;
both applications in a CRE comparison should be CRE type, so this factor is
typically 0.

### Stress results

Apply the CRE dual-stress formula to both applications. Report `base_dscr`,
`stressed_dscr`, and `breaches_threshold`.

### Concentration analysis

- Existing CRE exposure: sum of `outstanding_balance` for all CRE-type loans
  already on the books.
- `cre_policy_limit_pct`: from branch detail.
- `fdic_benchmark_metric`: choose the FDIC field matching the delinquency
  concern (for CRE, typically `total_real_estate_30_89_pct`).
- Branch delinquency ratio: `delinquency_30_plus_pct` from most recent
  branch metrics.
- Compute post-approval concentration by adding the selected application's
  requested amount to existing CRE exposure, dividing by `total_loans_outstanding`.
- Compute policy variance: `(post_approval_pct - cre_policy_limit_pct) * 10000`.

### Recommended path

Select the application with the lower weighted score (better). If both
are weak, the one with the lower score is still preferred but may get
`participation_required` instead of `approve`. The unselected application
gets `decline` or `defer` based on its score class: `weak` -> `decline`,
`conditional` -> `defer`.

Unselected reason codes: include `sector_breach` if CRE concentration
is already over the CRE policy limit, `fdic_adverse_variance` if the
branch delinquency ratio materially exceeds the FDIC benchmark,
`weak_dscr` if the application's base DSCR is below 1.25.

### Conditions

For the selected application, list conditions from the template's
allowed values. Always include: `committee_cre_exception` (when policy
limit is breached), `minimum_dscr_covenant_1_25`, `quarterly_financial_reporting`,
`updated_appraisal_before_close`, `tenant_roll_and_lease_review`,
`no_additional_cre_without_committee_review`. When the post-approval
concentration exceeds policy, add `bank_retained_exposure_cap`.
