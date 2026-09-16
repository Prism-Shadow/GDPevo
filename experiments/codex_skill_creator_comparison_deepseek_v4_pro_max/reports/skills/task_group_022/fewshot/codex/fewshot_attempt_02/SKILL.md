---
name: atlas-ops
description: Connect to the Atlas Commerce Operations API to explore its live database schema, run analytical SQL queries, execute controlled data corrections, and produce structured JSON answers from business request payloads. Use when tasked with scorecards, reconciliations, quality corrections, productivity reviews, support health reports, or any operational analysis that requires querying or correcting the Atlas database through its HTTP API.
---

# Atlas Operations

Query and optionally correct the Atlas Commerce Operations database through its
HTTP API. The API provides schema introspection, a read-only SQL endpoint, a
transactional SQL endpoint, and a correction-audit view.

## Connectivity

The base URL is provided in the task prompt as `<TASK_ENV_BASE_URL>` (or an
equivalent placeholder). The authorization header from the environment access
notes must be sent on every request:

```
Authorization: Bearer atlas-ops-token-022
```

All endpoints expect JSON and return JSON.

## Endpoints

| Method | Path                   | Purpose                                       |
|--------|------------------------|-----------------------------------------------|
| GET    | `/api/schema`          | List all tables and columns                   |
| GET    | `/api/data-dictionary` | Human-readable descriptions of every column   |
| POST   | `/api/sql`             | Run a read-only analytical `SELECT` query     |
| POST   | `/api/sql/transaction` | Run a controlled `UPDATE` (corrections only)  |
| GET    | `/api/correction-audit`| Inspect committed correction audit records    |

## Workflow

### Step 1 – Orient

Read the task prompt and the request payload (usually a JSON file under
`input/payloads/`). The payload defines the scope, business definitions,
rollup rules, classification policies, and rounding. Also read the
answer template (`answer_template.json`) — it is a strict JSON Schema
describing every required field and its constraints. The final answer
must conform to it with no extra fields.

### Step 2 – Explore the schema

Fetch `GET /api/schema` and `GET /api/data-dictionary`. Use them to
understand table names, column names, column types, relationships, and
what each field means. See [references/schema_exploration.md](references/schema_exploration.md)
for exploration patterns.

### Step 3 – Build and run analytical queries

Translate the business definitions from the request payload into SQL.
POST each query body to `/api/sql`:

```json
{"query": "SELECT ..."}
```

See [references/sql_patterns.md](references/sql_patterns.md) for common
query patterns (time windows, effective/canonical resolution, JOINs,
aggregation, NULL handling).

Run one query at a time. Use results from earlier queries to refine
later ones when needed.

### Step 4 – Compute derived values

Process raw query results into the fields required by the answer
template. See [references/computation_patterns.md](references/computation_patterns.md)
for rounding conventions, multi-level sorting with tiebreakers,
tiered status classification, rate calculations, and median.

### Step 5 – Corrections (only when the task requests one)

When the task payload includes an `approved_correction` block, the task
requires a controlled data mutation:

1. Use `POST /api/sql` to find the exact row that needs correction.
2. Build an `UPDATE` statement that changes only the single canonical
   field identified in the correction scope. `WHERE` must target the
   specific row by its stable identifier.
3. POST the UPDATE to `/api/sql/transaction`:
   ```json
   {"query": "UPDATE ... SET ... WHERE ...", "audit_id": "...", "correction_key": "...", "reason_code": "...", "corrected_at": "...", "actor": "..."}
   ```
   Include every metadata field exactly as given in the request
   payload's `approved_correction` block.
4. The response reports `affected_business_rows` and `audit_rows`.
5. Run a post-correction `SELECT` via `/api/sql` to confirm the new
   value is in place.
6. Verify the audit record with `GET /api/correction-audit`.
7. Report `APPLIED` only when exactly one business row and one audit
   row committed AND the post-change query confirms the corrected
   value. Otherwise report `NOT_APPLIED`.

Raw source values, source identity fields, and unrelated business rows
must remain unchanged.

### Step 6 – Write the answer

Write a single JSON object to `answer.json` that conforms exactly to
the answer template schema. No narrative text, no additional fields.
All array elements must be ordered as specified. All numeric fields
must respect the stated rounding and precision.

## Key conventions

- **Rounding**: Apply rounding only to final reported values, using the
  precision stated in the request payload (typically 4 decimal places
  for rates, 2 for currency, 2 for hours). Keep intermediate values
  unrounded.
- **Sorting**: Follow the payload's ordering specification exactly.
  When a tiebreaker is "ascending by X", that applies only among items
  that tie on the primary sort key.
- **Time windows**: Inclusive boundaries on both ends unless the
  payload states otherwise. Cutoffs are evaluated strictly (`<` for
  "before", `<=` for "at or before").
- **"Effective" / "canonical"**: Some tables have both raw and
  canonical columns. Business logic always uses the canonical or
  effective column, never the raw source column.
- **NULL handling**: An absent value changes semantics — e.g., an order
  with no shipment is incomplete, an incomplete order with no shipment
  promise does not satisfy the severe-exception time condition.
