---
name: northstar-payer-ops
description: Execute Northstar Health Plan payer operations tasks using a shared HTTP environment. Use this skill for prior authorization reviews, pharmacy appeals intake, claim repricing, peer-to-peer summaries, and therapy margin queues. The skill covers environment access via SQL and REST endpoints, task-context-driven workflows, answer-template-conformant JSON output, and source-precedence audit trails.
---

# Northstar Payer Operations

## Environment

All business data lives in the Northstar payer-operations environment at the base URL provided as `<TASK_ENV_BASE_URL>`. Never use local filesystem data as the primary source.

### SQL access

- **Endpoint**: `POST <TASK_ENV_BASE_URL>/sql/query`
- **Header**: `Authorization: Bearer pa-review-token-014`
- **Content-Type**: `application/json`
- **Body**: `{"sql": "<SELECT | WITH | PRAGMA table_info query>", "params": []}`
- **Restriction**: Only SELECT, WITH, and PRAGMA table_info statements are allowed. No INSERT, UPDATE, DELETE, or DDL.
- Always start exploration with `PRAGMA table_info(<table>)` or `SELECT name FROM sqlite_master WHERE type='table'` to discover schema before writing targeted SELECT queries.
- Use parameterised queries via the `params` array when filtering by known IDs.

### Business REST endpoints

The following GET endpoints are available and should be used in preference to SQL when the data matches the endpoint's purpose:

- `GET <TASK_ENV_BASE_URL>/` — root
- `GET <TASK_ENV_BASE_URL>/portal` — portal
- `GET <TASK_ENV_BASE_URL>/api/tables` — available tables listing
- `GET <TASK_ENV_BASE_URL>/api/cases` — list cases
- `GET <TASK_ENV_BASE_URL>/api/cases/{case_id}` — single case
- `GET <TASK_ENV_BASE_URL>/api/policies` — list policies
- `GET <TASK_ENV_BASE_URL>/api/policies/{policy_id}` — single policy
- `GET <TASK_ENV_BASE_URL>/api/documents/{document_id}` — single document
- `GET <TASK_ENV_BASE_URL>/api/rate-schedules` — list rate schedules
- `GET <TASK_ENV_BASE_URL>/api/appeals` — list appeals

### Operational URL resolution

- `<TASK_ENV_BASE_URL>` is a placeholder resolved at execution time. Always read `environment_access.md` for the actual base URL before issuing requests. It is *not* a literal URL.

## Task input structure

Each task provides three input files in `input/`:

- `prompt.txt` — Human-readable business instruction. Identifies the case/appeal/claim/queue, the requester role, the work domain, any special handling rules, and the output contract (usually "return JSON only matching answer_template.json").
- `payloads/task_context.json` — Machine-readable metadata: `task_id`, `target_business_id` (or `target.claim_id` / `target_appeal_id` / `business_id`), `requester_role`, `reporting_date` (or `reporting_period` / `request_date`), `environment` config object, and a `local_memo` (or `finance_memo` / `work_item`) with additional operational instructions specific to the domain.
- `payloads/answer_template.json` — The mandatory output schema. Defines `required_top_level_fields` (or `required_top_level_keys`), field-by-field types, enums, ordering rules, and any `basis_audit` structure.

### Key fields in task_context.json

- **Target identifiers** vary by task type. Look for `target_business_id`, `target.claim_id`, `target_appeal_id`, `business_id`, or `target.case_id`. Always use the environment to resolve the full record.
- **environment** block provides `base_url` (the placeholder), `sql_endpoint`, and `sql_bearer_token`.
- **local_memo** / **finance_memo** / **work_item** may contain additional constraints: service domain, queue row IDs, total-cost definitions, revenue-to-cost thresholds, business due dates, clinical file needs, or known CPT codes. Treat these as operational parameters that narrow the scope of the task.

## Output requirements

### JSON only

Every response must be a single JSON object. No markdown, prose, comments, or explanatory text outside the JSON.

### Conform to answer_template.json

- Every field listed in `required_top_level_fields` must be present.
- Enums must use exactly the values defined in the template.
- Lists must follow the ordering rule specified in the template (e.g. ascending document_id, alphabetical by medication name, claim-line order).
- Numeric fields must use the precision defined in the template (typically two decimal places for USD, integer for units, 4 decimal places for ratios).
- Use `null` for absent modifiers or inapplicable fields — never use empty strings.
- The `additional_fields_allowed` key (when present and `false`) means no extra top-level keys are permitted.

### Dates

All dates must be ISO 8601 calendar dates in `YYYY-MM-DD` format.

## Basis audit trail

Every output must include a `basis_audit` object with four required keys:

- **source_precedence** — A string enum that names the operational rule used to weigh evidence sources.
- **precedence_record_order** — A list of environment record IDs, ordered from highest to lowest priority, combining both controlling and exception records.
- **controlling_record_ids** — A list of environment record IDs that directly control the result. Ordered by operational evidence order.
- **exception_record_ids** — A list of environment record IDs that explain exclusions, denials, missing information, or route priority. Ordered with criteria/route gaps before stale/excluded records.

### source_precedence rules

Choose the rule that matches the task's business domain:

| source_precedence | Domain |
|---|---|
| `current_clinical_records_over_stale_export` | Prior authorization / UM nurse review (clinical records override stale exports) |
| `payer_appeal_before_manufacturer_assistance` | Pharmacy appeals intake (payer-side appeal evidence before manufacturer assistance) |
| `effective_benchmark_by_plan_modifier_and_date` | Payment integrity / claim repricing (benchmark selected by plan, modifier, and effective date) |
| `new_patient_specific_p2p_information` | Peer-to-peer review (new clinical information from the P2P discussion) |
| `margin_threshold_then_charge_sensitivity` | UM-finance / margin queue (classify by revenue-to-cost threshold first, then charge sensitivity) |
| `appeal_deadline_then_clinical_then_payment_integrity` | Mixed appeal/deadline-driven workflows |

## Operational workflow

### 1. Orient to the task

Read all three input files. Identify the business domain, target IDs, requester role, reporting date, and output contract.

### 2. Discover the data model

Query `PRAGMA table_info` for any table relevant to the domain (cases, claims, policies, documents, appeals, rate_schedules, service_margin, etc.), then write targeted SELECT queries to retrieve the records linked to the target business IDs.

### 3. Cross-reference records

Business records are interlinked by IDs. Follow the chain: cases reference policies, claims reference rate schedules and authorizations, appeals reference cases and documents, documents reference cases. Use SQL JOINs or successive queries to follow these links. Always prefer the current environment record over any locally cached or stale export.

### 4. Apply domain rules

Each domain has specific evaluation logic:

- **Prior authorization (UM nurse)**: Check requested CPT codes against policy criteria. Evaluate clinical documents for medical necessity. Classify evidence documents as relied-on or excluded. Determine the recommendation (approve/pend/escalate/deny/partial), final status, route, and letter type.
- **Pharmacy appeals**: Route the appeal path (standard/expedited/external/not_eligible). Classify documented vs undocumented medication failures. Check criteria for DRUG-AUTH, DRUG-DENIAL, DRUG-RATIONALE, DRUG-FAILURES. Build required and missing packet item lists. Screen for manufacturer assistance program eligibility.
- **Claim repricing (payment integrity)**: Identify the effective rate schedule by plan, modifier, and date. Reject any stale or inapplicable schedule. Price each claim line using the benchmark's unit rate × units. Calculate paid_total, correct_allowed_total, and recovery_amount per line and in aggregate.
- **Peer-to-peer (P2P)**: Retrieve the P2P event, authorization case, policy criteria, and clinical evidence. Determine whether the P2P supplied new patient-specific information. Evaluate PET-specific criteria (PET-IND, PET-FACTOR). Identify unresolved criteria and missing PET factors. Set p2p_outcome, final_status, and letter_type. If the final determination is adverse, calculate the internal appeal deadline as 180 calendar days from the final adverse determination date.
- **Therapy margin queue (UM-finance)**: For each queue row ID, retrieve cost, revenue, and margin data. Compute total_cost as variable_cost + fixed_cost_allocated. Compute revenue_to_cost_ratio. Flag as below_threshold when ratio < the threshold (default 1.2). Flag as charge_sensitive per the environment record. Assign recommended_action: `payer_contract_review` for below-threshold rows, `monitor_charge_sensitive` for charge-sensitive rows where threshold is met, otherwise `monitor_no_action`.

### 5. Compose the audit trail

Identify:
- The **controlling records**: the environment record IDs that directly determine the result (the policy used, the rate schedule applied, the criteria evaluated, the clinical document relied upon).
- The **exception records**: records that explain gaps (missing documents, stale schedules, failed criteria, documents excluded from review).
- Order them into `precedence_record_order` following the domain's source_precedence rule.

### 6. Validate and output

Verify every required key is present, every enum value matches the template, every list follows the template's ordering rule, and no extra keys are present unless `additional_properties` is true. Output the JSON object only.

## Cross-cutting conventions

- **Record IDs are stable strings**: Use them as-is from the environment. Do not synthesise or guess IDs.
- **NULL vs empty**: Use `null` for absent values; never use empty strings `""` or empty arrays `[]` unless the template explicitly permits them (e.g. "Use an empty list only if no applicable criteria remain unresolved").
- **Currency**: All monetary values are in USD, rounded to two decimal places (cents). Use JSON number type, not strings.
- **Service domains**: Recognised values include `physical_therapy`, `speech_therapy`, `occupational_therapy`, `cardiac_imaging`. Match the value from the environment or memo exactly.
- **Payer segments**: `medicaid`, `commercial`, `workers_comp` — use exactly these lowercase strings.
- **Never fabricate data**: Every value in the output must be traceable to an environment record or a calculation derived from environment records. If information is genuinely unavailable, use the appropriate enum sentinel (e.g. `unclear`, `not_applicable`, `none`).
