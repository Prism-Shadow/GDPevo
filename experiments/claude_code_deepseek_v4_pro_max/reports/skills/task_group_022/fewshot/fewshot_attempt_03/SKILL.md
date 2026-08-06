# Atlas Commerce Operations — Analytical & Data-Correction Tasks

## When to use

Invoke this skill whenever a task involves:

- Querying an **Atlas Commerce Operations** database through a REST API
- Fulfillment, refund, carrier, warehouse, or support-case analytics
- A prompt that references `<TASK_ENV_BASE_URL>`, Atlas, or input `payloads/*.json` files
- Read-only analytical scorecards **or** controlled data corrections (mutations) with audit verification

## Environment

Every run receives its target environment through a placeholder string (e.g. `<TASK_ENV_BASE_URL>`) in the task prompt. The actual base URL and credentials are provided in an `environment_access.md` file in the working directory.

**Before any API call**, read `environment_access.md` to obtain:

- `base_url` — the root URL for all API calls
- `credentials` — the `Authorization` header value (and any other required headers)
- `allowed_endpoints` — the list of endpoints the task may call

The file also documents the exact request shape (method, headers, body) for each endpoint. Use those shapes exactly.

## Workflow

### Step 1 — Understand the task scope

Read the task prompt file (typically at `input/prompt.txt` or the task root). The prompt names:

- The business domain (fulfillment, refunds, carrier operations, warehouse productivity, support health, …)
- One or more **payload files** (e.g. `input/payloads/refund_reconciliation_request.json`) that define the business scope, cutoffs, classification rules, and metric definitions
- An **output contract** — an `answer_template.json` that the final result must conform to

Read every payload file and the answer template. The template is the schema for the output — every key must be present and every value must have the correct type.

### Step 2 — Explore the database

Use `GET /api/schema` to list every table and view, and `GET /api/data-dictionary` to understand each column's meaning, data type, and relationships. Pay special attention to:

- **Time/date columns** — understand the cutoff logic (inclusive/exclusive boundaries, UTC)
- **Status/enum columns** — know every legal value before filtering
- **Foreign-key relationships** — which tables join on which columns
- **Canonical vs. raw fields** — some tables have both raw-source values and a canonical (authoritative) column

Do not skip the data dictionary. Many tasks hinge on a single column's precise semantics (e.g. whether `settled_at` includes reversals, or whether `status` vs. `canonical_status` drives the business rule).

### Step 3 — Design and execute analytical queries

Translate the business scope and metric definitions from the payload into SQL. Use `POST /api/sql` for every query. Principles:

- **Use common table expressions (WITH clauses)** to build intermediate result sets that match the payload's definitions exactly
- **Filter to the stated cutoff** — use the exact UTC boundaries from the payload, not approximations
- **When the payload defines classifications** (e.g. "severe exception", "leakage", "high priority delayed"), encode the classification rule in SQL with `CASE WHEN` so no post-processing is needed
- **Validate counts** — if two queries should agree (e.g. eligible count = complete + incomplete), verify that relationship holds
- **Round numeric rates** to the same precision shown in the answer template (typically 4 decimal places for rates, 2 for monetary amounts and durations)

### Step 4 — Handle mutations (data-correction tasks only)

Some tasks require a controlled data correction. The prompt will explicitly state this — look for phrases like "apply the approved minimal canonical correction", "correct", or "mutation".

When a correction is needed:

1. **Identify the exact target** — the single row (by primary key), the field name, the old value, and the new value. The correction must be the *minimal* change the business rules require.
2. **Do not alter** raw source values, source identity columns, or unrelated business rows.
3. **Use `POST /api/sql/transaction`** with `expected_total_changes` set to the exact number of business rows the correction should affect (typically 1). The transaction body wraps statements in the documented shape.
4. **Verify** the correction by re-querying the affected row with `POST /api/sql` and by calling `GET /api/correction-audit` to confirm an audit record was created.
5. **Determine `APPLIED` vs `NOT_APPLIED`** — report `APPLIED` only if the transaction succeeded AND the post-change state matches the expected new value AND the audit record exists. Otherwise report `NOT_APPLIED` with the actual observed results.

### Step 5 — Format and write the output

Write the final result to `answer.json` at the working-directory root. The output must:

- Be a single JSON object (or array if the template requires it)
- Conform **exactly** to the `answer_template.json` — same keys, same types, same nesting, same key ordering
- Contain **no commentary**, no markdown fences, no extra fields
- Use the exact naming conventions from the template (camelCase, snake_case, or PascalCase — match what the template uses)

## API reference

### GET /api/schema
Returns the list of tables and views with their column names and types. Always call this first.

### GET /api/data-dictionary
Returns human-readable descriptions of every column. Call this before writing any SQL.

### POST /api/sql
Read-only analytical queries. The body shape is:
```json
{"sql": "<SELECT or WITH statement>", "params": []}
```
Use parameterized placeholders (`$1`, `$2`, …) when the query depends on values from the payload, and pass them in the `params` array.

### POST /api/sql/transaction
Controlled mutations. The body shape is:
```json
{
  "statements": [{"sql": "<UPDATE/INSERT/DELETE>", "params": []}],
  "expected_total_changes": <integer>
}
```
`expected_total_changes` must equal the number of business rows the correction mutates. The endpoint validates this — a mismatch means the transaction is rejected.

### GET /api/correction-audit
Returns audit records for past corrections. Use this after a mutation to verify the audit trail was written.

## Cautions

- **Never skip the data dictionary** — column names can be misleading without their definitions
- **Use the exact cutoff** from the payload — inclusive vs. exclusive boundaries change results
- **For mutations, the `APPLIED`/`NOT_APPLIED` decision must be evidence-based** — re-query the row and check the audit endpoint after the transaction
- **Do not copy answer values from training examples** — every task has its own data and the correct answers depend on the live database state at query time
