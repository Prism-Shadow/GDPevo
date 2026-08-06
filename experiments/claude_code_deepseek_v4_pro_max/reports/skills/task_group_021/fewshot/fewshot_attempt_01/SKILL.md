# Asteria Fleet Data Quality Hub — Certification Skill

## Purpose

Complete Asteria Fleet data-certification tasks by reconciling source records, applying quality rules,
assigning internal control codes, and producing a JSON answer that conforms exactly to the supplied
output contract (`answer_template.json`).

## Input files (every task provides these)

| File | Role |
|---|---|
| `prompt.txt` | Business narrative and list of required outputs. |
| `payloads/case_scope.json` | Task parameters: collection, cutoff, focus items, threshold rules, ranking policies. |
| `payloads/answer_template.json` | JSON Schema or field contract the output must satisfy. |
| `environment_access.md` | Base URL, credentials, and allowed endpoints for the running environment. |

## Phase 1 — Connect and discover the data landscape

### 1.1 Read the access file

Parse `environment_access.md` for `base_url`, the `Authorization` header value, and the list of
allowed endpoints. All HTTP requests use these values.  The default base URL is
`http://task-env:9021/`.

### 1.2 Discover collections and their schemas

```
GET /api/catalog/collections
```
Returns the list of loaded collections.  Identify the collection whose name or id matches
`collection_id` from the case scope.

```
GET /api/catalog/schema
```
Returns column-level schema for every loaded collection.  Use this to understand column names,
types, and which fields carry identifiers, timestamps, measures, status flags, consent flags,
category/class labels, and region/geography dimensions.

### 1.3 Identify authoritative source snapshots

```
GET /api/source-snapshots
```
Returns snapshot metadata for each collection: snapshot id, status (`CERTIFIED` / `PROVISIONAL` /
`STALE`), row count, and temporal coverage.  **The certified snapshot (status `CERTIFIED`) is the
authoritative source.**  When both a certified and a provisional snapshot exist for the same
collection, prefer the certified snapshot for final answers.  Provisional snapshots are used only to
detect cross-snapshot duplicates.

### 1.4 Fetch reference data

Several tasks require additional reference tables:

| Endpoint | Typical use |
|---|---|
| `GET /api/reference/aliases` | Map merchant/carrier/service aliases to canonical categories. |
| `GET /api/reference/conversions` | Convert raw quantities to canonical units (L, KG, KM). |
| `GET /api/reference/fx` | Convert local-currency amounts to the base currency (USD). |

## Phase 2 — Acquire and reconcile the data

### 2.1 Page-aware data acquisition

Use `POST /api/query` with SQL `SELECT` statements.  The body is `{"query": "<SQL>"}`.
The collection may be larger than a single response page; use `LIMIT` / `OFFSET` (or ordered
pagination on a stable key) to retrieve all rows.  Verify the total retrieved row count against
the source-snapshot metadata.

### 2.2 Reconcile overlapping source records (duplicates)

When multiple snapshots exist, a single business event/entity may appear in both.  Steps:

1.  Query the certified snapshot for all rows.
2.  Query the provisional snapshot for its rows.
3.  Join on the logical identifier (e.g., `logical_event_id`, `charge_id`, or a composite business key)
    to find rows present in both snapshots.
4.  For each duplicate group, retain the certified-snapshot row.  Count the dropped provisional rows
    as `duplicate_raw_count`.

### 2.3 Reconcile overlapping contact/entity records (entity resolution)

When three source systems report the same person/entity:

1.  Collect all rows from the scoped collection.
2.  Group by the business merge key (provider-supplied cluster, cross-system identifier, or
    deterministic match on normalized name + contact fields).
3.  For each cluster, choose one survivor row.  The precedence order across source systems is
    defined by the task domain: HR Directory > Identity Registry > Dispatch for name, and
    Identity Registry > HR Directory > Dispatch for contact fields.
4.  Derive the canonical fields from the survivor row or via field-level precedence, and record
    which source system supplied each field.  Record the survivor row id as `master_id` and list
    all source row ids sorted lexicographically in `member_row_ids`.

### 2.4 Apply business-cutoff and temporal scoping

Filter all rows to those with a timestamp ≤ `business_cutoff` or `cutoff_at` (or within the
`business_period` start/end range).  Rows with timestamps after the cutoff are excluded.

## Phase 3 — Quality and integrity checks

### 3.1 Data-quality issue categories

Depending on the domain, check for:

| Issue | Detection rule |
|---|---|
| Missing timestamp | `NULL` or empty timestamp column. |
| Invalid / unparseable timestamp | Non-ISO-8601 or out-of-range values. |
| Invalid odometer / measure | Negative, zero (when positive required), or value exceeding a domain maximum. |
| Negative labor / nonpositive quantity | Value ≤ 0 where a positive value is expected. |
| Extreme labor / extreme quantity | Value exceeds a domain-specific high-water mark. |
| Odometer regression | For the same asset, the odometer reading decreases between chronologically later events. |
| Unrecognized category | Description/alias maps to zero canonical categories. |
| Ambiguous category | Description/alias maps to more than one canonical category. |
| Expected-vs-actual mismatch | The expected category/class field differs from the recognized (resolved) category/class. |

### 3.2 Quarantine rules

A row is quarantined (excluded from normalized totals) when:
- It has no usable contact channel (no valid email AND no valid phone).
- Its category/class cannot be resolved (unrecognized or ambiguous alias).
- It has an invalid physical measure (nonpositive weight, nonpositive distance, invalid quantity).

Quarantined row IDs must be reported as a deduplicated, lexicographically sorted list.

### 3.3 Duplicate groups

Report every logical event/charge that appears in more than one snapshot.  For each group, include
the logical id, the set of snapshot ids (sorted lexicographically), the retained event/charge id,
and the retained snapshot id.  Sort groups by logical id ascending.

## Phase 4 — Compute normalized totals

### 4.1 Unit conversion and currency normalization

- Convert raw quantities to the canonical unit using `/api/reference/conversions`.
- Convert local-currency amounts to the base currency using `/api/reference/fx`.
- Do not include quarantined rows in normalized totals.
- Valid rows with category mismatches are included in normalized totals.

### 4.2 Breakdowns

- Compute totals (count, volume/weight/distance, spend) grouped by the recognized canonical
  category/class, sorted by category/class ascending.
- Each recognized category in the domain must appear as exactly one row, even if its count is zero.

### 4.3 Numeric precision

- Count fields: exact integers.
- Monetary and physical-measure fields: rounded to exactly 2 decimal places (use banker's rounding
  or `ROUND(value, 2)`).
- Rates (e.g., quarantine rate): rounded to exactly 4 decimal places.
- All `number` / non-integer fields must conform to their JSON Schema `multipleOf` constraint
  (typically 0.01 for 2-decimal or 0.0001 for 4-decimal).

## Phase 5 — Focus-item resolution

### 5.1 Focus clusters / focus people / focus assets

For each focus item listed in the case scope, anchor on the supplied seed row id and expand to the
full resolved cluster the seed belongs to.  Report:

- All member row ids in the cluster (deduplicated, lexicographically sorted).
- The survivor (master) row id.
- Canonical fields (name, email, phone digits, city, region/depot, consent status, record status).
- The source system that supplied each canonical field.
- The resolution outcome (e.g., `FIELD_LEVEL_PRECEDENCE_APPLIED`, `SINGLE_SOURCE`,
  `CONTESTED_NO_AUTOMERGE`, `NO_USABLE_CONTACT`).

### 5.2 Control cases / anchored cases

For each control case or anchored case in the scope, examine the evidence rows and assign the
applicable internal codes.  Code systems are listed in Phase 7.

## Phase 6 — Ranking outputs

When the task requests a ranked list (top-N assets by risk, top-N merchants/carriers by exceptions):

1.  Compute the ranking metric per entity from the reconciled data.
2.  Apply the primary sort (typically the ranking metric descending).
3.  Apply tie-breaks in the order specified by the case scope (e.g., secondary metric descending,
    then entity id ascending).
4.  Assign rank numbers starting at 1.
5.  Return exactly the requested number of entries.

## Phase 7 — Internal control and policy codes

These Asteria-internal codes recur across tasks.  Assign them based on the evidence in the
reconciled data, NOT by guessing.  The code values allowed for a given output field are constrained
by the answer template's `enum` for that field.

### Identity codes (IC-series)
| Code | Meaning |
|---|---|
| `IC-25` | Single-source identity — one system provides the only record. |
| `IC-40` | Quarantined identity — no usable contact channel exists. |
| `IC-70` | Multi-source merged identity — field-level precedence applied across two or more systems. |
| `IC-90` | Cross-system contested identity — records from different systems cannot be automatically merged. |

### Outreach / readiness codes (OR-series)
| Code | Meaning |
|---|---|
| `OR-15` | Inactive exclusion — entity is inactive and excluded from outreach. |
| `OR-35` | Channel-ready — entity is active with consent granted and at least one usable channel. |
| `OR-60` | Quarantined — entity lacks any usable contact channel. |
| `OR-80` | Consent-blocked — entity is active with a channel but consent is not granted. |

### Field provenance codes (FP-series)
| Code | Meaning |
|---|---|
| `FP-20` | Single-source provenance — field value from one source system only. |
| `FP-55` | Multi-source consistent — two or more source systems agree on the field value. |
| `FP-75` | Unusable / quarantined — no valid field data available. |

### Reference policy codes (RB-series)
| Code | Meaning |
|---|---|
| `RB-17` | Alias maps to a single recognized category confirmed by a single reference source. |
| `RB-42` | Alias maps to a single recognized category confirmed by consensus across references. |
| `RB-83` | Alias resolution requires an override or domain-specific exception. |

### Source basis codes (SB-series)
| Code | Meaning |
|---|---|
| `SB-24` | Certified snapshot is the sole source. |
| `SB-61` | Cross-reference reconciled — certified and provisional snapshots agree. |
| `SB-79` | Certified snapshot retained over a conflicting provisional record. |

### Ledger disposition codes (LD-series)
| Code | Meaning |
|---|---|
| `LD-14` | Quarantine exclusion — charge cannot enter the ledger. |
| `LD-31` | Mismatch — charge enters ledger under the recognized (actual) class. |
| `LD-53` | Clean — no mismatch and no quarantine condition; normal routing. |
| `LD-72` | Duplicate resolution — retained certified occurrence enters ledger; duplicate excluded. |
| `LD-88` | Unresolved class — charge has an unrecognized or ambiguous category. |

### Maintenance source codes (MS-series)
| Code | Meaning |
|---|---|
| `MS-12` | Single-snapshot event — event appears only in one snapshot. |
| `MS-47` | Multi-snapshot retained — certified occurrence kept over provisional duplicate. |
| `MS-86` | Reconstructed event — event value was corrected or derived during reconciliation. |

### History route codes (HR-series)
| Code | Meaning |
|---|---|
| `HR-19` | Rejected — event excluded from the corrected history due to invalid data. |
| `HR-33` | Validated — event passed all quality checks and enters the corrected history. |
| `HR-74` | Regression-flagged — event is valid but its odometer value regressed relative to the sequence. |

## Phase 8 — Certification / reconciliation status

Derive the final status from the scope's thresholds:

| Status | Meaning | Default action |
|---|---|---|
| `PASS` | All metrics within acceptable bounds (e.g., quarantine rate = 0). | `RELEASE` |
| `PASS_WITH_EXCEPTIONS` | Metrics exceed the pass threshold but are within the exception threshold. | `REVIEW_EXCEPTIONS` |
| `HOLD` | Metrics exceed the maximum allowed threshold. | `BLOCK_AND_REMEDIATE` |

The status-to-action mapping is supplied in the case scope (`status_action_map` or
`certification_gate`).  Apply it exactly.

### Readiness-specific status

For contact-readiness tasks, an entity is eligible only when active and possessing at least one
usable email or phone.  A channel is ready only when consent is `GRANTED`.  Compute mutually
exclusive readiness partitions: `both` (email + phone ready), `email_only`, `phone_only`,
`not_ready` (neither channel ready, or entity ineligible).

### Region/depot rollups

When the task requires a region or depot breakdown, group canonical entities by their region/depot
field value (from the resolved canonical data) and report the count for each distinct region.  Sort
the output alphabetically by the region/depot code.  Every region that appears in the canonical
entity set must be represented.

## Phase 9 — Output assembly

### 9.1 Follow the answer template exactly

The answer template defines every required top-level key, every allowed value, and every ordering
rule.  The output must:

- Include every `required` key.
- Match every `enum`, `pattern`, `minLength`, `maxLength`, `minItems`, `maxItems`, `multipleOf`,
  `minimum`, and `maximum` constraint.
- Use `additionalProperties: false` where specified — do not add extra keys.
- Where the template provides an `x-ordering_rules` block or inline descriptions, follow the stated
  sort order.

### 9.2 Standard ordering conventions

Unless overridden by the template:

- Row id lists within an entity: deduplicated, lexicographically ascending.
- Entity lists: sorted by their primary identifier (e.g., `cluster_id`, `event_id`, `charge_id`,
  `focus_person_id`, `control_case_id`) ascending.
- Region/depot lists: sorted by the region/depot code ascending.
- Snapshot id lists within a duplicate group: lexicographically ascending.
- Ranked lists: by the rank metric descending, then tie-breaks, then entity id ascending.

### 9.3 Return format

Return a single JSON object.  Do not wrap it in Markdown code fences.  Do not include commentary,
explanations, or log output.  The response must be parseable as JSON directly.

## Phase 10 — Verification checklist

Before emitting the final answer, verify:

1. Row counts are internally consistent: `raw_row_count = valid + duplicate_raw + invalid` and
   `logical_count = raw_row_count - duplicate_raw_count`.
2. Quarantine rate = `quarantine_row_count / canonical_entity_count` (or
   `quarantine_count / logical_charge_count` for transaction tasks), rounded to 4 decimal places.
3. Readiness counts: `both + email_only + phone_only + not_ready = readiness_eligible_entity_count`,
   and all four counts are mutually exclusive.
4. Depot/region counts: for each depot, the disposition counts sum to `total_person_count`.
5. Every required top-level key is present and non-null.
6. Every `enum` value is exactly one of the allowed strings.
7. All identifiers match their required pattern.
8. Numeric fields conform to their precision and `multipleOf` constraints.
9. All lists are sorted correctly and contain no duplicates.
10. The certification status and action are consistent with the computed metrics and the thresholds
    in the case scope.
