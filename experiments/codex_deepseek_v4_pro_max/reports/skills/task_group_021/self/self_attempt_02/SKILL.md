## Asteria Fleet Data Quality Hub — Reconciliation Skill

Follow these rules whenever a task requires auditing, reconciling, or certifying data
through the Asteria Fleet Data Quality Hub. The hub is a read-only REST API backed by
multiple overlapping source snapshots; every task follows the same operating model
even though domain details differ.

### 1. Source material layout

Every task provides three artefacts:

- `payloads/case_scope.json` — collection identifier, business cutoff, focus IDs,
  thresholds, decision-panel IDs, ranking rules, and status-action maps.
- `payloads/answer_template.json` — full output contract: required keys, allowed
  enumerations, ordering rules, and precision requirements.
- `environment_access.md` — base URL, allowed GET endpoints, the authenticated
  query credential, and a sample `POST /api/query` invocation.

Read all three before touching the API. The template and scope together define
every value the caller expects; never invent extra keys, rename fields, or omit
required sections.

### 2. API conventions

- **Base URL** — given in `environment_access.md` as `GDPEVO_ENV_BASE_URL`.
- **Authentication** — `Authorization: Bearer <token>` header for `POST /api/query`
  only. The token is listed in `environment_access.md`. All GET endpoints are
  unauthenticated.
- **Query interface** — `POST /api/query` with `Content-Type: application/json`
  and body `{"query":"<SQL>"}`. The database exposes *public views*
  (e.g. `v_source_snapshots`, `v_contacts`, `v_fuel_transactions`,
  `v_freight_charges`, `v_maintenance_events`, `v_reference_aliases`,
  `v_reference_conversions`, `v_reference_fx`).
- **Pagination** — collections may be larger than a single response page. Always
  read the full dataset using `LIMIT`/`OFFSET` loops when pagination metadata
  (e.g. `total`, `page`, `page_size`) is present in the response.
- **Idempotency** — the hub is read-only. Re-run queries freely; no data is
  modified.

### 3. Schema discovery

Before querying any collection data:

1. `GET /api/catalog/collections` — list every collection and its business
   identifier (`collection_id`). Confirm the scoped collection exists.
2. `GET /api/catalog/schema` — obtain the schema for all views. Map every field
   mentioned in `case_scope.json` or `answer_template.json` to its public view
   column.
3. `GET /api/source-snapshots` — retrieve source-snapshot metadata (snapshot
   IDs, collection membership, status flags like `CERTIFIED`/`PROVISIONAL`/
   `STALE`, creation timestamps).

### 4. Authoritative snapshot selection

Most tasks deal with overlapping records from multiple source snapshots.

- Choose the snapshot that is **newest by creation timestamp** among snapshots
  whose status is `CERTIFIED` and that are within the business cutoff.
- If no `CERTIFIED` snapshot exists, fall back to `PROVISIONAL`, then `STALE`,
  preferring the most recent creation timestamp.
- A snapshot older than the cutoff is still eligible if it is the newest
  qualifying snapshot.
- Document the chosen snapshot ID in the output (field name varies per answer
  contract — e.g. `authoritative_snapshot_id`).

### 5. Data retrieval and pagination

Use `POST /api/query` to run `SELECT` or `WITH` queries against public views.

- Always filter to the scoped collection and the chosen authoritative
  snapshot(s).
- Apply the business cutoff from `case_scope.json`: exclude rows whose
  timestamp is strictly after the cutoff.
- If the answer contract requires data from multiple snapshots (e.g. to
  enumerate duplicates), fetch both the authoritative view and a union over
  all in-scope snapshots.
- When a GET collection endpoint exists (e.g. `/api/contacts`,
  `/api/transactions/fuel`), prefer it for bulk retrieval; use `/api/query`
  for filtered or aggregated views.

### 6. Duplicate resolution

When multiple raw rows represent the same logical entity (identified by a
shared stable business key):

1. Group raw rows that share the same logical ID.
2. From the authoritative snapshot, keep exactly one row per logical ID.
3. Rows from other snapshots that share the logical ID are **duplicate raw
   rows**. Count them separately (`duplicate_raw_count`).
4. Report every duplicate group with its logical ID, constituent snapshot
   IDs (sorted lexicographically), and the retained row/snapshot pair.

### 7. Quality checks and quarantine

Apply the checks implied by the answer template and scope. Common patterns:

- **Missing or unparseable timestamps** — row is invalid.
- **Negative or zero physical measures** (volume, weight, distance, labor
  hours) — row is invalid unless the contract explicitly allows zero.
- **Extreme/out-of-range values** — row is invalid if the contract defines a
  range.
- **Odometer regression** — when events for the same asset are sorted by
  timestamp, any odometer reading that is lower than the previous reading
  for that asset constitutes a regression.
- **Unrecognized category/class** — the row's category field does not match
  any known canonical value → set aside as unrecognized.
- **Ambiguous category/class** — the row's description maps to more than one
  canonical category → set aside as ambiguous.
- **Expected-vs-actual mismatch** — the expected category (from source
  metadata or ID prefix) differs from the recognized canonical category. A
  mismatch is still a *valid* row for totals unless it is also quarantined.
- **No usable contact channel** — the row has no email and no phone, or both
  are invalid/missing → quarantine.

Rows that fail a quarantine check **do not enter normalized totals**. Rows
with category/class mismatches **do** enter normalized totals (they are valid
but flagged).

### 8. Normalization and unit conversion

- Use `/api/reference/conversions` to convert physical measures to the
  canonical unit declared in `case_scope.json`.
- Use `/api/reference/fx` for currency conversion to the declared base
  currency.
- Use `/api/reference/aliases` to resolve human-readable identifiers to
  canonical service classes, fuel types, or carrier codes.
- Round to the decimal precision declared in the answer contract (commonly
  2 decimal places). Use standard rounding (half-up or half-even as
  appropriate to the target; prefer half-up unless specified otherwise).

### 9. Ranking rules

Many tasks request a top-N ranking. Read the ranking spec from
`case_scope.json` (primary sort, tie-breaks, limit). Common patterns:

- **Merchant/carrier ranking by exceptions** — order by exception count
  descending, then ID ascending.
- **Carrier ranking by exposure** — order by mismatch spend descending, then
  carrier ID ascending.
- **Asset risk ranking** — order by rejected-event count descending, then
  regression-event count descending, then asset ID ascending.

Always apply tie-breaks in the exact order specified. The limit field
(e.g. `merchant_ranking_limit`, `carrier_ranking_limit`) controls how many
entries to return.

### 10. Control-code assignment

Most answer contracts include enumerated internal codes (identity, outreach,
field provenance, source basis, ledger disposition, reference policy,
maintenance source, history route). These codes are **not** stored as
separate API fields; they must be inferred from:

- The evidence rows supplied in `case_scope.json` (e.g. `evidence_row_ids`).
- The data provenance visible in the public views (which source system
  contributed the row, which snapshot carried it, whether fields agree or
  disagree across sources).
- Business rules implied by the allowed code enumerations and the outcome
  labels in the template.

Assign exactly one allowed code per decision item. The answer template
lists the permitted values for each code slot (e.g. `IC-25`, `IC-40`,
`IC-70`, `IC-90` for identity codes). Do **not** use a code outside its
allowed slot.

### 11. Certification / close / release decision

Every task ends with a status-action pair:

| Status              | Action              |
|---------------------|---------------------|
| `PASS`              | `RELEASE`           |
| `PASS_WITH_EXCEPTIONS` | `REVIEW_EXCEPTIONS` |
| `HOLD`              | `BLOCK_AND_REMEDIATE` |

Determine the status by applying the thresholds in `case_scope.json` (e.g.
`status_thresholds`, `certification_gate`) or by the logical rules embedded
in the task. For example:

- If the quarantine rate exceeds `pass_max_quarantine_rate` and is ≤
  `pass_with_exceptions_max_quarantine_rate` → `PASS_WITH_EXCEPTIONS`.
- If the quarantine rate exceeds
  `pass_with_exceptions_max_quarantine_rate` → `HOLD`.
- If any odometer regression exists and the certification gate says
  `HOLD` → `HOLD`.

### 12. Output rules

- Produce exactly **one JSON object**. No markdown, no commentary, no
  wrapping text.
- Match every required key, sub-key, type, enum, and pattern from the
  answer template.
- Arrays must be sorted per the ordering rules declared in the template
  (lexicographically ascending unless otherwise stated).
- Count fields are exact non-negative integers.
- Floating-point fields use the declared precision (commonly 2 decimal
  places).
- Do not add extra keys; `additionalProperties: false` is the norm.
- Stable IDs in lists must use the exact values from the public data or
  scope — never fabricate IDs.

### 13. Procedural checklist

For every task, execute in this order:

1. Read `payloads/case_scope.json` and `payloads/answer_template.json`.
2. Read `environment_access.md` for URL and credentials.
3. `GET /api/catalog/collections` — verify collection.
4. `GET /api/catalog/schema` — map fields.
5. `GET /api/source-snapshots` — identify authoritative snapshot.
6. Retrieve full dataset (via collection endpoint or paginated query).
7. Apply cutoff filter.
8. Resolve duplicates; select survivors.
9. Run quality checks; classify rows as valid, mismatch, unrecognized,
   ambiguous, or quarantined.
10. Normalize physical measures and currency.
11. Compute aggregations (totals, rollups, rankings).
12. Assign control codes from evidence.
13. Determine certification status from thresholds.
14. Assemble and emit the JSON object, conforming strictly to the answer
    template.

### 14. Common pitfalls

- **Using the wrong snapshot** — always confirm which snapshot is
  authoritative by timestamp and status, not by position in a list.
- **Including quarantined rows in totals** — quarantined rows are excluded
  from normalized totals but are still listed in quarantine arrays and
  counted in quarantine tallies.
- **Including duplicates in row counts** — `raw_row_count` includes every
  raw row; `logical_*_count` counts distinct business entities. Make sure
  the answer-template definitions match this distinction.
- **Rounding too early** — accumulate raw values, then round the final
  result. Intermediate rounding can cause off-by-0.01 errors.
- **Missing the cutoff** — rows with timestamps after the cutoff must be
  excluded even if they appear in the snapshot.
- **Wrong ordering** — stable-ID lists and arrays nearly always require
  explicit sorting (lexicographic or the declared rule). Unordered arrays
  are not accepted.
- **Extra keys** — the answer templates forbid additional properties. Do
  not include helper fields, intermediate results, or debug keys in the
  final output.
