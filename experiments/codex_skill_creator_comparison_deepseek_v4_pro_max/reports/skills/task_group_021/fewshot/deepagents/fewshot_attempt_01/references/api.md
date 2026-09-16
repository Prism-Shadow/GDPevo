# Asteria Fleet Data Quality Hub API Reference

The task supplies a base URL in `environment_access.md`. Build every request URL
by appending the endpoint path to that base. All endpoints return JSON.

## Discovery

### GET /api/catalog/collections
Returns the list of available collections. Each object has at least `id` and
`name` fields. Identify the target collection from the `case_scope.json`
`collection_id`.

### GET /api/catalog/schema
Returns the field definitions for collections. Look up the target collection
to understand field names, types, and constraints.

## Source snapshots

### GET /api/source-snapshots
Returns snapshots keyed by collection. A typical collection has two snapshots:

- `{collection}-certified` — authoritative source
- `{collection}-provisional` — supplementary data

Resolve duplicates by preferring the certified copy. Count raw rows across all
snapshots; logical count after deduplication; duplicate count = raw - logical.

## Domain records

| Endpoint | Typical row ID prefix | Notes |
|---|---|---|
| GET /api/contacts | PAR-C or FIE-C | Contact/roster records with name, email, phone, city, region, consent, status |
| GET /api/transactions/fuel | FT- | Fuel purchase records with asset, merchant, fuel category, quantity, amount, currency |
| GET /api/transactions/freight | FC- | Freight charge records with carrier, service-class alias, weight, distance, amount |
| GET /api/maintenance/events | ME-Q1- | Maintenance events with asset, timestamp, odometer, labor hours, event type |

All domain endpoints return arrays of record objects. The response may be
paginated (check for a `next` link or similar pagination envelope).

**Fuel records** include a `description` field that must be mapped to a
recognized fuel category via `/api/reference/aliases`. Records whose description
matches zero aliases (unrecognized) or more than one alias (ambiguous) are
quarantined. Records whose mapped category differs from the expected category
are mismatches.

**Freight records** include a `service_class` field that must be mapped via
`/api/reference/aliases`. Quarantine applies to unrecognized aliases, ambiguous
aliases, non-positive weight, and non-positive distance. Mismatches are records
where the recognized class differs from the expected class.

**Maintenance events** include timestamp, odometer reading, and labor hours.
Filter invalid records: missing or unparseable timestamp, odometer outside
valid range, negative or extreme labor hours. Odometer regressions (a later
event has a lower reading than an earlier one for the same asset) are tracked
separately — they remain in the valid set but are flagged.

**Contact/roster records** come from multiple source systems (e.g., HR Directory,
Dispatch, Identity Registry). Records sharing the same logical identity form
duplicate clusters. Resolve fields by source-system precedence (defined in the
case scope or inferred from the answer template). Quarantine records with no
usable contact channel (email or phone).

## Reference tables

### GET /api/reference/aliases
Returns alias-to-canonical-category mappings. Used by fuel and freight domains
to map free-text descriptions to recognized fuel types or service classes.
 Each entry has an `alias_id` (matching patterns like FUA-NNN or FRA-NNN) and a canonical target.

### GET /api/reference/conversions
Returns unit conversion factors. Use when the source data uses non-canonical
units. Apply to normalize quantities before aggregation.

### GET /api/reference/fx
Returns foreign-exchange rates. Use when source amounts are not in the base
currency (typically USD). Apply the rate to convert before aggregation.

## Query interface

### POST /api/query

Sends a read-only SQL query. The request body is JSON with at minimum a
`query` field. The response is a JSON array of result rows.

The query endpoint requires authentication. Check `environment_access.md` for
credentials — they may be a token, API key, or empty.

Use `POST /api/query` when you need filtered subsets (by asset, by time range,
by region), aggregations (COUNT, SUM), or groupings (GROUP BY). This is
essential for computing totals and rankings without pulling all raw records
into context.

**Important**: The query endpoint is read-only. Use `SELECT` statements only.

## Numeric normalization

Apply conversions and FX rates before rounding:

1. Convert source unit to canonical unit using `/api/reference/conversions`.
2. Convert source currency to base currency using `/api/reference/fx`.
3. Round to 2 decimal places for all monetary and physical totals.
4. Round quarantine_rate (and similar rates) to 4 decimal places.
