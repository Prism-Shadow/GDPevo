---
name: atlas-commerce-ops
description: Analyze or correct operational data through the Atlas Commerce Operations API. Use this skill whenever a task references an authenticated Atlas workplace, Atlas Commerce Operations, a task environment base URL, or an API with /api/schema, /api/sql, /api/sql/transaction, or /api/correction-audit endpoints. The skill covers the API contract, source-record deduplication, effective event selection, integer boolean and monetary conventions, controlled data corrections, and strict answer-template output.
---

# Atlas Commerce Operations — Workplace Data Analysis and Correction

Use this skill to query, analyze, or correct business records through the
Atlas Commerce Operations workplace API. Follow every step — the API is
opinionated and small mistakes in conventions produce wrong answers.

## 1. Environment Setup

The prompt supplies a base URL placeholder (usually `<TASK_ENV_BASE_URL>`).
Read the task's `input/prompt.txt` to get the actual base URL; it is
available from the runtime environment.

Every API call must carry this header:

```
Authorization: Bearer atlas-ops-token-022
```

Available endpoints:

| Method | Path                  | Purpose                                   |
|--------|-----------------------|-------------------------------------------|
| GET    | /api/schema            | Full DDL for every table plus indexes     |
| GET    | /api/data-dictionary   | Column descriptions, conventions, semantics |
| POST   | /api/sql               | Read-only analytical SQL                  |
| POST   | /api/sql/transaction   | Controlled write (INSERT/UPDATE only)     |
| GET    | /api/correction-audit  | Public audit records of past corrections  |

Call `/api/schema` and `/api/data-dictionary` first in every session. The
schema is stable but the dictionary carries convention notes (timestamp
formats, boolean encoding, money semantics) that change how queries must
be written.

## 2. Writing SQL Queries (POST /api/sql)

Send a JSON body:

```json
{"sql": "SELECT ..."}
```

Rules:

- **UTC timestamps.** Every stored timestamp ends in `Z` and is ISO-8601.
  Calendar dates use `YYYY-MM-DD`. When the task specifies a boundary like
  `"start": "2026-03-01", "end": "2026-04-30", "inclusive": true`, use
  `service_date BETWEEN '2026-03-01' AND '2026-04-30'`.  When the boundary
  uses ISO-8601 timestamps use the same literal with the appropriate
  comparator.

- **Integer booleans.** Columns named `is_*` use 0 for false and 1 for
  true. Compare with `= 0` or `= 1`, never with `IS TRUE`.

- **Monetary minor units.** Columns named `*_minor` hold values in the
  smallest currency unit (cents for USD). `gross_amount_minor` on `orders`
  is in the order's currency. `amount_minor` on `refund_attempts` and
  `payment_events` is in the row's currency.  To convert to major units
  divide by 100.  When the task requests USD, multiply by an FX rate from
  the `fx_rates` table (see section 4).

- **NULL handling.** `corrected_at` and `correction_reason` in source-row
  tables (`carrier_scans`, `inventory_movements`) are NULL when the row has
  never been corrected. `linked_refund_id` on `refund_attempts` is NULL
  when there is no linked reversal. `active_to` on `employees` is NULL when
  the assignment is still active. Check the schema for each column's
  nullability.

## 3. Source-Data Deduplication

Every source-ingestion table has a deduplication index on `(source_system,
external_event_id, ingested_at)`. The same external event can arrive more
than once.  **Always deduplicate before analysis** by picking the row with
the lowest `ingested_at` for each `(source_system, external_event_id)`.

The affected tables and their dedup key:

| Table                 | Dedup Key                                        |
|-----------------------|--------------------------------------------------|
| carrier_scans         | source_system, external_event_id, ingested_at    |
| case_events           | source_system, external_event_id, ingested_at    |
| inventory_movements   | source_system, external_event_id, ingested_at    |
| order_events          | source_system, external_event_id, ingested_at    |
| payment_events        | source_system, external_event_id, ingested_at    |
| refund_attempts       | source_system, external_event_id, ingested_at    |
| warehouse_task_events | source_system, external_event_id, ingested_at    |

Use a subquery or CTE:

```sql
WITH dedup AS (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY source_system, external_event_id
    ORDER BY ingested_at ASC
  ) AS rn
  FROM <table>
)
SELECT ... FROM dedup WHERE rn = 1
```

After dedup, treat the surviving row as the single source of truth for
that external event.  Reference tables (`accounts`, `campaigns`, `orders`,
`products`, `shipments`, `support_cases`, `warehouse_tasks`, `warehouses`,
`employees`) do not need dedup.

## 4. Effective Event Selection

Several tables have an "effective" index designed for picking the most
recent event per entity:

| Effective Index                 | Key                                         |
|--------------------------------|---------------------------------------------|
| carrier_scans                  | shipment_id, canonical_event_at, scan_row_id |
| case_events                    | case_id, event_at, case_event_id            |
| order_events                   | order_id, event_at, event_id                |
| warehouse_task_events          | task_id, event_at, task_event_id            |

When a task asks for the "effective final" state of an entity, use the row
with the latest `canonical_event_at` (carrier_scans) or `event_at` (other
tables), breaking ties with the row-id. Example for carrier scans:

```sql
WITH dedup AS (...),
effective AS (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY shipment_id
    ORDER BY canonical_event_at DESC, scan_row_id DESC
  ) AS rn
  FROM dedup
)
SELECT ... FROM effective WHERE rn = 1
```

The `current_status` column on `orders`, `shipments`, `support_cases`, and
`warehouse_tasks` is a convenience snapshot and may lag append-only event
history.  When the task definition requires event-level precision, always
derive state from the effective event instead.

## 5. Monetary Conversion to USD

When a task calls for USD values, join `fx_rates` on the row's `currency`
and the appropriate date. The `fx_rates` table maps `(rate_date, currency)`
to `usd_per_unit`.

- For `refund_attempts`, use `service_date`.
- For `payment_events`, use `DATE(event_at)`.
- For `orders`, use the date from the task's policy (typically the refund
  or payment service date relevant to the comparison).

Convert minor-unit amounts to major USD:

```sql
ROUND((r.amount_minor / 100.0) * fx.usd_per_unit, 2) AS amount_usd
```

The division by 100.0 converts minor units to major currency units. The
`usd_per_unit` rate is multiplied. Always round only the final displayed
USD value to the precision requested in the task's money_policy (usually 2
decimal places).  Keep intermediate sums unrounded until the final step.

## 6. Controlled Corrections (POST /api/sql/transaction)

Only one of the five task families uses corrections, but the pattern is
consistent.  The endpoint accepts a JSON body with a single write statement:

```json
{"sql": "UPDATE carrier_scans SET canonical_status = '<new>', corrected_at = '<ts>', correction_reason = '<code>' WHERE scan_row_id = '<id>'"}
```

The only allowed operations are INSERT and UPDATE.  The response reports
`affected_business_rows` and `audit_rows`.  The system automatically writes
a matching row to `correction_audit`.

The request payload (e.g., `carrier_quality_request.json`) provides:
- The field to change and the new value.
- `reason_code`, `actor`, `audit_id`, `correction_key`, `corrected_at`.
- A correction_status_rule defining when to report APPLIED vs NOT_APPLIED.

Workflow:

1. Query pre-correction state to identify the target row and verify the
   expected old value.
2. Submit the UPDATE via `POST /api/sql/transaction`.  Read the response
   to get `affected_business_rows` and `audit_rows`.
3. Re-query the target row to confirm the new value is persisted.
4. Fetch the audit record from `GET /api/correction-audit` and confirm it
   matches.
5. Re-compute the business metric affected by the correction (e.g.,
   backlog count).
6. Report `APPLIED` only when every condition in the request's
   correction_status_rule is satisfied; otherwise report `NOT_APPLIED`.

**Important: raw values must not be changed.** Only canonical fields may
be corrected. The `raw_status`, `raw_event_at`, and identity fields like
`shipment_id` and `scan_row_id` stay untouched.

## 7. Answer Template Conformance

Every task includes an `input/payloads/answer_template.json`.  The final
output must match that schema exactly:

- All `required` fields must be present.
- `additionalProperties: false` means no extra fields are allowed.
- Enum fields must use exactly the listed values (case-sensitive).
- Numeric fields with `multipleOf` or `minimum`/`maximum` must satisfy
  those constraints.
- Arrays with `uniqueItems: true` must not contain duplicates.
- Array ordering specified in the request definition must be followed
  exactly.
- Output only pure JSON — no surrounding text, explanation, or markdown
  fences unless the template itself is a JSON Schema and the prompt asks
  for a file named `answer.json`.

Read the answer template *before* running queries.  Some templates
describe ordering rules (e.g., "ascending by order_id") that affect how
query results are sorted.  Some embed `pattern` constraints that clarify
ID formats.  Some have `description` notes that clarify business meaning.

## 8. Common Task Workflow

1. Read `input/prompt.txt` and every payload file under `input/payloads/`.
2. Read `input/payloads/answer_template.json` — note every required field
   and constraint.
3. Call `GET /api/schema` and `GET /api/data-dictionary` to confirm table
   shapes and conventions.
4. Write dedup CTEs for every source-ingestion table you query.
5. Write effective-event CTEs when the task asks for "final" or "effective"
   state.
6. Filter to the exact cohort described in the request payload (account
   tier, region, campaign, time window, warehouse, batch, etc.).
7. Apply the business definitions from the request payload literally —
   composite conditions, threshold rules, ranking rules.
8. Compute all required output fields, respecting rounding and ordering
   rules.
9. Write the result as a single JSON object to `answer.json` that conforms
   exactly to the answer template. No commentary outside the JSON.

## 9. Reference

For the full schema at-a-glance without calling the API, see
[references/schema-summary.md](references/schema-summary.md).  Always
prefer the live API responses for column-level details; use the reference
only as a quick-lookup supplement.
