# Atlas Commerce Operations — Analytical Task Runner

## Purpose

Execute analytical and corrective tasks against the Atlas Commerce Operations database through its authenticated HTTP API. Each task follows a standard discovery→query→compute→output pipeline, producing a single `answer.json` that conforms to a supplied output schema.

## Invocation

This skill applies when a task directory contains:
- `input/prompt.txt` — natural-language task description referencing `<TASK_ENV_BASE_URL>`
- `input/payloads/*.json` — one or more JSON payloads with business scope, definitions, and rules
- `input/payloads/answer_template.json` — the exact output JSON schema

The skill is also triggered by references to "Atlas Commerce Operations", "Atlas workplace", or the endpoint names `/api/schema`, `/api/data-dictionary`, `/api/sql`, `/api/sql/transaction`, `/api/correction-audit`.

## Environment Resolution

1. The prompt uses the placeholder `<TASK_ENV_BASE_URL>`. Resolve this to the actual base URL from the environment. If an `environment_access.md` file exists in the working directory, its `base_url` field is authoritative and overrides any other reference (localhost, env vars, `setup.sh`, `TASK_ENV_BASE_URL`).
2. Use the `credentials` block from `environment_access.md` for the `Authorization` header. The token is typically a Bearer token.
3. If `environment_access.md` lists `allowed_endpoints`, only those endpoints are available. The canonical set is:
   - `GET /api/schema`
   - `GET /api/data-dictionary`
   - `POST /api/sql`
   - `POST /api/sql/transaction`
   - `GET /api/correction-audit`

## API Reference

All calls use the resolved base URL. Every request must include the `Authorization` header.

### GET /api/schema
Returns the database schema (tables, columns, types, relationships). Always call this first to understand the data model before writing any query.

### GET /api/data-dictionary
Returns human-readable field descriptions, enumerations, and business semantics. Call this after schema discovery to interpret column meanings and value domains.

### POST /api/sql
Read-only analytical queries. The service only accepts `SELECT` and `WITH` (CTE) statements. All other statement types are rejected.

**Request:**
```
Content-Type: application/json
Authorization: Bearer <token>

{
  "sql": "<SELECT or WITH SQL string>",
  "params": ["<optional scalar: string|number|boolean|null>"]
}
```

**Usage notes:**
- Use parameterized queries (`$1`, `$2`, …) with the `params` array for values that vary. Do not interpolate user or request values into the SQL string.
- Start with exploratory `SELECT * FROM <table> LIMIT 5` queries to see representative rows.
- Build queries incrementally: verify each intermediate result before composing it into a larger CTE or subquery.

### POST /api/sql/transaction
Controlled write operations. Use only when the task explicitly requires a data correction. Every statement in the transaction must be a data-modifying statement (`UPDATE`, `INSERT`, `DELETE`). `SELECT` statements are not permitted inside a transaction.

**Request:**
```
Content-Type: application/json
Authorization: Bearer <token>

{
  "statements": [
    {
      "sql": "<SQL statement>",
      "params": ["<optional scalar>"]
    }
  ],
  "expected_total_changes": "<required integer — the exact number of rows the transaction is expected to modify>"
}
```

**Usage notes:**
- `expected_total_changes` is mandatory and must match the actual row count modified. The service rejects the transaction if the count does not match.
- Only correct the minimal set of fields and rows needed. Do not alter raw source values, source identity columns, or unrelated business rows.
- After the transaction, verify the result with a read-only `POST /api/sql` query.

### GET /api/correction-audit
Returns audit records for past corrections. Use after a transaction to confirm the audit trail was written, or to inspect existing correction history. Filter by audit ID, correction key, entity ID, or time range as the endpoint supports.

## Task Execution Pipeline

### Phase 1 — Read Inputs
1. Read `input/prompt.txt` to understand the task type (analytical vs. corrective), the business domain, and any special instructions.
2. Read every JSON file under `input/payloads/`. At minimum there will be:
   - A **request payload** (`*_request.json`) — contains scope, cohort definitions, business rules, classification policies, cutoff timestamps, rounding policies, and ranking rules.
   - An **answer template** (`answer_template.json`) — JSON Schema describing the exact output shape, required fields, types, enum values, array ordering, and numeric precision.

### Phase 2 — Schema Discovery
1. Call `GET /api/schema` and study the returned structure. Map every table and column referenced (directly or implied) by the request payload.
2. Call `GET /api/data-dictionary` and cross-reference field descriptions with the business definitions in the request payload. Pay special attention to:
   - Enumeration values and their meanings
   - Timestamp semantics (created_at vs. effective dates vs. system timestamps)
   - Status lifecycles and terminal states
   - Currency and unit conventions
   - Relationship cardinalities (one-to-many, optional vs. required)

### Phase 3 — Query and Compute
1. Write exploratory queries to understand data volumes, distributions, and edge cases within the task's scope.
2. Build progressive analytical queries. Common patterns:
   - **Cohort isolation**: Filter to the exact population defined in the request (by campaign, account tier, region, warehouse, time window, etc.).
   - **State evaluation**: Determine effective state at a cutoff timestamp by examining the most recent event/status before or at the cutoff.
   - **Aggregation with grouping**: Compute rates, counts, and sums grouped by dimension (region, account, reason code, team, employee).
   - **Ranking with tie-breaking**: Use the ordering rules from the request payload — the primary key is always specified, with a deterministic tie-break (typically ascending ID).
   - **Classification**: Apply tiered status/risk rules in order. The rules are evaluated top-to-bottom; the first matching condition wins. If no explicit rule matches, use the catch-all/"otherwise" status.
3. Round only at the final step, using the precision specified in the request payload (typically 2 or 4 decimal places).

### Phase 4 — Correction (Conditional)
Only execute this phase when the task explicitly requests a data correction.

1. **Identify the contradiction**: Query both raw and canonical representations of the data to find the exact row and field where they diverge. The request payload will describe the contradiction type.
2. **Plan the minimal change**: Determine the single field update that resolves the contradiction. Do not change raw source values, identity columns, or unrelated rows.
3. **Execute the transaction**: Use `POST /api/sql/transaction` with `expected_total_changes` set to the exact number of business rows that should change. The service confirms or rejects based on the count match.
4. **Verify**: Query the corrected row to confirm the new canonical value. Query `GET /api/correction-audit` to confirm the audit record was written with the expected fields (`audit_id`, `correction_key`, `entity_type`, `entity_id`, `source_row_id`, `field_name`, `old_value`, `new_value`, `reason_code`, `corrected_at`, `actor`).
5. **Determine status**: If exactly one business row and one audit row were committed and the post-change query confirms the corrected value, report `APPLIED`. Otherwise report `NOT_APPLIED` with the results actually observed.

### Phase 5 — Answer Construction
1. Build a JSON object where every key and value type matches `answer_template.json` exactly.
2. Constraints to observe:
   - **No additional properties**: The answer object must not contain any key not listed in the template's `required` array and `properties` block.
   - **Type fidelity**: Integers must be whole numbers (no decimal point). Numbers with `multipleOf` must satisfy that constraint. Strings must match any specified `pattern`.
   - **Enum values**: Use the exact enum strings from the template, not synonyms.
   - **Array ordering**: Follow the ordering rules in the template or request payload. Common orderings: ascending ID, descending metric then ascending ID as tie-break.
   - **Array uniqueness**: Arrays marked `uniqueItems: true` must not contain duplicates.
   - **Array cardinality**: Arrays with `minItems`/`maxItems` must have exactly that many elements.
   - **Numeric precision**: Round final reported rates and amounts to the specified decimal places. Use the rounding rule from the request (typically round-half-up or standard IEEE 754).
   - **Null handling**: Do not use `null` unless the schema explicitly permits it. Empty arrays are preferred over null for missing collections.
3. Write the result to `answer.json` in the working directory. The file must contain only the JSON object — no markdown fences, no commentary, no trailing text.

## Business Rule Patterns

These patterns recur across tasks. When you encounter them in a request payload, apply the corresponding interpretation:

### Cutoff-Based State Evaluation
When a task specifies a `cutoff_at` or `as_of_cutoff` timestamp:
- Consider only events/statuses with an effective timestamp **at or before** the cutoff.
- For an entity to be in a terminal state (e.g., "delivered", "resolved", "complete"), the terminal event must exist and be the most recent effective event at or before the cutoff.
- An entity without a terminal event at the cutoff is in its last known non-terminal state.

### Time-Window Cohort Membership
When a task specifies a window with `start_at`/`end_at` (or `start`/`end`) and `boundary: "inclusive"` (or `inclusive: true`):
- Both boundaries are inclusive: `effective_timestamp >= start AND effective_timestamp <= end`.
- When the boundary is not labeled, treat UTC timestamps as exact and inclusive of the stated instant.

### Active-Time Clock
When a task specifies a "clock basis" of `SUPPORT_ACTIVE_TIME` or similar:
- Measure durations using only the intervals the entity is in an active state (not paused, not suspended, not awaiting-external).
- For unresolved/uncompleted entities at the cutoff, use the active elapsed time from creation/opening to the cutoff.
- For resolved/completed entities, use the active elapsed time from creation/opening to resolution/completion.

### Multi-Tier Status/Risk Classification
When a task provides a list of status rules (e.g., `overall_status_rules`, `facility_status_rules`, `support_risk_policy`):
- Evaluate rules in the order listed. The first rule whose condition is satisfied determines the status.
- If no rule matches and an "otherwise"/"all other outcomes" catch-all exists, use that.
- Conditions are combined with AND within a rule. All sub-conditions must be true.

### Ranking with Tie-Breaking
When a task specifies ordering rules:
- Apply the primary sort first (typically a metric descending).
- Apply the secondary tie-break sort (typically an identifier ascending).
- When a limit is specified (e.g., "top three", "first two"), take exactly that many after sorting.

### Rounding Policy
- Apply rounding only to the final reported value, not to intermediate calculations.
- Use the precision declared in the answer template's `multipleOf` or the request payload's rounding directive.
- Unless otherwise specified, use standard mathematical rounding (round half up).

## Error Recovery

- If a SQL query returns an error, read the error message carefully. Common causes: misspelled column names, wrong table references, invalid join conditions, or unsupported statement types.
- If the schema or data dictionary is surprising, re-read the request payload's business definitions — the definitions are authoritative over assumptions.
- If computed values seem unreasonable, verify intermediate counts with simpler queries before debugging the formula.
- If a transaction fails, check `expected_total_changes` — it must match exactly, including zero for no-op corrections.
