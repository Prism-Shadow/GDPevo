# Asteria Fleet Data Quality Hub — API Reference

## Base URL

Read `<TASK_ENV_BASE_URL>` from `environment_access.md`. The file provides:

```
base_url: http://task-env:9021/
credentials: none
```

All endpoints are relative to `base_url`. No authentication header is needed.

## GET /api/catalog/collections

Returns the list of available collections.

Response shape:
```json
{
  "collections": [
    {
      "collection_id": "partner_onboarding_2026w03",
      "kind": "contacts",
      "description": "...",
      "source_systems": ["CRM", "Compliance Master", "Partner Portal"],
      "snapshot_policy": "certified+provisional"
    }
  ]
}
```

Key fields:
- `collection_id` — stable identifier; matches case_scope.json
- `kind` — determines which data endpoint to use: `contacts`, `transactions`,
  `maintenance`
- `source_systems` — ordered list of upstream sources; use for precedence
- `snapshot_policy` — indicates whether multiple snapshots may exist

## GET /api/catalog/schema?collection_id=<id>

Returns the field schema for a collection.

Response shape:
```json
{
  "collection_id": "...",
  "fields": [
    {"name": "transaction_id", "type": "string", "nullable": false},
    {"name": "asset_id", "type": "string", "nullable": false},
    {"name": "merchant_id", "type": "string", "nullable": false},
    {"name": "fuel_type", "type": "string", "nullable": true},
    {"name": "description", "type": "string", "nullable": false},
    {"name": "volume_l", "type": "number", "nullable": true},
    {"name": "spend", "type": "number", "nullable": true},
    {"name": "spend_currency", "type": "string", "nullable": true},
    {"name": "timestamp", "type": "string", "format": "date-time", "nullable": false},
    {"name": "snapshot_id", "type": "string", "nullable": false}
  ]
}
```

Use this to identify:
- The primary ID field (for dedup)
- Timestamp fields (for cutoff validation)
- Numeric measure fields (for quantity validation, normalization)
- Categorical fields (for category matching)
- Currency fields (for FX conversion)

## GET /api/source-snapshots?collection_id=<id>

Lists all snapshots for a collection.

Response shape:
```json
{
  "snapshots": [
    {
      "snapshot_id": "fuel_purchases_2026_01-certified",
      "collection_id": "fuel_purchases_2026_01",
      "status": "CERTIFIED",
      "row_count": 1305,
      "loaded_at": "2026-02-01T00:00:00Z"
    },
    {
      "snapshot_id": "fuel_purchases_2026_01-provisional",
      "collection_id": "fuel_purchases_2026_01",
      "status": "PROVISIONAL",
      "row_count": 45,
      "loaded_at": "2026-02-02T00:00:00Z"
    }
  ]
}
```

**Snapshot authority rules:**
1. Status priority: `CERTIFIED` > `PROVISIONAL` > `STALE`
2. Within the same status, pick the most recent `loaded_at`

The authoritative snapshot is the one whose rows are retained when a record
appears in multiple snapshots.

## GET /api/contacts?collection_id=<id>

Returns contact records for contact-oriented collections.

Response shape:
```json
{
  "rows": [
    {
      "row_id": "PAR-C00001",
      "snapshot_id": "partner_onboarding_2026w03-certified",
      "source_system": "CRM",
      "cluster_id": "partner_onboarding_2026w03-cluster-001",
      "name": "Sofia Smith",
      "email": "sofia.smith@example-fleet.com",
      "phone": "+1-210-000-6500",
      "city": "Austin",
      "region": "TX",
      "status": "ACTIVE",
      "consent": "PENDING"
    }
  ]
}
```

When the contacts endpoint is available, prefer it over `/api/query` for loading
contact data. It may include hub-computed fields like `cluster_id`.

## GET /api/transactions/fuel?collection_id=<id>

Returns fuel transaction records.

Response shape:
```json
{
  "rows": [
    {
      "transaction_id": "FT-202601-000001",
      "asset_id": "AST-0000",
      "merchant_id": "MER-001",
      "fuel_type": "DIESEL",
      "description": "Diesel pump #4",
      "volume_l": 150.00,
      "spend": 45.00,
      "spend_currency": "USD",
      "timestamp": "2026-01-05T08:30:00Z",
      "snapshot_id": "fuel_purchases_2026_01-certified"
    }
  ]
}
```

## GET /api/transactions/freight?collection_id=<id>

Returns freight charge records.

Response shape:
```json
{
  "rows": [
    {
      "charge_id": "FC-202602-000001",
      "carrier_id": "CAR-001",
      "service_class": "EXPRESS",
      "alias_id": "FRA-001",
      "billed_weight_kg": 1200.50,
      "distance_km": 450.00,
      "spend": 850.00,
      "spend_currency": "USD",
      "timestamp": "2026-02-03T10:00:00Z",
      "snapshot_id": "freight_charges_2026_02-certified"
    }
  ]
}
```

## GET /api/maintenance/events?collection_id=<id>

Returns maintenance event records.

Response shape:
```json
{
  "rows": [
    {
      "event_id": "ME-Q1-000001",
      "asset_id": "AST-0001",
      "event_type": "REPAIR",
      "timestamp": "2026-01-10T14:00:00Z",
      "odometer_km": 15000.00,
      "labor_hours": 2.5,
      "snapshot_id": "maintenance_events_2026_q1-certified"
    }
  ]
}
```

## POST /api/query

Paginated, filtered query endpoint. Use this as the primary data-loading
mechanism for large collections.

Request:
```json
{
  "collection_kind": "transactions",
  "collection_id": "fuel_purchases_2026_01",
  "snapshot_ids": ["fuel_purchases_2026_01-certified", "fuel_purchases_2026_01-provisional"],
  "limit": 500,
  "offset": 0,
  "filters": {
    "timestamp_before": "2026-01-31T23:59:59Z"
  }
}
```

Parameters:
- `collection_kind` (required) — matches the catalog `kind`: `contacts`,
  `transactions`, `maintenance`
- `collection_id` (required) — stable collection ID
- `snapshot_ids` (optional) — restrict to specific snapshots; omit or pass all
  to get the full picture
- `limit` (optional, default 500) — page size
- `offset` (optional, default 0) — zero-based offset
- `filters` (optional) — server-side filters; supports `timestamp_before`,
  `timestamp_after`

Response:
```json
{
  "rows": [...],
  "total_count": 1350,
  "limit": 500,
  "offset": 0
}
```

Pagination loop:
```python
all_rows = []
offset = 0
while True:
    resp = query(offset=offset, limit=500)
    rows = resp["rows"]
    all_rows.extend(rows)
    if len(rows) < 500:
        break
    offset += 500
```

The `total_count` field (when present) can be used as a consistency check.

## GET /api/reference/aliases?collection_id=<id>

Maps alias IDs to canonical service classes for freight.

Response shape:
```json
{
  "aliases": [
    {"alias_id": "FRA-001", "canonical_class": "EXPRESS"},
    {"alias_id": "FRA-002", "canonical_class": "STANDARD"}
  ]
}
```

Some aliases may appear multiple times with different canonical classes — these
are ambiguous.

## GET /api/reference/conversions?collection_id=<id>

Provides unit conversion factors.

Response shape:
```json
{
  "conversions": [
    {"from_unit": "GAL", "to_unit": "L", "factor": 3.78541},
    {"from_unit": "LB", "to_unit": "KG", "factor": 0.453592},
    {"from_unit": "MI", "to_unit": "KM", "factor": 1.60934}
  ]
}
```

Apply conversions before computing normalized totals. Keep intermediate values
at full precision; only round final aggregated totals.

## GET /api/reference/fx?collection_id=<id>

Provides FX rates for currency conversion.

Response shape:
```json
{
  "rates": [
    {"from_currency": "EUR", "to_currency": "USD", "rate": 1.10},
    {"from_currency": "GBP", "to_currency": "USD", "rate": 1.27}
  ]
}
```

Apply to `spend` fields where `spend_currency` differs from the base currency
(from case scope).

## Error handling

All endpoints return standard HTTP status codes. A non-2xx response means the
request was malformed. Common issues:
- Missing required `collection_id` parameter → 400
- Unknown collection → 404
- Invalid query JSON → 422

If an endpoint returns an unexpected response, read the response body for an
error message, fix the request, and retry.
