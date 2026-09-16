---
name: credit-risk-committee
description: >
  Prepare credit risk committee deliverables from the shared credit office API.
  Use this skill whenever the task involves a credit-risk committee review,
  branch loan portfolio analysis, risk-rating migration review, lending-committee
  allocation package, credit-union segment posture page, watch-list stress
  packet, CRE competing-credit decision, FDIC or NCUA benchmark comparison,
  CDFI-style risk classification, DSCR stress testing, concentration-limit
  checks, or any committee-ready credit memo. The skill encodes the full policy
  framework and API surface; always load it before computing committee outputs.
---

# Credit Risk Committee Analyst

This skill prepares committee-ready JSON deliverables for a shared credit
office. Every task follows the same core pattern: fetch API data, apply the
policy rules encoded in the references, and produce valid JSON conforming
exactly to the provided answer template.

## Core workflow

1. Read `input/payloads/answer_template.json` to learn the exact output shape,
   enum values, ordering rules, and precision requirements.
2. Fetch the API manifest at `<TASK_ENV_BASE_URL>/api/manifest` to confirm
   available benchmark versions and record counts.
3. Fetch credit policies at `<TASK_ENV_BASE_URL>/api/policies`. These encode
   risk-rating thresholds, CDFI factor scores, CRE weighted-scoring weights,
   stress formulas, and capacity/concentration rules. The references/policies.md
   document reproduces these rules for quick lookup during computation.
4. Fetch branch-level data at the relevant endpoints (branch details, metrics,
   loans, sector-exposures, applications).
5. Fetch benchmark data (FDIC or NCUA) when the task references benchmarks.
6. For credit-union tasks, fetch the segment endpoint.
7. Apply the policy rules step by step and populate the answer template.
8. Output **only** valid JSON conforming to the template. No narrative text
   outside the JSON.

## Task archetypes

The API supports five committee-product archetypes. Match the task to the
closest archetype and follow its computation guide.

### 1. Rating migration review (branch portfolio regrade)

Re-derive risk ratings for a filtered loan population, summarize migration,
compute NPA benchmark variance, and flag material downgrades and the top
problem credit.

**Fetch:** branch, branch loans, branch metrics, policies, FDIC benchmark.

**Computation steps:**

1. Filter loans to the target rating floor (e.g. current_rating >= 3).
2. For each loan, re-derive the rating from three factors (see
   [references/policies.md](references/policies.md) -- "Risk Rating Rules"):
   - **DSCR-based rating** from dscr_thresholds.
   - **LTV-based rating** from ltv_thresholds.
   - **Delinquency-based rating** from delinquency_minimums (skip if Current).
   - **Final rating** = worst (highest numeric) of the available factor ratings.
3. Compute `final_rating_exposure_totals`: group loans by final_rating, sum
   loan_count and exposure, sort ascending by final_rating.
4. Compute `migration_from_current_rating_3`: subset of loans whose
   current_rating equals the exact floor (e.g. 3), grouped by final_rating,
   sorted ascending.
5. **Material downgrade**: a loan whose final_rating minus current_rating >=
   `material_downgrade_notches` (2). List them sorted ascending by loan_id.
6. **NPA benchmark**: NPA exposure = sum of outstanding_balance for loans with
   payment_status Nonaccrual or final_rating >= 8. Compute branch NPA ratio as
   NPA exposure / total_loans_outstanding. Compare against the FDIC
   `total_loans_noncurrent_pct`. Variance = branch ratio - benchmark ratio.
   Variance in bps = variance * 10000. Round to 2 decimal places.
7. **Top problem credit**: the loan with the worst combination of final_rating
   and exposure. Among loans with the worst final_rating, pick the highest
   exposure.
8. **Watch-list action coverage**: assign a recommended action to loans needing
   follow-up after regrade. Loans with final_rating 7 that are 90+DPD or
   Nonaccrual -> `special_assets`. Loans with final_rating 8 ->
   `partial_chargeoff_review`. Loans with final_rating 6 -> `watchlist`. Loans
   with final_rating 7 and payment_status Current -> `special_assets`. See
   [references/reason_codes.md](references/reason_codes.md) for the full
   action-assignment rules. Group covered loans by action, sorted ascending by
   action.

### 2. Lending-committee allocation package

Allocate a branch's quarterly lending capacity across pending applications,
identify concentration flags, and report post-approval sector concentrations.

**Fetch:** branch, branch metrics, branch sector-exposures, branch applications,
policies.

**Computation steps:**

1. Read `lending_capacity_q1` from branch details.
2. Read all pending applications for the branch. Prioritize by risk quality:
   applications with stronger metrics (higher DSCR, lower LTV, higher FICO,
   longer relationship) rank higher. Approved and conditionally approved
   applications appear in `priority_ranking`.
3. For each application, decide: approve (fully within capacity and no policy
   issues), conditional_approve (needs mitigation like participation or SBA
   guaranty), decline (hard policy failures), or defer.
4. `bank_capacity_used` for a participation_required application = the bank's
   retained portion (approved_amount minus the participation share). For
   sba_guaranty_required, the SBA-guaranteed portion does not consume bank
   capacity.
5. `gross_approved_amount` = sum of approved_amount for approve +
   conditional_approve decisions. `committed_capacity_amount` = sum of
   bank_capacity_used for those same decisions. `remaining_capacity` =
   lending_capacity_q1 - committed_capacity_amount.
6. **Concentration flags**: for each sector with a pending application, compute
   post_approval_pct = (existing sector exposure + approved_amount) /
   total_loans_outstanding. Compare against the sector's limit_pct from the
   sector-exposures endpoint. Flag true when post_approval_pct > limit_pct.
   Set handling per [references/reason_codes.md](references/reason_codes.md).
7. **Decline reasons**: assign controlled reason codes from the template's enum
   per the rules in [references/reason_codes.md](references/reason_codes.md).
8. **Post-approval concentrations**: for every sector with any existing
   exposure, add the approved amounts and recompute post_approval_pct. Flag
   over_limit when post_approval_pct > limit_pct.

### 3. Credit-union segment posture page

Produce a controlled posture recommendation for a credit-union segment backed
by NCUA state benchmarks, peer comparison, operating controls, and escalation
triggers.

**Fetch:** manifest, policies, NCUA benchmark, credit-union segment.

**Computation steps:**

1. Read the segment endpoint to get state_code, peer_states, quarterly_capacity,
   minimum_checklist, internal_context, and risk_tolerance.
2. From the NCUA benchmark table, extract the row for the segment's state_code
   and the US row. Compute peer median: for each metric, take the median of the
   peer_states' values.
3. Compare NC vs US and NC vs peer_median on all four metrics: delinquency_bps,
   loan_to_share_pct, roaa_bps, positive_net_income_pct. Direction is higher,
   lower, or equal.
4. **Posture**: choose based on capacity, external risk, and risk_tolerance.
   - If internal delinquency is approaching or exceeding 90bps, or external
     delinquency_bps is substantially above both US and peer median ->
     `temporarily_pause`.
   - If external risk is weaker but capacity available and risk_tolerance moderate
     -> `continue_with_tighter_conditions`.
   - If all metrics stronger -> `continue_approving`.
   See [references/policies.md](references/policies.md) for the full decision matrix.
5. **Controls**: `required_checklist_gates` come from the segment's
   minimum_checklist. `added_operating_controls` include at minimum:
   lien_perfection_prior_to_funding, monthly_segment_delinquency_watch,
   pre_close_insurance_binder_verification, quarterly_state_benchmark_monitoring,
   senior_underwriter_second_review.
6. **Escalation triggers**: assign trigger_ids and conditions per
   [references/reason_codes.md](references/reason_codes.md). The three standard
   triggers are segment recent delinquency >= 90bps, missing insurance/lien
   exceptions, and quarterly capacity exceeded.
7. **Interpretation**: map capacity_status (capacity_available when
   quarterly_capacity > 0), external_risk_status (weaker_than_national_and_peers
   when NC metrics are directionally worse than both US and peer median),
   risk_tolerance from the segment, and committee_message from the
   posture/risk combination.

### 4. Watch-list stress packet

Identify adverse-rated loans, assign CDFI risk classes, stress DSCR at +200bp,
and queue workout actions.

**Fetch:** branch, branch loans, policies.

**Computation steps:**

1. Filter loans to the adverse rating floor (current_rating >= 6).
2. **CDFI risk class**: for each loan, compute a factor score by summing
   contributions from fico, liquidity_months, ltv, and debt_to_asset using the
   tables in [references/policies.md](references/policies.md) -- "CDFI Factor
   Scores". Map the total score to a risk class:
   - 0-5: Prime
   - 6-9: Desirable
   - 10-13: Satisfactory
   - 14-18: Watch
   - >=19 and ltv <= 1.0: Doubtful
   - >=19 and ltv > 1.0, or payment_status Nonaccrual: Projected Loss
   Sort risk_classes by ascending loan_id.
3. **Monitoring cadence**: monthly when any loan's risk_class is Watch or worse
   or any loan is 90+DPD or Nonaccrual; quarterly otherwise; semiannual
   only when all loans are Desirable or better and all are Current.
4. **DSCR stress**: for every adverse loan with a DSCR value, compute
   stressed_dscr = dscr / 1.18. Breach threshold = 1.0. Flag loans where
   stressed_dscr < 1.0. Sort results ascending by loan_id (only loans with
   DSCR available). List breached loan_ids sorted ascending.
5. **Workout queue**: all adverse loans, sorted descending by exposure then
   ascending loan_id. Assign recommended_action per
   [references/reason_codes.md](references/reason_codes.md). Set projected_loss
   = true for Projected Loss risk class or Nonaccrual status, false otherwise.
6. **Severe bucket counts**: for loans with current_rating >= 6 (the original
   adverse filter), group by current_rating and payment_status, sorted
   ascending by current_rating then payment_status. Sum loan_count and
   exposure per bucket.

### 5. Competing CRE decision

Compare two CRE applications with weighted scoring, dual-factor stress, and
concentration analysis.

**Fetch:** branch, branch metrics, branch loans, branch sector-exposures,
branch applications, policies, FDIC benchmark.

**Computation steps:**

1. Fetch both applications. Compute the **weighted CDFI score** using the CRE
   weights from [references/policies.md](references/policies.md) -- "CRE
   Weighted Score". The five dimensions are capacity, capital, character,
   collateral_exposure, and conditions. Map application fields to dimension
   scores using the factor tables (a higher scored dimension is worse).
2. Map each application's weighted score to a score_class: approve_quality
   (<=2.0), conditional (<=3.0), weak (>3.0).
3. Assign an individual decision per application based on score_class,
   concentration checks, stress results, and FDIC benchmark comparison.
4. **Recommended path**: select the stronger application (lower weighted
   score). If both have the same score_class, prefer the one that passes the
   stress test and triggers fewer concentration flags.
5. **CRE dual-factor stress**: stressed_dscr = dscr * 0.85 / 1.18.
   Coverage breach threshold = 1.0. Report base_dscr, stressed_dscr, and
   breaches_threshold for each application.
6. **Concentration**: use cre_policy_limit_pct from branch details. Compute
   existing_cre_exposure as sum of outstanding_balance for all branch loans
   where loan_type is CRE. existing_cre_concentration = existing_cre_exposure /
   total_loans_outstanding. selected_post_approval_cre_concentration =
   (existing_cre_exposure + selected approved_amount) /
   total_loans_outstanding. selected_policy_variance_bps = (post_approval_pct -
   cre_policy_limit_pct) * 10000.
7. **FDIC benchmark**: use total_real_estate_30_89_pct. branch_delinquency_ratio
   = delinquency_30_plus_pct from branch metrics. Variance = branch ratio -
   FDIC ratio. Variance in bps = variance * 10000.
8. **Conditions**: assign per conditions enum in the answer template, guided by
   [references/reason_codes.md](references/reason_codes.md). Always include
   at minimum: committee_cre_exception, minimum_dscr_covenant_1_25,
   quarterly_financial_reporting, and no_additional_cre_without_committee_review.
   Add tenant_roll_and_lease_review and updated_appraisal_before_close when the
   property type warrants it.

## Computation discipline

- Always use the exact field names, enum values, and ordering rules from the
  answer template. Do not invent field names or values.
- Round numeric values to the precision specified in the template (typically
  2 decimals for currency, 4 decimals for ratios/percentages).
- When the template says "ascending" or "descending", sort exactly that way.
- Do not skip null/empty fields; include them with appropriate null or 0 values
  as the template requires.
- Compute values from API data; do not guess or hardcode them.
- For NCUA peer median computation: sort the peer states' values and take the
  middle value. For an even number of peers, average the two middle values and
  round to the nearest integer.

## Reference files

- [references/policies.md](references/policies.md) -- Full policy rules: risk
  rating thresholds, CDFI factor scores, CRE weighted scoring, stress formulas,
  concentration/capacity rules. Load this before computing any committee output.
- [references/api_surface.md](references/api_surface.md) -- API endpoint catalog,
  data shapes, and field descriptions. Load this when you need to understand
  what data each endpoint returns.
- [references/reason_codes.md](references/reason_codes.md) -- Decision reason
  codes, watch-list action assignment rules, condition codes, decline triggers,
  and escalation trigger mappings. Load when assigning codes or actions.

## Common pitfalls

- **Risk rating**: the dominant-factor rule means final_rating is the worst
  (highest numeric) of DSCR, LTV, and delinquency-derived ratings, not an
  average. If a factor is unavailable (null), skip it.
- **NPA definition**: nonperforming loans include Nonaccrual loans AND loans
  with final_rating >= 8. Do not count 90+DPD loans as NPA unless they are also
  Nonaccrual.
- **Capacity**: bank_capacity_used is the bank's retained portion after
  subtracting SBA-guaranteed or participation shares. Do not double-count.
- **Concentration percentages**: always divide by total_loans_outstanding from
  branch metrics, not by total_assets.
- **FDIC benchmark metric choice**: use total_loans_noncurrent_pct for general
  NPA comparisons; use total_real_estate_30_89_pct for CRE-specific delinquency
  comparisons. The task context determines which metric applies.
- **Sort stability**: when two items have equal sort keys, use the secondary
  sort specified in the template. If none is specified, use ascending loan_id
  or application_id as tiebreaker.
- **Loan field name variations**: the API uses different field names across
  endpoints (e.g., outstanding_balance in /loans vs requested_amount in
  /applications; borrower_name vs applicant_name; payment_status in loans vs
  no direct equivalent in applications). Always inspect the actual API response
  rather than assuming field names.
