# Atlas Commerce Operations — Analytical & Correction Skill

## When to use

Invoke this skill whenever a task requires querying or correcting data in the Atlas Commerce Operations database through the authenticated workplace API. The task will involve reading structured business-scope payloads, running SQL against the service, applying domain policies (classification, ranking, aggregation), and returning a strictly conformant JSON answer.

## Step 0 — Locate the task inputs

Every task instance lives in a directory with this shape:

```
<input_dir>/
  prompt.txt                  # natural-language summary of the business request
  payloads/
    <request_facts>.json      # structured scope, policies, thresholds, business definitions
    answer_template.json      # exact JSON Schema for the output
```

Always read all three before writing any SQL. The prompt provides context; the request-facts JSON is the **authoritative source** for every number, threshold, definition, and rule. The answer template is the **non-negotiable output contract**.

## Step 1 — Read environment access

The file `environment_access.md` (at the task root, or at the workspace root) provides:

- `base_url` — the root URL of the workplace API
- `credentials` — the `Authorization` header value (typically `Bearer <token>`)
- `allowed_endpoints` — exact API paths available
- Request shape and examples for each endpoint

**This file is the single source of truth for connectivity.** Do not use localhost, `127.0.0.1`, or any URL embedded in the prompt. Substitute the base URL from this file wherever the prompt writes `<TASK_ENV_BASE_URL>`.

## Step 2 — Discover the data model

Before writing any analysis query, call:

```
GET {base_url}/api/schema
GET {base_url}/api/data-dictionary
```

Both require the `Authorization` header from Step 1.

- `/api/schema` returns table and column names, types, nullability, and primary/foreign key constraints.
- `/api/data-dictionary` returns human-readable descriptions of each column and table, including enumeration semantics (e.g., what each status code means) and unit annotations.

Use these responses to build a mental map: which tables hold orders, shipments, scans, refunds, reversals, tasks, cases, accounts, FX rates — and how they join. Correlate column names with the business definitions in the request-facts JSON.

## Step 3 — Parse the request-facts JSON

The request-facts payload (the non-template JSON in `payloads/`) contains structured, machine-readable business policy. It is **not** a narrative — every field is a precise instruction. Common structures include:

### Scope / cohort
Defines which rows are eligible. Look for:
- `cutoff_at` — an ISO-8601 UTC instant; include rows at-or-before this time.
- `window` / `*_window` — `start_at` / `end_at` with a `boundary` field (`"inclusive"` or `"INCLUSIVE"`).
- `account_tier`, `account_population`, `segment`, `regions[]` — filters on account dimension tables.
- `cohort` / `population` — a prose definition that maps to SQL `WHERE` clauses; cross-reference with the data dictionary.

### Business definitions
Key/value pairs where the value is a prose formula. Translate each into a `CASE` expression or a CTE. Examples:
- *"A complete order has at least one physical shipment and every shipment is DELIVERED by the cutoff"* — aggregate shipment status per order, apply the cutoff, compute completeness.
- *"An on-time complete order has every shipment delivered no later than its promised_delivery_at"* — compare each shipment's delivery timestamp to its promise.
- *"A severe exception is an incomplete order more than 24 hours past its latest promise, or a complete order with any shipment delivered more than 24 hours late"* — two disjunctive conditions.

### Thresholds & SLAs
Structured by priority/severity level with numeric hour/minute values. Use these in `CASE` expressions for breach detection.

### Status / risk classification rules
A list of tiered rules, each with a `status` (or `risk`) label and a `condition`. **Evaluate rules in the order given.** The first rule whose condition is satisfied wins. The final rule is typically an `"otherwise"` or `"All other outcomes"` catch-all.

Conditions combine numeric thresholds with comparison operators described in prose (e.g., *"below 2%"*, *"at least 0.88"*). Translate exactly: *"below X%"* → `< X/100`, *"at least Y"* → `>= Y`.

### Ranking / ordering
Specifies a result count (`limit`, `result_size`), primary order, and tie-break order. Translate to `ORDER BY primary_col <ASC|DESC>, tie_col <ASC|DESC> LIMIT n`.

### Money / currency policy
When present, specifies:
- `reporting_currency` — the output currency (convert everything to it).
- `fx_basis` — use an FX rates table, joining on service date and row currency to get the `usd_per_unit` rate.
- `net_refund_display_decimals` / precision — round only the final displayed value.

### Rounding
Always specified as *"round only final reported rates to N decimal places"*. Apply `ROUND(..., N)` (or equivalent) **only** to the final scalar going into the output JSON — never round intermediate values used in other computations.

## Step 4 — Query the data (read-only analysis)

Use:

```
POST {base_url}/api/sql
Content-Type: application/json
Authorization: Bearer <token>

{"sql": "<SQL string>", "params": [<scalar>, ...]}
```

### SQL construction principles

1. **Use CTEs (`WITH`) for multi-step logic.** One CTE for eligibility filtering, another for aggregation, another for ranking, another for classification. This makes each step auditable.

2. **Parameterize values from the request-facts JSON.** Pass cutoff timestamps, region lists, account tiers, and priority codes as `params` rather than interpolating them into the SQL string. Use `?` placeholders or `$1`, `$2` syntax as supported by the endpoint.

3. **Window functions for ranking.** Use `ROW_NUMBER()`, `RANK()`, or `DENSE_RANK()` partitioned and ordered as the request-facts specify.

4. **Aggregate carefully.** When a definition says *"every shipment"* or *"at least one"*, use `bool_and()`, `bool_or()`, `COUNT(...) FILTER (...)`, or equivalent conditional aggregation.

5. **Join FX rates precisely.** Match on `service_date` and `currency` columns. Convert row-currency amounts to the reporting currency before summing: `amount * fx.usd_per_unit`.

6. **Handle NULLs defensively.** A missing `promised_delivery_at` may mean a condition cannot be satisfied — the business definition usually handles this (e.g., *"an order with no shipment promise does not satisfy the condition"*).

7. **Median computation.** For an even number of values, average the two central values. Use `PERCENTILE_CONT(0.5)` or a row-number-based approach with `ORDER BY value` and positional logic.

### Iterate
Run the query, inspect results, refine. If the result set looks wrong, query individual rows to debug — check boundary cases at the cutoff, verify join cardinalities, spot-check aggregations.

## Step 5 — Apply corrections (only when the task requires mutation)

Some tasks ask for a **single controlled data correction**. This is distinct from analysis:

1. **Identify the contradiction** — query the raw/source data, find where two representations disagree. The request-facts will state *"exactly one raw/canonical contradiction"*.

2. **Use the transaction endpoint:**

```
POST {base_url}/api/sql/transaction
Content-Type: application/json
Authorization: Bearer <token>

{
  "statements": [
    {"sql": "<UPDATE statement>", "params": [...]}
  ],
  "expected_total_changes": <integer>
}
```

- `expected_total_changes` must be provided and must be accurate. A mismatch will cause the transaction to fail or roll back.
- The correction scope is always *"MINIMAL_CANONICAL_FIELD_ONLY"* — update only the one field that needs canonical correction; leave raw/source values, identity columns, and unrelated rows unchanged.
- The request-facts provides the `reason_code`, `actor`, `audit_id`, `correction_key`, and `corrected_at` to include.

3. **Verify post-correction** — re-run the pre-correction query; confirm the canonical value is now correct and no other rows were affected.

4. **Retrieve the audit record:**

```
GET {base_url}/api/correction-audit
Authorization: Bearer <token>
```

Filter by `audit_id` to retrieve the committed audit row and confirm its fields match the correction.

5. **Report status:**
- `"APPLIED"` — exactly one business row and one audit row committed, and post-change verification confirms the correction.
- `"NOT_APPLIED"` — any other outcome.

## Step 6 — Write the conformant output

Write to `answer.json` in the task working directory (the directory containing `prompt.txt`).

### Enforce the answer template exactly

The `answer_template.json` is a JSON Schema document. Comply with every constraint:

| Constraint | Enforcement |
|---|---|
| `type: "object"` | Output must be `{}`, not `[]` or a scalar |
| `additionalProperties: false` | No fields beyond those in `properties` |
| `required: [...]` | Every listed field must be present, even if its value is `0`, `[]`, or `null` |
| `type: "integer"` | Must be a whole number — not `0.0` or a float |
| `type: "number"` | May be a float; respect `multipleOf` and `minimum`/`maximum` |
| `enum: [...]` | Value must be exactly one of the listed strings — case-sensitive |
| `pattern: "..."` | String must match the regex (e.g., `^ORD-[0-9]{6}$`) |
| `minItems` / `maxItems` | Arrays must have the specified cardinality |
| `uniqueItems: true` | No duplicates in arrays |
| `multipleOf` | Number must be an exact multiple (e.g., `0.0001` enforces 4 decimal places) |
| `description` / `x-*` | Human annotations only — not runtime constraints |

### Array ordering

When the template or request-facts specifies an array ordering, sort accordingly before writing. When an array has `uniqueItems: true`, deduplicate.

### No commentary

The output file must contain **only** the JSON object — no surrounding text, no markdown fences, no explanation.

## Reference — API summary

| Method | Path | Purpose | Body |
|---|---|---|---|
| GET | `/api/schema` | Table/column/constraint metadata | — |
| GET | `/api/data-dictionary` | Column descriptions, enum semantics | — |
| POST | `/api/sql` | Read-only analysis queries | `{"sql":"...","params":[...]}` |
| POST | `/api/sql/transaction` | Controlled data corrections | `{"statements":[...],"expected_total_changes":N}` |
| GET | `/api/correction-audit` | Audit trail of past corrections | — |

All require `Authorization: Bearer <token>` from `environment_access.md`. `POST` endpoints additionally require `Content-Type: application/json`.

## Reference — common business-logic patterns

### Cascading classification (first-match-wins)

The request-facts gives an ordered list of `{status, condition}` entries. Evaluate in order. The first whose condition evaluates to true wins. The last entry is the catch-all.

```
WITH classified AS (
  SELECT *,
    CASE
      WHEN <condition-1> THEN '<status-1>'
      WHEN <condition-2> THEN '<status-2>'
      ELSE '<catch-all-status>'
    END AS classification
)
```

**Important nuance**: some policies say *"condition A and condition B must both be true"* for tier 1, then *"the tier-1 conditions are not both met, AND condition C and condition D"* for tier 2. Translate the negation explicitly: when tier 1 conditions are `A AND B`, tier 2 is `NOT (A AND B) AND C AND D`. The catch-all is `NOT (tier1) AND NOT (tier2)`.

### Regional / dimensional rollups

When the request asks for per-region metrics, group by the dimension, compute the metric per group, then rank or filter the groups:

1. Join to the dimension table (warehouse, account, team) to get the grouping attribute.
2. Compute the metric per group.
3. Order by the metric (and tie-break) as specified.
4. Take the top/bottom N groups.

### Multi-key ranking with tie-breaks

Primary key descending/ascending, tie-break key ascending. In SQL: `ORDER BY primary_metric <dir>, tie_break_col ASC`. When the tie-break itself has a direction specified, use that direction.

### Boolean aggregation for *"every"* / *"at least one"*

- *"every shipment must be DELIVERED"* → `bool_and(status = 'DELIVERED')` or `COUNT(*) FILTER (WHERE status <> 'DELIVERED') = 0`
- *"at least one physical shipment"* → `COUNT(*) > 0`
- *"at least two with the same reason"* → `COUNT(DISTINCT refund_id) >= 2` grouped by reason

### Currency conversion

Join the FX rates table on `service_date` and `currency`, multiply the source amount by the rate, then aggregate in the reporting currency.

### Median

When the count of resolved values is odd: return the middle value. When even: average the two central values. Round the result to the specified precision.

## Reference — error recovery

- **Schema mismatch**: re-read `/api/schema` and `/api/data-dictionary`; a column name or join key may differ from what the request-facts imply.
- **Unexpected row counts**: query the boundary rows at the cutoff to confirm inclusive/exclusive semantics. Check for NULLs that silently drop from comparisons.
- **Transaction rejected**: verify `expected_total_changes` — it must equal the number of rows the `UPDATE` actually modifies (not matches via `WHERE`).
- **Output validation failure**: re-read `answer_template.json`; check `additionalProperties`, `required`, `type`, `enum`, `pattern`, `minItems`, `maxItems`, `multipleOf`.
