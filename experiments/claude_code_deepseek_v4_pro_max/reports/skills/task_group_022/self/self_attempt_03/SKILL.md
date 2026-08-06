# Atlas Operations Skill

Reusable skill for analyzing and correcting business data through the Atlas Commerce Operations authenticated workplace API. Handles scorecards, reconciliations, quality corrections, productivity reviews, and support-health assessments.

## Preconditions

Before executing any task, confirm these files are present in the working directory:
- `input/prompt.txt` — the task brief
- `input/payloads/<request_file>.json` — business scope, definitions, policies, and rules
- `input/payloads/answer_template.json` — output contract (schema, required fields, constraints)
- `environment_access.md` — base URL, credentials, and allowed endpoints (overrides any `<TASK_ENV_BASE_URL>` placeholder in the prompt)

If any file is missing or the working directory contains material not matching this structure, stop and report the discrepancy before proceeding.

## API Reference

Read the base URL and credentials from `environment_access.md`. All requests use the header:

```
Authorization: Bearer <token from environment_access.md>
```

| Method | Endpoint | Purpose | Body |
|--------|----------|---------|------|
| GET | `/api/schema` | Database table and column catalog | — |
| GET | `/api/data-dictionary` | Field-level business descriptions | — |
| POST | `/api/sql` | Read-only analytical queries (SELECT / WITH) | `{"sql": "<query>", "params": [...]}` |
| POST | `/api/sql/transaction` | Controlled data corrections | `{"statements": [...], "expected_total_changes": <int>}` |
| GET | `/api/correction-audit` | Audit trail for past corrections | — |

- `/api/sql` is read-only; use it for all analytical work.
- `/api/sql/transaction` is the ONLY endpoint for mutations. It requires `expected_total_changes` as an exact integer; the call fails if the actual row-change count does not match.
- `/api/correction-audit` exposes previously applied corrections for verification.

## Workflow

### Phase 1 — Orient

1. Read `input/prompt.txt` to understand the business task, the role requesting it, and any special instructions (e.g., read-only vs. correction).
2. Read the request payload (`input/payloads/<request_file>.json`) for the full scope:
   - **Cohort / population**: which rows are in scope (account tier, region, campaign, date window, warehouse).
   - **Cutoffs**: the `as_of_cutoff` or `cutoff_at` timestamp; treat all date-window boundaries as inclusive on both ends unless stated otherwise, and treat all timestamps as exact UTC.
   - **Business definitions**: how key terms (complete, on-time, severe, breach, rework, leakage candidate) are computed from raw fields.
   - **Rollup / aggregation rules**: how rates are formed, which denominator to use, how to group and rank.
   - **Rounding policy**: apply rounding ONLY to final reported values, never to intermediate figures.
   - **Status / risk classification rules**: ordered or tiered thresholds that determine the final label.
3. Read `input/payloads/answer_template.json` to internalize the exact output contract — required fields, types, ranges, enum values, array sizes, ordering constraints, and regex patterns. The final JSON MUST match this schema exactly with no extra fields and no narrative.

### Phase 2 — Discover schema

1. `GET /api/schema` — learn table names, column names, and types.
2. `GET /api/data-dictionary` — learn the business meaning of each field, especially status enums, currency columns, timestamp columns, and foreign-key relationships.
3. Map every business concept from the request (e.g., "eligible order", "complete order", "effective settled logical refund", "productive minutes") to concrete SQL expressions using the discovered schema.

### Phase 3 — Gather data

1. Compose read-only SQL (SELECT / WITH / CTEs) against the tables from Phase 2.
2. Submit each query via `POST /api/sql`. Always include the `params` array even when empty.
3. Apply scope filters (date windows, regions, tiers, campaigns) inside the SQL WHERE clause so only relevant rows are returned.
4. Treat all timestamp comparisons as inclusive of the boundary value (`<= cutoff` or `>= start AND <= end`) unless the request explicitly states otherwise.
5. Verify result cardinalities match expectations before proceeding — if a count seems off, re-check the cohort definition and query filters.

### Phase 4 — Compute

1. Apply the business definitions from the request JSON to classify each row (e.g., is this order complete? on-time? a severe exception? a leakage candidate?).
2. Compute aggregates:
   - **Counts**: always `DISTINCT` on stable business identifiers (order_id, case_id, task_id, shipment_id) unless the metric explicitly calls for non-distinct counting.
   - **Rates**: divide the qualifying subset by the eligible population. Incomplete or unresolved items remain in the denominator.
   - **Rankings**: apply the specified sort order (e.g., rate ascending → label ascending; count descending → count descending → ID ascending). For "worst" or "lowest" metrics, the sort direction is in the metric name.
   - **Medians**: for an odd count pick the central value; for an even count average the two central values.
3. Apply roundings ONLY at the final step — compute with full precision, then round the reported number to the specified decimal places.
4. Evaluate tiered status/risk rules:
   - Check conditions in the order specified by the request.
   - If rules are ordered (first-match-wins), stop at the first matching tier.
   - If rules use an `otherwise` / fallback, the last tier catches everything not matched above.

### Phase 5 — Mutate (correction tasks only)

Only execute this phase when the prompt explicitly authorizes a data correction and the request payload includes an `approved_correction` block.

1. Identify the single contradiction from the raw data (e.g., raw carrier status vs. canonical status for the same scan).
2. Determine the exact target: `scan_row_id`, `shipment_id`, `field_name`, `old_value` (current canonical), `new_value` (correct canonical derived from raw evidence).
3. Construct a single UPDATE statement that changes only the one canonical field on the one row.
4. Submit via `POST /api/sql/transaction` with `expected_total_changes` set to 1 (for a minimal single-row correction).
5. Verify the result:
   - Confirm `affected_business_rows` is exactly 1 and `audit_rows` is exactly 1.
   - Query the corrected row to confirm the canonical value now matches `new_value`.
   - Query `/api/correction-audit` and locate the audit record matching the correction.
6. Report `APPLIED` only when the success conditions in the request are fully satisfied; otherwise report `NOT_APPLIED` with the actual observed results.

**Correction principles:**
- Change only the minimal canonical field on the minimal set of rows.
- Never alter raw source values, source identity columns, or unrelated business rows.
- Use only the `approved_correction` values for `reason_code`, `actor`, `audit_id`, `correction_key`, and `corrected_at`.

### Phase 6 — Write output

1. Construct exactly one JSON object matching every constraint in the answer template.
2. Validate:
   - All `required` fields are present.
   - No extra fields beyond the schema (unless `additionalProperties` is `true`, which it never is in these templates).
   - Types, ranges, `minimum`, `maximum`, `enum`, `pattern`, `multipleOf`, `minItems`, `maxItems`, and `uniqueItems` are all satisfied.
   - Array sort orders match the specified ordering rules.
3. Write the JSON to `answer.json` in the working directory (not inside `input/` or `skill/`).
4. Do NOT include any commentary, explanation, or markdown outside the JSON document.

## Cross-Cutting Rules

These apply to every task regardless of domain:

- **Read-only by default.** Do not mutate data unless the prompt and request payload both explicitly authorize a correction.
- **Stable identifiers.** Use business identifiers (order_id, case_id, task_id, shipment_id, scan_row_id, account_id, employee_id, team_id) as the primary keys for counting, grouping, and ranking. The underlying database row IDs are opaque.
- **UTC boundaries.** All timestamps in requests are UTC. Treat date-window boundaries as inclusive on both ends.
- **Precision discipline.** Compute with full precision; round only at the final reported value using the rounding rule from the request (4 decimal places for rates, 2 for monetary amounts and hours).
- **Distinct counts.** Count distinct business entities unless the metric definition says otherwise. "Count of orders" means `COUNT(DISTINCT order_id)`.
- **Null handling.** A null/missing value does not satisfy a threshold condition (e.g., an order with no promised delivery date cannot breach a lateness threshold). Exclude nulls from median calculations.
- **Template conformity.** The answer template is the authoritative contract. If a constraint in the template appears to conflict with the request narrative, the template wins on structure (types, required fields, enum values) and the request JSON wins on business semantics (definitions, policies, thresholds).
- **No invented data.** Every value in the output must be derived from workplace API responses. Never fabricate or guess.
