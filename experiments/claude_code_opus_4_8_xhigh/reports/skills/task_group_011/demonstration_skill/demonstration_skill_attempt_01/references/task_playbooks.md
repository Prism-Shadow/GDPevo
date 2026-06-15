# Task Playbooks

Per-task-type procedures. Each is verified against the standard answers. Read SKILL.md first for the shared
rules (risk-rating re-derivation, action mapping, stress formulas, CDFI scoring, concentration math, rounding,
ordering). Below, "exposure" = loan `outstanding_balance`; round currency to 2 dp, ratios to 4 dp, bps to 2 dp,
DSCR to 2 dp, CDFI weighted score to 1 dp. Always emit only the JSON object.

## Table of contents
1. Rating Migration Review
2. Watch-List Stress Packet
3. Allocation Package
4. Competing CRE Decision
5. Segment Posture Page

---

## 1. Rating Migration Review

Top-level keys: `branch_id`, `review_date`, `portfolio_regrade`, `npa_benchmark`, `material_downgrades`,
`top_problem_credit`.

**Population:** loans with `current_rating >= target_current_rating_min` (usually 3 — "rated 3 or worse").
Fetch `GET /api/branches/{id}/loans?min_current_rating=3`.

**Steps**

1. **Re-derive** each loan's `final_rating` (worst of DSCR/LTV/delinquency candidate ratings; if no factor,
   keep `current_rating`). See SKILL.md.
2. `portfolio_regrade`:
   - `target_current_rating_min` = the min you filtered on (e.g. 3).
   - `target_loan_count` = number of loans in the population.
   - `target_exposure` = sum of their `outstanding_balance`.
   - `final_rating_exposure_totals` = group **all** population loans by `final_rating`; per group emit
     `{final_rating, loan_count, exposure}`. **Order ascending by final_rating.**
   - `migration_from_current_rating_3` = take only loans whose `current_rating == 3` **and whose final_rating
     changed** (i.e. final != 3), group by `final_rating`; emit `{final_rating, loan_count, exposure, loan_ids}`
     with `loan_ids` sorted ascending. **Order ascending by final_rating.** (Loans that stay at 3 are omitted.)
   - `watch_list_action_coverage`: assign each population loan an action by its **final** rating
     (6→watchlist, 7→special_assets, 8→partial_chargeoff_review; ≤5 → not covered). `covered_loan_count` and
     `covered_exposure` aggregate the covered (rating ≥6) loans. `by_action` groups them by action with
     `{action, loan_count, exposure, loan_ids}`, loan_ids ascending, list **ordered ascending by action name**.
3. `npa_benchmark` (FDIC, metric `total_loans_noncurrent_pct`):
   - `branch_npa_exposure` = sum of `outstanding_balance` over **all** branch loans (not just the population)
     whose `payment_status` is `90+ Days Past Due` or `Nonaccrual`.
   - `branch_total_loans` = `metrics(2025Q1).total_loans_outstanding`.
   - `branch_npa_ratio` = npa_exposure / total_loans (4 dp).
   - `fdic_benchmark_ratio` = `total_loans_noncurrent_pct`.
   - `variance_ratio` = branch_npa_ratio − fdic_benchmark_ratio (4 dp); `variance_bps` = variance_ratio*10000 (2 dp).
   - `benchmark_version` = `"fdic_q4_2024"`, `benchmark_metric` = `"total_loans_noncurrent_pct"`.
4. `material_downgrades` = population loans with `final_rating − current_rating >= 2`; emit
   `{loan_id, current_rating, final_rating, downgrade_notches, exposure}`, **ordered ascending loan_id**.
5. `top_problem_credit` = the loan with the worst `final_rating` (tie-break largest exposure). Emit
   `{loan_id, borrower_name, exposure, current_rating, final_rating, payment_status, recommended_action}` where
   `recommended_action` follows the action map on the final rating (rating-8 Nonaccrual → `partial_chargeoff_review`).

---

## 2. Watch-List Stress Packet

Top-level keys: `branch_id`, `watch_list_summary`, `stress_results`, `workout_queue`, `severe_bucket_counts`.

**Population:** "adverse" loans = `current_rating >= 6`. Fetch with `min_current_rating=6`.

**Steps**

1. `watch_list_summary`:
   - `adverse_rating_min` = 6; `adverse_loan_count` = count; `adverse_balance` = sum exposure.
   - `risk_classes` = for each loan, CDFI `factor_score` (sum of present fico/ltv/debt_to_asset/liquidity_months
     band scores) and its `risk_class` (Prime/Desirable/Satisfactory/Watch/Doubtful, with the Projected Loss
     override: underwater `ltv>1.0` + Nonaccrual, or score≥19 & ltv>1.0). Emit `{loan_id, risk_class,
     factor_score}`, **ordered ascending loan_id**.
   - `monitoring_cadence` = severity-driven; the train answer used `"monthly"` for a population containing
     Projected-Loss / Nonaccrual credits. Use `"monthly"` when any Watch/Doubtful/Projected-Loss or
     noncurrent credit is present; otherwise `quarterly`.
2. `stress_results` (+200bp watch-list shock):
   - `shock_label` = `"+200bp"`; `breach_threshold` = `1.0` (= `stress.coverage_breach_threshold`).
   - `results` = for each loan **with DSCR present** (skip null DSCR), `base_dscr` (2 dp), `stressed_dscr =
     dscr/1.18` (2 dp), `breaches_threshold = stressed_dscr < 1.0`. **Ordered ascending loan_id.**
   - `breach_loan_ids` = the loan_ids that breach, ascending.
3. `workout_queue` = every adverse loan, with `{loan_id, exposure, risk_class, payment_status,
   recommended_action, projected_loss}`. `risk_class` is the CDFI class; `recommended_action` follows the
   action map on the loan's **current_rating** (6→watchlist, 7→special_assets, 8→partial_chargeoff_review);
   `projected_loss = (risk_class == "Projected Loss")`. **Order descending exposure, then ascending loan_id.**
4. `severe_bucket_counts` = group the adverse population by `(current_rating, payment_status)`; emit
   `{current_rating, payment_status, loan_count, exposure}`. **Order ascending current_rating, then payment_status.**

---

## 3. Allocation Package

Top-level keys: `branch_id`, `allocation`, `decisions`, `concentration_flags`, `decline_reasons`,
`post_approval_concentrations`. This task allocates **pending applications** against quarterly capacity.

**Inputs:** `GET /api/branches/{id}` (capacity, sector_ceiling_pct), `GET /api/branches/{id}/applications`,
`GET /api/branches/{id}/sector-exposures`, `metrics(2025Q1)`.

**Per-application underwriting screen → decision.** Evaluate each application's objective factors against the
policy bands and assign a `decision` and (if declined) sorted `decline_reasons`. Reason-code semantics
(template enum) and the signals that trigger them:

- `weak_dscr` — DSCR materially below the policy DSCR floor for an approvable credit.
- `high_ltv` — LTV above the acceptable band for that loan type (CRE/commercial LTV is held tighter than
  consumer/residential; judge against the `ltv_thresholds` shape).
- `low_fico` — FICO in the weakest band (`<580`).
- `recent_bankruptcy` — `bankruptcy_months_ago` is set and recent.
- `startup_risk` — very low `years_in_business` (e.g. < ~1–2 yrs) without mitigation.
- `capacity_limit` — no remaining quarterly capacity for this request.
- `sector_breach` — would push a sector over its ceiling without mitigation.
- Others (`underwater_collateral`, `policy_floor_missing`, `documentation_gap`, `fdic_adverse_variance`,
  `ncua_peer_weakness`) per their plain meaning.

A credit that is fundamentally sound but bumps a sector ceiling or needs structure gets `conditional_approve`
(with `conditions`) or `participation_required` rather than `decline`. Sound, in-capacity credits get
`approve` with `conditions: ["none"]`. Order `decline_reasons` lists **ascending alphabetically**; map only
declined application_ids in `decline_reasons`.

**Conditions & bank capacity used.** `conditions` enum: `participation_required`, `reduced_amount`,
`board_exception`, `sba_guaranty_required`, `startup_monitoring`, `none`.
- For an **SBA-guaranteed** approval, the bank only uses the unguaranteed share:
  `bank_capacity_used = approved_amount * (1 - sba_guaranty_pct)`; conditions include `sba_guaranty_required`
  (plus `startup_monitoring` for young borrowers).
- For a **participation** (to fit a sector ceiling), `approved_amount` is the gross facility but
  `bank_capacity_used` is the retained bank share (less than gross); condition `participation_required`.
- Otherwise `bank_capacity_used = approved_amount`. Declines have both = 0.0 and `conditions: ["none"]`.

**allocation block:**
- `lending_capacity_q1` = branch `lending_capacity_q1`.
- `gross_approved_amount` = sum of `approved_amount` over approved + conditionally-approved apps.
- `committed_capacity_amount` = sum of `bank_capacity_used` over those apps.
- `remaining_capacity` = `lending_capacity_q1 − committed_capacity_amount`.
- `priority_ranking` = ordered list of the approved/conditional application_ids, **highest priority first**
  (strongest credits / best risk-adjusted first).

**decisions** = one entry per application `{application_id, decision, approved_amount, bank_capacity_used,
conditions}`, **ordered ascending application_id**. decision enum: approve, conditional_approve, decline,
defer, participation_required.

**concentration_flags** = entries for apps whose approval brings a sector to/over its ceiling
`{sector, application_id, limit_pct, post_approval_pct, flag, handling}`; `limit_pct` is the sector's
`limit_pct` from `/sector-exposures` (fallback branch `sector_ceiling_pct`); `post_approval_pct` 4 dp;
`handling` is how it's resolved (e.g. `participation_required`). **Order by sector then application_id.**

**post_approval_concentrations** = for each sector touched, `{sector, exposure_after_approval,
post_approval_pct, limit_pct, over_limit}`. `exposure_after_approval` = existing sector `current_exposure`
+ sum of **gross approved_amount** booked to that sector. `post_approval_pct` = exposure_after_approval ÷
(`total_loans_outstanding` + total gross approved), 4 dp. `over_limit = post_approval_pct > limit_pct`.
**Order ascending by sector.**

---

## 4. Competing CRE Decision

Top-level keys: `branch_id`, `applications_compared`, `recommended_path`, `stress`, `concentration`,
`conditions`. Compares two named CRE applications and picks the stronger.

**Inputs:** the two applications, branch detail (`cre_policy_limit_pct`), `metrics(2025Q1)`, all loans (for
existing CRE exposure), `GET /api/benchmarks/fdic/q4-2024`.

**1. Weighted CRE score** (`cre_weighted_score`, lower is better). Score each "C" factor for the application
from its governing fields, using the same band shapes as the risk/CDFI tables, then weight:
`score = capacity*0.45 + collateral_exposure*0.36 + conditions*0.11 + character*0.05 + capital*0.03`
(weights from policy). Map the factors as: **capacity↔DSCR**, **collateral_exposure↔LTV**,
**capital↔debt/asset** (`total_debt/total_assets`), **character↔relationship depth / co-guarantor strength /
prior delinquencies**, **conditions↔documentation completeness / structure (SBA, rate, term)**. Round the
weighted score to **1 dp**. Classify via `cre_weighted_score.classes`: `approve_quality` (≤2.0),
`conditional` (≤3.0), `weak` (>3.0). Per application emit `{application_id, weighted_cdfi_score, score_class,
decision, reason_codes}`, reason_codes sorted alphabetically, list **ordered ascending application_id**.
(Note: the exact per-factor sub-rubric is not published in the policy; derive each C from its fields using the
band shapes above, and let the class cutoffs and the relative ranking of the two credits drive the decision —
the stronger credit must score better and land in the better class.)

**2. CRE dual stress** (`stress`): `formula` = `"dscr * 0.85 / 1.18"`; `coverage_breach_threshold` = 1.0;
`results` per application `{application_id, base_dscr, stressed_dscr, breaches_threshold}` with
`stressed_dscr = dscr*0.85/1.18` (2 dp), breach if `< 1.0`. **Order ascending application_id.**

**3. concentration:**
- `cre_policy_limit_pct` = branch `cre_policy_limit_pct`.
- `existing_cre_exposure` = sum of `outstanding_balance` for loans with `loan_type == "CRE"`.
- `existing_cre_concentration` = existing_cre_exposure ÷ `total_loans_outstanding` (4 dp).
- `selected_post_approval_cre_concentration` = (existing_cre_exposure + selected `requested_amount`) ÷
  (`total_loans_outstanding` + selected `requested_amount`) (4 dp).
- `selected_policy_variance_bps` = (selected_post_approval_cre_concentration − cre_policy_limit_pct) * 10000 (2 dp).
- `fdic_benchmark_metric` = `"total_real_estate_30_89_pct"`; `fdic_benchmark_ratio` = that FDIC value.
- `branch_delinquency_ratio` = `metrics.delinquency_30_plus_pct` (4 dp).
- `fdic_variance_ratio` = branch_delinquency_ratio − fdic_benchmark_ratio (4 dp);
  `fdic_variance_bps` = *10000 (2 dp).

**4. recommended_path:** pick the stronger credit (better/lower weighted score, passes stress, lower added
concentration). `selected_application_id`, `path` (its decision, e.g. `participation_required` when sector/CRE
is elevated). For the loser: `unselected_application_id`, `unselected_disposition` (`decline` or `defer` —
`defer` when the credit is salvageable but weaker), `unselected_reason_codes` sorted alphabetically (from the
restricted enum `sector_breach, weak_dscr, high_ltv, fdic_adverse_variance`).

**5. conditions** = sorted-alphabetically list from the conditions enum
(`bank_retained_exposure_cap, committee_cre_exception, updated_appraisal_before_close,
tenant_roll_and_lease_review, minimum_dscr_covenant_1_25, quarterly_financial_reporting,
no_additional_cre_without_committee_review`) appropriate to a CRE approval that breaches the CRE ceiling and
underperforms the FDIC benchmark.

---

## 5. Segment Posture Page

Top-level keys: `segment_id`, `posture`, `state_metrics`, `peer_comparison`, `controls`,
`escalation_triggers`, `interpretation`. For a credit-union segment.

**Inputs:** `GET /api/credit-union-segments/{id}` (peer_states, risk_tolerance, minimum_checklist,
quarterly_capacity, internal_context), `GET /api/benchmarks/ncua/q1-2025?state_code=XX` for the segment state,
each peer state, and `US`.

**Steps**

1. `state_metrics` = copy the NCUA row for the segment's `state_code` **verbatim as integers**:
   `{state_code, benchmark_version:"ncua_q1_2025", delinquency_bps, loan_to_share_pct, roaa_bps,
   positive_net_income_pct}`.
2. `peer_comparison`:
   - `peer_states` = segment `peer_states`, **ascending**.
   - `nc_vs_us` = direction of the state's value vs the `US` row for each metric:
     `higher`/`lower`/`equal`. (For delinquency, "higher" = worse; for roaa/pni "lower" = worse.)
   - `nc_vs_peer_median` = direction vs the **median** of the peer-state values for each metric.
3. `controls`:
   - `required_checklist_gates` = the segment's `minimum_checklist` (a set of the gate enums).
   - `added_operating_controls` = the extra controls warranted by the posture. When metrics are weaker than
     peers/national and there are insurance/lien control issues, add (alphabetically as a set):
     `lien_perfection_prior_to_funding`, `monthly_segment_delinquency_watch`,
     `pre_close_insurance_binder_verification`, `quarterly_state_benchmark_monitoring`,
     `senior_underwriter_second_review`.
4. `escalation_triggers` = ordered list `{trigger_id, condition, owner}` with `trigger_id` `ET001`, `ET002`,
   `ET003`, ... ascending. Pair conditions with owners:
   `segment_recent_delinquency_ge_90_bps` → `credit_risk_manager`;
   `missing_insurance_or_lien_exception` → `operations_control_manager`;
   `quarterly_capacity_exceeded_or_exception_requested` → `lending_committee_chair`;
   `state_delinquency_gap_widens_25_bps` → typically `credit_risk_manager`.
5. `interpretation`:
   - `capacity_status` = `capacity_available` when quarterly capacity remains; else constrained / none.
   - `external_risk_status` = `weaker_than_national_and_peers` when the state is worse on delinquency and
     roaa/pni vs both US and peer median; `stronger_...` / `mixed_...` otherwise.
   - `risk_tolerance` = segment `risk_tolerance` (e.g. `moderate`).
   - `committee_message` = the matching enum, e.g. `capacity_available_but_external_risk_weaker` when capacity
     is available but external risk is weaker; `pause_until_state_metrics_recover` when pausing;
     `routine_approval_path_supported` when clean.
6. `posture` = `continue_approving` (clean), `continue_with_tighter_conditions` (capacity available but
   external risk weaker / control issues → added controls), or `temporarily_pause` (capacity gone or metrics
   sharply adverse).
