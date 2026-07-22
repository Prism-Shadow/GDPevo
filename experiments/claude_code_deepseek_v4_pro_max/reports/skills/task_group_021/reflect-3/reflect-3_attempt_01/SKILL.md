# Asteria Fleet Data Quality Hub — Reconciliation Skill

## Purpose
Use the Asteria Fleet Data Quality Hub REST API to audit, reconcile, classify, and normalize multi-source fleet records for a business-scoped collection, producing a structured answer that conforms exactly to a supplied answer-template contract.

## Step 1 — Understand the Data Landscape

### 1.1 Discover available collections
```
GET /api/catalog/collections
```
Returns every available collection with its `collection_id`, `family`, `source_systems`, `time_start`/`time_end`, and approximate row count. Match the `collection_id` from the task's case scope (`payloads/case_scope.json`) to confirm it exists.

### 1.2 Inspect the logical schema
```
GET /api/catalog/schema
```
Returns the full set of logical views (`v_contacts`, `v_fuel_transactions`, `v_freight_charges`, `v_maintenance_events`, `v_source_snapshots`, `v_reference_aliases`, `v_unit_conversions`, `v_fx_rates`). Each view lists every field name, type, and business meaning. Use this to understand which columns are available and what they represent before writing queries.

### 1.3 Read the answer template and case scope
Every task provides:
- **`payloads/case_scope.json`** — collection id, business cutoff, focus items, ranking policies, certification thresholds, and any required stable-ID panels.
- **`payloads/answer_template.json`** — the exact output JSON schema (required keys, types, enums, array lengths, sort orders).

Parse both carefully. The answer template defines what to produce; the case scope defines what to operate on and how.

## Step 2 — Examine Reference Data

### 2.1 Reference aliases
Query `v_reference_aliases` filtered by `domain`:
```
SELECT * FROM v_reference_aliases WHERE domain = '<domain>'
```
Aliases map raw source text (e.g. "road diesel") to canonical values (e.g. "DIESEL"). Common domains: `fuel`, `freight`.

**Alias classification rules:**
- Use only aliases with `reference_status = 'ACTIVE'`. INACTIVE and PROVISIONAL aliases are not authoritative.
- When multiple alias texts could match a description, apply **longest-subsumption-first**: if a longer alias contains a shorter alias at the same position, only the longer match counts. This prevents false multi-matches (e.g. "premium unleaded" matching both "premium unleaded"→PREMIUM_UNLEADED and "unleaded"→UNLEADED).
- Use `\b` word-boundary matching so substrings inside unrelated words are not matched (e.g. "biodieseline" must not match "diesel").
- A description matching **zero** aliases is *unrecognized*. A description matching **more than one** non-subsumed alias from *different* canonical families is *ambiguous*. Both are quarantined.
- A description matching exactly one canonical value becomes the *recognized category*.

### 2.2 Unit conversions
```
SELECT * FROM v_unit_conversions WHERE kind = '<kind>'
```
Kinds: `volume` (L, US_GAL, IMP_GAL), `weight` (KG, LB), `distance` (KM, MI).

Convert source-unit values to the canonical unit by multiplying: `canonical = source_value × factor`. Round to the precision declared in the conversion row (typically 3 significant decimal places), then round the final aggregated totals to the decimal places required by the answer template (typically 2).

### 2.3 Foreign-exchange rates
```
SELECT * FROM v_fx_rates WHERE rate_status = 'CERTIFIED' AND rate_date <= '<cutoff>' ORDER BY rate_date ASC
```
Use only `CERTIFIED` rates. For a transaction on date *D*, use the CERTIFIED rate whose `rate_date` is the latest date ≤ *D*. Convert non-USD amounts by multiplying: `usd = amount × usd_per_unit`.

## Step 3 — Reconcile Source Snapshots

### 3.1 Query source snapshots
```
SELECT * FROM v_source_snapshots WHERE collection_id = '<id>'
```
Each collection may have one or more snapshots (e.g. `*-certified`, `*-provisional`, `*-s01/s02/s03`). Note each snapshot's `source_system`, `snapshot_status` (CERTIFIED / PROVISIONAL / STALE), `row_count`, and `business_cutoff`.

### 3.2 Determine the authoritative snapshot
The CERTIFIED snapshot is authoritative over PROVISIONAL. When the same business record appears in multiple snapshots (matched by its stable ID — `transaction_id`, `event_id`, or `row_id`), **retain the row from the authoritative snapshot** and count the discarded row as a duplicate.

### 3.3 Count duplicates
Duplicate raw row count = sum over every multi-snapshot business record of (total occurrences − 1). This is the number of raw rows discarded during deduplication.

## Step 4 — Classify Records

### 4.1 For transaction/freight audit tasks
For each deduplicated logical record, classify into exactly one of these mutually-exclusive dispositions:

| Disposition | Condition |
|---|---|
| **Invalid quantity** | Quantity/weight/distance ≤ 0 (non-positive) |
| **Unrecognized** | Description matches zero aliases |
| **Ambiguous** | Description matches > 1 non-subsumed alias from different canonicals |
| **Quarantine** | REVIEW status, invalid quantity, unrecognized, or ambiguous |
| **Valid match** | Exactly one recognized category matches the expected category |
| **Mismatch** | Exactly one recognized category differs from the expected category |

A quarantined record is excluded from normalized totals. A mismatch is included in normalized totals but flagged.

### 4.2 For contact reconciliation tasks
For each record (row) across all source snapshots:
- **Quarantine a row** when it has no usable email AND no usable phone. "Usable" means the value is present, non-empty, and not a sentinel like "N/A", "none", "NULL", or whitespace-only.
- A **canonical entity** ("person") is formed by grouping rows that share the same normalized contact identifier. Use the `master_hint` field when present to guide cross-source merging (rows sharing the same non-null `master_hint` belong to the same entity even when their surface-level identifiers differ).
- Within each canonical entity, select a **survivor row** using source-system precedence (Compliance Master > Partner Portal > CRM for contact domains; HR Directory > Identity Registry > Dispatch for roster domains), with the `verified_flag` (1 beats 0) as a secondary tiebreaker.
- The **canonical email** is the survivor's email, normalized to lowercase with whitespace trimmed. The **canonical phone** is the survivor's phone reduced to digits only.
- The **canonical city** is determined by majority vote across all rows in the entity; ties are broken by the same source-system precedence. The `city_source_system` names which source's value was selected.
- **Duplicate clusters** are entities containing two or more rows that share the same normalized email (i.e., multiple source systems reported the same contact).

### 4.3 For maintenance event tasks
For each deduplicated event:
- **Missing timestamp**: `event_time_raw` is null or empty.
- **Invalid timestamp**: `event_time_raw` is not parseable as ISO-8601.
- **Invalid odometer**: `odometer_value` is negative. Convert MI to KM using the distance conversion factor (1 MI = 1.609344 KM) before range checks and distance calculations.
- **Negative labor**: `labor_hours` < 0.
- **Extreme labor**: `labor_hours` > 24.
- **Odometer regression**: For a given asset, when events are sorted by timestamp, any event whose odometer reading is less than the previous event's reading. Regression events are noted but are still included in the valid event set and distance calculation if they otherwise pass all other checks.
- An event with any of the first five conditions is **invalid** and excluded from the corrected history.

## Step 5 — Compute Aggregations

### 5.1 Normalized totals
Sum normalized volumes/weights/distances and USD spends over all valid (non-quarantined) records. Group by the recognized canonical category and report per-category subtotals. Round all currency and measure values to 2 decimal places in the final output.

### 5.2 Readiness / eligibility counts
For contact tasks: an entity is *eligible* for readiness reporting when it is ACTIVE and has at least one usable email or phone. A channel (email, phone) is **ready** when the entity's consent status is GRANTED. Partition eligible entities into four mutually-exclusive buckets: `both` (GRANTED + has email + has phone), `email_only` (GRANTED + has email only), `phone_only` (GRANTED + has phone only), `not_ready` (consent is not GRANTED).

### 5.3 Rankings
When ranking entities (merchants, carriers, assets), apply the tie-breaking rules declared in the case scope. Common pattern: primary sort by exception/mismatch count descending, secondary sort by the entity's stable ID ascending.

## Step 6 — Assign Decision Codes

The answer template enumerates the allowed code values for each code family. Codes are opaque — their meanings must be inferred from the data relationships revealed during reconciliation.

### General heuristic for code assignment
- **Reference / source-basis codes**: distinguish records that come from a single source (CERTIFIED-only vs PROVISIONAL-only) from those appearing in multiple snapshots. Active/authoritative references get one code; inactive or ambiguous references get another.
- **Disposition / routing codes**: map to the classification outcome. Valid records get one code, mismatch records another, quarantined records a third, and invalid records a fourth. Unrecognized/ambiguous records typically share a code.
- **Control codes** (identity, outreach, field-provenance): reflect the *certainty* and *coverage* of the reconciliation. Match these to the evidence pattern:
  - All sources verified and agree → highest-confidence code.
  - Majority agree, one source unverified → moderate-confidence code.
  - Single source or conflicting sources → low-confidence code.
  - No usable contact / inactive → exclusion code.

## Step 7 — Apply Certification Thresholds

The case scope defines status-action mappings and numeric thresholds (e.g. `pass_max_quarantine_rate`, `pass_with_exceptions_max_quarantine_rate`). Compute the relevant rate (e.g. quarantine rows ÷ canonical entities, or exception records ÷ valid records), compare against the thresholds, and assign the corresponding status and action from the mapping.

## Step 8 — Assemble the Answer

1. **Follow the answer template exactly.** Every required key must be present. No extra keys are allowed (when `additionalProperties: false` is declared).
2. **Sort all arrays** as specified in the template or its ordering-rules annotations. Lexicographic sort on stable IDs unless a different order is declared.
3. **Use stable IDs from the public data.** Do not invent IDs. Row IDs, transaction IDs, event IDs, merchant IDs, asset IDs, carrier IDs, snapshot IDs — all come directly from the queried records or the case scope.
4. **Return JSON only.** No markdown, no commentary, no wrapping text.
5. **Validate numeric precision.** Counts are integers. Rates are rounded to the declared number of decimal places (typically 4). Currency and measure values are rounded to 2 decimal places.

## Key API Conventions

- All data is read through `POST /api/query` with `{"query": "<SQL>"}` and the Authorization header.
- Reference endpoints (`/api/reference/aliases`, `/api/reference/conversions`, `/api/reference/fx`) may support query parameters for filtering; if these fail, use the query endpoint with the corresponding view (`v_reference_aliases`, `v_unit_conversions`, `v_fx_rates`).
- The query endpoint returns `{"columns": [...], "rows": [[...]], "row_count": N, "truncated": bool}`. If `truncated` is true, paginate or refine the filter.
- Source-snapshot metadata is accessed via `SELECT * FROM v_source_snapshots WHERE collection_id = '...'`.

## Self-Check Before Submitting

- [ ] Every required key from the answer template is present.
- [ ] No extra keys beyond the template.
- [ ] All arrays are sorted per the declared ordering rules.
- [ ] All array lengths match the template's minItems/maxItems.
- [ ] All `enum` values match the allowed set.
- [ ] All `pattern` constraints on IDs are satisfied.
- [ ] Count values are non-negative integers.
- [ ] Numeric values use the declared precision (decimal places).
- [ ] The certification status and action are consistent with the computed rate and the case-scope threshold mapping.
- [ ] Quarantined records are excluded from normalized totals but counted in exception/audit summaries.
- [ ] IDs come from the data, not invented.
