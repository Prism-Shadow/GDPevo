# Atlas Commerce Operations — Analytical & Correction Skill

## When to use

Invoke this skill whenever the task involves querying or correcting data in the **Atlas Commerce Operations** database through its authenticated REST API. The task will arrive with a `prompt.txt` describing the business ask, a request payload (`.json`) scoping the work and defining business rules, and an `answer_template.json` specifying the exact output schema.

Do **not** use this skill if the task references a different database or API surface.

## Environment setup

Read `environment_access.md` from the working directory. It contains:

- `base_url` — the root URL for all API calls (e.g. `http://task-env:9022/`)
- `credentials` — an `Authorization` header to include on every request

Use `curl` with `-H "Authorization: Bearer <token>"` for every API call. Pipe through `jq` for JSON processing. Construct full endpoint URLs by appending the path to `base_url`.

## Available endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/schema` | Returns the database schema — table names, column names, types, relationships |
| GET | `/api/data-dictionary` | Returns field-level descriptions, enumerations, business meanings |
| POST | `/api/sql` | Submit a read-only SQL `SELECT` query. Body: `{"sql": "<query>"}`. Returns result rows as JSON. |
| POST | `/api/sql/transaction` | Submit a controlled write (UPDATE/INSERT). Body: `{"sql": "<statement>"}`. Returns affected row count and audit info. Use ONLY when the task explicitly authorizes a data correction. |
| GET | `/api/correction-audit` | Returns audit-trail records for past corrections. Used to verify that a transaction committed correctly. |

## Phase 1 — Understand the task scope

Read three input files in the task directory:

1. **`prompt.txt`** — The business narrative. Identifies the stakeholder, the operation type (analytical vs. correction), and which payload files to consult. It also tells you where to write the answer.

2. **The request payload** (named in `prompt.txt`, e.g. `input/payloads/fulfillment_request.json`) — Contains:
   - Population scope and filters (date windows, cohorts, regions, tiers, cutoff timestamps)
   - Business definitions (how to classify rows, compute metrics, identify exceptions)
   - Ranking and ordering rules
   - Status/risk classification tier tables with explicit thresholds
   - Rounding and unit conventions

3. **`answer_template.json`** (e.g. `input/payloads/answer_template.json`) — The exact JSON Schema for the output. Every `required` field must appear. `additionalProperties: false` means no extra keys. Pay attention to `type`, `enum`, `pattern`, `minimum`/`maximum`, `multipleOf`, array `minItems`/`maxItems`/`uniqueItems`, and ordering descriptions.

Before writing any SQL, identify:
- Is this read-only (analytical) or does it require a correction (transactional)?
- What is the population filter? (date ranges, account tiers, regions, statuses, campaign IDs)
- What are the computed metrics and their formulas?
- What are the ranking/sorting rules?
- What are the status/risk classification bands and their thresholds?

## Phase 2 — Explore the schema

Issue two discovery calls before writing domain queries:

```bash
curl -s -H "Authorization: Bearer <token>" "<base_url>/api/schema" | jq .
curl -s -H "Authorization: Bearer <token>" "<base_url>/api/data-dictionary" | jq .
```

From the schema, identify:
- Which tables hold the relevant business entities (orders, shipments, refunds, carrier scans, warehouse tasks, support cases, accounts, etc.)
- Join keys between tables
- Column types relevant to filtering (timestamps, enums, amounts)

From the data dictionary, identify:
- Enumeration values for status columns
- The meaning of timestamp columns (created_at vs. updated_at vs. effective dates)
- Currency and unit conventions
- Identifier patterns (order IDs, shipment IDs, case IDs)

## Phase 3 — Query the data

Construct SQL queries that implement the task's business definitions directly:

- **Filtering**: Translate scope conditions into `WHERE` clauses. Treat cutoff timestamps as exact UTC boundaries. Use inclusive/exclusive as specified.
- **Joins**: Follow the schema relationships. When a definition requires related rows (e.g. "every shipment for an order"), join and aggregate.
- **Aggregation**: Use `COUNT`, `SUM`, `AVG`, `GROUP BY` as needed. When computing rates, compute both numerator and denominator before dividing — do not average pre-computed rates.
- **Ordering**: Apply the exact ordering rules in the request. For tie-breaking, use the secondary (and tertiary) sort keys exactly as specified.
- **Edge cases**: Handle NULLs explicitly. An order with no shipments is incomplete, not an error. A case with no response uses elapsed time at the cutoff. A reverse-sorted array is still sorted.

Submit queries one at a time via:

```bash
curl -s -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"sql": "<query>"}' "<base_url>/api/sql" | jq .
```

Iterate: start with a broad population count, then refine. Verify intermediate counts add up (complete + incomplete = total, etc.).

## Phase 4 — Apply business logic

Compute derived values from query results using `jq` or direct calculation:

- **Rates and ratios**: Compute from the raw counts. Round only at the final step, to the specified precision. Use `round($n * 10000) / 10000` for 4 decimal places, or `* 100 / 100` for 2 decimal places.
- **Rankings**: Sort programmatically using the request's ordering rules. The data may already be ordered by SQL, but verify. For "first N" or "worst N", apply the sort direction (ascending/descending) and ties as specified.
- **Status/risk classification**: Evaluate tier conditions in order. The first matching tier wins. Use the exact thresholds from the request. Do not invert comparisons — "below X" means `< X`, not `<= X`, unless the request says "at or below".
- **Exception/leakage/candidate identification**: Apply the multi-condition definitions exactly. A candidate matches if *any* condition is true. Order the output IDs as specified (usually ascending).
- **Median**: For an odd count, pick the center value after sorting. For an even count, average the two central values.

## Phase 5 — Data correction (transactional tasks only)

When the task requires a correction:

1. **Identify the contradiction**: Query the raw data to find the row where a source/canonical field mismatch exists. The request will describe the contradiction pattern. Only one row should match — if more or fewer, the preconditions are not met.

2. **Plan the correction**: Determine the exact column, old value, and new canonical value. The request provides the correction metadata (reason_code, actor, audit_id, correction_key, corrected_at).

3. **Execute the transaction**:
   ```bash
   curl -s -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
     -d '{"sql": "UPDATE <table> SET <column> = '\''<new_value>'\'' WHERE <id_column> = '\''<row_id>'\''"}' \
     "<base_url>/api/sql/transaction" | jq .
   ```
   Record `affected_business_rows` and `audit_rows` from the response.

4. **Verify the correction**: Re-query the corrected row to confirm the new canonical value is persisted. Query the audit endpoint to confirm the audit record matches the request metadata.

5. **Report status**: `APPLIED` only if exactly one business row and one audit row committed AND the post-change query confirms the corrected value. Otherwise `NOT_APPLIED`.

## Phase 6 — Produce the output

Write the answer as a single JSON object to the output file named in `prompt.txt` (usually `answer.json`):

- Include every `required` field from the answer template.
- Use the exact types, formats, and constraints from the template schema.
- Arrays must be in the specified order. Integer fields must be whole numbers (no decimals). Number fields must use the specified precision.
- Enum fields must use exact values (case-sensitive).
- IDs must match the pattern in the template (e.g. `^ORD-[0-9]{6}$`).
- No commentary, no extra fields, no markdown wrapping — just the JSON object.

Validate the output against the template before writing:

```bash
# Check required fields are all present
jq '...' answer.json
```

## Common pitfalls

- **Rounding too early**: Compute rates from raw integers, round only the final reported value.
- **Denominator confusion**: When the rate denominator is "all eligible X" and the numerator is a subset, incomplete items stay in the denominator — do not exclude them.
- **Timestamp cutoff precision**: "At or before the cutoff" means `<=`. "Strictly before" means `<`. "More than 24 hours after" means `> cutoff + 24h`.
- **Sorting arrays**: When IDs must be "sorted ascending", sort them. When objects must be ordered by one key descending then another ascending, implement the multi-key sort exactly.
- **Correction preconditions**: If the data doesn't match the expected contradiction (e.g. zero rows or multiple rows found), report `NOT_APPLIED` with the observed state — do not attempt the correction.
- **Even-count median**: Average the two central values, don't pick one.
- **NULL handling**: A NULL promised_delivery_at means "no promise" — the order cannot be late (but can still be incomplete).
