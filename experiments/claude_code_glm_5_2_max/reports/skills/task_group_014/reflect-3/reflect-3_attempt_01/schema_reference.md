# Environment Schema Reference

The shared Northstar payer-operations environment exposes its schema at `GET /api/tables` and
is queryable via the SQL endpoint (see `SKILL.md` → The environment). These are the tables and
the fields most relevant to solving tasks. Always confirm current columns with `/api/tables` at
solve time in case of minor drift.

## SQL request / response shape

```
POST /sql/query
Authorization: Bearer <token from environment_access.md / task_context>
Content-Type: application/json

{"sql": "SELECT ... WHERE case_id = '...' ", "params": {}}
```

Response:
```json
{"columns": ["..."], "rows": [{...}], "row_count": N, "max_rows": 500, "limited": false}
```
The request field is `sql` (not `query`). `params` is optional; inline string literals also work.
Results cap at 500 rows — always filter on the target IDs.

## Core case / member tables

- **cases** — `case_id` (pk), `member_id`, `provider_id`, `request_type`, `service_domain`,
  `policy_id`, `request_date`, `due_date`, `current_stage`, `current_status`, `urgency`,
  `summary`. The hub record for PA, P2P, and appeal cases.
- **members** — `member_id` (pk), `patient_name`, `dob`, `plan_id`, `plan_type`, `product`,
  `employer_group`, `member_status`. `plan_type` drives benchmark selection and appeal rules.
- **plans** — `plan_id` (pk), `payer_name`, `plan_type`, `state`, `network`, `effective_start`,
  `effective_end`, `notes`.
- **providers** — `provider_id` (pk), `provider_name`, `specialty`, `npi`, `phone`, `fax`,
  `organization`.

## Policy / criteria tables

- **policies** — `policy_id` (pk), `policy_name`, `version`, `effective_start`, `effective_end`,
  `precedence`, `summary`.
- **policy_criteria** — `criterion_id` (pk), `policy_id`, `criterion_key`, `criterion_text`,
  `approval_required` (0/1), `result_if_missing` (`pend`/`deny`/`uphold`). Defines the criteria
  for a policy. `result_if_missing` tells you the consequence when a criterion is unmet/missing:
  `deny` → denial, `pend` → pended for information, `uphold` → uphold prior decision.
- **case_criteria** — `case_id`+`criterion_id` (pk), `result` (met/not_met/partial/unclear/
  not_applicable), `evidence_fact_ids`, `gap_description`, `reviewer_scope`. **The per-case
  criterion results** — usually maps directly into the answer's `criteria_results`. Read
  `gap_description` for missing-item and exception clues.

## Evidence tables

- **documents** — `document_id` (pk), `case_id`, `document_type`, `document_date`,
  `received_date`, `source_system`, `is_current` (0/1), `title`, `summary`. `is_current=0`
  marks stale/non-current documents (typically excluded from the determination and listed as
  exceptions).
- **document_facts** — `fact_id` (pk), `document_id`, `case_id`, `fact_key`, `fact_value`,
  `numeric_value`, `unit`, `supports_criteria` (criterion_id or null). The structured facts
  inside a document; a fact with `supports_criteria=null` and a "not documented"-style value is
  a gap/exception record.

## Decision / event tables (one per family)

- **authorizations** — `auth_id` (pk), `case_id`, `auth_number`, `status`, `approved_units`,
  `approved_start`, `approved_end`, `approved_cpt` (comma-separated string; emit as a sorted
  list), `approved_modifier`, `denial_reason`. Used for PA and as the claim's auth reference.
- **request_lines** — `line_id` (pk), `case_id`, `cpt_code`, `modifier`, `service_name`,
  `requested_units`, `requested_start`, `requested_end`, `diagnosis_codes`, `billed_charge`.
  The requested therapy/procedure lines for PA and P2P cases.
- **p2p_events** — `p2p_id` (pk), `case_id`, `scheduled_at`, `duration_minutes`,
  `provider_argument`, `new_information`, `outcome`, `final_status`, `reviewer`, `notes`.
  The P2P discussion record; `new_information` and `outcome` drive the P2P summary.
- **appeals** — `appeal_id` (pk), `case_id`, `denial_date`, `received_date`,
  `appeal_type_requested`, `appeal_path`, `expedited_attestation`, `appeal_deadline`,
  `outcome`, `owner`, `notes`. The appeal routing/deadline/owner.
- **assistance_screen** — `case_id` (pk), `program_name`, `income_percent_fpl`,
  `insurance_type`, `denial_required` (0/1), `denial_on_file` (0/1), `missing_fields`
  (comma-separated), `assistance_status`. The manufacturer-assistance intake record.
- **drug_trials** — `trial_id` (pk), `case_id`, `medication`, `outcome`, `documented` (0/1),
  `start_date`, `end_date`, `notes`. `documented=1` → documented failure; `documented=0` →
  undocumented/insufficient failure.

## Payment-integrity tables

- **claims** — `claim_id` (pk), `member_id`, `case_id`, `payer`, `received_date`,
  `claim_status`, `auth_number`, `billed_total`, `paid_total`.
- **claim_lines** — `claim_line_id` (pk), `claim_id`, `line_number`, `cpt_code`, `modifier`
  (nullable), `units`, `billed_amount`, `paid_amount`, `denial_code`, `service_date`. Order by
  `line_number` for the output `lines` list. `service_date` selects the effective benchmark.
- **payment_benchmarks** — `benchmark_id` (pk), `payer`, `plan_type`, `service_domain`,
  `cpt_code`, `modifier` (nullable), `effective_start`, `effective_end`, `allowed_amount`,
  `source_name`, `source_version`. The rate schedules. Select by matching payer + plan_type +
  service_domain + cpt_code + modifier (or null modifier) AND `service_date` within
  [effective_start, effective_end]. A benchmark whose `effective_end` < service_date is **stale**
  (rejected). Distractor schedules exist for other CPTs/domains — ignore rows whose cpt_code or
  service_domain does not match the claim line.

## Finance table

- **service_margin** — `month_id` (pk), `period`, `payer`, `payer_segment`, `service_domain`,
  `cpt_code`, `visits`, `net_revenue`, `variable_cost`, `fixed_cost_allocated`,
  `charge_sensitive` (0/1). For margin queues:
  - `total_cost` = `variable_cost` + `fixed_cost_allocated`
  - `margin` = `net_revenue` − `total_cost`
  - `revenue_to_cost_ratio` = `net_revenue` / `total_cost` (4 decimals)
  - `below_threshold` = ratio < threshold (from task_context finance_memo, e.g. 1.2)
  - `charge_sensitive` = the flag (0/1 → false/true)
