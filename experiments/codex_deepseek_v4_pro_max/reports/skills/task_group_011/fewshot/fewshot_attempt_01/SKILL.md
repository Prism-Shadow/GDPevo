---
name: credit-risk-committee
description: Produce committee-ready credit risk analysis reports using the shared credit office API. Covers rating migration, lending allocation, segment posture, watch-list stress, and competing CRE decisions.
synopsis: Credit risk committee analysis using shared credit office REST API with FDIC/NCUA benchmarks and controlled output templates.
---

# Credit Risk Committee Skill

## Purpose

Generate committee-ready JSON answers for branch-level credit risk analyses (rating migration, lending allocation, segment posture, watch-list stress, or competing CRE decisions) by calling the shared credit office REST API, applying controlled business-logic formulas, and conforming to supplied answer templates.

## Environment

The shared credit office API base URL is injected at runtime as the shell variable `TASK_ENV_BASE_URL`. Every analysis starts by reading that variable and constructing fully qualified endpoint URLs.

```bash
BASE="${TASK_ENV_BASE_URL}"   # e.g. http://task-env:9011/
```

The API requires no credentials (public routes only).

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/manifest` | Lists all branches and segment IDs available. |
| GET | `/api/policies` | Credit policies with sector limits, rating thresholds, capacity rules, CRE/construction caps, concentration limits, and LTV/DSCR floors. |
| GET | `/api/benchmarks/fdic/q4-2024` | FDIC Q4 2024 industry benchmark ratios (noncurrent, delinquency, charge-off, etc.). |
| GET | `/api/benchmarks/ncua/q1-2025` | NCUA Q1 2025 credit-union benchmark table: state-level delinquency, loan-to-share, ROAA, and positive-net-income percentages. |
| GET | `/api/branches` | Collection of all branches with metadata. |
| GET | `/api/branches/{branch_id}` | Single branch detail. |
| GET | `/api/branches/{branch_id}/metrics` | Branch-level financial metrics: total loans, NPA exposure, CRE exposure, capacity values, delinquency ratios, rating distributions. |
| GET | `/api/branches/{branch_id}/loans` | All loans for a branch. Each loan has `loan_id`, `current_rating` (1–8), `exposure`, `payment_status`, `sector`, `ltv`, `dscr`, `fico`, and risk-factor fields. |
| GET | `/api/branches/{branch_id}/sector-exposures` | Sector-level exposures and concentration percentages. |
| GET | `/api/branches/{branch_id}/applications` | Pending credit applications with `application_id`, `requested_amount`, `sector`, `dscr`, `ltv`, `fico`, `cdfi_score`, and risk flags. |
| GET | `/api/credit-union-segments/{segment_id}` | Credit-union segment detail including capacity, state association, and historical delinquency data. |

Substitute `{branch_id}` and `{segment_id}` with the identifiers given in the task prompt.

## General Workflow

1. **Read the prompt** for the task type, target identifier (`branch_id` or `segment_id`), review date, and any task-specific parameters (e.g. application IDs to compare).
2. **Read the answer template** from the payload directory (`input/payloads/answer_template.json`). The template defines all required keys, enum choices, ordering rules, and numeric precision.
3. **Fetch data** from all relevant API endpoints for the given branch or segment. Include `/api/policies` and the appropriate benchmark endpoint whenever ratios or caps are needed.
4. **Apply business logic** (see task-type sections below) to derive computed fields from raw API data.
5. **Sort and format** every list per the template ordering rules.
6. **Return only valid JSON** matching the template shape. No narrative text outside the JSON.

## Numeric Precision & Ordering Conventions

- Currency amounts (USD): round to 2 decimal places.
- Ratios/concentrations: round to 4 decimal places.
- BPS (basis points): round to 2 decimal places.
- Integer fields: use exact integer values.
- Lists: sort according to the ordering key specified per field in the template. When not otherwise specified, sort IDs and codes ascending.

## Task Type A — Rating Migration Review

**Typical prompt keywords:** rating migration, regrade, watch-list, NPA benchmark, problem credit.

### APIs to Call

- `GET /api/branches/{branch_id}`
- `GET /api/branches/{branch_id}/metrics`
- `GET /api/branches/{branch_id}/loans`
- `GET /api/policies`
- `GET /api/benchmarks/fdic/q4-2024`

### Business Logic

**Regrade population.** Select every loan whose `current_rating` is at or above the threshold specified in the prompt (typically `>= 3`). Record the count (`target_loan_count`) and sum of exposures (`target_exposure`). Re-derive each loan's rating using the policies endpoint's rating matrix: apply objective risk factors (LTV, DSCR, FICO, payment status, collateral position) to determine a `final_rating`. The final rating is never better than the current rating for loans in the regrade population; it can only stay the same or worsen.

**Final rating totals.** Group all regraded loans by `final_rating`. Sum loan counts and exposures per rating bucket. Sort by `final_rating` ascending.

**Rating migration from a specific starting rating.** Take the subset of loans whose `current_rating` equals the migration origin (e.g. 3). For those that migrated to a worse rating, group by `final_rating`, summing counts, exposures, and collecting `loan_id` lists. Sort by `final_rating` ascending.

**Watch-list action coverage.** Map final ratings to watch-list actions using the policy-defined thresholds:
- `final_rating == 8`: `partial_chargeoff_review`
- `final_rating == 7`: `special_assets`
- `final_rating == 6`: `watchlist`

Compute `covered_loan_count` and `covered_exposure` as the totals for all loans assigned an action. Group by action and collect `loan_ids` per action. Sort by action name ascending.

**NPA benchmark.** From branch metrics, take `npa_exposure` and `total_loans`. Compute `branch_npa_ratio = npa_exposure / total_loans`. From the FDIC Q4 2024 benchmark, look up `total_loans_noncurrent_pct` and convert from percentage to ratio (`benchmark_pct / 100`). Compute `variance_ratio = branch_npa_ratio - fdic_benchmark_ratio` and `variance_bps = variance_ratio * 10000`.

**Material downgrades.** A downgrade is "material" when `final_rating - current_rating >= 2`. List each such loan with `loan_id`, `current_rating`, `final_rating`, `downgrade_notches` (the difference), and `exposure`. Sort by `exposure` descending.

**Top problem credit.** Select the single most severe loan: the nonaccrual loan with the worst (highest) `final_rating` and the largest `exposure` among ties. Include `loan_id`, `borrower_name`, `exposure`, `current_rating`, `final_rating`, `payment_status`, and `recommended_action` (from watch-list mapping).

## Task Type B — Lending Committee Allocation

**Typical prompt keywords:** allocation, lending capacity, priority ranking, decisions, concentration flags.

### APIs to Call

- `GET /api/branches/{branch_id}`
- `GET /api/branches/{branch_id}/metrics`
- `GET /api/branches/{branch_id}/applications`
- `GET /api/branches/{branch_id}/sector-exposures`
- `GET /api/policies`

### Business Logic

**Lending capacity.** From branch metrics, read `lending_capacity_q1` (or derive from `total_loans * capacity_ratio` from policies).

**Application scoring and ranking.** Score each application using policy-driven factors:
- CDFI score from the application data.
- LTV: penalize if above policy threshold (typically 0.80).
- DSCR: penalize if below policy threshold (typically 1.25).
- FICO: penalize if below policy floor.
- Flags: `recent_bankruptcy`, `startup_risk` are hard declines.

Applications with hard-decline flags are excluded from the priority ranking. Remaining applications are ranked by a composite score (higher CDFI score = more desirable, with credit-metric tiebreakers).

**Decision logic — Approve.** Assign `approve` when:
- All credit metrics pass policy floors (LTV <= cap, DSCR >= floor, FICO >= floor).
- Capacity is available (`remaining_capacity >= requested_amount`).
- No sector-concentration breach.

**Decision logic — Conditional Approve.** Assign `conditional_approve` when the credit is otherwise sound but a policy exception is needed:
- Sector concentration would exceed the policy limit → `participation_required`.
- Startup risk with acceptable metrics → `startup_monitoring`.
- SBA-eligible → `sba_guaranty_required`.

**Decision logic — Decline.** Assign `decline` with reason codes when:
- LTV exceeds the policy cap.
- DSCR falls below the policy floor.
- FICO falls below the policy floor.
- `recent_bankruptcy` or other hard-decline flag is present.
- Remaining capacity is exhausted for lower-priority applications.

Use only the enum reason codes from the template.

**Allocation totals.** Compute:
- `gross_approved_amount`: sum of `approved_amount` across all decisions.
- `committed_capacity_amount`: sum of `bank_capacity_used` across all decisions.
- `remaining_capacity`: `lending_capacity_q1 - committed_capacity_amount`.
- `priority_ranking`: ordered list of application IDs for approved and conditionally approved applications, highest priority first.

**Concentration flags.** For each sector that has a policy limit, compute `post_approval_pct` after adding approved application exposures. Set `flag: true` when `post_approval_pct > limit_pct`. Set `handling` to `participation_required` when flagged near the limit.

**Post-approval concentrations.** For each sector, report the final `exposure_after_approval`, `post_approval_pct`, `limit_pct`, and `over_limit` boolean.

## Task Type C — Credit Union Segment Posture

**Typical prompt keywords:** segment, posture, credit union, NCUA, peer comparison, controls, escalation.

### APIs to Call

- `GET /api/manifest`
- `GET /api/policies`
- `GET /api/benchmarks/ncua/q1-2025`
- `GET /api/credit-union-segments/{segment_id}`

### Business Logic

**State metrics.** From the NCUA Q1 2025 benchmark table for the state indicated by the segment (derived from segment name or data), extract: `delinquency_bps`, `loan_to_share_pct`, `roaa_bps`, `positive_net_income_pct`. Use exact integer values from the benchmark.

**Peer comparison.** Select the three geographically adjacent states named in the prompt as peer states (sort ascending). Compare the target state to:
- **National (US) aggregates:** report direction (`higher`/`lower`/`equal`) for each of the four metrics.
- **Peer median:** compute the median of the peer states' values for each metric; report direction relative to the target state.

**Posture recommendation.** Choose one of:
- `continue_approving`: state metrics are at or better than national/peer benchmarks, segment capacity is healthy.
- `continue_with_tighter_conditions`: state metrics are weaker than national/peer benchmarks but capacity is still available; add operating controls.
- `temporarily_pause`: state delinquency is critically elevated and capacity is constrained.

**Controls — required checklist gates.** Select from the template enum. Standard gates include:
- `board_authorization`
- `equipment_invoice`
- `public_contract_or_tax_support`
- `proof_of_insurance`
- `ucc_or_title_lien`

**Controls — added operating controls.** When posture is `continue_with_tighter_conditions`, add:
- `lien_perfection_prior_to_funding`
- `monthly_segment_delinquency_watch`
- `pre_close_insurance_binder_verification`
- `quarterly_state_benchmark_monitoring`
- `senior_underwriter_second_review`

**Escalation triggers.** Define 2–3 triggers with unique IDs (`ET001`, `ET002`, …), a condition from the template enum, and an owner role. Typical triggers:
- Delinquency >= 90 bps → `credit_risk_manager`
- Missing insurance or lien exception → `operations_control_manager`
- Quarterly capacity exceeded → `lending_committee_chair`

**Interpretation block.** Provide controlled values:
- `capacity_status`: from the segment endpoint (capacity field or derived).
- `external_risk_status`: derived from peer comparison directions.
- `risk_tolerance`: `moderate` when weaker-than-peers but capacity available; `restrained` when capacity constrained; `expansive` when stronger-than-peers.
- `committee_message`: choose from the template enum reflecting the overall posture.

## Task Type D — Watch-List Stress & Workout

**Typical prompt keywords:** watch-list, stress, DSCR, adverse rating, workout, severe buckets.

### APIs to Call

- `GET /api/branches/{branch_id}`
- `GET /api/branches/{branch_id}/metrics`
- `GET /api/branches/{branch_id}/loans`
- `GET /api/policies`

### Business Logic

**Adverse-rated population.** Select loans with `current_rating` >= the adverse threshold (typically 6). Compute `adverse_loan_count` and `adverse_balance` (sum of exposures).

**CDFI risk class assignment.** For each adverse loan, compute a factor score from objective loan fields (payment status delinquency level, LTV, DSCR, FICO, collateral type). Map the factor score to a risk class:
- Score 0–5: `Prime`
- Score 6–10: `Desirable`
- Score 11–14: `Satisfactory`
- Score 15–18: `Watch`
- Score 19–22: `Doubtful`
- Score 23+: `Projected Loss`

Sort by `loan_id` ascending. Set `monitoring_cadence` to `monthly` (standard for adverse-rated credits).

**DSCR stress test.** For each adverse loan where DSCR data is available:
- Apply the `+200bp` shock: `stressed_dscr = base_dscr - 0.15`.
- Compare against `breach_threshold = 1.0`. A loan breaches when `stressed_dscr < 1.0`.
- Collect the subset of `loan_id` values that breach into `breach_loan_ids`, sorted ascending.

**Workout queue.** Construct a priority queue of adverse-rated loans that require action. Sort by `exposure` descending, then `loan_id` ascending. For each entry include `loan_id`, `exposure`, `risk_class` (from CDFI assignment), `payment_status`, `recommended_action` (mapped from payment_status + risk_class), and `projected_loss` (`true` only for "Projected Loss" risk class).

Action mapping:
- `Nonaccrual` + `Projected Loss` → `partial_chargeoff_review`
- `90+ Days Past Due` → `special_assets`
- `Current` + `Watch`/`Doubtful` → `special_assets`
- `Current` + `Desirable`/`Satisfactory` → `watchlist`

**Severe bucket counts.** For loans with `current_rating` in the severe range (6–8), group by `(current_rating, payment_status)`. Sum `loan_count` and `exposure` per bucket. Sort by `current_rating` ascending, then `payment_status` ascending (e.g. "Current" before "90+ Days Past Due" before "Nonaccrual").

## Task Type E — Competing CRE Decision

**Typical prompt keywords:** competing CRE, applications to compare, weighted CDFI score, stressed repayment, concentration, conditions.

### APIs to Call

- `GET /api/branches/{branch_id}`
- `GET /api/branches/{branch_id}/metrics`
- `GET /api/branches/{branch_id}/applications`
- `GET /api/branches/{branch_id}/loans`
- `GET /api/branches/{branch_id}/sector-exposures`
- `GET /api/policies`
- `GET /api/benchmarks/fdic/q4-2024`

### Business Logic

**Weighted CDFI scoring.** For each application, the `weighted_cdfi_score` is a composite of the application's CDFI score adjusted by policy weightings for the CRE asset class. Derive `score_class`:
- Score 0.0–2.99: `strong`
- Score 3.0–3.99: `conditional`
- Score 4.0+: `weak`

**Decision per application.** Map score class to decision:
- `strong` → `approve`
- `conditional` → `participation_required` (or `conditional_approve` if no concentration breach)
- `weak` → `defer`

Assign `reason_codes` for any application that is not a clean approval. Sort alphabetically.

**Recommended path.** Select the stronger application (lower weighted CDFI score = better) as `selected_application_id`. Set its `path`. The unselected application gets `unselected_disposition: "defer"` with its `unselected_reason_codes` (alphabetically sorted).

**CRE DSCR stress.** Apply the dual-stress formula: `stressed_dscr = base_dscr * 0.85 / 1.18`. Set `coverage_breach_threshold = 1.0`. For each application, compute `stressed_dscr` and flag whether it breaches. Sort results by `application_id` ascending.

**Concentration analysis.** From policies, extract `cre_policy_limit_pct` (the CRE concentration cap as a ratio). From branch metrics/sector-exposures, compute:
- `existing_cre_exposure`: total CRE loan exposure.
- `existing_cre_concentration`: `existing_cre_exposure / total_loans`.
- `selected_post_approval_cre_concentration`: `(existing_cre_exposure + selected_application_amount) / total_loans`.
- `selected_policy_variance_bps`: `(selected_post_approval_cre_concentration - cre_policy_limit_pct) * 10000`.
- FDIC benchmark: look up `total_real_estate_30_89_pct` delinquency ratio, compare with branch CRE delinquency.
- `fdic_variance_ratio`: `branch_delinquency_ratio - fdic_benchmark_ratio`.
- `fdic_variance_bps`: `fdic_variance_ratio * 10000`.

**Conditions.** When the selected path requires conditions, choose from the template enum. Standard CRE conditions include:
- `bank_retained_exposure_cap`
- `committee_cre_exception`
- `minimum_dscr_covenant_1_25`
- `no_additional_cre_without_committee_review`
- `quarterly_financial_reporting`
- `tenant_roll_and_lease_review`
- `updated_appraisal_before_close`

Sort alphabetically.

## Answer Template Compliance

Every task supplies an answer template at `input/payloads/answer_template.json`. The template is authoritative for:
- Required top-level keys and their types.
- Nested required keys per object.
- Enum values for every controlled field.
- List ordering rules.
- Numeric precision.

Before writing the final answer, validate that:
1. Every required key is present.
2. Every list is sorted per the template ordering rule.
3. Every enum value matches the template's allowed values.
4. Numeric precision matches the template specification.

## Common Pitfalls

- **Computing ratios from percentages:** Benchmarks often report percentages (e.g. `0.98` meaning 0.98%). Convert by dividing by 100 before comparing with branch ratios.
- **Sort order:** Check each list's ordering rule in the template; some sort by a numeric key ascending, others by ID ascending, others by exposure descending.
- **Enum casing:** Template enum values use `snake_case`. Do not invent values outside the template's allowed lists.
- **Missing data:** Some loans lack DSCR data. Exclude them from stress results rather than fabricating values. Include only loans with available DSCR in stress arrays.
- **BPS conversion:** 1 basis point = 0.0001 as a ratio. Multiply a ratio by 10000 to get bps.
