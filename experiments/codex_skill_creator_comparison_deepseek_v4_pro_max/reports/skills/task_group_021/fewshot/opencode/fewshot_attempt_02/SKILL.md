---
name: asteria-dq-hub-certification
description: Reconcile source records, assign opaque control codes, and produce certification decisions against the Asteria Fleet Data Quality Hub. Use when the user references Asteria, a Fleet Data Quality Hub, TASK_ENV_BASE_URL, contact/partner onboarding certification, fuel-purchase normalization, freight-charge reconciliation, maintenance-log integrity, field-service roster readiness, or any audit that involves /api/catalog/collections, /api/catalog/schema, /api/contacts, /api/transactions/fuel, /api/transactions/freight, /api/maintenance/events, /api/source-snapshots, /api/reference/aliases, /api/reference/conversions, /api/reference/fx, or /api/query endpoints. Use whenever the task asks you to reconcile overlapping source records from this hub and produce a JSON certification answer conforming to a supplied answer template.
---

# Asteria Fleet Data Quality Hub Certification

Use this skill whenever a task requires reconciling records across the Asteria Fleet Data Quality Hub, classifying rows, assigning opaque control codes, and producing a structured JSON certification answer per a supplied answer template.

## Hub connectivity

Read `environment_access.md` for the base URL (`TASK_ENV_BASE_URL`). All endpoints are authenticated read-only. The hub exposes a REST catalog and a SQL query interface.

**Key endpoints — always available:**
- `GET /api/catalog/collections` — list available collections
- `GET /api/catalog/schema` — list logical views and their field definitions
- `GET /api/source-snapshots?collection_id=...` — list snapshots for a collection
- `POST /api/query` — submit SQL against the hub's read-only query engine
- `GET /api/contacts?collection_id=...,snapshot_id=...` — paginated contact rows
- `GET /api/transactions/fuel?collection_id=...,snapshot_id=...` — paginated fuel transactions
- `GET /api/transactions/freight?collection_id=...,snapshot_id=...` — paginated freight charges
- `GET /api/maintenance/events?collection_id=...,snapshot_id=...` — paginated maintenance events
- `GET /api/reference/aliases` — alias-to-canonical-value mappings (with domain, valid_from, valid_to)
- `GET /api/reference/conversions` — unit conversion factors (with valid_from, valid_to)
- `GET /api/reference/fx` — currency exchange rates (with rate_date, rate_status)

**Pagination:** All transactional GET endpoints (contacts, fuel, freight, maintenance) return paginated results. Always read the full `total` count from the first response and fetch every page. If a collection is larger than a single response page, walk through pages via the `offset` and `limit` parameters until all rows are retrieved.

**POST /api/query** accepts a JSON body with `collection_id` and `sql` fields. The query engine supports standard SELECT with WHERE, GROUP BY, ORDER BY, JOINs across logical views, aggregates, and subqueries. Use it to run custom aggregations instead of downloading all rows and computing locally when that is more efficient.

## Overall workflow

1. **Read the inputs.** Start by reading the user prompt, `payloads/case_scope.json`, and `payloads/answer_template.json`. Understand the business cutoff, the target collection, the requested focus items, certification thresholds, and the required output shape.

2. **Discover the collection.** Call `/api/catalog/collections` and confirm the `collection_id` from `case_scope.json` exists. Note its source systems and time range.

3. **Discover the schema.** Call `/api/catalog/schema`. Identify the logical view name that matches the collection family and note every field name, type, and meaning. The schema describes what is available — use those exact field names in SQL queries.

4. **Reconcile snapshots.** Call `/api/source-snapshots?collection_id=...` to list all snapshots. Choose the authoritative snapshot:
   - Prefer the snapshot with `snapshot_status = "CERTIFIED"` whose `business_cutoff` is on or before the task's cutoff (the snapshot whose `business_cutoff` is closest to but not after the task cutoff).
   - If no CERTIFIED snapshot exists, use the PROVISIONAL snapshot whose `business_cutoff` is on or before the cutoff.
   - Note: some tasks scope to ALL rows across all snapshots; in that case all snapshots matter for duplicate detection but the authoritative one is used for retained values.

5. **Fetch reference data.** Retrieve `/api/reference/aliases`, `/api/reference/conversions`, and `/api/reference/fx`. Filter each to the rows valid as of the task cutoff (where `valid_from <= cutoff` and `valid_to` is null or `>= cutoff`). For fx rates, filter to the latest rate per currency on or before the cutoff date with `rate_status = "PUBLISHED"`.

6. **Fetch data rows.** Download all rows from the relevant transactional view. For multi-snapshot collections, query all snapshots individually to detect duplicates. Use the paginated GET endpoint for the target view, or use POST /api/query for filtered or joined datasets.

7. **Classify and reconcile.** Apply the domain-specific classification rules in the reference sections below. The core pattern is:
   - Match free-text descriptions against reference aliases to determine canonical categories.
   - Compare expected vs. recognized categories to detect mismatches.
   - Handle duplicates across snapshots by retaining the authoritative-snapshot occurrence.
   - Quarantine rows that cannot be resolved or contain invalid measures.
   - Assign opaque control codes per the reference tables.

8. **Produce the output.** Generate exactly one JSON object matching the schema in `payloads/answer_template.json`. No commentary, no Markdown. Follow every ordering rule declared in the template or schema. Use the field names and enumeration values exactly as specified.

## General reconciliation rules

### Snapshot precedence

When the same logical record (same row ID or logical ID) appears in multiple snapshots:
- Retain the occurrence from the authoritative snapshot (usually CERTIFIED).
- Count the duplicate occurrences but do not include them in normalized totals.
- For cross-snapshot deduplication where snapshots use different ID schemes, detect duplicates by matching on the logical business key (e.g., same charge_id across snapshots).

### Quarantine criteria

Rows are quarantined when they cannot be confidently classified or their physical measures are invalid for the domain:
- **Contacts:** no usable email AND no usable phone (empty, null, or the literal string "null").
- **Fuel transactions:** description cannot be uniquely matched to a recognized fuel type, or quantity is non-positive.
- **Freight charges:** description alias is unrecognized or matches multiple canonical classes, or billed_weight <= 0, or distance <= 0.
- **Maintenance events:** event_time_raw is missing or unparsable, odometer_value is outside a valid range, or labor_hours is negative or extreme.

### Invalid/rejected rows

These are not counted as quarantined — they are excluded entirely from the reconciled dataset. Invalid rows are those with fundamentally broken data (unparsable timestamps, out-of-range odometer values, negative labor, completely missing required fields) that prevent any meaningful classification. Quarantined rows have enough structure to be identified but cannot be assigned to a valid category.

### Duplicate counting

`duplicate_raw_count` is the number of raw rows that were excluded because the same logical record appeared in the authoritative snapshot. It equals `raw_row_count - logical_record_count`.

`logical_X_count` is the number of distinct logical records after deduplication across snapshots.

## Domain-specific classification references

Read the relevant reference file based on the collection family:

| Collection family | Reference file |
|---|---|
| `contacts` | [references/contacts.md](references/contacts.md) |
| `fuel` | [references/fuel.md](references/fuel.md) |
| `freight` | [references/freight.md](references/freight.md) |
| `maintenance` | [references/maintenance.md](references/maintenance.md) |

Each reference file defines:
- The logical view and key field mapping
- How to match free-text to canonical categories
- How to identify quarantined and invalid rows
- How to assign control codes

## Control codes

Control codes are opaque, fixed-enum values assigned by domain-specific rules. Their expansions are not needed — only match them to the allowed enum values in the answer template. The complete code tables are in [references/control-codes.md](references/control-codes.md).

### General code assignment approach

Control codes are determined by examining the source systems, field values, and resolution outcomes for specific rows or clusters. The answer template lists the allowed codes for each decision type. To assign a code:

1. Identify the code family requested by the answer template field name (e.g., `identity_code` → IC family, `outreach_code` → OR family, `field_provenance_code` → FP family, etc.).
2. Look at the reference table for rules mapping observed data patterns to codes.
3. When evidence rows span multiple systems with conflicting signals, pick the code that best describes the reconciled state.
4. The same family of codes appears across domains but with different mappings — always cross-reference against the specific reference file for the domain.

## Output precision and ordering

- All numeric totals are rounded to exactly 2 decimal places unless the answer template specifies another precision.
- All arrays must be sorted exactly as specified by the template's `x-ordering_rules` or field descriptions.
- String IDs must be lexicographically sorted (standard ASCII/Unicode lexicographic order).
- Lists of row IDs must be deduplicated (`uniqueItems: true`).
- Every required field must be present — the template's `required` arrays define what is mandatory.
- Do not add extra keys beyond what the template allows (`additionalProperties: false`).

## Certification thresholds

The `status_action_map` or equivalent in the case scope maps statuses to actions. Common patterns:
- `quarantine_rate == 0` → status `PASS`, action `RELEASE`
- `quarantine_rate > 0` but at or below the `pass_with_exceptions_max_quarantine_rate` threshold → status `PASS_WITH_EXCEPTIONS`, action `REVIEW_EXCEPTIONS`
- `quarantine_rate` exceeds the exceptions threshold, or a hard gate fires (e.g., odometer regression) → status `HOLD`, action `BLOCK_AND_REMEDIATE`

Always apply the explicit thresholds from the case scope. If a domain-specific gate (like odometer regression in maintenance) overrides the rate-based threshold, that gate takes precedence.
