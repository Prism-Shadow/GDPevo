# SQL Payer Operations Skill

Use this skill for `task_group_014_sql_payer_ops` tasks that ask for JSON answers from the remote SQLite query service. The tasks cover utilization-management authorization intake, clinical review, pharmacy appeals and assistance routing, reimbursement compliance, and clinic profitability action lists.

## Access And Scope

1. Read `environment_access.md` for the SQL service base URL, username, and password. Do not hard-code the host in notes or solutions.
2. Read the staged prompt and payload files first. Treat payload case IDs, bucket names, clinics, periods, plan types, service categories, and materiality thresholds as the only allowed scope.
3. Start with schema discovery:
   - `SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name`
   - Then targeted table queries only for the staged scope.
4. Prefer one scoped join per task plus one targeted follow-up query for criteria, corrections, or budget details. Avoid broad `target_bucket` inventories.
5. Build the final JSON directly from SQL aggregates, then round at the output boundary.

## Common Output Rules

- Preserve the exact top-level keys and nested field names from `answer_template.json`.
- Sort case-level arrays by ascending case ID or medication case ID when requested.
- Sort analytic rows in a stable business order: period/quarter, clinic, payer or plan type, service category.
- Money, per-unit rates, costs, revenue, margin dollars, and recovery amounts: round to 2 decimals.
- Percentages and ratios: decimals rounded to 4 places, not whole-percent values.
- Summary counts must be recomputed from the final row arrays, not from intermediate unfiltered rows.
- Use JSON booleans and `null` where the template expects them; do not stringify booleans or nulls.

## Authorization Intake

Core tables:
`authorization_requests`, `auth_lines`, `service_codes`, `members`, `plans`, `providers`, `facilities`, `existing_authorizations`, `state_sla_rules`.

Recommended workflow:

1. Scope requests from payload case IDs or the staged bucket.
2. Join each request to member, plan, requesting and servicing providers, facility, line service-code rules, duplicate existing authorizations, and state SLA rules.
3. Aggregate lines by case before deciding disposition:
   - `MIN(service_codes.covered)` for covered-service failures.
   - `MAX(pa_required)`, `MAX(notification_only)`, `MAX(gold_card_exclusion)`, `MAX(mandatory_md_review)`.
   - `GROUP_CONCAT(DISTINCT external_vendor)` and `specialty_program` for review queues.
4. Apply first-failing-check logic in a fixed order:
   - active coverage
   - COB completion
   - covered service
   - network
   - service area
   - PA required or notification-only close
   - retrospective submission
   - duplicate authorization
   - none
5. Duplicate matching should compare member, CPT, overlapping service dates, and active/approved existing authorization status. Return duplicate IDs even when a prior check determines the final halt if the template asks for duplicate handling.
6. Provider sanctions and inactive credentials are usually reported in `provider_item`; do not convert them into intake halts unless the prompt explicitly says to.
7. OON exceptions and facility service-area flags can override simple network/service-area assumptions. Check the specific request flags before denying.
8. Gold-card auto approval requires plan permission, requesting-provider gold-card eligibility, covered/non-excluded service, and no mandatory MD review. If intake halted, use `not_reached_intake_halt`; otherwise choose the most specific not-eligible reason.
9. Review queues:
   - Intake halt: `No Review - Intake Halt`.
   - Gold card: `Auto Approval`.
   - External vendor values such as MedImage, CareEquip, or HomeCare generally drive the queue.
   - Mandatory MD review without a vendor goes to `Medical Director Review`; otherwise use nurse clinical review.
10. SLA due times come from `state_sla_rules` matched by plan state and plan type filter. Preserve the receipt timestamp time of day. Respect `calendar` vs `business` day rules.

## Clinical Review Slate

Core tables:
`authorization_requests`, `auth_lines`, `service_codes`, `members`, `plans`, `coverage_criteria`, `criteria_sources`, `clinical_facts`, `evidence_documents`, `case_review_events`, `p2p_sessions`.

Recommended workflow:

1. Scope cases from `authorization_requests.target_bucket` or explicit IDs in the staged worklist.
2. Determine service category from requested auth lines. If a case has multiple lines in one category, aggregate units for that category.
3. Criteria source selection should start with `coverage_criteria.criteria_source_id` for the case service category. Do not replace it with a plan-specific `criteria_sources` row unless the criteria rows themselves support that source.
4. Required evidence is the set of `coverage_criteria` rows with `is_required_for_approval = 1`.
5. A required key is missing when no current fact exists, `fact_value` does not match the required value, or the best fact has a weak confidence flag such as `stale`, `conflicting`, or `partial`. Strict confidence handling is safer than approving on `fact_value = met` alone.
6. A clean nurse approval requires all required evidence, no mandatory MD service rule, and no adverse prior review posture.
7. MD escalation is driven by mandatory MD service rules, current MD queue/stage, adverse-pending nurse events, or unresolved high-risk missing evidence. Use `none` for the reason code only when `md_escalation_required` is false.
8. Do not mark P2P suitable just because evidence is incomplete. Look for actual adverse posture, denial risk, or P2P session records.
9. `approved_units` should be positive only for approval recommendations; otherwise use `0`.
10. Queue counts should be derived from final case rows after MD/P2P decisions.

## Pharmacy Appeals And Assistance

Core tables:
`medication_cases`, `appeals`, `members`, `plans`, `drug_policy_requirements`, `medication_trials`, `assistance_programs`, `household_financials`.

Recommended workflow:

1. Scope medication cases from the staged medication case IDs or docket bucket.
2. Join appeal intake, plan type, policy requirements, documented medication trials, assistance program rules, and household financials.
3. Keep payer appeal routing and manufacturer assistance routing separate. Do not let assistance blockers change payer appeal timeliness or completeness.
4. Filing deadlines: use the prompt or plan-specific rule if provided. If no other rule is present, a 60-day deadline from `adverse_notice_date` is the safer default for these tasks.
5. `deadline_status` compares `appeal_received_date` to the filing deadline.
6. Expedited classification:
   - Expedited attestation plus supporting new evidence: `expedited_accepted_72h`.
   - Expedited attestation without support: `expedited_requested_needs_evidence`.
   - No expedited attestation: `standard_30d`.
7. Missing policy requirements should come only from `drug_policy_requirements` that are not supported by documented diagnosis or trial evidence. Do not invent extra requirements outside the policy table.
8. Assistance eligibility:
   - Compare household income against `max_income_fpl` using the relevant FPL threshold.
   - `requires_commercial_insurance` and `excludes_government_plan` can both block government-plan members.
   - `requires_denial`, `has_denial_letter`, and `assistance_consent_on_file` drive document/consent blockers.
9. Hard blockers such as income over limit or government-plan exclusion usually mean `program_owner: not_routed`.
10. If the only assistance blockers are missing denial letter and/or consent, keep the case with `manufacturer_assistance_team` for follow-up.
11. Path separation:
   - Appeal route only active: `appeal_only`.
   - Assistance route only active: `assistance_only`.
   - Both appeal and assistance follow-up active: `parallel_appeal_and_assistance`.
   - Neither active: `no_active_route`.

## Reimbursement Compliance

Core tables:
`encounters`, `rate_schedules`, `claim_corrections`.

Recommended workflow:

1. Build scoped clinic and quarter CTEs from `audit_scope.json`.
2. Assign each encounter to a quarter by `service_date`.
3. Join rate schedules on payer, plan type, service category, CPT code, clinic state from the audit scope, and service date within the rate effective range.
4. Paid-rate compliance uses paid encounters only. In practice, filter paid metrics with `paid_amount > 0`; count denied or unpaid encounters separately according to the prompt.
5. Benchmark amount is `units * benchmark_rate`.
6. Variance convention is `paid_amount - benchmark_amount`; material underpayments are negative variances.
7. Material cell filter:
   - `paid_units >= minimum_paid_units`
   - `benchmark_amount - paid_amount >= minimum_underpayment_amount`
   - `(benchmark_amount - paid_amount) / benchmark_amount >= minimum_underpayment_pct`
8. `paid_per_unit = paid_amount / paid_units`; `benchmark_per_unit = benchmark_amount / paid_units`.
9. Keep recovery opportunities separate from paid-rate compliance. Use only the active statuses listed in the task scope for `tracked_recovery_amount`.
10. Top recovery opportunity is the active correction with the highest `expected_recovery_amount`, carrying through encounter details.
11. Clinic-quarter classification is `material_underpayment` if any material cells exist for that clinic-quarter; otherwise `compliant`.

## Profitability Action Lists

Core tables:
`encounters`, `clinic_costs`, `clinic_budgets`, `claim_corrections`.

Recommended workflow:

1. Scope by fiscal year, clinics, plan types, and service categories from the worklist.
2. Aggregate by clinic, plan type, and service category:
   - `encounter_count = COUNT(*)`
   - `units = SUM(units)`
   - `paid_amount = SUM(paid_amount)` for paid revenue; zero-paid encounters still contribute units and cost.
3. For recovery in this task family, use claim corrections whose status is literally `open` unless the prompt provides a broader active-status list. Do not reuse reimbursement-compliance active statuses by default.
4. `cost_per_unit = direct_cost_per_unit + allocated_overhead_per_unit`.
5. `total_cost = units * cost_per_unit`.
6. `net_revenue = paid_amount + open_recovery`.
7. `net_margin = net_revenue - total_cost`.
8. `margin_pct = net_margin / net_revenue` when net revenue is nonzero.
9. Rank the top three loss drivers by the most negative `net_margin`, with stable tie-breakers by clinic, plan type, and service category.
10. Budget targets can be sensitive because `clinic_budgets` may expose clinic, payer, service category, and fiscal year but not an explicit plan type. Inspect duplicate budget rows and `budget_id` ordering before mapping targets. If no defensible plan mapping exists, use the visible budget dimensions consistently and make the action logic deterministic.
11. A payer-service cell needs action when `margin_pct` is below the budget margin target. Classify large gaps as `major_shortfall`; cells at or above target should not appear in `payer_actions`.
12. Projected improvement to reach the budget margin target:
    - `required_net_revenue = total_cost / (1 - budget_margin_pct)`
    - `projected_improvement_amount = max(0, required_net_revenue - net_revenue)`
13. Persistence should be checked across quarters within the fiscal year. A cell with repeated below-budget quarters is `persistent`; otherwise use a nonpersistent/watchlist class consistent with the template.
14. `portfolio_summary.payer_service_results` should include every scoped cell, not only action cells. `flagged_pair_count` should match the number of action rows.

## Pitfalls

- Do not infer answers from final `status` alone. Use the task's requested workflow: intake, clinical review, appeal routing, compliance, or profitability.
- Do not substitute plan state for clinic state in reimbursement rate matching when the audit scope supplies clinic states.
- Do not flip reimbursement variance signs: underpayments should remain negative when the field is `variance_amount`.
- Do not include closed correction statuses in recovery totals. Use exactly the statuses specified by the task.
- Do not let manufacturer assistance ineligibility suppress an otherwise timely payer appeal.
- Do not approve clinical cases on stale, conflicting, or partial evidence without considering confidence flags.
- Do not assume every repeated budget row maps cleanly to a plan type; inspect and document the mapping before relying on it.
