# Northstar Payer-Operations Environment — Access & Data Model

Reference for the shared read-only portal. Confirm live at runtime with
`GET /api/tables` (schema may evolve); this document reflects the observed shape.

## HTTP access

- **Base URL**: from `task_context.environment.base_url`; if literal
  `<TASK_ENV_BASE_URL>`, use `GDPEVO_ENV_BASE_URL` from `environment_access.md`.
- **Auth**: `Authorization: Bearer <token>` (e.g. the `pa-review-token-…` value in the
  task/`environment_access.md`). Required for `POST /sql/query`. GET business endpoints
  respond without auth but sending the header is fine.

### Business (GET) endpoints
- `GET /` and `GET /portal` — HTML landing pages (entry-point list; not data).
- `GET /api/tables` — schema: every table with columns, types, PK/not-null flags.
- `GET /api/cases` — list of cases (joined with member/provider summary fields).
- `GET /api/cases/{case_id}` — **bundled** case: nested `criteria`, `authorizations`,
  `documents`, `claims`, `appeals`, `assistance_screen`, `request_lines`, `p2p_events`,
  `drug_trials`. Fastest way to load a case's related rows.
- `GET /api/policies`, `GET /api/policies/{policy_id}` — policy + its `policy_criteria`.
- `GET /api/documents/{document_id}` — a document (and its facts).
- `GET /api/rate-schedules` — payment benchmark schedules.
- `GET /api/appeals` — appeals list.

### SQL endpoint
`POST /sql/query` with JSON body `{"sql": "SELECT ..."}` and the bearer header.
- Read-only: only `SELECT`, `WITH`, and `PRAGMA table_info(...)` are allowed; writes
  return `{"error":"invalid_sql", ...}`.
- Response: `{"columns":[...], "rows":[{...}], "row_count":N, "max_rows":500, "limited":bool}`.
- Results are capped at 500 rows (`limited:true` if truncated) — filter by the target id.
- Do **not** attempt to read DB/source/manifest/setup files; use these endpoints only.

Use `scripts/nsql.py` to run a query:
`python3 scripts/nsql.py "SELECT * FROM cases WHERE case_id='<ID>'"`
(reads base URL from `--base`/`GDPEVO_ENV_BASE_URL`, token from `--token`/`NS_TOKEN`).

## Tables (columns; `*` = primary key)

- **cases**: case_id*, member_id, provider_id, request_type, service_domain, policy_id,
  request_date, due_date, current_stage, current_status, urgency, summary
- **members**: member_id*, patient_name, dob, plan_id, plan_type, product,
  employer_group, member_status
- **plans**: plan_id*, payer_name, plan_type, state, network, effective_start,
  effective_end, notes
- **providers**: provider_id*, provider_name, specialty, npi, phone, fax, organization
- **policies**: policy_id*, policy_name, version, effective_start, effective_end,
  precedence, summary
- **policy_criteria**: criterion_id*, policy_id, criterion_key, criterion_text,
  approval_required, result_if_missing  *(result_if_missing ∈ pend/deny/…)*
- **case_criteria**: case_id*, criterion_id*, result, evidence_fact_ids, gap_description,
  reviewer_scope  *(result ∈ met/not_met/partial/unclear/not_applicable)*
- **request_lines**: line_id*, case_id, cpt_code, modifier, service_name,
  requested_units, requested_start, requested_end, diagnosis_codes, billed_charge
- **authorizations**: auth_id*, case_id, auth_number, status, approved_units,
  approved_start, approved_end, approved_cpt (comma-joined), approved_modifier,
  denial_reason
- **documents**: document_id*, case_id, document_type, document_date, received_date,
  source_system, is_current (1=current, 0=stale), title, summary
- **document_facts**: fact_id*, document_id, case_id, fact_key, fact_value,
  numeric_value, unit, supports_criteria
- **appeals**: appeal_id*, case_id, denial_date, received_date, appeal_type_requested,
  appeal_path, expedited_attestation, appeal_deadline, outcome, owner, notes
- **drug_trials**: trial_id*, case_id, medication, outcome, documented (1/0),
  start_date, end_date, notes
- **assistance_screen**: case_id*, program_name, income_percent_fpl, insurance_type,
  denial_required, denial_on_file, missing_fields, assistance_status
- **p2p_events**: p2p_id*, case_id, scheduled_at, duration_minutes, provider_argument,
  new_information, outcome, final_status, reviewer, notes
- **claims**: claim_id*, member_id, case_id, payer, received_date, claim_status,
  auth_number, billed_total, paid_total
- **claim_lines**: claim_line_id*, claim_id, line_number, cpt_code, modifier, units,
  billed_amount, paid_amount, denial_code, service_date
- **payment_benchmarks**: benchmark_id*, payer, plan_type, service_domain, cpt_code,
  modifier, effective_start, effective_end, allowed_amount, source_name, source_version
- **service_margin**: month_id*, period, payer, payer_segment, service_domain, cpt_code,
  visits, net_revenue, variable_cost, fixed_cost_allocated, charge_sensitive (1/0)

## Notes / pitfalls

- The DB holds many unrelated cases/benchmarks/margin rows (distractor `…-D-…`, alt
  plan_types, distractor schedules). Always filter to the target id / listed row IDs.
- `payment_benchmarks` includes stale/legacy and distractor schedules for the same CPT.
  Select the row whose `payer` + `plan_type` (from the member's plan) + `service_domain`
  + `cpt_code` + `modifier` match and whose `effective_start..effective_end` covers the
  service/reporting date; treat expired or distractor schedules as the rejected source.
- `approved_cpt` is a comma-joined string — split it and sort ascending when the
  template asks for a CPT list.
- `documents.is_current` distinguishes current evidence (1) from stale exports (0).
