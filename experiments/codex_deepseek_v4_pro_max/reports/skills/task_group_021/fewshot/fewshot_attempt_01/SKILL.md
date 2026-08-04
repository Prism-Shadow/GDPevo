# Asteria Fleet Data Quality Hub — Reconciliation & Certification Skill

## Overview

This skill provides reusable instructions for completing data-quality audit, reconciliation, and certification tasks against the Asteria Fleet Data Quality Hub. The hub exposes structured fleet-domain data across multiple overlapping source snapshots through a REST API and a read-only SQL query interface. Every task follows a common pipeline: discover available data, query and extract records, reconcile overlapping sources, normalize values through reference tables, detect and classify quality issues, assign internal control codes, and render a certification decision.

## When to Use

Apply this skill when a prompt references the Asteria Fleet Data Quality Hub, a `<>` base-URL placeholder, the API endpoints listed below, or any of the following task domains:

- Partner / contact onboarding certification
- Fuel-purchase normalization and audit
- Maintenance-log integrity certification
- Field-service roster / contact-readiness briefs
- Freight-charge cleanup and accrual reconciliation

## Hub API Reference

### Base URL

The base URL is supplied at runtime as `<TASK_ENV_BASE_URL>` (or equivalent placeholder). Every endpoint below is appended to that base.

### GET Endpoints (unauthenticated unless noted)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/catalog/collections` | List available data collections (name, snapshot members, status). |
| `GET /api/catalog/schema` | Full schema: tables, views, columns, types, and join metadata. |
| `GET /api/contacts` | Raw contact records across all source systems. |
| `GET /api/transactions/fuel` | Fuel purchase transaction records. |
| `GET /api/transactions/freight` | Freight charge transaction records. |
| `GET /api/maintenance/events` | Maintenance event records. |
| `GET /api/reference/aliases` | Stable-ID alias mappings (e.g., category aliases, service-class aliases). |
| `GET /api/reference/conversions` | Unit-of-measure conversion factors (KG, LB, KM, MI, L, GAL, etc.). |
| `GET /api/reference/fx` | Foreign-exchange rates keyed by currency pair and date. |
| `GET /api/source-snapshots` | Snapshot metadata: snapshot IDs, collection membership, certification status (CERTIFIED / PROVISIONAL / STALE). |

### POST /api/query (authenticated read-only SQL)

- **URL**: `POST /api/query`
- **Headers**: `Content-Type: application/json`, `Authorization: Bearer asteria-read-021`
- **Body**: `{"query": "<SELECT or WITH query string over public views>"}`
- **Notes**:
  - Only `SELECT` and `WITH` (CTE) queries are permitted.
  - Query against the public views exposed by the schema. The schema endpoint reveals exact view and column names.
  - Data may span multiple pages. When row counts approach any apparent response-size limit, use `LIMIT` / `OFFSET` or range predicates to paginate.
  - There is no stored-procedure or DDL access.

## General Task Pipeline

Every task follows these phases. Not every phase is required for every task, but the ordering is reliable.

### Phase 1 — Orientation

1. Read the prompt and `payloads/case_scope.json` carefully. Note:
   - The `collection_id` or `case_id` that identifies the data source.
   - The `business_cutoff` / `cutoff_at` / `as_of` timestamp that defines the point-in-time view.
   - Any `focus_` lists (clusters, assets, people, charge IDs, etc.) that limit the scope.
   - Thresholds (`status_thresholds`, `certification_gate`, etc.) that drive the certification decision.
   - The ranking / ordering rules declared in the case scope or answer template.
2. Read `payloads/answer_template.json`. This is the output contract. Every required key, enum value, array size constraint (`minItems` / `maxItems`), pattern constraint, and ordering rule must be satisfied exactly. Do not add extra keys.
3. Read `environment_access.md` for the actual base URL and any runtime-specific notes.

### Phase 2 — Catalog and Snapshot Discovery

1. `GET /api/catalog/collections` — Confirm the target collection exists and note its structure.
2. `GET /api/catalog/schema` — Inspect the public views relevant to the task. Identify:
   - The primary data view (e.g., contacts, fuel transactions, freight charges, maintenance events).
   - Any associated reference / lookup views.
   - Column names, types, and nullable constraints.
   - The snapshot / source columns that distinguish overlapping raw records.
3. `GET /api/source-snapshots` — Identify every snapshot belonging to the target collection. Note:
   - Certification status (`CERTIFIED` takes precedence over `PROVISIONAL` over `STALE`).
   - Snapshot IDs that will be needed in WHERE clauses when querying the data view.

### Phase 3 — Data Extraction

1. Determine the authoritative snapshot:
   - Prefer the snapshot whose status is `CERTIFIED` and whose timestamp is <= business cutoff.
   - When two snapshots cover the same logical record, retain the occurrence from the higher-priority snapshot (CERTIFIED > PROVISIONAL > STALE).
2. Query the data view via `POST /api/query`. Use predicates on the snapshot column to scope to the relevant snapshots. Apply the business-cutoff timestamp filter.
3. Paginate as needed. Summing counts across pages must equal the final raw row total.

### Phase 4 — Reference Table Normalization

1. `GET /api/reference/aliases` — Resolve raw category / class / type strings to canonical recognized values through alias mappings. An alias may map to:
   - Exactly one canonical value → adopt it.
   - Zero canonical values → the raw value is *unrecognized*.
   - More than one canonical value → the raw value is *ambiguous*.
2. `GET /api/reference/conversions` — Convert raw physical measures (weights, distances, volumes) to the canonical unit declared in the case scope (`canonical_weight_unit`, `canonical_volume_unit`, `canonical_distance_unit`). Apply the conversion factor for each raw unit.
3. `GET /api/reference/fx` — Convert raw currency amounts to the declared `base_currency`. Match on the raw currency code and the transaction / event date. Use the rate effective for that date.

### Phase 5 — Cross-Source Reconciliation and Deduplication

1. Identify all raw rows that represent the same logical entity (contact, transaction, event, charge) across different snapshots. The schema typically exposes a stable logical ID.
2. For each logical entity with multiple raw occurrences:
   - Record the `snapshot_ids` list (sorted lexicographically).
   - Retain the occurrence from the highest-priority snapshot.
   - Count the excess raw occurrences as duplicates (`duplicate_raw_count` = total raw rows − distinct logical entities).
3. For contact/identity tasks, additionally cluster rows that represent the same real-world person across different source systems or row IDs. Membership clustering follows identity-resolution rules embedded in the data itself (shared identifiers, name similarity, or explicit cluster hints).

### Phase 6 — Quality Issue Detection

Apply the following checks to every retained occurrence. Each check results in the record being counted in the appropriate issue bucket or flagged for quarantine.

| Issue Category | Detection Rule | Disposition |
|----------------|----------------|-------------|
| Mismatch | Expected category/class differs from recognized canonical category/class. | Count in mismatch totals; record remains in valid/normalized totals unless also quarantined. |
| Unrecognized / Ambiguous | Raw category/class/alias has zero or >1 canonical mapping. | Quarantine: exclude from normalized totals. |
| Invalid quantity | Physical measure ≤ 0 or null (weight, distance, volume, etc.). | Quarantine. |
| Invalid timestamp | Null, unparseable, or outside business period. | Reject from valid set. |
| Missing timestamp | Null timestamp where one is required. | Reject. |
| Invalid odometer | Outside valid range or null. | Reject. |
| Negative labor | Labor hours < 0. | Reject. |
| Extreme labor | Labor hours exceeding a plausible threshold (> 24 or similar). | Reject. |
| Odometer regression | For a given asset ordered by event timestamp, a later reading is lower than an earlier reading. | Count as regression; affected event IDs and asset IDs go into regression lists. |

### Phase 7 — Compute Normalized Totals

1. Valid set = retained occurrences minus quarantined occurrences minus invalid/rejected occurrences.
2. Group by canonical dimension (fuel type, service class, region, depot, etc.) and sum:
   - Count of valid records.
   - Sum of canonicalized physical measures (rounded to declared decimal precision, typically 2 decimal places).
   - Sum of USD-normalized spend (rounded to 2 decimal places).
3. For ranking outputs (merchants, carriers, assets):
   - Compute exception counts (mismatch + quarantine per entity).
   - Sort by the primary metric descending, then by tie-break fields ascending.

### Phase 8 — Control Code Assignment

Many answer templates require internal Asteria control codes. These are opaque enumerations whose meanings are inferred from the resolved data, not from external documentation. The allowed code sets are always declared in the answer template's enum constraints.

**Common code families:**

- `IC-25`, `IC-40`, `IC-70`, `IC-90` — Identity codes. Assigned based on how a contact's identity was resolved (e.g., single-source match, multi-source merge, contested, quarantined).
- `FP-20`, `FP-55`, `FP-75` — Field provenance codes. Assigned based on which source system supplied the surviving field value.
- `OR-15`, `OR-35`, `OR-60`, `OR-80` — Outreach / readiness codes. Assigned based on consent + channel availability status.
- `MS-12`, `MS-47`, `MS-86` — Maintenance source codes.
- `HR-19`, `HR-33`, `HR-74` — History route codes.
- `RB-17`, `RB-42`, `RB-83` — Reference policy codes (alias resolution disposition).
- `SB-24`, `SB-61`, `SB-79` — Source basis codes (which snapshot/record type was authoritative).
- `LD-14`, `LD-31`, `LD-53`, `LD-72`, `LD-88` — Ledger disposition codes (how a transaction is routed for accounting).

**Assignment principle:** For each scoped entity (focus cluster, control case, decision-panel entry), inspect the resolved state of that entity, compare it against the reference data, and select the code from the allowed enum whose semantic role matches the disposition. The correct mapping is deterministic given the data; it is typically inferred from:
- Which source system supplied the surviving value.
- Whether the record was quarantined, contested, or clean.
- The consent / channel-readiness state.
- The reconciliation outcome (single-source, merged, etc.).

### Phase 9 — Certification Decision

1. Compute the quarantine rate (or equivalent exception metric) defined in the case scope.
2. Compare against the declared thresholds:
   - `PASS` when below `pass_max_quarantine_rate` (or equivalent threshold).
   - `PASS_WITH_EXCEPTIONS` when below `pass_with_exceptions_max_quarantine_rate` (or equivalent).
   - `HOLD` otherwise.
3. Map status to action using `status_action_map` (or equivalent).
4. For tasks with a hard certification gate (e.g., odometer regression gate), `HOLD` / `BLOCK_AND_REMEDIATE` applies regardless of other metrics if the gate condition triggers.

### Phase 10 — Assembly and Output

1. Build the JSON object strictly following `payloads/answer_template.json`.
2. Sort every array as specified in the template's ordering rules (usually lexicographic ascending, or by a declared sort key).
3. Ensure every `minItems` / `maxItems` constraint is met.
4. Use the declared numeric precision (always exact integers for counts; 2 decimal places for floats).
5. Output the JSON and nothing else — no Markdown fences, no commentary.

## Task-Specific Guidance

### Contact / Identity Resolution Tasks (Partner Onboarding, Field Service Roster)

- Use `GET /api/contacts` for raw data, or `POST /api/query` against the contacts view.
- Canonical entities are resolved by clustering rows from different source systems (HR Directory, Dispatch, Identity Registry, Compliance Master, Partner Portal, CRM) that represent the same person.
- For each cluster: select a survivor row, pick canonical field values by source-system precedence (stated in the prompt or inferred from the data), and record which system supplied each canonical field.
- Quarantine rows with no usable email or phone.
- Channel readiness: an entity is eligible only when active AND has at least one usable email or phone. A channel is ready only when consent is GRANTED. Partition into `both`, `email_only`, `phone_only`, `not_ready`.
- Identifier watchlist: check whether watchlist anchors map to the same canonical person or different people; report contested cases.

### Fuel Audit Tasks

- Use `GET /api/transactions/fuel` or query the fuel transactions view.
- Match each transaction's `description` against `/api/reference/aliases` to determine the canonical `fuel_type`.
- Mismatch: expected fuel category ≠ recognized category.
- Unrecognized: zero or multiple canonical matches.
- Normalize volume to `L` via `/api/reference/conversions`.
- Normalize spend to `USD` via `/api/reference/fx`.
- Quarantined transactions (unrecognized, invalid quantity) are excluded from normalized totals.

### Maintenance Log Tasks

- Use `GET /api/maintenance/events` or query the maintenance events view.
- Check: missing/invalid timestamps, invalid odometer readings, negative labor, extreme labor, odometer regression.
- Odometer regression is detected per asset: sort events by timestamp, compare consecutive readings.
- Corrected distance = sum across assets of (last reliable odometer − first reliable odometer) in Q1 period.
- Invalid events are excluded from corrected metrics.

### Freight Charge Tasks

- Use `GET /api/transactions/freight` or query the freight charges view.
- Match alias IDs against `/api/reference/aliases` for service class resolution.
- Convert weight to `KG` and distance to `KM` via `/api/reference/conversions`.
- Convert spend to `USD` via `/api/reference/fx`.
- Quarantine: unrecognized/ambiguous aliases, nonpositive weight, nonpositive distance.
- Carrier ranking: sort by mismatch spend descending, carrier ID ascending.

## Pagination Pattern

When a data view returns more rows than fit in a single response:

```sql
SELECT <columns> FROM <view>
WHERE snapshot_id IN ('<snap1>', '<snap2>')
  AND <timestamp_col> <= '<cutoff>'
ORDER BY <stable_id>
LIMIT <batch_size> OFFSET <offset>
```

Accumulate rows across pages and verify total count against `COUNT(*)` queries.

## Common Mistakes to Avoid

1. **Treating provisional snapshots as authoritative.** Always prefer CERTIFIED. When two records overlap, retain CERTIFIED and discard PROVISIONAL/STALE.
2. **Including quarantined rows in normalized totals.** Mismatch rows stay in totals; quarantined rows do not.
3. **Confusing mismatch and quarantine.** A mismatch (expected ≠ actual) is a valid row flagged for review. A quarantine (unrecognized class, invalid measure) is excluded from valid totals.
4. **Sorting violations.** Lexicographic ascending is the default array order unless the answer template explicitly declares a different sort. Always read the `x-ordering_rules` or field descriptions.
5. **Rounding before summing.** Sum raw values first in the canonical unit, then round the total. Rounding individual rows before summing introduces error.
6. **Outputting Markdown wrappers.** The answer must be raw JSON with no ``` fences.
7. **Missing control codes.** Every scoped entity listed in the case scope's decision panels, focus clusters, or control cases must have a code assignment in the output.
8. **Using hard-coded values from train examples.** All counts, IDs, codes, and totals must be derived from the actual runtime data, not copied from training answers.

## Required Runtime Inputs

Every task invocation requires two files alongside the prompt:

- `payloads/case_scope.json` — Defines the collection, cutoff, scoped entities, thresholds, and ranking rules.
- `payloads/answer_template.json` — Defines the exact output shape, required keys, allowed enums, array sizes, and ordering rules.
- `environment_access.md` — Supplies the actual `<TASK_ENV_BASE_URL>` and any auth credentials.
