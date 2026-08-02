# Hub access — endpoints, auth, snapshots, pagination

## Connection

`environment_access.md` supplies, per run:

- `GDPEVO_ENV_BASE_URL=<base>` — substitute this wherever the prompt says
  `<TASK_ENV_BASE_URL>`.
- `AUTHORIZATION: Bearer <token>` — send on **every** request (GETs and the
  query POST alike).
- The explicit allow-list of endpoints. Use only those. Never assume an endpoint
  that isn't listed, and never attempt a mutating call — the hub is read-only.

Do not hardcode a base URL, token, port, or task number from any prior run; they
change per task. Always re-read `environment_access.md`.

## Endpoints seen in this family

Not every task exposes all of these — the prompt lists the ones that matter.

- `GET /api/catalog/collections` — enumerate collections; confirm the scoped
  `collection_id` exists and read its metadata.
- `GET /api/catalog/schema` — field names, types, enums, and structural hints:
  which field is the **business date**, which are **stable IDs**, how snapshots
  attach to rows, the shape/params of `/api/query`, and any code dictionary.
  Always consult this before assuming a field name.
- `GET /api/contacts` — person/contact source rows (contact sub-families).
- `GET /api/transactions/fuel` — fuel transaction rows.
- `GET /api/transactions/freight` — freight charge rows.
- `GET /api/maintenance/events` — maintenance event rows.
- `GET /api/reference/aliases` — free-text → canonical-category mapping (fuel
  type, service class, etc.); may also carry reference-policy attributes used to
  infer RB-* codes.
- `GET /api/reference/conversions` — unit conversion factors (→ L, KG, KM, …).
- `GET /api/reference/fx` — currency rates → base currency (usually USD),
  typically effective-dated.
- `GET /api/source-snapshots` — snapshot metadata: id, `status`
  (`CERTIFIED` / `PROVISIONAL` / `STALE`), effective/as-of time, row counts,
  which collection it belongs to.
- `POST /api/query` — authenticated read-only structured query. Use it to
  filter/aggregate server-side, to confirm counts, and to page large
  collections. Discover its request contract from `/api/catalog/schema`; it does
  not mutate anything.

## Selecting the authoritative snapshot

The same logical population is published across several snapshots. To reconcile
"as of the business cutoff / `as_of`":

1. Restrict to snapshots for the scoped collection whose effective/as-of time is
   **≤** the cutoff.
2. The **authoritative snapshot** is the highest-precedence one:
   `CERTIFIED` > `PROVISIONAL` > `STALE`; among equal status, the latest
   effective ≤ cutoff. Report it as `authoritative_snapshot_id` (and
   `snapshot_status` where required).
3. When the contract distinguishes `authoritative_row_count` from
   `scoped_raw_row_count`: the former is the authoritative snapshot's own row
   count; the latter is the count of all in-scope raw rows fed into
   reconciliation (the union you page in step 5). Read exactly which one each
   answer field wants.

The authoritative snapshot is also the **retention winner** when a logical
record appears in more than one snapshot (see `reconciliation.md`).

## Cutoff / period filtering

Filter on the **business/effective date field** identified from the schema —
not ingestion or load time. Honor the exact scope form:

- `cutoff_at` / `business_cutoff` → keep rows with business date ≤ cutoff.
- `business_period` `{start, end}` → keep rows within the inclusive window.
- `as_of` → the reconstruction instant for snapshot selection and history.

## Pagination — page everything

Collections exceed one response page ("larger than a single response page"). Do
not stop at the first page:

- Follow the pagination mechanism the API exposes (cursor / `next` / page &
  page-size params — confirm from the schema or the response envelope).
- Loop until exhausted; accumulate all rows before reconciling.
- Cross-check the total against a `POST /api/query` count (or the snapshot's
  declared row count) so you can prove you fetched the whole population. A
  truncated fetch silently corrupts every downstream count.
