# Credit Office Committee JSON Skill

Use this skill for Credit Office / lending committee tasks that ask for a JSON answer over the public credit office API.

## Ground Rules

- Use only the task prompt, its `input/payloads/answer_template.json`, and the public API described by `environment_access.md`.
- Do not inspect local environment source/data, train outputs, test files, notes, prior runs, reports, other attempts, or judge endpoints.
- Prefer the remote public API directly. In this workspace the base URL is `<environment_base_url>`.
- Return exactly one valid JSON object. Do not add prose around it.
- Treat `answer_template.json` as the contract: required keys, enum spellings, ordering, and precision rules override intuition.

## API Workflow

1. Read the prompt for target ids, review/as-of date, benchmark family, and requested analysis.
2. Read the answer template and list every required key, enum, sort order, and rounding instruction.
3. Fetch `/api/manifest` and `/api/policies` first to confirm policy and benchmark versions.
4. Fetch only the public records needed:
   - Branch base data: `/api/branches/{branch_id}`
   - Metrics: `/api/branches/{branch_id}/metrics`
   - Loans: `/api/branches/{branch_id}/loans`
   - Sector exposure: `/api/branches/{branch_id}/sector-exposures`
   - Applications: `/api/branches/{branch_id}/applications`
   - FDIC benchmark: `/api/benchmarks/fdic/q4-2024`
   - NCUA benchmark: `/api/benchmarks/ncua/q1-2025`
   - Credit-union segment: `/api/credit-union-segments/{segment_id}`
5. Compute with a script or structured JSON tooling, then validate the final object against the template before answering.

## Field Conventions

- Loan exposure is `outstanding_balance`.
- Application exposure/capacity use is usually `requested_amount`, unless the decision explicitly reduces or participates the amount.
- Branch capacity is `lending_capacity_q1`.
- Branch sector limits come from `sector-exposures.limit_pct`; fall back to `branches.sector_ceiling_pct` only if no sector-specific row exists.
- CRE policy limit is `branches.cre_policy_limit_pct`.
- Metrics rows use `quarter`, not an `as_of_date`; select the row matching the review quarter.
- In metrics, map `nonperforming_loans` to NPA exposure and `total_loans_outstanding` to total loans.
- Ratios are decimals, not percentages. Basis points are `ratio * 10000`.
- Currency is rounded to 2 decimals. Ratio fields usually round to 4 decimals. DSCR fields usually round to 2 decimals. Weighted CRE score rounds to 1 decimal.

## Rating Migration Tasks

For regrading loans, filter the exact population requested, commonly loans with `current_rating >= target_min`.

Apply the policy `risk_rating` dominant-factor rule: final rating is the worst numeric rating from available DSCR, LTV/collateral, and delinquency factors.

- DSCR rating: `>=1.50 -> 3`, `>=1.25 -> 4`, `>=1.05 -> 5`, `>=1.00 -> 6`, `<1.00 -> 7`.
- LTV rating: `<=0.65 -> 3`, `<=0.75 -> 4`, `<=0.85 -> 5`, `<=1.00 -> 6`, `>1.00 -> 7`.
- Delinquency minimum: `30 Days Past Due -> 4`, `60 Days Past Due -> 5`, `90+ Days Past Due -> 7`, `Nonaccrual -> 8`, `Current -> no floor`.
- Material downgrade is `final_rating - current_rating >= material_downgrade_notches`.

Aggregate exposure by final rating, sort ascending by rating, and sort loan ids ascending where requested. For NPA benchmark variance, use:

- `branch_npa_ratio = nonperforming_loans / total_loans_outstanding`
- `variance_ratio = branch_ratio - fdic_benchmark_ratio`
- `variance_bps = variance_ratio * 10000`

Choose problem-credit and watch-list actions from the template enums only. Tie severity to final rating, payment status, projected loss/collateral weakness, and exposure.

## Watch-List Stress Tasks

Adverse-rated watch lists usually mean loans with `current_rating >= 6` unless the prompt gives another threshold.

For CDFI factor scoring, sum the available policy scores for `fico`, `ltv`, `liquidity_months`, and `debt_to_asset`.

- Classes: `Prime` 0-5, `Desirable` 6-9, `Satisfactory` 10-13, `Watch` 14-18, `Doubtful` 19+, and `Projected Loss` when score is 19+ and `ltv > 1.0`.
- Use only the risk class enum in the template.
- If DSCR is missing, omit that loan from DSCR stress results but keep it in population and workout aggregates.
- Watch-list stress formula: `stressed_dscr = dscr / (1 + 0.18)`.
- Breach threshold is the policy `coverage_breach_threshold`, normally `1.00`.

Workout queues are typically sorted by descending exposure, then ascending loan id. Severe bucket counts group by `current_rating` and `payment_status`, sorted as the template requires.

## Application Allocation Tasks

For pending-application packages:

- Fetch branch, sector exposures, and all pending applications for the target branch.
- Evaluate application-level policy issues: DSCR, LTV, FICO, recent bankruptcy, startup risk, documentation, SBA guaranty, capacity, and sector concentration.
- Keep decisions and conditions to template enums exactly.
- Capacity math:
  - `gross_approved_amount` is total approved or conditionally approved face amount.
  - `committed_capacity_amount` is the bank-retained amount after reductions or participation.
  - `remaining_capacity = lending_capacity_q1 - committed_capacity_amount`.
- Sector post-approval concentration:
  - `exposure_after_approval = current_exposure + bank_capacity_used for that sector`
  - `post_approval_pct = exposure_after_approval / total_assets`
  - compare to the sector-specific `limit_pct`.
- Existing over-ceiling exposure can be grandfathered, but a new approval should not worsen it without mitigation.
- Sort decisions by `application_id`, concentration flags by sector then `application_id`, post-approval concentrations by sector, and reason-code lists alphabetically.

## Competing CRE Decision Tasks

When comparing named CRE applications, filter the application list to the exact ids in the prompt.

- Use policy `cre_weighted_score.weights`: capacity `.45`, capital `.03`, character `.05`, collateral/exposure `.36`, conditions `.11`.
- Lower weighted score is better. Classify by policy: `approve_quality <= 2.0`, `conditional <= 3.0`, `weak > 3.0`.
- If component scores are not explicit fields, derive them transparently from objective application factors: DSCR for capacity, debt-to-assets/net income for capital, relationship/delinquency/bankruptcy for character, LTV/collateral for collateral exposure, and documentation/concentration/benchmark environment for conditions.
- CRE stress formula: `stressed_dscr = dscr * 0.85 / (1 + 0.18)`.
- Use the policy coverage breach threshold, normally `1.00`.
- CRE concentration after selecting an application:
  - existing CRE exposure comes from existing CRE/CRE-like sector exposure as requested by the prompt.
  - post-approval concentration adds the selected bank-retained amount and divides by `total_assets`.
  - policy variance bps is `(post_approval_concentration - cre_policy_limit_pct) * 10000`.
- FDIC 30-89 or noncurrent benchmark variance uses `branch_ratio - benchmark_ratio`; keep the exact metric enum from the template.

## Credit-Union Segment Posture Tasks

For segment posture pages:

- Fetch the segment endpoint, policies, manifest, and NCUA benchmark table.
- Use the segment `state_code`, `peer_states`, `quarterly_capacity`, `current_outstanding`, `risk_tolerance`, `minimum_checklist`, notes, and `internal_context`.
- State metrics come directly from the NCUA row for the segment state; do not convert bps or integer percentages unless the template says to.
- Peer comparison directions are relative to US and to the median of named peer states. Return only `higher`, `lower`, or `equal`.
- Required checklist gates should include the segment minimum checklist, restricted to template choices.
- Added operating controls should respond to the actual context: insurance/lien gaps, elevated delinquency, capacity exceptions, staffing/second review, or benchmark monitoring.
- Escalation triggers must use allowed trigger ids/conditions/owners only and be sorted ascending by `trigger_id`.
- Match posture and interpretation enums to the evidence: capacity availability, external risk status, and risk tolerance.

## Final QA Checklist

- All required top-level keys are present and no narrative text is outside the JSON.
- Every enum value is copied exactly from the template.
- Every list follows the requested ordering.
- Currency, ratios, DSCRs, scores, and bps use the requested precision.
- Benchmark versions and policy versions come from the API, not memory.
- Denominators are correct: total assets for concentration, total loans outstanding for NPA ratios, and capacity for allocation.
- Nulls, missing DSCR values, and missing FICO values are handled deliberately rather than coerced to zero.
- The answer contains no training-output values or test-answer leakage.
