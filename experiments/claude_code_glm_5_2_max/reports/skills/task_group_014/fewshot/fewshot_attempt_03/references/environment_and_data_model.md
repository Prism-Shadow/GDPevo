# Environment Access & Data Model

The shared Northstar payer-operations environment is **read-only** and reached
**only over the network**. Do not inspect local source/data/SQLite/manifest/setup
files. All access details come from `environment_access.md`.

## Base URL

From `environment_access.md` (e.g. `http://task-env:9014/`). All paths below are
relative to it.

## Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/portal` | none | Landing page; lists business entry points. |
| GET | `/api/tables` | none | Full schema: every table with columns, types, PK, NOT NULL. Call this first to confirm the data model. |
| GET | `/api/cases` | none | List cases. |
| GET | `/api/cases/{case_id}` | none | One case. |
| GET | `/api/policies` | none | List policies. |
| GET | `/api/policies/{policy_id}` | none | One policy. |
| GET | `/api/documents/{document_id}` | none | One document. |
| GET | `/api/rate-schedules` | none | List payment benchmarks / rate schedules. |
| GET | `/api/appeals` | none | List appeals. |
| POST | `/sql/query` | `Authorization: Bearer pa-review-token-014` | Arbitrary SQL (see below). |

## SQL wire format

- Request: JSON body `{"sql": "<SQL string>"}`. The field is **`sql`**, not
  `query`. Header `Authorization: Bearer pa-review-token-014` is required
  (missing/invalid → HTTP 401).
- Dialect: **SQLite**. Table and column names are as returned by
  `/api/tables`. Use single quotes for string literals.
- Response: `{"columns":[...], "rows":[{...}, ...], "row_count":N,
  "max_rows":500, "limited":bool}`. Rows are objects keyed by column name.
- **Row cap:** at most 500 rows per query. If `"limited": true`, results were
  truncated — narrow the query (add `WHERE`/`LIMIT`/tighter predicates) and
  re-run until `limited` is false. Never assume a `limited:true` result is
  complete.

Use SQL for joins and filtered retrieval; use the `GET /api/...` endpoints for
single-record lookups by ID.

## Data model (tables)

Schema is confirmed at runtime via `GET /api/tables`. The tables below are the
expected set; verify column names against the live response before querying.

- **cases** — `case_id` (PK), `member_id`, `provider_id`, `request_type`,
  `service_domain`, `policy_id`, `request_date`, `due_date`, `current_stage`,
  `current_status`, `urgency`, `summary`.
- **members** — `member_id` (PK), `patient_name`, `dob`, `plan_id`, `plan_type`,
  `product`, `employer_group`, `member_status`.
- **plans** — `plan_id` (PK), `payer_name`, `plan_type`, `state`, `network`,
  `effective_start`, `effective_end`, `notes`.
- **providers** — `provider_id` (PK), `provider_name`, `specialty`, `npi`,
  `phone`, `fax`, `organization`.
- **request_lines** — `line_id` (PK), `case_id`, `cpt_code`, `modifier`,
  `service_name`, `requested_units`, `requested_start`, `requested_end`,
  `diagnosis_codes`, `billed_charge`.
- **policies** — `policy_id` (PK), `policy_name`, `version`, `effective_start`,
  `effective_end`, `precedence`, `summary`.
- **policy_criteria** — `criterion_id` (PK), `policy_id`, `criterion_key`,
  `criterion_text`, `approval_required`, `result_if_missing`.
- **case_criteria** — (`case_id`, `criterion_id`) PK, `result`,
  `evidence_fact_ids`, `gap_description`, `reviewer_scope`.
- **documents** — `document_id` (PK), `case_id`, `document_type`,
  `document_date`, `received_date`, `source_system`, `is_current`, `title`,
  `summary`. **`is_current`** distinguishes current clinical records from stale
  exports.
- **document_facts** — `fact_id` (PK), `document_id`, `case_id`, `fact_key`,
  `fact_value`, `numeric_value`, `unit`, `supports_criteria`.
- **authorizations** — `auth_id` (PK), `case_id`, `auth_number`, `status`,
  `approved_units`, `approved_start`, `approved_end`, `approved_cpt`,
  `approved_modifier`, `denial_reason`.
- **appeals** — `appeal_id` (PK), `case_id`, `denial_date`, `received_date`,
  `appeal_type_requested`, `appeal_path`, `expedited_attestation`,
  `appeal_deadline`, `outcome`, `owner`, `notes`.
- **drug_trials** — `trial_id` (PK), `case_id`, `medication`, `outcome`,
  `documented`, `start_date`, `end_date`, `notes`. **`documented`** (0/1)
  separates documented prior failures from undocumented/insufficient ones.
- **assistance_screen** — `case_id` (PK), `program_name`, `income_percent_fpl`,
  `insurance_type`, `denial_required`, `denial_on_file`, `missing_fields`,
  `assistance_status`.
- **p2p_events** — `p2p_id` (PK), `case_id`, `scheduled_at`, `duration_minutes`,
  `provider_argument`, `new_information`, `outcome`, `final_status`,
  `reviewer`, `notes`.
- **claims** — `claim_id` (PK), `member_id`, `case_id`, `payer`,
  `received_date`, `claim_status`, `auth_number`, `billed_total`, `paid_total`.
- **claim_lines** — `claim_line_id` (PK), `claim_id`, `line_number`, `cpt_code`,
  `modifier`, `units`, `billed_amount`, `paid_amount`, `denial_code`,
  `service_date`.
- **payment_benchmarks** — `benchmark_id` (PK), `payer`, `plan_type`,
  `service_domain`, `cpt_code`, `modifier`, `effective_start`, `effective_end`,
  `allowed_amount`, `source_name`, `source_version`.
- **service_margin** — `month_id` (PK), `period`, `payer`, `payer_segment`,
  `service_domain`, `cpt_code`, `visits`, `net_revenue`, `variable_cost`,
  `fixed_cost_allocated`, `charge_sensitive`.

## Effective-record selection (recurring pattern)

Several tables carry date ranges or version/currency flags. When multiple
candidate records exist, pick the **effective** one and treat the rest as stale
exceptions:

- `payment_benchmarks`: effective for the claim's `plan_type`/`modifier`/`cpt_code`
  where `service_date` is within `[effective_start, effective_end]`; prefer the
  newest `source_version`. Older `source_name`/`source_version` rows are the
  stale source to reject.
- `documents`: prefer `is_current = 1`; `is_current = 0` (e.g. a legacy export)
  is the stale record to exclude.
- `policies` / `policy_criteria`: use the version effective on the
  request/service date; `precedence` breaks ties.
- `plans`: effective on the date of service.
