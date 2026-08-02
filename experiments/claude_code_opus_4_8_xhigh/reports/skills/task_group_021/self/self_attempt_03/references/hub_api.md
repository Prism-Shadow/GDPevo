# Fleet Data Quality Hub — API & query cheatsheet

Runtime connection details live in `environment_access.md` (base URL +
`Authorization: Bearer <token>`; token is environment-specific, e.g. `asteria-read-021`).
All endpoints are **read-only**. There is no `curl` in some environments — a tiny Python
`urllib` client works fine.

## REST endpoints

| Endpoint | Notes |
|---|---|
| `GET /api/catalog/collections` | All collections: `collection_id`, `family`, `source_systems`, `time_start/end`, `approximate_record_count`. Paged (`limit/offset/total`). |
| `GET /api/catalog/schema` | Logical views + fields (see below). |
| `GET /api/contacts` | Contact rows (also reachable as view `v_contacts`). |
| `GET /api/transactions/fuel` | Fuel rows (view `v_fuel_transactions`). |
| `GET /api/transactions/freight` | Freight rows (view `v_freight_charges`). |
| `GET /api/maintenance/events` | Maintenance rows (view `v_maintenance_events`). |
| `GET /api/reference/aliases?domain=<fuel\|freight>` | Category alias table. **`domain` required.** |
| `GET /api/reference/conversions?kind=<volume\|weight\|distance\|odometer>` | Unit factors. **`kind` required.** |
| `GET /api/reference/fx` | FX rates; accepts `?limit=`. |
| `GET /api/source-snapshots?collection=<collection_id>` | Snapshots for a collection. **`collection` required.** |
| `POST /api/query` | SQL over the views (below). |

Reference/snapshot endpoints return `400 {"error":"invalid filter"}` if you omit the
required filter param. Note the param name is `collection` (not `collection_id`) for
snapshots.

## `POST /api/query`

Body: `{"query":"SELECT ... FROM <view> WHERE ..."}` (key **must** be `query`; `sql`/
`statement` → `400 invalid request`). Response:
`{"columns":[...],"rows":[[...]],"row_count":N,"truncated":bool}`.

- SQLite-flavored SQL: `WHERE`, `GROUP BY`, `HAVING`, `ORDER BY`, `DISTINCT`, `COUNT`,
  `SUM`, `MIN`/`MAX`, `LOWER`, `TRIM`, `IN`, joins across views.
- **Hard cap 2000 rows per response**; `"truncated": true` when there is more. Prefer
  server-side aggregation (`GROUP BY`) for counts/sums; paginate with `LIMIT/OFFSET` over
  a stable `ORDER BY` when you truly need every row. A raw collection can exceed 2000 rows
  across snapshots, so a single unfiltered `SELECT *` is almost never complete.

## Logical views and their fields

- `v_contacts`: `collection_id, row_id, snapshot_id, source_system, source_record_id,
  person_or_org_name, email, phone, city, region, country, consent_status, record_status,
  verified_flag, business_updated_at, ingested_at, master_hint`
- `v_fuel_transactions`: `collection_id, transaction_id, snapshot_id, asset_id, merchant_id,
  purchased_at, expected_fuel_type, purchased_description, quantity, quantity_unit, currency,
  amount, record_status, business_updated_at, ingested_at`
- `v_freight_charges`: `collection_id, charge_id, snapshot_id, invoice_id, invoice_line_no,
  carrier_id, lane_id, service_date, expected_service_class, description, billed_weight,
  weight_unit, distance, distance_unit, currency, amount, record_status, business_updated_at,
  ingested_at`
- `v_maintenance_events`: `collection_id, snapshot_id, event_id, work_order_id, asset_id,
  event_type, event_time_raw, odometer_value, odometer_unit, labor_hours, parts_cost,
  currency, technician_id, event_status, business_updated_at, ingested_at`
- `v_source_snapshots`: `collection_id, snapshot_id, source_system, snapshot_status,
  business_cutoff, created_at, ingested_at, row_count, checksum`
- `v_reference_aliases`: `domain, alias_id, alias_text, canonical_value, valid_from,
  valid_to, reference_status, published_at`
- `v_unit_conversions`: `kind, from_unit, to_unit, factor, valid_from, valid_to, precision`
- `v_fx_rates`: `rate_date, currency, usd_per_unit, rate_status, published_at`

## Observed value domains (verify per collection; ranges, not answers)

- `snapshot_status`: `CERTIFIED`, `PROVISIONAL`, `STALE`. Transaction/event collections
  usually have one CERTIFIED "ledger/ERP" snapshot + a PROVISIONAL "feed/mobile" snapshot;
  contact collections have one snapshot per source system (mixed statuses) that get merged.
- `reference_status` (aliases): `ACTIVE`, `PROVISIONAL`, `INACTIVE`, with `valid_from`/
  `valid_to` windows. Only aliases effective at the business date recognize a category.
- `rate_status` (fx): `CERTIFIED`, `PROVISIONAL` — multiple rows per (currency, date);
  prefer CERTIFIED, latest `published_at`.
- Contacts: `record_status ∈ {ACTIVE, INACTIVE}`; `consent_status ∈ {GRANTED, PENDING,
  DENIED, UNKNOWN}`; `verified_flag ∈ {0,1}`; `master_hint` like `MH-####` or null.
- Maintenance: `event_status ∈ {OPEN, COMPLETED, CLOSED}`; `odometer_unit ∈ {KM, MI}`.
- Units seen: fuel `quantity_unit ∈ {L, US_GAL, IMP_GAL}`; freight `weight_unit ∈ {KG, LB}`,
  `distance_unit ∈ {KM, MI}`; currencies `{USD, EUR, GBP, CAD}`.

## Reference constants (stable conversion factors → canonical unit)

- volume → **L**: `L` 1.0; `US_GAL` 3.785411784; `IMP_GAL` 4.54609.
- weight → **KG**: `KG` 1.0; `LB` 0.45359237.
- distance/odometer → **KM**: `KM` 1.0; `MI` 1.609344.

Always re-read the tables at runtime (factors carry `valid_from/valid_to` and a
`precision`); do not assume this list is exhaustive for a new environment.
