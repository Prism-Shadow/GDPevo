# Asteria Fleet Data Quality Hub — API Endpoint Catalog

## Connection

All endpoints are served from a single `base_url` (provided in `environment_access.md`). No authentication credentials are required for the read-only endpoints listed below. The Hub is a RESTful JSON API.

## Endpoint Reference

### GET /api/catalog/collections

Returns a JSON array of collection objects.

```
GET {{base_url}}/api/catalog/collections
```

Response shape (array of):
```json
{
  "collection_id": "string",
  "snapshot_ids": ["string", ...],
  "row_count": 0
}
```

### GET /api/catalog/schema

Returns field definitions for a collection.

```
GET {{base_url}}/api/catalog/schema?collection_id=<id>
```

Response shape (array of):
```json
{
  "name": "string",
  "type": "string",
  "nullable": true,
  "primary_key": true
}
```

### GET /api/contacts

Returns contact rows for a collection. Supports `?snapshot_id=...` and `?collection_id=...` query parameters.

```
GET {{base_url}}/api/contacts?collection_id=<id>&snapshot_id=<id>
```

Response returns all rows. Fields include: `row_id`, `person_identity_key`, `name`, `email`, `phone`, `city`, `region`, `consent_status`, `record_status`, `source_system`, and other collection-specific fields. Refer to the schema for the exact field list.

Source system values for contacts are one of: `HR Directory`, `Dispatch`, `Identity Registry`.

### GET /api/transactions/fuel

Returns fuel transaction rows for a collection. Supports `?snapshot_id=...` and `?collection_id=...`.

```
GET {{base_url}}/api/transactions/fuel?collection_id=<id>&snapshot_id=<id>
```

Key fields: `transaction_id`, `expected_fuel_type`, `description`, `volume`, `volume_unit`, `spend`, `spend_currency`, `asset_id`, `merchant_id`, `transaction_date`. Refer to the catalog schema for the full field list.

### GET /api/transactions/freight

Returns freight charge rows for a collection. Supports `?snapshot_id=...` and `?collection_id=...`.

```
GET {{base_url}}/api/transactions/freight?collection_id=<id>&snapshot_id=<id>
```

Key fields: `charge_id`, `expected_service_class`, `description`, `billed_weight`, `weight_unit`, `distance`, `distance_unit`, `spend`, `spend_currency`, `carrier_id`, `charge_date`. Refer to the catalog schema for the full field list.

### GET /api/maintenance/events

Returns maintenance event rows for a collection. Supports `?snapshot_id=...` and `?collection_id=...`.

```
GET {{base_url}}/api/maintenance/events?collection_id=<id>&snapshot_id=<id>
```

Key fields: `event_id`, `logical_event_id`, `asset_id`, `event_timestamp`, `odometer_reading`, `labor_hours`, `snapshot_id`. Refer to the catalog schema for the full field list.

### GET /api/reference/aliases

Returns the alias-to-category mapping used for fuel type and service class resolution.

```
GET {{base_url}}/api/reference/aliases
```

Response shape (array of):
```json
{
  "alias_text": "string",
  "canonical_category": "string"
}
```

For fuel: `canonical_category` is one of `BIODIESEL`, `DIESEL`, `ELECTRIC_CHARGE`, `PREMIUM_UNLEADED`, `UNLEADED`.
For freight: `canonical_category` is one of `EXPRESS`, `HAZMAT`, `OVERSIZE`, `REFRIGERATED`, `STANDARD`.

Aliases may serve both fuel and freight domains — filter by checking the canonical category against the expected domain's set.

### GET /api/reference/conversions

Returns unit conversion factors for physical measures.

```
GET {{base_url}}/api/reference/conversions
```

Response shape (array of):
```json
{
  "from_unit": "string",
  "to_unit": "string",
  "factor": 1.0
}
```

Multiply a value in `from_unit` by `factor` to obtain the equivalent in `to_unit`.

### GET /api/reference/fx

Returns currency exchange rates relative to a base currency.

```
GET {{base_url}}/api/reference/fx
```

Response shape (array of):
```json
{
  "from_currency": "string",
  "to_currency": "string",
  "rate": 1.0
}
```

Multiply an amount in `from_currency` by `rate` to obtain the equivalent in `to_currency`.

### GET /api/source-snapshots

Returns all snapshots across all collections, or filtered by `?collection_id=...`.

```
GET {{base_url}}/api/source-snapshots
GET {{base_url}}/api/source-snapshots?collection_id=<id>
```

Response shape (array of):
```json
{
  "snapshot_id": "string",
  "collection_id": "string",
  "status": "CERTIFIED | PROVISIONAL | STALE",
  "row_count": 0,
  "created_at": "string (ISO-8601)"
}
```

### POST /api/query

Authenticated read-only SQL-like query interface. Accepts a JSON body with a `query` string field.

```
POST {{base_url}}/api/query
Content-Type: application/json

{
  "query": "SELECT ... FROM ... WHERE ..."
}
```

Response shape:
```json
{
  "rows": [ ... ],
  "row_count": 0
}
```

The query language supports SELECT, FROM, WHERE, GROUP BY, ORDER BY, and LIMIT/OFFSET clauses. Table names correspond to collection and snapshot IDs. Use this endpoint when the domain-specific endpoints do not provide the necessary filtering, aggregation, or joins.

## Pagination

Domain-specific GET endpoints (contacts, fuel, freight, maintenance) return paginated results when a collection has more rows than a single response page. Check the response for pagination metadata (commonly `next` links or `offset`/`limit` fields). If pagination info is not present, the endpoint returns all rows in one response.

The POST /api/query endpoint also supports LIMIT/OFFSET for pagination.
