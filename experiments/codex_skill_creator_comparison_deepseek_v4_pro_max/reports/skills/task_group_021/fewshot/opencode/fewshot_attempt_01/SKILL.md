---
name: asteria-dq-hub
description: Use when the task involves reconciling, auditing, certifying, or computing derived metrics from the Asteria Fleet Data Quality Hub REST API. Triggers on mentions of Asteria, Fleet Data Quality Hub, fleet data reconciliation, partner onboarding certification, fuel audit, maintenance event audit, field-service roster, freight charge audit, or any task that supplies a case_scope.json plus an answer_template.json and references a base URL for a read-only data quality API. Also use when the user asks to audit or reconcile fleet, fuel, freight, maintenance, or contact data from an HTTP API.
---

# Asteria Fleet Data Quality Hub

Reconcile, audit, and certify data from the Asteria Fleet Data Quality Hub — a
multi-source, multi-snapshot REST API. Every task follows the same structural
pattern: discover the hub, fetch the data, reconcile overlapping sources,
validate records, compute aggregates, assign opaque decision codes, and return
one JSON object that conforms exactly to a provided answer template.

## Task structure

Every Asteria DQ Hub task supplies two artifacts:

- **`case_scope.json`** — runtime parameters: which collection to audit, the
  business cutoff, focus records, decision-panel IDs, ranking policies, and
  certification thresholds.
- **`answer_template.json`** — the exact output contract: required keys,
  allowed enum values, ordering rules, numeric precision, and array lengths.

The answer template is the primary specification for output shape. The case
scope is the primary specification for what to compute. The task prompt provides
the business framing; those two files define the machine-readable contract.

## Hub discovery

The hub lives at the base URL supplied in `environment_access.md`. Start every
task by surveying the available data in this order:

### 1. Read the catalog and schema

```
GET {base_url}/api/catalog/collections
GET {base_url}/api/catalog/schema
```

The catalog lists every collection with its stable ID, business name, and
row-count metadata. The schema describes fields, types, nullable/required
status, and value constraints.

### 2. Read the source snapshots

```
GET {base_url}/api/source-snapshots
```

Returns every snapshot for the target collection: `snapshot_id`,
`collection_id`, `status` (`CERTIFIED`, `PROVISIONAL`, `STALE`), `row_count`,
and `created_at`.

### 3. Read the reference tables (when relevant)

```
GET {base_url}/api/reference/aliases     — canonical-category mappings
GET {base_url}/api/reference/conversions  — unit-conversion factors
GET {base_url}/api/reference/fx           — currency-rate table
```

Read these unconditionally when the task involves category matching, unit
normalization, or currency conversion.

## Source reconciliation

Every collection has at least two snapshots: one `CERTIFIED` and at least one
`PROVISIONAL`. Records with the same logical key appear in both; only the
CERTIFIED occurrence is retained.

**Reconciliation steps:**

1. **Identify the authoritative snapshot.** Choose the snapshot with
   `status: "CERTIFIED"`. If multiple CERTIFIED snapshots exist, use the one
   with the latest `created_at`. If none is CERTIFIED, treat the latest
   PROVISIONAL as authoritative and flag the degraded status.
2. **Detect cross-snapshot duplicates.** Group rows by their logical key (the
   record's primary ID field). Rows with the same key across different
   snapshots are duplicates.
3. **Retain the authoritative occurrence.** Keep the CERTIFIED row; discard
   PROVISIONAL rows when a CERTIFIED duplicate exists for the same key.
4. **Produce counts.** `raw_row_count` = total across all snapshots.
   `logical_count` = count after deduplication. `duplicate_raw_count` =
   raw - logical.

For contacts (`/api/contacts`), the logical key is more complex — rows from
different source systems represent the same person when they share identifying
attributes. See [references/domains.md](references/domains.md) for
contact-matching rules.

## Fetching collection data

### Direct endpoints (preferred)

| Endpoint | Collection kind |
|---|---|
| `GET /api/contacts` | Contact records |
| `GET /api/transactions/fuel` | Fuel-purchase transactions |
| `GET /api/transactions/freight` | Freight-charge transactions |
| `GET /api/maintenance/events` | Maintenance-event records |

These return a flat JSON array; snapshot rows are interleaved. Use the
`snapshot_id` field to partition.

### Pagination

Larger collections paginate with a `next_cursor` field. Continue fetching
with `?cursor={next_cursor}` until `next_cursor` is `null` or absent. Use the
bundled `scripts/fetch_all.py` script (see [scripts/README.md](scripts/README.md))
or write equivalent logic.

### Query API

For ad-hoc filtering, use the read-only query endpoint:

```
POST {base_url}/api/query
Content-Type: application/json

{ "collection_id": "...", "filters": [...], "limit": N, "cursor": "..." }
```

Prefer the direct endpoint when no server-side filtering is needed.

## Answer template conformance

The answer template is a JSON Schema document that defines the exact output
structure. Every task prompt says "Return one JSON object matching
`payloads/answer_template.json`" or equivalent. Honor it precisely.

**Key rules:**

- **`required` arrays are mandatory.** Every key listed under `required` at
  every nesting level must be present.
- **`enum` constraints are exact.** Do not invent values; use only the listed
  set.
- **`minItems` / `maxItems` are hard bounds.** When the template says
  `minItems: 5, maxItems: 5`, output exactly 5 items.
- **`additionalProperties: false` means no extra keys.**
- **List ordering** is declared in `description` fields, `x-ordering_rules`,
  or the prompt. Lexicographic ascending is the most common default. Respect
  multi-key sort orders.
- **Numeric precision** is declared in `description`, `multipleOf`, or a
  `numeric_precision` field. Round to the declared precision (typically 2
  decimal places). Use `round(value, 2)`.
- **Phone digits** strip all non-digit characters; keep as a string.
- **Emails** are trimmed, NFKC-normalized, and lowercased.

## Decision codes

Every task assigns opaque codes that are never documented explicitly. They must
be **inferred from the reconciled data**. The process:

1. **Group rows by structural situation** — focus clusters, control-case
   evidence rows, all quarantined rows, all readiness-eligible rows, etc.
2. **Identify the discriminating attributes** — which source systems
   contributed, how many sources overlapped, whether resolution was clean,
   contact-channel usability, consent status, snapshot provenance,
   validation outcome.
3. **Map attribute combinations to codes deterministically.** The same
   combination always produces the same code within a task.

The domain reference at [references/domains.md](references/domains.md)
documents the assignment patterns that appear across the training evidence.

## Certification and close status

Every task ends with a certification or close-status decision. The case scope
provides thresholds:

```
if quarantine_rate <= pass_max_quarantine_rate:             PASS → RELEASE
elif quarantine_rate <= pass_with_exceptions_max_quarantine_rate: PASS_WITH_EXCEPTIONS → REVIEW_EXCEPTIONS
else:                                                       HOLD → BLOCK_AND_REMEDIATE
```

For maintenance tasks, any odometer regression forces `HOLD` regardless of
other metrics. Always check both the case-scope thresholds and template-level
gates.

## Step-by-step workflow

### 1. Orient: read the case scope and answer template

Parse every field constraint, enum, ordering rule, and required key. Identify
which domain the task belongs to (contacts, fuel, freight, maintenance).

### 2. Survey the hub

Fetch catalog, schema (filtered to the target collection), and source-snapshots.
Identify the authoritative snapshot. Read reference tables relevant to the
domain.

### 3. Fetch and reconcile

Fetch all rows from the appropriate endpoint. Paginate fully. Partition by
snapshot. Deduplicate by logical key, retaining CERTIFIED rows.

### 4. Validate and classify

Apply domain-specific validation rules (see [references/domains.md](references/domains.md)).
Classify each record: valid vs. quarantined, recognized vs. unrecognized,
matched vs. mismatched.

### 5. Compute aggregates

Counts, rates, normalized totals, focus-asset rollups, carrier/merchant
rankings — follow the formulas in the case scope and prompt.

### 6. Assign decision codes

For every decision-panel entry, control case, focus cluster, readiness
partition, and code-required field: inspect the underlying data and select
the correct code from the allowed enum.

### 7. Render the JSON answer

Produce exactly one JSON object. Validate against the answer template before
returning: check required keys, enum values, list lengths, ordering, and
numeric precision.

## Reference files

- [references/api-endpoints.md](references/api-endpoints.md) — complete API
  reference: endpoints, parameters, response shapes, pagination.
- [references/domains.md](references/domains.md) — domain-specific rules:
  contact matching, fuel/freight category matching, maintenance validation,
  decision-code assignment patterns.
- [scripts/README.md](scripts/README.md) — bundled scripts and usage.

Read the reference file for the relevant domain before implementing.
