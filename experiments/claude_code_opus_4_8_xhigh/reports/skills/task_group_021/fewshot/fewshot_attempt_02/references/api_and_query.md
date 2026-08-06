# Hub API & SQL query reference

All access is read-only. The base URL and bearer token live in
`environment_access.md` (shipped with each task). Read them at runtime — never
hard-code — e.g. `Hub.from_env()` in `scripts/hub_client.py`. Send the token as
`Authorization: Bearer <token>` on every request.

## Endpoints

REST resources return a paginated envelope `{"items":[...], "total", "limit",
"offset"}`. Follow `offset`/`limit` until you have `total` rows (the helper's
`hub.get()` does this automatically). Some collections are larger than one page.

| Endpoint | Purpose |
|---|---|
| `GET /api/catalog/collections` | List collections: `collection_id`, `family` (contacts/fuel/freight/maintenance/…), `source_systems`, `approximate_record_count`, time range. |
| `GET /api/catalog/schema` | Logical view definitions (field names + meanings). |
| `GET /api/source-snapshots?collection=<id>` | Snapshots for a collection: `snapshot_id`, `snapshot_status` (CERTIFIED/PROVISIONAL), `source_system`, `business_cutoff`, `row_count`, `checksum`. **Filter param is `collection` (not `collection_id`)**; omitting it returns 400. |
| `GET /api/contacts` | Raw contact rows. |
| `GET /api/transactions/fuel` / `GET /api/transactions/freight` | Raw fuel / freight rows. |
| `GET /api/maintenance/events` | Raw maintenance events. |
| `GET /api/reference/aliases` | Category alias table (fuel/freight description → canonical class). |
| `GET /api/reference/conversions` | Unit-conversion factors. |
| `GET /api/reference/fx` | FX rates (USD per unit) by date/status. |
| `POST /api/query` | Read-only SQL over the logical views (below). |

## The SQL endpoint — your primary tool

`POST /api/query` with body `{"query":"SELECT ..."}` → `{"columns":[...],
"rows":[[...]], "row_count":N, "truncated":bool}`. It is SQLite-flavoured
(supports `GROUP BY`, `GROUP_CONCAT`, `COUNT`, `MIN/MAX`, `CASE`, `JOIN`,
subqueries, `LIKE`, `LOWER`, etc.).

**It returns the full result set — no row cap observed** (e.g. 1350 rows,
`truncated:false`). Prefer SQL over paging REST endpoints for every count,
join, and aggregation. Do the reconciliation math with SQL and only pull raw
rows when you need to inspect individual records.

Every row-bearing view carries `collection_id` and `snapshot_id`; **always
filter by the scoped `collection_id`** (the hub holds many collections at once).

## Logical views (from `/api/catalog/schema`)

- **`v_source_snapshots`**: `collection_id, snapshot_id, source_system, snapshot_status, business_cutoff, created_at, ingested_at, row_count, checksum`
- **`v_contacts`**: `collection_id, row_id, snapshot_id, source_system, source_record_id, person_or_org_name, email, phone, city, region, country, consent_status, record_status, verified_flag, business_updated_at, ingested_at, master_hint`
- **`v_fuel_transactions`**: `collection_id, transaction_id, snapshot_id, asset_id, merchant_id, purchased_at, expected_fuel_type, purchased_description, quantity, quantity_unit, currency, amount, record_status, business_updated_at, ingested_at`
- **`v_freight_charges`**: `collection_id, charge_id, snapshot_id, invoice_id, invoice_line_no, carrier_id, lane_id, service_date, expected_service_class, description, billed_weight, weight_unit, distance, distance_unit, currency, amount, record_status, business_updated_at, ingested_at`
- **`v_maintenance_events`**: `collection_id, snapshot_id, event_id, work_order_id, asset_id, event_type, event_time_raw, odometer_value, odometer_unit, labor_hours, parts_cost, currency, technician_id, event_status, business_updated_at, ingested_at`
- **`v_reference_aliases`**: `domain (fuel/freight), alias_id, alias_text, canonical_value, valid_from, valid_to, reference_status (ACTIVE/INACTIVE/PROVISIONAL), published_at`
- **`v_unit_conversions`**: `kind (volume/weight/distance/odometer), from_unit, to_unit, factor, valid_from, valid_to, precision`
- **`v_fx_rates`**: `rate_date, currency, usd_per_unit, rate_status (CERTIFIED/PROVISIONAL), published_at`

## Reference data (stable environment facts, not task answers)

**Unit conversions** (`to_unit` is always the canonical unit):

| kind | from → to | factor |
|---|---|---|
| volume | US_GAL → L | 3.785411784 |
| volume | IMP_GAL → L | 4.54609 |
| volume | L → L | 1.0 |
| weight | LB → KG | 0.45359237 |
| weight | KG → KG | 1.0 |
| distance / odometer | MI → KM | 1.609344 |
| distance / odometer | KM → KM | 1.0 |

Do not memorise these — read `v_unit_conversions` for the scoped task and honour
its `precision` column. FX: use `v_fx_rates` with `rate_status='CERTIFIED'`, the
row's transaction/service **business date**, and `usd_per_unit`
(`usd = amount * usd_per_unit`). Ignore PROVISIONAL FX rates.

**Category aliases** map a free-text description to a canonical class. `fuel`
canonical values: DIESEL, UNLEADED, PREMIUM_UNLEADED, BIODIESEL,
ELECTRIC_CHARGE. `freight`: STANDARD, EXPRESS, REFRIGERATED, HAZMAT, OVERSIZE.
Only `ACTIVE` aliases whose validity window covers the cutoff are authoritative;
a single `alias_text` mapping to two different canonical values is an *ambiguous*
alias; `PROVISIONAL` aliases are not yet authoritative. Read the live table each
time — the alias set can differ per task.
