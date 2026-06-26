# Credit Office Committee JSON SOP

Use this skill for credit-office tasks that ask for a committee-ready JSON answer about a bank branch, loan portfolio, pending applications, CRE comparison, watch-list stress, or credit-union segment posture.

## Source Discipline

- Use the remote public API only: `<environment_base_url>`.
- Do not start, inspect, or read any local environment service, database, generated data file, run output, train output, test file, notes, reports, judge endpoint, or prior skill attempt.
- Read the task prompt and its `input/payloads/answer_template.json` first. The template is the output contract for top-level keys, enum spellings, precision, required empty arrays/maps, and ordering.
- Fetch only public API data needed for the target branch or segment plus `/api/manifest`, `/api/policies`, and the named benchmark endpoint.
- Return exactly one valid JSON object. Do not include prose outside JSON.

## API Checklist

Start with:

- `/api/manifest` for `policy_version` and benchmark versions.
- `/api/policies` for rating thresholds, CDFI scoring, CRE weights, stress formulas, capacity rules, and material downgrade threshold.

For branch tasks, fetch as needed:

- `/api/branches/{branch_id}`: capacity, `sector_ceiling_pct`, `cre_policy_limit_pct`, total assets, state, benchmark set.
- `/api/branches/{branch_id}/metrics`: quarter metrics. For a 2025-03-31 review, use `2025Q1`.
- `/api/branches/{branch_id}/loans`: balances, ratings, payment status, DSCR, LTV, FICO, debt-to-asset, liquidity, loan type, sector.
- `/api/branches/{branch_id}/sector-exposures`: current sector exposure, `limit_pct`, grandfathering.
- `/api/branches/{branch_id}/applications`: pending underwriting factors and requested amounts.

For benchmark/segment tasks:

- `/api/benchmarks/fdic/q4-2024`: FDIC ratios such as `total_loans_noncurrent_pct`, `total_real_estate_30_89_pct`, and `total_real_estate_noncurrent_pct`.
- `/api/benchmarks/ncua/q1-2025`: state rows with integer `delinquency_bps`, `loan_to_share_pct`, `roaa_bps`, and `positive_net_income_pct`.
- `/api/credit-union-segments/{segment_id}`: state, peer states, checklist gates, internal context, capacity, current outstanding, and risk tolerance.

## Common Field Conventions

- Use `outstanding_balance` for loan exposure and `requested_amount` for application gross amount.
- `metrics.total_loans_outstanding` equals the sum of branch loan balances and is the denominator for branch portfolio, NPA, CRE, and sector concentration ratios unless the prompt says otherwise.
- For post-approval concentration, use a post-approval denominator: current `total_loans_outstanding` plus retained approved exposure.
- Sector limits come from `sector-exposures.limit_pct`; fall back to branch `sector_ceiling_pct` only when the sector has no override row.
- CRE exposure is the sum of `outstanding_balance` for loans with `loan_type == "CRE"`. CRE concentration is CRE exposure divided by total loans.
- Keep ratios as decimals, not whole percentages. Basis points are `ratio * 10000`.
- Round only at the output boundary: currency to 2 decimals, ratios to 4 decimals, bps to 2 decimals, DSCR to 2 decimals, CRE weighted scores to 1 decimal, unless the template says otherwise.

## Risk Rating Regrade

For a regrade population such as `current_rating >= 3`, filter by the requested current-rating minimum. Re-derive the final rating from objective policy factors, not from the prior rating.

Policy thresholds:

- DSCR: `>=1.50 -> 3`, `>=1.25 -> 4`, `>=1.05 -> 5`, `>=1.00 -> 6`, `<1.00 -> 7`.
- LTV: `<=0.65 -> 3`, `<=0.75 -> 4`, `<=0.85 -> 5`, `<=1.00 -> 6`, `>1.00 -> 7`. If LTV is missing but balance and collateral value exist, compute balance divided by collateral value.
- Delinquency minimums: `30 Days Past Due -> 4`, `60 Days Past Due -> 5`, `90+ Days Past Due -> 7`, `Nonaccrual -> 8`, `Current -> no minimum`.
- Final rating is the worst numeric rating from available DSCR, LTV/collateral, and delinquency factors.
- A material downgrade is `final_rating - current_rating >= policies.risk_rating.material_downgrade_notches`.

For NPA benchmarks:

- `branch_npa_exposure = metrics.nonperforming_loans`.
- `branch_total_loans = metrics.total_loans_outstanding`.
- `branch_npa_ratio = branch_npa_exposure / branch_total_loans`.
- `variance_ratio = branch_ratio - benchmark_ratio`; `variance_bps = variance_ratio * 10000`. Preserve the sign unless the template asks for absolute variance.

For problem-credit selection, rank first by most severe final rating, then by nonaccrual/90+ status, then by largest exposure. Use only the action enums allowed by the template; a practical severity ladder is `monitor`, `watchlist`, `special_assets`, `workout`, `partial_chargeoff_review`, `legal_referral`.

## CDFI Factor Scores And Watch-List Stress

For adverse-rated or watch-list loans, compute `factor_score` from `policies.cdfi_factor_scores` using available objective factors:

- FICO bins, LTV bins, debt-to-asset bins, and liquidity-month bins add together.
- Exact boundary values belong to the explicit middle range where listed, such as `0.40-0.60` or `680-720`.
- Class by total score: `0-5 Prime`, `6-9 Desirable`, `10-13 Satisfactory`, `14-18 Watch`, `>=19 Doubtful`.
- Override to `Projected Loss` when score is `>=19` and LTV is `>1.0`.

For watch-list DSCR stress:

- Use the policy formula exactly: `stressed_dscr = dscr / (1 + 0.18)`, even when the label says `+200bp`.
- Use only loans with DSCR available in stress result rows.
- `breaches_threshold` is true when stressed DSCR is below `policies.stress.coverage_breach_threshold` unless the prompt defines a stricter comparison.
- Sort stress rows and breach ID lists exactly as the template requires.

## Application Allocation And Concentration

For pending application packages:

- Capacity starts from `branches.lending_capacity_q1`.
- `gross_approved_amount` is the sum of approved or conditionally approved gross requested amounts.
- `bank_capacity_used` and `committed_capacity_amount` should reflect retained bank exposure after any SBA guaranty, participation, or reduced-amount condition. If no mitigation applies, retained exposure equals approved amount.
- `remaining_capacity = lending_capacity_q1 - committed_capacity_amount`.
- Rank only approved and conditionally approved applications in `priority_ranking`.

For concentration flags:

- Existing sector exposure is `sector-exposures.current_exposure`.
- `exposure_after_approval = current_exposure + retained approved exposure for that sector`.
- `post_approval_pct = exposure_after_approval / (current total loans + total retained approved exposure)`.
- `over_limit` or flags should compare post-approval percentage to the sector-specific `limit_pct`.
- Grandfathered existing over-limit exposure may be tolerated, but a new approval should not worsen it without a template-allowed mitigation such as participation, reduced amount, board exception, or decline.

Reason codes should come only from the template. Typical mappings are: weak DSCR to `weak_dscr`, high LTV to `high_ltv`, low FICO to `low_fico`, recent bankruptcy to `recent_bankruptcy`, incomplete documentation to `documentation_gap`, capacity shortfall to `capacity_limit`, sector over-limit to `sector_breach`, adverse FDIC comparison to `fdic_adverse_variance`, and weak NCUA comparison to `ncua_peer_weakness`.

## CRE Competition

For competing CRE applications:

- Fetch branch details, metrics, loans, sector exposures, the target applications, policies, and FDIC benchmark data.
- Use `policies.cre_weighted_score.weights`: capacity `0.45`, capital `0.03`, character `0.05`, collateral exposure `0.36`, conditions `0.11`.
- Lower weighted score is better. Classify with policy thresholds: `<=2.0 approve_quality`, `<=3.0 conditional`, `>3.0 weak`.
- Derive components from raw factors: DSCR for capacity, LTV for collateral exposure, total debt divided by total assets for capital when present, FICO/bankruptcy/prior delinquencies/relationship/guarantor for character, and documentation, sector concentration, CRE policy pressure, and FDIC variance for conditions.
- CRE dual stress uses `stressed_dscr = dscr * 0.85 / (1 + 0.18)`.
- Selected post-approval CRE concentration is `(existing CRE exposure + selected retained exposure) / (current total loans + selected retained exposure)`.
- Policy variance bps is `(post_approval_cre_concentration - cre_policy_limit_pct) * 10000`.
- Sort application comparisons by `application_id`; sort reason code and condition lists alphabetically when required.

## Credit-Union Segment Posture

For segment posture pages:

- Use the segment endpoint for `state_code`, `peer_states`, `minimum_checklist`, `internal_context`, `quarterly_capacity`, `current_outstanding`, notes, and risk tolerance.
- Use the NCUA benchmark row for the segment state, the `US` row, and all named peer-state rows.
- For `peer_comparison`, compare the state value to the US value and to the median of the peer-state values. Return only `higher`, `lower`, or `equal`.
- State metrics in the template are integer values exactly as reported by NCUA, not ratios.
- Required checklist gates usually come directly from `minimum_checklist`; add operating controls from current context, such as missing insurance or lien follow-up, state benchmark monitoring, second review, or capacity exceptions.
- Choose escalation triggers and owners only from the template enums, aligning owner responsibility with the trigger type.

## Output Validation

Before finalizing:

- Confirm every required top-level key is present and no uncontrolled enum value appears.
- Confirm all specified sort orders: IDs ascending, final ratings ascending, actions alphabetically, workout queues by descending exposure then ID, or template-specific order.
- Confirm numeric values are numbers, booleans are booleans, and absent result groups are represented as empty arrays or objects if required.
- Do not include candidate train answers, hidden reasoning, citations, markdown fences, or explanatory text outside the JSON response.
