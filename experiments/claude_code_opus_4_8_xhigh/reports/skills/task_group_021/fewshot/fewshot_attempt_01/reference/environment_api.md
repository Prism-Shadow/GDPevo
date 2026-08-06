# Asteria Fleet Data Quality Hub — API & data model

Runtime base URL and bearer token live in the task's `environment_access.md`
(`GDPEVO_ENV_BASE_URL=...` and `AUTHORIZATION: Bearer ...`). Never hard-code them;
read them at runtime (`scripts/hub_client.py` does this for you). The service is
read-only.

## Two ways in

1. **`POST /api/query`** — the workhorse. Body `{"query": "<SQL SELECT>"}` →
   `{"columns":[...], "rows":[[...]], "row_count": N, "truncated": bool}`.
   - Read-only SQLite-flavored SELECT. Supports `WHERE`, `GROUP BY`, `COUNT`,
     `COUNT(DISTINCT ...)`, `SUM`, `MIN`, `MAX`, `ORDER BY`, `IN (...)`, joins.
   - **Hard 2000-row output cap** — if `truncated` is `true` you lost rows.
     Prefer to aggregate server-side; when you must pull rows, page with
     `LIMIT/OFFSET` + `ORDER BY` (see `Hub.sql_all`). `sqlite_master` is not queryable.
   - Bad SQL → HTTP 400 `{"error":"invalid query"}`. `{"error":"invalid request"}`
     means the body wasn't `{"query": ...}`.
2. **REST list endpoints** — raw rows with `?collection=<id>&limit=&offset=`
   pagination returning `{items, total, limit, offset}`. Note the param is
   `collection` (not `collection_id`). Endpoints: `/api/catalog/collections`,
   `/api/catalog/schema`, `/api/contacts`, `/api/transactions/fuel`,
   `/api/transactions/freight`, `/api/maintenance/events`, `/api/reference/aliases`,
   `/api/reference/conversions`, `/api/reference/fx`, `/api/source-snapshots`.

The SQL views expose the same data as the REST endpoints and are far easier to
reconcile with; use SQL for everything except a quick sanity peek.

## SQL views

| view | grain | key columns |
|------|-------|-------------|
| `v_source_snapshots` | one row per (collection, snapshot) | `collection_id, snapshot_id, source_system, snapshot_status {CERTIFIED,PROVISIONAL,STALE}, business_cutoff, created_at, row_count, checksum` |
| `v_contacts` | raw contact row | `collection_id, row_id, snapshot_id, source_system, source_record_id, person_or_org_name, email, phone, city, region, country, consent_status, record_status, verified_flag, business_updated_at, ingested_at, master_hint` |
| `v_fuel_transactions` | raw fuel row | `collection_id, transaction_id, snapshot_id, asset_id, merchant_id, purchased_at, expected_fuel_type, purchased_description, quantity, quantity_unit, currency, amount, record_status, business_updated_at, ingested_at` |
| `v_freight_charges` | raw freight row | `collection_id, charge_id, snapshot_id, invoice_id, invoice_line_no, carrier_id, lane_id, service_date, expected_service_class, description, billed_weight, weight_unit, distance, distance_unit, currency, amount, record_status, business_updated_at, ingested_at` |
| `v_maintenance_events` | raw maintenance row | `collection_id, snapshot_id, event_id, work_order_id, asset_id, event_type, event_time_raw, odometer_value, odometer_unit, labor_hours, parts_cost, currency, technician_id, event_status, business_updated_at, ingested_at` |
| `v_reference_aliases` | alias→canonical map | `domain {fuel,freight}, alias_id, alias_text, canonical_value, valid_from, valid_to, reference_status {ACTIVE,INACTIVE,PROVISIONAL}, published_at` |
| `v_unit_conversions` | unit factor | `kind {volume,weight,distance,odometer}, from_unit, to_unit, factor, valid_from, valid_to, precision` |
| `v_fx_rates` | fx rate | `rate_date, currency, usd_per_unit, rate_status {CERTIFIED,PROVISIONAL}, published_at` |

## Snapshot model (the heart of "reconcile overlapping source records")

Each collection has several snapshots. A logical entity (a `transaction_id` /
`charge_id` / `event_id`, or a person cluster) can appear in more than one
snapshot — that is the "overlap" every task asks you to resolve.

- The **authoritative snapshot** is `"{collection_id}-certified"`
  (`snapshot_status = CERTIFIED`). For fuel/freight/maintenance it is a single
  certified snapshot; the answer's `authoritative_snapshot_id` equals it.
- Contact collections carry **three** source systems across snapshots (two
  `CERTIFIED`, one `PROVISIONAL`) and are reconciled by *field-level precedence*
  across systems, not by picking one snapshot.
- **Duplicate resolution:** when a logical id appears in >1 snapshot, retain the
  occurrence from the certified/authoritative snapshot; the others are the
  duplicate raw rows. `raw_row_count` counts every raw occurrence across snapshots;
  `logical_*_count` counts distinct ids; `duplicate_raw_count = raw − logical`.
- Ignore `STALE` snapshots and any snapshot whose `created_at` is after the
  scope's `as_of`, when those fields are in play.

## Normalization inputs

- **Units** — `v_unit_conversions`: multiply the source value by `factor` for the
  matching `(kind, from_unit → to_unit)` where the canonical `to_unit` comes from
  case_scope (`L`, `KG`, `KM`). `odometer` is its own `kind` (distinct precision).
- **Currency** — `v_fx_rates`: `usd = amount * usd_per_unit` for the row's
  `(currency, rate_date = the transaction/charge business date)`. Prefer the
  `CERTIFIED` rate over `PROVISIONAL`; USD is 1.0.
- **Category recognition** — `v_reference_aliases`: normalize the free-text
  description and match it against `alias_text` within the row's `domain`,
  honoring temporal effectivity and status (see reconciliation_pipeline.md).
