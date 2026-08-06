# Asteria Fleet Data Quality Hub — Reusable Reconciliation Skill

## Overview

When you receive a data-quality certification or audit task against the Asteria Fleet Data Quality Hub, follow the systematic process below. The hub exposes a read-only SQL query interface, reference tables, and collection metadata. Every task follows the same reconciliation pattern: **scope → deduplicate → normalize → classify → certify**.

---

## Phase 1 — Understand the Task Scope

1. **Read the case scope** (`payloads/case_scope.json`) for:
   - `collection_id` — which data collection to audit
   - `cutoff_at` / `as_of` — business-time cutoff; only rows with `business_updated_at` ≤ cutoff are in scope
   - `focus_*` lists — specific entities (assets, people, transactions) requiring detailed per-row decisions
   - Thresholds and ranking policies — determine the final certification status

2. **Read the answer contract** (`payloads/answer_template.json`) — every required field, enum value, ordering rule, and precision constraint must be honored exactly.

---

## Phase 2 — Explore the Collection

### Catalog and Schema
Query `/api/catalog/collections` to confirm the collection exists and note its `source_systems`. Query `/api/catalog/schema` to see all available views and their column meanings. The key views are:

| View | Purpose |
|------|---------|
| `v_contacts` | People/org contact records |
| `v_fuel_transactions` | Fleet fuel/charging purchases |
| `v_freight_charges` | Carrier freight invoice lines |
| `v_maintenance_events` | Work-order events with odometer readings |
| `v_source_snapshots` | Snapshot metadata per collection |
| `v_reference_aliases` | Domain-specific alias → canonical-value mappings |
| `v_unit_conversions` | Unit conversion factors |
| `v_fx_rates` | Currency-to-USD exchange rates |

### Source Snapshots
Every collection has at least two snapshots. One is `CERTIFIED` (authoritative); others may be `PROVISIONAL`. The authoritative snapshot is the one with `snapshot_status = 'CERTIFIED'`. Note its `snapshot_id`, `row_count`, and `business_cutoff`.

### Query the Raw Data
Pull all rows for the target collection with `SELECT * FROM v_<view> WHERE collection_id = '<id>' ORDER BY <natural key>, snapshot_id`. Expect 500–1700 rows.

---

## Phase 3 — Deduplicate and Reconcile

### Rule 1: Prefer the CERTIFIED snapshot
When the same logical record (same `transaction_id`, `charge_id`, `event_id`, or cross-snapshot cluster key) appears in multiple snapshots, retain the row from the CERTIFIED snapshot. If both snapshots are CERTIFIED, retain the one with the earlier `ingested_at`. If tied, pick the lexicographically first `row_id`.

### Rule 2: Cluster cross-snapshot contact records
Contact collections use `source_record_id` prefixes to encode person identity:
- `PA-XXXX-N` (Partner Portal), `CR-XXXX-N` (CRM), `CO-XXXX-N` (Compliance Master): same `XXXX` = same person across snapshots.
- `SR-NNNNNN` rows: cluster by **(snapshot_id, normalized person name)** to deduplicate exact-repeat rows within a snapshot. Then map cross-snapshot by **repeating-cycle position** — positions that share the same offset modulo the cycle width belong to the same canonical person. The `master_hint` column (when non-null) confirms or overrides positional clustering.

### Rule 3: Survivor selection
Within each cluster, select one "survivor" row as the canonical record. Precedence:
1. CERTIFIED snapshot over PROVISIONAL
2. Source system priority (check the `master_hint` carrier — the source that supplies the hint is most authoritative)
3. `verified_flag = 1` over `0`
4. Lexicographically first `row_id`

The survivor's values become the canonical values after normalization.

---

## Phase 4 — Normalize and Classify

### Contact normalization
- **email**: Trim whitespace, lowercase, NFKC-normalize. Treat `"none"`, `"null"`, `"unknown"`, `"N/A"`, and empty strings as absent.
- **phone**: Strip all non-digit characters. Treat `"none"`, `"null"`, `"unknown"`, `"N/A"`, and empty strings as absent.
- **name**: Trim whitespace, collapse inner whitespace, NFC-normalize. Preserve original Unicode — do not strip accents.
- **city**: Trim whitespace only.

### Transaction normalization (fuel / freight)
Retrieve reference data once and index it in memory:

1. **Aliases** (`v_reference_aliases`): Filter to `domain` matching the task. For each alias, check `reference_status` (only `ACTIVE` aliases apply) and `valid_from`/`valid_to` date bounds against the transaction's business date. Match alias text in the transaction description using **word-boundary regex** (`\b` + escaped text + `\b`).

2. **Longest-match ambiguity resolution**: When multiple aliases match the same description pointing to different canonical categories, choose the canonical of the **longest** matching alias text. If the longest-match heuristic still produces ties across different canonicals, the description is genuinely ambiguous and the transaction is quarantined.

3. **Unit conversions** (`v_unit_conversions`): Index `(kind, from_unit)` → `factor`. Multiply quantity by factor to get canonical units. Treat non-positive quantities as invalid.

4. **FX rates** (`v_fx_rates`): Use only `rate_status = 'CERTIFIED'`. Match on `(rate_date, currency)`. The transaction's `purchased_at` / `service_date` date (YYYY-MM-DD prefix) must equal the rate's `rate_date`. USD is identity (`usd_per_unit = 1.0`).

### Quarantine conditions
A transaction/charge is quarantined (excluded from normalized totals) when:
- Its description matches **zero** active aliases (unrecognized), or
- It matches aliases pointing to **multiple** canonical categories with equal-length longest matches (ambiguous), or
- Its quantity/weight/distance is **non-positive** (≤ 0)

### Mismatch
A valid (non-quarantined) transaction is a mismatch when its recognized canonical category differs from the `expected_*` field in the source data.

---

## Phase 5 — Compute Aggregates

For every aggregate (totals, counts, rankings), use the **deduplicated, survivor-only** rows. Exclude quarantined rows from volume/spend/count totals. Include mismatched rows in totals (they are valid, just classified differently).

- **Rounding**: Monetary amounts and physical measures round to 2 decimal places. Rates and percentages round to 4 decimal places. Use `round(value, precision)` — banker's rounding is acceptable.
- **Ordering**: Arrays must follow the ordering rules declared in the answer contract (typically lexicographic ascending by the stable ID field).

---

## Phase 6 — Assign Internal Control Codes

The answer contract defines allowed code values but not their meanings. Infer the mapping from the reference data properties:

### Reference policy codes (`RB-*`)
Map from `reference_status` of the alias/rule being decided:
- `ACTIVE` → `RB-17`
- `INACTIVE` → `RB-42`
- `PROVISIONAL` → `RB-83`

### Source basis codes (`SB-*`)
Map from the authoritative snapshot status of the retained row:
- `CERTIFIED` snapshot → `SB-24`
- `PROVISIONAL` snapshot → `SB-61`

### Ledger disposition / history route codes (`LD-*`, `HR-*`)
Map from the row's reconciliation outcome:
- Valid, no issues → lowest code in the enum (e.g., `LD-14`, `HR-19`)
- Mismatch (category differs from expected) → middle code (e.g., `LD-31`, `HR-33`)
- Quarantined or invalid → highest code (e.g., `LD-53`, `HR-74`)

### Contact control codes (`IC-*`, `OR-*`, `FP-*`)
These map to the three control families (IDENTITY, OUTREACH, FIELD_PROVENANCE). Within each family, pick the code that corresponds to the record's status tier:
- Normal/clean records → lowest tier code
- Records with exceptions or special handling → middle tier
- Quarantined or highest-risk records → highest tier

### Maintenance source codes (`MS-*`)
Map from the event's source snapshot status:
- CERTIFIED (Maintenance ERP) → `MS-12`
- PROVISIONAL (Mobile Work Orders) → `MS-47`

---

## Phase 7 — Certify

The certification/reconciliation status follows a decision table:

| Condition | Status | Action |
|-----------|--------|--------|
| No issues (zero quarantines, zero mismatches) | `PASS` | `RELEASE` |
| Issues below the case-scope threshold | `PASS_WITH_EXCEPTIONS` | `REVIEW_EXCEPTIONS` |
| Issues exceed threshold, or odometer regressions detected | `HOLD` | `BLOCK_AND_REMEDIATE` |

Check the case scope for explicit thresholds (`status_thresholds`, `certification_gate`). If none are provided, treat any quarantine rate > 0 as warranting at least `PASS_WITH_EXCEPTIONS`.

---

## Quick Reference: Common Pitfalls

1. **Not filtering by cutoff**: Always check `business_updated_at` against the scope cutoff.
2. **Using PROVISIONAL over CERTIFIED**: The certified snapshot is always authoritative for dedup.
3. **Substring-without-boundaries matching**: `"diesel"` inside `"biodiesel"` creates false ambiguities. Always use `\b` word-boundary regex.
4. **Ignoring alias validity dates**: An alias with `valid_from` after the transaction date does not apply.
5. **Including quarantined rows in totals**: Quarantined transactions must be excluded from normalized volume/spend.
6. **Wrong survivor for contacts**: The `master_hint` column identifies the authoritative source. The snapshot that carries the hint (typically Compliance Master) sets the survivor.
7. **Forgetting ordering rules**: Every list in the answer contract has a declared sort order. Lexicographic string sort is the default.
