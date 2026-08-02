# Environment contract & data model

Cached reference for the Northstar payer-operations environment. Re-fetch
`GET /api/tables` at run time to confirm — shapes can vary per task group.

## Access

- **Base URL:** resolve `<TASK_ENV_BASE_URL>` from `GDPEVO_ENV_BASE_URL` in
  `environment_access.md` (observed default `http://task-env:9014/`).
- **Auth:** `Authorization: Bearer <token>` on every request (observed default token
  `pa-review-token-014`). Read the actual token from `environment_access.md`; do not
  assume it across environments.

### `POST /sql/query`
- Body: `{"sql": "<statement>"}`.
- Allowed statements only: `SELECT`, `WITH`, `PRAGMA table_info`. Writes/DDL rejected
  with `{"error":"invalid_sql","message":"only SELECT, WITH, and PRAGMA table_info statements are allowed"}`.
- Success: `{"columns":[...], "rows":[{col:val,...}], "row_count":N, "limited":bool, "max_rows":500}`.
- Errors: `{"error":"unauthorized"}` (bad/missing token); `{"error":"sql_error","message":...}`
  (bad SQL/table/column).
- **Result cap 500 rows.** Always filter by the target ID / period so you never depend on
  truncated output; if `limited` is true, tighten the query.

### REST endpoints (read-only, same auth)
`GET /`, `GET /portal`, `GET /api/tables`, `GET /api/cases`, `GET /api/cases/{case_id}`,
`GET /api/policies`, `GET /api/policies/{policy_id}`, `GET /api/documents/{document_id}`,
`GET /api/rate-schedules`, `GET /api/appeals`. List responses are wrapped, e.g.
`{"appeals":[...]}`, `{"rate_schedules":[...], "count":N}`. Use only endpoints listed in
`environment_access.md`.

**Do not** read source/generated/SQLite files, manifests, or setup scripts directly.

## Tables (columns)

- **cases** — case_id (PK), member_id, provider_id, request_type, service_domain,
  policy_id, request_date, due_date, current_stage, current_status, urgency, summary.
  *Entry point for most tasks. `request_type`/`service_domain`/`current_stage` identify the archetype.*
- **members** — member_id (PK), patient_name, dob, plan_id, plan_type, product,
  employer_group, member_status.
- **plans** — plan_id (PK), payer_name, plan_type, state, network, effective_start,
  effective_end, notes.
- **providers** — provider_id (PK), provider_name, specialty, npi, phone, fax, organization.
- **request_lines** — line_id (PK), case_id, cpt_code, modifier, service_name,
  requested_units, requested_start, requested_end, diagnosis_codes, billed_charge.
  *The requested service line(s) for a prior-auth/P2P case.*
- **policies** — policy_id (PK), policy_name, version, effective_start, effective_end,
  precedence, summary.
- **policy_criteria** — criterion_id (PK), policy_id, criterion_key, criterion_text,
  approval_required (1/0), result_if_missing (`pend`/`deny`/`uphold`).
  *Defines each criterion; `approval_required=0` are informational.*
- **case_criteria** — case_id+criterion_id (PK), result (`met`/`not_met`/`partial`/`unclear`),
  evidence_fact_ids, gap_description, reviewer_scope.
  *The actual per-case criterion results — usually source them straight from here.*
- **documents** — document_id (PK), case_id, document_type, document_date, received_date,
  source_system, is_current (1/0), title, summary.
  *`is_current=1` → evidence; `is_current=0` (stale_export / legacy source) → excluded.*
- **document_facts** — fact_id (PK), document_id, case_id, fact_key, fact_value,
  numeric_value, unit, supports_criteria.
- **authorizations** — auth_id (PK), case_id, auth_number, status, approved_units,
  approved_start, approved_end, approved_cpt (comma-joined), approved_modifier, denial_reason.
- **appeals** — appeal_id (PK), case_id, denial_date, received_date, appeal_type_requested,
  appeal_path (`standard_internal`/`expedited_internal`/`external_review`/...),
  expedited_attestation, appeal_deadline, outcome, owner, notes (often lists the required packet).
- **drug_trials** — trial_id (PK), case_id, medication, outcome, documented (1/0),
  start_date, end_date, notes. *`documented=1` = documented failure; `0` = insufficient.*
- **assistance_screen** — case_id (PK), program_name, income_percent_fpl, insurance_type,
  denial_required, denial_on_file, missing_fields, assistance_status.
- **claims** — claim_id (PK), member_id, case_id, payer, received_date, claim_status,
  auth_number, billed_total, paid_total.
- **claim_lines** — claim_line_id (PK), claim_id, line_number, cpt_code, modifier, units,
  billed_amount, paid_amount, denial_code, service_date. *Order lines by `line_number`.*
- **payment_benchmarks** — benchmark_id (PK), payer, plan_type, service_domain, cpt_code,
  modifier, effective_start, effective_end, allowed_amount (**per unit**), source_name,
  source_version. *Select by payer+plan_type+service_domain+cpt+modifier and date window.*
- **p2p_events** — p2p_id (PK), case_id, scheduled_at, duration_minutes, provider_argument,
  new_information, outcome, final_status, reviewer, notes.
- **service_margin** — month_id (PK), period, payer, payer_segment, service_domain,
  cpt_code, visits, net_revenue, variable_cost, fixed_cost_allocated, charge_sensitive (1/0).

## Join map (typical)

```
cases.member_id      -> members.member_id -> members.plan_id -> plans.plan_id
cases.provider_id    -> providers.provider_id
cases.policy_id      -> policies.policy_id -> policy_criteria.policy_id
cases.case_id        -> request_lines / case_criteria / documents / document_facts
                        / authorizations / drug_trials / assistance_screen / p2p_events / appeals
claims.claim_id      -> claim_lines.claim_id ; claims.member_id -> members (plan_type)
claim line pricing   -> payment_benchmarks (match payer+plan_type+service_domain+cpt+modifier+date)
```
