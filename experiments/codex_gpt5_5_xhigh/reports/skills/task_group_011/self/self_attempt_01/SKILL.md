# Credit Office Committee JSON SOP

Use this skill for credit-office committee tasks that ask for a branch or credit-union segment analysis and require a JSON response matching `input/payloads/answer_template.json`.

## Boundaries and Sources

- Use the remote public API only. Do not inspect local environment source, local data files, generated databases, train outputs, test files, notes, reports, or judge endpoints.
- Base API: `<environment_base_url>`.
- Start every task by reading the prompt and its `answer_template.json`. The template is the contract for required keys, enum values, precision, and list ordering.
- Fetch only data needed for the requested target:
  - `/api/manifest`
  - `/api/policies`
  - `/api/branches/{branch_id}`
  - `/api/branches/{branch_id}/metrics`
  - `/api/branches/{branch_id}/loans`
  - `/api/branches/{branch_id}/sector-exposures`
  - `/api/branches/{branch_id}/applications`
  - `/api/benchmarks/fdic/q4-2024`
  - `/api/benchmarks/ncua/q1-2025`
  - `/api/credit-union-segments/{segment_id}`

## General Answer Discipline

- Return only valid JSON when requested; no prose outside the object.
- Preserve required top-level keys from the template. Use exactly the controlled enum strings and reason codes from the template.
- Apply the template's sorting rules: common patterns are ascending `loan_id`, ascending `application_id`, ascending rating, sector, action, trigger id, or descending exposure then ascending id.
- Round currency/exposure fields to 2 decimals, ratios to 4 decimals, basis points to 2 decimals, DSCR values to 2 decimals, and weighted scores to the template precision.
- Use current/as-of metrics carefully. Branch metrics are rows; select the row matching the review quarter/as-of date, usually the latest `2025Q1` row for 2025-03-31 tasks.
- Use `outstanding_balance` as loan exposure. Use `requested_amount` for application request size. Use `bank_capacity_used` for the amount retained by the branch after participation or reductions.

## Policy Math

Read `/api/policies` each time and use its values rather than hard-coding from memory.

Risk regrade:

- Regrade only the population requested by the prompt, such as loans with `current_rating >= 3` or adverse loans with `current_rating >= 6`.
- Final re-derived rating is the worst numeric rating from available DSCR, LTV/collateral, and delinquency factors.
- DSCR policy buckets: `>=1.50 -> 3`, `>=1.25 -> 4`, `>=1.05 -> 5`, `>=1.00 -> 6`, `<1.00 -> 7`.
- LTV policy buckets: `<=0.65 -> 3`, `<=0.75 -> 4`, `<=0.85 -> 5`, `<=1.00 -> 6`, `>1.00 -> 7`.
- Delinquency minimums: `30 Days Past Due -> 4`, `60 Days Past Due -> 5`, `90+ Days Past Due -> 7`, `Nonaccrual -> 8`; `Current` has no minimum.
- Material downgrade means `final_rating - current_rating >= policies.risk_rating.material_downgrade_notches`.

CDFI factor score:

- Sum the policy score buckets for available `fico`, `ltv`, `debt_to_asset`, and `liquidity_months`.
- Class ranges: `Prime` 0-5, `Desirable` 6-9, `Satisfactory` 10-13, `Watch` 14-18, `Doubtful` >=19.
- Override to `Projected Loss` when score is >=19 and `ltv > 1.0`.

Stress tests:

- Watch-list stress: `stressed_dscr = dscr / (1 + 0.18)`, shock label from policy (`+200bp`), threshold `1.00`.
- CRE dual stress: `stressed_dscr = dscr * 0.85 / (1 + 0.18)`, threshold `1.00`.
- Include stress rows only when DSCR is available. Breach lists contain only ids with stressed DSCR below the threshold.

Benchmarks and variances:

- FDIC benchmark values are ratios. `variance_ratio = branch_ratio - fdic_benchmark_ratio`; `variance_bps = variance_ratio * 10000`.
- Branch NPA ratio uses `metrics.nonperforming_loans / metrics.total_loans_outstanding`.
- For NCUA segment tasks, benchmark rows are integer metrics. Direction fields mean literal numeric direction (`higher`, `lower`, `equal`) versus US or peer median, not whether the direction is favorable.

## Branch Portfolio Reviews

- For rating migration, group final exposure totals by final rating and count loans. For migrations from a current rating bucket, filter first, then group by final rating and include sorted `loan_ids`.
- Choose the top problem credit by severity first (highest final rating, nonaccrual/90+ status, projected loss or weakest CDFI class), then by exposure if needed.
- Watch-list/workout actions should follow severity using only template enums: `monitor`, `watchlist`, `special_assets`, `workout`, `partial_chargeoff_review`, `legal_referral`. Tie actions to objective severity such as final rating, payment status, stress breach, and projected-loss status.
- For severe bucket counts, group the adverse population by `current_rating` and `payment_status`; sum `outstanding_balance`.

## Application Allocation and CRE Decisions

- Capacity comes from `branches.lending_capacity_q1`. Sum approved retained exposure into `committed_capacity_amount`; `remaining_capacity = lending_capacity_q1 - committed_capacity_amount`.
- Sector exposure rows provide `current_exposure`, `limit_pct`, and `grandfathered`. If a sector row is absent, fall back to `branches.sector_ceiling_pct`.
- Concentration ratios use branch loan totals, not total assets. Current sector concentration is `current_exposure / metrics.total_loans_outstanding`.
- For post-approval views, keep the same denominator convention consistently: add approved/retained loan exposure to the sector numerator and to the total-loan denominator when modeling the pro-forma loan portfolio.
- Existing over-limit exposure can be grandfathered, but new approvals should not worsen a sector over the ceiling without mitigation such as participation, reduced amount, or board exception.
- CRE policy limit comes from `branches.cre_policy_limit_pct`; selected policy variance in bps is `(selected_post_approval_cre_concentration - cre_policy_limit_pct) * 10000`.
- CRE weighted scoring uses `policies.cre_weighted_score.weights`; lower is better. Classify using policy class cutoffs: `approve_quality` up to 2.0, `conditional` up to 3.0, `weak` above 3.0.
- Reason codes should be objective and sorted where required: examples include `capacity_limit`, `sector_breach`, `weak_dscr`, `high_ltv`, `low_fico`, `recent_bankruptcy`, `startup_risk`, `underwater_collateral`, `policy_floor_missing`, `documentation_gap`, `fdic_adverse_variance`, and `ncua_peer_weakness`.

## Credit-Union Segment Posture

- Fetch the segment endpoint, NCUA benchmark table, policy, and manifest. Use the segment's `state_code`, `peer_states`, `minimum_checklist`, `quarterly_capacity`, `current_outstanding`, and `risk_tolerance`.
- `state_metrics` should be copied from the NCUA row for the segment state with integer values as reported.
- Sort `peer_states` ascending in the answer. Compute peer median for each metric from those states, then compare the target state to US and peer median.
- Capacity status is based on remaining quarterly capacity. External risk status should summarize whether the state is stronger, mixed, or weaker versus national and peer metrics.
- Controls should combine the required checklist gates from the segment with operating controls justified by the risk posture. Escalation triggers must use only template condition and owner enums and be sorted by `trigger_id`.

## Final Validation

- Validate the object against the template manually before responding: required keys present, no extra narrative, all enums legal, numbers rounded, and list ordering correct.
- Recalculate totals from source rows rather than copying intermediate text. Watch especially for ratio denominators, basis-point signs, missing DSCR rows, and declined/deferred applications that should use zero approved amount and zero capacity.
