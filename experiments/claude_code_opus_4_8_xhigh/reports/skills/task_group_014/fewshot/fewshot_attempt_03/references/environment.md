# Northstar operations environment — data model & access

Read-only HTTP environment shared across many tasks. Discover the live schema any
time with `GET /api/tables`; the tables below are the stable set.

## Access

- Base URL: the `GDPEVO_ENV_BASE_URL` value in `environment_access.md`
  (task packets reference it as `<TASK_ENV_BASE_URL>`).
- SQL auth: header `Authorization: Bearer <token>`, token from
  `environment_access.md`.
- `POST /sql/query` body `{"sql": "<one SELECT>"}` → `{columns, rows, row_count,
  max_rows: 500, limited}`. One statement only; writes/multi-statement rejected.
  If `limited` is true the 500-row cap truncated the result — filter more tightly.
- REST (auth optional in practice, but send the header anyway): `GET /`,
  `/portal`, `/api/tables`, `/api/cases`, `/api/cases/{id}`, `/api/policies`,
  `/api/policies/{id}`, `/api/documents/{id}`, `/api/rate-schedules`,
  `/api/appeals`. `/api/cases/{id}` bundles the case with its criteria,
  authorizations, appeals, claims, and documents — a fast way to orient before
  precise SQL.

## Tables (name: columns)

- **cases**: case_id, member_id, provider_id, request_type, service_domain,
  policy_id, request_date, due_date, current_stage, current_status, urgency,
  summary
- **members**: member_id, patient_name, dob, plan_id, plan_type, product,
  employer_group, member_status
- **plans**: plan_id, payer_name, plan_type, state, network, effective_start,
  effective_end, notes
- **providers**: provider_id, provider_name, specialty, npi, phone, fax,
  organization
- **request_lines**: line_id, case_id, cpt_code, modifier, service_name,
  requested_units, requested_start, requested_end, diagnosis_codes, billed_charge
- **policies**: policy_id, policy_name, version, effective_start, effective_end,
  precedence, summary
- **policy_criteria**: criterion_id, policy_id, criterion_key, criterion_text,
  approval_required, result_if_missing  *( `result_if_missing` ∈ pend/deny — tells
  you whether an unmet/missing criterion pends or denies )*
- **case_criteria**: case_id, criterion_id, result, evidence_fact_ids,
  gap_description, reviewer_scope  *( `result` ∈ met/not_met/partial/unclear/
  not_applicable — maps straight into `criteria_results` )*
- **documents**: document_id, case_id, document_type, document_date,
  received_date, source_system, is_current, title, summary  *( `is_current` 1 =
  current evidence, 0 = stale/excluded export )*
- **document_facts**: fact_id, document_id, case_id, fact_key, fact_value,
  numeric_value, unit, supports_criteria
- **authorizations**: auth_id, case_id, auth_number, status, approved_units,
  approved_start, approved_end, approved_cpt (comma-joined), approved_modifier,
  denial_reason
- **appeals**: appeal_id, case_id, denial_date, received_date,
  appeal_type_requested, appeal_path, expedited_attestation, appeal_deadline,
  outcome, owner, notes
- **drug_trials**: trial_id, case_id, medication, outcome, documented (1/0),
  start_date, end_date, notes
- **assistance_screen**: case_id, program_name, income_percent_fpl, insurance_type,
  denial_required, denial_on_file, missing_fields (comma-joined), assistance_status
- **claims**: claim_id, member_id, case_id, payer, received_date, claim_status,
  auth_number, billed_total, paid_total
- **claim_lines**: claim_line_id, claim_id, line_number, cpt_code, modifier, units,
  billed_amount, paid_amount, denial_code, service_date
- **payment_benchmarks**: benchmark_id, payer, plan_type, service_domain,
  cpt_code, modifier, effective_start, effective_end, allowed_amount, source_name,
  source_version
- **p2p_events**: p2p_id, case_id, scheduled_at, duration_minutes,
  provider_argument, new_information, outcome, final_status, reviewer, notes
- **service_margin**: month_id, period, payer, payer_segment, service_domain,
  cpt_code, visits, net_revenue, variable_cost, fixed_cost_allocated,
  charge_sensitive (1/0)

## Scoping & distractors

- Filter by the exact `target_business_id` from `task_context` and follow foreign
  keys (`case_id`, `claim_id`, `appeal_id`, `month_id`). Records for other cases
  will be present — ignore them.
- Reference tables (`payment_benchmarks`, `policy_criteria`) are keyed by business
  attributes, not case_id. Select by payer/plan_type/service_domain/cpt/modifier
  **and** the effective date window around the task's `reporting_date`. Multiple
  rows can match on keys; the one in the effective window is current, an
  out-of-window row for the same key is the stale/rejected source. Rows whose ID
  stem belongs to a different task are distractors.
