---
name: northstar-payer-ops
description: Process Northstar Health Plan payer operations tasks (UM prior auth, pharmacy appeals, payment integrity, peer-to-peer, margin queues). Use when the task involves Northstar payer operations environment at <TASK_ENV_BASE_URL>, requires SQL and REST API access, and expects structured JSON output matching a provided answer template.
---

# Northstar Payer Operations Skill

## When to use this skill

Use this skill when the input includes:
- A `prompt.txt` describing a Northstar Health Plan business task for a specific role (UM nurse, pharmacy appeals coordinator, payment integrity analyst, P2P coordinator, UM-finance analyst).
- A `task_context.json` with structured task metadata including a target business identifier and environment configuration.
- An `answer_template.json` defining the required output JSON schema.
- An `environment_access.md` or equivalent providing the base URL, SQL endpoint, and REST API endpoints.

## Operating environment

### Base connectivity

All environment access uses the base URL provided as `<TASK_ENV_BASE_URL>` in prompts and task context. Substitute this placeholder with the actual environment URL when present. Never inspect local construction files, database files, manifests, or setup scripts directly.

### SQL access

Use `POST /sql/query` at the environment base URL:
- Content-Type: `application/json`
- Authorization: `Bearer pa-review-token-014`
- Request body: `{"sql": "<query>", "params": []}`
- Allowed SQL: `SELECT`, `WITH`, and `PRAGMA table_info` only.

### REST business endpoints

The environment exposes GET endpoints. Consult `environment_access.md` for the complete list. Typical endpoints include:

- `GET /` — environment root
- `GET /portal` — plan portal
- `GET /api/tables` — schema overview
- `GET /api/cases` — all cases
- `GET /api/cases/{case_id}` — case detail
- `GET /api/policies` — all policies
- `GET /api/policies/{policy_id}` — policy detail
- `GET /api/documents/{document_id}` — clinical/administrative documents
- `GET /api/rate-schedules` — rate schedules
- `GET /api/appeals` — appeals

## Input file conventions

Every task follows the same directory layout:

```
train_tasks/train_NNN/input/
  prompt.txt              — Natural-language task request
  payloads/
    task_context.json     — Structured task metadata and instructions
    answer_template.json  — Output JSON schema
```

### prompt.txt

Contains the business request in prose. Key elements to extract:
- Payer/plan name (always Northstar Health Plan)
- Requester role and team
- Target business identifier (case ID, claim ID, appeal ID, queue ID)
- Reporting date or period
- Specific review requirements (policies, documents, criteria, schedules)

### task_context.json

Always read this file first to determine:
- `task_id` — the train task identifier
- Target business ID (field name varies: `target_business_id`, `target_appeal_id`, `target.claim_id`, `business_id`)
- `requester_role` — perspective for the analysis
- Dates: `reporting_date`, `reporting_period`, `request_date`
- `environment` block with base URL, SQL endpoint, and bearer token
- `local_memo` — internal operating instructions, domain hints, and scope constraints

The `local_memo` often contains domain-specific operating parameters such as:
- `known_service_domain` (e.g., `physical_therapy`, `cardiac_imaging`)
- `work_type` or `work_item` describing the task category
- Finance parameters like `total_cost_definition`, `revenue_to_cost_threshold`, `queue_row_ids`

### answer_template.json

Defines the strict output contract. Always:
- Read every field definition, enum choice, ordering rule, and precision constraint.
- Return only one JSON object — no markdown, prose, or commentary.
- Match every `required_top_level_fields` / `required_top_level_keys` entry exactly.
- Observe numeric precision rules (currency to 2 decimal places, ratios to 4 decimal places).
- Observe date format rules (ISO 8601 `YYYY-MM-DD`).
- Observe ordering rules for lists (alphabetical, ascending, claim-line order, operational evidence order, gap order).

## Universal basis audit pattern

Every output requires a `basis_audit` object with four required keys:

```
{
  "source_precedence": "<one of six rules>",
  "controlling_record_ids": ["<records that directly control the result>"],
  "exception_record_ids": ["<gap/exception records>"],
  "precedence_record_order": ["<controlling + exception records in priority order>"]
}
```

### source_precedence options

Select the single rule that governs the task:

| Rule | When to use |
|------|-------------|
| `current_clinical_records_over_stale_export` | UM prior auth determinations where current clinical documents take precedence over stale data exports |
| `payer_appeal_before_manufacturer_assistance` | Pharmacy appeal intake where payer appeal packet items are resolved before manufacturer assistance gaps |
| `effective_benchmark_by_plan_modifier_and_date` | Payment integrity repricing where the effective rate schedule (by plan, modifier, and effective date) controls |
| `new_patient_specific_p2p_information` | Peer-to-peer reviews where new patient-specific information from the P2P discussion changes the review |
| `margin_threshold_then_charge_sensitivity` | Finance margin queues where revenue-to-cost threshold analysis precedes charge-sensitivity flagging |
| `appeal_deadline_then_clinical_then_payment_integrity` | Complex cases where appeal deadlines govern, followed by clinical review, then payment integrity |

### Record ID ordering rules

- **controlling_record_ids**: List environment record IDs that directly control the result in operational evidence order.
- **exception_record_ids**: List gap/exception records in business gap order — criteria or route gaps before stale or excluded records when both appear.
- **precedence_record_order**: Combine all controlling and exception record IDs into a single list, highest source priority first. This mirrors the chosen `source_precedence` rule's logical order.

## Data normalization rules

Apply these rules to every output:

- **Currency**: JSON numbers in dollars, rounded to two decimal places (cents). Do not use strings for monetary values.
- **Ratios**: JSON numbers with up to four decimal places.
- **Dates**: ISO 8601 calendar dates in `YYYY-MM-DD` format. Periods use `YYYY-MM`.
- **Null modifiers**: Use JSON `null` for absent modifiers — never an empty string.
- **List ordering**: Follow the ordering directive specified in each template field. Common directives: alphabetical, ascending ID, claim-line order from source, same order as task_context list, operational evidence order, gap order (criteria/route gaps before stale/excluded).
- **Enum selection**: Use exactly the enum values defined in the template. No synonyms or approximations.

## Task-type operating frameworks

### Prior authorization (UM nurse review)

**Task indicators**: `requester_role` is "UM nurse reviewer", template includes `authorization` object and `criteria_results` with medical policy keys, `evidence_documents` and `excluded_documents` lists.

**Operating steps**:
1. Query the target case via REST (`/api/cases/{case_id}`) and SQL.
2. Retrieve active member and plan context from the environment.
3. Review all requested therapy/service lines against applicable policy criteria.
4. Classify each criterion as `met`, `not_met`, `unclear`, or `not_applicable`.
5. Collect current clinical/administrative documents that support the determination.
6. Identify and exclude any stale or irrelevant documents with documented rationale.
7. Build the authorization object with approved units, dates, CPT codes, and modifiers.
8. Map the overall recommendation (`approve`, `pend_for_information`, `escalate_to_md`, `deny`, `partial_approval`) to the correct route, final_status, determination_letter, and next_action.

### Pharmacy appeal and assistance intake

**Task indicators**: `requester_role` is "pharmacy appeals coordinator", template includes `appeal_id`, `drug`, `appeal_path`, `documented_failures`, `assistance` object.

**Operating steps**:
1. Query the appeal and associated case via REST and SQL.
2. Determine the appeal path: `standard_internal`, `expedited_internal`, `external_review`, or `not_eligible`.
3. Calculate the appeal deadline based on appeal type and determination dates.
4. Classify prior medication failures as documented or undocumented/insufficient.
5. Evaluate drug-specific criteria results (authorization, denial rationale, failure evidence).
6. Assemble the required appeal packet checklist and identify missing items.
7. Evaluate manufacturer assistance eligibility, status, and missing fields.
8. Determine next action combining appeal and assistance outcomes.

### Payment integrity claim repricing

**Task indicators**: `requester_role` is "payment integrity analyst", template includes `benchmark_source`, `stale_source_rejected`, `lines` with per-line correction fields, monetary recovery amounts.

**Operating steps**:
1. Query the target claim via REST and SQL to retrieve claim header and lines.
2. Identify the authorization number recorded on the claim.
3. Review available rate schedules to determine the correct benchmark source and version.
4. Identify and reject any stale or inapplicable schedule sources.
5. For each claim line: compare paid amounts against the corrected allowed amounts using the benchmark.
6. Calculate per-line recovery amounts (downward corrections) or underpayment amounts (upward corrections).
7. Sum paid total, correct allowed total, and recovery amount across all lines.
8. Assign the resubmission route and priority.
9. Maintain claim-line order in the lines array.

### Peer-to-peer coordination

**Task indicators**: `requester_role` is "peer-to-peer coordinator", template includes `p2p_id`, `p2p_outcome`, `new_information_changed_review`, `missing_pet_factors`, `internal_appeal_deadline`.

**Operating steps**:
1. Query the authorization case, policy criteria, clinical evidence, and P2P event records.
2. Determine the P2P outcome: whether the discussion overturned or upheld the intended decision.
3. Map the outcome to the final_status.
4. Evaluate each applicable criterion and classify results.
5. Identify unresolved criteria (those remaining unclear or unmet after P2P).
6. Determine if new patient-specific information from the P2P materially changed the review.
7. For cardiac imaging / PET-specific tasks, assess PET-over-SPECT factors (prior equivocal SPECT, BMI limitation, attenuation artifact).
8. Assign the letter type and recommended alternative modality.
9. If the final determination is adverse, calculate the internal appeal deadline using the plan's appeal window (typically 180 days from the adverse determination date); otherwise use null.

### Finance margin queue analysis

**Task indicators**: `requester_role` is "UM-finance operations analyst", template includes `period`, `threshold_revenue_to_cost_ratio`, `rows` with per-row margin data, `below_threshold_segments`, `charge_sensitive_segments`.

**Operating steps**:
1. Query the target queue rows using the IDs provided in `task_context.finance_memo.queue_row_ids`.
2. Calculate total cost using the definition from `finance_memo.total_cost_definition` (e.g., `variable_cost` + `fixed_cost_allocated`).
3. Calculate margin as `revenue - total_cost`.
4. Calculate `revenue_to_cost_ratio` as `revenue / total_cost`.
5. Determine `below_threshold` by comparing the ratio against `finance_memo.revenue_to_cost_threshold`.
6. Determine `charge_sensitive` from the source data flag.
7. Assign `recommended_action` per row based on both flags: `payer_contract_review` for below-threshold, `monitor_charge_sensitive` for charge-sensitive above-threshold, `monitor_no_action` otherwise.
8. Aggregate `below_threshold_segments` and `charge_sensitive_segments` across all rows (alphabetical order).
9. Identify the `top_issue` (the below-threshold row with the largest absolute gap) and compute `gap_to_120pct` as `(1.2 * total_cost) - revenue`.

## Query methodology

1. **Start broad**: Use `PRAGMA table_info` or `GET /api/tables` to discover schema.
2. **Target specific records**: Use REST endpoints for single-record retrieval when the exact ID is known.
3. **Cross-reference**: Use SQL `SELECT` with `JOIN` to connect cases to policies, documents, authorizations, and related entities.
4. **Iterate methodically**: Query each needed entity, verify results, and move to the next. Do not batch unrelated queries.
5. **Verify completeness**: Ensure every record referenced in the output is traceable back to environment data.

## Output discipline

- Return exactly one JSON object. No wrapping text, no markdown fences, no commentary.
- Include every required top-level field. Missing fields invalidate the output.
- Preserve the template's exact key names — case-sensitive.
- Use the template's enum values verbatim — no guesswork or near-matches.
- Currency and precision fields must match the template's stated precision.
- Lists must follow the template's ordering directive exactly.
- The `additional_fields_allowed` flag (when present) determines whether extra keys are permitted.
