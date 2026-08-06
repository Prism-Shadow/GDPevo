# Environment data model

Read-only Northstar payer-operations store. Confirm live columns with `GET /api/tables` or
`PRAGMA table_info(<table>)` before relying on this list — treat it as a map, not a guarantee.
Every table mixes real target rows with `-TE-` (held-out) and `-D-` (distractor) rows; always
filter by the exact target id from `task_context.json`.

## Access

- SQL: `POST /sql/query`, body `{"sql": "SELECT ..."}` (key is `sql`). SELECT / WITH /
  PRAGMA only. Response `{columns, rows, row_count, limited, max_rows: 500}`.
- REST (auth header required on every call):
  - `GET /api/tables` — schema for all tables.
  - `GET /api/cases` / `GET /api/cases/{case_id}` — the id form returns a **bundle**:
    `case`, plus nested `criteria` (case_criteria joined to policy_criteria, so each row
    carries both `result` and `result_if_missing`), `authorizations`, `appeals`,
    `assistance_screen`, `claims`.
  - `GET /api/policies` / `GET /api/policies/{policy_id}`.
  - `GET /api/documents/{document_id}`.
  - `GET /api/appeals` — appeals joined with case fields (patient_name, plan_type, summary).
  - `GET /api/rate-schedules` — all `payment_benchmarks` rows.
  - `GET /api/portal`, `GET /`.

## Tables (columns)

- **cases**: case_id, member_id, provider_id, request_type, service_domain, policy_id,
  request_date, due_date, current_stage, current_status, urgency, summary
- **members**: member_id, patient_name, dob, plan_id, plan_type, product, employer_group,
  member_status
- **plans**: plan_id, payer_name, plan_type, state, network, effective_start, effective_end,
  notes
- **providers**: provider_id, provider_name, specialty, npi, phone, fax, organization
- **policies**: policy_id, policy_name, version, effective_start, effective_end, precedence,
  summary
- **policy_criteria**: criterion_id, policy_id, criterion_key, criterion_text,
  approval_required, `result_if_missing` (pend / deny / uphold / …)
- **case_criteria**: case_id, criterion_id, `result` (met / not_met / partial / unclear /
  not_applicable), evidence_fact_ids, gap_description, reviewer_scope
- **request_lines**: line_id, case_id, cpt_code, modifier, service_name, requested_units,
  requested_start, requested_end, diagnosis_codes, billed_charge
- **documents**: document_id, case_id, document_type, document_date, received_date,
  source_system, `is_current` (1 = evidence, 0 = stale/excluded), title, summary
- **document_facts**: fact_id, document_id, case_id, fact_key, fact_value, numeric_value,
  unit, `supports_criteria` (criterion_id this fact substantiates, or null)
- **authorizations**: auth_id, case_id, auth_number, status, approved_units, approved_start,
  approved_end, approved_cpt (comma-joined), approved_modifier, denial_reason
- **appeals**: appeal_id, case_id, denial_date, received_date, appeal_type_requested,
  appeal_path, expedited_attestation, appeal_deadline, outcome, owner, notes
- **assistance_screen**: case_id, program_name, income_percent_fpl, insurance_type,
  denial_required, denial_on_file, missing_fields, assistance_status
- **drug_trials**: trial_id, case_id, medication, outcome, `documented` (1/0), start_date,
  end_date, notes
- **p2p_events**: p2p_id, case_id, scheduled_at, duration_minutes, provider_argument,
  new_information, outcome, final_status, reviewer, notes
- **claims**: claim_id, member_id, case_id, payer, received_date, claim_status, auth_number,
  billed_total, paid_total
- **claim_lines**: claim_line_id, claim_id, line_number, cpt_code, modifier, units,
  billed_amount, paid_amount, denial_code, service_date
- **payment_benchmarks**: benchmark_id, payer, plan_type, service_domain, cpt_code, modifier,
  effective_start, effective_end, allowed_amount, source_name, source_version
- **service_margin**: month_id, period, payer, payer_segment, service_domain, cpt_code,
  visits, net_revenue, variable_cost, fixed_cost_allocated, charge_sensitive

## Join map (target id → what to pull)

- A case/authorization/P2P id → cases → members/plans, request_lines, policies +
  policy_criteria, case_criteria, documents + document_facts, authorizations, p2p_events.
- An appeal id → appeals + its case → case_criteria, drug_trials, documents,
  assistance_screen, policy_criteria.
- A claim id → claims + claim_lines → member plan_type, payment_benchmarks (by
  service_domain/cpt/modifier/plan_type/date).
- A finance-queue id / month_ids → service_margin rows named in the memo's `queue_row_ids`.
