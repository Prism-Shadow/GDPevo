## When to Use

Use this skill when the task involves analyzing or correcting business operations data through the Atlas Commerce Operations API — including fulfillment scorecards, refund reconciliation, carrier quality reviews, warehouse productivity assessments, and support health reviews. The skill applies whenever a prompt references an authenticated workplace service at `<TASK_ENV_BASE_URL>` with SQL query and transaction endpoints.

## API Endpoints and Authentication

All `/api/` endpoints require the HTTP header:

```
Authorization: Bearer atlas-ops-token-022
```

### Discovery Endpoints

- `GET /api/schema` — Returns table names and column definitions.
- `GET /api/data-dictionary` — Maps business concepts to technical column names and field meanings.
- `GET /api/correction-audit` — Returns correction-audit records for verification.

### Read-Only Queries

```
POST /api/sql
Content-Type: application/json
JSON body: {"sql": "<SELECT or WITH query>", "params": ["<scalar>"]}
```

Only `SELECT` and `WITH` statements are allowed. Use parameterized queries with `?` placeholders and the `params` array.

### Guarded Transactions

```
POST /api/sql/transaction
Content-Type: application/json
JSON body: {
  "statements": [
    {"sql": "<SQL>", "params": ["<scalar>"]}
  ],
  "expected_total_changes": <integer 0-12>
}
```

Rules:
- 1 to 6 statements per transaction.
- `expected_total_changes` must match the actual total rows changed.
- Allowed mutations: guarded `UPDATE` on `carrier_scans` or `inventory_movements`; `INSERT` into `correction_audit` with all audit columns.
- `SELECT`/`WITH` statements may also appear in a transaction.
- Wrap mutations in a transaction only when the task explicitly authorizes data correction.

## Task Workflow

### 1. Orient to the Task

Read these three inputs, always present in the task directory:

- `prompt.txt` — High-level business context and the service base URL.
- `input/payloads/<request_payload>.json` — Precise scope, business definitions, metric formulas, classification rules, rounding policy, and ranking/ordering directives.
- `input/payloads/answer_template.json` — The exact JSON Schema contract for the output file.

### 2. Explore the Data Model

Before writing any analytical query, call `GET /api/schema` and `GET /api/data-dictionary`. Use the schema to learn table and column names. Use the data dictionary to map business terms (e.g., "eligible production order," "effective settled refund," "carrier status") to the correct columns and join paths.

### 3. Build Queries Iteratively

Start with exploratory `SELECT` queries to verify row counts and value distributions. Build up to the final analytical queries using:
- `JOIN` across tables on foreign-key columns identified in the data dictionary.
- `WHERE` clauses for time windows, account tiers, regions, and other scope filters.
- `GROUP BY` for rollups by region, account, team, or reason code.
- `CASE` expressions for classification logic.
- Subqueries or CTEs (`WITH`) for multi-step calculations.

### 4. Produce the Answer

Write the result to `answer.json` in the task root. The output must:
- Conform exactly to `answer_template.json`: every `required` field present, no extra fields.
- Use the exact enum values defined in the template.
- Match all `pattern` constraints for ID fields.
- Apply rounding only to final reported values, using the precision specified in the template or request payload.
- Order array elements strictly according to the ordering rules in the request payload.

## Reusable Operating Rules

### Time and Boundaries

- All timestamps in the request payload are exact UTC.
- Respect boundary qualifiers: `INCLUSIVE` means `<=` for end and `>=` for start; `EXCLUSIVE` means `<` or `>`.
- When computing elapsed active time, subtract the earlier timestamp from the later one and convert to the requested unit (hours, minutes).
- A "cutoff" means the as-of point: include all records with timestamps at or before the cutoff (inclusive) unless otherwise specified.

### Rounding and Precision

- Count fields: integer, no rounding.
- Rate fields: typically 4 decimal places; only round the final reported rate.
- Monetary fields: 2 decimal places.
- Median fields: 2 decimal places when unit is hours.
- For rates that feed into status classification, use unrounded values for threshold comparison and rounded values only for output.

### Status and Risk Classification

- Evaluate classification rules in the order listed in the request payload.
- The first matching rule determines the status.
- A catch-all rule (labeled "otherwise," "neither … applies," or "All other outcomes") always comes last and must match if no prior rule does.
- Classification thresholds use the rate denominator specified in the request (e.g., eligible orders, eligible cases).

### Array Ordering and Ranking

- When the request specifies an ordering (e.g., "units_per_hour descending, then employee_id ascending"), apply it exactly — sort by the first key, then break ties with the second, and so on.
- ID arrays must be sorted ascending unless a different ordering is explicitly provided.
- Arrays of objects must appear in the exact order produced by the ranking rules.

### Currency Conversion

- When monetary values span multiple currencies, use the `fx_rates` table (or its equivalent as shown in the data dictionary).
- Match each row's currency and service date to the corresponding `usd_per_unit` rate.
- Convert each row to USD before aggregating.
- Report the final net amount in USD.

### Data Correction Workflow

When the task authorizes a data correction:

1. Query the raw/source values and the canonical values to identify the exact contradiction.
2. Determine the single field that needs correction and its old and new canonical values.
3. Construct a transaction with:
   - A guarded `UPDATE` on the business table (e.g., `carrier_scans`) targeting the specific row and setting the corrected canonical field.
   - An `INSERT` into `correction_audit` with all required audit columns: `audit_id`, `correction_key`, `entity_type`, `entity_id`, `source_row_id`, `field_name`, `old_value`, `new_value`, `reason_code`, `corrected_at`, `actor`.
   - Set `expected_total_changes` to exactly the number of rows the transaction will change.
4. Execute the transaction via `POST /api/sql/transaction`.
5. Run a post-correction `SELECT` query to confirm the canonical value updated correctly.
6. Report `APPLIED` only if exactly one business row and one audit row committed and the post-change query confirms the new value. Otherwise report `NOT_APPLIED` with the results actually observed.

### ID Format Patterns

Business IDs in the Atlas schema follow predictable formats. Do not hardcode task-specific values; these are examples of typical patterns:

- Order IDs: `ORD-` followed by 6 digits.
- Case IDs: `CASE-` followed by 6 digits.
- Account IDs: `ACC-` followed by 4 digits.
- Warehouse IDs: `WH-` followed by a region code and number (e.g., `WH-NORTH-01`).
- Batch IDs: `BATCH-` followed by segment identifiers.
- Shipment IDs: `SHP-` followed by digits.
- Audit IDs: `AUD-` followed by a date segment and sequence number.

### Common Business Concepts

The data dictionary will define these for each task, but the following concepts appear frequently:

- **Accounts** have a tier (e.g., GOLD, SILVER) and a population type (e.g., PRODUCTION, TEST).
- **Orders** belong to accounts, have a gross value in an order currency, and may be attributed to campaigns.
- **Shipments** are associated with orders, have a carrier, a promised delivery time, and scans that track status.
- **Carrier scans** have both raw and canonical status values; canonical is authoritative.
- **Refunds** are linked to orders, have a reason code, a settlement status, and may be reversed.
- **Tasks** belong to employees and teams, have a priority, a creation time, a due time, and a completion state with units.
- **Support cases** belong to accounts, have a priority (URGENT, HIGH, MEDIUM, LOW), an opened time, and state transitions (open, reopened, resolved).
- **Active time** for support cases is computed from state-transition timestamps, not wall-clock time.

## Quality Checklist

Before finalizing `answer.json`, verify:

- Every `required` field from the template is present.
- No fields outside the template are included.
- All enum values are from the allowed set.
- All ID strings match the template's `pattern` regex.
- Array lengths match `minItems`/`maxItems` constraints.
- Numeric values respect `minimum`, `maximum`, `multipleOf`, and precision requirements.
- Rounding is applied only at the final step and only as specified.
- Array ordering follows the request payload's ranking rules exactly.
