# Environment access — Asteria Fleet Data Quality Hub

## Credentials (never hard-code — read them at runtime)
The task ships an `environment_access.md` in the working directory. It contains:
- `GDPEVO_ENV_BASE_URL=<base url>` (e.g. `http://task-env:9021/`)
- `AUTHORIZATION: Bearer <token>` (e.g. `Bearer asteria-read-...`)

The base URL and token differ per environment/run, so always parse them from that
file. `scripts/hub_client.py` does this for you (`HubClient()` needs no arguments).
Every request must send the `Authorization: Bearer <token>` header. `curl` is often
absent in the sandbox — use Python `urllib` (the helper) instead.

## Endpoints
All GET unless noted. Read-only.

| Endpoint | Filter param | Notes |
|---|---|---|
| `GET /api/catalog/collections` | — | lists every `collection_id`, `family`, `source_systems`, `approximate_record_count`, time window |
| `GET /api/catalog/schema` | — | logical views + field meanings (see `data_model.md`) |
| `GET /api/source-snapshots` | `?collection=<collection_id>` | snapshots for a collection: `snapshot_status` (CERTIFIED/PROVISIONAL), `source_system`, `business_cutoff`, `row_count`, `checksum` |
| `GET /api/contacts` | `?collection=<id>` | raw contact rows (paginated) |
| `GET /api/transactions/fuel` | `?collection=<id>` | raw fuel rows (paginated) |
| `GET /api/transactions/freight` | `?collection=<id>` | raw freight rows (paginated) |
| `GET /api/maintenance/events` | `?collection=<id>` | raw maintenance rows (paginated) |
| `GET /api/reference/aliases` | `?domain=<fuel\|freight\|...>` | alias→canonical mappings |
| `GET /api/reference/conversions` | `?kind=<volume\|weight\|distance\|odometer>` | unit factors |
| `GET /api/reference/fx` | — | daily USD rates by currency + status |
| `POST /api/query` | body `{"query":"<SQL>"}` | **primary bulk interface** — SQL over the logical views |

**Filter names are strict.** Wrong/missing filters return `400 {"error":"invalid filter"}`.
Confirmed working: `source-snapshots?collection=`, `aliases?domain=`, `conversions?kind=`.

## The query interface (use this for everything analytical)
`POST /api/query` with `{"query": "<SQL>"}` returns
`{"columns":[...], "rows":[[...]], "row_count":N, "truncated":bool}`.

- It is SQLite-dialect SQL over the **views only** (see `data_model.md`). You cannot
  read `sqlite_master` or non-view tables (`400 {"error":"invalid query"}`).
- Results are **not** capped at 100 — a full-collection `SELECT` (1000s of rows)
  returns complete with `truncated:false`. Still, always check the `truncated` flag
  and prefer aggregating server-side (`GROUP BY`, `count(*)`) over pulling raw rows.
- Prefer `/api/query` over the REST list endpoints for analysis: one call, full set,
  and you can join views. Use the REST endpoints mainly to confirm counts.

## Pagination (REST list endpoints)
List endpoints return `{"items":[...], "limit":L, "offset":O, "total":T}` and default
to `limit=100`. Collections legitimately span multiple pages (maintenance/fuel/freight
are >1000 rows), so **never trust a single page's `items` as the whole collection** —
page with `&limit=&offset=` until `offset >= total`, or just use `/api/query`.
`HubClient.get_all(path)` does the paging for you.

## Recommended workflow
1. `HubClient()` (auto-reads creds).
2. Read `case_scope.json` (collection_id, cutoff, focus/anchor lists, thresholds).
3. `GET /api/source-snapshots?collection=<id>` → identify the authoritative snapshot
   (the `*-certified` one; `snapshot_status = CERTIFIED`).
4. Pull the scoped rows with `/api/query`, reconcile in Python (see `reconciliation.md`).
5. Emit JSON matching `answer_template.json` exactly (see `output_contract.md`).
