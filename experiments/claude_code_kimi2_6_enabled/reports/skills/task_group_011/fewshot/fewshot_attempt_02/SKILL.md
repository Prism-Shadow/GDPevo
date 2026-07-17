# Credit Office Decision Skill

## API Workflow (all tasks)

Base URL is in `environment_access.md` (do not run `env/setup.sh`).

1. `GET /api/manifest` → discover endpoints.
2. `GET /api/policies` → credit_policy_v2025Q1 thresholds, score tables, stress formulas.
3. `GET /api/branches` → list branches; find `branch_id`, `total_assets`, `lending_capacity_q1`, `sector_ceiling_pct`, `cre_policy_limit_pct`, `institution_type`.
4. Fetch branch-specific data:
   - `GET /api/branches/{branch_id}`
   - `GET /api/branches/{branch_id}/metrics`
   - `GET /api/branches/{branch_id}/loans`
   - `GET /api/branches/{branch_id}/sector-exposures`
   - `GET /api/branches/{branch_id}/applications`
5. For credit-union tasks:
   - `GET /api/credit-union-segments/{segment_id}`
   - `GET /api/benchmarks/ncua/q1-2025`
6. For bank benchmark tasks:
   - `GET /api/benchmarks/fdic/q4-2024`

## Task-Type Detection

Read the prompt and answer template to determine which of the five patterns applies:

| Pattern | Keywords | Branch Type |
|---------|----------|-------------|
| **Portfolio Regrade** | "portfolio regrade", "re-derive risk rating", "NPA benchmark" | bank |
| **Credit Decisions** | "credit decisions", "allocation", "concentration flags", "decline reasons" | bank |
| **CU Segment Review** | "credit union", "segment review", "NCUA", "posture", "escalation triggers" | credit_union |
| **Watch List Review** | "watch list", "adverse loans", "workout queue", "stress results" | bank |
| **Competing CRE** | "competing CRE", "compare", "recommended path", "stress", "weighted_cdfi_score" | bank |

---

## Pattern 1: Portfolio Regrade

### Business Rules
- Re-derive each loan’s **final_rating** from the worst numeric rating produced by:
  1. **DSCR** (if present): ≥1.5→3, ≥1.25→4, ≥1.05→5, ≥1.0→6, <1.0→7
  2. **LTV** (if present): ≤0.65→3, ≤0.75→4, ≤0.85→5, ≤1.0→6, >1.0→7
  3. **Delinquency** (from `payment_status`): Current→null, 30 DPD→4, 60 DPD→5, 90+ DPD→7, Nonaccrual→8
- Final rating = `max(available factor ratings, current_rating if no factors apply)`.
- **Material downgrades**: `final_rating - current_rating ≥ 2`. List every such loan with `downgrade_notches`.
- **Watch-list actions** (based on final_rating):
  - Rating 8 → `partial_chargeoff_review`
  - Rating 7 → `special_assets`
  - Rating 6 → `watchlist`
- **NPA benchmark**:
  - `branch_npa_exposure` = sum of `outstanding_balance` for loans with `payment_status` in (`Nonaccrual`, `90+ Days Past Due`)
  - `branch_total_loans` = sum of all loan `outstanding_balance`
  - `branch_npa_ratio` = `branch_npa_exposure / branch_total_loans` (4 decimals)
  - Use FDIC benchmark `total_loans_noncurrent_pct`
  - `variance_ratio = branch_npa_ratio - fdic_benchmark_ratio`
  - `variance_bps = variance_ratio * 10000` (2 decimals)

### Output Fields
- `branch_id`, `review_date`
- `portfolio_regrade`: `target_current_rating_min`, `target_loan_count`, `target_exposure`, `final_rating_exposure_totals[]` (group by final_rating, sum exposure/count), `migration_from_current_rating_3[]` (loans whose current_rating was 3, grouped by final_rating), `watch_list_action_coverage`
- `npa_benchmark`
- `material_downgrades[]`
- `top_problem_credit` (highest final_rating, then highest exposure)

---

## Pattern 2: Credit Decisions

### Business Rules
- Evaluate each application in ascending `application_id` order.
- **Decline reasons** (alphabetical, from controlled enum): `capacity_limit`, `sector_breach`, `weak_dscr`, `high_ltv`, `low_fico`, `recent_bankruptcy`, `startup_risk`, `underwater_collateral`, `policy_floor_missing`, `documentation_gap`, `fdic_adverse_variance`, `ncua_peer_weakness`.
- DSCR < 1.25 → `weak_dscr`; LTV > 0.80 → `high_ltv` (use application `ltv` when present).
- FICO < 620 → `low_fico`.
- Bankruptcy within last 24 months (i.e. `bankruptcy_months_ago` ≤ 24) → `recent_bankruptcy`.
- `years_in_business` < 2 → `startup_risk`.
- `documentation_complete == 0` → `documentation_gap`.
- **Capacity**: `lending_capacity_q1` is the ceiling. Approved amounts cannot exceed remaining capacity. If an app would exhaust capacity → `capacity_limit`.
- **Sector concentration**: `post_approval_pct = (current_exposure + approved_amount) / total_assets`. If > `limit_pct` → `sector_breach`.
  - If sector is new (no existing exposure), `current_exposure = 0`.
  - Grandfathered exposures may stay over-limit, but new approvals may not worsen the breach without mitigation.
- **SBA guaranty**: If `sba_guaranty_pct` is present, `bank_capacity_used = approved_amount * (1 - sba_guaranty_pct)`.
- **Participation required**: If post-approval would breach limit, set decision to `conditional_approve` with condition `participation_required` and reduce `bank_capacity_used` accordingly (see train_002 LAK-APP-901: approved_amount 1,650,000 but bank_capacity_used 1,508,113.31 implies ~8.6% participation).
- Priority ranking: list `application_id`s of approved and conditionally approved applications, highest priority first. Sort by: stronger credits first (lower risk), or by amount/largest approved first if tied.
- `gross_approved_amount` = sum of all `approved_amount` for approved/conditionally approved.
- `committed_capacity_amount` = sum of all `bank_capacity_used` for approved/conditionally approved.
- `remaining_capacity = lending_capacity_q1 - committed_capacity_amount`.

### Output Fields
- `branch_id`
- `allocation`: `lending_capacity_q1`, `gross_approved_amount`, `committed_capacity_amount`, `remaining_capacity`, `priority_ranking`
- `decisions[]` (ascending `application_id`): `application_id`, `decision`, `approved_amount`, `bank_capacity_used`, `conditions[]`
- `concentration_flags[]` (sort by sector then application_id): `sector`, `application_id`, `limit_pct`, `post_approval_pct` (4 decimals), `flag` (boolean), `handling`
- `decline_reasons`: map `application_id` → sorted list of reason strings
- `post_approval_concentrations[]` (sort by sector ascending): `sector`, `exposure_after_approval`, `post_approval_pct` (4 decimals), `limit_pct`, `over_limit` (boolean)

---

## Pattern 3: Credit Union Segment Review

### Business Rules
- Fetch segment data and NCUA Q1 2025 benchmarks.
- `state_metrics`: pull the row for the segment’s `state_code` from NCUA benchmarks.
- `peer_comparison`:
  - `peer_states` from segment data.
  - For each metric (`delinquency_bps`, `loan_to_share_pct`, `roaa_bps`, `positive_net_income_pct`), compare segment state vs US median and vs peer-state median. Label: `higher` / `lower` / `equal`.
- `posture`: derive from capacity and risk:
  - If `current_outstanding` is near or above `quarterly_capacity` → `pause_new_originations` or `continue_with_tighter_conditions`
  - If external risk is weaker than peers → `continue_with_tighter_conditions`
  - Otherwise → `continue_normal_underwriting`
- `controls.required_checklist_gates`: from segment `minimum_checklist`, sorted alphabetically.
- `controls.added_operating_controls`: add segment-appropriate controls (e.g. lien perfection, monthly delinquency watch, quarterly benchmark monitoring, senior underwriter second review, pre-close insurance verification). Sort alphabetically.
- `escalation_triggers`: create 3 triggers with IDs `ET001`–`ET003` covering delinquency threshold, missing documentation/lien exceptions, and capacity overrun.
- `interpretation`: `capacity_status` (`capacity_available` / `at_capacity`), `external_risk_status` (`weaker_than_national_and_peers` / `stronger_than_peers`), `risk_tolerance` from segment, `committee_message` concise summary.

### Output Fields
- `segment_id`, `posture`
- `state_metrics`
- `peer_comparison`
- `controls`
- `escalation_triggers[]`
- `interpretation`

---

## Pattern 4: Watch List Review

### Business Rules
- Scope: loans with `current_rating >= 6` **or** loans the prompt explicitly flags as adverse (e.g. "watch list pool"). If the prompt says "adverse_rating_min": 6, include all loans with current_rating ≥ 6.
- Compute **CDFI factor score** for each scoped loan using loan-level data:
  - `fico`: >720→0, 680-720→1, 580-679→3, <580→5
  - `ltv`: <0.40→0, 0.40-0.60→2, 0.60-0.80→4, >0.80→6
  - `debt_to_asset`: <0.40→0, 0.40-0.60→2, 0.60-0.80→4, >0.80→6
  - `liquidity_months`: >12→0, 6-12→1, 3-6→3, <3→5
  - Sum available factor scores. If a factor is null, skip it.
- **Risk class** from total score:
  - 0-5 → `Prime`
  - 6-9 → `Desirable`
  - 10-13 → `Satisfactory`
  - 14-18 → `Watch`
  - ≥19 and ltv > 1.0 → `Projected Loss`
  - ≥19 otherwise → `Doubtful`
- **Stress test** (watch-list formula from policy):
  - `stressed_dscr = base_dscr / (1 + 0.18)`
  - Breach threshold = 1.0
  - Only test loans that have a `dscr` value.
- **Workout queue**: sort scoped loans by severity:
  - `Projected Loss` first
  - Then by `payment_status` severity (Nonaccrual > 90+ DPD > 60 DPD > 30 DPD > Current)
  - Then by `current_rating` descending
  - Then by `outstanding_balance` descending
- `recommended_action` per loan:
  - `Projected Loss` or Nonaccrual → `partial_chargeoff_review`
  - 90+ DPD or rating 7+ → `special_assets`
  - Others → `watchlist`
- `monitoring_cadence`: `monthly` for any Watch/Projected Loss present, otherwise `quarterly`.
- `severe_bucket_counts`: group scoped loans by (`current_rating`, `payment_status`), count and sum exposure.

### Output Fields
- `branch_id`
- `watch_list_summary`: `adverse_rating_min`, `adverse_loan_count`, `adverse_balance`, `risk_classes[]`, `monitoring_cadence`
- `stress_results`: `shock_label` (`+200bp`), `breach_threshold`, `results[]`, `breach_loan_ids[]`
- `workout_queue[]`
- `severe_bucket_counts[]`

---

## Pattern 5: Competing CRE Decision

### Business Rules
- Compare exactly the two CRE applications specified in the prompt.
- **CRE weighted score** (from policy weights):
  - `capacity` 0.45, `capital` 0.03, `character` 0.05, `collateral_exposure` 0.36, `conditions` 0.11
  - Compute each factor as a normalized score (typically 1-5 scale based on thresholds), then `weighted_cdfi_score = sum(factor_score * weight)`.
  - Round to 1 decimal.
- **Score class**:
  - ≤2.0 → `approve_quality`
  - ≤3.0 → `conditional`
  - >3.0 → `weak`
- **Decision** per application:
  - `approve_quality` + no concentration breach → `approve`
  - `conditional` + no major issues → `conditional_approve`
  - `weak` or concentration breach or FDIC variance adverse → `decline`, `defer`, or `participation_required`
- **Stress test** (CRE dual-stress formula):
  - `stressed_dscr = dscr * 0.85 / (1 + 0.18)`  (i.e. `dscr * 0.85 / 1.18`)
  - Threshold = 1.0
- **Concentration**:
  - `existing_cre_exposure` = sum of `outstanding_balance` for all branch loans where `loan_type == "CRE"`
  - `existing_cre_concentration = existing_cre_exposure / total_assets` (4 decimals)
  - `selected_post_approval_cre_concentration = (existing_cre_exposure + selected_approved_amount) / total_assets` (4 decimals)
  - `selected_policy_variance_bps = (selected_post_approval_cre_concentration - cre_policy_limit_pct) * 10000` (2 decimals)
- **FDIC comparison**:
  - `branch_delinquency_ratio` = branch’s `delinquency_30_plus_pct` from metrics (2025Q1 row) (4 decimals)
  - `fdic_benchmark_ratio` = relevant FDIC metric (e.g. `total_real_estate_30_89_pct`) (4 decimals)
  - `fdic_variance_ratio = branch_delinquency_ratio - fdic_benchmark_ratio` (4 decimals)
  - `fdic_variance_bps = fdic_variance_ratio * 10000` (2 decimals)
- **Recommended path**:
  - Select the application with lower `weighted_cdfi_score` (better credit).
  - If tied, select the one with higher DSCR or lower LTV.
  - `path` = decision of selected application.
  - `unselected_disposition` = `decline` or `defer`.
  - `unselected_reason_codes` = sorted list from the allowed subset (`sector_breach`, `weak_dscr`, `high_ltv`, `fdic_adverse_variance`).
- **Conditions**: select all applicable conditions from the allowed enum, sorted alphabetically. Include items like `bank_retained_exposure_cap`, `committee_cre_exception`, `updated_appraisal_before_close`, `tenant_roll_and_lease_review`, `minimum_dscr_covenant_1_25`, `quarterly_financial_reporting`, `no_additional_cre_without_committee_review`.

### Output Fields
- `branch_id`
- `applications_compared[]` (ascending `application_id`): `application_id`, `weighted_cdfi_score` (1 decimal), `score_class`, `decision`, `reason_codes[]` (sorted)
- `recommended_path`: `selected_application_id`, `path`, `unselected_application_id`, `unselected_disposition`, `unselected_reason_codes[]`
- `stress`: `formula`, `coverage_breach_threshold`, `results[]`
- `concentration`: `cre_policy_limit_pct`, `existing_cre_exposure`, `existing_cre_concentration`, `selected_post_approval_cre_concentration`, `selected_policy_variance_bps`, `fdic_benchmark_metric`, `branch_delinquency_ratio`, `fdic_benchmark_ratio`, `fdic_variance_ratio`, `fdic_variance_bps`
- `conditions[]` (sorted alphabetically)

---

## Universal Precision Rules

- Currency / balances: round to **2 decimals**.
- Percentages as ratios: round to **4 decimals**.
- Percentage points / bps: round to **2 decimals**.
- Scores: round to **1 decimal**.
- DSCR / stress values: round to **2 decimals**.
- Sort all lists alphabetically or numerically as specified in the template.
- JSON output must match the exact keys and nesting of the provided `answer_template.json`.

## Common Pitfalls

1. **Using wrong benchmark set**: Banks use FDIC Q4 2024; credit unions use NCUA Q1 2025.
2. **Null handling**: Skip null factors in CDFI scoring; do not treat null as 0.
3. **Sector-exposure vs. limit**: `limit_pct` for a sector may differ from branch `sector_ceiling_pct` if the exposure is grandfathered. Use the value from `/api/branches/{branch_id}/sector-exposures`.
4. **SBA guaranty math**: `bank_capacity_used` is reduced by the guaranty percentage, but `approved_amount` stays at the full requested (or reduced) amount.
5. **CRE stress formula**: use `* 0.85 / 1.18`, not the watch-list `/(1+0.18)`.
6. **Total assets denominator**: always use the branch’s `total_assets` from `/api/branches/{branch_id}`, not loans outstanding or deposits.
7. **Do not include narrative text outside the JSON**.
