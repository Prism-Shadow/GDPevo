# Hub access mechanics

All network access comes from `environment_access.md`: the base URL (`GDPEVO_ENV_BASE_URL` / `<TASK_ENV_BASE_URL>`), the `Authorization` bearer token, and the allowed-endpoint list. Do not hardcode these — read them each run. The mechanics below are stable API behavior.

## Auth
Every request carries `Authorization: Bearer <token>` (the read credential from environment_access.md). Every endpoint is read-only. The same bearer token authorizes both the GET endpoints and `POST /api/query`.

## Endpoints

### GET /api/catalog/collections
Returns `{"items":[{collection_id, family, source_systems, approximate_record_count, time_start, time_end, description}, ...]}`. No filter required. Use to confirm the target collection and its family / source systems.

### GET /api/catalog/schema
Returns `{"views":[{name, fields:[{name, type, meaning}, ...]}, ...]}`. The view `name`s are the table names usable in `/api/query`. Read this first to learn each view's fields; the `meaning` text documents each field.

### GET /api/source-snapshots
Requires the filter `?collection=<collection_id>` (the query param is `collection`, **not** `collection_id`). Returns `{"items":[{snapshot_id, snapshot_status, collection_id, source_system, business_cutoff, created_at, ingested_at, row_count, checksum}, ...]}`.
- `snapshot_status` ∈ {CERTIFIED, PROVISIONAL, STALE}.
- The **authoritative** snapshot is the CERTIFIED one matching the business cutoff; its `snapshot_id` (typically `<collection>-certified`) is reported as `authoritative_snapshot_id` and used to resolve overlapping records.

### GET row endpoints
Each returns `{"items":[...], "limit", "offset", "total"}` — offset-based pagination. Filter with `?collection=<collection_id>`; page with `?limit=<n>&offset=<n>` until `offset >= total`.
- `/api/contacts` → v_contacts rows
- `/api/transactions/fuel` → v_fuel_transactions rows
- `/api/transactions/freight` → v_freight_charges rows
- `/api/maintenance/events` → v_maintenance_events rows
- `/api/reference/aliases` → v_reference_aliases rows
- `/api/reference/conversions` → v_unit_conversions rows
- `/api/reference/fx` → v_fx_rates rows

### POST /api/query  (the workhorse)
- Body: `{"query": "<SQL>"}` — a single SQL **string**. The envelope key is `query` and its value is a SQL string (not an object). Sending `{"view":...}`, `{"from":...}`, or an object as the query value returns `invalid query`.
- Query the views by name: `v_contacts`, `v_fuel_transactions`, `v_freight_charges`, `v_maintenance_events`, `v_reference_aliases`, `v_unit_conversions`, `v_fx_rates`, `v_source_snapshots`.
- Supports `SELECT` projection, `WHERE`, `ORDER BY`, and `LIMIT`/`OFFSET`. String-literal filters use single quotes, e.g. `WHERE collection_id='fuel_purchases_2026_01'`.
- Response: `{"columns":[...], "row_count":<n>, "rows":[[...], ...], "truncated":<bool>}`. `rows` is an array of arrays, positional per `columns`. `truncated:true` means the result was cut — re-issue with a smaller LIMIT and page through OFFSET until `row_count` drops below your page size.

Use `/api/query` for filtered / joined / aggregated reads (e.g. only the authoritative snapshot's rows, only a focus asset's rows, alias lookups, snapshot metadata). Use the GET endpoints for simple full-collection pulls.

## Pagination rule (never sample)
Collections are larger than one page. Always loop until exhausted:
- GETs: increment `offset` by `limit` while `offset < total`.
- `/api/query`: `LIMIT <page> OFFSET <k>` loop; stop when a page returns fewer than `limit` rows (and `truncated` is false / you've paged past the end).

A missed page means a wrong count, a wrong total, or a wrong ranking. Page until dry.
