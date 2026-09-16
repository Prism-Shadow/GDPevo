---
name: atlas-commerce-ops
description: Solve Atlas Commerce Operations analytical tasks by querying the REST API, computing business metrics from SQL results, and producing template-conforming JSON answers. Covers scorecards, reconciliations, data-quality corrections, productivity reviews, and support-health assessments.
---

# Atlas Commerce Operations Skill

Use this skill for tasks that target the Atlas Commerce Operations workplace
service. The service exposes a relational business database through REST
endpoints, and every task follows a consistent workflow: ingest the business
request and answer template, discover the schema, query with SQL, apply
business definitions exactly, compute results, and produce a single
`answer.json` that conforms to the template.

## Environment Setup

The task prompt includes a base URL in the placeholder `<TASK_ENV_BASE_URL>`.
Resolve it from the prompt text before making any API call. All requests use
these headers:

```
Authorization: Bearer atlas-ops-token-022
Content-Type: application/json
```

### Read-Only Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Confirm the service is reachable. |
| GET | `/api/schema` | Full database schema: tables, columns, types, keys, and relationships. |
| GET | `/api/data-dictionary` | Business descriptions of each table and column; domain values and semantics. |
| POST | `/api/sql` | Submit a read-only SQL `SELECT` query. Body: `{"sql": "<query>"}`. |
| GET | `/api/correction-audit` | Read correction audit records (for data-quality correction tasks). |

### Write Endpoint (Data-Correction Tasks Only)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/sql/transaction` | Submit a controlled write mutation. Body includes `sql` and metadata. |

Do not use the write endpoint unless the task explicitly requests a data
correction. All analytical tasks use only read-only endpoints.

### curl Patterns

```bash
BASE="<TASK_ENV_BASE_URL>"
AUTH="Authorization: Bearer atlas-ops-token-022"
CT="Content-Type: application/json"

# Health
curl -s -H "$AUTH" -H "$CT" "$BASE/health"

# Schema (save for reference)
curl -s -H "$AUTH" -H "$CT" "$BASE/api/schema" > /tmp/schema.json

# Data dictionary
curl -s -H "$AUTH" -H "$CT" "$BASE/api/data-dictionary" > /tmp/dict.json

# Read-only SQL
curl -s -H "$AUTH" -H "$CT" -d '{"sql": "SELECT ..."}' "$BASE/api/sql"

# Correction audit
curl -s -H "$AUTH" -H "$CT" "$BASE/api/correction-audit"
```

When the query result is large, pipe through `jq` to inspect structure or
redirect to a temporary file for programmatic processing.

## Task Workflow

Execute these steps in order. Do not skip schema discovery even when the
request payload mentions table or column names; the schema and data dictionary
may surface constraints, enums, or join paths not evident from the request
alone.

### 1. Ingest the Task Input

Read every file under `input/`:

- `input/prompt.txt` -- natural-language instructions. Extract the
  `<TASK_ENV_BASE_URL>` placeholder value and any task-specific warnings.
- `input/payloads/*.json` -- at least two files:
  - **Business request** (names vary): scope, cohort definitions, metric
    formulas, ranking rules, risk/status classification policies, rounding
    rules.
  - **Answer template** (often named `answer_template.json`): exact output
    schema with `type`, `required`, `properties`, `additionalProperties`,
    `minItems`, `maxItems`, `pattern`, `enum`, `minimum`, `maximum`,
    `multipleOf`, and `uniqueItems` constraints.

Pay close attention to every word in the business definitions. These tasks use
precise language: "at least one," "every," "strictly before," "no later than,"
and similar quantifiers directly determine SQL `WHERE` clauses and aggregation
logic.

### 2. Discover the Schema

Call `GET /api/schema` and `GET /api/data-dictionary` before writing any SQL.

From the schema response, identify:
- Table names and column names that match the business domain.
- Primary-key and foreign-key relationships.
- Column data types (especially temporal types vs. text timestamps).
- Enum or constrained columns.

From the data dictionary, identify:
- Business meaning of each column.
- Effective/raw/canonical distinctions (e.g. `raw_carrier_status` vs.
  `canonical_status`).
- Status lifecycles (e.g. what values a status column can take).
- Unit-of-measure and currency columns.

### 3. Explore the Data Incrementally

Before writing the final analytical query, run small exploratory queries:

- `SELECT DISTINCT <column> FROM <table>` on categorical columns to discover
  actual domain values.
- `SELECT COUNT(*) FROM <table> WHERE <cohort boundary>` to gauge population
  sizes.
- `SELECT * FROM <table> LIMIT 5` to see representative rows and confirm
  column formats.

Use this exploration to validate that the schema's documented values match
what the business request expects. A mismatch between documented enums and
actual data is common and must be resolved by using the actual data values.

### 4. Build and Execute Analytical Queries

Translate each business definition into SQL. Common patterns:

- **Cohort filtering**: time-window `WHERE` clauses on create/open dates, plus
  account-tier, region, campaign, or warehouse filters. Always confirm whether
  boundaries are inclusive or exclusive.
- **Effective/eligible filtering**: multi-table joins where a parent entity
  must have at least one child row meeting a condition (use `EXISTS` or
  `INNER JOIN` with `DISTINCT`).
- **Status derivation**: may require aggregating child rows (e.g. "every
  shipment must be DELIVERED") with `GROUP BY`/`HAVING` or `NOT EXISTS` for
  the negative case.
- **Rate computation**: keep numerator and denominator as separate counts
  until the final step; round only the reported rate.
- **Ranking**: `ORDER BY` with multiple columns matching the request's
  primary-secondary-tiebreak ordering, then `LIMIT`.
- **Tiered classification**: compute the condition values, then apply
  cascading `CASE`/`WHEN` or post-query if/else logic.
- **Time arithmetic**: use the database's native datetime functions. When the
  request specifies "active time" or "support active time," those are
  typically pre-computed columns.
- **Currency conversion**: join `fx_rates` on `service_date` and currency,
  multiply by `usd_per_unit`. Use the same rate for related comparisons.
- **ID patterns**: expect `ORD-\d{6}`, `CASE-\d{6}`, `WT-\d{6}`, `SCN-\d{6}`,
  `SHP-\d{6}`, `ACC-\d{4}`, `EMP-\d{4}`, `AUD-\w+`.

Break complex computations into multiple queries when a single SQL statement
would be unreadable or error-prone. Use temporary files or shell variables to
carry intermediate results.

### 5. Compute Results and Assemble the Answer

Apply the business definitions exactly as stated:

- **Rounding**: round only final reported values, to the decimal places
  specified in the request. Intermediate values used for ranking or
  classification should use unrounded computations.
- **Sorting**: arrays must be sorted exactly as specified (e.g. "ascending by
  order_id," "descending by rate then ascending by region").
- **Tie-breaking**: when two items have equal primary sort values, apply the
  secondary tiebreak exactly.
- **Null handling**: an incomplete order with no shipment promise does not
  satisfy a lateness condition. A missing value is not zero unless the
  definition explicitly says so.
- **Distinct counts**: pay attention to whether the definition says "distinct
  orders" vs. "logical refunds" vs. "rows." Use `COUNT(DISTINCT ...)` when the
  definition requires it.

### 6. Validate and Write the Answer

Before writing `answer.json`:

- Confirm every required field from the template is present.
- Confirm `additionalProperties: false` means no extra fields.
- Confirm array lengths match `minItems`/`maxItems`.
- Confirm numeric values satisfy `minimum`, `maximum`, `multipleOf`.
- Confirm string values match `pattern` and `enum` constraints.
- Confirm `uniqueItems` arrays have no duplicates.
- Confirm array ordering matches the request's specification.
- Validate the JSON with `jq` or `python3 -m json.tool`.

Write the validated JSON to `answer.json` at the workspace root. Do not
include any commentary, markdown fences, or text outside the JSON object.

## Data-Correction Tasks

When the task involves a data-quality correction (a single canonical field
update with audit trail):

1. **Identify the contradiction**: compare raw source values against canonical
   columns by querying both. The request will state how many contradictions
   exist (typically exactly one).
2. **Read correction metadata from the request**: `reason_code`, `actor`,
   `audit_id`, `correction_key`, `corrected_at`.
3. **Run the pre-correction analysis**: query the cohort's backlog or other
   metric as defined before the fix.
4. **Execute the transaction**: use `POST /api/sql/transaction` with the exact
   `UPDATE` statement and the audit metadata from the request. The service
   returns affected-row counts.
5. **Verify post-correction state**: re-run the analysis query to confirm the
   canonical value changed and the metric shifted as expected.
6. **Retrieve the audit record**: call `GET /api/correction-audit` and locate
   the matching record by `audit_id` or `correction_key`.
7. **Set `correction_status`**: `APPLIED` only when exactly one business row
   and one audit row committed, and a post-change query confirms the new
   canonical value. Otherwise `NOT_APPLIED`.

## Common Pitfalls

- **Ignoring the data dictionary**: the schema shows column names and types,
  but the data dictionary explains business semantics. A column named `status`
  might be raw, canonical, or derived -- only the dictionary tells you which.
- **Time boundary off-by-one**: inclusive vs. exclusive boundaries on datetime
  ranges. When the request says "at or before the cutoff," use `<=`. When it
  says "strictly before," use `<`.
- **Rounding intermediate values**: round only final reported rates. Using
  rounded values for ranking or classification can change the outcome.
- **Mixing up "delivered by" vs. "delivered after"**: "no later than" means
  `<= promised_delivery_at`. "More than 24 hours after" means
  `> promised_delivery_at + interval '24 hours'`.
- **Forgetting the denominator for rates**: incomplete orders typically remain
  in the denominator for on-time rates. Read the rate definition carefully.
- **Case sensitivity in enums**: compare `UPPER()` or use exact casing as
  found in exploratory queries. Request documents may use a different case
  convention than the database.
- **Reopened cases**: when a state summary separates "open at cutoff" and
  "reopened at cutoff," reopened is a subset of open. Count reopened
  separately, then report both.
- **Median computation**: for an even number of values, average the two
  central values. Use `ORDER BY` and offset-based selection or post-query
  computation.
- **FX rate timing**: the request specifies which date to use for the rate
  (typically the refund/reversal `service_date`). Do not use the order date.
- **Raw values in corrections**: only the canonical column is updated; raw
  source columns, identity columns, and unrelated rows must stay untouched.

## Answer Template Validation Checks

Before finalizing, verify these template constraints programmatically:

```bash
# Check required fields are present
jq -e '.required' answer_template.json

# Validate the output object against the template
python3 -c "
import json
with open('answer.json') as f:
    answer = json.load(f)
with open('input/payloads/answer_template.json') as f:
    tmpl = json.load(f)
for r in tmpl.get('required', []):
    assert r in answer, f'Missing required: {r}'
extra = set(answer.keys()) - set(tmpl.get('properties', {}).keys())
assert not extra, f'Extra fields: {extra}'
print('Validation passed')
"
```
