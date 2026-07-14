---
name: task_group_014_sql_payer_ops
description: Compact operating procedure for payer-operations SQL tasks using the staged prompt, payload templates, gold few-shot examples, and the remote SQLite query service.
---

# Payer Ops SQL Workflow

Use this skill for `task_group_014_sql_payer_ops` tasks. Solve from the prompt, the input payloads, the answer template, and targeted SQL against the remote SQLite service. Do not assume a local database file.

## Connection And Setup

1. Read `environment_access.md` for the query endpoint and credentials. Do not hard-code the host or port in notes or reusable code.
2. Read the task prompt, every JSON payload under `input/payloads/`, and `answer_template.json` before querying.
3. Use only read-only SQL through `POST /query` with body `{"sql":"SELECT ...","params":[]}` and HTTP Basic Auth from `environment_access.md`.
4. Start with schema confirmation:

```sql
SELECT name, sql
FROM sqlite_master
WHERE type = 'table'
ORDER BY name;
```

Then inspect only relevant rule tables or target rows. The recurring tables are:

- UM authorization: `authorization_requests`, `auth_lines`, `members`, `plans`, `providers`, `facilities`, `service_codes`, `existing_authorizations`, `state_sla_rules`.
- Clinical review: UM tables plus `criteria_sources`, `coverage_criteria`, `clinical_facts`, `evidence_documents`, `case_review_events`, `p2p_sessions`.
- Drug appeal and assistance: `medication_cases`, `appeals`, `drug_policy_requirements`, `medication_trials`, `assistance_programs`, `household_financials`, `members`, `plans`.
- Finance and rehab: `encounters`, `rate_schedules`, `claim_corrections`, `clinic_costs`, `clinic_budgets`.

## General Output Rules

- Return exactly one JSON object matching `answer_template.json`; no prose.
- Preserve template field names and enum spelling exactly.
- Sort case-level rows by ascending case ID or medication case ID unless the prompt says otherwise.
- Use empty arrays for no missing items or no duplicates. Use `null` for inapplicable values when a decision is not made, such as `approved_units` for escalated clinical cases or a missing assistance program.
- Round money and per-unit rates to 2 decimals. Round percentages/ratios to decimal values with 4 places. Keep intermediate SQL math unrounded until the final projection.
- Emit ISO dates as requested by the template: dates as `YYYY-MM-DD`, datetimes as `YYYY-MM-DDTHH:MM`.
- Build case-level CTEs before aggregate summaries. Avoid line-level joins that multiply facts, corrections, or costs.

## UM Intake Audit

Target cases come from the payload case list or `authorization_requests.target_bucket`.

Core joins:

- `authorization_requests.member_id -> members -> plans`
- requesting and servicing providers from `requesting_npi`/`servicing_npi`
- `facility_id -> facilities`
- `auth_lines.cpt_code -> service_codes`
- duplicate check against `existing_authorizations`
- SLA rule by plan/facility state and plan type through `state_sla_rules`

Reusable business rules:

- Active coverage: request/service timing must fall within member coverage dates, with any retro reinstatement considered if present.
- COB halt uses `authorization_requests.cob_primary_processed = 0`; do not treat `members.cob_primary_status` alone as the halt.
- Duplicate authorization is a hard intake halt when the same member has an overlapping existing authorization for the requested CPT and the existing status is open or approved. Sort duplicate IDs ascending. This halt can preempt later service-area, vendor, or review routing.
- Covered-service halt if any requested line has `service_codes.covered = 0`.
- Network and service-area halts use provider network/credential facts and `facilities.in_service_area`, while respecting any task-specific out-of-network exception flag.
- Notification-only/no-PA services use `service_codes.notification_only = 1` or `pa_required = 0` and close as notification-only when no other halt applies.
- Retrospective halt uses `authorization_requests.rendered_before_submission = 1`.
- Provider follow-up item is based on the requesting provider: active sanction takes `requesting_provider_active_sanction`; inactive credentials take `requesting_provider_credentials_inactive`; otherwise `none`.

Gold-card and queue routing:

- If any intake halt applies, `gold_card_decision` is `not_reached_intake_halt` and review queue is `No Review - Intake Halt`.
- Gold-card auto-approval requires the plan to allow gold carding, the requesting provider to have active gold-card status, and no line-level exclusion such as `gold_card_exclusion = 1` or mandatory MD review. Collapse multiple failures to the template's multiple-reason enum when needed.
- If not auto-approved, route by line flags: non-`none` external vendors first (`MedImage Review`, `CareEquip Review`, `HomeCare Review`), then `Medical Director Review` for mandatory MD review, otherwise `Nurse Clinical Review`.

SLA:

- Use `state_sla_rules` matching the plan type and applicable state. Plan state is usually primary; facility state can matter for conflict/basis text when a matching facility-state rule also applies.
- Use `routine_days`, `urgent_hours`, or `stat_hours` from the matched rule based on `urgency_attested`.
- For `day_type = business`, add business days and skip weekends. For `calendar`, add calendar days/hours. Preserve the receipt time.
- Format `sla_basis` compactly from state/plan type/day type/days or hours, matching staged style.

## Clinical Review Slate

Target cases usually come from `authorization_requests.target_bucket` or a payload worklist.

Criteria workflow:

1. Determine each case's plan type and service category from `plans` and `auth_lines -> service_codes`.
2. Select the highest-precedence `criteria_sources` row whose plan/service filters match and that has corresponding `coverage_criteria` rows. Use `ALL` filters as fallbacks.
3. Required approval keys are `coverage_criteria.is_required_for_approval = 1`.
4. A criterion is clearly met only when `clinical_facts.fact_value` equals the required value and `confidence_flag = 'clear'`. Treat missing, `unclear`, `not_met`, `partial`, `stale`, and `conflicting` as missing evidence.
5. Sort `missing_evidence_keys` alphabetically for stable output.

Recommendations:

- Approve as requested only when all required evidence is clearly met and no service-code exclusion/mandatory MD issue applies. `approved_units` is the sum of requested line units.
- Escalate to MD for benefit exclusions, mandatory MD review, unclear criteria, or adverse multi-line requests. Use `approved_units: null` for escalations.
- Use `benefit_exclusion_or_mandatory_md` for noncovered/experimental or mandatory-MD services, `adverse_multiline_request` for problematic multi-line requests, and `criteria_not_clearly_met` for missing/unclear criteria.
- `p2p_suitable` is usually true for evidence-remediable criteria gaps and false for approvals or hard benefit exclusions.
- Count MD escalations by service category and omit zero-count service categories from the map unless the template explicitly requires them.

## Pharmacy Appeal And Assistance

Target medication cases come from payload IDs or `medication_cases.target_bucket`.

Appeal path:

- Join `medication_cases -> members -> plans`, `appeals`, `drug_policy_requirements`, and `medication_trials`.
- Filing deadline is 60 days after `appeals.adverse_notice_date`. `deadline_status` is timely when `appeal_received_date <= filing_deadline`.
- `missing_policy_requirements` are required drug-policy keys not supported by documented requirement-specific evidence. Diagnosis usually comes from the medication case diagnosis; step therapy, topical failure, TB screen, and similar keys require matching documented trial or evidence rows.
- `appeal_ready` requires a timely appeal and no missing policy requirements. Timely but incomplete cases are `appeal_incomplete`; late cases are `appeal_not_timely`.
- If expedited attestation is present and the case is ready, use `expedited_accepted_72h`; if expedited is requested but evidence is missing, use `expedited_requested_needs_evidence`; otherwise `standard_30d`.

Manufacturer assistance:

- Join `assistance_programs` by drug and `household_financials` by member.
- Blocking reasons follow template order: `income_over_program_limit`, `commercial_insurance_required`, `government_plan_excluded`, `denial_letter_missing`, `assistance_consent_missing`.
- Staged data aligns with the 2025 contiguous-US FPL calculation `15650 + 5500 * (household_size - 1)` when comparing annual income to `max_income_fpl`; check the task year before reusing this constant.
- A route is manufacturer-team follow-up when only collectable documents/consent are missing or the case is assistance eligible. Fundamental income or plan-type blockers are `not_routed`.
- Keep payer appeal routing and manufacturer assistance routing separate. `path_separation` is `parallel_appeal_and_assistance` only when both paths remain active; otherwise choose `appeal_only`, `assistance_only`, or `no_active_route`.

## Reimbursement Compliance

Use scope periods, clinics, materiality thresholds, and active recovery statuses from the payload.

Paid-rate cell calculation:

- Assign quarters from `encounters.service_date`.
- Paid-rate compliance uses paid encounters only; denied or unpaid encounters are counted in `excluded_denied_or_unpaid_encounters` and excluded from paid-rate benchmark math.
- Match `rate_schedules` on payer, plan type, service category, CPT, applicable state, and effective date range. Benchmark amount is `units * benchmark_rate`.
- Group variance cells by quarter, clinic, payer, plan type, and service category. Aggregate paid encounters, units, paid amount, benchmark amount, paid/benchmark per unit, variance amount, and variance pct (`variance_amount / benchmark_amount`).
- A material underpayment cell meets all payload thresholds: enough paid units, underpayment amount at or above the dollar threshold, and underpayment pct at or above the percent threshold. Output `variance_amount` as paid minus benchmark, so underpayments are negative.
- `rate_schedule_rate_ids` should be distinct and sorted.

Clinic-quarter summaries:

- Aggregate paid-rate math at clinic-quarter level.
- Sum tracked recovery from `claim_corrections.expected_recovery_amount` for corrections whose status is in the payload's active recovery statuses and whose encounter is in scope.
- `material_underpayment_cells` is the count of flagged cells in that clinic-quarter. Use `high_review` when there is at least one material cell or material recovery concern; otherwise `compliant`.
- `top_recovery_opportunity` is the single largest active correction in scope, with deterministic tie-breakers such as earliest deadline then correction ID.

## Outpatient Rehab Profitability

Use `encounters`, `clinic_costs`, `clinic_budgets`, and `claim_corrections` for the scoped fiscal year, clinics, plan types, and service categories.

Cell calculation:

- Analyze cells by `clinic_id`, `plan_type`, and `service_category`.
- `open_recovery` is open claim correction recovery included in the action economics. Unless the payload defines a broader active list, use status `open`.
- `net_revenue = paid_amount + open_recovery`.
- `cost_per_unit = direct_cost_per_unit + allocated_overhead_per_unit`; `total_cost = units * cost_per_unit`.
- `net_margin = net_revenue - total_cost`; `margin_pct = net_margin / net_revenue` when revenue is nonzero.
- Join budget targets by clinic, fiscal year, payer, and service category. If budget has no plan-type dimension, apply the same service target to each scoped plan type.

Actions and ranking:

- `budget_variance_class` is `on_or_above_budget` when `margin_pct >= budget_margin_pct`; staged below-target cells use `major_shortfall`.
- `persistence_class` is `acceptable` for on-budget cells, `persistent` for below-budget cells with meaningful volume, and `noise` for low-volume below-budget cells. In staged examples, low volume is fewer than 5 encounters.
- For flagged cells, projected improvement is the revenue needed to hit the budget margin:

```text
required_revenue = total_cost / (1 - budget_margin_pct)
projected_improvement_amount = required_revenue - net_revenue
```

- Recommend `recover_and_rate_floor_review` when a below-budget flagged cell also has open recovery; otherwise `rate_floor_review`.
- Rank top loss drivers by most negative `net_margin`, take the top three, and assign ranks 1..3.
- Sort `payer_actions` and `payer_service_results` by clinic, plan type, and service category for reproducibility.

## Common Pitfalls

- Do not use the enum order in the template as a substitute for business precedence. Confirm hard-stop precedence from the prompt and target data.
- Do not double count clinical facts across multiple auth lines or claim corrections across multiple rate rows.
- For clinical evidence, `fact_value = 'met'` is not enough when `confidence_flag` is partial, stale, or conflicting.
- For authorization duplicates, statuses are open/approved rather than an `active` literal in staged data.
- For finance tasks, keep recovery opportunity separate from paid-rate compliance unless the specific profitability prompt says to include open recovery in net revenue.
- Use final rounding only after all sums, variances, and projected-improvement formulas are complete.
