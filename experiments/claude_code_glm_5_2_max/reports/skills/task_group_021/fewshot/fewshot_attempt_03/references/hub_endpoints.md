# Hub endpoints

All access details (base URL, bearer token, allowed endpoints) come from
`environment_access.md` at runtime — read them; do not hardcode. Call only the
endpoints the file lists. Send the documented `Authorization` header on every
request, and substitute the file's base URL for `<TASK_ENV_BASE_URL>`.

## Endpoint roles

| Endpoint | Role |
|---|---|
| `GET /api/catalog/collections` | Collection catalog; resolve `collection_id` → snapshots, row counts, status. |
| `GET /api/catalog/schema` | Field definitions per collection type. |
| `GET /api/source-snapshots` | Snapshot metadata: id, status (`CERTIFIED`/`PROVISIONAL`/`STALE`), row count, timestamps. |
| `GET /api/contacts` | Raw contact / master rows (partner onboarding, field-service roster). |
| `GET /api/transactions/fuel` | Raw fuel-purchase rows. |
| `GET /api/transactions/freight` | Raw freight-charge rows. |
| `GET /api/maintenance/events` | Raw maintenance-event rows. |
| `GET /api/reference/aliases` | Alias → canonical category / service-class mapping. |
| `GET /api/reference/conversions` | Unit conversion factors. |
| `GET /api/reference/fx` | Currency → base-currency FX rates. |
| `POST /api/query` | Authenticated scoped/paged query over a collection. |

If `environment_access.md` lists a different or smaller endpoint set for a
given task, use exactly that set — do not call endpoints it does not permit.

## Authoritative snapshot

The snapshot with status `CERTIFIED` (id conventionally
`<collection_id>-certified`) is authoritative. Resolve overlapping records
against it; when the contract asks which occurrence was retained, report the
authoritative-snapshot id. `PROVISIONAL` / `STALE` snapshots supply duplicate
rows to collapse. If the contract exposes a `snapshot_status` field, echo the
authoritative snapshot's status.

## Paging

Collections are larger than one response page. When using `POST /api/query`,
follow the hub's pagination until the result is exhausted; never assume a
single page is complete. The direct `GET` domain endpoints may likewise page —
read all pages before reconciling.

## Reference tables

Load aliases, conversions, and fx up front:

- **aliases** resolve free-text descriptions to exactly one canonical
  category / service class. Zero match → unrecognized; >1 match → ambiguous;
  both lead to quarantine.
- **conversions** map each raw unit to the canonical unit declared in
  `case_scope.json` (`L`, `KG`, `KM`, …).
- **fx** map each raw currency to the base currency (`USD`).
