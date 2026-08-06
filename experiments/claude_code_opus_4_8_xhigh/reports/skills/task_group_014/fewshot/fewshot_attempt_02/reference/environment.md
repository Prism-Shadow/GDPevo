# Northstar payer-operations environment — schema & endpoint catalog

Read-only shared environment for utilization management, appeals, payment review, and
queue analysis. Connect using the base URL and bearer token from `environment_access.md`
and `task_context.json`. Do **not** open any underlying data/source/db files — use the
network only.

## Connection

- Base URL: value of `<TASK_ENV_BASE_URL>` (observed: `http://task-env:9014/`).
- SQL: `POST /sql/query`
  - Header: `Authorization: Bearer <token>` (observed: `pa-review-token-014`).
  - Body: `{"sql": "SELECT ..."}`. Only `SELECT`, `WITH`, `PRAGMA table_info` allowed;
    non-SELECT is rejected (`invalid_sql`). Response: `{columns, rows, row_count,
    max_rows: 500, limited}`. Add `LIMIT` and precise `WHERE` filters — there are many
    distractor rows.
- Business GET endpoints (token optional in practice, but send it anyway):
  - `GET /` — HTML portal index.
  - `GET /portal` — portal page.
  - `GET /api/tables` — full schema: every table with column name/type/pk/not_null.
  - `GET /api/cases` — list of cases (many decoys) with joined member/provider/plan.
  - `GET /api/cases/{case_id}` — **single case bundle** (see below). Best entry point
    for any case-linked task.
  - `GET /api/policies`, `GET /api/policies/{policy_id}` — policy + its criteria.
  - `GET /api/documents/{document_id}` — document + its `facts`.
  - `GET /api/rate-schedules` — all `payment_benchmarks` rows (includes decoy schedules).
  - `GET /api/appeals` — appeals with current stage/status.

### `GET /api/cases/{case_id}` bundle

Returns `{"case": {...}}` where the case object flattens member/provider/plan fields and
carries these related lists (empty when N/A for that case):
`criteria` (case_criteria joined with policy_criteria: adds `criterion_text`,
`approval_required`, `result_if_missing`), `documents`, `document_facts`,
`request_lines`, `authorizations`, `appeals`, `assistance_screen`, `drug_trials`,
`p2p_events`, `claims`.

## Tables (from `GET /api/tables`)

Core / membership:
- `cases` — case_id, member_id, provider_id, request_type, service_domain, policy_id,
  request_date, due_date, current_stage, current_status, urgency, summary
- `members` — member_id, patient_name, dob, plan_id, plan_type, product,
  employer_group, member_status
- `providers` — provider_id, provider_name, specialty, npi, phone, fax, organization
- `plans` — plan_id, payer_name, plan_type, state, network, effective_start,
  effective_end, notes
- `policies` — policy_id, policy_name, version, effective_start, effective_end,
  precedence, summary
- `policy_criteria` — criterion_id, policy_id, criterion_key, criterion_text,
  approval_required, result_if_missing (`pend`/`deny` when the criterion is missing)

Clinical / determination:
- `request_lines` — line_id, case_id, cpt_code, modifier, service_name,
  requested_units, requested_start, requested_end, diagnosis_codes, billed_charge
- `case_criteria` — case_id, criterion_id, result (met/not_met/partial/unclear/…),
  evidence_fact_ids, gap_description, reviewer_scope
- `documents` — document_id, case_id, document_type, document_date, received_date,
  source_system, **is_current** (1 = current evidence, 0 = stale/superseded export),
  title, summary
- `document_facts` — fact_id, document_id, case_id, fact_key, fact_value,
  numeric_value, unit, supports_criteria
- `authorizations` — auth_id, case_id, auth_number, status
  (`recommended_approval`/`denied`/…), approved_units, approved_start, approved_end,
  approved_cpt (comma-joined), approved_modifier, denial_reason

Appeals / pharmacy:
- `appeals` — appeal_id, case_id, denial_date, received_date, appeal_type_requested,
  appeal_path (standard_internal/expedited_internal/external_review/not_eligible),
  expedited_attestation, appeal_deadline, outcome, owner, notes (notes often lists the
  required packet items)
- `drug_trials` — trial_id, case_id, medication, outcome, **documented** (1/0),
  start_date, end_date, notes
- `assistance_screen` — case_id, program_name, income_percent_fpl, insurance_type,
  denial_required, denial_on_file, missing_fields, assistance_status

Claims / payment:
- `claims` — claim_id, member_id, case_id, payer, received_date, claim_status,
  auth_number, billed_total, paid_total
- `claim_lines` — claim_line_id, claim_id, line_number, cpt_code, modifier, units,
  billed_amount, paid_amount, denial_code, service_date
- `payment_benchmarks` — benchmark_id, payer, plan_type, service_domain, cpt_code,
  modifier, effective_start, effective_end, allowed_amount, source_name, source_version.
  Multiple sources exist (current schedule, legacy/stale export, decoy "Distractor"
  schedule). Pick by payer+plan_type+service_domain+cpt+modifier AND the effective
  window covering the line's service_date; prefer ids in the target's own namespace.

P2P / finance:
- `p2p_events` — p2p_id, case_id, scheduled_at, duration_minutes, provider_argument,
  new_information, outcome (overturn_to_approval/uphold_intended_adverse_decision),
  final_status, reviewer, notes
- `service_margin` — month_id, period, payer, payer_segment
  (medicaid/commercial/workers_comp), service_domain, cpt_code, visits, net_revenue,
  variable_cost, fixed_cost_allocated, charge_sensitive (1/0)

## Distractor awareness

- ~160 cases exist; only your target id matters. Decoy cases use ids like `CASE-D-*`.
- `payment_benchmarks` includes a "Northstar Distractor Schedule" and duplicate rows
  from other task namespaces (e.g. `BM-TE-005-*`). Match on the operative keys and the
  correct effective window; prefer the benchmark id in your claim's own id namespace.
- Records for the real task typically share the target's `-TR-00N-` id stem.
