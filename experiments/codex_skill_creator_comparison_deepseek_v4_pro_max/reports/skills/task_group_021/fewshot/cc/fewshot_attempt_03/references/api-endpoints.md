# Asteria Fleet Data Quality Hub API Reference

All endpoints are read-only GET unless noted otherwise. The base URL is supplied in `environment_access.md`.

## Catalog and discovery

### GET /api/catalog/collections
Returns the list of available collections with metadata (collection_id, name, description, row counts).

### GET /api/catalog/schema
Returns field definitions for all collections. Each field has a name, type, and optional constraints. Study this before querying to understand the data shape and to know which fields are filterable in `/api/query`.

## Source snapshots

### GET /api/source-snapshots
Returns all snapshots across collections. Each entry has:
- `snapshot_id` — stable identifier, e.g., `partner_onboarding_2026w03-certified`
- `collection_id` — which collection it belongs to
- `status` — CERTIFIED, PROVISIONAL, or STALE
- `row_count` — number of rows in the snapshot
- `created_at` — creation timestamp

**Snapshot selection rule**: When the same logical record exists in both a CERTIFIED and PROVISIONAL snapshot, the CERTIFIED row is authoritative. PROVISIONAL snapshots provide secondary evidence; STALE snapshots should not be used as the primary source.

## Domain data endpoints

### GET /api/contacts
Returns contact records across collections. Key fields:

| Field | Description |
|---|---|
| `row_id` | Unique record identifier (e.g., `PAR-C00001`, `FIE-C00001`) |
| `collection_id` | Parent collection |
| `snapshot_id` | Source snapshot |
| `source_system` | Origin: `"HR Directory"`, `"Dispatch"`, or `"Identity Registry"` |
| `full_name` | Display name (may include Unicode) |
| `email` | Email address (normalize to lowercase NFC/NFKC) |
| `phone_digits` | Digits-only phone string |
| `city` | City name |
| `region` | Region code (e.g., `TX`, `ON`, `BE`, `England`, `MD`, `SG`) |
| `consent_status` | `GRANTED`, `PENDING`, `DENIED`, or `UNKNOWN` |
| `record_status` | `ACTIVE` or `INACTIVE` |

Use query parameters or the `/api/query` endpoint to filter by `collection_id` and `snapshot_id`. Pagination may apply — check for a `next` link.

### GET /api/transactions/fuel
Returns fuel purchase records. Key fields:

| Field | Description |
|---|---|
| `transaction_id` | Unique identifier (e.g., `FT-202601-000001`) |
| `collection_id` | Parent collection |
| `snapshot_id` | Source snapshot |
| `asset_id` | Vehicle asset (e.g., `AST-0000`) |
| `merchant_id` | Fuel merchant |
| `timestamp` | Purchase time (ISO-8601) |
| `expected_fuel_type` | What the system expected |
| `description` | Free-text fuel description — resolve to canonical type via `/api/reference/aliases` |
| `quantity` | Numerical amount |
| `quantity_unit` | Unit of `quantity` (convert to liters if needed) |
| `cost` | Amount paid |
| `cost_currency` | Currency of `cost` (convert to USD if needed) |

Canonical fuel types: `BIODIESEL`, `DIESEL`, `ELECTRIC_CHARGE`, `PREMIUM_UNLEADED`, `UNLEADED`.

### GET /api/maintenance/events
Returns maintenance event records. Key fields:

| Field | Description |
|---|---|
| `event_id` | Unique identifier (e.g., `ME-Q1-000001`) |
| `collection_id` | Parent collection |
| `snapshot_id` | Source snapshot |
| `asset_id` | Vehicle asset |
| `timestamp` | Event time (ISO-8601) |
| `odometer_km` | Odometer reading in kilometers |
| `labor_hours` | Labor hours billed |

Quality bounds: odometer must be in [0, 1,000,000]; labor hours must be in [0, 100].

### GET /api/transactions/freight
Returns freight charge records. Key fields:

| Field | Description |
|---|---|
| `charge_id` | Unique identifier (e.g., `FC-202602-000001`) |
| `collection_id` | Parent collection |
| `snapshot_id` | Source snapshot |
| `carrier_id` | Freight carrier (e.g., `CAR-004`) |
| `expected_service_class` | Anticipated service level |
| `description` | Free-text — resolve to canonical class via `/api/reference/aliases` |
| `billed_weight` | Numerical weight |
| `weight_unit` | Unit of weight (convert to KG if needed) |
| `distance` | Numerical distance |
| `distance_unit` | Unit of distance (convert to KM if needed) |
| `cost` | Amount billed |
| `cost_currency` | Currency of cost (convert to USD) |
| `timestamp` | Charge timestamp (ISO-8601) |

Canonical service classes: `EXPRESS`, `HAZMAT`, `OVERSIZE`, `REFRIGERATED`, `STANDARD`.

## Reference data

### GET /api/reference/aliases
Maps free-text descriptions to canonical categories. Each entry has:
- `alias_id` — stable reference ID (e.g., `FUA-003`, `FRA-002`)
- `description` — the free-text string to match against
- `category` — one or more canonical category values

Resolution logic: for a given record's `description`, find the alias entry whose `description` matches. If exactly one `category` value exists → recognized. If zero → unrecognized. If more than one → ambiguous.

### GET /api/reference/conversions
Unit conversion factors. Critical conversions:

| From | To | Multiply by |
|---|---|---|
| gallons | liters | 3.78541 |
| miles | kilometers | 1.60934 |
| pounds | kilograms | 0.453592 |

Apply the conversion factor: `canonical_value = source_value * conversion_factor`. Sum only after converting all values to the canonical unit.

### GET /api/reference/fx
Currency exchange rates keyed by date and currency pair. To normalize a cost to USD:
1. Find the rate entry for `{cost_currency} -> USD` with a date <= the transaction timestamp (the nearest date on or before)
2. Multiply: `cost_usd = cost * rate`
3. Round to 2 decimal places after summing

## Query interface

### POST /api/query
Accepts a JSON body for filtered data retrieval:

```json
{
  "collection": "collection_id",
  "filter": { "field": "value" },
  "snapshot": "snapshot_id"
}
```

Use this to subset by collection, snapshot, asset ID, date range, or other criteria. The catalog schema tells you which fields are filterable.

## Pagination

Some data endpoints paginate. If a response body contains a `next` field (a URL suffix or cursor), follow it. Common pattern:

```
GET {base_url}/api/contacts?collection_id=X&snapshot_id=Y
-> response has "next": "...&cursor=abc123"
-> GET {base_url}/api/contacts?collection_id=X&snapshot_id=Y&cursor=abc123
-> repeat until "next" is null or absent
```

Always check the first response for pagination indicators before assuming you have all data.
