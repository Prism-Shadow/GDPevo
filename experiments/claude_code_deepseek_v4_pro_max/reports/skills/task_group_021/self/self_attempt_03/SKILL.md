---
name: asteria-fleet-data-quality-hub
description: Reusable operating rules for reconciling and certifying data-quality collections against the Asteria Fleet Data Quality Hub REST API.
---

# Asteria Fleet Data Quality Hub — Reusable Operating Rules

## Environment

The Asteria Fleet Data Quality Hub is a read-only REST API. Runtime access details are supplied in `environment_access.md`:

- **Base URL**: specified in `environment_access.md` under `base_url`
- **Auth header**: specified under `credentials.query_authorization_header`
- **Allowed endpoints**: listed under `allowed_endpoints`
- **Query endpoint**: `POST /api/query` accepts `{"query": "<SQL>"}` with the auth header

Apply the base URL, auth header, and endpoint list from `environment_access.md` for every call. Do not use localhost, 127.0.0.1, or any other base URL.

## Input Files

Every task provides three input files:

| File | Purpose |
|---|---|
| `prompt.txt` | Business scenario, reconciliation instructions, and output rules |
| `payloads/case_scope.json` | Task-specific parameters: collection ID, cutoff date, focus entities, thresholds, ranking limits, decision-panel IDs, certification gates |
| `payloads/answer_template.json` | JSON Schema defining the exact output shape, required fields, allowed enum values, ordering rules, and numeric precision |

**Rule**: The answer contract (answer template) is authoritative for output structure. Read every field description, enum constraint, pattern, min/max items, and ordering annotation before producing output.

## Discovery Workflow

### Step 1: Catalog and Schema

```
GET /api/catalog/collections
GET /api/catalog/schema
```

The collections endpoint lists available named collections with metadata including their stable IDs. The schema endpoint describes field names, types, and source-system labels for each collection.

Use the collection ID from `case_scope.json` to locate the target collection. Verify the collection exists before proceeding.

### Step 2: Source Snapshots

```
GET /api/source-snapshots
```

Each collection may have multiple ingested snapshots. Snapshot metadata includes a snapshot ID, a status (CERTIFIED, PROVISIONAL, STALE), an ingestion timestamp, a row count, and coverage notes.

**Authoritative snapshot selection**: When a collection has multiple snapshots, select the most recent CERTIFIED snapshot whose ingestion timestamp is on or before the business cutoff. If no CERTIFIED snapshot is available, use the most recent PROVISIONAL snapshot before cutoff. When snapshots overlap in time, the authoritative snapshot resolves duplicates — retain its occurrence for each logical entity.

### Step 3: Query Data

```
POST /api/query
{"query": "SELECT * FROM <collection_id>"}
```

The query returns paginated results when the collection is large. The response includes `rows`, `total_rows`, and pagination metadata. If `total_rows` exceeds the returned row count, add `LIMIT` and `OFFSET` clauses to retrieve remaining pages. Collect all rows before performing reconciliation.

All query text is SQL executed against the named collection. The collection name in `FROM` clauses is the stable `collection_id` from the case scope. Columns correspond to the schema fields returned by `/api/catalog/schema`.

## Reconciliation Patterns

### Pattern A: Logical Deduplication (Transactions, Events, Charges)

Collections with overlapping source snapshots may contain the same logical entity recorded multiple times — once per snapshot.

1. Query the collection without snapshot filtering to obtain all raw rows.
2. Group raw rows by their logical identifier (e.g., `transaction_id`, `event_id`, `charge_id`).
3. For each group with rows in multiple snapshots, retain the row from the **authoritative snapshot**.
4. Count duplicate raw rows as `raw_row_count - logical_entity_count`.
5. Retain a single row per logical entity for all downstream computation.

**Duplicate groups**: Report every logical entity that appears in two or more snapshots. Include the logical ID, the set of snapshot IDs it appears in, and which snapshot's occurrence was retained.

### Pattern B: Contact/Entity Merging (People, Partners)

When a collection contains contact rows from multiple source systems (e.g., HR Directory, Dispatch, Identity Registry, CRM, Compliance Master, Partner Portal), merge them into canonical entities:

1. Group rows by a shared identifier (email, phone, or deterministic cluster key).
2. Within each cluster, apply **field-level source precedence** to select the canonical value for each field. Precedence is observable from the source-system label on schema fields:
   - For identity fields (name, DOB): use the system with the most complete, non-null values across the cluster.
   - For contact fields (email, phone): use the system whose rows most consistently carry usable channel values.
   - The precedence order is intrinsic to the data, not stated in task materials. Test candidate orders against evidence and adopt the one that minimizes contradiction.
3. Select a **survivor row** (master ID) from among the merged rows. Prefer the row whose source system contributed the most canonical field values, breaking ties by the earliest source-system row in the cluster.
4. The resolved entity record includes: all member row IDs (sorted), the survivor row ID, and the canonical values for each field.

**Identifier watchlists**: When case scope provides an identifier watchlist, check whether watchlist-anchored rows have been merged with other rows in the population. If a watchlist-anchor's cluster contains rows that disagree on identity fields, mark the watchlist case as contested.

### Pattern C: Category/Class Matching (Fuel, Freight)

When transactions have both an expected category and a text description that must be mapped to a recognized category:

1. Query the reference endpoints for the collection's recognized category taxonomy.
2. Match each transaction's description text against the taxonomy. A match is **unique** when the description maps to exactly one recognized category. A match is **ambiguous** when it maps to more than one. The category is **unrecognized** when it maps to none.
3. Compare the matched category against the expected category on the row. A **mismatch** occurs when the recognized category differs from the expected category (both must be valid and recognized).
4. **Quarantine conditions for class/category**: unrecognized (no match), ambiguous (multiple matches), invalid physical measures (non-positive weight, distance, or quantity). Quarantined items are excluded from normalized totals.
5. A **valid** item has a unique recognized category, matches its expected category (or no expected category to check), and has positive physical measures.

### Pattern D: Time-Series Integrity (Maintenance, Odometer)

For event collections with ordered timestamps and odometer readings:

1. **Invalid records**: Remove events with missing or unparsable timestamps, odometer readings outside valid range, or labor hours outside valid range. These go to `invalid_event_ids` (sorted) and are excluded from all metrics.
2. **Odometer regression**: After removing invalid records, sort valid events per asset by timestamp. An odometer regression occurs when a later event has a lower odometer reading than an earlier event for the same asset. Report regression events separately — they are not rejected for other reasons but flag data-quality concerns.
3. **Corrected distance**: For each asset, compute `last_reliable_odometer - first_reliable_odometer` from the reconstructed history. Sum across assets for the total.

## Control Codes

Many answer contracts require **opaque internal codes** — short alphanumeric identifiers from a closed enumeration. These codes are not defined in any reference table; they are **embedded in the source data rows** of the collection.

### Code Families

| Prefix | Domain | Where to Find |
|---|---|---|
| `IC-` | Identity classification | Contact/entity source rows, identity fields |
| `OR-` | Outreach/consent | Contact source rows, consent/outreach fields |
| `FP-` | Field provenance | Contact/entity source rows, provenance/source-quality fields |
| `RB-` | Reference basis | Reference/alias rows, classification/policy fields |
| `SB-` | Source basis | Transaction/charge source rows, source-attribution fields |
| `LD-` | Ledger disposition | Transaction/charge source rows, ledger/routing fields |
| `MS-` | Maintenance source | Maintenance event rows, source-system fields |
| `HR-` | History route | Maintenance event rows, history/routing fields |

### Code Assignment Procedure

1. For each scoped entity (focus cluster, control case, reference ID, transaction ID, maintenance event), query the relevant source row — the row from which the entity was drawn.
2. Inspect the row's fields that semantically align with the code family. For example, a field labeled `source_system`, `provenance`, `policy`, `disposition`, `identity_class`, `outreach_status`, or similar.
3. The code value present in that field is the answer. If multiple candidate fields exist, prefer the field whose name most directly matches the code family's domain.
4. For **control cases**: each case specifies evidence row IDs. Query those rows and extract the code from the field matching the control family (`IDENTITY` → `IC-*`, `OUTREACH` → `OR-*`, `FIELD_PROVENANCE` → `FP-*`).
5. For **anchored cases**: query the seed rows and extract all three code families (`IC-*`, `OR-*`, `FP-*`) from the relevant fields.
6. For **focus clusters**: query the survivor row and extract the applicable codes from its fields.

## Thresholds and Certification

### Status Decision

Every task concludes with a certification status and action:

- `PASS` → `RELEASE`: all thresholds satisfied
- `PASS_WITH_EXCEPTIONS` → `REVIEW_EXCEPTIONS`: some thresholds exceeded but within acceptable limits
- `HOLD` → `BLOCK_AND_REMEDIATE`: critical thresholds exceeded

### Threshold Application

Thresholds are specified in `case_scope.json`. Common patterns:

1. **Quarantine rate**: `quarantined_items / canonical_or_valid_items`. Compare to `pass_max_quarantine_rate` and `pass_with_exceptions_max_quarantine_rate`.
2. **Absolute gate**: a specific condition (e.g., odometer regression) maps directly to a status/action pair.
3. **Channel readiness**: compute readiness categories (both channels, email only, phone only, not ready) on eligible entities. The resulting distribution may inform or determine the certification decision.

Apply thresholds as specified. When multiple thresholds exist, the most severe outcome governs.

### Readiness

An entity is **readiness-eligible** when it is active (record status is ACTIVE) and has at least one usable contact channel. A channel is **usable** when it has a non-null, well-formed value. A channel is **ready** when consent is GRANTED. Categories:

- `both`: active, has usable email AND usable phone, consent is GRANTED for both
- `email_only`: active, has usable email with GRANTED consent, phone is absent or consent not granted
- `phone_only`: active, has usable phone with GRANTED consent, email is absent or consent not granted
- `not_ready`: active but neither channel is consent-granted, or no usable channels at all

## Normalized Totals

- **Valid items only**: exclude all quarantined items from normalized volume, spend, distance, and weight totals.
- **Unit conversions**: when raw values are in non-canonical units, use the conversion factors from `GET /api/reference/conversions` to convert to the canonical unit declared in the case scope.
- **Currency conversions**: when raw spend is in a non-base currency, use rates from `GET /api/reference/fx` to convert to the base currency declared in the case scope.
- **Rounding**: monetary and measure values are rounded to exactly 2 decimal places. Counts are exact integers.

## Ranking

When case scope requests ranked lists (top-N merchants, carriers, assets):

1. Compute the ranking metric for every eligible entity using only valid retained rows.
2. Sort by the primary sort key (typically descending: highest exception count, highest exposure, highest risk first).
3. Apply tie-breaks in the exact order specified in case scope (secondary sort descending, then ID ascending).
4. Take the top N and assign sequential ranks starting from 1.

## Output Rules

1. **JSON only**: return a single JSON object. No markdown fences, no commentary before or after.
2. **Conform exactly** to `payloads/answer_template.json`: every required key present, no additional keys, values within allowed enums and patterns.
3. **Sorting**: all ID lists are sorted lexicographically ascending unless the answer template or case scope specifies otherwise. Object arrays are sorted by their primary key ascending.
4. **Deduplication**: every ID list in the output is a set — no duplicate entries.
5. **Numeric precision**: counts are exact integers. Monetary and measure values are numbers rounded to 2 decimal places (use `Math.round(value * 100) / 100` or equivalent). Rates are rounded to 4 decimal places when specified.
6. **Null handling**: no field in the output object may be null unless the answer template explicitly allows it. Use empty arrays (`[]`) for empty lists.

## Endpoint Reference

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/catalog/collections` | List available data collections |
| GET | `/api/catalog/schema` | Field definitions and source-system labels |
| GET | `/api/contacts` | Contact records (paginated) |
| GET | `/api/transactions/fuel` | Fuel purchase transactions (paginated) |
| GET | `/api/transactions/freight` | Freight charge transactions (paginated) |
| GET | `/api/maintenance/events` | Maintenance event records (paginated) |
| GET | `/api/reference/aliases` | Alias/category lookup tables |
| GET | `/api/reference/conversions` | Unit conversion factors |
| GET | `/api/reference/fx` | Foreign exchange rates |
| GET | `/api/source-snapshots` | Snapshot metadata for each collection |
| POST | `/api/query` | Authenticated SQL query (`{"query": "SELECT ..."}`) |

## Task Execution Sequence

1. Read `prompt.txt`, `payloads/case_scope.json`, and `payloads/answer_template.json`.
2. Read `environment_access.md` for base URL, auth header, and allowed endpoints.
3. GET `/api/catalog/collections` — confirm the target collection exists.
4. GET `/api/catalog/schema` — understand the field layout and source systems.
5. GET `/api/source-snapshots` — identify the authoritative snapshot for the collection and cutoff.
6. POST `/api/query` — retrieve all scoped rows (paginate if needed). Apply cutoff filtering in SQL when possible.
7. GET supporting reference data (aliases, conversions, fx, contacts) as needed by the task domain.
8. Reconcile: deduplicate, merge entities, match categories, detect quality issues.
9. Assign control codes by querying source rows for the scoped entities.
10. Compute normalized totals (excluding quarantined items, applying conversions).
11. Compute rankings, readiness partitions, region rollups, and other task-specific rollups.
12. Apply certification thresholds and determine final status/action.
13. Assemble the output object conforming to the answer template. Validate against the schema.
14. Return the JSON object.

## Common Pitfalls

- **Using the wrong base URL**: always read `environment_access.md` for the base URL; do not assume localhost.
- **Forgetting pagination**: when `total_rows > len(rows)` in a query response, issue additional queries with `OFFSET` to collect all data.
- **Including quarantined items in normalized totals**: quarantined items must be excluded from spend, volume, distance, and weight summaries.
- **Incorrect survivor selection**: the survivor must be a row that actually exists in the source data — not a synthetic row.
- **Missing control codes**: every scoped entity in the answer contract that requires codes must have them. Query the source rows directly.
- **Sorting errors**: lexicographic sorting means string comparison, not numeric. `"PAR-C00002"` comes before `"PAR-C00010"` because `'0' < '1'` at position 6.
- **Schema non-conformance**: test the assembled output against the answer template's `additionalProperties: false`, `enum`, `pattern`, `minItems`, and `maxItems` constraints.
