# Answer Template Reference

Each task provides a JSON answer template at `input/payloads/answer_template.json`. This reference documents the five template shapes with their required keys, enums, sort orders, and numeric precision rules. Always read the live template during execution; these are reference summaries.

## 1. Rating Migration Review

**Top-level keys:** `branch_id`, `review_date`, `portfolio_regrade`, `npa_benchmark`, `material_downgrades`, `top_problem_credit`

**Sort orders:**
- `final_rating_exposure_totals`: ascending by `final_rating`
- `migration_from_current_rating_3`: ascending by `final_rating`; `loan_ids` ascending within each entry
- `watch_list_action_coverage.by_action`: ascending by `action`; `loan_ids` ascending
- `material_downgrades`: ascending by `loan_id`

**Key enums:**
- `benchmark_metric`: `total_loans_noncurrent_pct`, `total_real_estate_noncurrent_pct`, `construction_development_noncurrent_pct`
- `action` (watch list): `monitor`, `watchlist`, `special_assets`, `workout`, `partial_chargeoff_review`, `legal_referral`
- `payment_status`: `Current`, `30 Days Past Due`, `60 Days Past Due`, `90+ Days Past Due`, `Nonaccrual`
- `recommended_action`: `monitor`, `watchlist`, `special_assets`, `workout`, `partial_chargeoff_review`, `legal_referral`

**Action derivation from final_rating:**
- 8 → `partial_chargeoff_review`
- 7 → `special_assets`
- 6 → `watchlist`
- 3-5 → `monitor`
- 1-2: not in regrade population (loans below rating 3 are excluded)

**NPA benchmark computation:**
- `branch_npa_exposure`: sum of `outstanding_balance` for all branch loans with `payment_status == "Nonaccrual"` (not just regrade population)
- `branch_total_loans`: latest quarter `total_loans_outstanding` from branch metrics
- Ratios computed to 4 decimals, bps to 2 decimals

## 2. Lending Allocation

**Top-level keys:** `branch_id`, `allocation`, `decisions`, `concentration_flags`, `decline_reasons`, `post_approval_concentrations`

**Sort orders:**
- `decisions`: ascending by `application_id`
- `concentration_flags`: ascending by `sector` then `application_id`
- `post_approval_concentrations`: ascending by `sector`
- `priority_ranking`: approved and conditionally approved only, ordered by dscr descending, relationship_deposit_balance descending, existing_relationship_years descending

**Decision enums:** `approve`, `conditional_approve`, `decline`, `defer`, `participation_required`

**Conditions enums:** `participation_required`, `reduced_amount`, `board_exception`, `sba_guaranty_required`, `startup_monitoring`, `none`

**Reason code enums:** `capacity_limit`, `sector_breach`, `weak_dscr`, `high_ltv`, `low_fico`, `recent_bankruptcy`, `startup_risk`, `underwater_collateral`, `policy_floor_missing`, `documentation_gap`, `fdic_adverse_variance`, `ncua_peer_weakness`

**Handling enums:** `approve`, `conditional_approve`, `decline`, `participation_required`, `none`

**Percentages:** as ratios rounded to 4 decimals.

## 3. Credit-union Segment Posture

**Top-level keys:** `segment_id`, `posture`, `state_metrics`, `peer_comparison`, `controls`, `escalation_triggers`, `interpretation`

**Posture choices:** `continue_approving`, `continue_with_tighter_conditions`, `temporarily_pause`

**Peer comparison direction choices:** `higher`, `lower`, `equal`

**Controls:**
- `required_checklist_gates` choices: `board_authorization`, `equipment_invoice`, `fleet_replacement_plan`, `payer_contract_summary`, `public_contract_or_tax_support`, `proof_of_insurance`, `ucc_or_title_lien`
- `added_operating_controls` choices: `pre_close_insurance_binder_verification`, `lien_perfection_prior_to_funding`, `senior_underwriter_second_review`, `quarterly_state_benchmark_monitoring`, `monthly_segment_delinquency_watch`, `committee_exception_for_capacity_overrun`

**Escalation trigger conditions:** `segment_recent_delinquency_ge_90_bps`, `missing_insurance_or_lien_exception`, `quarterly_capacity_exceeded_or_exception_requested`, `state_delinquency_gap_widens_25_bps`

**Escalation owners:** `credit_risk_manager`, `operations_control_manager`, `lending_committee_chair`

**Interpretation choices:**
- `capacity_status`: `capacity_available`, `capacity_constrained`, `no_capacity`
- `external_risk_status`: `stronger_than_national_and_peers`, `mixed_vs_national_and_peers`, `weaker_than_national_and_peers`
- `risk_tolerance`: `restrained`, `moderate`, `expansive`
- `committee_message`: `capacity_available_but_external_risk_weaker`, `pause_until_state_metrics_recover`, `routine_approval_path_supported`

**Sort orders:**
- `peer_states`: ascending state code
- `escalation_triggers`: ascending trigger_id

## 4. Watch-list Stress

**Top-level keys:** `branch_id`, `watch_list_summary`, `stress_results`, `workout_queue`, `severe_bucket_counts`

**Risk class enums:** `Prime`, `Desirable`, `Satisfactory`, `Watch`, `Doubtful`, `Projected Loss`

**Monitoring cadence:** `monthly`, `quarterly`, `semiannual`

**Action enums (workout):** `monitor`, `watchlist`, `special_assets`, `workout`, `partial_chargeoff_review`, `legal_referral`

**Sort orders:**
- `risk_classes`: ascending by `loan_id`
- `stress_results.results`: ascending by `loan_id` (only loans with DSCR available)
- `breach_loan_ids`: ascending by `loan_id`
- `workout_queue`: descending by `exposure` then ascending by `loan_id`
- `severe_bucket_counts`: ascending by `current_rating` then `payment_status`

## 5. Competing CRE Decision

**Top-level keys:** `branch_id`, `applications_compared`, `recommended_path`, `stress`, `concentration`, `conditions`

**Score class enums:** `approve_quality`, `conditional`, `weak`

**Decision enums:** `approve`, `conditional_approve`, `decline`, `defer`, `participation_required`

**Reason codes (applications_compared):** full set: `capacity_limit`, `sector_breach`, `weak_dscr`, `high_ltv`, `low_fico`, `recent_bankruptcy`, `startup_risk`, `underwater_collateral`, `policy_floor_missing`, `documentation_gap`, `fdic_adverse_variance`, `ncua_peer_weakness`

**Unselected reason codes:** restricted to `sector_breach`, `weak_dscr`, `high_ltv`, `fdic_adverse_variance`

**Unselected disposition:** `decline`, `defer`

**FDIC benchmark metric:** `total_real_estate_30_89_pct`

**Conditions choices:** `bank_retained_exposure_cap`, `committee_cre_exception`, `updated_appraisal_before_close`, `tenant_roll_and_lease_review`, `minimum_dscr_covenant_1_25`, `quarterly_financial_reporting`, `no_additional_cre_without_committee_review`

**Sort orders:**
- `applications_compared`: ascending by `application_id`; `reason_codes` ascending alphabetically
- `stress.results`: ascending by `application_id`
- `recommended_path.unselected_reason_codes`: ascending alphabetically
- `conditions`: ascending alphabetically
