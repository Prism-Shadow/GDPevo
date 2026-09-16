---
name: northstar-payer-ops
description: Solve Northstar Health Plan payer-operations tasks by querying the shared environment and producing structured JSON determinations for UM review, appeals, payment integrity, P2P, and finance queues.
---

Use this skill when the task involves a Northstar Health Plan payer-operations
work item: prior authorization nurse review, pharmacy coverage appeals,
payment-integrity claim repricing, peer-to-peer authorization closure, or
therapy-margin queue analysis. The target environment is a shared read-only
payer-operations service that exposes REST business endpoints and an SQL query
interface.

## Environment

The task prompt supplies a base URL (e.g. `<TASK_ENV_BASE_URL>`). Substitute
that value for `{BASE}` below when constructing requests.

**Authentication.** Every SQL request uses the bearer token provided in the
task prompt (typically `pa-review-token-014`):

```text
Authorization: Bearer {TOKEN}
```

**Available endpoints.**

| Method | Path | Purpose |
|--------|------|---------|
| GET | `{BASE}/` | Portal landing page |
| GET | `{BASE}/health` | Service health and DB presence |
| GET | `{BASE}/api/tables` | Full schema listing (table names, columns, keys, nullability) |
| GET | `{BASE}/api/cases` | All case records |
| GET | `{BASE}/api/cases/{case_id}` | Single case |
| GET | `{BASE}/api/policies` | All policy records |
| GET | `{BASE}/api/policies/{policy_id}` | Single policy |
| GET | `{BASE}/api/documents/{document_id}` | Single document |
| GET | `{BASE}/api/rate-schedules` | All rate schedule / benchmark records |
| GET | `{BASE}/api/appeals` | All appeal records |
| POST | `{BASE}/sql/query` | Arbitrary read-only SQL (JSON body with `"sql"` key) |

The SQL interface returns JSON shaped as `{"columns": [...], "rows": [...],
"row_count": N, "limited": bool}`. Use it for cross-table joins and targeted
queries; fall back to REST endpoints when you need a single record or simple
listing.

**Do not** inspect environment source files, generated data files, SQLite
files, manifests, or setup scripts. Use only the REST endpoints and the SQL
endpoint listed above.

## Database schema

The tables available in the environment are:

- `cases` — case header: `case_id`, `member_id`, `provider_id`, `request_type`,
  `service_domain`, `policy_id`, `request_date`, `due_date`, `current_stage`,
  `current_status`, `urgency`, `summary`
- `members` — member demographics: `member_id`, `patient_name`, `dob`,
  `plan_id`, `plan_type`, `product`, `employer_group`, `member_status`
- `providers` — provider details: `provider_id`, `provider_name`,
  `specialty`, `npi`, `phone`, `fax`, `organization`
- `plans` — plan info: `plan_id`, `payer_name`, `plan_type`, `state`,
  `network`, `effective_start`, `effective_end`, `notes`
- `documents` — clinical/admin documents: `document_id`, `case_id`,
  `document_type`, `document_date`, `received_date`, `source_system`,
  `is_current` (1 = current, 0 = stale), `title`, `summary`
- `document_facts` — structured facts from documents: `fact_id`,
  `document_id`, `case_id`, `fact_key`, `fact_value`, `numeric_value`,
  `unit`, `supports_criteria` (criterion ID or null)
- `request_lines` — requested service lines: `line_id`, `case_id`,
  `cpt_code`, `modifier`, `service_name`, `requested_units`,
  `requested_start`, `requested_end`, `diagnosis_codes`, `billed_charge`
- `authorizations` — auth records: `auth_id`, `case_id`, `auth_number`,
  `status`, `approved_units`, `approved_start`, `approved_end`,
  `approved_cpt` (comma-separated list), `approved_modifier`,
  `denial_reason`
- `policies` — policy definitions: `policy_id`, `policy_name`, `version`,
  `effective_start`, `effective_end`, `precedence`, `summary`
- `policy_criteria` — individual criteria: `criterion_id`, `policy_id`,
  `criterion_key`, `criterion_text`, `approval_required` (1/0),
  `result_if_missing` (deny/pend/uphold/correct)
- `case_criteria` — criteria evaluated per case: `case_id`, `criterion_id`,
  `result`, `evidence_fact_ids`, `gap_description`, `reviewer_scope`
- `appeals` — appeal records: `appeal_id`, `case_id`, `denial_date`,
  `received_date`, `appeal_type_requested`, `appeal_path`,
  `expedited_attestation`, `appeal_deadline`, `outcome`, `owner`, `notes`
- `drug_trials` — formulary failure trials: `trial_id`, `case_id`,
  `medication`, `outcome`, `documented` (1/0), `start_date`, `end_date`,
  `notes`
- `assistance_screen` — manufacturer assistance: `case_id`, `program_name`,
  `income_percent_fpl`, `insurance_type`, `denial_required`,
  `denial_on_file`, `missing_fields` (comma-separated), `assistance_status`
- `claims` — claim headers: `claim_id`, `member_id`, `case_id`, `payer`,
  `received_date`, `claim_status`, `auth_number`, `billed_total`,
  `paid_total`
- `claim_lines` — claim line items: `claim_line_id`, `claim_id`,
  `line_number`, `cpt_code`, `modifier`, `units`, `billed_amount`,
  `paid_amount`, `denial_code`, `service_date`
- `payment_benchmarks` — rate schedules: `benchmark_id`, `payer`,
  `plan_type`, `service_domain`, `cpt_code`, `modifier`,
  `effective_start`, `effective_end`, `allowed_amount`, `source_name`,
  `source_version`
- `p2p_events` — peer-to-peer discussions: `p2p_id`, `case_id`,
  `scheduled_at`, `duration_minutes`, `provider_argument`,
  `new_information`, `outcome`, `final_status`, `reviewer`, `notes`
- `service_margin` — monthly margin: `month_id`, `period`, `payer`,
  `payer_segment`, `service_domain`, `cpt_code`, `visits`,
  `net_revenue`, `variable_cost`, `fixed_cost_allocated`,
  `charge_sensitive`

Use `GET /api/tables` to refresh the schema in case of environment updates.

## General workflow

Follow this sequence for every payer-operations task:

1. **Read the input.** Open `input/prompt.txt` for the task description and
   `input/payloads/task_context.json` for the target business ID, role,
   reporting date, and any domain-specific memo. Open
   `input/payloads/answer_template.json` to get the required output shape,
   allowed enum values, field definitions, and ordering rules.

2. **Gather environment records.** Use the SQL endpoint or REST endpoints to
   retrieve every record linked to the target business ID. At minimum pull:
   - The case record from `cases`
   - The member record from `members`
   - All documents from `documents` (pay attention to `is_current`)
   - All document facts from `document_facts` (note `supports_criteria`)
   - All request lines from `request_lines`
   - All case criteria from `case_criteria`
   - The authorization record from `authorizations`
   - The policy criteria from `policy_criteria` joined through the case's
     `policy_id`
   - Any domain-specific tables: `drug_trials` + `assistance_screen` for drug
     appeals, `claims` + `claim_lines` + `payment_benchmarks` for payment
     integrity, `p2p_events` for P2P, `service_margin` for finance queues,
     `appeals` for appeals

3. **Evaluate against criteria.** Compare the `case_criteria` results and
   `document_facts` against the policy criteria. Identify which criteria are
   met, not met, unclear, or not applicable. Note gaps and exceptions:
   - Stale documents (`is_current = 0`) that should be excluded
   - Undocumented or insufficient evidence
   - Missing packet items
   - Charge-sensitive rows in margin queues

4. **Determine source precedence.** Select the `source_precedence` rule that
   matches the task domain:

   | Precedence | When to use |
   |---|---|
   | `current_clinical_records_over_stale_export` | UM nurse review, PT prior auth — current clinical documents take priority over stale history |
   | `payer_appeal_before_manufacturer_assistance` | Pharmacy appeals — resolve the payer appeal path before manufacturer assistance |
   | `effective_benchmark_by_plan_modifier_and_date` | Payment integrity / claim repricing — select the benchmark effective on the service date for the correct plan type and modifier |
   | `new_patient_specific_p2p_information` | Peer-to-peer authorization — P2P discussion and its new information takes precedence |
   | `margin_threshold_then_charge_sensitivity` | Finance / margin queue — flag below-threshold rows first, then charge-sensitive rows |
   | `appeal_deadline_then_clinical_then_payment_integrity` | Combined appeal + payment integrity tasks |

5. **Build the answer.** Start from the answer template shape and populate
   every required field. Follow all ordering rules, enum choices, numeric
   precision, and date formatting constraints in the template. Keep the JSON
   strict — no comments, no prose outside the JSON object.

6. **Verify the basis audit.** Every answer includes a `basis_audit` object:

   - `source_precedence` — the rule from step 4
   - `controlling_record_ids` — environment record IDs that directly control
     the result, listed in operational evidence order
   - `exception_record_ids` — records explaining exclusions, denials, gaps,
     or missing information; list criteria/route gaps before stale/excluded
     records when both appear
   - `precedence_record_order` — controlling records followed by exception
     records, highest priority first under the source-precedence rule

## Domain-specific guidance

### UM nurse prior-authorization review

- Check member coverage (`PT-ACTIVE`): `member_status` in `members` must be
  `active` and the plan must be effective on the requested dates.
- Check diagnosis (`PT-DX`): document facts must support the lumbar/spine
  diagnosis.
- Check functional deficit (`PT-DEFICIT`): facts must include objective
  scores or baseline measurements.
- Check plan of care (`PT-POC`): POC document must be current (`is_current
  = 1`) with frequency, duration, and skilled goals.
- Check unit limit (`PT-UNITS`): sum of requested units across all request
  lines must not exceed the policy limit.
- Exclude stale documents: any `documents` row with `is_current = 0` goes
  into `excluded_documents`.
- Authorization values come from `authorizations` and `request_lines`.
  Approved CPT codes are collected from request lines, sorted ascending by
  code. The modifier is the common modifier across lines (e.g. `GP` for PT).

### Pharmacy appeals

- Identify documented vs. undocumented failures from `drug_trials`:
  `documented = 1` rows are documented failures; `documented = 0` rows are
  undocumented or insufficient.
- List medications in lowercase, alphabetically.
- Check criteria: `DRUG-AUTH` (member authorization), `DRUG-DENIAL` (denial
  notice), `DRUG-RATIONALE` (prescriber rationale), `DRUG-FAILURES` (formulary
  failures). `DRUG-FAILURES` is `partial` when at least one is documented but
  one or more required failures are missing or undocumented.
- `required_packet_items` include payer appeal items (denial notice, member
  authorization, prescriber rationale, formulary failure evidence) plus any
  assistance items (household income proof when manufacturer program is
  involved). Order: payer appeal items before assistance items.
- `missing_packet_items` are those documented as absent in the environment
  records. Order: appeal evidence gaps before assistance information gaps.
- For `assistance`, read `assistance_screen`. The `missing_fields` list is
  sorted alphabetically by field ID. Status is `eligible_ready` when all
  fields are present, `eligible_missing_information` when fields are missing,
  `not_eligible` when the program criteria are not met, `not_applicable` when
  no program applies.
- Appeal deadline is the `appeal_deadline` from the `appeals` table.
- Appeal path and expedited status come from the appeal record.
- Owner is the `owner` from the appeal record.

### Payment integrity claim repricing

- Identify the stale source: look at `payment_benchmarks` for the same CPT
  but with an `effective_end` before the service date (stale schedule).
- Identify the current benchmark: the benchmark whose `effective_start` ≤
  service date ≤ `effective_end` for matching CPT, modifier, plan type, and
  payer. If multiple current benchmarks exist, use the one whose
  `source_name` is the current commercial schedule (not a legacy export).
- Compute corrected amounts: `correct_allowed_amount = allowed_amount ×
  units` for each line, rounded to two decimal places.
- Compute recovery: `recovery_amount = correct_allowed_amount − paid_amount`
  for each line. Use positive values for underpayments (correct upward).
- `recovery_amount` at the claim level is `correct_allowed_total −
  paid_total`.
- Line disposition: `correct_upward` when recovery > 0, `correct_downward`
  when recovery < 0, `no_change` when recovery = 0.
- Sort lines by `line_number` from `claim_lines`.
- `modifier` is `null` (JSON null, not string "null") when the claim line
  has no modifier.
- `benchmark_source` is the `source_name` of the current benchmark;
  `benchmark_version` is its `source_version`.
- `stale_source_rejected` is the `source_name` of the stale benchmark, or
  `"none"` if no stale source was present.
- `controlling_record_ids` include the claim line IDs and the current
  benchmark IDs. `exception_record_ids` include stale benchmark IDs.

### Peer-to-peer authorization closure

- The `p2p_outcome` comes from `p2p_events.outcome`.
- `final_status` comes from `p2p_events.final_status` (or is derived from
  the authorization status).
- `new_information_changed_review` is `true` when the P2P event supplied
  new patient-specific information that materially changed the original
  criterion result; otherwise `false`.
- `unresolved_criteria` list criterion IDs in ascending order. Only include
  criteria that remain unresolved after the P2P.
- For the `missing_pet_factors` list, compare the P2P `new_information`
  against the known PET-over-SPECT factors listed in the template and
  include every listed factor that remains unsupported.
- `recommended_alternative` is the modality recommended when the requested
  service is denied (e.g. `SPECT MPI` when PET is denied).
- `internal_appeal_deadline` calculates 180 calendar days from the final
  adverse determination date (use the P2P scheduled date or the reporting
  date when the determination is finalized). Use `null` only when no appeal
  deadline applies (i.e. the result was not adverse).
- `letter_type` matches the final status: `approval` for approved,
  `denial` for denied, `partial_denial` for partially approved,
  `no_letter` when no letter is needed.

### Therapy margin queue analysis

- `total_cost = variable_cost + fixed_cost_allocated` for each row.
- `margin = net_revenue − total_cost`.
- `revenue_to_cost_ratio = net_revenue / total_cost`, rounded to 4 decimal
  places.
- `below_threshold` is `true` when `revenue_to_cost_ratio <
  threshold_revenue_to_cost_ratio`.
- `charge_sensitive` maps directly from the `charge_sensitive` column (1 =
  true, 0 = false).
- `recommended_action`: `payer_contract_review` for rows below threshold;
  `monitor_charge_sensitive` for rows not below threshold but charge
  sensitive; `monitor_no_action` for rows with neither flag.
- `below_threshold_segments` lists payer segments (alphabetical) that have
  at least one row below threshold.
- `charge_sensitive_segments` lists payer segments (alphabetical) that have
  at least one charge-sensitive row not below threshold.
- `top_issue` is the segment + CPT combo for the row with the largest gap
  between actual revenue and 120% of cost (i.e. the most severe
  below-threshold issue). Format: `{segment}_{cpt_code}`. Use `"none"` when
  no row is below threshold.
- `gap_to_120pct = (threshold_revenue_to_cost_ratio × total_cost) −
  net_revenue` for the top issue, rounded to 2 decimal places. This is the
  dollar gap to reach the 1.2 ratio.
- `controlling_record_ids` are all the `month_id` values for the rows.
  `exception_record_ids` are the `month_id` values for below-threshold rows.
- Rows in the output list follow the order given in `task_context`'s
  `queue_row_ids`.

## Answer construction rules

- Return exactly one JSON object. No markdown fences, no surrounding prose.
- Follow every field definition in the answer template exactly: required
  keys, enum choices, ordering rules, and numeric precision.
- Use `null` for absent modifiers and for dates that are explicitly
  inapplicable — not the string `"null"`.
- Currency values are JSON numbers rounded to two decimal places.
- Dates are ISO 8601 calendar dates (`YYYY-MM-DD`).
- Lists of document IDs, criterion IDs, and record IDs are sorted as
  specified by the answer template (ascending, alphabetical, or operational
  order).
- The `basis_audit` is mandatory in every answer. Choose the correct
  `source_precedence` for the task domain, populate `controlling_record_ids`
  with the records that directly determine the result, and
  `exception_record_ids` with the records that explain gaps or exclusions.
  Order `precedence_record_order` highest priority first under the chosen
  precedence rule.
