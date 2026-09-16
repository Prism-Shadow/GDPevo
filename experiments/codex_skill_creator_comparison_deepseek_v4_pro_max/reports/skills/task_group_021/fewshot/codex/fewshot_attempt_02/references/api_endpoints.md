# API Endpoint Reference

## Catalog and Schema

### GET /api/catalog/collections

Returns the list of available collections.

Response shape:
```json
{
  "collections": [
    {
      "id": "string",
      "display_name": "string",
      "snapshot_ids": ["string"],
      "record_count": "integer"
    }
  ]
}
```

### GET /api/catalog/schema

Returns column definitions and quality-rule semantics. The response includes:

- Column names and data types
- Which column is the logical-record identifier (e.g., `transaction_id`, `event_id`, `charge_id`)
- Source-system provenance columns (e.g., `source_system`, `snapshot_id`)
- Quality-check columns: timestamp fields, odometer fields, labor-hour fields, contact-channel fields, category fields, physical-measure fields
- Acceptable ranges for numeric fields

## Data Endpoints

### GET /api/contacts

Returns contact rows. Each row has:
- A stable row ID (e.g., `PAR-C00001` or `FIE-C00001`)
- Contact fields: `display_name`, `email`, `phone`, `city`, `region`
- Status fields: `record_status` (ACTIVE/INACTIVE), `consent_status` (GRANTED/PENDING/DENIED/UNKNOWN)
- Source provenance: `source_system` (e.g., "CRM", "Compliance Master", "Partner Portal" or "HR Directory", "Dispatch", "Identity Registry")
- `collection_id` for scoping

### GET /api/transactions/fuel

Returns fuel transaction rows. Each row has:
- `transaction_id` (e.g., `FT-202601-000001`)
- `asset_id`, `merchant_id`
- `fuel_type` (raw, from the data)
- `description` (text to map through aliases)
- `volume`, `volume_unit`
- `spend`, `currency`
- `snapshot_id`, `timestamp`

### GET /api/transactions/freight

Returns freight charge rows. Each row has:
- `charge_id` (e.g., `FC-202602-000001`)
- `carrier_id`
- `service_class` (raw, from the data)
- `description` (text to map through aliases)
- `billed_weight`, `weight_unit`
- `distance`, `distance_unit`
- `spend`, `currency`
- `snapshot_id`, `timestamp`

### GET /api/maintenance/events

Returns maintenance event rows. Large collections: use pagination.

Each event row has:
- `event_id` (e.g., `ME-Q1-000001`)
- `asset_id`
- `timestamp` (ISO-8601)
- `odometer_reading` (numeric)
- `labor_hours` (numeric)
- `source_system`
- `snapshot_id`

## Reference Endpoints

### GET /api/reference/aliases

Maps free-text descriptions to canonical categories. Response shape:
```json
{
  "aliases": [
    {
      "id": "string",
      "label": "string",
      "canonical_value": "string",
      "category": "string"
    }
  ]
}
```

The `category` field indicates the domain: `fuel_type` for fuel, `service_class` for freight.

### GET /api/reference/conversions

Unit conversion factors. Response shape:
```json
{
  "conversions": [
    {
      "from_unit": "string",
      "to_unit": "string",
      "factor": "number"
    }
  ]
}
```

Multiply the raw value by `factor` to convert from `from_unit` to `to_unit`.

### GET /api/reference/fx

Currency exchange rates. Response shape:
```json
{
  "rates": [
    {
      "from_currency": "string",
      "to_currency": "string",
      "rate": "number"
    }
  ]
}
```

Multiply the raw amount by `rate` to convert to the base currency.

## Source Snapshots

### GET /api/source-snapshots

Response shape:
```json
{
  "snapshots": [
    {
      "id": "string",
      "collection_id": "string",
      "status": "string",
      "row_count": "integer",
      "created_at": "string"
    }
  ]
}
```

`status` is either `certified` (authoritative) or `provisional` (supplementary). Always prefer `certified` rows when the same logical record appears in both snapshots.

## Query Interface

### POST /api/query

Accepts a JSON body with a `sql` field containing a `SELECT` statement. Supports standard SQL clauses: `WHERE`, `ORDER BY`, `LIMIT`, `OFFSET`.

Example:
```json
{"sql": "SELECT * FROM maintenance_events_2026_q1 WHERE timestamp >= '2026-01-01T00:00:00Z' AND timestamp <= '2026-03-31T23:59:59Z' ORDER BY event_id LIMIT 200 OFFSET 0"}
```

Use for server-side filtering, pagination, or when the GET endpoint does not return all needed data.

## Pagination Pattern

When a collection is larger than a single response page:

1. Send the first query with `LIMIT 200 OFFSET 0`
2. If the response row count equals the limit, send the next query with `OFFSET 200`, then `OFFSET 400`, etc.
3. Stop when the response row count is less than the limit
4. Concatenate all pages into the full dataset

Always include `ORDER BY` with the logical ID column to ensure deterministic page boundaries.
