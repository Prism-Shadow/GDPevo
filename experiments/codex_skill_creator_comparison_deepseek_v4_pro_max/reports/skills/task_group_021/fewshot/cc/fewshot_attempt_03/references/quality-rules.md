# Domain-Specific Quality Rules

Apply these rules during Phase 6 after source reconciliation and after filtering out records whose timestamps exceed the business cutoff. Quarantined records are excluded from all normalized totals. Invalid records are excluded from both totals and validity counts.

## Contacts (Partner Onboarding / Field Service)

| Rule | Condition | Disposition |
|---|---|---|
| Unusable contact | `email` is null/empty/whitespace AND `phone_digits` is null/empty/whitespace | Quarantine |
| Active | `record_status` = `"ACTIVE"` | Eligible for readiness |
| Inactive | `record_status` = `"INACTIVE"` | Excluded from dispatchable; counted in total person count |
| Consent granted | `consent_status` = `"GRANTED"` | Channel is ready |
| Consent not granted | `consent_status` in {`PENDING`, `DENIED`, `UNKNOWN`} | Channel is blocked |

**Readiness eligibility**: An entity is eligible when ACTIVE AND has at least one usable channel. A channel is ready when consent is GRANTED.

**Readiness partition**: Count entities by their channel readiness status:
- `both` — email AND phone are both ready (both present and consent granted)
- `email_only` — only email is ready
- `phone_only` — only phone is ready
- `not_ready` — neither channel is ready (missing channels, non-granted consent, or quarantined)

**Depot rollup**: Group canonical people by `region` (the depot code). For each depot, the four disposition counts sum to `total_person_count`:
- `dispatchable_person_count` — active, consent granted, usable contact
- `blocked_consent_count` — active, usable contact, non-granted consent
- `blocked_no_contact_count` — no usable contact channel
- `blocked_inactive_count` — inactive with a usable channel

## Fuel Transactions

| Rule | Condition | Disposition |
|---|---|---|
| Invalid quantity | `quantity` <= 0 or null | Invalid — exclude from everything |
| Category mismatch | `expected_fuel_type` != canonical type resolved from `description` | Valid but flagged as mismatch |
| Unrecognized category | `description` resolves to 0 canonical fuel types | Quarantine |
| Ambiguous category | `description` resolves to 2 or more canonical fuel types | Quarantine |

Canonical fuel types (sorted ascending): `BIODIESEL`, `DIESEL`, `ELECTRIC_CHARGE`, `PREMIUM_UNLEADED`, `UNLEADED`.

**Volume normalization**: Convert `quantity` from `quantity_unit` to liters using `/api/reference/conversions`. Round summed totals to 2 decimal places.

**Exception**: A distinct logical transaction that has a category mismatch OR a quarantine condition.

## Maintenance Events

| Rule | Condition | Disposition |
|---|---|---|
| Missing timestamp | `timestamp` is null/empty | Invalid |
| Unparsable timestamp | `timestamp` cannot be parsed as ISO-8601 | Invalid |
| Invalid odometer | `odometer_km` is null, negative, or > 1,000,000 | Invalid |
| Negative labor | `labor_hours` < 0 | Invalid |
| Extreme labor | `labor_hours` > 100 | Invalid |
| Odometer regression | For a single asset, a later valid event has a lower `odometer_km` than an earlier valid event | Flagged in regression lists |

**Distance computation**: For each asset:
1. Keep only valid events (pass all non-regression rules above)
2. Sort by timestamp ascending
3. Set `current_max` = first event's odometer; `first_reading` = first event's odometer
4. For each subsequent event: if its odometer >= `current_max`, update `current_max` and accumulate the delta; if it regresses (odometer < `current_max`), skip it for distance and flag it as a regression event
5. Asset distance contribution = `current_max` - `first_reading`
6. `total_distance_km` = sum of asset contributions, rounded to 2 decimal places

**Asset risk ranking**: Sort by `rejected_event_count` DESC, then `regression_event_count` DESC, then `asset_id` ASC. Limit to the requested number.

## Freight Charges

| Rule | Condition | Disposition |
|---|---|---|
| Unrecognized alias | `description` resolves to 0 canonical service classes | Quarantine |
| Ambiguous alias | `description` resolves to 2 or more canonical service classes | Quarantine |
| Invalid weight | `billed_weight` <= 0 or null | Quarantine |
| Invalid distance | `distance` <= 0 or null | Quarantine |
| Class mismatch | `expected_service_class` != canonical class resolved from `description` | Valid but flagged as mismatch |

Canonical service classes (sorted ascending): `EXPRESS`, `HAZMAT`, `OVERSIZE`, `REFRIGERATED`, `STANDARD`.

**Physical normalization**: Convert `billed_weight` to KG and `distance` to KM using `/api/reference/conversions`. Convert `cost` to USD using `/api/reference/fx`. Round summed totals to 2 decimal places.

**Exception count per carrier**: Distinct retained charges for that carrier that are either a valid class mismatch or quarantined. A charge with both a mismatch and a quarantine counts once (quarantine takes priority).

## Field Service Roster

| Rule | Condition | Disposition |
|---|---|---|
| No usable contact | After deduplication, canonical person has no email AND no phone | Quarantine row |
| Inactive person | `canonical_record_status` = `"INACTIVE"` | Blocked from dispatchable |
| Consent not granted | `canonical_consent_status` != `"GRANTED"` | Blocked from dispatchable |

**Person deduplication**: Contact records from different source systems (HR Directory, Dispatch, Identity Registry) may represent the same person. Group by identity evidence (name, email, phone) and merge into canonical people. Within a multi-source cluster, resolve each canonical field by source precedence:
- **Name**: HR Directory > Dispatch > Identity Registry
- **Contact channels (email, phone)**: Identity Registry > Dispatch > HR Directory
- **Depot (region)**: HR Directory > Dispatch > Identity Registry
- **Consent**: Identity Registry > Dispatch > HR Directory

The `resolution_outcome` for focus people is:
- `SINGLE_SOURCE` — only one source row for this person
- `FIELD_LEVEL_PRECEDENCE_APPLIED` — multiple sources merged with precedence rules
- `CONTESTED_NO_AUTOMERGE` — identifier watchlist case that cannot be auto-resolved
- `NO_USABLE_CONTACT` — all rows for this person have no usable channel

## General rules for all domains

- Filter by business cutoff first: records with timestamps strictly after the cutoff are out of scope
- The authoritative snapshot's `row_count` (from `/api/source-snapshots`) should equal the total rows received from that snapshot minus any out-of-scope rows
- Sort all ID lists lexicographically ascending unless the answer template specifies a different ordering
- A single logical record matching multiple quarantine conditions still counts as exactly one quarantine
- `exception_count` = number of distinct logical records that are either quarantined OR have a category mismatch (each record counted at most once)
