# Domain-Specific Classification and Certification

## Common pipeline steps (all domains)

1. Read `case_scope.json` for the collection, cutoff, and scoped IDs.
2. Call `/api/source-snapshots` to identify authoritative (`-certified`) and
   supplementary (`-provisional`) snapshots.
3. Load all rows from every relevant snapshot via the domain endpoint and via
   `POST /api/query` for aggregations.
4. Classify each row. Quarantined rows are excluded from all normalized totals.
5. Assign opaque control codes using the fact patterns in
   [code_families.md](code_families.md).
6. Apply the certification gate from the case scope.

## Deduplication (cross-snapshot overlap)

When the same logical record appears in both the certified and provisional
snapshot:

- Retain the certified copy as the survivor.
- Count the provisional copy as a duplicate raw row.
- The logical count = total raw rows - number of duplicate pairs.
- In `duplicate_groups`, report each multi-occurrence logical ID with its
  snapshot_ids and retained_snapshot_id (always the certified ID).

When a record appears in only one snapshot, retain it as-is.

## Contact / Roster domain

**Endpoints**: `GET /api/contacts`, `POST /api/query`
**Row ID format**: PAR-Cxxxxx (partner onboarding) or FIE-Cxxxxx (field service)

### Duplicate clustering

Rows sharing a common logical identity form clusters. Within a cluster:

- **Name, city, depot/region**: Prefer HR Directory over other sources.
- **Email, phone**: Prefer Identity Registry.
- **Consent status**: Prefer Identity Registry.
- **Record status (ACTIVE/INACTIVE)**: Prefer HR Directory.
- **Survivor/master row**: Select the highest-ID row in the cluster as the
  stable master ID.

A cluster of 3 rows from 3 different source systems is resolved with
`FIELD_LEVEL_PRECEDENCE_APPLIED`.

### Quarantine

A row is quarantined when it has no usable email AND no usable phone (both
missing, empty, or invalid). Quarantined rows are counted in quarantine totals,
listed in `quarantine_row_ids`, and excluded from readiness eligibility.

### Readiness

An entity is readiness-eligible when:
- Record status is ACTIVE, AND
- At least one usable channel (email or phone) is present.

A channel is ready when consent is GRANTED. Partitions:
- **both**: usable email AND usable phone, consent GRANTED.
- **email_only**: usable email only, consent GRANTED.
- **phone_only**: usable phone only, consent GRANTED.
- **not_ready**: eligible but consent is not GRANTED, or no usable channel.

### Certification gate (partner onboarding)

From the case scope `status_thresholds`:
- `pass_max_quarantine_rate`: if quarantine_rate <= this, status is PASS.
- `pass_with_exceptions_max_quarantine_rate`: if quarantine_rate <= this but
  > pass_max, status is PASS_WITH_EXCEPTIONS.
- Above exceptions threshold: HOLD.

Compute `quarantine_rate = quarantine_count / canonical_entity_count`, rounded
to 4 decimal places.

### Region rollup

Group canonical entities by their `region` field. Count entities per region.
Output every region listed in the enum (not only those with counts). Regions
in the partner onboarding schema are: BE, England, MD, ON, SG, TX.

### Anchored control cases

For each control case anchor in the case scope, query the seed rows. Assign
identity_code, outreach_code, and field_provenance_code based on:

- **IC-25**: single-source, no merge.
- **IC-90**: contested identifier with conflicting identity signals.
- **IC-40**: quarantined row.
- **IC-70**: multi-source merge with field-level precedence.
- **OR-80**: consent-blocked (active with usable channel but not GRANTED).
- **OR-60**: no usable contact channel.
- **OR-15**: inactive exclusion.
- **OR-35**: channel-eligible (consent GRANTED with usable channel).
- **FP-20**: single-source.
- **FP-55**: multi-source merge.
- **FP-75**: quarantined/invalid.

## Fuel audit domain

**Endpoints**: `GET /api/transactions/fuel`, `GET /api/reference/aliases`,
`GET /api/reference/conversions`, `GET /api/reference/fx`, `POST /api/query`
**Row ID format**: FT-YYYYMM-NNNNNN
**Canonical fuel types**: BIODIESEL, DIESEL, ELECTRIC_CHARGE, PREMIUM_UNLEADED,
UNLEADED

### Classification

For each transaction, map the description to a canonical fuel type via the
alias reference table:

- **Valid (no exception)**: exactly one alias match AND the matched category
  equals the expected category.
- **Mismatch**: exactly one alias match but category differs from expected.
  Included in normalized totals, flagged in `mismatch_transaction_ids`.
- **Unrecognized (0 matches)**: description matches zero aliases. Quarantined,
  excluded from normalized totals.
- **Ambiguous (>1 match)**: description matches more than one alias.
  Quarantined, excluded from normalized totals.

Also quarantine any transaction with non-positive quantity (<=0).

### Exception counting

`exception_transaction_count` = mismatch_count + unrecognized_count +
ambiguous_count + invalid_quantity_count.

The `unrecognized_transaction_ids` list includes BOTH zero-match AND ambiguous
transactions. The unrecognized_count field counts only zero-match; ambiguous_count
counts only >1-match.

### Normalization

1. Convert quantity to liters (L) using `/api/reference/conversions`.
2. Convert amount to USD using `/api/reference/fx`.
3. Round to 2 decimal places.

### Focus assets

For each scoped asset_id, compute over all logical transactions (including
mismatches and quarantined):

- logical_transaction_count: all transactions for the asset.
- valid_transaction_count: non-quarantined transactions.
- mismatch_count: valid transactions with category mismatch.
- quarantine_count: quarantined transactions.
- exception_count = mismatch_count + quarantine_count.
- volume_l and spend_usd: totals for valid (non-quarantined) transactions only.

### Merchant ranking

A merchant exception is a logical transaction with a category mismatch or a
quarantine condition. Rank merchants by exception_count descending, then
merchant_id ascending.

### Policy decision panel

For each scoped alias: assign RB-17 (unambiguous single-match), RB-42
(ambiguous multi-match), or RB-83 (unrecognized).

For each scoped transaction: assign source_basis_code (SB-24 = certified-only,
SB-61 = both-snapshots retained, SB-79 = provisional-only) and
ledger_disposition_code (LD-14 = unrecognized, LD-31 = valid mismatch,
LD-53 = clean valid, LD-72 = clean duplicate-resolved, LD-88 = ambiguous).

### Certification gate

Check the case scope for thresholds. In the fuel audit training example, there
is no explicit threshold; status is HOLD when exceptions exist.

## Maintenance audit domain

**Endpoints**: `GET /api/maintenance/events`, `POST /api/query`
**Row ID format**: ME-Q1-NNNNNN
**Snapshots**: `maintenance_events_YYYY_Q-certified` and `...-provisional`

### Invalid event detection

Reject (do not include in corrected_metrics valid_event_count) events with:
- Missing or unparseable `timestamp`.
- `timestamp` outside the business period (from case_scope).
- `odometer` outside valid range.
- Negative `labor_hours`.
- Extreme `labor_hours` (beyond a reasonable threshold).

List rejected event IDs in `invalid_event_ids`, sorted lexicographically.

### Odometer regression

For each asset, sort valid (non-invalid) events by timestamp ascending. If any
event has a lower odometer reading than the previous event, flag it as a
regression. Regression events remain in the valid_event_count but are listed in
`regression_event_ids`. The asset is listed in `regression_asset_ids`.

### Corrected distance

For each asset: total_distance = last valid odometer - first valid odometer.
Sum across all assets to get `total_distance_km`. Round to 2 decimal places.

Exclude regression events from distance calculation: use only the reliable
readings (the highest odometer before a regression, and the first valid
reading).

### Issue counts

Count distinct events exhibiting each issue. An event may contribute to
multiple issue counts.

- `missing_timestamp`: timestamp is null or empty.
- `invalid_timestamp`: timestamp exists but is unparseable or outside the
  business period.
- `invalid_odometer`: odometer outside valid range.
- `negative_labor`: labor_hours < 0.
- `extreme_labor`: labor_hours exceeds reasonable threshold.
- `odometer_regression`: regression flagged (subset of valid events).

### Duplicate groups

Every event appearing in both certified and provisional snapshots. Report the
logical_event_id, both snapshot_ids, retained_event_id (certified copy), and
retained_snapshot_id.

### Event decision panel

For each scoped event_id, assign:
- `maintenance_source_code`: MS-12 (provisional-only), MS-47 (certified-only),
  MS-86 (both snapshots).
- `history_route_code`: HR-19 (regression), HR-33 (clean), HR-74 (invalid).

### Asset risk ranking

Rank assets by `rejected_event_count DESC`, then `regression_event_count DESC`,
then `asset_id ASC`. Top 5.

### Certification gate

From the case scope: odometer_regression_status = HOLD and
odometer_regression_action = BLOCK_AND_REMEDIATE when any regression exists.
This means the certification status is HOLD / BLOCK_AND_REMEDIATE whenever
odometer_regression > 0.

## Freight audit domain

**Endpoints**: `GET /api/transactions/freight`, reference endpoints,
`POST /api/query`
**Row ID format**: FC-YYYYMM-NNNNNN
**Canonical service classes**: EXPRESS, HAZMAT, OVERSIZE, REFRIGERATED, STANDARD

### Classification

Map the service_class field (an alias like FRA-xxx) to canonical service class
via `/api/reference/aliases`:

- **Valid**: exactly one alias match AND matched class equals expected class.
- **Mismatch**: exactly one match but class differs from expected. Included in
  normalized totals.
- **Unrecognized (0 matches)**: quarantined.
- **Ambiguous (>1 match)**: quarantined.
- **Invalid physical measures**: non-positive weight or non-positive distance:
  quarantined.

Quarantine reasons are tracked separately:
- `unrecognized_alias`: 0 alias matches.
- `ambiguous_alias`: >1 alias matches.
- `invalid_weight`: weight <= 0.
- `invalid_distance`: distance <= 0.

### Normalization

1. Convert weight to KG and distance to KM using `/api/reference/conversions`.
2. Convert amount to USD using `/api/reference/fx`.
3. Round to 2 decimal places.
4. Exclude quarantined charges from all normalized totals.

### Carrier ranking

Accrual exposure = normalized USD on valid mismatch charges (where the
recognized class differs from expected). Rank carriers by `mismatch_spend_usd`
descending, then `carrier_id` ascending. Top 5.

`exception_count` = mismatch_count + quarantine_count for each carrier.

### Decision panels

- **reference_rows**: RB-17 (unambiguous single match), RB-42 (ambiguous),
  RB-83 (unrecognized).
- **source_retention**: SB-24 (certified-only), SB-61 (both-retained),
  SB-79 (provisional-only).
- **ledger_routing**: LD-14 (unrecognized alias), LD-31 (valid mismatch),
  LD-53 (invalid physical measure), LD-72 (valid clean), LD-88 (ambiguous
  alias).

### Certification gate

From the training examples, status is HOLD / BLOCK_AND_REMEDIATE when
quarantine_count > 0 or mismatch_count exceeds a threshold. Apply the same
logic: if any quarantined charges exist, recommend HOLD.

## Field service roster domain

**Endpoints**: `GET /api/contacts`, `POST /api/query`
**Row ID format**: FIE-Cxxxxx
**Source systems**: HR Directory, Dispatch, Identity Registry

### Merge clustering

Group rows sharing a common logical identity. Resolve fields with source
precedence:

- Name: HR Directory > Dispatch > Identity Registry
- Email, phone: Identity Registry > HR Directory > Dispatch
- City, depot/region: HR Directory > Dispatch > Identity Registry
- Consent: Identity Registry > HR Directory > Dispatch
- Record status: HR Directory > Dispatch > Identity Registry

Survivor/master ID: highest row ID in the cluster.

### Quarantine

A person with no usable email AND no usable phone is quarantined.

### Dispatchable

A person is dispatchable when: ACTIVE AND has at least one usable channel AND
consent is GRANTED.

### Identifier watchlist

Rows with conflicting identity signals form contested clusters. These appear in
 `contested_cluster_ids` (matching patterns like IDENTIFIER-CASE-NNN).

### Depot readiness

Group by depot_code (region field). For each depot:
- `total_person_count` = all canonical people.
- `dispatchable_person_count` = active + usable channel + consent GRANTED.
- `blocked_consent_count` = active + usable channel + consent NOT GRANTED.
- `blocked_no_contact_count` = no usable channel.
- `blocked_inactive_count` = INACTIVE + usable channel.

Sum of the four disposition counts must equal total_person_count.

### Policy control cases

For each CONTROL-xxx case, inspect the evidence row IDs:

- **IDENTITY cases**: IC-25 (single-source single-row), IC-40 (quarantined),
  IC-70 (multi-source merge), IC-90 (contested identifier).
- **OUTREACH cases**: OR-15 (inactive), OR-35 (dispatchable), OR-60
  (quarantined/no-contact), OR-80 (consent-blocked).
- **FIELD_PROVENANCE cases**: FP-20 (single-source), FP-55 (multi-source merge),
  FP-75 (quarantined/invalid).

### Release decision

- **PASS / RELEASE**: zero quarantined rows, all depots have dispatchable
  people.
- **PASS_WITH_EXCEPTIONS / REVIEW_EXCEPTIONS**: minor issues only.
- **HOLD / BLOCK_AND_REMEDIATE**: significant quarantine or consent issues
  exist (the most common outcome when any depot has zero dispatchable people or
  when blocked_consent_count is high).
