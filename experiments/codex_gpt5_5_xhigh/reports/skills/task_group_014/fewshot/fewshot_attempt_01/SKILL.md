---
name: sql-payer-ops
description: Solve payer-operations SQL tasks that require scoped JSON outputs for authorization intake, clinical review, medication appeals, reimbursement compliance, or payer-service profitability.
---

# SQL Payer Operations

Use this skill when a task provides payer-operations payloads and asks for a JSON answer built from a remote SQLite query service.

## Access And Ground Rules

- Read `environment_access.md` first. It contains the runtime base URL and HTTP Basic Auth credentials. Do not hard-code the concrete host in notes, code, or final answers.
- Query only through the SQL endpoint described there, with JSON shaped like `{"sql":"SELECT ...","params":[]}`.
- Use read-only SQLite statements only. Do not assume a local database file exists.
- Use `input/payloads/answer_template.json` as the output contract. Return exactly one JSON object, with the same top-level shape and enum spelling.
- Scope every query from the payload, not from broad database contents. Typical scope files provide target case IDs, target buckets, clinic lists, periods, plan types, service categories, materiality thresholds, or active correction statuses.

Useful discovery queries:

```sql
SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name;
SELECT name, sql FROM sqlite_master WHERE type = 'table' ORDER BY name;
PRAGMA table_info(table_name);
```

Core table groups:

- Authorization intake/review: `authorization_requests`, `auth_lines`, `members`, `plans`, `providers`, `facilities`, `service_codes`, `existing_authorizations`, `state_sla_rules`.
- Clinical evidence: `coverage_criteria`, `criteria_sources`, `clinical_facts`, `evidence_documents`, `case_review_events`, `p2p_sessions`.
- Medication appeals/assistance: `medication_cases`, `appeals`, `drug_policy_requirements`, `medication_trials`, `assistance_programs`, `household_financials`, plus `members` and `plans`.
- Reimbursement/profitability: `encounters`, `rate_schedules`, `claim_corrections`, `clinic_costs`, `clinic_budgets`.

## General Output Conventions

- Sort case-level rows by the case ID requested by the template: `case_id` ascending for authorizations, `med_case_id` ascending for medication cases.
- Sort financial clinic results by `clinic_id`, then period/quarter. Sort payer-service detail by `clinic_id`, `plan_type`, `service_category`.
- Use JSON numbers, booleans, arrays, and `null` exactly as implied by the template. Do not stringify numbers or booleans.
- Round money and per-unit rates to 2 decimals. Round ratios and percentages represented as decimals to 4 decimals.
- Summary counts must be recomputed from the final detail rows, not separately guessed.

## Authorization Intake Audits

Scope cases from the payload's explicit `target_case_ids` or the specified `authorization_requests.target_bucket`.

Build one joined working set with request, member, plan, requesting provider, servicing provider, facility, lines, and service-code rules. Keep provider sanction/credential follow-up separate from the intake disposition.

Recommended fail-fast intake order:

1. `active_coverage`: member coverage does not cover the request/service window. Consider `coverage_start`, `coverage_end`, and any retro reinstatement field.
2. `cob_completion`: `authorization_requests.cob_primary_processed = 0`.
3. `covered_service`: any requested line has `service_codes.covered = 0`.
4. `network`: requesting/servicing provider is out of network without an allowed exception.
5. `service_area`: facility is outside service area and `oon_exception` is not set.
6. `pa_required`: requested codes are notification-only or no prior auth is required.
7. `retrospective_submission`: `rendered_before_submission = 1`.
8. `duplicate_authorization`: overlapping active existing authorization for the same member and requested CPT.
9. `none`: no intake halt.

Duplicate matching is line-level: join `existing_authorizations` by `member_id` and `cpt_code`, require overlapping service date ranges, and keep only active/open/approved statuses. Return sorted matching `existing_auth_id` values.

Gold card is evaluated only if no intake halt exists. A safe auto-approval requires all of:

- plan allows gold carding;
- requesting provider has active gold-card status;
- provider credentials are active and sanctions are not active;
- all services are covered, PA-required if relevant, not excluded from gold card, and not mandatory MD review.

If gold card does not apply, route to review:

- external vendor queue from `service_codes.external_vendor` when present, for example imaging, DME, or home-health vendor queues;
- `Medical Director Review` when any line requires mandatory MD review;
- otherwise `Nurse Clinical Review`.

SLA:

- Start from `authorization_requests.receipt_timestamp`.
- Use `urgency_attested`: routine uses days; urgent/stat use hours.
- Prefer `state_sla_rules` for the plan state and plan type; fall back to plan SLA fields if needed.
- For routine business-day rules, add business days and skip Saturdays/Sundays. Calendar-day rules add calendar days.
- `sla_basis` should describe state, plan type, day type, and count. If the plan state and facility state both have applicable rules and create a conflict/special basis, reflect both states in the text.

Provider item:

- `requesting_provider_active_sanction` when the requesting provider has active sanctions.
- `requesting_provider_credentials_inactive` when credentials are inactive.
- `none` otherwise.

Notice flag:

- Usually true for adverse denials/halts such as noncovered service, duplicate, retrospective halt, network/service-area denial.
- Usually false for pure administrative holds such as COB completion.

## Clinical Review Slates

Scope authorizations from the payload and review date. Join request, plan, auth lines, service codes, criteria, and clinical facts.

Criteria source:

- Use `criteria_sources.precedence_rank` to choose the highest-precedence source applicable to the plan type and service category.
- A plan-specific source only applies if it has criteria rows for the requested service category. Otherwise use the applicable `ALL` policy source with criteria for that service.
- Return the selected `criteria_source_id`.

Evidence evaluation:

- Required criteria come from `coverage_criteria` for the selected source, service category, and plan filter (`plan_type` or `ALL`) where `is_required_for_approval = 1`.
- A criterion is satisfied only when a matching `clinical_facts` row has `fact_value = required_value` and `confidence_flag = 'clear'`.
- Treat missing rows, `not_met`, `unclear`, `partial`, `stale`, and `conflicting` evidence as missing evidence.
- Return `missing_evidence_keys` in criteria order, usually by criterion/source rank then key.

Recommendation:

- If every required criterion is clearly satisfied, use `approve_as_requested`, `md_escalation_required = false`, reason `none`, `p2p_suitable = false`, and `approved_units = authorization_requests.requested_total_units`.
- Otherwise use `escalate_to_md`, `approved_units = null`, and `md_escalation_required = true`.
- Use `benefit_exclusion_or_mandatory_md` when the service is noncovered, benefit-excluded, or mandatory MD review.
- Use `adverse_multiline_request` for adverse/prior-denied multi-line requests.
- Use `criteria_not_clearly_met` for ordinary evidence gaps.
- `p2p_suitable` is usually true for clinical evidence gaps that a provider discussion could cure, and false for approvals or benefit-exclusion/mandatory-MD cases.

Queue counts are derived from final rows: count MD escalations by service category, total MD escalations, nurse approvals, and P2P-suitable cases.

## Medication Appeal And Assistance Dockets

Scope `medication_cases` from payload IDs or `target_bucket`. Join member, plan, appeal, household financials, drug policy requirements, trials, and assistance program.

Appeal route:

- Filing deadline is 60 calendar days after `appeals.adverse_notice_date`.
- `deadline_status` is `timely_received` when `appeal_received_date <= filing_deadline`; otherwise `late_received`.
- Filter drug requirements by `drug_name` and applicable plan type (`plan_type_filter = plan_type` or `ALL`).
- Diagnosis requirements are satisfied from the medication case diagnosis when it matches the drug policy intent.
- Step/topical/trial requirements require documented medication-trial evidence with an appropriate failed, contraindicated, or adverse outcome. Undocumented trials do not satisfy requirements.
- Missing policy requirements are the unsatisfied requirement keys, ordered by requirement rank/key.
- `appeal_not_timely` overrides readiness if the appeal was received late.
- If timely and no missing policy requirements, use `appeal_ready`; otherwise `appeal_incomplete`.
- Expedited classification:
  - `standard_30d` when expedited attestation is not present.
  - `expedited_accepted_72h` when attestation is present and the appeal is ready.
  - `expedited_requested_needs_evidence` when attestation is present but policy evidence is missing.
- `next_step` should be a short enum-style action derived from the missing key or readiness, for example collect the missing requirement then submit, submit expedited appeal, or submit standard appeal.

Manufacturer assistance route:

- Join `assistance_programs` by `drug_name`.
- Use household income against the program's `max_income_fpl`. For 2025-style tasks, 100% FPL is commonly `15650 + 5500 * (household_size - 1)` for the contiguous US; compare `annual_income` to `max_income_fpl / 100 * FPL`.
- Blocking reasons, in this order:
  - `income_over_program_limit`;
  - `commercial_insurance_required`;
  - `government_plan_excluded`;
  - `denial_letter_missing`;
  - `assistance_consent_missing`.
- `assistance_eligible` only when no blocking reasons exist.
- Route to `manufacturer_assistance_team` when eligible or when only document/consent collection is blocking. Use `not_routed` for income or government-plan/commercial-insurance blocks.
- Preserve payer appeal routing separately from manufacturer assistance. Set `path_separation` from the two routes:
  - `parallel_appeal_and_assistance` when both appeal and manufacturer follow-up are active;
  - `appeal_only` when only payer appeal is active;
  - `assistance_only` when only manufacturer assistance is active;
  - `no_active_route` when neither is active.

## Reimbursement Compliance Exception Logs

Scope clinics, periods, materiality thresholds, and active recovery statuses from `audit_scope.json`.

Rate compliance uses only clean paid encounters with an applicable rate schedule:

```sql
e.paid_amount > 0 AND e.denial_code IS NULL
```

Join `rate_schedules` on:

- `payer`;
- `plan_type`;
- `service_category`;
- `cpt_code`;
- clinic state from the audit scope;
- `service_date BETWEEN effective_start AND effective_end`.

Clinic-quarter results:

- `paid_encounters`, `paid_units`, `paid_amount`, and `benchmark_amount` are computed only from clean paid encounters with a matching rate schedule.
- `benchmark_amount = SUM(units * benchmark_rate)`.
- `variance_amount = paid_amount - benchmark_amount`.
- `variance_pct = variance_amount / benchmark_amount` when benchmark is nonzero.
- `excluded_denied_or_unpaid_encounters` counts scoped encounters in the period where `paid_amount <= 0`, `paid_amount IS NULL`, or `denial_code IS NOT NULL`. Count these even if no rate schedule matches.
- `tracked_recovery_amount` sums `claim_corrections.expected_recovery_amount` for active statuses from the payload, joined to scoped encounters with a denial code. Keep recovery separate from paid-rate compliance math.

Flagged variance cells:

- Group clean paid, rate-matched encounters by quarter, clinic, payer, plan type, and service category.
- Include a cell when all materiality checks pass:
  - `paid_units >= minimum_paid_units`;
  - `benchmark_amount - paid_amount >= minimum_underpayment_amount`;
  - `(benchmark_amount - paid_amount) / benchmark_amount >= minimum_underpayment_pct`.
- Return paid and benchmark per-unit rates as paid/units and benchmark/units.
- `rate_schedule_rate_ids` is the sorted unique list of rate IDs used in the cell.
- Classification is `material_underpayment` for flagged cells.

Top recovery opportunity:

- Use active statuses from the payload.
- Join correction to encounter and period/clinic scope.
- Prefer corrections tied to denial-coded encounters.
- Pick the highest `expected_recovery_amount`; use deterministic tie-breakers such as deadline then correction ID.

Summary:

- `material_underpayment_cell_count` is the number of flagged variance cells.
- `total_tracked_recovery_amount` is the sum of tracked recovery amounts across clinic-quarter results.
- Clinic-quarter classification is usually `high_review` when material cells or tracked recovery exist, otherwise `compliant` unless the template defines more specific enums.

## Outpatient Rehab Profitability Action Lists

Scope the analysis period, fiscal year, clinics, plan types, and service categories from `worklist_scope.json`.

Aggregate payer-service cells by `clinic_id`, `plan_type`, and `service_category`:

- `encounter_count = COUNT(*)`;
- `units = SUM(units)`;
- `paid_amount = SUM(paid_amount)`;
- `open_recovery = SUM(expected_recovery_amount)` from `claim_corrections` where `status = 'open'`;
- `net_revenue = paid_amount + open_recovery`;
- `cost_per_unit = clinic_costs.direct_cost_per_unit + clinic_costs.allocated_overhead_per_unit`;
- `total_cost = units * cost_per_unit`;
- `net_margin = net_revenue - total_cost`;
- `margin_pct = net_margin / net_revenue` when net revenue is nonzero.

Budget target:

- Join `clinic_budgets` by clinic, fiscal year, payer, and service category. These budgets are service-level, not plan-type-specific.
- When multiple rows exist for the same clinic/service, use the highest `expected_margin_pct` as the budget target.

Classifications:

- `on_or_above_budget` when `margin_pct >= budget_margin_pct`.
- `major_shortfall` when `margin_pct < budget_margin_pct`.
- `acceptable` persistence for on-budget cells.
- For shortfall cells, use `persistent` when encounter volume is meaningful (for example at least 5 encounters) and `noise` for very low volume.

Actions:

- Include payer actions for shortfall cells.
- `recommended_action = 'recover_and_rate_floor_review'` when a shortfall cell also has open recovery; otherwise `rate_floor_review`.
- `projected_improvement_amount = total_cost / (1 - budget_margin_pct) - net_revenue`, rounded to 2 decimals. This is the additional net revenue needed to reach the budget margin.
- Rank the top three loss drivers by most negative `net_margin`; tie-break deterministically by clinic, plan type, and service category.

Portfolio summary:

- `cells_analyzed` is the number of scoped payer-service cells returned.
- `flagged_pair_count` is the number of shortfall/action cells.
- Totals are sums over the payer-service detail rows after rounding inputs consistently.

## Common Pitfalls

- Do not use the whole database when the payload gives a scope.
- Do not treat `member.cob_primary_status` alone as a COB intake halt; the request-level processed flag is the decisive field.
- Do not auto-approve gold-card cases before checking intake halts and duplicates.
- Do not count partial, stale, or conflicting clinical facts as satisfying criteria.
- Do not merge payer appeal readiness with manufacturer assistance routing; they are separate paths.
- Do not include denial-coded encounters in paid-rate compliance, even if they have a positive paid amount.
- Do not fold recovery opportunities into reimbursement variance math. Recovery is a separate field.
- In profitability, do include open recoveries in net revenue, but only for the open-recovery profitability task.
- Always recompute summary counts from final rows and round only at the output boundary or at the same aggregate level the template expects.
