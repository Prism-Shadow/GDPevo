---
name: asteria-fleet-data-quality-hub
description: "Data quality audit, reconciliation, and certification for the Asteria Fleet Data Quality Hub. Use when the task involves auditing, reconciling, normalizing, or certifying fleet operational data (contacts, fuel transactions, freight charges, or maintenance events) against a read-only Hub API, or when the task requires assigning Asteria opaque control codes (IC, OR, FP, RB, SB, LD, MS, HR) based on data evidence. Trigger on phrases like 'Fleet Data Quality Hub', 'Asteria fleet', 'partner onboarding certification', 'fuel ledger audit', 'freight accrual reconciliation', 'maintenance log integrity', 'field service roster readiness', 'contact-readiness brief', or any task referencing environment_access.md with Asteria API endpoints."
license: MIT
compatibility: designed for deepagents-code
---

# Asteria Fleet Data Quality Hub

## Quick Start

Every Asteria Fleet audit follows the same skeleton:

1. Read `environment_access.md` for `base_url` and `allowed_business_endpoints`.
2. Read the task's `case_scope.json` for the collection ID, business cutoff, and scoped decision IDs.
3. **Discover**: call `GET /api/catalog/collections` and `GET /api/catalog/schema` to confirm the collection shape.
4. **Source snapshots**: call `GET /api/source-snapshots` to identify the authoritative (certified) snapshot and any provisional duplicates.
5. **Fetch data**: use domain-specific endpoints or `POST /api/query` with pagination.
6. **Reconcile**: deduplicate (retain certified over provisional), quarantine invalid rows, detect mismatches.
7. **Normalize**: apply unit conversions (`/api/reference/conversions`) and FX (`/api/reference/fx`).
8. **Resolve focus entities**: merge clusters, select survivors, compute canonical values.
9. **Assign control codes**: derive opaque codes from data evidence (see [control_codes.md](references/control_codes.md)).
10. **Certify**: compute quality metrics, apply thresholds, return PASS/PASS_WITH_EXCEPTIONS/HOLD.

## API Discovery

Use `GET /api/catalog/collections` to list available collections. Each object includes `collection_id`, `snapshot_ids`, and `row_count`. Use `GET /api/catalog/schema` to see field definitions for a collection. The schema endpoint accepts `?collection_id=...` and returns field names, types, nullable flags, and primary-key markers.

`GET /api/source-snapshots` returns every snapshot across all collections. Filter by `?collection_id=...` to get only relevant snapshots. Each snapshot has a `snapshot_id` and `status` field. Typical status values are `CERTIFIED`, `PROVISIONAL`, and `STALE`.

All domain endpoints support `?snapshot_id=...` to scope to a single snapshot. Omitting the parameter returns the union. Use `POST /api/query` for SQL-like queries when you need filtering, aggregation, or joins beyond what the domain endpoints provide.

A full endpoint catalog is in [api_endpoints.md](references/api_endpoints.md).

## Source Reconciliation (General)

Every audit resolves overlapping source records. The universal rule:

- **Certified snapshots always take priority over provisional snapshots.**
- When the same logical record appears in both, retain the certified occurrence and discard the provisional one.
- When a logical record appears only in a provisional snapshot, that occurrence is retained but may carry source-basis implications.

For contacts and maintenance events, logical identity is determined by the domain's natural key (person identity key for contacts, `logical_event_id` for maintenance events). For transactions (fuel and freight), logical identity is the transaction ID itself.

**Snapshot status field**: snapshots carry a `status` field. Read it from `/api/source-snapshots`. Values:
- `CERTIFIED`: authoritative, always preferred
- `PROVISIONAL`: secondary, retained only when no certified copy exists
- `STALE`: treat as provisional for priority purposes

Count `duplicate_raw_count` as the number of raw rows that were discarded because a certified copy of the same logical record exists.

## Domain-Specific Rules

Full quality rules per domain are in [data_quality_rules.md](references/data_quality_rules.md). The summary:

### Contacts (Partner Onboarding / Field Service)
- **Cluster key**: person identity key (UID or equivalent). Rows sharing the same identity key are the same person.
- **Quarantine**: a row with no usable email AND no usable phone. A usable email is non-empty and contains `@`. A usable phone is non-empty, after stripping non-digits has length >= 7.
- **Survivor**: highest `row_id` (lexicographic) in the cluster.
- **Canonical city**: from the Compliance Master source row in the cluster.
- **Channel readiness**: an entity is eligible when active AND has at least one usable email or phone. A channel is ready when consent is GRANTED.
- **Field-level precedence for multi-source merges**: name from HR Directory, contact (email/phone) from Identity Registry, depot (region) from HR Directory, consent from Identity Registry. When a source is absent for a given person, fall through Dispatch then HR Directory then Identity Registry.

### Fuel Transactions
- **Category matching**: the `description` field on each transaction is matched against `/api/reference/aliases`. Aliases map descriptive text to canonical `fuel_type` values (`BIODIESEL`, `DIESEL`, `ELECTRIC_CHARGE`, `PREMIUM_UNLEADED`, `UNLEADED`). A mismatch occurs when the `expected_fuel_type` on the transaction differs from the recognized canonical fuel type.
- **Unrecognized**: a description that matches zero aliases (no recognized category) or matches aliases that resolve to more than one distinct fuel type (ambiguous).
- **Invalid quantity**: `volume` is zero, negative, or null.
- **Normalization**: apply `/api/reference/conversions` (target unit `L`) then `/api/reference/fx` (target currency `USD`).
- **Quarantine**: transactions with an unrecognized description or invalid quantity. Do not include quarantined transactions in normalized totals.

### Freight Charges
- **Service class matching**: `description` field matched against `/api/reference/aliases`. Canonical service classes: `EXPRESS`, `HAZMAT`, `OVERSIZE`, `REFRIGERATED`, `STANDARD`. Mismatch when `expected_service_class` differs from recognized canonical class.
- **Quarantine**: ambiguous alias (matches >1 class), unrecognized alias (matches zero classes), non-positive `weight_kg`, non-positive `distance_km`.
- **Normalization**: apply `/api/reference/conversions` for weight (target `KG`) and distance (target `KM`), then `/api/reference/fx` for currency (target `USD`).
- **Duplicate groups**: when a `charge_id` appears in both certified and provisional snapshots, report it as a duplicate group. Retain the certified occurrence.

### Maintenance Events
- **Duplicate resolution**: by `logical_event_id` across snapshots. Retain certified.
- **Invalid events**: missing or unparsable `event_timestamp`, `odometer_reading` outside range (null, negative, or implausible), `labor_hours` negative or extreme. Invalid events are fully rejected from the corrected history.
- **Odometer regression**: within a single asset, when a later event (by timestamp) has a lower odometer reading than an earlier event. The later event is flagged as a regression. Regression events remain in the history for count purposes but their odometer reading is excluded from the corrected distance calculation.
- **Corrected distance**: for each asset, `last_reliable_odometer - first_reliable_odometer`, excluding regressions, summed across all assets.

## Control Code Assignment

Asteria uses opaque three-character codes for internal controls. The code schemes and assignment rules are documented in [control_codes.md](references/control_codes.md). Key families:

- **IC** (Identity): assigned based on identity resolution confidence and cluster characteristics.
- **OR** (Outreach): assigned based on contact readiness state.
- **FP** (Field Provenance): assigned based on source-system lineage of canonical field values.
- **RB** (Reference Basis): assigned for alias/fuel-reference decisions.
- **SB** (Source Basis): assigned for source-retention decisions per transaction.
- **LD** (Ledger Disposition): assigned for ledger routing per transaction.
- **MS** (Maintenance Source): assigned per maintenance event based on source snapshot.
- **HR** (History Route): assigned per maintenance event based on validation outcome.

## Numeric Precision

All intermediate calculations use full precision. Round only at the final output to the precision specified in the answer template (typically 2 decimal places for monetary and physical measures, 4 decimal places for rates). Use standard rounding (half-up or half-even, either is acceptable as long as it is consistent).

## Resources

### [api_endpoints.md](references/api_endpoints.md)
Complete endpoint catalog with parameters, pagination, and request/response shapes.

### [data_quality_rules.md](references/data_quality_rules.md)
Domain-specific quality rules: quarantine conditions, deduplication, normalization, and survivor selection for each data domain.

### [control_codes.md](references/control_codes.md)
Opaque control code schemes and assignment rules for all eight code families used in Asteria Fleet audits.
