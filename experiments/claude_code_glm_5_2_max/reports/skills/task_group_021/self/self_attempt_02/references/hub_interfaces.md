# Hub interfaces

## Auth & base URL
- Read `environment_access.md` for the base URL (e.g. an `GDPEVO_ENV_BASE_URL`/`<TASK_ENV_BASE_URL>` value), the `Authorization: Bearer <token>` credential, and the allow-list of endpoints.
- Call form: `GET|POST <BASE_URL>/api/...` with the `Authorization` header set to that bearer value.
- Use ONLY endpoints listed in `environment_access.md`. Do not invent paths.

## Discovery

### `GET /api/catalog/collections`
- No filter required. Paginates as `{items, limit, offset, total}` (use `limit`/`offset`).
- Item fields: `collection_id`, `family` (`fuel`|`freight`|`contacts`|`maintenance`|`quote`|`telematics`), `source_systems`, `approximate_record_count`, `time_start`, `time_end`, `description`.
- Use `family` to select the reconciliation variant; confirm the task's `collection_id` exists.

### `GET /api/catalog/schema`
- No filter required. Returns `{views:[{name, fields:[{name, type, meaning}]}]}`.
- Logical views: `v_contacts`, `v_fuel_transactions`, `v_freight_charges`, `v_maintenance_events`, `v_source_snapshots`, `v_fx_rates`, `v_reference_aliases`, `v_unit_conversions`.

## Primary query — `POST /api/query` (SQL over views)
- Body: `{"query": "<SELECT ... FROM <view> ...>"}`.
- Response: `{columns:[...], row_count:N, rows:[[...],...], truncated:bool}`. `rows` are positional arrays aligned with `columns`.
- Supports `WHERE`, `LIMIT n`, `OFFSET m`, aggregations (`COUNT`, `SUM`), and `ORDER BY`.
- `information_schema` is NOT available — query the views directly.
- Page large results with `LIMIT`/`OFFSET` until `row_count` is below the page size and `truncated` is false. This is the reliable way to read transaction/contact/maintenance/snapshot data; prefer it over the per-domain GET endpoints.
- Strings in `WHERE` need single quotes (e.g., `WHERE collection_id='fuel_purchases_2026_01'`).

## Reference data (GET, paginated `{items, limit, offset, total}`)

### `GET /api/reference/fx`
- No filter required. Fields: `rate_date`, `currency`, `usd_per_unit`, `rate_status`, `published_at`.
- Use `usd_per_unit` to convert an amount in `currency` to USD for a given date (pick the rate with `rate_date` ≤ transaction date and acceptable `rate_status`).

### `GET /api/reference/aliases?domain=<fuel|freight|...>`
- `domain` filter REQUIRED (omitting it yields `{"error":"invalid filter"}`).
- Fields: `domain`, `alias_id`, `alias_text`, `canonical_value`, `valid_from`, `valid_to`, `reference_status`, `published_at`.
- Maps a free-text `description` to a canonical category by matching `alias_text` → `canonical_value`. Respect `valid_from`/`valid_to` and `reference_status`.

### `GET /api/reference/conversions?kind=<volume|weight|distance|...>`
- `kind` filter REQUIRED. Fields: `kind`, `from_unit`, `to_unit`, `factor`, `valid_from`, `valid_to`, `precision`.
- Multiply the source value by `factor` to convert `from_unit` → `to_unit`. Select the row whose `to_unit` is the scope's canonical unit (`L`, `KG`, `KM`).

## Per-domain GET endpoints
`GET /api/contacts`, `/api/transactions/fuel`, `/api/transactions/freight`, `/api/maintenance/events`, `/api/source-snapshots` are listed in `environment_access.md`. They require a filter (the natural-key pattern used by the reference endpoints is `domain=`/`kind=`; discover the accepted key by probing if needed). In practice `POST /api/query` over the views covers all of these and is the reliable primary path.

## View field reference (from `/api/catalog/schema`)
- **`v_fuel_transactions`**: collection_id, transaction_id, snapshot_id, asset_id, merchant_id, purchased_at, expected_fuel_type, purchased_description, quantity, quantity_unit, currency, amount, record_status, business_updated_at, ingested_at
- **`v_freight_charges`**: collection_id, charge_id, snapshot_id, invoice_id, invoice_line_no, carrier_id, lane_id, service_date, expected_service_class, description, billed_weight, weight_unit, distance, distance_unit, currency, amount, record_status, business_updated_at, ingested_at
- **`v_contacts`**: collection_id, row_id, snapshot_id, source_system, source_record_id, person_or_org_name, email, phone, city, region, country, consent_status, record_status, verified_flag, business_updated_at, ingested_at, master_hint
- **`v_maintenance_events`**: collection_id, snapshot_id, event_id, work_order_id, asset_id, event_type, event_time_raw, odometer_value, odometer_unit, labor_hours, parts_cost, currency, technician_id, event_status, business_updated_at, ingested_at
- **`v_source_snapshots`**: collection_id, snapshot_id, source_system, snapshot_status, business_cutoff, created_at, ingested_at, row_count, checksum
- **`v_fx_rates`**: rate_date, currency, usd_per_unit, rate_status, published_at
- **`v_reference_aliases`**: domain, alias_id, alias_text, canonical_value, valid_from, valid_to, reference_status, published_at
- **`v_unit_conversions`**: kind, from_unit, to_unit, factor, valid_from, valid_to, precision

## ID formats encountered
`PAR-C#####`, `FIE-C#####` (contact row IDs); `AST-####` (assets); `ME-Q1-######` (maintenance events); `FT-YYYYMM-######` (fuel transactions); `FC-YYYYMM-######-######` (freight charges); `CAR-###` (carriers); `FUA-###`, `FRA-###` (reference alias IDs); `FOCUS-###`, `CONTROL-###` (focus/control case IDs); cluster IDs of the form `<collection_id>-cluster-###`.
