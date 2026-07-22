# Asteria Fleet Data Quality Hub — Audit & Reconciliation Skill

## Purpose

Execute data-quality audit, entity reconciliation, canonical-master certification, and accrual-close tasks against the Asteria Fleet Data Quality Hub. This skill covers any task that: (a) involves the Asteria Fleet Data Quality Hub as the data source, (b) requires reconciling overlapping source records into canonical entities, (c) assigns opaque internal control/decision codes derived from business evidence, and (d) produces a certification or release decision from business thresholds.

## Trigger

Invoke this skill when the task prompt references the **Asteria Fleet Data Quality Hub**, instructs you to conform to an `answer_template.json` or `payloads/answer_template.json`, includes a `payloads/case_scope.json`, and/or mentions operations such as: contact-master certification, fuel-purchase audit, maintenance-log integrity certification, field-service roster readiness, or freight-charge accrual reconciliation.

## Environment Setup

Before any work, read `environment_access.md` at the task root. This file supplies:

- `base_url` — the actual origin for all API calls (overrides `<TASK_ENV_BASE_URL>`, `localhost`, `127.0.0.1`, and any `TASK_ENV_BASE_URL` env var)
- `credentials.query_authorization_header` — the exact `Authorization` header value for all requests
- `allowed_endpoints` — the set of permitted HTTP method + path pairs
- `runtime_notes` — any additional constraints (e.g., container networking)

Use the `base_url` + endpoint path for every call. Include the authorization header on every request. Do not substitute `localhost` or any other host.

## Input Contract

Every task supplies three files under a train directory:

| File | Purpose |
|---|---|
| `prompt.txt` | Natural-language instructions and business context |
| `payloads/case_scope.json` | Task parameters: collection id, cutoff/as-of, focus entities, thresholds, ranking policies, decision-panel IDs |
| `payloads/answer_template.json` | Output schema (JSON Schema or field contract) — defines required keys, types, enums, ordering rules, and numeric precision |

**Read all three files before starting work.** The answer template is the authoritative output contract; every key, enum value, and ordering constraint it declares is mandatory.

## Operating Procedure

Follow these phases in order. Do not skip phases; if a phase produces no results (e.g., no duplicates found), report empty arrays/zero counts rather than omitting the field.

### Phase 1 — Discover the Collection

1. Call `GET /api/catalog/collections` to list available collections.
2. Locate the collection identified by `case_scope.collection_id`.
3. Call `GET /api/catalog/schema` with the collection's stable ID to inspect its column layout, primary keys, and foreign-key relationships.
4. Record the column names, types, and nullable constraints — these govern which fields can be missing, which are linkable, and what validation rules apply.

### Phase 2 — Resolve Authoritative Source Snapshot

1. Call `GET /api/source-snapshots` for the target collection.
2. Every snapshot has a `status` field. Identify the **authoritative snapshot** as follows:
   - Prefer `CERTIFIED` over `PROVISIONAL` over `STALE`.
   - Among snapshots of equal status, prefer the most recent as-of timestamp that is ≤ the business cutoff/as-of.
   - The snapshot with the highest row count among candidates at the same tier breaks additional ties.
3. Record the authoritative snapshot's stable ID and its row count. This snapshot is the source of truth for deduplication and canonical values.
4. When a task scope references a `population_scope` of `ALL_COLLECTION_ROWS`, include all snapshots' rows for reconciliation but still resolve conflicts using the authoritative snapshot.

### Phase 3 — Acquire Raw Data

1. Fetch raw records from the collection's dedicated endpoint (e.g., `GET /api/contacts`, `GET /api/transactions/fuel`, `GET /api/transactions/freight`, `GET /api/maintenance/events`).
2. If the collection is larger than a single response page, paginate until all rows are retrieved.
3. For structured comparisons, joins, or filtered subsets, use `POST /api/query` with a SQL `SELECT` statement. The request body is `{"query": "SELECT ..."}`.
4. Fetch any supporting reference data needed: `GET /api/reference/aliases` (service-class or category mappings), `GET /api/reference/conversions` (unit conversions), `GET /api/reference/fx` (currency conversions).
5. Compute normalized physical measures: apply reference conversions to canonical units, apply FX rates to the base currency declared in case_scope.

### Phase 4 — Reconcile Overlapping Records

1. Group raw rows by their logical/business identifier. A logical identifier is the natural key that should be unique within the collection (e.g., a contact identity, a transaction ID, an event ID).
2. For each logical group with rows in multiple snapshots:
   - Retain the row from the authoritative snapshot when it is present.
   - If the authoritative snapshot does not contain the logical entity, retain the row from the highest-priority snapshot that does (using the same priority order as Phase 2).
   - Count the remaining rows as duplicates (`duplicate_raw_count`).
3. Build the set of **retained rows** — one per logical entity — using the survivor rule above. All downstream analysis uses only retained rows.

### Phase 5 — Classify Data Quality

Apply these classification rules to retained rows only (quarantine rules apply before normalization):

**Quarantine / Invalid rows** — rows that cannot enter normalized totals or canonical resolution:
- Missing or unparsable time fields (null, empty, or non-parseable timestamp)
- Values outside declared valid ranges (non-positive quantities, odometer values outside `[0, 999999]`, labor hours outside `[0, 100]`)
- Unrecognized or ambiguous category/class: a reference description that maps to zero canonical categories or more than one
- Missing all usable contact channels (no email AND no phone, or both null/empty)
- For physical measures: non-positive weight, distance, or volume

**Category/Class mismatches** — retained rows where the expected category (from the source system) differs from the recognized category (from the reference alias mapping). Mismatches are counted and reported separately from quarantines. Valid mismatches still enter normalized totals.

**Odometer regression** — for time-ordered maintenance events on the same asset: an event whose odometer reading is strictly less than the preceding event's reading. Regressions are reported as events and assets but do not invalidate the rows (they enter corrected metrics excluding regression pairs).

**Watchlist / contested identifiers** — when a case scope supplies identifier watchlist cases, test each anchor row against its cluster. A case is contested when the anchor row's resolved cluster contains rows from differing source systems that disagree on the identifier field. A case is uncontested when all rows in the cluster agree or when only one source system contributes rows.

### Phase 6 — Resolve Canonical Entities

For person/contact reconciliation tasks:

1. Cluster raw rows into canonical entities using the collection's natural identity fields (name variants, identifiers, contact points).
2. For each cluster:
   - Select a **survivor/master row** using field-level source precedence. Prefer: Identity Registry for identifiers, HR Directory for names and employment status, Dispatch for contact channels and depot assignment.
   - Derive canonical values from the survivor's fields: name (Unicode-preserving), email (trimmed, NFKC-normalized, lowercase), phone (digits only), city, region/depot code.
   - Record the `city_source_system` / `name_source_system` / `contact_source_system` / `depot_source_system` / `consent_source_system` indicating which source system the canonical value was drawn from.
3. For each focus cluster/seed row requested in case_scope, report:
   - All member row IDs (deduplicated, lexicographically sorted)
   - The survivor row ID
   - Canonical contact fields and their source systems
   - Resolution outcome: `SINGLE_SOURCE` (all rows from one system), `FIELD_LEVEL_PRECEDENCE_APPLIED` (multi-source merge succeeded), `CONTESTED_NO_AUTOMERGE` (multi-source with unreconcilable identifier conflict), `NO_USABLE_CONTACT` (no usable email or phone)

### Phase 7 — Assign Control and Decision Codes

Opaque codes are assigned by inferring the correct value from the reconciled data evidence. Every code belongs to a fixed enum defined in the answer template.

**Code families and their enums** (always consult the answer template for the active set):

| Code Family | Enum Values | Assigned To | Derivation |
|---|---|---|---|
| Identity | `IC-25`, `IC-40`, `IC-70`, `IC-90` | Focus clusters, control cases, quarantine results | Source-system agreement pattern of the identity field |
| Outreach | `OR-15`, `OR-35`, `OR-60`, `OR-80` | Anchored control cases, readiness partitions, quarantine results, inactive exclusions | Contact-channel availability and consent pattern of the resolved entity |
| Field Provenance | `FP-20`, `FP-55`, `FP-75` | Focus decisions, anchored control cases, quarantine results | Number and type of source systems contributing to the resolved entity |
| Reference Policy | `RB-17`, `RB-42`, `RB-83` | Reference alias decision rows | Alias mapping behavior (1:1 deterministic, 1:many, or unmatched) |
| Source Basis | `SB-24`, `SB-61`, `SB-79` | Transaction/charge source-retention rows | Snapshot status of the retained occurrence |
| Ledger Disposition | `LD-14`, `LD-31`, `LD-53`, `LD-72`, `LD-88` | Transaction/charge ledger-routing rows | Validity, mismatch, and quarantine status of the charge |
| Maintenance Source | `MS-12`, `MS-47`, `MS-86` | Maintenance event decision rows | Source system and snapshot status of the event |
| History Route | `HR-19`, `HR-33`, `HR-74` | Maintenance event decision rows | Whether the event is valid, a regression, or invalid |

**Derivation methodology**: For each code assignment, examine the evidence for that specific entity across all available source records:
- Which source systems contributed data?
- Do they agree or conflict on the key field for that code family?
- What is the snapshot status of the retained record?
- What quality issues (if any) apply to the entity?

Assign the code whose semantic meaning best matches the evidence pattern. Do not assign codes randomly — the answer template's enums are exhaustive, and exactly one value is correct for each entity based on the data.

### Phase 8 — Compute Aggregations and Rankings

1. **Normalized totals**: Sum valid (non-quarantined) retained rows by the grouping dimensions in the answer template (e.g., fuel type, service class, region). Apply unit conversions and FX rates. Round to the precision declared in the answer template (typically 2 decimal places).
2. **Rankings**: Sort entities by the primary key declared in case_scope, applying tie-breaks in the exact order specified. Ranks are 1-indexed integers.
3. **Region/Depot rollups**: Group canonical entities by their resolved region/depot, count per group, sort lexicographically.
4. **Channel readiness**: For each canonical entity that is active and has at least one usable contact:
   - `both` — usable email AND usable phone, consent granted for both channels
   - `email_only` — usable email only, consent granted
   - `phone_only` — usable phone only, consent granted
   - `not_ready` — active with usable channel(s) but consent not granted; or inactive with usable channel(s); or no usable channels
5. **Merchant/Carrier/Asset risk ranking**: Compute exception counts (mismatches + quarantines) per entity, sort by exception count descending, break ties per case_scope.

### Phase 9 — Apply Certification Thresholds

1. Compute the key ratio declared in case_scope (e.g., `quarantine_rate = quarantine_count / canonical_entity_count`).
2. Compare against the thresholds in case_scope:
   - `PASS` when `status_thresholds.pass_max_quarantine_rate` is not exceeded.
   - `PASS_WITH_EXCEPTIONS` when the rate exceeds the pass threshold but does not exceed `pass_with_exceptions_max_quarantine_rate`.
   - `HOLD` when the rate exceeds the `pass_with_exceptions` threshold.
3. Map status to action using `status_action_map` from case_scope:
   - `PASS` → action for `PASS`
   - `PASS_WITH_EXCEPTIONS` → action for `PASS_WITH_EXCEPTIONS`
   - `HOLD` → action for `HOLD`
4. Some tasks use hardcoded certification gates (e.g., "odometer regression → HOLD/BLOCK_AND_REMEDIATE"). When present, the gate overrides the threshold calculation.
5. For tasks without explicit thresholds, derive the status from the presence of exceptions: zero exceptions → `PASS`/`RELEASE`; exceptions present → `PASS_WITH_EXCEPTIONS`/`REVIEW_EXCEPTIONS`; blocking conditions → `HOLD`/`BLOCK_AND_REMEDIATE`.

## Output Rules

These rules are universal and non-negotiable:

### Format
- Return exactly one JSON object. No surrounding text, no Markdown fences, no commentary.
- The object must conform to `payloads/answer_template.json` — every required key present, no additional keys, every enum value from the allowed set.

### Ordering
- All arrays must be in the declared sort order. Default rules when the template does not specify:
  - String IDs: lexicographic ascending (Unicode code-point order).
  - Numeric ranks: ascending.
  - Grouped summaries: ascending by the group key (alphabetical for enums, lexicographic for IDs).
- The answer template's `description` fields and `x-ordering_rules` blocks are binding.

### Numeric Precision
- Integer fields: exact integers (no trailing `.0`).
- Decimal fields: round to the precision declared in the answer template (typically 2 decimal places). Use standard round-half-up.
- Rates: round to 4 decimal places unless otherwise specified.

### Lists
- All list fields with `uniqueItems: true` must contain no duplicates.
- All lists with `minItems` / `maxItems` must satisfy those cardinality constraints exactly.
- Empty arrays are permitted only when neither `minItems` nor the task logic requires entries; use `[]`, never `null` or absent keys.

### Enums
- Every string field with an `enum` constraint must use one of the listed values exactly.
- Do not invent or interpolate codes. If a code's derivation is ambiguous, pick the best-fitting enum member based on the evidence — do not fabricate a value outside the enum.

## Certification Matrix

The standard decision matrix (subject to case_scope overrides):

| Status | Action | Meaning |
|---|---|---|
| `PASS` | `RELEASE` | All quality gates met; data is ready for downstream use |
| `PASS_WITH_EXCEPTIONS` | `REVIEW_EXCEPTIONS` | Minor issues found; review the exception lists and approve before release |
| `HOLD` | `BLOCK_AND_REMEDIATE` | Blocking issues found; data must be remediated before any downstream use |

## Hub API Reference

The following endpoints are available. `environment_access.md` declares the active subset and the authorization header.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/catalog/collections` | List available data collections with stable IDs and metadata |
| GET | `/api/catalog/schema` | Inspect column definitions for a collection |
| GET | `/api/contacts` | Fetch contact records (people, emails, phones, consent, status) |
| GET | `/api/transactions/fuel` | Fetch fuel-purchase transaction records |
| GET | `/api/transactions/freight` | Fetch freight-charge records |
| GET | `/api/maintenance/events` | Fetch maintenance-log event records |
| GET | `/api/reference/aliases` | Fetch alias/description-to-category mappings |
| GET | `/api/reference/conversions` | Fetch unit-conversion factors |
| GET | `/api/reference/fx` | Fetch foreign-exchange rates |
| GET | `/api/source-snapshots` | Fetch snapshot metadata (status, as-of, row count, stable ID) |
| POST | `/api/query` | Execute a read-only SQL query; body: `{"query": "SELECT ..."}` |

All requests must include the `Authorization` header from `environment_access.md`. The POST `/api/query` endpoint requires `Content-Type: application/json`.
