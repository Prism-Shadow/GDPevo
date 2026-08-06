# Deliverable Patterns

The answer_template.json in front of you is always authoritative. What follows is a map of the recurring deliverable shapes this family uses, so you can recognize the pattern and know what each section must capture. Field names below come from the template schemas (generic); **substitute the exact field names and enums from your template**, and never copy specific numeric values from any deal.

## Pattern A — Issue register (seller or buyer side)

Typical of an APA/SPA issue-register task. Top level: `deal_id`, `client_side`, `issue_register[]`, `priority_order[]`, `summary_metrics{}`.

- `issue_register[]` — one entry per issue (present-and-deviating term, or required-but-missing term). Each entry: `issue_id` (from a stable enum like `possible_issue_ids`), `source_term_ids` (`[]` when missing), `business_outcome`, `issue_status`, `risk_rating`, `recommended_action`, `required_position_code`, then the quantification triples `draft_*` / `preferred_*` / `fallback_*` and the `delta_to_fallback_*` for percent / dollars / months, plus fee fields (`required_fee_percent`, `required_fee_dollars`, `shortfall_dollars`), employee fields (`employee_count`, `pto_liability_dollars`, `service_credit_required`), regulatory booleans (`hell_or_high_water_required`, `hsr_required`, `regulatory_effort_code`), tax/governing-law fields, and a `covenant_limits` object for restrictive-covenant specifics. Fill only the fields relevant to that issue's category; leave the rest `null`.
- `priority_order[]` — issue_ids highest negotiation priority → lowest.
- `summary_metrics{}` — counts, `headline_value_dollars`, `total_quantified_exposure_low/high_dollars`, `total_negotiation_delta_dollars`, `required_closing_consent_count`, `total_employee_count`, `total_pto_liability_dollars`. Must reconcile with the register (see review_methodology §5).

## Pattern B — Closing & economics package (buyer SPA)

Typical of a buyer-side SPA closing package. Top level: `task_id`, `deal_id`, `economics{}`, `closing_conditions{}`, `covenants{}`, `regulatory{}`, `closing_readiness{}`.

- `economics` — `headline_value`, `upfront_cash`, `stock_value`, `milestone_value`; `holder_allocation[]` (pro-rata on cap-table `as_converted_shares`/`fully_diluted_pct` → `cash_amount`, `stock_amount`, `total_consideration`); `indemnity_package` (draft/preferred/fallback cap pct + amounts, survival months, materiality-scrape, risk); `escrow` (basis, required_pct, amount, release_months, release_trigger, status); `nwc_adjustment` (required, mechanic, collar_amount, source_finding_id, status).
- `closing_conditions` — `required_consents[]` (source_id, contract_name, counterparty, condition_type, risk_rating, amount_at_risk), `material_contract_conditions[]` (contract_id, condition_type, annual_revenue), `non_blocking_notices[]` (source ids only).
- `covenants` — `employment` (continuing_employee_count, service_credit_employee_ids, pto_liability_total, warn_risk_employee_ids, required_action), `restrictive_covenants` (required, covered_holder_groups, required_action), `do_tail_and_expenses` (do_tail_required, tail_period_years, tail/seller/buyer expense allocation, amount_status).
- `regulatory` — hsr_required, threshold_basis, regulatory_approval, hell_or_high_water_required, closing_condition_required.
- `closing_readiness` — overall_status (READY / READY_WITH_CONDITIONS / NOT_READY), risk_rating, `blocker_ids[]`, `tradeable_issue_ids[]`, and the at-risk/conditioned totals. Blocker vs tradeable split is the key judgment.

## Pattern C — Committee escalation memo

Typical of an M&A-Committee escalation task that **excludes** stale/in-policy/non-committee distractors. Top level: `task_id`, `deal_id`, `memo{}`, `escalation_terms[]`, `aggregate_summary{}`.

- `memo` — prepared_for, client_name, project_name, target_name, counterparty_name, policy_id, signing_date, meeting_date, currency, value_basis, headline_value.
- `escalation_terms[]` — only out-of-policy / restricted terms. Each: `term_id`, `category` (reverse_termination_fee, fiduciary_out, rw_survival, mae_carveouts, …), `clause_ref`, `issue_status` (out_of_policy), `risk_rating`, `draft_metric{}` (value, unit, basis, amount, and category-specific sub-fields like fundamental/general months, restricted_carveouts, added_count, match_right_business_days), `policy_metric{}` (threshold_value, unit, basis, threshold_amount, required_triggers, approved_carveout_groups), `delta{}` (percent_points, amount, fundamental/general months, removed_triggers, excess_count), `benchmark{}` (metric, sample_size, median, upper_quartile, position), `exposure{}` (type, low, high, source_estimate_id), `recommendation` (approve / approve_with_conditions / reject), `required_conditions[]`.
- `aggregate_summary` — escalated_term_count, `excluded_in_policy_terms[]`, `excluded_in_policy_categories[]`, `risk_counts{HIGH,MEDIUM,LOW}`, aggregate_quantified_exposure_low/high, `included_exposure_components[]`, `excluded_exposure_components[]`, `rtf_excess_amount`, `overall_recommendation`, `committee_action` (one-line narrative of the recommended action), `negotiation_priority[]` (category order).

## Pattern D — Carveout transition review (seller APA)

Typical of a carveout/separation transition package. Top level: `deal_id`, `client_side`, `transition_issues[]`, `required_redlines[]`, `operational_risk{}`.

- `transition_issues[]` — focus on transition/separation: IP & domain transition, trademark license, TSA scope/duration/fees, Section 1060 allocation, transfer-tax split, employee continuity/PTO, closing-deadline/outside-date protection, governing law/forum, customer-consent termination rights. Each: `issue_id` (from `stable_issue_ids`), `category`, `source_term_ids`, `source_record_ids`, `issue_status`, `risk_rating`, `recommended_action`, `draft_value_normalized{}` (what the draft says/omits), `required_position_normalized{}` (the affirmative position with concrete limits), `quantified_impact_dollars`.
- `required_redlines[]` — one per issue, linked by `related_issue_id`. Each: `redline_id` (from `stable_redline_ids`), `related_issue_id`, `redline_action` (delete/revise/add), `must_have_terms{}` (the concrete terms the redline must insert).
- `operational_risk` — `overall_risk_rating`, `overall_posture` (accept_as_drafted / revise_before_signing / escalate_to_business_lead / reject), `priority_order[]`, `quantified_exposures{}` (stranded_cost_gap, field_operations_pto_liability, required_closing_consent_amount_at_risk, top_customer_annual_revenue_at_risk, transition_disruption_high), `required_closing_consent_ids[]`, `material_contract_consent_ids[]`, `business_outcomes_protected[]`.

## Pattern E — Deviation / position matrix (buyer SPA)

Typical of a buyer-side deviation matrix. Top level: `deal_id`, `prepared_for`, `currency`, `position_matrix[]`, `closing_blockers[]`, `risk_totals{}`.

- `position_matrix[]` — the buyer's positions across indemnity cap & basket, survival & knowledge, materiality scrape, escrow/holdback/release, consent closing condition, HSR, material contracts. Each: `issue_id`, `source_term_ids` (`[]` when missing from the draft), `status`, `risk_rating`, `recommended_action`, `final_position` (from a stable enum), `priority_rank`, the percent/months/amount triples, `shortfall_to_fallback_usd` / `shortfall_to_preferred_usd`, `special_indemnity_amount_usd`, `privacy_finding_amount_usd`, and per-issue `*_status` flags (`basket_status`, `knowledge_qualifier_status`, `escrow_agent_status`, `release_status`) using `not_found_in_current_records` / `found` / `not_applicable`, plus `required_consent_ids[]` / `required_contract_ids[]` / `excluded_contract_ids[]` / `excluded_from_draft[]`.
- `closing_blockers[]` — each: `blocker_id` (consent id / contract id / synthetic regulatory id), `blocker_type` (required_consent / regulatory_clearance / material_contract_consent), `related_contract_id`, `must_be_satisfied_before_closing`, `risk_rating`, `amount_at_risk_usd`, `annual_revenue_usd`, `required_action` (obtain_consent / obtain_clearance / add_closing_condition).
- `risk_totals{}` — headline_purchase_price_usd, position_issue_count, out_of_policy_issue_count, draft_below_playbook_count, missing_required_term_count, high_risk_issue_count, closing_blocker_count, required_consent_amount_at_risk_usd, material_contract_revenue_requiring_consent_usd, indemnity_cap_shortfall_to_fallback_usd, indemnity_cap_shortfall_to_preferred_usd, total_modeled_exposure_low_usd, total_modeled_exposure_high_usd, highest_modeled_exposure_category.

## Cross-pattern notes
- Several patterns coexist within one family; a single task uses exactly one. Identify yours from the answer_template.json, not from the prompt narrative alone.
- `source_term_ids` is `[]` whenever the required term is absent from the draft (missing-required-term issues) — this is consistent across patterns.
- "Not found in current records" is a first-class finding (e.g. an escrow agent or basket the workbench does not contain) — emit the template's `not_found_in_current_records` enum rather than guessing.
- All patterns require the aggregate/total fields to reconcile with their line items (see review_methodology §5).
