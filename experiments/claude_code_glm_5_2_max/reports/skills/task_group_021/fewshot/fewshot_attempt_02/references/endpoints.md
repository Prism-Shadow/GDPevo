# Asteria Fleet Data Quality Hub — endpoint catalog

All access comes from `environment_access.md`: a base URL and a bearer token. Use only the allow-listed endpoints. Everything is read-only; `POST /api/query` is a read-only query interface that still requires the bearer credential.

## Discovery endpoints (call these first, every task)

### GET /api/catalog/collections
Lists collections. Each has a stable `collection_id` and references to its snapshots. Use it to confirm `case_scope.collection_id` exists and to find snapshot IDs / row counts.

### GET /api/catalog/schema
Field schema for a collection (column names, types, per-source-system fields). **Call this to learn field names at runtime** — do not hardcode them. It tells you which fields carry the expected class, the raw description/alias, the measures, the timestamps, and the source-system provenance.

### GET /api/source-snapshots
Snapshot metadata per collection: `snapshot_id`, `collection_id`, `status` (`CERTIFIED` | `PROVISIONAL` | `STALE`), `as_of`, `row_count`. The `CERTIFIED` snapshot is authoritative. If none is CERTIFIED, prefer the newest non-STALE snapshot and note the fallback.

## Record endpoints (paginated — always page to the end)

| Endpoint | Records | Used by |
|---|---|---|
| GET /api/transactions/fuel | fuel purchases | fuel ledger audit |
| GET /api/transactions/freight | freight charges | freight accrual close |
| GET /api/maintenance/events | maintenance log events | maintenance integrity cert |
| GET /api/contacts | contact records | partner onboarding / field-service roster |

Collections are explicitly larger than one page. Follow the page token / `next` cursor / offset until exhausted. Cross-reference each row with `/api/source-snapshots` to know which snapshot it came from (needed for survivorship).

## Reference endpoints (lookup tables — fetch once, hold in memory)

### GET /api/reference/aliases
Maps raw descriptions / merchant names / external aliases → canonical category (fuel_type / service_class). A raw value may map to **one**, **zero** (unrecognized), or **more than one** (ambiguous) canonical category. Use this to resolve each record's recognized class and to drive mismatch / unrecognized / ambiguous classification.

### GET /api/reference/conversions
Unit conversion factors. Apply to bring measures to the canonical unit declared in `case_scope` (volume → L, weight → KG, distance → KM).

### GET /api/reference/fx
FX rates to the base currency (USD). Convert each amount using the rate valid on the record's business date.

## Query endpoint

### POST /api/query
Authenticated read-only query interface. Use it to:
- filter the underlying records by collection and cutoff (often faster than paging the raw endpoint for large scopes),
- look up evidence for individual scoped IDs when inferring control codes,
- resolve focus clusters / control-case anchors / focus-people anchors to their member rows.

Send the bearer token from `environment_access.md`. Treat results as paginated where applicable.

## Discovery checklist
1. `GET /api/catalog/collections` → confirm the collection.
2. `GET /api/source-snapshots` → identify the CERTIFIED (authoritative) snapshot.
3. `GET /api/catalog/schema` → learn field names.
4. Fetch + paginate the record endpoint (and/or `POST /api/query`), scoped to the cutoff.
5. Fetch the three reference tables once and hold them in memory.
