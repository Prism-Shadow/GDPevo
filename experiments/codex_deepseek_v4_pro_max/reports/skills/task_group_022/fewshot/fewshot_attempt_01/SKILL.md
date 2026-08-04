Atlas Commerce Operations — Analytical and Correction Tasks
---

This skill covers read‑only analytical reporting tasks and controlled
single‑row data‑correction tasks against the Atlas Commerce Operations
database. Follow this workflow whenever a prompt references an Atlas
Commerce Operations, Atlas workplace, or Atlas fulfillment service
accessible through an authenticated HTTP API at a runtime‑provided base
URL.

## Connection Details

The service lives at `<TASK_ENV_BASE_URL>`. Every request to an
`/api/` endpoint MUST include:

```
Authorization: Bearer atlas-ops-token-022
```

Available endpoints:

| Method | Path                    | Purpose                                  |
|--------|-------------------------|------------------------------------------|
| GET    | `/api/schema`           | Table names and column lists             |
| GET    | `/api/data-dictionary`  | Column descriptions and business meaning |
| GET    | `/api/correction-audit` | Audit trail of applied corrections       |
| POST   | `/api/sql`              | Read‑only SELECT / WITH queries          |
| POST   | `/api/sql/transaction`  | Guarded writes + reads in one transaction|

`POST /api/sql` body:
```json
{"sql": "<SELECT or WITH>", "params": ["<scalar>"]}
```

`POST /api/sql/transaction` body:
```json
{
  "statements": [
    {"sql": "<SQL>", "params": ["<scalar>"]}
  ],
  "expected_total_changes": 0
}
```
Transaction rules:
- 1 to 6 statements per call.
- `expected_total_changes`: integer 0–12. Set it to the number of INSERT
  or UPDATE rows you expect (does not count SELECT rows).
- Only `carrier_scans` and `inventory_movements` accept guarded UPDATE.
- Only `correction_audit` accepts INSERT (all audit columns required).
- Any read‑only statement is allowed alongside writes.

## Discovery Workflow (Always Do First)

1. Call `GET /api/schema` to learn every table name and its columns.
   Do not query `sqlite_master` or any PRAGMA; use only the schema
   endpoint for metadata.

2. Call `GET /api/data-dictionary` to understand column meanings,
   enumerations, and business semantics. Rely on this for domain
   interpretation rather than guessing from column names.

3. If the task is a correction task, also call
   `GET /api/correction-audit` to see the current audit trail.

## Input File Pattern

Every task supplies two files in `input/payloads/`:

- **Request payload** (e.g. `fulfillment_request.json`,
  `warehouse_productivity_request.json`): Contains the business scope,
  metric definitions, cohort rules, rounding policies, and any
  correction instructions. This is the source of truth for *what* to
  compute and *how*.

- **Answer template** (always named `answer_template.json`): A JSON
  Schema document specifying the exact output shape, required fields,
  types, enums, minimum/maximum values, decimal precision, and
  ordering rules. The final output MUST conform to this schema
  exactly — no extra fields, no omitted required fields.

**Read both files completely before writing any SQL.** The request
payload defines the business logic; the answer template defines the
output contract.

## Analytical Task Workflow

These tasks compute metrics from the database without changing any
rows. They dominate (fulfillment scorecards, refund reconciliations,
warehouse productivity reviews, support health reviews).

### Step 1 — Understand the Cohort
Identify the population from the request payload:
- Which tables contain the primary entities (orders, shipments, tasks,
  cases, refunds)?
- What time window and cutoff apply?
- What account/warehouse/region filters are in scope?

### Step 2 — Map Business Definitions to SQL
Translate each business definition into a query or a computed column.
Common patterns:
- **Effective / logical rows**: Use the most authoritative (canonical)
  row per entity. Never count raw source rows when a canonical
  interpretation exists.
- **Time‑window filtering**: Apply inclusive boundaries exactly as
  specified.
- **Cutoff‑based state**: Evaluate entity state as of the cutoff
  timestamp, not as of the current moment.
- **Composite conditions**: Use CTEs (WITH clauses) to layer
  intermediate results — first the cohort, then entity‑level
  aggregations (shipments per order, scans per shipment), then final
  metric computation.

### Step 3 — Compute Metrics
Build the final SELECT that produces every metric needed by the
answer template. Key conventions:

- **Rounding**: Apply rounding exactly as specified in the request
  payload. Only round *final* reported values; keep intermediate
  computations at full precision.
- **Rates**: A rate is a ratio in [0, 1]. The denominator is always the
  eligible population (not just the completed/closed subset).
- **Rankings**: Multi‑key ordering is common. Apply all keys in the
  exact order given.
- **Status rules**: Evaluate tiered status rules (HEALTHY / WATCH /
  CRITICAL; CONTROLLED / ELEVATED / SEVERE; etc.) in the order listed.
  The first matching rule wins.

### Step 4 — Format the Output
Construct a single JSON object matching every `required` field in the
answer template. Validate:
- Integer fields are integers (not floats).
- Array fields have unique items and are sorted as specified.
- Enum fields use exactly the stated uppercase values.
- Decimal fields match the stated precision (`multipleOf` /
  `decimal_places`).

Write the result to `answer.json` with no surrounding commentary.

## Correction Task Workflow

These tasks fix a single data-quality issue and verify the result
(carrier quality reviews). They combine analytical queries with one
controlled write.

### Step 1 — Identify the Contradiction
Query the relevant tables to find the row where a raw/source value
conflicts with the canonical value. The request payload describes what
kind of contradiction to look for (e.g. a carrier scan whose raw
status contradicts its canonical status). Find exactly one affected
row.

### Step 2 — Measure Pre‑Correction State
Run the analytical queries that define the *before* picture (e.g.
backlog count at the cutoff). Record these values.

### Step 3 — Apply the Correction
Use `POST /api/sql/transaction` with two statements:

1. A guarded UPDATE on the business table (only `carrier_scans` or
   `inventory_movements`), changing only the canonical field to the
   correct value. Guard with a WHERE clause that targets the specific
   row and its current value to avoid accidental multi‑row writes.

2. An INSERT into `correction_audit` with all audit columns populated
   from the request payload's approved correction block: `audit_id`,
   `correction_key`, `entity_type`, `entity_id`, `source_row_id`,
   `field_name`, `old_value`, `new_value`, `reason_code`,
   `corrected_at`, `actor`.

Set `expected_total_changes` to exactly 2 (one UPDATE row + one INSERT
row). The transaction API validates this; a mismatch indicates
unexpected behavior.

### Step 4 — Verify Post‑Correction State
Re‑run the pre‑correction analytical query to confirm the change is
visible. Compute the delta (post − pre).

### Step 5 — Report
Populate the answer template with:
- `correction_target`: the identified row, field, old and new values.
- `mutation_result`: affected business rows and audit rows (from the
  transaction result).
- `audit_record`: all audit columns as written.
- `backlog_analysis` (or equivalent): pre/post counts and delta.
- `correction_status`: `APPLIED` only if exactly one business row and
  one audit row were committed AND the post‑change query confirms the
  corrected value. Otherwise `NOT_APPLIED`.

## General Rules

- **Never query SQLite metadata tables** (`sqlite_master`, PRAGMA).
  Use `/api/schema` and `/api/data-dictionary` exclusively.

- **Never change raw/source values**. Only canonical fields may be
  corrected, and only with an approved correction and audit record.

- **Keep intermediate computation at full precision**. Round only
  the final reported values.

- **Sort arrays exactly as specified** (ascending IDs, descending
  metric then ascending tie‑break, etc.).

- **Use `application/json` Content‑Type** on all POST requests.

- **curl patterns** for reference:
  ```bash
  # Schema discovery
  curl -sS "http://task-env:9022/api/schema" \
    -H "Authorization: Bearer atlas-ops-token-022"

  # Read query
  curl -sS -X POST "http://task-env:9022/api/sql" \
    -H "Authorization: Bearer atlas-ops-token-022" \
    -H "Content-Type: application/json" \
    --data '{"sql":"SELECT ...","params":[...]}'

  # Transaction
  curl -sS -X POST "http://task-env:9022/api/sql/transaction" \
    -H "Authorization: Bearer atlas-ops-token-022" \
    -H "Content-Type: application/json" \
    --data '{"statements":[...],"expected_total_changes":2}'
  ```

- **Output discipline**: Write exactly one JSON object matching the
  answer template to `answer.json`. No explanatory text, no additional
  fields, no markdown fences around the JSON.
