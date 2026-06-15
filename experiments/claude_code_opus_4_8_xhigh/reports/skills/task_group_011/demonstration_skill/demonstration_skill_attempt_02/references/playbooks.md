# Variant Playbooks (SOPs)

Each section is the procedure for one known output shape. Identify the variant from the
template's `required_top_level_keys`. These steps are transferable; the specific branch,
segment, loan ids, and numbers come from the live API for the task at hand. Always read the
actual `answer_template.json` — keys may be added or renamed in unseen tasks; follow the
template over this doc when they disagree.

Common setup for all: fetch `/api/policies`; fetch the named entity; build the loan/app set
the prompt scopes; apply policy math; round and order; emit JSON only.

---

## 1. Rating migration / regrade review
Top keys: `branch_id`, `review_date`, `portfolio_regrade`, `npa_benchmark`,
`material_downgrades`, `top_problem_credit`. Surfaces: branch, loans, metrics, FDIC.

1. **Population**: loans with `current_rating >= target_current_rating_min` (the prompt says
   "rated 3 or worse" → min 3). `target_loan_count` = count; `target_exposure` = Σ
   `outstanding_balance` (2 dp).
2. **Re-derive final rating** for each loan (dominant-factor rule; no-factor loans keep
   current_rating).
3. `final_rating_exposure_totals`: group population by final_rating → `loan_count`, `exposure`
   (Σ balance). Order ascending final_rating.
4. `migration_from_current_rating_3`: of loans whose `current_rating == 3`, group by final
   rating (only ratings that changed appear; include `loan_ids` ascending). Order ascending
   final_rating.
5. `watch_list_action_coverage`: loans whose **final** rating is adverse (>= 6) need follow-up.
   `covered_loan_count`/`covered_exposure` = those loans. `by_action`: map final rating →
   action (8→partial_chargeoff_review, 7→special_assets, 6→watchlist), group, list loan_ids
   ascending, order list **ascending by action string**.
6. **npa_benchmark**: `benchmark_version` = "fdic_q4_2024"; `benchmark_metric` =
   `total_loans_noncurrent_pct`. `branch_npa_exposure` = metrics `nonperforming_loans`
   (2025Q1); `branch_total_loans` = metrics `total_loans_outstanding`; `branch_npa_ratio` =
   exposure/total (4 dp); `fdic_benchmark_ratio` = the FDIC metric (4 dp); `variance_ratio` =
   branch−fdic (4 dp); `variance_bps` = (branch−fdic)×10000 from **unrounded** ratios (2 dp).
7. **material_downgrades**: loans where `final−current >= material_downgrade_notches` (2).
   Fields: loan_id, current_rating, final_rating, downgrade_notches, exposure. Order ascending
   loan_id.
8. **top_problem_credit**: the single worst credit — highest final rating, tie-break by largest
   exposure / most severe payment_status (e.g. the Nonaccrual rating-8 loan). Report loan_id,
   borrower_name, exposure, current_rating, final_rating, payment_status, recommended_action
   (per the action map).

## 2. Watch-list stress / workout
Top keys: `branch_id`, `watch_list_summary`, `stress_results`, `workout_queue`,
`severe_bucket_counts`. Surfaces: branch, loans, policies.

1. **Population**: loans with `current_rating >= adverse_rating_min` (prompt: "6 or worse" → 6).
   `adverse_loan_count`, `adverse_balance` (Σ balance, 2 dp).
2. **risk_classes**: for each loan, CDFI `factor_score` (sum of fico/ltv/dta/liquidity scores;
   missing → 0) and `risk_class` from the score band, with the **Projected Loss override**
   (Watch-band-or-worse + ltv>1.0 → Projected Loss). Order ascending loan_id.
3. **monitoring_cadence**: choose from {monthly, quarterly, semiannual}; an adverse watch-list
   population is monitored `monthly`.
4. **stress_results**: `shock_label` "+200bp", `breach_threshold` = coverage_breach_threshold
   (1.0). For each loan **with a DSCR**, `base_dscr` (2 dp), `stressed_dscr = dscr/1.18` (2 dp),
   `breaches_threshold = stressed < 1.0`. Order ascending loan_id. `breach_loan_ids` = those
   that breach, ascending.
5. **workout_queue**: one row per adverse loan with loan_id, exposure, risk_class,
   payment_status, recommended_action (8/Nonaccrual/Projected Loss→partial_chargeoff_review;
   7 or 90+ PD→special_assets; 6/Current→watchlist), `projected_loss` (true iff risk_class is
   Projected Loss). Order **descending exposure, then ascending loan_id**.
6. **severe_bucket_counts**: group population by (`current_rating`, `payment_status`) →
   loan_count, exposure. Order ascending current_rating, then ascending payment_status (string
   sort: "90+ Days Past Due" < "Current").

## 3. Allocation / pending applications
Top keys: `branch_id`, `allocation`, `decisions`, `concentration_flags`, `decline_reasons`,
`post_approval_concentrations`. Surfaces: branch, metrics, sector-exposures, applications,
policies.

1. **Screen each application** to a decision (enum: approve, conditional_approve, decline,
   defer, participation_required). Objective decline triggers (assign matching reason codes):
   - `weak_dscr` if DSCR present and < 1.25 (rating-4 floor); hard concern if < 1.0.
   - `high_ltv` if LTV > ~0.85 for CRE/business credits (use the policy LTV band that maps to
     rating 5+/6; consumer credits with strong FICO+low DTI may still pass).
   - `low_fico` if FICO < 580; `recent_bankruptcy` if `bankruptcy_months_ago` is recent (≈ ≤24).
   - `startup_risk` if `years_in_business < 2`.
   - `sector_breach` if approving would push the sector over its `limit_pct`/ceiling without a
     mitigation.
   - `capacity_limit` if otherwise approvable but no remaining lending capacity after
     higher-priority approvals.
   Strong credits near a sector ceiling → `conditional_approve` with `participation_required`.
   Startups with SBA support → `conditional_approve` with `sba_guaranty_required` +
   `startup_monitoring`. Conditions come from the conditions enum; use `["none"]` when none.
2. **Prioritise** approvable apps (strongest credit / best risk-adjusted first) and allocate
   against `lending_capacity_q1` in priority order until capacity is exhausted; apps that no
   longer fit get `decline` + `capacity_limit`.
3. **bank_capacity_used** per approved app = approved amount reduced by participation (bank
   retains the committee-set portion) and SBA (`approved × (1 − sba_guaranty_pct)`).
4. **allocation**: `gross_approved_amount` = Σ approved amounts (full) for approved+conditional;
   `committed_capacity_amount` = Σ bank_capacity_used; `remaining_capacity` = capacity − committed;
   `priority_ranking` = approved+conditional application_ids, highest priority first.
5. **decisions**: one per application, ascending application_id; declined → approved_amount 0,
   bank_capacity_used 0, conditions ["none"].
6. **concentration_flags**: one per app that touches a sector at/over its limit after approval;
   fields sector, application_id, limit_pct, post_approval_pct (4 dp), flag (bool), handling
   (enum). Order by sector then application_id.
7. **decline_reasons**: map each declined application_id → sorted (alphabetical) list of reason
   codes.
8. **post_approval_concentrations**: per sector, `exposure_after_approval` (existing +
   approved additions, 2 dp), `post_approval_pct` (÷ post-approval total portfolio = Σ all
   sector exposures + all approved additions, 4 dp), `limit_pct`, `over_limit` (bool). Order
   ascending sector.

## 4. Competing CRE decision
Top keys: `branch_id`, `applications_compared`, `recommended_path`, `stress`, `concentration`,
`conditions`. Surfaces: branch, metrics, loans, sector-exposures, the two applications, FDIC.

1. **applications_compared** (ascending application_id): `weighted_cdfi_score` (1 dp; weight
   the 5-C CDFI factor scores with `cre_weighted_score.weights` — capacity from DSCR-derived
   risk, collateral_exposure from LTV, capital from debt_to_asset, character from guarantor
   strength, conditions from documentation/qualitative risk); `score_class` from the bands
   (≤2.0 approve_quality, ≤3.0 conditional, >3.0 weak); `decision` (the better credit gets the
   stronger path, the weaker gets defer/decline); `reason_codes` ascending alphabetical.
2. **stress**: `formula` = the CRE dual-stress expression string (e.g. "dscr * 0.85 / 1.18");
   `coverage_breach_threshold` 1.0; per app `base_dscr`, `stressed_dscr = dscr*0.85/1.18` (2 dp),
   `breaches_threshold`. Order ascending application_id.
3. **recommended_path**: pick the stronger credit (better score_class, passes stress). When the
   branch CRE concentration is already well over limit, even the stronger credit takes
   `participation_required` (bank caps retained exposure) rather than a clean approve. The
   unselected credit gets `defer` (or `decline`) with its reason codes (ascending).
4. **concentration**: `cre_policy_limit_pct` = branch `cre_policy_limit_pct`;
   `existing_cre_exposure` = Σ `outstanding_balance` of loans with `loan_type == "CRE"`;
   `existing_cre_concentration` = existing ÷ metrics `total_loans_outstanding` (4 dp);
   `selected_post_approval_cre_concentration` = (existing + bank-retained portion of the
   selected request) ÷ total (4 dp); `selected_policy_variance_bps` = (post − limit)×10000 (2 dp);
   `fdic_benchmark_metric` = `total_real_estate_30_89_pct`; `branch_delinquency_ratio` =
   metrics `delinquency_30_plus_pct` (4 dp); `fdic_benchmark_ratio` (4 dp); `fdic_variance_ratio`
   = branch − fdic (4 dp); `fdic_variance_bps` = (branch − fdic)×10000 from unrounded (2 dp).
5. **conditions**: sorted alphabetical list from the conditions enum reflecting the chosen
   path (e.g. bank_retained_exposure_cap, committee_cre_exception, minimum_dscr_covenant_1_25,
   no_additional_cre_without_committee_review, quarterly_financial_reporting,
   tenant_roll_and_lease_review, updated_appraisal_before_close).

## 5. Credit-union segment posture
Top keys: `segment_id`, `posture`, `state_metrics`, `peer_comparison`, `controls`,
`escalation_triggers`, `interpretation`. Surfaces: manifest, policies, NCUA Q1 2025, segment.

1. **state_metrics**: `state_code` = segment state; `benchmark_version` "ncua_q1_2025"; copy
   the NCUA row's `delinquency_bps`, `loan_to_share_pct`, `roaa_bps`, `positive_net_income_pct`
   **verbatim integers**.
2. **peer_comparison**: `peer_states` = segment `peer_states` ascending. `nc_vs_us` and
   `nc_vs_peer_median`: for each of the four metrics, direction of the segment-state value vs
   the US row and vs the median of the peer-state values → {higher, lower, equal}. (For
   delinquency, higher = worse; for roaa/positive_net_income/loan_to_share, higher = stronger.)
3. **controls**: `required_checklist_gates` = the segment `minimum_checklist` (intersected with
   the allowed gate enum), as a set. `added_operating_controls`: pick controls that address the
   segment's `internal_context` and external risk (e.g. a missed insurance binder →
   pre_close_insurance_binder_verification + lien_perfection_prior_to_funding; weaker external
   metrics → quarterly_state_benchmark_monitoring + monthly_segment_delinquency_watch; staffing
   constraint → senior_underwriter_second_review). Emit each set sorted.
4. **escalation_triggers**: ascending trigger_id (ET001, ET002, ...). Map conditions to owners:
   delinquency trigger → credit_risk_manager; insurance/lien exception → operations_control_manager;
   capacity/exception → lending_committee_chair. Choose conditions/owners from the template enums.
5. **interpretation**: `capacity_status` (capacity_available if quarterly_capacity >
   current_outstanding usage / headroom remains); `external_risk_status`
   (weaker_than_national_and_peers when the state's delinquency/roaa lag both US and peer
   median); `risk_tolerance` = segment `risk_tolerance`; `committee_message` chosen to match
   (capacity available but external risk weaker → `capacity_available_but_external_risk_weaker`).
6. **posture**: capacity available but external metrics weak → `continue_with_tighter_conditions`;
   strong all around → `continue_approving`; capacity gone or metrics deteriorating →
   `temporarily_pause`.
