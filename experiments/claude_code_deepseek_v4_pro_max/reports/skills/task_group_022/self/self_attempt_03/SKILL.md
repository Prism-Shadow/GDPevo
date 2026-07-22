# Atlas Commerce Operations — Analytical Task Skill

## Purpose

Execute analytical and operational-review tasks against the Atlas Commerce Operations database. Each task follows the same pattern: read a business request and its output contract, explore the live database schema and field dictionary, query the data through the authenticated API, apply the stated business rules and policies, and produce a single JSON answer file that conforms exactly to the supplied template.

This skill covers both read-only analytical reports and controlled single-row data corrections with audit verification. It is reusable across any domain (fulfillment, refunds, carrier quality, warehouse productivity, support health) as long as the task follows the Atlas task-input convention.

---

## Input Convention

Every task provides three files inside its `input/` directory:

| File | Purpose |
|---|---|
| `prompt.txt` | Human-readable summary of the business question, the owning team, and the expected output file (`answer.json`). May reference a `<TASK_ENV_BASE_URL>` placeholder for the API. |
| `input/payloads/<domain>_request.json` | Machine-readable scope, business definitions, classification policies, status rules, and ranking/tiebreaking instructions. This is the **authoritative** source for all metric formulas. |
| `input/payloads/answer_template.json` | JSON Schema that the output must satisfy. Defines required fields, types, ranges, enums, array sizes, and ordering constraints. |

The working directory also contains `environment_access.md` with the resolved API base URL and credentials.

---

## API Reference

All tasks use the same authenticated REST API. Read `environment_access.md` first — it provides the concrete `base_url` and `credentials` block. The token is passed as an `Authorization: Bearer <token>` header on every request.

### Endpoints

| Method | Path | Purpose | Mutating |
|---|---|---|---|
| `GET` | `/api/schema` | Full database schema: table names, column names, types, nullability, primary/foreign keys. | No |
| `GET` | `/api/data-dictionary` | Human-readable descriptions of tables and columns, including enum-like value explanations. | No |
| `POST` | `/api/sql` | Submit a read-only `SELECT` query. Body: `{"sql": "<statement>"}`. Returns a JSON result set. | No |
| `POST` | `/api/sql/transaction` | Submit a controlled write statement (`UPDATE`). Body: `{"sql": "<statement>"}`. Returns affected-row and audit-row counts. Only use when the task explicitly requests a correction. | **Yes** |
| `GET` | `/api/correction-audit` | Retrieve audit records for prior corrections. May be filtered by query parameters. | No |

### Endpoint Selection Rules

- **Read-only tasks**: Use only `GET /api/schema`, `GET /api/data-dictionary`, and `POST /api/sql`. Never call the transaction endpoint.
- **Correction tasks** (the request payload contains an `approved_correction` block): After identifying the target row and field, call `POST /api/sql/transaction` with a single `UPDATE` statement scoped to exactly one business row. Then verify the change with `POST /api/sql` and retrieve the audit record from `GET /api/correction-audit`.

---

## Workflow

Follow these steps in order. Do not skip ahead.

### Phase 1 — Understand the Ask

1. **Read `prompt.txt`** to learn the business domain, the owning team, and the output filename.
2. **Read the request payload** (`input/payloads/<domain>_request.json`). Pay close attention to:
   - `scope` / `cohort` — which rows are eligible.
   - `business_definitions` / `reporting_definitions` — how metrics are computed.
   - `money_policy` — currency, FX basis, decimal precision (if monetary).
   - `sla_thresholds_hours` — priority-based time limits (if time-SLA).
   - `*_status_rules` / `*_risk_policy` — how the final classification is derived.
   - `*_ranking` — sort order and tiebreaking for any ranked output arrays.
   - `rounding` — when and to how many places to round.
3. **Read the answer template** (`input/payloads/answer_template.json`). Memorise:
   - Every `required` field.
   - Every type constraint, `enum`, `pattern`, `minimum`/`maximum`, `minItems`/`maxItems`.
   - Array ordering rules (often in `description` or `order` fields).
   - The `additionalProperties: false` constraint — the output must contain **only** the declared fields.

### Phase 2 — Explore the Data Model

4. **Call `GET /api/schema`.** Build a mental map of relevant tables, their columns, primary keys, and foreign-key relationships.
5. **Call `GET /api/data-dictionary`.** Cross-reference every column referenced in the business definitions. Note value domains, enum meanings, and units (e.g. currency codes, status labels, timezone conventions).

Never write a query before understanding the schema and dictionary. If a column meaning is ambiguous, re-read the dictionary description — the request's business definitions always govern interpretation.

### Phase 3 — Query and Compute

6. **Write SQL queries** submitted to `POST /api/sql`. Principles:
   - Filter to the exact cohort defined in the request (time windows, account tiers, regions, campaign IDs, batch IDs).
   - All timestamps in the database and in request boundaries are **UTC**. Treat window boundaries as inclusive/exclusive exactly as stated.
   - Perform calculations (aggregations, FX conversions, time arithmetic) in SQL when possible. Apply business rules from the request payload, not assumptions.
   - For multi-step logic, break into successive queries. Reference intermediate results in follow-up queries.
   - **Do not round intermediate values.** Round only the final reported figures to the precision stated in the request.
   - For array outputs, apply the stated sort order and tiebreaking in SQL (`ORDER BY`) so the result set is already correctly ordered.

7. **Apply business rules** to the query results:
   - Classification thresholds (e.g. "on-time rate ≥ 0.88 AND severe-exception rate < 0.05 → HEALTHY") are evaluated in priority order. The first matching rule wins.
   - For tiered risk policies, test conditions in the declared sequence and stop at the first match. A catch-all "otherwise" bucket applies when no earlier tier matches.
   - Ranking rules have a primary order and explicit tiebreaks — follow both exactly.
   - Monetary values: convert each row to the reporting currency using the FX rate for that row's `service_date` and currency, then aggregate. Report to the stated decimal places.
   - Median calculation: for an even number of values, average the two central values.

### Phase 4 — Corrections (Only When Requested)

Only enter this phase when the request payload contains an `approved_correction` block.

8. **Identify the contradiction.** Query to find the single row/field where raw and canonical values conflict per the request's scope.
9. **Apply the correction.** Send an `UPDATE` to `POST /api/sql/transaction` that:
   - Changes exactly one field in exactly one business row.
   - Sets the canonical column to the raw-source value.
   - Does not alter any source-identity column, raw-source column, or unrelated row.
   - Uses the `reason_code`, `actor`, `audit_id`, `correction_key`, and `corrected_at` from the `approved_correction` block.
10. **Verify.** Re-query the corrected row via `POST /api/sql` to confirm the canonical value matches the expected new value.
11. **Retrieve audit record** from `GET /api/correction-audit`, filtered to the correction's `audit_id` or `correction_key`.
12. **Set `correction_status`:**
    - `APPLIED` — exactly one business row and one audit row were committed, and the post-change query confirms the corrected value.
    - `NOT_APPLIED` — any other outcome.

### Phase 5 — Produce Output

13. **Assemble the JSON object** matching the answer template exactly:
    - Every `required` field must be present.
    - No extra fields beyond the schema.
    - Types must match: integers are integers (no trailing `.0`), numbers use the stated precision, strings match `pattern` constraints.
    - Arrays have the correct length and element order.
    - Enum fields use the exact string values (case-sensitive).
14. **Write `answer.json`** to the working directory. The file must contain only the JSON object — no markdown fences, no commentary, no trailing text.

---

## Operating Rules (Always Applied)

### Precision and Rounding
- Round only final reported values, never intermediate results.
- Use the exact decimal places stated in the request or answer template (`multipleOf`, `precision`, `decimal_places`).
- For rates bounded [0, 1], round to 4 decimal places unless the template specifies otherwise.
- Monetary amounts round to 2 decimal places unless the template specifies otherwise.

### Time and Timezones
- All timestamps in the database and all boundary values in requests are **UTC**.
- Window boundaries use the inclusiveness stated in the request (`inclusive`, `boundary`).
- Time arithmetic (elapsed hours, "more than 24 hours after") uses exact UTC second differences.

### Cohort and Eligibility
- Apply all scope filters from the request: time windows, account tiers, regions, campaign IDs, batch IDs, population types.
- "Eligible" always means "passes every scope filter in the request." If a row matches some but not all filters, it is ineligible.
- Time-window filters use the column named in the request definition (e.g. `created_at`, `service_date`, `opened_at`).

### Sorting and Tiebreaking
- When the request specifies a sort order, apply it in SQL. For multi-key sorts, respect the declared priority.
- Tiebreaking is not optional — if the primary key produces ties, the tiebreak key determines order.
- Default tiebreak (when none is stated) is the stable row identifier ascending.

### Error Handling and Edge Cases
- An empty result set for a count yields `0`, not `null` or omission.
- An empty result set for an array yields `[]`.
- A division by zero (e.g. rate with zero eligible items) yields `0` unless the request says otherwise.
- A missing value (e.g. no shipment promise for an incomplete order) does not satisfy a threshold condition that requires a comparison.
- When a classification rule references a rate that is undefined (0/0), treat the rate as `0` for threshold comparison.

### Output Discipline
- The output must be valid JSON conforming to the answer template's JSON Schema.
- `additionalProperties: false` is enforced — include exactly the declared fields.
- No markdown, no explanations, no log output surrounding the JSON in `answer.json`.
- Enum values are case-sensitive and must match exactly.

### API Discipline
- Never send a write statement to `POST /api/sql` — use `POST /api/sql/transaction` for any `UPDATE`.
- `POST /api/sql` accepts only `SELECT` statements.
- Always include the `Authorization: Bearer <token>` header from `environment_access.md`.
- The `Content-Type` for POST bodies is `application/json`.
