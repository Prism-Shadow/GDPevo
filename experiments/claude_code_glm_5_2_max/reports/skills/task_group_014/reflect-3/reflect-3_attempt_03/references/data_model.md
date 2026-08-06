# Northstar Payer Operations — Data Model

Verify against `GET /api/tables` before relying on any name. Below is the known
schema and how records link across tables. The unifying join key is usually a
business ID (`case_id`, `claim_id`, `appeal_id`, or the margin `month_id`).

## Identity & coverage

- **members** (`member_id` PK) — patient_name, dob, `plan_id`, plan_type,
  product, employer_group, member_status. Join `plan_id` → plans.
- **plans** (`plan_id` PK) — payer_name, plan_type, state, network,
  effective_start/end, notes. Plan notes sometimes carry rules (e.g. expedited
  appeal attestation requirements).
- **providers** (`provider_id` PK) — provider_name, specialty, npi, contact.

## Cases & requests

- **cases** (`case_id` PK) — member_id, provider_id, request_type,
  service_domain, `policy_id`, request_date, due_date, current_stage,
  current_status, urgency, summary. The central record for UM/P2P/claim-review
  tasks; `policy_id` points at the controlling policy.
- **request_lines** (`line_id` PK, `case_id` FK) — cpt_code, modifier,
  service_name, `requested_units`, requested_start/end, diagnosis_codes,
  billed_charge. What the provider asked for.
- **authorizations** (`auth_id` PK, `case_id` FK) — auth_number, status,
  approved_units, approved_start/end, approved_cpt (comma-separated),
  approved_modifier, denial_reason. The determination/output record for UM and
  P2P tasks.

## Policy & criteria

- **policies** (`policy_id` PK) — policy_name, version, effective_start/end,
  `precedence` (int), summary.
- **policy_criteria** (`criterion_id` PK, `policy_id` FK) — criterion_key,
  criterion_text, `approval_required` (0/1), `result_if_missing`
  (e.g. `pend`, `deny`, `correct`, `uphold`). Defines the rules and what
  happens when evidence is missing.
- **case_criteria** (PK = `case_id` + `criterion_id`) — `result`
  (met/not_met/partial/unclear/...), `evidence_fact_ids`, `gap_description`,
  reviewer_scope. The per-criterion review result already recorded for the
  case. Mirror these results into the answer's `criteria_results` map.

## Evidence

- **documents** (`document_id` PK, `case_id` FK) — document_type,
  document_date, received_date, source_system, `is_current` (0/1), title,
  summary. **`is_current = 0` marks a stale export — exclude it from
  evidence.**
- **document_facts** (`fact_id` PK, `document_id` + `case_id` FK) — fact_key,
  fact_value, numeric_value, unit, `supports_criteria` (criterion_id or null).
  The atomic evidence; `supports_criteria` ties a fact to the criterion it
  proves. A fact whose `supports_criteria` is null (e.g. a `stale_episode`
  fact) is gap/exclusion evidence.

## Appeals & pharmacy

- **appeals** (`appeal_id` PK, `case_id` FK) — denial_date, received_date,
  appeal_type_requested, `appeal_path` (standard_internal/expedited_internal/
  external_review/not_eligible), `expedited_attestation`, `appeal_deadline`,
  outcome, owner, notes (notes often list the required packet items).
- **drug_trials** (`trial_id` PK, `case_id` FK) — medication, outcome,
  `documented` (0/1), start/end_date, notes. `documented = 1` → a documented
  formulary failure; `documented = 0` → undocumented/insufficient failure
  (e.g. "mentioned but pharmacy fill missing").
- **assistance_screen** (PK = `case_id`) — program_name, income_percent_fpl,
  insurance_type, denial_required, denial_on_file, `missing_fields`
  (comma-separated), `assistance_status`. Drives the `assistance` object.

## Claims & payment

- **claims** (`claim_id` PK) — member_id, `case_id`, payer, received_date,
  claim_status, `auth_number`, billed_total, `paid_total`. `claim_status` such
  as `paid_stale_schedule` signals a repricing correction is needed.
- **claim_lines** (`claim_line_id` PK, `claim_id` FK) — `line_number`,
  cpt_code, `modifier` (nullable), `units`, billed_amount, `paid_amount`,
  denial_code, `service_date`. Output `lines` in `line_number` order; use
  `null` for absent modifier.
- **payment_benchmarks** (`benchmark_id` PK) — payer, `plan_type`,
  `service_domain`, `cpt_code`, `modifier` (nullable), `effective_start`,
  `effective_end`, `allowed_amount`, `source_name`, `source_version`. Match by
  payer + plan_type + service_domain + cpt_code + modifier, then pick the row
  whose `[effective_start, effective_end]` covers the claim `service_date`.
  The current schedule wins; older sources (e.g. a "Legacy … Export" with an
  `effective_end` before the service date) are rejected.

## Peer-to-peer

- **p2p_events** (`p2p_id` PK, `case_id` FK) — scheduled_at, duration_minutes,
  provider_argument, `new_information`, `outcome` (not_applicable /
  overturn_to_approval / uphold_intended_adverse_decision), `final_status`,
  reviewer, notes. Drives the P2P summary.

## Finance / margin

- **service_margin** (`month_id` PK) — period, payer, `payer_segment`
  (medicaid/commercial/workers_comp/...), service_domain, cpt_code, visits,
  `net_revenue`, `variable_cost`, `fixed_cost_allocated`, `charge_sensitive`
  (0/1). For margin tasks:
  - `total_cost = variable_cost + fixed_cost_allocated`
  - `margin = net_revenue - total_cost`
  - `revenue_to_cost_ratio = net_revenue / total_cost`
  - `below_threshold = ratio < threshold` (threshold from task_context)
  - `charge_sensitive` flag is taken directly from the row.
  - Use **only** the queue row IDs named in `task_context` for the request.

## Getting the data out

- `GET /api/tables` — schema discovery (open).
- `GET /api/cases`, `/api/cases/{id}`, `/api/policies`, `/api/policies/{id}`,
  `/api/documents/{id}`, `/api/rate-schedules`, `/api/appeals` — open business
  reads.
- `POST /sql/query` — arbitrary SQL; body is `{"sql": "..."}`; requires the
  bearer token from the environment access file. Best for multi-table joins and
  filtering to the target business ID.
