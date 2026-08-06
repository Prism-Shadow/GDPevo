# Northstar Payer Operations — Environment reference

The shared, **read-only** environment backs every task in this family. Access details
are never hard-coded: read them fresh each task from `environment_access.md` and the
task's `input/payloads/task_context.json`.

## Access

- **Base URL** — value of `GDPEVO_ENV_BASE_URL` in `environment_access.md`
  (also echoed as `environment.base_url` in `task_context.json`, sometimes as the
  placeholder `<TASK_ENV_BASE_URL>`; substitute the real URL from the env file).
- **Auth** — every request needs `Authorization: Bearer <sql_bearer_token>` where the
  token is given in `environment_access.md` and `task_context.json`
  (e.g. `pa-review-token-014`). Use the values you are given; do not assume them.
- Use **only** the endpoints listed in `environment_access.md`. Do **not** read the
  environment's source files, generated data, SQLite files, manifests, or setup scripts
  directly — several prompts forbid it explicitly. Go through the HTTP endpoints only.

## SQL endpoint (primary tool)

`POST /sql/query` with JSON body `{"sql": "<SELECT ...>"}` (key is `sql`; a missing/empty
value returns `{"error":"invalid_sql"}`). Response:

```json
{"columns": [...], "rows": [ {col:val, ...}, ... ], "row_count": N,
 "limited": false, "max_rows": 500}
```

Read-only `SELECT`s. Results are capped at **500 rows** (`limited:true` if truncated) —
always constrain with a `WHERE` on the target business id so you never rely on the cap.
Prefer **single quotes** for string literals inside the SQL (no JSON escaping needed).
`SELECT name FROM sqlite_master WHERE type='table'` lists tables; combine with
`GET /api/tables` for full column metadata.

Example (curl):
```
curl -s -X POST "$BASE/sql/query" -H "Authorization: Bearer $TOK" \
  -H "Content-Type: application/json" \
  -d '{"sql":"SELECT * FROM cases WHERE case_id='"'"'CASE-XXX'"'"'"}'
```

## Business REST endpoints (convenience)

- `GET /api/tables` — schema (tables + columns + types + PK/not-null).
- `GET /api/cases` and `GET /api/cases/{case_id}` — the single-case endpoint returns a
  **joined bundle**: the case plus its `criteria`, `authorizations`, `appeals`, `claims`,
  `assistance_screen`, etc. Handy to pull an entire case in one call.
- `GET /api/policies`, `GET /api/policies/{policy_id}`.
- `GET /api/documents/{document_id}`.
- `GET /api/rate-schedules` — all `payment_benchmarks` rows (`count` + `rate_schedules`).
- `GET /api/appeals` — all appeals.

REST and SQL read the same data; use whichever is convenient. SQL is best for filtering,
joins, and aggregation.

## Data model (19 tables)

`*` = primary key.

| Table | Key columns (selected) |
|---|---|
| `members` | member_id*, patient_name, dob, plan_id, plan_type, product, employer_group, member_status |
| `plans` | plan_id*, payer_name, plan_type, state, network, effective_start, effective_end |
| `providers` | provider_id*, provider_name, specialty, npi |
| `cases` | case_id*, member_id, provider_id, **request_type**, service_domain, policy_id, request_date, due_date, current_stage, current_status, urgency, summary |
| `request_lines` | line_id*, case_id, cpt_code, modifier, service_name, requested_units, requested_start, requested_end, diagnosis_codes, billed_charge |
| `documents` | document_id*, case_id, document_type, document_date, received_date, source_system, **is_current** (1/0), title, summary |
| `document_facts` | fact_id*, document_id, case_id, fact_key, fact_value, numeric_value, unit, supports_criteria |
| `policies` | policy_id*, policy_name, version, effective_start, effective_end, **precedence** (int), summary |
| `policy_criteria` | criterion_id*, policy_id, criterion_key, criterion_text, approval_required (1/0), **result_if_missing** (correct/deny/pend/uphold) |
| `case_criteria` | (case_id, criterion_id)*, **result**, evidence_fact_ids, gap_description, reviewer_scope |
| `p2p_events` | p2p_id*, case_id, scheduled_at, duration_minutes, provider_argument, new_information, **outcome**, **final_status**, reviewer, notes |
| `appeals` | appeal_id*, case_id, denial_date, received_date, appeal_type_requested, **appeal_path**, expedited_attestation, **appeal_deadline**, outcome, owner, notes |
| `drug_trials` | trial_id*, case_id, medication, outcome, **documented** (1/0), start_date, end_date, notes |
| `assistance_screen` | case_id*, program_name, income_percent_fpl, insurance_type, denial_required, denial_on_file, **missing_fields**, assistance_status |
| `claims` | claim_id*, member_id, case_id, payer, received_date, claim_status, auth_number, billed_total, paid_total |
| `claim_lines` | claim_line_id*, claim_id, line_number, cpt_code, modifier, units, billed_amount, paid_amount, denial_code, service_date |
| `authorizations` | auth_id*, case_id, auth_number, **status**, approved_units, approved_start, approved_end, approved_cpt, approved_modifier, denial_reason |
| `payment_benchmarks` | benchmark_id*, payer, plan_type, service_domain, cpt_code, modifier, **effective_start**, **effective_end**, allowed_amount, **source_name**, source_version |
| `service_margin` | month_id*, period, payer, payer_segment, service_domain, cpt_code, visits, net_revenue, variable_cost, fixed_cost_allocated, **charge_sensitive** (1/0) |

## Controlled vocabularies observed (use the answer template's enum, not these, when they differ)

- `authorizations.status`: approved, denied, pended, recommended_approval
- `case_criteria.result`: met, not_met, partial, unclear, not_applicable, stale_schedule_used
- `policy_criteria.result_if_missing`: correct, deny, pend, uphold
- `appeals.appeal_path`: standard_internal, expedited_internal, external_review (also `not_eligible` in templates)
- `appeals.owner`: appeals-rx, appeals-um  → map to template owners (appeals-rx, um-nurse, …)
- `appeals.expedited_attestation`: not_requested, missing, provider_attested_serious_health_risk
- `assistance_screen.assistance_status`: e.g. pending_missing_income_proof → template `eligible_missing_information`
- `p2p_events.outcome`: overturn_to_approval, reschedule, uphold_intended_adverse_decision
- `p2p_events.final_status`: approved, denied, pending
- `documents.is_current`: 1 (current) / 0 (stale — exclude)
- `payment_benchmarks.source_name`: Northstar Commercial Imaging Schedule, Northstar WC Surgery Schedule, Legacy Imaging Export (**stale**), Northstar Distractor Schedule (**decoy**)

## Distractor discipline

The environment holds **many** cases, benchmarks, documents, and margin rows beyond the
one you were asked about (dozens of cases across every `request_type` × `service_domain`).
Treat everything as noisy:

- Filter strictly by the **target business id(s)** from `task_context.json`
  (`target_business_id`, `target_appeal_id`, `target.claim_id`, `finance_memo.queue_row_ids`, …).
- Ignore benchmark rows whose `source_name` is a *Distractor Schedule*, whose cpt/modifier
  don't match the claim line, or that are duplicates/`BM-TE-*` test rows.
- Ignore records outside the target case, period, or listed queue rows.
