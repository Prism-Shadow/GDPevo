# Atlas Commerce Operations API Reference

All endpoints are served from TASK_ENV_BASE_URL/api/path.
Authentication uses the Authorization: Bearer token header on every request.
All responses are JSON.

## Endpoint Summary

| Method | Path | Purpose | Body |
|--------|------|---------|------|
| GET | /api/schema | Table and column listing | None |
| GET | /api/data-dictionary | Human-readable field descriptions | None |
| POST | /api/sql | Read-only analytical SQL | {sql: statement} |
| POST | /api/sql/transaction | Controlled data correction | {sql: UPDATE, audit_id: ..., ...} |
| GET | /api/correction-audit | Audit records for past corrections | None |

## GET /api/schema

Returns a JSON object where each key is a table name and each value is an array
of column names in that table.

Example response:
{
  orders: [id, account_id, warehouse_id, campaign_id, created_at, gross_amount, currency],
  shipments: [id, order_id, carrier, promised_delivery_at, created_at],
  carrier_scans: [id, shipment_id, raw_status, canonical_status, scanned_at, import_batch_id],
  ...
}

## GET /api/data-dictionary

Returns a JSON object where each key is a table.column string and each value
is a human-readable description of what that field means.

Example fragment:
{
  orders.id: Stable order identifier.,
  orders.created_at: UTC timestamp when the order was placed.,
  shipments.promised_delivery_at: UTC timestamp of the carrier promise to the customer.,
  carrier_scans.raw_status: Original status reported by the carrier.,
  carrier_scans.canonical_status: Normalized status used for business logic.,
  ...
}

Always read the data dictionary before writing SQL. Field names alone do not
convey the business meaning.

## POST /api/sql

Submit a read-only analytical SQL query.

Request body:
{sql: SELECT ... FROM ... WHERE ... ORDER BY ...}

Returns an array of result rows (each row a JSON object with column-name keys).

## POST /api/sql/transaction

Execute a controlled single-row data correction. Used only for correction tasks
with an approved_correction section in the request payload.

Request body includes the SQL UPDATE plus audit metadata:
{
  sql: UPDATE table SET field=new_value WHERE id=row_id,
  audit_id: AUD-...,
  correction_key: ...,
  reason_code: SOURCE_RECONCILIATION,
  actor: ops-data-quality,
  corrected_at: 2026-03-20T09:30:00Z,
  field_name: canonical_status,
  old_value: IN_TRANSIT,
  new_value: DELIVERED
}

Returns a JSON object with affected_business_rows and audit_rows counts.

## GET /api/correction-audit

Returns an array of all correction audit records. Filter by audit_id or
correction_key to verify that the expected audit row was created.

Each record contains: audit_id, correction_key, entity_type, entity_id,
source_row_id, field_name, old_value, new_value, reason_code,
corrected_at, actor.
