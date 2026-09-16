---
name: credit-office-committee-json
description: Use this skill whenever a task asks for committee-ready JSON from the shared credit office API, especially prompts mentioning <TASK_ENV_BASE_URL>, branch_id, segment_id, lending committee, credit risk, risk-rating migration, pending application allocation, CRE comparisons, watch-list stress, CDFI scoring, FDIC/NCUA benchmarks, sector exposures, or an answer_template.json.
---

# Credit Office Committee JSON

Use this skill to solve credit-office API tasks that require controlled JSON output. These tasks are calculation-heavy: the main risk is not prose quality, it is missing an endpoint, using the wrong denominator, drifting from the template enum values, or rounding/sorting inconsistently.

## Core Workflow

1. Read the user prompt and `input/payloads/answer_template.json` before calculating.
2. Extract the target identifiers and constraints: `branch_id`, `segment_id`, application IDs, review/as-of date, current-rating cutoff, benchmark family, required output keys, enum choices, precision, and ordering rules.
3. Resolve the API base URL from the runner-provided `<TASK_ENV_BASE_URL>` value, environment variable, or staged environment access file. Use only public API endpoints.
4. Fetch `GET /api/manifest` and `GET /api/policies` first. Then fetch only the target data needed for the prompt:
   - Branch: `/api/branches/{branch_id}`, `/metrics`, `/loans`, `/sector-exposures`, `/applications`
   - Benchmarks: `/api/benchmarks/fdic/q4-2024`, `/api/benchmarks/ncua/q1-2025`
   - Credit-union segment: `/api/credit-union-segments/{segment_id}`
5. Do calculations with code, `jq`, or the bundled helper. Avoid mental arithmetic for ratios, capacity, exposure aggregation, stress results, and score weighting.
6. Shape the result exactly to the answer template. Drop helper-only diagnostic fields unless the template explicitly asks for them.
7. Return only valid JSON. No markdown fences and no explanatory text outside the JSON.

Optional helper:

```bash
python scripts/credit_office_helper.py --base-url "$TASK_ENV_BASE_URL" inventory --branch-id "$BRANCH_ID"
python scripts/credit_office_helper.py --base-url "$TASK_ENV_BASE_URL" rating-migration --branch-id "$BRANCH_ID" --current-rating-min 3 --review-date "$REVIEW_DATE"
python scripts/credit_office_helper.py --base-url "$TASK_ENV_BASE_URL" allocation --branch-id "$BRANCH_ID"
python scripts/credit_office_helper.py --base-url "$TASK_ENV_BASE_URL" watchlist-stress --branch-id "$BRANCH_ID" --adverse-rating-min 6
python scripts/credit_office_helper.py --base-url "$TASK_ENV_BASE_URL" cre-compare --branch-id "$BRANCH_ID" --application-ids APP-1 APP-2
python scripts/credit_office_helper.py --base-url "$TASK_ENV_BASE_URL" cu-posture --segment-id "$SEGMENT_ID"
```

The helper is a worksheet generator, not a substitute for reading the template. Rename generic helper keys to the required template keys, remove diagnostics, enforce enum choices, and re-sort fields/lists as requested.

## Common Rules

- Use the latest branch metric quarter unless the prompt gives a different quarter. Match FDIC and NCUA benchmark versions to the prompt and manifest.
- Treat percentages in templates as ratios unless the template says otherwise. Example: 19% is `0.19`, and basis points are ratio variance times `10000`.
- Round only final reported values: currency to 2 decimals, ratios to 4 decimals, stressed/base DSCR to 2 decimals, weighted CRE scores to 1 decimal, and NCUA integer metrics exactly as reported.
- Respect every ordering rule in the template. Common orders are ascending IDs, ascending rating, ascending action/sector, and descending exposure for workout queues.
- If the template has enum choices, output only those exact strings. When a calculated diagnostic reason is not allowed by the local template, omit it or map it to an allowed reason only if the prompt/template supports that mapping.

## Risk-Rating Migration

Use this pattern for branch loan regrades, rating migration, material downgrades, NPA variance, top problem credit, and watch-list action coverage.

For the target population, filter loans by the prompt's current-rating cutoff, commonly `current_rating >= 3`.

Re-derive each loan's final rating from objective factors:

- DSCR: `>=1.50 -> 3`, `>=1.25 -> 4`, `>=1.05 -> 5`, `>=1.00 -> 6`, `<1.00 -> 7`
- LTV: `<=0.65 -> 3`, `<=0.75 -> 4`, `<=0.85 -> 5`, `<=1.00 -> 6`, `>1.00 -> 7`
- Payment status: `30 Days Past Due -> 4`, `60 Days Past Due -> 5`, `90+ Days Past Due -> 7`, `Nonaccrual -> 8`, `Current -> no delinquency rating`
- Final rating is the worst numeric rating from available factors. If no objective factor is available, fall back to the current rating.

Then compute:

- Final-rating exposure totals from outstanding balance, grouped by final rating.
- Migration from the specified current rating to each final rating, with sorted loan IDs.
- Material downgrades where `final_rating - current_rating >= policies.risk_rating.material_downgrade_notches`.
- Watch-list/action coverage for loans needing follow-up after regrade. A practical mapping is final 6 to `watchlist`, final 7 or 90+ past due to `special_assets`, and final 8/Nonaccrual/projected loss to `partial_chargeoff_review`.
- NPA benchmark variance from latest `metrics.nonperforming_loans / metrics.total_loans_outstanding` against the requested FDIC benchmark metric.
- Top problem credit by highest final rating, then largest exposure, with borrower, payment status, and recommended action.

## Watch-List Stress And Workout

Use this pattern for adversely rated loans, CDFI-style risk classes, +200bp stress packets, workout queues, and severe bucket counts.

Filter adverse loans by the prompt's cutoff, commonly `current_rating >= 6`.

Compute CDFI factor score by summing available policy factors:

- FICO: `>720 -> 0`, `680-720 -> 1`, `580-679 -> 3`, `<580 -> 5`
- LTV: `<0.40 -> 0`, `0.40-0.60 -> 2`, `0.60-0.80 -> 4`, `>0.80 -> 6`
- Liquidity months: `>12 -> 0`, `6-12 -> 1`, `3-6 -> 3`, `<3 -> 5`
- Debt-to-asset: `<0.40 -> 0`, `0.40-0.60 -> 2`, `0.60-0.80 -> 4`, `>0.80 -> 6`

Classify scores as `Prime` for 0-5, `Desirable` for 6-9, `Satisfactory` for 10-13, `Watch` for 14-18, and `Doubtful` for 19+. Use `Projected Loss` for severe underwater/nonaccrual cases when objective factors indicate loss exposure.

For watch-list stress, use the policy formula `stressed_dscr = dscr / (1 + 0.18)` for loans with DSCR available. The breach threshold is usually `1.00`; breach means stressed DSCR is below the threshold.

Workout queues should include the adverse population unless the prompt narrows it. Sort by descending exposure, then loan ID. Severe bucket counts group by `current_rating` and `payment_status`.

## Pending Application Allocation

Use this pattern for lending capacity, application decisions, concentration flags, decline reasons, and post-approval concentration views.

Fetch branch details, latest metrics, pending applications, sector exposures, policies, and any benchmark the prompt names.

Apply these controls in order:

1. Identify hard policy weaknesses from application fields: missing documentation, recent bankruptcy, low FICO, weak DSCR, high LTV, underwater collateral, startup risk, and capacity/sector breach.
2. Use SBA guaranty and participation as mitigants when the template allows `sba_guaranty_required` or `participation_required`.
3. Bank capacity used is the retained bank exposure, not always the full approved amount. For SBA, use `requested_amount * (1 - sba_guaranty_pct)`. For participation, cap retained exposure at the amount that keeps the relevant sector within its limit.
4. Gross approved amount is the full amount approved for borrowers, including participated or SBA-guaranteed portions. Committed capacity is retained bank exposure.
5. Existing sector exposure denominator should reconcile to latest total loans. For post-approval concentration views, use existing total exposure plus gross approved amount, then compute each reported sector as `(current_exposure + gross approvals in sector) / post_total`.
6. Flag sectors that breach or sit at the ceiling after approval, and set handling to the mitigation/decision path.

Decline reason codes should be controlled by the template. Typical mappings are weak DSCR, high LTV, low FICO, recent bankruptcy, startup risk, documentation gap, sector breach, and capacity limit.

## Competing CRE Decisions

Use this pattern for two CRE applications compared on weighted CDFI score, stressed repayment coverage, CRE concentration, FDIC underperformance, recommended path, and conditions.

Fetch the selected applications, branch, latest metrics, loans, sector exposures, FDIC benchmark, and policies. Existing CRE exposure is the sum of current loans with `loan_type == "CRE"`, not a broad sector-name guess.

Compute:

- Existing CRE concentration: `existing_cre_exposure / latest_total_loans`.
- Selected post-approval CRE concentration: `(existing_cre_exposure + selected_requested_amount) / (latest_total_loans + selected_requested_amount)`.
- CRE policy variance bps: `(selected_post_concentration - branch.cre_policy_limit_pct) * 10000`.
- FDIC adverse variance using the prompt's FDIC metric, commonly `total_real_estate_30_89_pct`, against `metrics.delinquency_30_plus_pct`.
- CRE dual stress from policy: `stressed_dscr = dscr * 0.85 / (1 + 0.18)`.
- Weighted CDFI score using `policies.cre_weighted_score.weights`. Lower is better. Use objective sub-scores for capacity/DSCR, capital/debt-to-asset, character/guarantor and delinquency history, collateral/LTV and exposure, and conditions/market or concentration stress.

Reason codes usually include `fdic_adverse_variance` when branch delinquency materially exceeds the FDIC benchmark, `sector_breach` when CRE or sector concentration exceeds policy, and `weak_dscr` when stressed DSCR breaches threshold. Select the stronger application by lower weighted score and stress resilience; use participation or conditional approval when concentration risk requires mitigation.

## Credit-Union Segment Posture

Use this pattern for NCUA benchmark posture, peer-state comparisons, controls, triggers, and interpretation.

Fetch the segment and NCUA Q1 2025 benchmark table. Use the segment's `state_code`, `peer_states`, `quarterly_capacity`, `minimum_checklist`, `risk_tolerance`, and `internal_context`.

Report state metrics exactly as the NCUA row provides them. Compare the target state to `US` and to the median of peer states for delinquency, loan-to-share, ROAA, and positive net income. Use `higher`, `lower`, or `equal`.

Posture and interpretation should connect capacity and external risk:

- Capacity above zero supports `capacity_available`; no remaining capacity supports `no_capacity`.
- Higher delinquency/loan-to-share with lower ROAA/positive net income than national and peers indicates `weaker_than_national_and_peers`.
- If capacity is available but external or internal controls are weaker, prefer a tighter-conditions posture rather than a pause.
- Required checklist gates come from the segment. Add operating controls for insurance/lien issues, second review, state benchmark monitoring, segment delinquency watch, and capacity exceptions when those risks appear in segment context.

Escalation triggers should use only template enum values and owners. Keep trigger IDs sorted and stable.

## Final Validation

Before answering:

- Parse your final JSON locally with `python -m json.tool`.
- Confirm all required top-level keys and nested required keys from the template are present.
- Confirm no diagnostic-only fields remain.
- Confirm all lists are sorted exactly as requested.
- Confirm all numeric precision matches the template.
- Confirm all enum strings are copied exactly from the template.
