---
name: asteria-fleet-data-quality-hub
description: Reconcile overlapping source records, resolve canonical entities, assign opaque control codes, and produce certification decisions using the Asteria Fleet Data Quality Hub API.
---

# Asteria Fleet Data Quality Hub Solver

Use this skill for tasks that audit, reconcile, or certify data collections served
by the Asteria Fleet Data Quality Hub. The hub provides read-only access to
multi-source records, reference tables, source-snapshot metadata, and a SQL
query interface. Every task follows the same structural pattern: discover the
environment, select authoritative sources, reconcile overlapping records, resolve
references, quarantine invalid rows, compute canonical aggregates, assign opaque
control codes, apply certification thresholds, and return a single JSON answer
that matches the supplied answer template exactly.

## Environment discovery

The hub base URL and authentication token are always provided through a
separate `environment_access.md` or similar runtime context file. Do not
hardcode URLs or credentials; read them from the runtime-supplied access
configuration.

Start every task by calling these catalog endpoints in parallel:

1. `GET /api/catalog/collections` — list available collections and their IDs
2. `GET /api/catalog/schema` — column names and types for every collection
3. `GET /api/source-snapshots` — snapshot IDs, statuses (CERTIFIED, PROVISIONAL, STALE), creation timestamps, and row counts

The case scope from `payloads/case_scope.json` supplies the target
`collection_id` and a business cutoff timestamp. Use the snapshot metadata to
select which snapshots are in scope (created on or before the cutoff).

## Source selection and authoritative snapshot

When a collection has multiple snapshots:

- Prefer the snapshot with status `CERTIFIED` whose creation timestamp is on or
  before the business cutoff.
- If no CERTIFIED snapshot exists, prefer `PROVISIONAL` with the latest
  creation timestamp within the cutoff.
- The selected snapshot becomes the authoritative source for all subsequent
  reconciliation and counting.

If a task asks for the `authoritative_snapshot_id`, always report the stable
snapshot identifier from the `/api/source-snapshots` response, not a derived
string.

## Data retrieval

The hub offers two retrieval paths:

### Paginated GET endpoints

Domain-specific collections are available as paginated GET endpoints. The
catalog and schema responses list the available endpoint paths. Common
endpoints include:

- `/api/contacts` — contact/people records
- `/api/transactions/fuel` — fuel purchase transactions
- `/api/transactions/freight` — freight charge transactions
- `/api/maintenance/events` — maintenance event records

These endpoints typically use cursor-based or offset-based pagination. Fetch
all pages by looping until an empty page or an exhausted cursor is returned.
Some collections are larger than a single response page; always paginate
completely.

### SQL query interface

Use `POST /api/query` with `Authorization: Bearer <token>` for complex
filtering, aggregations, or joining across collections. The query token is
provided in `environment_access.md`. Send SQL as the request body.

When the collection is large or the task requires filtering by date range,
prefer the query interface to avoid transferring unnecessary rows.

## Reference table resolution

Several reference endpoints provide canonical mappings:

- `/api/reference/aliases` — maps free-text descriptions or alias strings to
  canonical categories (fuel types, service classes, etc.). Each alias row has
  an `alias_id`, the raw text, and the canonical category it resolves to.
- `/api/reference/conversions` — unit conversion factors (e.g., gallons to
  liters, miles to kilometers, pounds to kilograms).
- `/api/reference/fx` — foreign exchange rates with a base currency (usually
  USD), effective-date ranges, and conversion multipliers.

### Alias matching rules

For every reference alias, match the raw description text or alias identifier
from the primary record:

- **Exact match to one canonical category**: assign that category.
- **No match to any alias**: mark as `unrecognized`; the record cannot be
  assigned a recognized category.
- **Matches more than one distinct canonical category**: mark as `ambiguous`;
  both the unrecognized and ambiguous categories are counted separately in
  audit summaries that track them.

### Unit conversion

Convert physical quantities to the canonical unit declared in the case scope
using the factors from `/api/reference/conversions`. Apply the conversion
factor exactly as given (multiply source quantity by the factor). Round to
the precision declared in the answer template or case scope (typically 2
decimal places for volume, weight, distance, and currency).

### Currency conversion

Convert spend amounts to the declared base currency using the effective FX
rate for the transaction date from `/api/reference/fx`. Multiply the source
amount by the rate. Round to the declared precision.

## Duplicate reconciliation

Records from the same logical entity may appear in multiple snapshots. Detect
duplicates by matching on the stable logical identifier (e.g., `transaction_id`,
`charge_id`, `event_id`, or a composite key defined in the schema).

For each duplicate group:

1. List all snapshot IDs that contain the logical ID, sorted lexicographically.
2. Retain the occurrence from the authoritative (CERTIFIED) snapshot.
3. Count the total raw occurrences across all snapshots.
4. The duplicate raw count is the sum of (occurrences − 1) across all groups,
   or equivalently total raw rows across all snapshots minus the count of
   distinct logical IDs.

When two snapshots overlap and both are in scope, the certified snapshot's
version of each logical record always wins.

## Quarantine rules

Quarantined records are excluded from normalized totals but counted in
quarantine summaries. The quarantine conditions are domain-specific:

**Contact/people records:**
- A row with no usable contact channel: neither a non-empty email nor a
  non-empty phone field. Rows quarantined this way cannot participate in
  readiness or dispatchability.

**Fuel transactions:**
- Non-positive quantity (less than or equal to 0) after unit conversion.
- Recognized fuel category is `UNRECOGNIZED` or ambiguous.

**Freight charges:**
- Non-positive billed weight (less than or equal to 0) after unit conversion.
- Non-positive distance (less than or equal to 0) after unit conversion.
- Unrecognized service class alias (no matching canonical class).
- Ambiguous service class alias (matches more than one canonical class).

**Maintenance events:**
- Missing or unparseable timestamp.
- Odometer value outside the valid range defined in the schema.
- Negative labor hours (less than or equal to 0).
- Extreme labor hours exceeding the schema-defined maximum.

Quarantined rows must be listed in the quarantine output array sorted
lexicographically. For freight, separate quarantine reason counts
(`unrecognized_alias`, `ambiguous_alias`, `invalid_weight`,
`invalid_distance`) are required.

## Contact and entity resolution

When the task involves people or contact records from multiple source systems
(e.g., HR Directory, Dispatch, Identity Registry, CRM, Compliance Master,
Partner Portal):

### Duplicate clustering

Group source rows that represent the same real-world person or entity. Match
on identity keys such as normalized email address (lowercase, trimmed) or
normalized phone digits. A cluster of rows sharing a common normalized email
or phone constitutes one canonical person.

### Survivor selection

Within each cluster, pick one row as the survivor (master record) using this
precedence order among source systems:

1. Identity Registry (highest)
2. HR Directory
3. Compliance Master
4. Dispatch
5. CRM
6. Partner Portal (lowest)

When multiple rows share the same highest-precedence source, pick the row with
the lexicographically largest row ID as the survivor.

### Canonical field resolution

For each canonical entity, resolve each field from the highest-precedence
source system that supplies a non-empty, usable value for that field:

- **canonical_name**: Unicode-preserving display name from the best source.
- **canonical_email**: Trimmed, NFKC-normalized lowercase email from the best
  source. If no source provides a usable email, the field may be empty.
- **canonical_phone_digits**: Digits-only string from the best source. If no
  source provides a usable phone, the field may be empty.
- **canonical_city**: City value from the best source.
- **depot_code / region**: Value of the public region field from the best
  source that supplies it.
- **canonical_consent_status**: Prefer `GRANTED` over `PENDING` over `DENIED`
  over `UNKNOWN`. If multiple sources report consent, pick the most permissive
  (highest-precedence) status.
- **canonical_record_status**: Prefer `ACTIVE` over `INACTIVE`. If any source
  reports `ACTIVE`, the canonical status is `ACTIVE`.

Track which source system supplied each canonical field (`name_source_system`,
`contact_source_system`, `depot_source_system`, `consent_source_system`).

### Resolution outcomes

- **SINGLE_SOURCE**: Only one source row exists for this person; no merge
  needed.
- **FIELD_LEVEL_PRECEDENCE_APPLIED**: Multiple source rows were merged; field
  values were chosen by source-system precedence.
- **CONTESTED_NO_AUTOMERGE**: An identifier watchlist case where the source
  records cannot be automatically merged (divergent identities).
- **NO_USABLE_CONTACT**: The canonical entity has neither a usable email nor a
  usable phone; it is quarantined.

### Readiness and dispatchability

An entity is **readiness-eligible** when its canonical record status is
`ACTIVE` and it has at least one usable contact channel (non-empty email or
non-empty phone digits).

A channel is **ready** only when consent is `GRANTED`:

- `both`: active, has both usable email and usable phone, consent GRANTED.
- `email_only`: active, has only usable email, consent GRANTED.
- `phone_only`: active, has only usable phone, consent GRANTED.
- `not_ready`: all other readiness-eligible entities (active with a channel
  but consent not GRANTED, or no usable channel, or inactive).

An entity is **dispatchable** when it is active, consent is GRANTED, and it
has at least one usable contact channel.

### Depot/region rollups

Group canonical entities by their `region` field. For each depot, partition
the canonical entities into dispatchable, blocked-by-consent (active + usable
channel + non-GRANTED consent), blocked-no-contact (no usable channel), and
blocked-inactive (inactive + usable channel). These four counts sum to the
total person count for that depot.

## Data integrity checks (maintenance events)

For maintenance events, scan each raw event (after deduplication) for these
integrity issues:

- **missing_timestamp**: event timestamp is null or empty.
- **invalid_timestamp**: timestamp cannot be parsed or is outside the business
  period.
- **invalid_odometer**: odometer value is null, non-numeric, or outside the
  valid range defined by the schema.
- **negative_labor**: labor_hours less than or equal to 0.
- **extreme_labor**: labor_hours exceeds the schema maximum.
- **odometer_regression**: for a given asset, a chronologically later event
  has a lower odometer reading than a chronologically earlier event, and both
  events are otherwise valid (have parseable timestamps and valid odometer
  readings).

Events with missing/invalid timestamps, invalid odometer, negative labor, or
extreme labor are **rejected** (invalid) and listed in `invalid_event_ids`.
Odometer regressions are not rejected; they are reported in
`corrected_metrics.regression_event_ids` and the affected assets in
`corrected_metrics.regression_asset_ids`.

Compute `total_distance_km` as the sum across all assets of (last reliable
odometer reading minus first reliable odometer reading) for that asset within
the reconstructed history, using only valid non-rejected events. Round to the
declared precision.

### Asset risk ranking

For each asset, count:
- `rejected_event_count`: number of events rejected for this asset.
- `regression_event_count`: number of odometer regression events for this
  asset.

Rank by `rejected_event_count` descending, then `regression_event_count`
descending, then `asset_id` ascending. Take the top N as specified by the case
scope.

## Category mismatch detection

For transactions with an expected category and a recognized (resolved) category:

- Compare the expected category (from the source record) against the
  recognized category (from alias resolution).
- If they differ, the transaction is a **mismatch**.
- Mismatched transactions are listed in the mismatch output array sorted
  lexicographically by transaction/charge ID.

For fuel: expected fuel type from the transaction record versus resolved fuel
type from alias matching.

For freight: expected service class from the charge record versus resolved
service class from alias matching.

## Exception counting

An **exception** is a retained logical record that is either:
- A category mismatch (expected does not equal recognized), or
- Quarantined for any reason.

A single record counts as one exception even if it satisfies multiple
conditions (e.g., both a mismatch and a quarantine). For merchant/carrier
ranking, count exceptions per merchant/carrier and break out mismatch vs.
quarantine sub-counts.

## Carrier and merchant ranking

When case scope requests top-N carriers or merchants:

- **Fuel merchants** (train 002 pattern): rank by `exception_count` descending,
  then `merchant_id` ascending.
- **Freight carriers** (train 005 pattern): rank by `mismatch_spend_usd`
  descending, then `carrier_id` ascending. `mismatch_spend_usd` is the
  normalized USD spend on valid charges where the recognized service class
  differs from the expected class. Quarantined charges do not contribute to
  mismatch_spend_usd but count toward `quarantine_count` and `exception_count`.

## Opaque control code assignment

The answer template defines allowed code values as enums. These codes represent
internal Asteria policy decisions. Infer them from observable data properties
following the mapping patterns below. The exact code labels (e.g., `IC-25`,
`FP-55`, `OR-80`, `RB-42`, `SB-61`, `LD-53`, `MS-47`, `HR-74`) are drawn
from the enum sets in the answer template; the mapping logic is consistent
across tasks.

### IDENTITY codes (IC-*)

Identity codes classify the provenance and confidence of a canonical person
resolution:

| Code  | When to assign |
|-------|---------------|
| IC-25 | A single-source identity (one row, no merge) that is active, consent GRANTED, and dispatchable. |
| IC-40 | A quarantined identity (no usable contact channel). |
| IC-70 | A multi-source merged identity where field-level precedence was applied and the canonical entity has at least one usable contact channel. |
| IC-90 | A multi-source merged identity where all member rows are quarantined (no usable channel from any source), or a contested watchlist case that cannot be resolved. |

Assign IC-70 for focus clusters where the survivor was selected by source
precedence and the entity has usable contact. Assign IC-25 for single-row
dispatchable entities. Assign IC-40 for single-row quarantined entities.
Assign IC-90 for multi-row quarantined clusters or contested watchlist cases.

### FIELD_PROVENANCE codes (FP-*)

Field provenance codes capture how field values were sourced:

| Code  | When to assign |
|-------|---------------|
| FP-20 | Single-source record from a certified system; no merge needed. |
| FP-55 | Multi-source merge with field-level precedence applied; the canonical entity draws values from different source systems. |
| FP-75 | Quarantined record where field provenance is unreliable (no usable contact). |

### OUTREACH codes (OR-*)

Outreach codes describe the contact readiness and consent state:

| Code  | When to assign |
|-------|---------------|
| OR-15 | Inactive canonical entity. |
| OR-35 | Active entity with consent GRANTED and at least one usable channel (dispatchable / channel-ready). |
| OR-60 | Quarantined entity (no usable contact channel). |
| OR-80 | Active entity with a usable channel but consent is not GRANTED (PENDING, DENIED, or UNKNOWN), or a contested watchlist entity. |

For readiness partition codes, assign OR-35 to `both`, `email_only`, and
`phone_only` (all represent channel-ready states). Assign OR-80 to `not_ready`.

### REFERENCE policy codes (RB-*)

Used for reference alias decisions:

| Code  | When to assign |
|-------|---------------|
| RB-17 | The alias resolves unambiguously to a canonical category AND it appears in more than one alias entry (multiple surface forms map to the same category). |
| RB-42 | The alias resolves unambiguously to a canonical category AND it is the only alias entry for that surface form (one-to-one mapping). |
| RB-83 | The alias has no recognized canonical category (unrecognized), or it matches multiple categories (ambiguous). |

Check the alias reference table: if an `alias_id` has a one-to-one mapping
(single row with that text, single canonical category), assign RB-42. If
multiple alias rows share the same canonical category but different surface
forms, assign RB-17. If no category or ambiguous, assign RB-83.

### SOURCE BASIS codes (SB-*)

Used for source retention decisions on individual transactions/charges:

| Code  | When to assign |
|-------|---------------|
| SB-24 | The record exists only in the provisional snapshot (not in certified). The authoritative copy is the provisional one by necessity. |
| SB-61 | The record appears in both certified and provisional snapshots, and the certified copy was retained. |
| SB-79 | The record exists only in the certified snapshot. No duplicate resolution needed. |

### LEDGER DISPOSITION codes (LD-*)

Used for ledger routing decisions:

| Code  | When to assign |
|-------|---------------|
| LD-14 | Quarantined AND unrecognized/ambiguous (class or category cannot be determined). |
| LD-31 | Valid but with a category mismatch (expected does not equal recognized). |
| LD-53 | Quarantined for invalid physical measures (non-positive weight, non-positive distance, or non-positive quantity), but the category IS recognized. |
| LD-72 | Valid with matching category (expected equals recognized), no issues. |
| LD-88 | Quarantined for both a physical measure issue AND unrecognized/ambiguous category. |

### MAINTENANCE SOURCE codes (MS-*)

Used for maintenance event source classification:

| Code  | When to assign |
|-------|---------------|
| MS-12 | The event is valid (no integrity issues) and appears only in the certified snapshot. |
| MS-47 | The event is valid and appears in both snapshots; the certified copy was retained. |
| MS-86 | The event has one or more integrity issues (invalid, rejected, or regression). |

### HISTORY ROUTE codes (HR-*)

Used for maintenance event history routing:

| Code  | When to assign |
|-------|---------------|
| HR-19 | The event is rejected (invalid) due to missing/invalid timestamp, invalid odometer, negative labor, or extreme labor. |
| HR-33 | The event is valid with no integrity issues and no odometer regression. |
| HR-74 | The event is valid but has an odometer regression, or the event appears in both snapshots and the certified copy was retained. |

When an event appears in both snapshots (duplicate group member), assign HR-74
if the event is also in the event_decision_panel; otherwise assess by its
validity status.

## Certification decision

Every task produces a final status/action pair. Map computed metrics to
thresholds declared in the case scope:

When the case scope supplies explicit thresholds (e.g., `pass_max_quarantine_rate`,
`pass_with_exceptions_max_quarantine_rate`):

1. Compute `quarantine_rate` = quarantined rows divided by canonical entity count,
   rounded to 4 decimal places.
2. If `quarantine_rate` less than or equal to `pass_max_quarantine_rate` (typically 0.0):
   status = `PASS`, action = `RELEASE`.
3. If `quarantine_rate` less than or equal to `pass_with_exceptions_max_quarantine_rate` (typically
   0.04): status = `PASS_WITH_EXCEPTIONS`, action = `REVIEW_EXCEPTIONS`.
4. Otherwise: status = `HOLD`, action = `BLOCK_AND_REMEDIATE`.

When the case scope provides an explicit certification gate (e.g.,
`odometer_regression_status: HOLD`):

- Use the gate value directly if no threshold computation is required.
- The status becomes `HOLD` whenever odometer regressions exist.
- Otherwise apply standard threshold logic.

For tasks without explicit thresholds, infer the status from the data quality
profile: `PASS` only when zero exceptions exist; `PASS_WITH_EXCEPTIONS` when
exceptions exist but are below an implicit tolerance; `HOLD` when exceptions
are widespread or a blocking condition (odometer regression, structural
mismatch, etc.) is present.

## Answer formatting

Return exactly one JSON object. Every key required by the answer template must
be present. No additional keys. No Markdown, no commentary, no whitespace
outside the JSON.

### Ordering rules

- All ID arrays (row IDs, transaction IDs, event IDs, charge IDs, asset IDs):
  sorted **lexicographically ascending** (standard string sort).
- Object arrays (focus clusters, duplicate groups, event panels, reference
  rows, etc.): sorted by their primary key field ascending.
- `focus_clusters`: sorted by `cluster_id` ascending.
- `member_row_ids` within each cluster: sorted lexicographically ascending,
  deduplicated.
- `region_rollup`: sorted by `region` ascending.
- `fuel_type_totals`: sorted by `fuel_type` ascending.
- `service_class_totals`: sorted by `service_class` ascending.
- `exception_merchant_ranking` / `carrier_ranking`: ordered by the ranking
  criteria declared in the case scope, then by the tie-break ID ascending.
- `asset_risk_ranking`: by `rejected_event_count` DESC, `regression_event_count`
  DESC, `asset_id` ASC, with `rank` starting at 1.
- `policy_control_cases`: sorted by `control_case_id` ascending.
- `event_decision_panel`: sorted by `event_id` ascending.
- `duplicate_groups`: sorted by the logical ID ascending; `snapshot_ids`
  within each group sorted lexicographically ascending.

### Numeric precision

- All counts are exact integers.
- Currency, volume, weight, and distance values are numbers rounded to 2
  decimal places (or the precision declared in the case scope).
- Rates and ratios use the precision declared in the answer template (commonly
  4 decimal places for quarantine rate).

### Odometer distance calculation

For maintenance events, compute per-asset distance:

1. Group valid (non-rejected) events by asset_id.
2. Sort each asset's events by timestamp ascending.
3. For each asset: `distance` = last event's odometer minus first event's odometer.
4. Sum across all assets.
5. If an asset has only one valid event, its distance contribution is 0.
6. Round the total sum to 2 decimal places.

## Workflow summary

1. Read `environment_access.md` for base URL and credentials.
2. Call `/api/catalog/collections`, `/api/catalog/schema`, and
   `/api/source-snapshots` in parallel.
3. Identify the target collection and its available snapshots.
4. Select the authoritative snapshot (CERTIFIED, within cutoff).
5. Fetch all reference data: `/api/reference/aliases`,
   `/api/reference/conversions`, `/api/reference/fx`.
6. Fetch the primary data collection from all in-scope snapshots using
   paginated GET or `POST /api/query`.
7. Reconcile duplicates across snapshots; retain certified copies.
8. Resolve aliases/references to canonical categories.
9. Apply unit and currency conversions to physical quantities and spend.
10. Quarantine invalid records per domain rules.
11. Compute canonical entities and field-level resolutions (for contact tasks).
12. Detect category mismatches.
13. Compute all aggregate counts, rates, and per-entity/per-region rollups.
14. Assign opaque control codes based on observable data properties.
15. Apply certification thresholds to determine status and action.
16. Format the answer JSON with strict ordering and precision compliance.

## Domain-specific schemas

The hub collections share common patterns but differ in detail. Always consult
`/api/catalog/schema` for exact column names and types. Key fields observed
across tasks:

**Contacts** (`/api/contacts`):
`row_id`, `snapshot_id`, `source_system`, `name`, `email`, `phone`,
`city`, `region`, `consent_status`, `record_status`, `created_at`

**Fuel transactions** (`/api/transactions/fuel`):
`transaction_id`, `snapshot_id`, `asset_id`, `merchant_id`, `transaction_at`,
`description`, `expected_fuel_type`, `quantity`, `quantity_unit`, `spend`,
`spend_currency`

**Freight charges** (`/api/transactions/freight`):
`charge_id`, `snapshot_id`, `carrier_id`, `charge_date`, `description`,
`expected_service_class`, `billed_weight`, `weight_unit`, `distance`,
`distance_unit`, `spend`, `spend_currency`

**Maintenance events** (`/api/maintenance/events`):
`event_id`, `snapshot_id`, `asset_id`, `event_timestamp`, `odometer_km`,
`labor_hours`, `description`

**Reference aliases** (`/api/reference/aliases`):
`alias_id`, `canonical_category`, `raw_text`

**Reference conversions** (`/api/reference/conversions`):
`from_unit`, `to_unit`, `factor`

**Reference FX** (`/api/reference/fx`):
`from_currency`, `to_currency`, `rate`, `effective_from`, `effective_to`
