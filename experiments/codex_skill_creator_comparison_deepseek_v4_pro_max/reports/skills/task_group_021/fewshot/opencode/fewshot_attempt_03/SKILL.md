---
name: asteria-dq-hub
description: Reconcile contact, fuel, maintenance, freight, or field-service collections against the Asteria Fleet Data Quality Hub read-only REST API. Use this skill whenever the user mentions the Asteria Fleet Data Quality Hub, Fleet Data Quality Hub, DQ Hub, Asteria DQ, reconciling Asteria data, partner onboarding certification, fuel audit, maintenance audit, freight accrual, field-service roster, or any task that references the /api/catalog/collections, /api/contacts, /api/transactions/fuel, /api/transactions/freight, /api/maintenance/events, or /api/query endpoints. Do not use for generic REST API tasks unrelated to Asteria Fleet data.
compatibility: No special dependencies; HTTP and JSON tooling is sufficient.
---

# Asteria Fleet Data Quality Hub

Reconcile overlapping source records from the Asteria Fleet Data Quality Hub
read-only REST API and produce structured answer JSON conforming to a supplied
answer template.

## Startup: read the runtime environment

The task always includes `environment_access.md` which provides the base URL
and allowed endpoints. Start by reading that file. All API calls use that base
URL with no authentication credentials.

## Phase 1: Understand the data landscape

Before touching any collection data, orient yourself with the hub structure.
Read these endpoints in parallel when possible:

1. `GET /api/catalog/collections` — lists every collection, its business period,
   and its associated snapshot IDs. This tells you whether the collection in
   the case scope actually exists under that ID and what snapshots are
   available.

2. `GET /api/catalog/schema` — column definitions for every collection. Every
   field name, type, and canonical value set lives here. When a task asks you
   to "recognize" a category, match against an alias, or inspect a field, use
   the schema's documented value set, not the collection rows alone.

3. `GET /api/source-snapshots` — lists every snapshot, its status
   (`CERTIFIED`/`PROVISIONAL`/`DEPRECATED`), row counts, source system, and
   ingestion timestamps. This is the foundation for snapshot resolution.

## Phase 2: Snapshot resolution (always do this first)

Every task involves overlapping records across snapshots. Establish the
authoritative source before computing any counts or totals.

**Rule**: A certified snapshot (`status: "CERTIFIED"`) is always authoritative
over a provisional or deprecated snapshot. When the collection has exactly one
certified snapshot, that snapshot is the authority. When two snapshots contain
the same logical record (same stable ID), keep the certified-snapshot row and
discard the other. The discarded row is a "duplicate raw row."

The `environment_access.md` may list `/api/reference/aliases`,
`/api/reference/conversions`, and `/api/reference/fx` as available. When the
task mentions aliases, unit conversions, or currency translation, read those
endpoints alongside the catalog and schema.

## Phase 3: Fetch the collection data

The raw collection endpoints return paginated data. Use them to pull all rows:

- **Contacts**: `GET /api/contacts?collection={collection_id}` (paginated)
- **Fuel**: `GET /api/transactions/fuel?collection={collection_id}` (paginated)
- **Freight**: `GET /api/transactions/freight?collection={collection_id}` (paginated)
- **Maintenance**: `GET /api/maintenance/events?collection={collection_id}` (paginated)

When pagination is present, follow the `next` link in each response until you
have every row.

In addition to the REST endpoints, the `POST /api/query` endpoint is available
for more targeted investigation. When a case scope asks for "focus" records,
"decision panel" entries, or anchored control rows, use `/api/query` to isolate
those rows efficiently rather than filtering a full collection dump. The query
body is a JSON object with the collection ID and filter criteria.

When the collection data is large, keep your working set in memory or in a
temporary file rather than re-reading it.

## Phase 4: Deduplicate and quarantine

These steps appear in every task, though the exact rules vary.

### Deduplication

Sort all rows by stable ID. For each ID that appears in more than one snapshot,
retain exactly the row from the authoritative snapshot (certified beats
provisional) and count the discarded ones as duplicates. The deduplicated set of
unique logical IDs and their retained rows is your working population for all
subsequent analysis.

See [references/snapshot-resolution.md](references/snapshot-resolution.md) for
the full algorithm and examples.

### Quarantine

Identify rows that cannot be used for the task's purpose. Quarantine rules by
domain:

- **Contacts**: no usable email AND no usable phone (both null, empty, or
  invalid). These rows go into the quarantine set and do NOT count as
  readiness-eligible entities. An active person with a usable channel but
  non-granted consent is blocked for readiness but is NOT quarantined.

- **Fuel**: non-positive quantity/liters, or a description that maps to zero
  recognized fuel categories (unrecognized) or more than one (ambiguous). These
  transactions enter quarantine and must not contribute to normalized totals.

- **Maintenance**: missing or unparsable timestamp, invalid odometer range (end
  <= start), negative labor hours, or extreme labor hours. These events are
  rejected. Odometer regressions (end reading below the previous event's end
  reading for the same asset) are NOT quarantined — they are reported separately
  in corrected metrics but remain in the valid history.

- **Freight**: ambiguous alias (maps to multiple service classes), unrecognized
  alias (maps to zero classes), non-positive weight, or non-positive distance.
  Quarantined charges stay out of normalized totals.

See [references/quarantine-rules.md](references/quarantine-rules.md) for full
per-domain conditions and edge cases.

## Phase 5: Category and alias matching

When the task involves expected-versus-actual comparisons:

1. Read `GET /api/reference/aliases` to load the alias-to-canonical mapping.
2. For each record, find the canonical category by matching the record's
   description text against the aliases. If one unambiguous match exists, that
   is the recognized category. If zero matches, the record is unrecognized. If
   multiple matches, it is ambiguous.
3. Compare the recognized category against the expected category field in the
   record. A mismatch occurs when they differ and both are valid.

## Phase 6: Physical and currency normalization

When totals are requested:

- **Volume**: apply unit conversions from `GET /api/reference/conversions` so
  every quantity lands in the canonical unit (liters for fuel, kg for freight
  weight, km for distance). Round to 2 decimal places unless the answer template
  specifies otherwise.

- **Currency**: apply FX rates from `GET /api/reference/fx` to convert
  local-currency amounts into the base currency (almost always USD). Round to 2
  decimal places.

- Quarantined rows **never** contribute to normalized totals. Category-mismatch
  rows **do** contribute — they are valid for normalization even if they carry a
  mismatch flag.

## Phase 7: Control codes, decision panels, and certifications

### Control codes

Every task requires opaque control codes (identity, outreach, field-provenance,
reference-policy, source-basis, ledger-disposition, maintenance-source,
history-route). These codes are **inferred from the data**, not randomly
assigned.

The code sets are always enumerated in the answer template's schema (as `enum`
constraints). Determine each code by examining:

- The record's source system or snapshot lineage
- Whether the record is quarantined, matched, or mismatched
- Whether the person is active/inactive, consent granted/denied
- For anchored control cases: the evidence rows listed in the case scope

The exact mapping is not supplied in the task materials — it must be inferred
from the data. Read [references/control-codes.md](references/control-codes.md)
for the full mapping guide across all five domains.

### Decision panels

Answer-template decision panels list specific stable IDs (reference IDs,
transaction IDs, charge IDs, event IDs) that each need a code. When the case
scope enumerates these IDs, look up each ID in the working set and assign the
correct code based on that record's properties.

### Certification

Every task ends with a certification decision (PASS / PASS_WITH_EXCEPTIONS /
HOLD). The thresholds come from the case scope's `status_thresholds`,
`certification_gate`, or equivalent fields. Compute the relevant rate
(quarantine rate, regression count, etc.) and compare against the threshold to
determine the outcome. Map status to action using the case scope's action map.

## Phase 8: Produce the answer

The answer must be **exactly one JSON object** that conforms to the answer
template supplied in the task. No Markdown, no commentary, no wrapping — just
the JSON.

Before writing the final answer:

1. Re-read the answer template to confirm every required field is present and
   every field type matches.
2. Verify all arrays have the correct length (minItems/maxItems) and ordering.
3. Verify all `enum` values match the allowed set.
4. Confirm stable IDs appear exactly as they do in the public data — do not
   invent, rename, or re-format them.
5. Verify numeric precision: round decimal values to the places specified, use
   exact integers for counts, and keep phone digits as strings.

## Common traps

- **Snapshot confusion**: applying quarantine or analysis before deduplicating
  across snapshots will produce wrong counts. Always deduplicate first.

- **Missing the authoritative snapshot**: the catalog or source-snapshots
  endpoint reveals which snapshot is certified. Do not assume — always check.

- **Quarantine-in-totals**: quarantined rows must be excluded from normalized
  totals but still count toward raw row counts and audit summaries. Mismatched
  rows contribute to totals but are flagged as exceptions.

- **Alias matching**: when matching record descriptions against reference
  aliases, use case-insensitive substring or exact matching as the data
  suggests. A record that partially matches multiple aliases from different
  canonical categories is ambiguous.

- **Ordering violations**: the answer template's ordering rules are strict.
  Lexicographic ascending means ASCII sort, not natural sort. ID lists must be
  deduplicated.

- **Pagination**: collection endpoints are paginated. Always check for and
  follow `next` links or iterate page parameters until every row is retrieved.
  A partial dataset produces wrong counts.

- **Phone digits**: when a field asks for canonical phone digits, strip all
  non-digit characters and return the result as a string (not a number), even
  if it contains only digits.

- **Email normalization**: canonical email addresses are trimmed and converted
  to NFKC lowercase. Do not add or remove characters beyond normalization.

## Reference files

When a specific domain needs deeper guidance, read the relevant reference:

- [references/control-codes.md](references/control-codes.md) — full mapping of
  control-code values to record properties across all five domains
- [references/snapshot-resolution.md](references/snapshot-resolution.md) —
  detailed rules for snapshot authority, deduplication, and retained-record
  selection
- [references/quarantine-rules.md](references/quarantine-rules.md) — per-domain
  quarantine conditions with concrete examples
