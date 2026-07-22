# Asteria Fleet Data Quality Hub — Audit & Certification Skill

## Purpose

Reconcile, audit, and certify fleet-domain datasets published through the **Asteria Fleet Data Quality Hub** (a shared, read-only HTTP API). Produce a structured JSON certification report conforming to a supplied answer-template schema.

## When to Use

This skill applies whenever a task involves:
- An Asteria collection name, case-scope payload, and answer-template payload provided as input files (`prompt.txt`, `payloads/case_scope.json`, `payloads/answer_template.json`).
- Runtime connection details supplied in a separate `environment_access.md`.
- Instructions to query the hub, reconcile overlapping source records, compute quality/integrity metrics, assign opaque control codes, and render a certification or close decision.

## Input File Contract

The task directory contains:

| File | Role |
|---|---|
| `prompt.txt` | Natural-language description of the specific audit or certification requested. |
| `payloads/case_scope.json` | Scoped parameters: collection ID, business cutoff, focus entities, decision-panel IDs, thresholds, ranking rules, anchor cases. |
| `payloads/answer_template.json` | JSON Schema or field contract for the required output. Every key, type, enum, and ordering rule is normative. |
| `environment_access.md` | (Provided at runtime) Base URL, `Authorization` header, allowed endpoints, and query syntax. |

## Environment Bootstrap

1. **Read** `environment_access.md` to obtain:
   - `base_url` — root of the hub.
   - `credentials.query_authorization_header` — full `Authorization: Bearer <token>` string.
2. **Use** only the `allowed_endpoints` listed in that file. Typical patterns:
   - `GET /api/catalog/collections`
   - `GET /api/catalog/schema` (query `?collection=<id>` to get field definitions)
   - `GET /api/contacts`, `GET /api/transactions/fuel`, `GET /api/transactions/freight`, `GET /api/maintenance/events` (domain data)
   - `GET /api/reference/aliases`, `GET /api/reference/conversions`, `GET /api/reference/fx` (reference data)
   - `GET /api/source-snapshots` (`?collection=<id>` to list snapshots)
   - `POST /api/query` — send `{"query": "<SQL>"}` with the auth header.
3. **Every** HTTP request includes the authorization header from step 1.

## Discovery & Exploration

### Find the Collection

- `GET /api/catalog/collections` returns all collections. Match the `collection_id` from `case_scope.json`.

### Learn the Schema

- `GET /api/catalog/schema?collection=<id>` returns field names, types, and semantics.

### Inspect Source Snapshots

- `GET /api/source-snapshots?collection=<id>` returns every registered snapshot for the collection. Each snapshot has a stable `snapshot_id`, a row count, and a status (`certified`, `provisional`, etc.).

### Page Through Large Datasets

- For collections larger than one page, use `POST /api/query` with SQL to retrieve the full dataset or to apply server-side filters. This is the primary mechanism for slicing by date range, region, asset, or other dimensions.

## Reconciliation Methodology

### Authoritative Snapshot Selection

1. Identify the snapshot with status `certified` (or the best available status) whose timestamp is ≤ the business cutoff.
2. When rows appear in multiple snapshots under the same logical ID, prefer the authoritative snapshot. If equal status, prefer the most recent snapshot within the cutoff.

### Duplicate Detection

1. **Within a collection**: Group source rows that share the same logical identity key (e.g., contact email, transaction ID, event ID). Each group of ≥2 rows forms a duplicate cluster.
2. **Across snapshots**: When the same logical key appears in multiple snapshots, it is a cross-snapshot duplicate. The authoritative snapshot's copy is retained; others count as duplicate raw rows.

### Survivor / Master Selection

For each duplicate cluster:
- A **precedence rule** selects one row as the survivor. Precedence may be based on source system priority (stated in the prompt or case scope), snapshot status, recency, or field completeness.
- If no explicit rule, default to the authoritative snapshot's row; if same snapshot, prefer the row with the most non-null canonical fields.
- The survivor's row ID becomes the canonical entity identifier.

### Business Cutoff

- All time-stamped data is evaluated as of the `business_cutoff` / `as_of` / `cutoff_at` timestamp in `case_scope.json`. Records with timestamps after the cutoff are excluded.

## Quality & Integrity Metrics

### Row-Level Metrics

| Metric | Definition |
|---|---|
| `raw_row_count` | Total source rows in scope (across all snapshots before dedup). |
| `canonical_entity_count` | Distinct canonical entities after deduplication (including quarantined entities). |
| `duplicate_cluster_count` | Number of multi-row clusters merged into one canonical entity. |
| `duplicate_raw_count` | `raw_row_count` − `logical_*_count` (superfluous rows that are duplicates). |
| `quarantine_*_count` | Rows/entities excluded from valid totals due to unresolvable data quality issues. |

### Quarantine Conditions (Domain-Specific)

Quarantine applies when a row cannot contribute to valid totals. Common triggers:

| Domain | Quarantine Trigger |
|---|---|
| Contacts | No usable email AND no usable phone. |
| Fuel | Non-positive quantity, unrecognized fuel category, ambiguous category match. |
| Freight | Unrecognized/ambiguous service-class alias, non-positive weight, non-positive distance. |
| Maintenance | Missing or unparseable timestamp, invalid odometer reading, negative labor hours. |

The quarantine rate is: `distinct_quarantined_rows / canonical_entity_count`, rounded to the precision declared in the answer template.

### Integrity Issue Counts

For each integrity dimension declared in the answer template, count distinct rows or events exhibiting the defect. A single row may contribute to multiple counts.

### Corrected / Normalized Totals

- Exclude quarantined records from all normalized totals.
- **Unit conversions**: Use `/api/reference/conversions` to convert raw measures to the canonical unit (e.g., L, KG, KM). Apply conversion factors multiplicatively.
- **Currency normalization**: Use `/api/reference/fx` to convert spend to the base currency (typically USD). Apply the rate valid at the transaction date.
- **Precision**: Follow the precision declarations in the answer template (usually 2 decimal places for amounts, 4 for rates).
- **Valid totals**: Sum over valid (non-quarantined) records only.

## Exception Classification

### Category/Class Mismatch

When a record has both an **expected** category (from its declared classification) and a **recognized** category (from reference data lookup), and they differ, it is a mismatch. Mismatched records are valid for totals (they are not quarantined) but contribute to exception counts.

### Unrecognized / Ambiguous

- **Unrecognized**: The record's descriptive field maps to zero canonical categories in the reference data.
- **Ambiguous**: The descriptive field maps to more than one canonical category.
- Both are reported in the unrecognized/ambiguous lists (sorted lexicographically).

### Invalid Measures

- Non-positive or null values for quantity fields (volume, weight, distance, labor hours, odometer reading).
- Out-of-range values (e.g., extreme labor hours exceeding a reasonable threshold).

### Odometer Regression

- Within an asset's maintenance history ordered by timestamp, any event where the odometer reading is less than the previous reading.

## Focus-Entity Reporting

For every entity (cluster, asset, person) listed in `case_scope.json`'s focus section:

1. **Resolve the anchor row** by its seed/source row ID from the case scope.
2. **Traverse the duplicate cluster** to collect all member row IDs (deduplicated, sorted lexicographically).
3. **Select the survivor** row ID per the reconciliation methodology.
4. **Populate canonical fields**: Apply field-level precedence rules (source system priority) to select the authoritative value for each canonical field (name, email, phone, city, etc.).
5. **Source attribution**: For each canonical field, record which source system supplied the value.
6. **Resolution outcome**: Classify as `SINGLE_SOURCE` (no merge needed), `FIELD_LEVEL_PRECEDENCE_APPLIED` (merged with precedence), `CONTESTED_NO_AUTOMERGE` (watchlist conflict), or `NO_USABLE_CONTACT` (quarantined).

## Channel / Communication Readiness

For contact-domain tasks:
- A **usable email** is a non-null, well-formed email address.
- A **usable phone** is a non-null phone number with at least one digit.
- An entity is **readiness-eligible** when its record is ACTIVE and has at least one usable channel.
- A channel is **ready** when consent is GRANTED.
- Partition entities into four mutually exclusive buckets: `both` (email+phone ready), `email_only`, `phone_only`, `not_ready`.
- Readiness counts are computed across **readiness-eligible** canonical entities only.
- For depot/region rollups, each entity is counted under its canonical region; the disposition counts (dispatchable, blocked-consent, blocked-no-contact, blocked-inactive) sum to the total for that depot.

## Control-Code Assignment

The hub emits opaque alphanumeric codes that encode internal policy decisions. The answer template declares the allowed code universe (enums). To assign codes:

### Decision Panels

For each scoped public ID (reference alias, transaction, charge, maintenance event, anchor case):

1. **Retrieve the data** for each ID from the hub.
2. **Inspect its attributes** in the reconciled dataset: source snapshot, category match result, measure validity, deduplication outcome, field provenance.
3. **Infer the code** by comparing the ID's data profile against the pattern exhibited by all other IDs assigned the same code in the training data. Codes partition IDs by:
   - **Source basis** (`SB-*`): Whether the record is single-snapshot, multi-snapshot retained, or multi-snapshot duplicate.
   - **Ledger disposition** (`LD-*`): Whether the record is valid, quarantined, mismatched, or unrecognized — routing to different financial treatment.
   - **Reference policy** (`RB-*`): Whether the alias maps uniquely to a recognized class, is ambiguous, or is unrecognized.
   - **Identity** (`IC-*`): Strength of identity resolution — single-source exact match, multi-source consensus, multi-source contested, or weak-link quarantine.
   - **Outreach** (`OR-*`): Contact readiness — both channels ready, single channel, not ready, or inactive.
   - **Field provenance** (`FP-*`): Whether all fields came from one source, mixed sources with agreement, or mixed sources with conflicts.
   - **Maintenance source** (`MS-*`): Source system that originated the maintenance event.
   - **History route** (`HR-*`): Whether the event is a unique occurrence, a duplicate with retained record, or a duplicate with discarded record.

### Inference Method

For each code family, classify scoped IDs by their reconciled data profile. The correct code for each ID is the one whose underlying attribute pattern matches the ID's actual state. Do not hardcode mappings — derive them from the data returned by the hub for each ID.

### Anchored Control Cases

- Each anchored case in `control_case_anchors` or `policy_control_cases` ties a case ID to a list of evidence row IDs.
- Retrieve each evidence row from the hub. Assign the code that reflects the aggregated data quality profile of those rows (e.g., all-from-one-source → one FP code; mixed → another).

### Readiness Partitions

- Assign one outreach code (`OR-*`) to each of the four readiness buckets (`both`, `email_only`, `phone_only`, `not_ready`). The code reflects the communication richness of that bucket.

### Inactive Exclusion

- Assign one outreach code to the population of inactive records excluded from readiness.

## Rankings

When the case scope requests a ranked list (top-N merchants, carriers, assets):

1. **Compute the primary metric** for each entity from reconciled data (e.g., exception count, mismatch spend USD, rejected event count).
2. **Sort** by the primary metric descending.
3. **Break ties** using the declared tie-break fields (typically entity ID ascending).
4. **Limit** to the declared N.
5. **Populate** all required per-entity fields for each ranked entry.

## Regional / Dimensional Rollups

- Group canonical entities by the declared dimension (region, depot, fuel type, service class).
- Produce one entry per distinct dimension value present in the reconciled data.
- Sort entries lexicographically by the dimension value.
- Sum entity counts and normalized measures within each group.

## Certification / Close Decision

The final status and action are determined by comparing computed quality metrics against thresholds declared in `case_scope.json`:

| Pattern | Status | Action |
|---|---|---|
| All thresholds satisfied (e.g., quarantine rate at or below `pass_max_quarantine_rate`) | `PASS` | `RELEASE` |
| Intermediate thresholds satisfied (e.g., quarantine rate ≤ `pass_with_exceptions_max_quarantine_rate`) | `PASS_WITH_EXCEPTIONS` | `REVIEW_EXCEPTIONS` |
| Any critical threshold violated, or specific hard-gate conditions met | `HOLD` | `BLOCK_AND_REMEDIATE` |

The `status_action_map` in the case scope defines the exact mapping. When the case scope specifies a hard gate (e.g., "odometer_regression → HOLD"), that condition overrides threshold-based decisions.

## Output Compliance

1. **Schema conformance**: Every key, type, enum value, `required` constraint, `minItems`/`maxItems`, `pattern`, `multipleOf`, and `additionalProperties` rule in the answer template is binding.
2. **Ordering**: Arrays declared with a sort order MUST be sorted accordingly (lexicographically ascending by ID, rank ascending, dimension ascending, etc.).
3. **Deduplication**: Arrays declared `uniqueItems: true` MUST contain no duplicates.
4. **Precision**: Numeric values follow the declared precision (2 decimal places for currency/measures, 4 for rates, exact integers for counts).
5. **Stable IDs**: All identifiers are the exact stable IDs from the hub or case scope.
6. **JSON only**: No Markdown, no commentary, no trailing text.

## Execution Checklist

- [ ] Read `environment_access.md` for base URL and credentials.
- [ ] Read `payloads/case_scope.json` for collection ID, cutoff, focus entities, thresholds.
- [ ] Read `payloads/answer_template.json` for output structure, enums, ordering rules.
- [ ] `GET /api/catalog/collections` — confirm collection exists.
- [ ] `GET /api/catalog/schema?collection=<id>` — learn fields.
- [ ] `GET /api/source-snapshots?collection=<id>` — identify authoritative snapshot.
- [ ] `GET /api/reference/aliases`, `/api/reference/conversions`, `/api/reference/fx` — load reference data.
- [ ] Retrieve domain data (paged queries as needed) from the relevant endpoint or via `POST /api/query`.
- [ ] Apply business cutoff filter.
- [ ] Deduplicate — detect clusters, select survivors, count duplicates.
- [ ] Classify exceptions — mismatches, unrecognized, quarantines, invalid measures.
- [ ] Compute normalized totals using conversions and FX.
- [ ] Resolve focus entities with full member lists, canonical fields, and source attribution.
- [ ] Compute channel readiness partitions (for contact tasks).
- [ ] Assign control codes to every scoped decision-panel entry, anchor case, readiness partition, and exclusion.
- [ ] Rank entities per case-scope rules.
- [ ] Compute regional/dimensional rollups.
- [ ] Apply certification thresholds and hard gates to determine status and action.
- [ ] Assemble the output JSON, validate against the answer template, and return only that object.
