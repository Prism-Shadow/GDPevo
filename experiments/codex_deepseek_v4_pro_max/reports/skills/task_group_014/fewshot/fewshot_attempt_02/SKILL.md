---
name: northstar-payer-ops
description: Work with the Northstar Health Plan payer operations environment to review prior authorization cases, coverage appeals, payment-integrity claims, peer-to-peer summaries, and therapy margin queues. Use when the task involves a Northstar case, appeal, claim, or queue and needs structured JSON output from the shared payer-operations API and SQL endpoint.
---

# Northstar Health Plan — Payer Operations

## Environment connection

All Northstar payer-operations tasks share a single environment. The base URL is provided in the task prompt as `<TASK_ENV_BASE_URL>` or in the `environment_access` context. Do not hardcode a URL; read it from the task input.

### SQL endpoint

```
POST <BASE_URL>/sql/query
Content-Type: application/json
Authorization: Bearer pa-review-token-014
```

The JSON body must be `{"sql": "<SELECT | WITH | PRAGMA table_info only>", "params": []}`.

Examples:
- Discover schema: `PRAGMA table_info(<table>)`
- List table names: `SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name`
- Query specific records: `SELECT * FROM cases WHERE case_id = ?`, `params: ["<id>"]`

### REST endpoints

The environment exposes REST endpoints for business objects. Use `curl -sS` with the base URL. Available endpoints typically include `GET` for the following paths (see the task `environment_access` block for the full list):

- `/` — root / health
- `/portal` — portal overview
- `/api/tables` — list of available tables/views
- `/api/cases` — list cases
- `/api/cases/{case_id}` — single case
- `/api/policies` — list policies
- `/api/policies/{policy_id}` — single policy
- `/api/documents/{document_id}` — single document
- `/api/rate-schedules` — list rate schedules
- `/api/appeals` — list appeals

## Operational workflow

Every Northstar task follows this pattern:

1. **Read the task context** — Identify the target business ID (`case_id`, `claim_id`, `appeal_id`, or queue ID), the requester role, service domain, and reporting date.
2. **Read the answer template** — The required JSON shape is always provided in `input/payloads/answer_template.json`. Study every required field, its type, allowed enum values, ordering rules, and precision notes.
3. **Query the environment** — Use SQL and/or REST calls to retrieve the target case, associated policies, documents, claims, rate schedules, appeal records, or margin rows needed for the determination.
4. **Apply business rules** — Match facts from the environment against the criteria or business logic rules defined for the workflow type.
5. **Return JSON only** — Output exactly one JSON object conforming to the answer template. No markdown, no prose outside the JSON.

## Domain model

The environment contains these business objects:

| Object | Typical ID pattern | Key attributes |
|--------|-------------------|----------------|
| Cases | `CASE-...` | case_id, member, plan, service_domain, request lines, status |
| Policies | `POLICY-...` or `POL-...` | policy_id, criteria, service domain, effective dates |
| Documents | `DOC-...` | document_id, type, content/body, date, stale flag |
| Claims | `CLAIM-...` or `CL-...` | claim_id, auth_number, lines, paid amounts, modifiers |
| Rate schedules | `BM-...` or schedule names | benchmark rates by CPT, modifier, plan, effective dates |
| Appeals | `APL-...` | appeal_id, path, deadline, drug/formulary context |
| P2P events | `P2P-...` | event_id, outcome, new patient-specific information |
| Service margin | `SM-...` | month_id, payer_segment, cpt_code, cost, margin, revenue |

Use `PRAGMA table_info` or `SELECT * FROM sqlite_master` to discover the exact schema and column names before querying.

## Source precedence rules

Choose the `source_precedence` value that matches the workflow:

| Workflow | source_precedence | Meaning |
|----------|-------------------|---------|
| UM clinical determination | `current_clinical_records_over_stale_export` | Use live clinical documents; exclude stale or exported records |
| Pharmacy/coverage appeal | `payer_appeal_before_manufacturer_assistance` | Appeal facts come first; assistance eligibility follows |
| Payment integrity / claim repricing | `effective_benchmark_by_plan_modifier_and_date` | Use the current benchmark schedule covering the plan, modifier, and service date; reject stale schedules |
| Peer-to-peer review | `new_patient_specific_p2p_information` | P2P event and new clinical evidence override prior determinations |
| Therapy margin queue | `margin_threshold_then_charge_sensitivity` | Below-threshold segments drive priority; charge sensitivity is secondary |

## Basis audit (basis_audit)

Every answer must include a `basis_audit` object with these keys:

- **`source_precedence`** — The rule from the table above that applies to this workflow.
- **`controlling_record_ids`** — Environment record IDs (document IDs, line IDs, appeal IDs, etc.) that directly determine the result, in operational evidence order.
- **`exception_record_ids`** — Records that explain gaps, exclusions, denials, missing information, or route priority. Criteria or route gaps come before stale or excluded records when both appear.
- **`precedence_record_order`** — The controlling and exception records in source-precedence order, highest priority first.

## Query strategy by workflow

### UM nurse determination (prior authorization)
- Retrieve the case, member/plan context, and request lines.
- Retrieve active clinical documents (evaluation, plan of care) and check for stale records.
- Retrieve applicable policy criteria (e.g., PT-ACTIVE, PT-DEFICIT, PT-DX, PT-POC, PT-UNITS).
- Evaluate each criterion against the clinical evidence.
- Classify documents as evidence or excluded.
- Determine the recommendation, route, determination letter, and authorization details.

### Pharmacy appeals coordinator
- Retrieve the appeal record and the associated case.
- Retrieve drug trial / formulary failure records.
- Classify medication failures as documented vs. undocumented/insufficient.
- Evaluate policy criteria (e.g., DRUG-AUTH, DRUG-DENIAL, DRUG-RATIONALE, DRUG-FAILURES).
- Determine the appeal path, expedited status, and deadline.
- Assess required and missing packet items (appeal evidence before assistance items).
- Check manufacturer assistance program eligibility and missing fields.

### Payment integrity claim repricing
- Retrieve the claim and its line items in claim-line order.
- Retrieve the authorization number from the claim or payment record.
- Retrieve rate schedules and identify the current benchmark vs. stale sources.
- For each line: look up the benchmark rate by CPT, modifier, plan, and date.
- Compute `correct_allowed = benchmark_rate * units`.
- Compute `recovery = correct_allowed - paid` (positive when underpaid).
- Determine the resubmission route and priority.
- Use `null` for absent line modifiers, not empty string.

### Peer-to-peer summary
- Retrieve the case, request line (CPT), and the completed P2P event.
- Retrieve clinical evidence and policy criteria (e.g., PET-IND, PET-FACTOR).
- List unresolved criteria and unsupported PET-over-SPECT factors.
- Determine whether new patient-specific information changed the review.
- Set the letter type and recommended alternative modality.
- If the final determination is adverse, compute the internal appeal deadline by adding the plan's internal appeal window in days to the determination date.

### Therapy margin queue
- Query the `service_margin` rows given by the task context's `queue_row_ids`.
- `total_cost = variable_cost + fixed_cost_allocated`.
- `margin = revenue - total_cost`.
- `revenue_to_cost_ratio = revenue / total_cost`.
- Compare `revenue_to_cost_ratio` against the threshold (default 1.2).
- For rows below threshold, recommend `payer_contract_review`.
- For rows at/above threshold but flagged as charge-sensitive, recommend `monitor_charge_sensitive`.
- Identify the top below-threshold issue and compute `gap_to_120pct = (threshold * total_cost) - revenue`.

## Precision and formatting rules

- **Currency**: JSON numbers in USD, rounded to 2 decimal places.
- **Ratios**: 4 decimal places.
- **Dates**: ISO 8601 `YYYY-MM-DD`.
- **Periods**: `YYYY-MM`.
- **Null modifiers**: Use JSON `null`, never empty string.
- **Sorting**: Follow the ordering rules specified in the answer template (ascending, claim-line order, operational packet order, etc.).
- **Lists**: Use `[]` (empty array) when no items apply, unless the template specifies otherwise.
- **Booleans**: Use JSON `true`/`false`, never strings.

## Anti-patterns

- Do not inspect database files, environment source files, generated data files, SQLite files, manifests, or setup scripts directly — use only the SQL and REST endpoints.
- Do not include markdown, prose, or comments outside the JSON output.
- Do not copy task-specific values (case IDs, amounts, dates) from training examples — always derive them from the live environment.
- Do not use stale or superseded rate schedules when a current benchmark is available.
- Do not merge payer appeal packet items with manufacturer assistance items in a single gap list — keep appeal gaps before assistance gaps.
