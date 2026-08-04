 # Northstar Health Plan Payer Operations

## When to Use

Use this skill whenever the task involves Northstar Health Plan payer operations — prior authorization determinations, coverage appeals, payment integrity claim repricing, peer-to-peer summaries, or therapy margin queue analysis. The skill covers how to access the shared Northstar payer-operations environment, gather evidence through SQL and REST endpoints, apply the correct business-precedence rule, and return a structured JSON response that matches the supplied answer template.

## Environment Access

The Northstar payer-operations environment is available at the base URL supplied in the task prompt or context as `<TASK_ENV_BASE_URL>`. All data access must go through the environment endpoints; do not inspect environment source files, SQLite files, manifests, generated data files, or setup scripts directly.

### Authentication

Every SQL request requires the bearer token `pa-review-token-014`. Send it as:

```
Authorization: Bearer pa-review-token-014
```

REST GET endpoints may not require authentication, but include the header when the task context indicates shared-environment access.

### REST Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Environment root / health |
| GET | `/portal` | Payer portal summary |
| GET | `/api/tables` | List available database tables |
| GET | `/api/cases` | List cases |
| GET | `/api/cases/{case_id}` | Single case detail |
| GET | `/api/policies` | List policies |
| GET | `/api/policies/{policy_id}` | Single policy detail |
| GET | `/api/documents/{document_id}` | Clinical or business document |
| GET | `/api/rate-schedules` | Rate schedules for repricing |
| GET | `/api/appeals` | Appeal records |

### SQL Endpoint

```
POST /sql/query
Content-Type: application/json
Authorization: Bearer pa-review-token-014
```

The SQL endpoint accepts only `SELECT`, `WITH`, and `PRAGMA table_info` statements. Use `PRAGMA table_info(<table>)` first to discover column names before querying data.

**Request body:**

```json
{"sql": "<SELECT/WITH/PRAGMA table_info only>", "params": []}
```

**Example — discover columns:**

```json
{"sql": "PRAGMA table_info(cases)", "params": []}
```

**Example — query with parameterized filter:**

```json
{"sql": "SELECT * FROM cases WHERE case_id = ?", "params": ["CASE-123"]}
```

Always use parameterized queries with the `params` array rather than string interpolation.

## Input Structure

Each task provides three input artifacts:

1. **`prompt.txt`** — Natural-language description of the business task, the requestor's role, the target business identifier, and output expectations.
2. **`task_context.json`** — Structured metadata: `task_id`, target business ID(s), requester role, reporting date, environment configuration, and local memos with business rules or formulas.
3. **`answer_template.json`** — The required output JSON schema. It defines required top-level keys, field types, allowed enum values, ordering rules, numeric precision, and date formatting.

Read all three files before querying the environment. The answer template is the authoritative contract for the output shape.

## Task Processing Flow

1. **Parse inputs.** Read `prompt.txt`, `task_context.json`, and `answer_template.json`. Identify the target business ID(s), the requester role, the work type, and the required output shape.
2. **Explore the environment.** Start with `GET /api/tables` or `PRAGMA table_info` queries to discover available tables and columns relevant to the task.
3. **Gather evidence.** Use SQL and REST endpoints to pull case records, policy criteria, clinical documents, rate schedules, appeal records, drug trial data, margin data, or authorization records as needed by the task.
4. **Apply the business-precedence rule.** Select the correct `source_precedence` from the six available rules (see below) based on the work type and task context. Use it to determine which records control the result and which are exceptions or stale.
5. **Build the response.** Construct a JSON object that exactly matches the answer template. Include every required top-level key. Use the specified enum values, ordering rules, date formats, and numeric precision.
6. **Include the basis audit trail.** Every response must contain a `basis_audit` object with `source_precedence`, `precedence_record_order`, `controlling_record_ids`, and `exception_record_ids`.

## Source Precedence Rules

Select the `source_precedence` rule that matches the work type:

| Rule | Applies To | Meaning |
|------|-----------|---------|
| `current_clinical_records_over_stale_export` | Prior authorization determinations (clinical review) | Current environment clinical records override any stale exported data. Prefer the live case, document, and policy records in the environment. |
| `payer_appeal_before_manufacturer_assistance` | Pharmacy coverage appeals and manufacturer assistance intake | Process the payer-side appeal facts (denial, criteria, required packet) before evaluating manufacturer assistance eligibility. Appeal routing and deadline take priority over assistance screening. |
| `effective_benchmark_by_plan_modifier_and_date` | Payment integrity claim repricing | Select the rate schedule that is effective for the claim's plan, modifier, and date of service. Reject stale or non-applicable schedules. |
| `new_patient_specific_p2p_information` | Peer-to-peer summaries | New patient-specific information presented during the P2P discussion takes precedence over the original clinical review. Use the P2P event record as the controlling source when it materially changes the review. |
| `margin_threshold_then_charge_sensitivity` | Therapy margin queue analysis | First segment rows by the revenue-to-cost threshold, then flag rows that are charge-sensitive within each segment. Below-threshold rows take operational priority over charge-sensitive flags. |
| `appeal_deadline_then_clinical_then_payment_integrity` | Multi-domain cross-functional reviews | When deadline, clinical, and financial concerns overlap, resolve deadline-critical items first, then clinical determinations, then payment integrity corrections. |

### Basis Audit Trail Rules

- **`controlling_record_ids`**: List the environment record IDs (case IDs, document IDs, policy IDs, rate schedule IDs, appeal IDs, P2P event IDs, or row IDs) that directly determine the result, in operational evidence order.
- **`exception_record_ids`**: List records that explain gaps, exclusions, denials, missing information, route escalations, stale sources, or charge-sensitive flags. Order criteria or route gaps before stale or excluded records when both appear.
- **`precedence_record_order`**: List both controlling and exception record IDs together in source-precedence order, highest priority first.

## Output Rules

### Format

- Return exactly one JSON object. No markdown fences, no prose, no comments.
- Every required top-level key from the answer template must be present.
- Do not include additional top-level keys unless the template explicitly permits.

### Dates

All dates must be ISO 8601 calendar dates in `YYYY-MM-DD` format. Use `null` for date fields only when the template says it is allowed (e.g., the internal appeal deadline when no appeal is pending).

### Currency

Currency amounts are JSON numbers in USD rounded to two decimal places. Calculate totals from line-level data; do not round intermediate values before aggregation.

### Enums

Use only the enum values defined in the answer template. Match the exact casing and spelling.

### Ordering

Follow the ordering rules stated in the answer template for every ordered field:
- Clinical documents: ascending `document_id`.
- Medication names: alphabetical, lowercase.
- Appeal packet items: payer items before assistance items.
- Claim lines: source claim line order.
- Margin rows: same order as `task_context.finance_memo.queue_row_ids`.
- Below-threshold / charge-sensitive segments: alphabetical by enum value.
- Criterion IDs: ascending order.
- Exception records: criteria or route gaps before stale or excluded records.

### Null Handling

- Use `null` (JSON null) for absent modifiers, not an empty string.
- Use `null` for deadline fields only when no deadline applies and the template permits it.

## Common Query Patterns

### Discover tables

```sql
SELECT name FROM sqlite_master WHERE type='table' ORDER BY name
```

### Discover columns

```sql
PRAGMA table_info(<table_name>)
```

### Look up a case with its documents

1. `GET /api/cases/{case_id}` for the case record.
2. `GET /api/documents/{document_id}` for each referenced document.
3. `GET /api/policies/{policy_id}` for each applicable policy.
4. Use SQL to join related records when REST endpoints do not expose the relationship directly.

### Look up an appeal

1. `GET /api/appeals` to list appeals, or filter with SQL.
2. Cross-reference the case through `GET /api/cases/{case_id}`.
3. Check the associated policy through `GET /api/policies/{policy_id}`.

### Reprice a claim

1. Pull the claim and claim lines via SQL.
2. Pull rate schedules via `GET /api/rate-schedules`.
3. Determine the effective schedule by matching plan, modifier, and date of service.
4. Identify and reject stale schedules.
5. Compute corrected allowed amounts per line using the effective schedule's rate × units.
6. Compute recovery as `paid_amount - correct_allowed_amount` per line, then sum.

### Analyze a margin queue

1. Pull the margin rows by the queue row IDs from `task_context`.
2. Compute `total_cost` as defined in the task context (e.g., `variable_cost + fixed_cost_allocated`).
3. Compute `margin = revenue - total_cost`.
4. Compute `revenue_to_cost_ratio = revenue / total_cost`.
5. Flag rows as `below_threshold` when the ratio is below the configured threshold (e.g., 1.2).
6. Flag charge-sensitive rows per the environment data.
7. Identify the top below-threshold issue by the largest dollar gap to 120% of cost.

## Cross-Cutting Patterns

### Identifying stale or excluded records

When the task involves comparing multiple data sources (e.g., rate schedules, clinical exports, document versions), always check:
- Effective dates vs. the service or reporting date.
- Whether a newer version exists in the environment.
- Whether the plan or modifier context matches.

Mark records as stale or excluded when they are superseded by a more current or more specific source.

### Criteria evaluation

When the answer template specifies criteria keys (e.g., `PT-ACTIVE`, `PET-IND`, `DRUG-AUTH`):
- Map each criterion to the relevant policy and clinical evidence.
- Evaluate as `met`, `not_met`, `unclear`, or `not_applicable`.
- Cite the specific policy ID, document ID, or case fact that supports each evaluation.

### Routing and next actions

The `route` and `next_action` fields follow the operational escalation path:
- Nurse-level decisions route to `nurse_approval`, `pending_information`, or `medical_director_review`.
- Peer-to-peer outcomes route to the appeal unit if adverse.
- Payment integrity corrections route to `payment_integrity_correction` or `provider_adjustment`.
- Appeal dispositions route to `file_appeal`, `request_more_information`, or `close_not_eligible`.

Match the route and next action to the final determination and the gaps identified during evidence review.
