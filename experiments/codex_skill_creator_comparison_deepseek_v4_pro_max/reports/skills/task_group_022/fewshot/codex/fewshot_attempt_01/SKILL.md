---
name: atlas-ops-queries
description: Query and correct the Atlas Commerce Operations database via its authenticated HTTP API. Use when the task involves the Atlas workplace service (typically at a TASK_ENV_BASE_URL), needs SQL analysis against the Atlas schema (orders, shipments, carrier_scans, refund_attempts, warehouse_tasks, support_cases, accounts, etc.), requires a controlled canonical-data correction with an audit record, or calls for a JSON output conforming to a supplied answer template. Do not use for general SQL tasks outside the Atlas domain.
---

# Atlas Operations Queries

## Quick Reference

- **Base URL**: read from the task prompt (usually `<TASK_ENV_BASE_URL>`)
- **Auth header**: `Authorization: Bearer atlas-ops-token-022`
- **Allowed endpoints**: `GET /api/schema`, `GET /api/data-dictionary`, `POST /api/sql`, `POST /api/sql/transaction`, `GET /api/correction-audit`

## Workflow

### 1. Gather Context

Every task provides a prompt and one or more payload files. Read them all:
- `input/prompt.txt` — narrative instructions, boundaries, and output contract
- `input/payloads/<request>.json` — scope, business definitions, metric formulas, status rules
- `input/payloads/answer_template.json` — exact JSON schema for the output

The request JSON defines: cohort eligibility, cutoff timestamps, business definitions
(e.g. what "complete" means), rollup rules, ranking/tiebreak rules, status classification
rules, and rounding policies. Every SQL query must faithfully implement these definitions.

### 2. Load Schema and Data Dictionary

```bash
curl -s -H "Authorization: Bearer atlas-ops-token-022" <BASE>/api/schema
curl -s -H "Authorization: Bearer atlas-ops-token-022" <BASE>/api/data-dictionary
```

The schema returns DDL + indexes. The data dictionary returns column descriptions.
Cross-reference the full schema in [references/schema.md](references/schema.md).

### 3. Write and Run SQL Queries

Submit queries to `POST /api/sql` with body `{"sql": "<query>"}`. Build queries
incrementally — start with cohort scoping, then add metric computations.

Consult [references/query_patterns.md](references/query_patterns.md) for deduplication,
effective-state derivation, FX conversion, ranking, median computation, and other
common patterns. Every query touching an imported table must apply deduplication.

### 4. Controlled Corrections (when the task requires a data change)

Use `POST /api/sql/transaction` for atomic write + audit:

```bash
curl -s -X POST -H "Authorization: Bearer atlas-ops-token-022" \
  -H "Content-Type: application/json" \
  -d '{"statements": ["<update>", "<insert audit>"]}' \
  <BASE>/api/sql/transaction
```

The transaction commits both statements atomically or rolls back entirely. After
committing, verify with a read-only query and confirm the audit record via
`GET /api/correction-audit?correction_key=<key>`.

Correction rules:
- Change only canonical fields (`canonical_status`, `canonical_event_at`, `canonical_quantity_each`), never raw fields.
- Set `corrected_at` and `correction_reason` on the updated row.
- Insert exactly one row into `correction_audit` with the caller-provided `audit_id` and `correction_key`.
- Use the exact `reason_code`, `corrected_at`, and `actor` values from the request.

### 5. Compute Results and Write Answer

Apply rounding only at the final step, not during intermediate computations.
Follow ranking/tiebreak rules exactly as stated in the request JSON.
Classify status by evaluating rules in the order given (first match wins if
exclusive; otherwise evaluate all).

Write the result as a single JSON object to `answer.json` that conforms exactly
to the answer template schema. Include no commentary outside the JSON.

## Key Gotchas

- **Deduplication is mandatory** on every imported table: `carrier_scans`, `case_events`,
  `inventory_movements`, `order_events`, `payment_events`, `refund_attempts`,
  `warehouse_task_events`. Use `ROW_NUMBER() OVER (PARTITION BY source_system,
  external_event_id ORDER BY ingested_at DESC)` and keep `rn = 1`.
- **`current_status` columns are stale snapshots.** Derive final state from the
  effective event table rows instead when correctness at a cutoff matters.
- **Carrier scan deduplication and effective row**: For a given shipment, the
  effective scan is the deduplicated row with the latest `canonical_event_at`
  (tiebreak on `scan_row_id`).
- **Inclusive timestamps**: All window boundaries in task requests are inclusive.
  Use `>=` and `<=`, not `>` or `<`.
- **Monetary math**: `amount_minor` / `gross_amount_minor` are in the smallest
  currency unit (cents for USD). Divide by 100 for display dollars. FX rates are
  `usd_per_unit` — multiply by the rate, not divide.
- **Rounding**: Round only final reported values. Carry full precision through
  intermediate computations. Use `ROUND(value, 4)` for rates and `ROUND(value, 2)`
  for dollar amounts.
- **Integer booleans**: `is_internal`, `is_test`, `is_active` are `INTEGER` with
  `0` = false, `1` = true. Write `= 0` not `= FALSE`.
- **NULL handling**: `campaign_id` on orders is nullable. `linked_refund_id` and
  `linked_event_id` are nullable. `shipped_at` on shipments is nullable. Always
  handle NULLs explicitly.
- **SQLite dialect**: The backend is SQLite. Use `julianday()` for time math,
  `||` for string concatenation, and window functions (`ROW_NUMBER`, `COUNT(*) OVER`)
  for ranking and aggregation.
- **Correction endpoint**: Only `POST /api/sql/transaction` accepts writes.
  `POST /api/sql` is read-only.
