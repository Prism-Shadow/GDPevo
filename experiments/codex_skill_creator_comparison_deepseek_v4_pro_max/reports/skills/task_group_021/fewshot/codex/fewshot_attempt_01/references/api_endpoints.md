# Asteria Fleet DQH API Endpoints

All endpoints are read-only GET unless noted. Base URL comes from environment_access.md.

## Catalog

### GET /api/catalog/collections
Returns the list of available collections. Response includes collection_id and metadata for each.

### GET /api/catalog/schema?collection_id=...
Returns field-level schema for a collection: field names, types, and descriptions. Use this to understand column semantics before querying.

## Source Snapshots

### GET /api/source-snapshots?collection_id=...
Returns all snapshots for a collection. Each snapshot has:
- snapshot_id: Stable identifier (e.g., <collection_id>-certified, <collection_id>-provisional)
- status: One of CERTIFIED, PROVISIONAL, or STALE
- row_count: Number of raw rows in this snapshot

The CERTIFIED snapshot is authoritative. PROVISIONAL may contain additional rows that duplicate CERTIFIED records; duplicates share the same public stable ID.

## Domain Data Endpoints

### GET /api/contacts?collection_id=...
Partner/people contact records. Response is a JSON array of objects. Each row has a row_id field (e.g., PAR-C00001 or FIE-C00001). Common fields: name, email, phone, city, region, consent_status, record_status, source_system.

### GET /api/transactions/fuel?collection_id=...
Fuel purchase transactions. Each row has a transaction_id (e.g., FT-202601-000001). Fields include asset_id, merchant_id, expected_fuel_type, description, volume, volume_unit, spend, spend_currency, source_snapshot_id, and a date/timestamp field.

### GET /api/transactions/freight?collection_id=...
Freight charge transactions. Each row has a charge_id (e.g., FC-202602-000001). Fields include carrier_id, alias_id, expected_service_class, billed_weight, weight_unit, distance, distance_unit, spend, spend_currency, source_snapshot_id.

### GET /api/maintenance/events?collection_id=...
Maintenance event records. Each row has an event_id (e.g., ME-Q1-000001). Fields include asset_id, timestamp, odometer_km, labor_hours, source_snapshot_id.

## Reference Data

### GET /api/reference/aliases
Maps description strings to recognized categories. Response: array of objects with alias_id, description_pattern, and category or fuel_type/service_class.

### GET /api/reference/conversions
Unit conversion factors. Maps source_unit to target_unit with a conversion_factor.

### GET /api/reference/fx
Foreign exchange rates. Maps currency to usd_rate for spend normalization.

## Query Interface

### POST /api/query
Accepts a JSON body with a query string (SQL-like syntax) and returns results.

## Pagination

Endpoints that return large collections support pagination via ?offset=N&limit=M query parameters. Continue fetching with increasing offsets until all pages are exhausted.
