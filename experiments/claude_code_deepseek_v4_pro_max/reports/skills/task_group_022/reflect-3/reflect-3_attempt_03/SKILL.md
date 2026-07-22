# Atlas Commerce Operations — Analytical Skill

Use this skill whenever you must answer a structured business question against the Atlas Commerce Operations workplace database. The service exposes an authenticated HTTP API; all interactions are read-only unless a controlled correction is explicitly requested.

---

## 1. Service Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/schema` | Table DDL and indexes |
| GET | `/api/data-dictionary` | Column descriptions and conventions |
| POST | `/api/sql` | Read-only analytical SQL (field: `"sql"`) |
| POST | `/api/sql/transaction` | Controlled DML with audit trail |
| GET | `/api/correction-audit` | Public correction audit records |

Authenticate every request with the `Authorization: Bearer <token>` header and `Content-Type: application/json`.

---

## 2. Schema Discovery (Always First)

Before writing any query, fetch the schema and data dictionary:

```
GET /api/schema        → tables, columns, foreign keys, indexes
GET /api/data-dictionary → column descriptions, conventions, domain values
```

The dictionary documents conventions:
- **Timestamps**: ISO-8601 UTC ending in `Z`.
- **Money**: `*_minor` columns hold the smallest currency unit (e.g., cents). Use `fx_rates.usd_per_unit` at the transaction's `service_date` for USD conversion.
- **Source rows**: `raw_*` columns preserve upstream values; `canonical_*` columns hold the normalised operational value.

---

## 3. SQL Patterns

### 3.1 Field name
The read-only SQL endpoint expects `{"sql": "<statement>"}` — the key is `"sql"`, not `"query"`.

### 3.2 Avoid large IN-subqueries
The SQL endpoint silently truncates result sets when an `IN (<subquery>)` list grows large. **Always rewrite eligibility filters as JOINs:**

```sql
-- ❌ may silently truncate
SELECT ... FROM shipments
WHERE order_id IN (SELECT order_id FROM orders WHERE campaign_id = 'CMP-...')

-- ✅ safe
SELECT ... FROM shipments s
JOIN orders o ON s.order_id = o.order_id
WHERE o.campaign_id = 'CMP-...'
```

### 3.3 Selecting the effective (latest) row per group
Every append-only event table (`carrier_scans`, `warehouse_task_events`, `case_events`, `refund_attempts`, `payment_events`) may contain import retries. The **effective row** for a business event is the one with the latest `ingested_at` among rows sharing the same `(source_system, external_event_id)`.

Use a **correlated subquery** to pick one effective row per group without hitting row limits:

```sql
SELECT cs.canonical_status, cs.canonical_event_at
FROM carrier_scans cs
WHERE cs.scan_row_id = (
  SELECT cs2.scan_row_id FROM carrier_scans cs2
  WHERE cs2.shipment_id = cs.shipment_id
  ORDER BY cs2.canonical_event_at DESC, cs2.scan_row_id DESC
  LIMIT 1
)
```

When ordering for "effective final" status, use the composite order that matches the table's effective index (typically `<parent>, <event_at> DESC, <row_id> DESC`).

### 3.4 Aggregation when row limits are a concern
Prefer `GROUP BY` with `MAX()` for getting the latest timestamp per group — the engine returns one row per group, avoiding the truncation that fetching every row can cause. Then join back for the full row if needed.

---

## 4. Business Data Concepts

### 4.1 Production accounts
A production account satisfies `is_internal = 0 AND is_test = 0`. Check both flags.

### 4.2 Effective carrier status
The operational delivery status of a shipment is the `canonical_status` of the **latest scan** (by `canonical_event_at`, ties broken by `scan_row_id DESC`). Do **not** rely on `shipments.current_status` — it is a convenience snapshot that may lag the append-only event history.

### 4.3 Effective refund / payment rows
Deduplicate by `(source_system, external_event_id)` → latest `ingested_at`. A logical refund is identified by `refund_id`; each `refund_id` maps to exactly one effective row.

### 4.4 Reversals
A reversal of a settled refund appears as a `refund_attempts` row with `status = 'REVERSED'` whose `linked_refund_id` points to the settled `refund_id` being reversed.

### 4.5 Currency conversion
- Every monetary `*_minor` field is in the smallest unit of the row's `currency`.
- Convert to USD: `(amount_minor / 100.0) × fx_rates.usd_per_unit` at the transaction's `service_date`.
- When comparing an order's gross value against refunds, convert the order gross at the refund's `service_date` FX rate.

### 4.6 Warehouse task productivity
- Use `warehouse_task_events` where `event_type = 'COMPLETED'` for `units` and `productive_minutes`.
- `units_per_hour = (total_completed_units / total_productive_minutes) × 60`.
- A "rework" task is identified by `current_status = 'REWORK'` or the presence of a `REWORK` event.

### 4.7 Support-case active time
"Active time" is total elapsed time minus periods the case spent `WAITING_CUSTOMER`. Compute it from the ordered `case_events`:
- Start a clock on `OPENED` or `CUSTOMER_REPLIED`.
- Pause the clock on `WAITING_CUSTOMER`.
- Stop the clock on `RESOLVED` or use the analysis cutoff for unresolved cases.
- `REOPENED` restarts the clock.

---

## 5. Answer Construction

1. Read the business request payload carefully — every definition, threshold, and rounding rule matters.
2. Locate the answer template and enforce **every constraint**: `required` fields, `additionalProperties: false`, `type`, `minimum`/`maximum`, `multipleOf`, `pattern`, `minItems`/`maxItems`, `uniqueItems`, and `enum`.
3. Round **only the final reported values** as specified (e.g., 4 decimal places for rates, 2 for USD). Use unrounded values for intermediate comparisons and rankings.
4. Sort array elements exactly as the request specifies. When a ranking has ties, apply every tiebreaker in order.
5. Write the answer as a single JSON object with no commentary outside the JSON.

---

## 6. Correction Workflow (When a Controlled DML Is Requested)

1. Identify the exact row and field that needs correction by comparing `raw_*` values against their `canonical_*` counterparts.
2. Use `POST /api/sql/transaction` to apply the minimal change atomically with its audit record.
3. Verify the correction with a post-change query.
4. Report `APPLIED` only when the transaction commits exactly one business-row change and one audit row, **and** a follow-up query confirms the corrected value.
5. Otherwise report `NOT_APPLIED` with the actual observed results.

---

## 7. Process Checklist

For every new analytical task:

1. **[ ]** Fetch `/api/schema` and `/api/data-dictionary`.
2. **[ ]** Read every word of the business request payload and the answer template.
3. **[ ]** Map business definitions to specific column values (e.g., "DELIVERED", "SETTLED", "PRODUCTION").
4. **[ ]** Write eligibility queries using JOINs, not large IN-subqueries.
5. **[ ]** Deduplicate event tables with correlated subqueries.
6. **[ ]** Compute intermediate values with full precision; round only final outputs.
7. **[ ]** Validate the answer against the template's JSON Schema before submitting.
8. **[ ]** For corrections: apply → verify → report `APPLIED` or `NOT_APPLIED`.
