# Asteria Fleet DQ Hub — API Reference

All endpoints live under the base URL provided in `environment_access.md`.
Every endpoint returns JSON. Authentication is handled through the credentials
supplied in that file.

## Catalog and discovery

### `GET /api/catalog/collections`

Returns the list of available collections.

**Response:**
```json
{
  "collections": [
    {
      "collection_id": "string",
      "name": "string",
      "row_count_estimate": "integer"
    }
  ]
}
```

### `GET /api/catalog/schema`

Returns the field-level schema for collections.

**Parameters:** `?collection_id=...` (optional; omit to get all collections,
include to get a single one).

**Response:**
```json
{
  "collections": {
    "<collection_id>": {
      "fields": [
        {
          "name": "string",
          "type": "string | integer | number | boolean",
          "nullable": "boolean",
          "constraints": {}
        }
      ]
    }
  }
}
```

### `GET /api/source-snapshots`

All registered snapshots across all collections.

**Response:**
```json
[
  {
    "snapshot_id": "string",
    "collection_id": "string",
    "status": "CERTIFIED | PROVISIONAL | STALE",
    "row_count": "integer",
    "created_at": "ISO-8601 string"
  }
]
```

## Reference data

### `GET /api/reference/aliases`

Maps free-text descriptions (fuel) or alias IDs (freight) to canonical
categories.

**Response:**
```json
[
  {
    "alias_id": "string",
    "collection_id": "string",
    "canonical_category": "string",
    "raw_description": "string",
    "match_type": "EXACT | PATTERN | FUZZY"
  }
]
```

For fuel, match `raw_description` against transaction `description` (case-
insensitive). For freight, match `alias_id` against the charge's `alias_id`.

### `GET /api/reference/conversions`

Unit-conversion factors. Multiply by `factor` to convert `from_unit` to
`to_unit`.

**Response:**
```json
[
  {
    "conversion_id": "string",
    "from_unit": "string",
    "to_unit": "string",
    "factor": "number"
  }
]
```

Common conversions: `GAL → L`, `LB → KG`, `MI → KM`.

### `GET /api/reference/fx`

Currency exchange rates. `rate` converts `from_currency` to `to_currency`.

**Response:**
```json
[
  {
    "rate_id": "string",
    "from_currency": "string",
    "to_currency": "string",
    "rate": "number",
    "effective_date": "string"
  }
]
```

The base currency is declared in `case_scope.json` (typically USD). Multiply
non-base-currency `spend` by the rate to normalize.

## Core data endpoints

### `GET /api/contacts`

Returns all contact rows from all source systems and snapshots.

**Response (array of objects, each with key fields):**

| Field | Type | Notes |
|---|---|---|
| `row_id` | string | Stable identifier (PAR-C... or FIE-C...) |
| `snapshot_id` | string | Which snapshot this row belongs to |
| `source_system` | string | CRM, Compliance Master, Partner Portal, HR Directory, Dispatch, Identity Registry |
| `name` | string | Unicode display name |
| `email` | string | May be null |
| `phone` | string | May be null, various formats |
| `city` | string | May be null |
| `region` | string | Two-letter codes (TX, ON, etc.) or full names (England) |
| `consent_status` | string | GRANTED, PENDING, DENIED, UNKNOWN |
| `record_status` | string | ACTIVE, INACTIVE |

**Pagination:** Cursor-based. Response includes `next_cursor`. Pass as
`?cursor=...`. When the collection is small (under 1000 rows), all rows are in
the first response.

### `GET /api/transactions/fuel`

Fuel-purchase transaction rows.

| Field | Type | Notes |
|---|---|---|
| `transaction_id` | string | FT-YYYYMM-NNNNNN |
| `snapshot_id` | string | |
| `asset_id` | string | AST-NNNN |
| `merchant_id` | string | MER-NNN |
| `expected_fuel_type` | string | BIODIESEL, DIESEL, ELECTRIC_CHARGE, PREMIUM_UNLEADED, UNLEADED |
| `description` | string | Free-text fuel description for alias matching |
| `quantity` | number | Volume; unit in `quantity_unit` |
| `quantity_unit` | string | GAL, L, etc. |
| `currency` | string | USD, EUR, etc. |
| `spend` | number | Payment amount |
| `transaction_date` | string | ISO-8601 date |

**Pagination:** Cursor-based. Fetch all pages.

### `GET /api/transactions/freight`

Freight-charge rows.

| Field | Type | Notes |
|---|---|---|
| `charge_id` | string | FC-YYYYMM-NNNNNN |
| `snapshot_id` | string | |
| `carrier_id` | string | CAR-NNN |
| `expected_service_class` | string | EXPRESS, HAZMAT, OVERSIZE, REFRIGERATED, STANDARD |
| `alias_id` | string | FRA-NNN; maps to canonical service class |
| `billed_weight` | number | Weight in `weight_unit` |
| `weight_unit` | string | LB, KG, etc. |
| `distance` | number | Distance in `distance_unit` |
| `distance_unit` | string | MI, KM, etc. |
| `currency` | string | |
| `spend` | number | |
| `charge_date` | string | ISO-8601 date |

**Pagination:** Cursor-based.

### `GET /api/maintenance/events`

Maintenance-event rows.

| Field | Type | Notes |
|---|---|---|
| `event_id` | string | ME-Q1-NNNNNN |
| `snapshot_id` | string | |
| `asset_id` | string | AST-NNNN |
| `event_timestamp` | string | ISO-8601; may be null/empty |
| `odometer_km` | number | May be null; expected range 0–999999 |
| `labor_hours` | number | May be null; expected range 0–100 |
| `description` | string | |

**Pagination:** Cursor-based. The collection is larger than a single page;
always paginate fully.

## Query API

### `POST /api/query`

Read-only filtered query.

**Request body:**
```json
{
  "collection_id": "string",
  "filters": [
    {
      "field": "string",
      "operator": "eq | gt | gte | lt | lte | in | contains",
      "value": "string or number"
    }
  ],
  "limit": "integer",
  "cursor": "string or null"
}
```

**Response:**
```json
{
  "rows": [],
  "next_cursor": "string or null"
}
```

Pagination: pass the returned `next_cursor` in the next request. Stop when
`next_cursor` is `null`.
