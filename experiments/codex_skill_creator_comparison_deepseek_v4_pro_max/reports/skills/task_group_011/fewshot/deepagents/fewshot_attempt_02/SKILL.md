---
name: credit-risk-committee
description: "Credit risk committee lending workflow for a shared credit office REST API. Handles rating migration reviews, lending-committee allocations, credit-union segment postures, watch-list stress packets, and competing CRE decisions. Use when a prompt mentions a credit risk committee, lending committee, branch rating review, branch allocation package, credit-union segment posture, watch-list stress or workout, competing CRE decision, or any task that references the shared credit office API at a base URL like TASK_ENV_BASE_URL. Also use when the prompt references branch review, FDIC/NCUA benchmarks, CDFI scoring, DSCR stress, policy re-rating, sector concentration, or committee-ready JSON answers for branch_id, segment_id, or application_id comparisons."
---

# Credit Risk Committee

## Overview

This skill covers five credit-risk committee workflows backed by a shared credit office REST API. Every workflow follows the same pattern: fetch branch/segment data, fetch policy rules, derive or recompute risk metrics from policy tables, compare against FDIC or NCUA benchmarks, and produce a committee-ready JSON answer matching a supplied answer template.

The API base URL is always provided as `TASK_ENV_BASE_URL`. The task prompt names the target (a `branch_id`, `segment_id`, or competing `application_id` pair) and supplies a JSON answer template under `input/payloads/answer_template.json`.

## API Quick Reference

| Endpoint | Purpose |
|---|---|
| `GET /api/manifest` | Environment info, benchmark versions, record counts |
| `GET /api/policies` | Credit policy rules (risk rating, CDFI, CRE scoring, stress, concentration) |
| `GET /api/branches` | All branches (branch_id, branch_name, institution_type, state_code, capacity/sector ceilings) |
| `GET /api/branches/{id}` | Single branch details |
| `GET /api/branches/{id}/metrics` | Branch quarterly metrics (total loans, NPA, delinquency, allowance) |
| `GET /api/branches/{id}/loans` | All loans at a branch (rating, DSCR, LTV, FICO, payment status, balance, sector, etc.) |
| `GET /api/branches/{id}/sector-exposures` | Per-sector exposures and limits |
| `GET /api/branches/{id}/applications` | Pending applications (DSCR, LTV, FICO, requested amount, sector, loan type, etc.) |
| `GET /api/benchmarks/fdic/q4-2024` | FDIC Q4 2024 benchmark ratios |
| `GET /api/benchmarks/ncua/q1-2025` | NCUA Q1 2025 state-level benchmark rows |
| `GET /api/credit-union-segments/{id}` | Credit union segment details (member profile, peer states, capacity, controls) |

All endpoints return JSON. No authentication is required.

## Policy Rules

The `/api/policies` response contains all rating, scoring, and concentration rules. It is a single JSON object with these top-level keys:

- `risk_rating` — risk-rating derivation tables
- `cdfi_factor_scores` — CDFI-style factor scoring tables
- `cre_weighted_score` — CRE weighted score weights and score-class thresholds
- `stress` — stress formulas and breach thresholds
- `capacity_concentration` — capacity and sector concentration rules

Full policy details are in [references/policies.md](references/policies.md). Always fetch `/api/policies` at the start of any committee task; do not hardcode values that may differ across runs.

## Workflows

### 1. Rating Migration Review (branch)

**Triggers:** "rating migration review", "re-derive risk ratings", "portfolio regrade", "watch-list action coverage"

**Data to fetch:** `/api/branches/{id}`, `/api/branches/{id}/loans`, `/api/branches/{id}/metrics`, `/api/policies`, `/api/benchmarks/fdic/q4-2024`

**Procedure:**

1. Fetch policies and branch/loan/metrics/benchmark data.
2. Identify the target population: loans where `current_rating >= target_current_rating_min` (from the task prompt; default 3 for "3 or worse").
3. For each target loan, re-derive the `final_rating` using the dominant-factor rule from policies. Compute the DSCR rating (from `dscr_thresholds`), LTV rating (from `ltv_thresholds`), and delinquency minimum rating (from `delinquency_minimums`). The final rating is the worst (highest numeric) of the three available factors. When `dscr` is null, omit the DSCR factor; when `collateral_value` is null or `ltv` is null, omit LTV; delinquency rating is always available from `payment_status`.
4. Build `portfolio_regrade`:
   - `target_current_rating_min`, `target_loan_count`, `target_exposure` from the filtered population.
   - `final_rating_exposure_totals`: group re-rated loans by `final_rating`, summing loan_count and exposure, sorted ascending by final_rating.
   - `migration_from_current_rating_3`: subset where `current_rating == 3`, grouped by `final_rating`, with `loan_ids` sorted ascending.
   - `watch_list_action_coverage`: determine actions for each re-rated loan:
     - `final_rating == 8` → `partial_chargeoff_review`
     - `final_rating == 7` → `special_assets`
     - `final_rating == 6` → `watchlist`
     - `final_rating >= 3 and final_rating <= 5` → `monitor`
     - Group by action, sum loan_count and exposure, sorted ascending by action.
5. Build `npa_benchmark`:
   - `benchmark_version`: from FDIC benchmark object (e.g. `fdic_q4_2024`).
   - `benchmark_metric`: `total_loans_noncurrent_pct`.
   - `branch_npa_exposure`: sum of `outstanding_balance` where `payment_status == "Nonaccrual"` across all branch loans.
   - `branch_total_loans`: `total_loans_outstanding` from latest branch metrics.
   - `branch_npa_ratio`: `branch_npa_exposure / branch_total_loans` (4 decimals).
   - `fdic_benchmark_ratio`: from FDIC benchmark.
   - `variance_ratio`: `branch_npa_ratio - fdic_benchmark_ratio` (4 decimals).
   - `variance_bps`: `variance_ratio * 10000` (2 decimals).
6. Build `material_downgrades`: loans where `final_rating - current_rating >= 2` (`material_downgrade_notches` from policy). Sorted ascending by `loan_id`. Include: `loan_id`, `current_rating`, `final_rating`, `downgrade_notches` (= final - current), `exposure` (= outstanding_balance, 2 decimals).
7. Build `top_problem_credit`: the single loan with the highest `final_rating`, then highest `exposure` as tiebreaker. Include `loan_id`, `borrower_name`, `exposure`, `current_rating`, `final_rating`, `payment_status`, and `recommended_action` (derived from final_rating as in watch_list_action_coverage).

**Template reference:** [references/templates.md](references/templates.md#1-rating-migration-review)

### 2. Lending-committee Allocation (branch)

**Triggers:** "lending-committee allocation", "allocation package", "pending applications", "application-level decisions"

**Data to fetch:** `/api/branches/{id}`, `/api/branches/{id}/applications`, `/api/branches/{id}/sector-exposures`, `/api/branches/{id}/metrics` (for total_loans), `/api/policies`, optionally `/api/benchmarks/fdic/q4-2024`

**Procedure:**

1. Fetch branch, applications, sector exposures, and policies.
2. **Decisions:** Evaluate every application. Compute the final decision:
   - Sector check: `post_approval_pct = (current_exposure + approved_amount) / total_loans`. If `post_approval_pct > limit_pct` (using branch `sector_ceiling_pct` unless a sector-specific override exists in `sector_exposures`), flag as sector breach.
   - The sector-specific `limit_pct` from `sector_exposures` overrides the branch default `sector_ceiling_pct` for that sector.
   - Decision logic (apply in order):
     - `ltv > 0.85` → `decline` (reason `high_ltv`)
     - `dscr < 1.05` → `decline` (reason `weak_dscr`)
     - `fico < 580` (when fico is not null) → `decline` (reason `low_fico`)
     - `years_in_business < 1` → `decline` (reason `startup_risk`)
     - `bankruptcy_months_ago` present and `< 36` → `decline` (reason `recent_bankruptcy`)
     - `documentation_complete == 0` → `decline` (reason `documentation_gap`)
     - When approved amount would exceed remaining lending capacity → `decline` (reason `capacity_limit`).
     - Sector limit breach → if allowed mitigation via `participation_required`, set `conditional_approve` with condition `participation_required`; otherwise `decline` (reason `sector_breach`).
     - `sba_guaranty_pct` present → set condition `sba_guaranty_required`.
     - `years_in_business >= 1 and years_in_business < 3` → add condition `startup_monitoring`.
     - Otherwise → `approve`.
   - `approved_amount`: requested_amount for approve, the portion the bank retains (total minus participation share) for conditional_approve with participation_required (bank_retained = requested_amount * (1 - participation_pct)); 0 for decline.
   - `bank_capacity_used`: the bank's retained portion of approved_amount.
   - `conditions`: list of applicable conditions; use `["none"]` for approve with no conditions.
3. **Allocation:**
   - `lending_capacity_q1`: from branch.
   - `gross_approved_amount`: sum of `approved_amount` across all approved and conditional_approve decisions.
   - `committed_capacity_amount`: sum of `bank_capacity_used` across all approved and conditional_approve decisions.
   - `remaining_capacity`: `lending_capacity_q1 - committed_capacity_amount`.
   - `priority_ranking`: approved and conditionally approved application_ids, ordered highest priority first. Priority is determined by `dscr` (descending), then `relationship_deposit_balance` (descending), then `existing_relationship_years` (descending).
4. **Concentration flags:** For each sector where an approved/conditionally-approved application exists, compute `post_approval_pct`. Flag is `true` when `post_approval_pct > limit_pct`. For flagged sectors, handling is `participation_required`. Sort by sector then application_id.
5. **Decline reasons:** Map each declined `application_id` to its reason codes from the template enum.
6. **Post-approval concentrations:** For each sector that has existing exposure or newly approved applications, compute `exposure_after_approval = current_exposure + sum(approved_amount for approved apps in that sector)`. Compute `post_approval_pct = exposure_after_approval / total_loans`. Sort by sector ascending.

**Template reference:** [references/templates.md](references/templates.md#2-lending-allocation)

### 3. Credit-union Segment Posture (segment)

**Triggers:** "credit-union segment posture", "segment posture page", "controlled posture recommendation"

**Data to fetch:** `/api/credit-union-segments/{id}`, `/api/benchmarks/ncua/q1-2025`, `/api/policies`

**Procedure:**

1. Fetch segment and NCUA benchmark data.
2. **Posture:** Determine from segment's `risk_tolerance`:
   - `expansive` → `continue_approving`
   - `moderate` → `continue_with_tighter_conditions`
   - `restrained` → `temporarily_pause`
3. **State metrics:** Extract the NCUA row for the segment's `state_code`. Values are integers exactly as reported: `delinquency_bps`, `loan_to_share_pct`, `roaa_bps`, `positive_net_income_pct`.
4. **Peer comparison:** Use `peer_states` from segment. Compute `nc_vs_us`: compare NC's value against the US row for each of the four metrics → `higher`, `lower`, or `equal`. Compute `nc_vs_peer_median`: take the median of peer states' values for each metric and compare NC against that median → `higher`, `lower`, or `equal`.
5. **Controls:** `required_checklist_gates` from segment's `minimum_checklist`. `added_operating_controls`: from the template enum. Select based on internal context: include all operating controls that address identified weaknesses (e.g., `lien_perfection_prior_to_funding` and `pre_close_insurance_binder_verification` for control issues; `monthly_segment_delinquency_watch` for elevated delinquency; `quarterly_state_benchmark_monitoring` for adverse state metrics; `senior_underwriter_second_review` for staffing constraints).
6. **Escalation triggers:** Select triggers from template enum based on internal context. `segment_recent_delinquency_ge_90_bps` when recent_delinquency_bps >= 90. `missing_insurance_or_lien_exception` when control issues exist. `quarterly_capacity_exceeded_or_exception_requested` for capacity monitoring. Assign owners per template choices.
7. **Interpretation:** Fill each field from template choices:
   - `capacity_status`: based on segment's `quarterly_capacity` and internal context.
   - `external_risk_status`: based on peer comparison results. If NC is mostly worse than peers and US → `weaker_than_national_and_peers`. If mixed → `mixed_vs_national_and_peers`. If mostly better → `stronger_than_national_and_peers`.
   - `risk_tolerance`: from segment.
   - `committee_message`: choose based on the combination of capacity_status and external_risk_status.

**Template reference:** [references/templates.md](references/templates.md#3-credit-union-segment-posture)

### 4. Watch-list Stress Packet (branch)

**Triggers:** "watch-list stress", "adverse-rated", "CDFI risk classes", "+200bp DSCR stress", "workout actions"

**Data to fetch:** `/api/branches/{id}/loans`, `/api/policies`

**Procedure:**

1. Fetch branch loans and policies.
2. Filter to adverse-rated loans: `current_rating >= 6` (unless template specifies otherwise).
3. **CDFI risk classes:** For each adverse loan, compute factor scores from `cdfi_factor_scores` tables in policies:
   - `fico_score` from fico ranges → integer 0-5 (omit if fico is null).
   - `ltv_score` from ltv ranges → integer 0-6 (omit if ltv is null).
   - `debt_to_asset_score` from debt_to_asset ranges → integer 0-6 (omit if debt_to_asset is null).
   - `liquidity_score` from liquidity_months ranges → integer 0-5 (omit if liquidity_months is null).
   - Sum all available factor scores for `factor_score`.
   - Map `factor_score` to risk class per the class thresholds. Special rule: `factor_score >= 19 and ltv > 1.0` → `Projected Loss`. Otherwise, use the class whose score_range includes factor_score.
   - Sort risk_classes ascending by loan_id.
4. **Monitoring cadence:** `monthly` if any loan is `Projected Loss` or `Doubtful` or has `payment_status` of `90+ Days Past Due` or `Nonaccrual`; `quarterly` otherwise.
5. **Stress results:** Apply the watch-list stress formula: `stressed_dscr = dscr / (1 + 0.18)` for each adverse loan that has a non-null DSCR. `breach_threshold = 1.0`. A loan `breaches_threshold` when `stressed_dscr < 1.0`. List results sorted ascending by loan_id. `breach_loan_ids` lists those where breaches_threshold is true, sorted ascending.
6. **Workout queue:** All adverse loans, sorted descending by `exposure` (= outstanding_balance), then ascending by `loan_id`. For each:
   - `recommended_action`:
     - `Projected Loss` risk class or `Nonaccrual` → `partial_chargeoff_review`
     - `Doubtful` risk class or `90+ Days Past Due` → `special_assets`
     - `Watch` risk class → `special_assets`
     - `Desirable`/`Satisfactory` with stressed DSCR breach → `watchlist`
     - `Desirable`/`Satisfactory` without breach → `watchlist` (current_rating >= 6 is adverse)
     - `Prime` → `monitor`
   - `projected_loss`: `true` for `Projected Loss` risk class; `false` otherwise.
7. **Severe bucket counts:** Group adverse loans by `current_rating` and `payment_status`. Sum `loan_count` and `exposure`. Sort ascending by current_rating, then payment_status. Include all adverse loan buckets (current_rating >= 6).

**Template reference:** [references/templates.md](references/templates.md#4-watch-list-stress)

### 5. Competing CRE Decision (branch, two application_ids)

**Triggers:** "competing CRE decision", "competing CRE", "weighted CRE credit scoring", "CRE dual-stress"

**Data to fetch:** `/api/branches/{id}`, `/api/branches/{id}/applications`, `/api/branches/{id}/loans`, `/api/branches/{id}/sector-exposures`, `/api/branches/{id}/metrics`, `/api/policies`, `/api/benchmarks/fdic/q4-2024`

**Procedure:**

1. Fetch all relevant data. Isolate the two competing applications.
2. **CDFI weighted CRE scoring:** For each application, compute the five sub-scores on a 1-5 scale (1 is best, 5 is worst):
   - **Capacity (weight 0.45):** Based on `dscr`: >= 1.50 → 1, >= 1.25 → 2, >= 1.05 → 3, >= 1.00 → 4, < 1.00 → 5.
   - **Collateral/Exposure (weight 0.36):** Based on `ltv`: < 0.40 → 1, < 0.60 → 2, < 0.80 → 3, < 1.00 → 4, >= 1.00 → 5.
   - **Conditions (weight 0.11):** Based on sector concentration risk: if the application's sector has existing exposure near or over its limit, score 4-5; if moderate, 3; if low, 1-2. Use sector_exposures data and the sector's limit_pct.
   - **Capital (weight 0.03):** Based on net_income / total_assets ratio from the application: >= 0.20 → 1, >= 0.10 → 2, >= 0.05 → 3, >= 0.00 → 4, < 0.00 → 5.
   - **Character (weight 0.05):** Based on `existing_relationship_years`: >= 10 → 1, >= 5 → 2, >= 2 → 3, >= 1 → 4, < 1 → 5.
   - `weighted_cdfi_score = sum(weight_i * sub_score_i)`, rounded to 1 decimal.
   - Score class per cre_weighted_score thresholds: <= 2.0 → `approve_quality`, <= 3.0 → `conditional`, > 3.0 → `weak`.
3. **Recommended path:** The application with the lower `weighted_cdfi_score` is selected. If tied, prefer lower DSCR stress breach, then higher DSCR.
   - Selected `path`: based on score class:
     - `approve_quality` → `approve`, unless sector concentration is breached → `conditional_approve` with sector conditions.
     - `conditional` → `conditional_approve` or `participation_required` depending on concentration.
     - `weak` → `defer`.
   - Unselected: if score_class is `weak` → `decline`; if `conditional` → `defer`; if `approve_quality` → `defer` (capacity/competition).
   - Unselected reason codes: include any applicable from template enum (`sector_breach`, `weak_dscr`, `high_ltv`, `fdic_adverse_variance`).
4. **Stress:** Apply CRE dual-stress formula: `stressed_dscr = dscr * 0.85 / (1 + 0.18)`. `coverage_breach_threshold = 1.0`. Results for both applications sorted by application_id ascending.
5. **Concentration:**
   - `cre_policy_limit_pct`: from branch.
   - `existing_cre_exposure`: sum of `outstanding_balance` for all branch loans where `loan_type == "CRE"` and `sector` indicates commercial real estate (e.g., Office, Retail CRE, Industrial CRE, Hospitality, Construction, Logistics — anything not purely residential/consumer).
   - `existing_cre_concentration = existing_cre_exposure / total_loans_outstanding` (from latest metrics).
   - `selected_post_approval_cre_concentration = (existing_cre_exposure + selected_app_requested_amount) / total_loans_outstanding`.
   - `selected_policy_variance_bps = (selected_post_approval_cre_concentration - cre_policy_limit_pct) * 10000`.
   - `fdic_benchmark_metric`: always `total_real_estate_30_89_pct`.
   - `branch_delinquency_ratio`: `delinquency_30_plus_pct` from latest branch metrics.
   - `fdic_benchmark_ratio`: `total_real_estate_30_89_pct` from FDIC benchmark.
   - `fdic_variance_ratio = branch_delinquency_ratio - fdic_benchmark_ratio`.
   - `fdic_variance_bps = fdic_variance_ratio * 10000`.
6. **Conditions:** Select from template enum. Always include `committee_cre_exception` when CRE concentration exceeds policy limit. Include `bank_retained_exposure_cap` and `no_additional_cre_without_committee_review` for concentration breaches. Include `minimum_dscr_covenant_1_25` and `quarterly_financial_reporting` for stress-sensitive loans. Include `tenant_roll_and_lease_review` and `updated_appraisal_before_close` for CRE loans. Sort ascending alphabetically.

**Template reference:** [references/templates.md](references/templates.md#5-competing-cre-decision)

## Execution Order

1. Read the template at `input/payloads/answer_template.json` to understand the required JSON shape, enums, and ordering rules.
2. Call `/api/policies` to load the current policy tables.
3. Call the branch-specific or segment-specific endpoints listed in the workflow above.
4. Apply the policy rules to derive ratings, scores, and decisions.
5. Fill the template exactly, respecting all enum values, numeric precision, and sort orders.
6. Output only valid JSON. No narrative text outside the JSON.

## Numeric Precision Rules

- Currency (USD) values: rounded to 2 decimals.
- Ratios and percentages as ratios: rounded to 4 decimals.
- Basis points: rounded to 2 decimals.
- Integer fields: whole numbers only.
- CDFI weighted score: rounded to 1 decimal.
- Stress DSCR values: rounded to 2 decimals.

## References

- [references/policies.md](references/policies.md) — Complete credit policy tables and scoring rules
- [references/templates.md](references/templates.md) — All five answer template JSON shapes with field ordering and enum constraints
- [references/api.md](references/api.md) — API endpoint reference with response field descriptions
