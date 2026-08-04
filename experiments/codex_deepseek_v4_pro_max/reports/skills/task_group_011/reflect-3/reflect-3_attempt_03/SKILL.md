## Credit Risk Committee Analysis Skill

This skill provides reusable patterns for analyzing a credit office API and producing committee-ready JSON reports. It covers portfolio regrades, lending allocations, credit union segment posture, watch-list stress, and competing CRE decisions.

### Core Workflow

1. Read the prompt to identify the target branch/segment, review date, and template shape
2. Fetch the API manifest at `{{TASK_ENV_BASE_URL}}/api/manifest` to confirm available endpoints
3. Fetch the policies at `{{TASK_ENV_BASE_URL}}/api/policies` — always first, as they define scoring, thresholds, stress formulas, and decision rules
4. Fetch the specific branch, its loans, metrics, sector-exposures, and applications as needed
5. Fetch benchmark data (FDIC or NCUA) when the template or prompt references benchmarks
6. Apply the policy rules to the fetched data to derive ratings, scores, decisions, and classifications
7. Assemble the answer JSON to exactly match the provided answer template — use only the enums, keys, and ordering specified

### Policy Rules Reference

#### Risk Rating Re-derivation (`risk_rating` section)

Use the **dominant factor rule**: the final re-derived rating is the worst (highest numeric) rating from available factors.

DSCR thresholds (higher rating = worse):
- DSCR ≥ 1.50 → rating 3
- DSCR ≥ 1.25 → rating 4
- DSCR ≥ 1.05 → rating 5
- DSCR ≥ 1.00 → rating 6
- DSCR < 1.00 → rating 7

LTV thresholds:
- LTV ≤ 0.65 → rating 3
- LTV ≤ 0.75 → rating 4
- LTV ≤ 0.85 → rating 5
- LTV ≤ 1.00 → rating 6
- LTV > 1.00 → rating 7

Delinquency minimums:
- 30 Days Past Due → min rating 4
- 60 Days Past Due → min rating 5
- 90+ Days Past Due → min rating 7
- Nonaccrual → min rating 8

When a factor is null/missing, exclude it from the worst-of computation. If no factors are available, retain the current rating.

#### CDFI Factor Score Classification (`cdfi_factor_scores` section)

Score each available objective factor from the loan/application data:

Debt-to-Asset: <0.40→0, 0.40-0.60→2, 0.60-0.80→4, >0.80→6
FICO: >720→0, 680-720→1, 580-679→3, <580→5
Liquidity (months): >12→0, 6-12→1, 3-6→3, <3→5
LTV: <0.40→0, 0.40-0.60→2, 0.60-0.80→4, >0.80→6

Sum available factor scores, then classify:
- 0-5 → Prime
- 6-9 → Desirable
- 10-13 → Satisfactory
- 14-18 → Watch
- ≥19 → Doubtful
- ≥19 and LTV > 1.0 → Projected Loss

Payment status overrides: Nonaccrual → at least Doubtful (or Projected Loss if LTV > 1.0). 90+ Days Past Due → at least Doubtful.

#### Watch-List Actions

Map severity to the appropriate action from the template's allowed enum:
- Nonaccrual → legal_referral
- 90+ Days Past Due → workout
- Projected Loss risk class → partial_chargeoff_review
- Doubtful risk class → workout
- Watch risk class → special_assets
- Lower risk classes with elevated current rating → watchlist
- Monitoring cadence: monthly if any Doubtful/Projected Loss, quarterly if any Watch, otherwise semiannual

#### Stress Formulas (`stress` section)

Watch-list parallel shock (+200bp): `stressed_dscr = dscr / (1 + 0.18)`
CRE dual-stress: `stressed_dscr = dscr * 0.85 / (1 + 0.18)`

Coverage breach threshold: 1.0 (stressed DSCR < 1.0 → breach)
Only compute stress for loans with DSCR available.

#### CRE Weighted Score (`cre_weighted_score` section)

Rate each component on a 1-5 scale (1 = best, 5 = worst):
- Capacity (DSCR): ≥1.50→1, ≥1.25→2, ≥1.05→3, ≥1.00→4, <1.00→5
- Capital (debt-to-asset): <0.40→1, ≤0.60→2, ≤0.80→3, ≤1.00→4, >1.00→5
- Character: consider FICO, guarantor strength, relationship tenure, prior delinquencies
- Collateral (LTV): ≤0.65→1, ≤0.75→2, ≤0.85→3, ≤1.00→4, >1.00→5
- Conditions: sector concentration — over limit→4, approaching (>80%)→3, clear→1

Weighted score = 0.45×capacity + 0.03×capital + 0.05×character + 0.36×collateral + 0.11×conditions

Classify: ≤2.0 → approve_quality, ≤3.0 → conditional, >3.0 → weak

#### Sector Concentration

- Each sector has a `limit_pct` from the sector-exposures endpoint (falls back to `branch.sector_ceiling_pct` if not listed)
- Sector limit in dollars = limit_pct × total_loans_outstanding
- Post-approval exposure = current_exposure + requested_amount
- Breach: post-approval exposure > limit in dollars
- For CRE concentration: sum all loans with `loan_type` "CRE" to get existing CRE exposure. Compare to `cre_policy_limit_pct × total_loans_outstanding`

#### NPA Benchmark Comparison

- Branch NPA exposure = sum of outstanding balances for loans with payment_status "Nonaccrual" or "90+ Days Past Due"
- Branch NPA ratio = branch NPA exposure / total_loans_outstanding
- Use FDIC benchmark: `total_loans_noncurrent_pct` for general portfolio, `total_real_estate_noncurrent_pct` for real-estate-heavy portfolios
- Variance ratio = branch ratio − benchmark ratio
- Variance bps = variance ratio × 10000

#### Credit Union Segment Posture

- Pull segment details and NCUA benchmark rows
- Compare the target state to US national and peer-state medians on four metrics: delinquency_bps, loan_to_share_pct, roaa_bps, positive_net_income_pct
- Determine direction (higher/lower/equal) for each comparison
- Use the segment's `internal_context` to identify added controls and escalation triggers
- Map findings to posture: `continue_approving` (strong metrics, capacity available), `continue_with_tighter_conditions` (some concern but capacity remains), `temporarily_pause` (severe issues)

### Data Fetching Checklist

For each task, fetch these endpoints as needed:
- `/api/manifest` — available endpoints and benchmark versions
- `/api/policies` — risk rating rules, CDFI scores, stress formulas, CRE weights, capacity rules
- `/api/branches` — list all branches
- `/api/branches/{branch_id}` — branch details (capacity, limits, state)
- `/api/branches/{branch_id}/metrics` — quarterly metrics (delinquency, NPA, total loans)
- `/api/branches/{branch_id}/loans` — full loan portfolio
- `/api/branches/{branch_id}/sector-exposures` — per-sector exposure and limits
- `/api/branches/{branch_id}/applications` — pending applications
- `/api/benchmarks/fdic/q4-2024` — FDIC benchmark ratios
- `/api/benchmarks/ncua/q1-2025` — NCUA state-level benchmark rows
- `/api/credit-union-segments/{segment_id}` — credit union segment details

### Answer Assembly Rules

- Match the template's required_top_level_keys, required_keys for each object, and field types exactly
- Use only the enum values specified in the template
- Respect ordering rules: ascending/descending as specified for each list
- Round numeric values to the precision specified in the template (dollars to 2 decimals, ratios to 4 decimals, bps to 2 decimals)
- Sort lists by the key specified (loan_id, application_id, sector, final_rating, etc.)
- Include all items in scope, not just problematic ones
- Do not include narrative text outside the JSON
