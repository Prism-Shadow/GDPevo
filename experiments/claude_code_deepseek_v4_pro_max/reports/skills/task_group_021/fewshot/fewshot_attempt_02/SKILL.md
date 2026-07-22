# Asteria Fleet Data Quality Hub — Audit & Certification Skill

## Purpose

Reconcile overlapping source records from the Asteria Fleet Data Quality Hub, compute integrity metrics, assign internal control codes, and produce a certification decision. This skill covers auditing transactional collections (fuel, freight, maintenance) and certifying entity populations (contacts, partners). Every task is scoped by a `case_scope.json` payload and must produce a single JSON object conforming exactly to an `answer_template.json` contract.

## Environment Setup

Connection details are always supplied in a companion file `environment_access.md` containing:

- `base_url` — the root URL of the Fleet Data Quality Hub (e.g. `http://task-env:9021/`)
- `credentials.query_authorization_header` — the full `Authorization: Bearer <token>` header value for POST `/api/query` and all GET endpoints
- `allowed_endpoints` — the list of API paths available for the task
- `runtime_notes` — any override of `<TASK_ENV_BASE_URL>` references found in task prompt text

**Before any data retrieval**, read `environment_access.md` and configure all HTTP requests with the base URL and Authorization header it specifies. The token is read-only.

## API Reference

All endpoints are JSON-only. The Hub is read-only; no data-mutating endpoints are provided.

### Catalog & Schema

| Endpoint | Method | Description |
|---|---|---|
| `/api/catalog/collections` | GET | List all available data collections with their stable IDs |
| `/api/catalog/schema` | GET | Return the full data dictionary: column names, types, nullable flags, value constraints, and collection-to-endpoint mappings |

Always call these two endpoints first. They tell you which collection maps to which data endpoint, what each column means, which columns form the business key, and what enumerated/constrained values are valid.

### Domain Data Endpoints (GET)

These endpoints return paginated lists. A task's `environment_access.md` gates which ones are available. Common ones include:

| Endpoint | Entity |
|---|---|
| `/api/contacts` | Person/partner contact rows with name, email, phone, city, region, consent, status, source-system provenance |
| `/api/transactions/fuel` | Fuel-purchase transaction rows |
| `/api/transactions/freight` | Freight-charge rows |
| `/api/maintenance/events` | Maintenance-event rows |
| `/api/reference/aliases` | Service-class or fuel-category alias-to-canonical mappings |
| `/api/reference/conversions` | Unit-of-measure conversion factors |
| `/api/reference/fx` | Currency exchange rates for a given date/period |
| `/api/source-snapshots` | Snapshot metadata: stable snapshot IDs, status (CERTIFIED/PROVISIONAL/STALE), row counts, timestamps |

**Pagination**: If a collection is larger than a single response page, the endpoint includes pagination controls (next-page links or offset/token). You must follow pagination links to retrieve the full dataset before performing any reconciliation.

### Query Interface

`POST /api/query` — Accepts `{"query": "SELECT ..."}` with the Authorization header from `environment_access.md`. The SQL dialect is read-only, supports standard `SELECT`/`WHERE`/`GROUP BY`/`ORDER BY`/`JOIN`, and the schema endpoint documents the available table and column names. Use this for filtered extracts, aggregations, and cross-reference lookups.

Note: `/api/query` is the only POST endpoint available and must include the exact Authorization header value.

## Standard Workflow

Every task follows the same five-phase structure.

### Phase 1: Scope & Contract Parsing

Read two payload files from the task input directory:

1. **`case_scope.json`** — defines WHAT to audit/certify:
   - `collection_id` — which data collection to work on
   - A cutoff timestamp (`business_cutoff`, `cutoff_at`, or `as_of`) — only records on or before this time are in scope
   - Focus entities (assets, people, transactions, reference IDs) for detailed reporting panels
   - Thresholds and ranking limits
   - Certification gates (e.g. odometer regression → HOLD)

2. **`answer_template.json`** — defines the OUTPUT SHAPE:
   - Required top-level keys and their types
   - Enum constraints for every code field
   - Ordering rules (lexicographic ascending is the default for all ID arrays)
   - Numeric precision (counts as integers, amounts/rates to 2 or 4 decimal places)
   - Min/max item counts

**Critical**: The answer template IS the contract. Every field it declares as `required` must be present. Every `enum` must be honored. No commentary or extra keys are permitted outside the template.

### Phase 2: Data Retrieval

1. Call `/api/catalog/collections` and `/api/catalog/schema` to understand the data model.
2. Call `/api/source-snapshots` to discover available snapshots for the collection. Each snapshot has:
   - A stable `snapshot_id`
   - A `status` field (CERTIFIED, PROVISIONAL, STALE)
   - Metadata including row counts and temporal bounds
3. Identify the **authoritative snapshot** for the collection:
   - If a snapshot's `status` is `CERTIFIED`, it is authoritative.
   - If multiple snapshots exist, the certified one takes precedence for the retained row in duplicate resolution.
   - Record the authoritative `snapshot_id` — it is always required in the answer.
4. Retrieve the full dataset from the domain data endpoint(s) listed in the schema for your `collection_id`. Follow pagination to exhaustion.
5. Apply the scope cutoff: filter all rows to `event_timestamp <= cutoff` (or the equivalent column documented in the schema).

### Phase 3: Reconciliation & Deduplication

**Source-coverage reconciliation**: Rows may appear in multiple snapshots. Count:

- `raw_row_count` — total rows across ALL snapshots before deduplication (i.e. sum of row counts from each snapshot for the scoped collection)
- `logical_<entity>_count` — distinct business entities (by business key) after merging snapshot overlaps
- `duplicate_raw_count` — difference between raw and logical counts (rows that are the "extra" copies)

**Duplicate resolution rules** (consistent across all domains):

- A logical entity is identified by its stable business ID (transaction ID, event ID, charge ID, contact row ID).
- When the same logical ID appears in multiple snapshots, the occurrence in the **CERTIFIED** snapshot is retained; occurrences in PROVISIONAL or STALE snapshots are duplicates.
- When a CERTIFIED snapshot is not among the sources, use the most recent snapshot by timestamp, then fall back to lexicographically first snapshot ID.
- The retained snapshot ID must be reported for every duplicate group.

**For entity/contact collections**: Source rows with the same person identity (matching on normalized email or phone across source systems) form a duplicate cluster. The survivor row is selected by precedence: prefer rows from the source system that provides the most fields in the order listed in the schema (typically the system with the richest attribute coverage), breaking ties by the lexicographically largest row ID.

### Phase 4: Validation & Quality Metrics

For each logical entity, apply the domain-specific validation rules documented in the catalog schema:

**Common data-quality issues across domains**:

| Issue Class | Condition | Action |
|---|---|---|
| Missing required field | `null` or empty in a required column | Exclude entity from valid counts; add to invalid-ID list |
| Invalid value range | Value outside documented min/max (e.g. negative quantity, zero distance, out-of-range odometer) | Exclude from valid counts; quarantine the row |
| Unrecognized category | Free-text description or alias has no match in the reference aliases table | Quarantine; add to unrecognized list |
| Ambiguous category/alias | Description or alias matches MORE THAN ONE canonical category | Quarantine; count as ambiguous |
| Expected-vs-actual mismatch | The recognized canonical category differs from the `expected_*` column | Count as mismatch; the row may still be valid but is flagged |
| Timestamp issues | Missing, unparseable, or outside the business period | Exclude; add to invalid-ID list |
| Sequence regression | Odometer decreases between consecutive events for the same asset | Flag as regression; both events may still be valid |

**Quarantine**: An entity that cannot be used for its intended business purpose (has no usable contact channel, has an unresolvable category, has invalid physical measures) is quarantined. Quarantined entities are excluded from normalized totals, readiness counts, and spend/volume aggregations.

**Exception**: An entity with a category mismatch OR any quarantine condition. Exception counts include mismatches PLUS quarantines (but don't double-count entities that have both).

### Phase 5: Control Code Assignment

Internal control codes come from fixed enums listed in the answer template. Each code family maps to a business concern:

| Code Family | Codes | Meaning |
|---|---|---|
| Identity (`IC-*`) | IC-25, IC-40, IC-70, IC-90 | How the canonical identity was resolved (single-source, field-precedence, merged, contested) |
| Outreach (`OR-*`) | OR-15, OR-35, OR-60, OR-80 | Contact readiness or channel-availability disposition |
| Field Provenance (`FP-*`) | FP-20, FP-55, FP-75 | Which source system or snapshot provided the winning field values |
| Reference Basis (`RB-*`) | RB-17, RB-42, RB-83 | How a reference alias maps to a canonical classification |
| Source Basis (`SB-*`) | SB-24, SB-61, SB-79 | Which snapshot or source is the basis of truth for a given record |
| Ledger Disposition (`LD-*`) | LD-14, LD-31, LD-53, LD-72, LD-88 | Where a financial record routes in the ledger |
| Maintenance Source (`MS-*`) | MS-12, MS-47, MS-86 | Which system originated the maintenance event |
| History Route (`HR-*`) | HR-19, HR-33, HR-74 | How a maintenance event enters the corrected history |

**Code assignment logic** is inferred from the data, not memorized:

1. For each scoped entity (focus cluster, control case, reference ID, decision-panel entry), examine the reconciled data.
2. Determine the applicable code family from the answer template's `enum` values at that position.
3. Map the data evidence to the correct code by applying the rules implicit in the schema documentation and the case scope:
   - **RB codes** (reference basis): If an alias maps to exactly one canonical category → `RB-42` (direct match). If it is the default/fallback mapping → `RB-17` (default). If it maps but the relationship is indirect or exceptional → `RB-83` (indirect).
   - **SB codes** (source basis): `SB-61` for records sourced from the CERTIFIED snapshot. `SB-24` for records from PROVISIONAL snapshots. `SB-79` for records existing only in STALE or non-authoritative sources.
   - **LD codes** (ledger disposition): `LD-53` for quarantined records. `LD-31` for records with category mismatches. `LD-72` for clean valid records. `LD-14` for unrecognized (zero-match) records. `LD-88` for ambiguous (multi-match) records.
   - **IC codes** (identity): `IC-70` when identity is resolved by field-level precedence across multiple source systems. `IC-25` when from a single source only. `IC-90` when multiple sources contribute but identity is contested. `IC-40` when the record lacks usable identity fields.
   - **OR codes** (outreach): `OR-35` when all channels are ready. `OR-80` when no channel is usable. `OR-60` when only some channels are usable. `OR-15` when the entity is inactive (excluded from readiness).
   - **FP codes** (field provenance): `FP-55` when canonical values come from the primary/richest source system. `FP-20` when from a single secondary source. `FP-75` when fields are missing or unusable across all sources.
   - **MS codes** (maintenance source): `MS-47` for the primary fleet-management system. `MS-12` for the secondary/tracking system. `MS-86` for the telematics provider.
   - **HR codes** (history route): `HR-74` for events that enter the corrected history directly from the authoritative snapshot. `HR-33` for valid events that route through reconciliation. `HR-19` for events excluded from the corrected history (regressions, invalid events).

When the task prompt or case scope explicitly maps a condition to a code, that mapping takes precedence. Otherwise, infer from the data as described above.

### Phase 6: Aggregation & Certification Decision

**Normalized totals**: Sum valid (non-quarantined) entities only. Apply unit conversions from `/api/reference/conversions` when the raw data uses non-canonical units. Apply FX rates from `/api/reference/fx` when the raw data uses non-base currencies. Round to the contract precision (typically 2 decimal places for amounts, 4 for rates).

**Rankings**: Sort by the primary metric descending, then by the documented tie-breaks (typically entity ID ascending).

**Certification decision**: Compare computed metrics against thresholds in `case_scope.json`:
- If no issues found → `PASS` / `RELEASE`
- If issues exist but below the exception threshold → `PASS_WITH_EXCEPTIONS` / `REVIEW_EXCEPTIONS`
- If issues exceed thresholds or a certification gate is triggered → `HOLD` / `BLOCK_AND_REMEDIATE`

**Channel readiness** (entity collections only): An entity is eligible when it is active AND has at least one usable email or phone. A channel is ready when consent is GRANTED. Count entities by their readiness partition (both channels ready, email only, phone only, not ready).

**Region/depot rollups**: Group canonical entities by their region/depot field. Sort the groups lexicographically. Each group reports its canonical entity count.

## Output Rules

1. **Return only one JSON object**. No markdown fences, no commentary, no trailing text.
2. **Match the answer template exactly** — every required key, no extra keys.
3. **Sort all ID arrays lexicographically ascending** unless the template specifies otherwise.
4. **Deduplicate all ID arrays** — use `uniqueItems` semantics.
5. **Preserve numeric precision**: integers for counts, exactly the declared decimal places for rates and amounts.
6. **Use stable IDs from the public data** — do not invent or generate IDs.
7. **Honor all `enum` constraints** — every code must come from the allowed set.
8. **Honor all `pattern` constraints** — IDs must match the declared regex.
9. **Order array elements** as specified in the template (usually by the ID field ascending).
10. **Use empty arrays `[]` only when the template explicitly allows zero items**; otherwise supply all required items (respect `minItems`).

## Domain-Specific Notes

### Transaction Audits (Fuel, Freight)

- The logical key is the transaction/charge ID.
- `expected_*` columns hold the expected category/class; the actual category is resolved through the aliases reference table.
- Quarantine reasons must be broken out into reason-specific counts (`ambiguous_alias`, `unrecognized_alias`, `invalid_distance`, `invalid_weight`, `invalid_quantity`).
- The exception-merchant/carrier ranking is ordered by the primary exception metric descending, then by merchant/carrier ID ascending.
- Mismatch lists include ALL transactions/charges with an expected-vs-actual mismatch, not just those in the scoped decision panels.

### Maintenance Audits

- The logical key is the maintenance event ID.
- Events may be duplicated across a CERTIFIED and a PROVISIONAL snapshot. Retain the certified occurrence.
- Invalid events (missing/bad timestamps, invalid odometer, negative/extreme labor hours) are excluded from corrected metrics but reported in `invalid_event_ids`.
- Odometer regression is detected per asset: when an event's odometer is lower than the previous event's for the same asset. Regression events are NOT added to `invalid_event_ids` — they are reported separately in `corrected_metrics.regression_event_ids`.
- Corrected distance uses only valid events, computing: `last_reliable_odometer - first_reliable_odometer` per asset, then summing across assets.

### Entity/Contact Certifications

- The logical entity is a canonical person; source rows from different systems may map to the same person.
- Duplicate clusters are formed by matching on normalized email (lowercase, trimmed) or phone digits.
- The survivor row is the source row selected as the canonical representation of the merged entity.
- Inactive entities are excluded from readiness eligibility.
- Channel readiness partitions are mutually exclusive counts.
- Focus people reports must include source-system provenance for each canonical field (name, contact, depot, consent).

## Common Pitfalls

- **Forgetting to paginate**: If a GET endpoint returns paginated results, you must follow ALL pages. An incomplete dataset produces wrong counts.
- **Mixing snapshot and collection scope**: The `scoped_raw_row_count` counts rows within the time window from ALL snapshots. The `authoritative_row_count` counts rows in the authoritative snapshot only. These are different numbers.
- **Double-counting exceptions**: An entity with both a mismatch AND a quarantine condition counts as ONE exception, not two.
- **Including quarantined rows in totals**: Quarantined entities never contribute to normalized volume, spend, weight, or distance sums.
- **Sort order**: Default to lexicographic ascending for ID arrays. For numeric arrays and ranked lists, follow the contract's explicit ordering.
- **Code value expansion**: The answer template's enums are the only allowed values. Do not use expansions or descriptions — only the compact codes.
- **Business cutoff**: Rows exactly at the cutoff timestamp are IN scope (`<=`, not `<`).
