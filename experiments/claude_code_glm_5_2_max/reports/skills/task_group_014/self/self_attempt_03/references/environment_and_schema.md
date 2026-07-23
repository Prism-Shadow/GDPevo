# Environment Access & Schema Reference

Reference for the shared Northstar payer-operations environment. Use this to plan queries and to know which table backs each archetype.

## Connection

- **Base URL:** `http://task-env:9014/` (from `environment_access.md`; also appears as `<TASK_ENV_BASE_URL>` in task payloads — they are the same target).
- **SQL endpoint:** `POST /sql/query` to the base URL, with header `Authorization: Bearer pa-review-token-014`. The request body is a SQL query string over the tables below. SQL is the flexible path for multi-table joins; use it when no single GET endpoint returns the joined shape you need.
- **Business GET endpoints:** open, no auth.

## Allowed endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/portal` | none | HTML landing page; lists business entry points |
| GET | `/api/tables` | none | Relational schema catalog (tables, columns, primary keys, types) |
| GET | `/api/cases` | none | List cases |
| GET | `/api/cases/{case_id}` | none | One case record |
| GET | `/api/policies` | none | List policies |
| GET | `/api/policies/{policy_id}` | none | One policy record |
| GET | `/api/documents/{document_id}` | none | One document record |
| GET | `/api/rate-schedules` | none | Benchmark / rate schedule rows (backs `payment_benchmarks`) |
| GET | `/api/appeals` | none | List appeals |
| POST | `/sql/query` | `Bearer pa-review-token-014` | Arbitrary SQL over the relational tables |

If you need a list of documents by case, appeal by case, or joined criteria + evidence, use `POST /sql/query` — the GET endpoints above cover single-record and list-by-collection lookups, not arbitrary filters.

## Prohibited actions

- Do **not** inspect environment source files, generated data files, SQLite files, manifests, or setup scripts directly. All access is through the HTTP endpoints above.
- Do **not** call any judge endpoint. No judge endpoint is exposed; do not invent one.
- Do **not** mutate data — the environment is read-only. Only `POST /sql/query` is allowed for writes-of-intent, and it is read-only `SELECT` semantics in practice.

## Table catalog (19 tables)

Primary key columns are marked `(pk)`.

**`cases`** `(pk: case_id)` — `member_id`, `provider_id`, `request_type`, `service_domain`, `policy_id`, `request_date`, `due_date`, `current_stage`, `current_status`, `urgency`, `summary`. The hub record for UM/P2P/appeal work items.

**`members`** `(pk: member_id)` — `patient_name`, `dob`, `plan_id`, `plan_type`, `product`, `employer_group`, `member_status`.

**`plans`** `(pk: plan_id)` — `payer_name`, `plan_type`, `state`, `network`, `effective_start`, `effective_end`, `notes`. `plan_type`/`network`/modifier drive benchmark selection.

**`providers`** `(pk: provider_id)` — `provider_name`, `specialty`, `npi`, `phone`, `fax`, `organization`.

**`request_lines`** `(pk: line_id)` — `case_id`, `cpt_code`, `modifier`, `service_name`, `requested_units`, `requested_start`, `requested_end`, `diagnosis_codes`, `billed_charge`. Requested therapy/procedure lines for UM and P2P tasks.

**`policies`** `(pk: policy_id)` — `policy_name`, `version`, `effective_start`, `effective_end`, `precedence`, `summary`. `precedence` ranks overlapping policies.

**`policy_criteria`** `(pk: criterion_id)` — `policy_id`, `criterion_key`, `criterion_text`, `approval_required`, `result_if_missing`. Defines each criterion (e.g., `PT-ACTIVE`, `DRUG-FAILURES`, `PET-IND`) and what happens when evidence is missing.

**`case_criteria`** `(pk: case_id, criterion_id)` — `result`, `evidence_fact_ids`, `gap_description`, `reviewer_scope`. The evaluated result per criterion for a case, with the evidence facts that support it and any gap. This is the source of `criteria_results` maps.

**`documents`** `(pk: document_id)` — `case_id`, `document_type`, `document_date`, `received_date`, `source_system`, `is_current`, `title`, `summary`. `is_current` distinguishes current clinical records from stale exports — central to the `current_clinical_records_over_stale_export` rule and to `evidence_documents` vs `excluded_documents`.

**`document_facts`** `(pk: fact_id)` — `document_id`, `case_id`, `fact_key`, `fact_value`, `numeric_value`, `unit`, `supports_criteria`. Structured facts extracted from documents; `supports_criteria` links a fact to a criterion. Source of evidence/exception records.

**`authorizations`** `(pk: auth_id)` — `case_id`, `auth_number`, `status`, `approved_units`, `approved_start`, `approved_end`, `approved_cpt`, `approved_modifier`, `denial_reason`. Existing authorization record for UM and P2P tasks; basis for the `authorization` object and `auth_number`.

**`appeals`** `(pk: appeal_id)` — `case_id`, `denial_date`, `received_date`, `appeal_type_requested`, `appeal_path`, `expedited_attestation`, `appeal_deadline`, `outcome`, `owner`, `notes`. Appeal routing, deadline, expediting, and ownership for the pharmacy appeal archetype.

**`assistance_screen`** `(pk: case_id)` — `program_name`, `income_percent_fpl`, `insurance_type`, `denial_required`, `denial_on_file`, `missing_fields`, `assistance_status`. Manufacturer assistance intake state; `denial_required`/`denial_on_file` drive the "payer appeal before assistance" logic; `missing_fields` feeds `assistance.missing_fields`.

**`drug_trials`** `(pk: trial_id)` — `case_id`, `medication`, `outcome`, `documented`, `start_date`, `end_date`, `notes`. Prior medication trials; `documented` splits `documented_failures` from `undocumented_or_insufficient_failures`.

**`p2p_events`** `(pk: p2p_id)` — `case_id`, `scheduled_at`, `duration_minutes`, `provider_argument`, `new_information`, `outcome`, `final_status`, `reviewer`, `notes`. The completed P2P discussion; `new_information` drives `new_information_changed_review` and the overturn/uphold decision.

**`claims`** `(pk: claim_id)` — `member_id`, `case_id`, `payer`, `received_date`, `claim_status`, `auth_number`, `billed_total`, `paid_total`. Claim header for payment-integrity repricing; `paid_total` is the baseline for recovery.

**`claim_lines`** `(pk: claim_line_id)` — `claim_id`, `line_number`, `cpt_code`, `modifier`, `units`, `billed_amount`, `paid_amount`, `denial_code`, `service_date`. Line detail for repricing; `line_number` sets output order; `service_date` selects the effective benchmark; `modifier` may be null.

**`payment_benchmarks`** `(pk: benchmark_id)` — `payer`, `plan_type`, `service_domain`, `cpt_code`, `modifier`, `effective_start`, `effective_end`, `allowed_amount`, `source_name`, `source_version`. Rate schedules. `source_name` ∈ {`Northstar Commercial Imaging Schedule`, `Legacy Imaging Export`, `Northstar Distractor Schedule`}; the effective window + modifier select the controlling row; stale/legacy/distractor sources are rejected. Also surfaced via `GET /api/rate-schedules`.

**`service_margin`** `(pk: month_id)` — `period`, `payer`, `payer_segment`, `service_domain`, `cpt_code`, `visits`, `net_revenue`, `variable_cost`, `fixed_cost_allocated`, `charge_sensitive`. Finance margin queue rows. `total_cost = variable_cost + fixed_cost_allocated`; `revenue_to_cost_ratio = net_revenue / total_cost`; `charge_sensitive` is a stored flag. `month_id` is the stable row id used in `queue_row_ids`.

## Table → archetype map

| Archetype | Primary tables |
|---|---|
| UM nurse determination (PT) | `cases`, `members`, `plans`, `request_lines`, `policies`, `policy_criteria`, `case_criteria`, `documents`, `document_facts`, `authorizations` |
| Pharmacy appeal + assistance | `appeals`, `assistance_screen`, `drug_trials`, `cases`, `policies`, `policy_criteria`, `case_criteria`, `documents`, `document_facts` |
| Payment-integrity repricing | `claims`, `claim_lines`, `payment_benchmarks`, `cases`, `policies` |
| P2P final summary (PET MPI) | `p2p_events`, `cases`, `request_lines`, `policies`, `policy_criteria`, `case_criteria`, `documents`, `document_facts`, `authorizations` |
| Finance margin queue | `service_margin` (rows by `month_id` from the task memo's `queue_row_ids`) |
