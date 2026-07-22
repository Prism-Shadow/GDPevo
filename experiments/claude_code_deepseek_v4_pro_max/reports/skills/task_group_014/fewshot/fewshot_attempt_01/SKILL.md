# Northstar Health Plan Payer Operations Review

Perform structured business reviews for Northstar Health Plan payer operations — utilization management, appeals, payment integrity, peer-to-peer, and margin analysis — by querying the shared payer environment and returning a determination that conforms to the supplied answer template.

## Task Inputs

Every task provides three inputs in the working directory under `input/`:

| File | Purpose |
|---|---|
| `input/prompt.txt` | Natural-language task description identifying the target business object, requester role, reporting date, and what to produce. |
| `input/payloads/task_context.json` | Structured metadata: task_id, target business identifier, requester role, environment configuration block, and local memos with domain-specific guidance. |
| `input/payloads/answer_template.json` | Exact required JSON shape. Lists `required_top_level_keys`, field types, enum choices, ordering rules, numeric precision, and date format. |

The answer template is the contract. Every required key must appear in the output. Enum values must match the listed choices exactly. Ordering rules on lists must be followed. The `basis_audit` sub-object is required in every Northstar determination.

## Environment Access

The payer operations environment is accessed over HTTP. Its base URL is supplied via the task context (`environment.base_url`), typically resolved from the `<TASK_ENV_BASE_URL>` placeholder in `environment_access.md`.

### REST API Endpoints

Use these read-only business endpoints to retrieve structured records. All endpoints accept GET requests. No write operations are needed.

| Endpoint | Returns |
|---|---|
| `GET /portal` | Portal landing page with available resources and navigation context. |
| `GET /api/tables` | List of available database tables and their schemas. |
| `GET /api/cases` | Collection of authorization or appeal cases. |
| `GET /api/cases/{case_id}` | Single case record with member, plan, and request-line details. |
| `GET /api/policies` | Available coverage policies and medical necessity criteria. |
| `GET /api/policies/{policy_id}` | Single policy or criteria document. |
| `GET /api/documents/{document_id}` | Clinical, pharmacy, or administrative document by ID. |
| `GET /api/rate-schedules` | Available rate/benchmark schedules and their versions. |
| `GET /api/appeals` | Appeal records for coverage and payment appeals. |

### SQL Access

When the REST endpoints do not expose a needed record, or when cross-table joins are required, send a SQL query:

```
POST /sql/query
Authorization: Bearer pa-review-token-014
Content-Type: application/json

{"query": "<SQL statement>"}
```

The SQL service provides direct read access to the environment's operational database. Use it for filtered lookups, aggregations, and joins that the REST API does not directly support. Only SELECT statements are permitted.

### Query Strategy

1. Start with the relevant REST endpoint for the target business object (e.g., `GET /api/cases/{case_id}` for a case review).
2. Follow references in the returned record to related policies, documents, appeals, or rate schedules.
3. Use SQL only when the REST API cannot reach a needed record or when a join across tables is required.
4. Gather all evidence before evaluating criteria — do not decide on partial data.

## Evidence Gathering

For each task, collect every record the environment holds for the target business identifier. The required evidence varies by task domain:

- **UM review**: case record, member and plan context, requested therapy lines, applicable policy criteria, clinical documents (evaluations, plans of care, imaging reports), and any existing authorization record.
- **Appeals**: appeal record, original denial, case context, formulary/policy criteria, drug trial/failure history, pharmacy claims, assistance program screens.
- **Payment integrity**: claim header, claim lines, authorization record, current and legacy rate/benchmark schedules.
- **Peer-to-peer**: case record, request line, policy criteria, clinical evidence, the P2P event record, and the authorization status.
- **Margin analysis**: service margin rows for the specified queue IDs, payer-segment metadata, cost and revenue figures.

Classify every record as either **controlling** (directly drives the determination) or **exception** (explains a gap, exclusion, denial reason, missing information, or route priority). Evidence that is stale, superseded, or insufficiently documented must be noted as an exception.

## Criteria Evaluation

Each task domain uses a specific set of business criteria identified in the answer template. Evaluate every required criterion against the gathered evidence:

1. For each criterion key listed in the template's required_keys, determine whether the evidence satisfies it.
2. Use the template's value choices (typically `met`, `not_met`, `unclear`, `not_applicable`; some domains add `partial`).
3. A criterion is `met` only when the environment holds affirmative evidence for every element it requires.
4. Mark `unclear` when evidence exists but is inconclusive; mark `not_applicable` when the criterion does not apply to the current case type or service domain.
5. Criteria that remain unresolved after review must be listed in any `unresolved_criteria` field in the output.

## Source Precedence

Every determination must identify the business rule that governed which evidence took priority. The answer template enumerates the available precedence rules. Select the one that matches the task's evidence conflict pattern:

- **current_clinical_records_over_stale_export** — when a current clinical document supersedes an older exported version of the same record type.
- **payer_appeal_before_manufacturer_assistance** — when payer-side appeal evidence is evaluated before manufacturer assistance program data.
- **effective_benchmark_by_plan_modifier_and_date** — when the applicable rate benchmark is selected by matching plan, modifier, and effective date.
- **new_patient_specific_p2p_information** — when a peer-to-peer discussion introduces new patient-specific information that must be weighed against existing clinical records.
- **margin_threshold_then_charge_sensitivity** — when margin rows are first classified by a revenue-to-cost threshold, then by charge-sensitivity flags.
- **appeal_deadline_then_clinical_then_payment_integrity** — when evidence is prioritized by appeal deadline proximity, then clinical merit, then payment record integrity.

Select exactly one. It governs how the `precedence_record_order` list is constructed.

## Constructing the Basis Audit

The `basis_audit` object is required in every Northstar determination. It documents the decision trail so the determination can be audited.

| Field | How to populate |
|---|---|
| `source_precedence` | The single precedence rule that governed this determination. Select from the template's enumerated choices based on which evidence conflict pattern applies. |
| `controlling_record_ids` | Every environment record ID that directly supports the result. Include case IDs, document IDs, appeal IDs, benchmark record IDs, service-margin row IDs, policy IDs, and P2P event IDs that the determination relies on. Order by operational evidence priority (the records that carry the most weight come first). |
| `exception_record_ids` | Every record ID or gap identifier that explains an exclusion, denial, missing information, or route priority. Include stale records that were rejected, criteria that were not met, missing packet items, or assistance fields that are absent. Order by business gap priority: criteria or route gaps before stale or excluded records when both appear. |
| `precedence_record_order` | The union of controlling and exception records, ordered by the selected source-precedence rule from highest to lowest priority. Every entry in this list must appear in either `controlling_record_ids` or `exception_record_ids`. |

## Answer Construction

Assemble the output by following the answer template precisely:

1. **Top-level keys**: Include every key listed in `required_top_level_keys`. The template may allow additional properties or forbid them — check `additional_fields_allowed` or `additional_properties`.

2. **Enum values**: Use only values from the listed choices. Match casing and underscores exactly.

3. **List ordering**: Follow the ordering rule stated for each list field. Common rules:
   - Ascending by ID or code
   - Alphabetical by name
   - Operational packet order (payer items before other items)
   - Case-specific gap order (evidence gaps before information gaps)
   - Same order as an input reference list

4. **Numeric precision**: Currency values are in USD, rounded to two decimal places (cents). Ratios use four decimal places. Units are integers.

5. **Dates**: ISO 8601 calendar dates in `YYYY-MM-DD` format. Month-only periods use `YYYY-MM`.

6. **Null handling**: Use `null` for absent modifiers (never an empty string). Use `null` for dates that do not apply (e.g., no internal appeal deadline when the determination is an approval).

7. **Output format**: Return exactly one JSON object. No markdown fences, no surrounding prose, no comments. The response must be parseable as JSON directly.

## Task Execution Flow

Follow this sequence for any Northstar payer operations task:

1. **Read the inputs**: Parse `prompt.txt` for the task description, `task_context.json` for structured metadata, and `answer_template.json` for the output contract.
2. **Retrieve the target record**: Use the REST API or SQL to fetch the primary business object (case, claim, appeal, queue).
3. **Expand to related records**: Follow references to policies, documents, rate schedules, P2P events, drug trials, assistance screens, or service margin rows.
4. **Evaluate every criterion**: Work through each required criterion key, comparing the evidence against what each criterion demands.
5. **Classify evidence**: Mark each record as controlling or exception. Identify stale, superseded, or insufficient records.
6. **Select source precedence**: Choose the precedence rule that matches the evidence conflict in this task.
7. **Make the determination**: Decide the recommendation, status, route, letter type, and next action based on the criteria results and evidence classification.
8. **Populate the answer template**: Fill every required field following the ordering, precision, and format rules.
9. **Build the basis audit**: Assemble `controlling_record_ids`, `exception_record_ids`, and `precedence_record_order` consistent with the selected source precedence.
10. **Return the JSON**: Output only the completed JSON object.

## Domain Notes

Northstar Health Plan is a health insurance payer. Common service domains include physical therapy, speech therapy, occupational therapy, cardiac imaging, and pharmacy. The organization uses standard medical coding (CPT/HCPCS), operates under standard UM frameworks (prior authorization, concurrent review, appeals), and follows payer-industry conventions for claim repricing, peer-to-peer review, and service margin analysis.

The bearer token `pa-review-token-014` grants read-only access to the payer operations environment. All endpoints are idempotent GET operations; the SQL endpoint accepts only SELECT statements. Do not attempt writes — the task is to review and determine, not to modify records.
