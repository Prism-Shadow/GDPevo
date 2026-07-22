# Atlas Commerce Operations — Analytical Task Runner

## Purpose

Execute analytical and controlled-correction tasks against the Atlas Commerce Operations workplace database. This skill covers discovery (schema and data dictionary), read-only analysis via SQL, controlled single-row corrections with audit-verification, and production of a strict JSON output contract.

## When to Use

Invoke this skill when the task:
- References the Atlas Commerce Operations workplace, the `<TASK_ENV_BASE_URL>` placeholder, or an `environment_access.md` file.
- Requires analytical SQL against production business records (fulfillment, refunds, carrier scans, warehouse productivity, support cases, or similar operational domains).
- Supplies a business-request payload with scope, definitions, rules, and policies alongside an `answer_template.json` output schema.
- Asks for a JSON result written to `answer.json` with no narrative outside the JSON document.

## Pre-requisites

Every task directory must contain:
- `input/prompt.txt` — narrative instructions.
- `input/payloads/` — at least one request JSON (business scope, definitions, rules, policies) and one `answer_template.json` (the JSON Schema or structural contract for the output).
- `environment_access.md` at the workspace root — the base URL, credentials, and allowed endpoint list.

If any unexpected material is present in the working directory, stop and write `contamination_report.txt` before proceeding.

## Workflow

### Phase 1 — Environment Setup

1. Read `environment_access.md` from the workspace root.
2. Extract `base_url`, the `Authorization` header value, and the `allowed_endpoints` list.
3. Resolve `<TASK_ENV_BASE_URL>` (or any equivalent placeholder in the prompt) to the `base_url` from `environment_access.md`. This container-visible URL overrides any localhost, 127.0.0.1, or environment-variable reference in the official task inputs.

### Phase 2 — Input Analysis

1. Read `input/prompt.txt` to understand the business ask and identify any special instructions (e.g., read-only vs. correction workflow, domain-specific notes).
2. Read every JSON file in `input/payloads/`. There will always be at least:
   - A **request payload** containing the business scope, definitions, classification rules, ranking policies, rounding rules, and any correction instructions.
   - An **answer template** defining the exact output schema (`type`, `required`, `properties`, `additionalProperties`, `enum` constraints, `pattern` constraints, precision/unit annotations).
3. Map every business term in the request payload to a concrete computation path. Pay attention to:
   - **Cohort/population filters** — which rows are eligible.
   - **Time windows** — whether boundaries are inclusive or exclusive, and whether timestamps are UTC.
   - **Cutoff semantics** — a state cutoff ("as of") vs. a creation window, and how incomplete/in-progress records are treated at the cutoff.
   - **Denominators and numerators** for every rate.
   - **Rounding rules** — whether rounding is applied only to final reported rates, and to how many decimal places.
   - **Tie-breaking rules** for any ranked output.

### Phase 3 — Schema Discovery

1. Call `GET {base_url}/api/schema` with the `Authorization` header. This returns the database schema: table names, column names, types, and relationships.
2. Call `GET {base_url}/api/data-dictionary` with the `Authorization` header. This returns semantic descriptions of tables and columns, including enum-like value meanings, business semantics for status fields, and relationship context not captured in raw schema.
3. Use the schema and data dictionary together to map every business concept from the request payload to concrete tables, columns, and join paths. Never guess a column meaning — verify it against the data dictionary.

### Phase 4 — Read-Only Analysis

1. Construct SQL queries against the discovered schema. All queries use `POST {base_url}/api/sql` with the `Authorization` header.
2. The request body is a JSON object with a `sql` key containing the SQL statement.
3. Follow these query construction rules:
   - **Filter early**: Apply cohort, time-window, and region filters in the WHERE clause before any aggregation.
   - **Respect cutoff semantics**: When the request defines a state cutoff, filter to rows that existed at or before that cutoff. When it defines a creation window, filter by creation timestamp within the window.
   - **Handle NULLs explicitly**: When a business definition says "no shipment promise" or "no response," test for NULL and apply the documented treatment (exclude, count as incomplete, etc.).
   - **Use the data dictionary for status values**: Carriers-status values, order states, case priorities, task types — these are domain-specific strings documented in the data dictionary. Never hardcode a status string without confirming it in the dictionary.
   - **FX conversions**: When the business policy requires currency conversion, join against the `fx_rates` table using the service date and row currency. Apply the rate, then round at the final display step only.
4. Run every query needed to collect all raw numbers. Prefer fewer, well-structured queries over many narrow ones, but do not force unrelated computations into one query if it compromises correctness.

### Phase 5 — Controlled Correction (only when the request mandates it)

This phase applies only when the request payload includes an `approved_correction` block or explicitly instructs a data correction. Skip it for read-only analytical tasks.

1. **Identify the contradiction**: Query the target cohort to find the exact row where the canonical field value contradicts the raw/source value. The request will specify the contradiction type (e.g., carrier-status mismatch).
2. **Build the correction transaction**: Use `POST {base_url}/api/sql/transaction` with the `Authorization` header. The body is a JSON object containing:
   - The UPDATE statement targeting exactly one row by its stable identifier.
   - The correction metadata from the request: `correction_key`, `reason_code`, `actor`, `audit_id`, `corrected_at`.
3. **Verify the mutation result**: The transaction response reports `affected_business_rows` and `audit_rows`. The correction is only valid when exactly one business row and one audit row were committed.
4. **Retrieve the audit record**: Call `GET {base_url}/api/correction-audit` with the `Authorization` header. Filter or identify the audit row matching the `audit_id` from the request. Validate that every field (`entity_type`, `entity_id`, `source_row_id`, `field_name`, `old_value`, `new_value`, `reason_code`, `corrected_at`, `actor`) matches the expected values.
5. **Post-correction verification**: Re-run the pre-correction analysis query. Confirm the corrected canonical value now appears in place of the old value. Compute the backlog delta and post-correction delivered count.
6. **Determine status**: Report `APPLIED` only when exactly one business row and one audit row committed AND the post-change query confirms the corrected canonical value. Otherwise report `NOT_APPLIED` with the results actually observed.

### Phase 6 — Compute Results

Apply the business rules from the request payload to the query results:

1. **Rates**: Compute using the exact numerator and denominator defined in the request. Round only the final reported rate to the specified number of decimal places.
2. **Tiered classification**: Evaluate cascading status/risk rules in the order given. The first matching condition wins. Ensure every possible outcome is covered (the last tier is typically a catch-all "otherwise").
3. **Ranking**: Sort by the primary dimension, then apply tie-breakers in the order specified. Pay attention to ascending vs. descending direction for each level.
4. **Median**: For an even number of values, average the two central values. Round the result to the specified precision.
5. **Dollar amounts**: Apply FX conversion using the service-date rate. Sum or net (refunds minus reversals) as defined. Round only the final displayed value to the specified number of decimal places.

### Phase 7 — Write Output

1. Build a JSON object that conforms exactly to `input/payloads/answer_template.json`.
2. Validate against every constraint in the template:
   - `required` fields — all must be present.
   - `additionalProperties: false` — no extra fields.
   - `type` — integers must be integers, not `1.0`.
   - `enum` — string fields must use exact enum values.
   - `pattern` — ID fields must match the documented format.
   - `minimum`/`maximum` — numeric fields must be within range.
   - `multipleOf` — rate fields must respect the precision constraint (e.g., `0.0001` for 4 decimal places).
   - `minItems`/`maxItems`/`uniqueItems` — array fields must match size and uniqueness constraints.
3. Write the JSON to `answer.json` in the working directory.
4. The file must contain only the JSON object — no markdown fences, no commentary, no trailing text.

## Endpoint Reference

All endpoints are accessed through the `base_url` from `environment_access.md` with the `Authorization` header.

| Method | Path | Purpose | Body |
|--------|------|---------|------|
| GET | `/api/schema` | Table and column structure | None |
| GET | `/api/data-dictionary` | Business semantics for tables and columns | None |
| POST | `/api/sql` | Read-only analytical queries | `{"sql": "<statement>"}` |
| POST | `/api/sql/transaction` | Controlled single-row correction | `{"sql": "<statement>", "correction_key": "...", "reason_code": "...", "actor": "...", "audit_id": "...", "corrected_at": "..."}` |
| GET | `/api/correction-audit` | Retrieve audit trail records | None |

## Business Rule Patterns

These patterns recur across analytical tasks. When you encounter them in a request payload, apply the corresponding computation:

### Tiered Classification
```
if condition_A: STATUS_X
elif condition_B: STATUS_Y
else: STATUS_Z
```
Evaluate conditions in order. The first matching tier wins. The final tier is the catch-all.

### Cutoff-Based State Evaluation
- **Creation window**: `created_at >= start AND created_at <= end` (inclusive) or `created_at >= start AND created_at < end` (exclusive end). Check the request's `boundary` field.
- **State cutoff**: Evaluate each record's state as it existed at the cutoff timestamp. Records created after the cutoff are excluded. Incomplete/in-progress records at the cutoff are counted based on their state at that moment.
- **Active-time clock**: When the request uses an active-time clock (e.g., support active time), elapsed time is measured from the relevant start event to either the resolution event or the cutoff (for unresolved records).

### Rate Calculation
- Numerator and denominator are defined in the request. Apply filters first, then count.
- Round only the final reported rate. Intermediate values used for ranking or comparison use unrounded values.
- Incomplete/ineligible records remain in the denominator when the definition says they do.

### Ranking with Tie-Breaking
- Primary sort: the main metric, in the direction specified.
- Secondary sort(s): apply in order. Each subsequent tie-break only matters when all prior dimensions are equal.
- For "worst N" ascending on the metric, the lowest values come first.
- For "top N" descending on the metric, the highest values come first.

### FX Conversion
- Join to `fx_rates` on the service date and row currency.
- Multiply the row amount by `usd_per_unit` to get USD.
- Apply rounding only to the final displayed total, not to intermediate per-row conversions.

### Correction Workflow
- Identify exactly one row with a canonical contradiction.
- Update exactly one field to its correct canonical value.
- Verify: exactly one business row affected, exactly one audit row created.
- Post-change query confirms the new value.
- Report `APPLIED` or `NOT_APPLIED` based on the verification result.

## Common Pitfalls

- **Off-by-one on boundaries**: When the request says "inclusive," use `>=` and `<=`. When it says "at or before," include the exact timestamp.
- **Integer vs. float**: Count fields must be integers. `1.0` is not valid for an integer field even if numerically equal.
- **Rounding before ranking**: Rank on unrounded values, then round for display. The request usually says "round only final reported rates."
- **NULL treatment**: An unset promise date, missing response timestamp, or absent shipment is not the same as a zero or a past date. Apply the request's explicit NULL policy — don't invent one.
- **Currency in comparisons**: When comparing refund value to order gross, convert both to the same currency using the same service-date rate before comparing.
- **Denominator selection**: The denominator for a rate may be "all eligible orders" not "all complete orders." Read the request definition carefully.
- **Reversal handling**: Linked reversals reduce the effective refund value. Net = sum of refunds minus sum of linked reversals.
- **Duplicate detection**: Leakage or exception criteria that check for "at least two" of something require grouping and a HAVING clause, not just a WHERE filter.
