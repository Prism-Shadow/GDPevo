# Data Quality Rules by Domain

## Contacts (Partner Onboarding, Field Service Roster)

### Source Systems
Contacts originate from three source systems: `HR Directory`, `Dispatch`, `Identity Registry`. Every row carries a `source_system` field.

### Identity Clustering
The `person_identity_key` field (or equivalent UID) is the cluster key. All rows sharing the same identity key represent the same person. The cluster membership determines the `member_row_ids` list.

### Quarantine
A row is quarantined when it has **no usable email AND no usable phone**.
- Usable email: non-empty string containing `@`.
- Usable phone: non-empty string, after stripping all non-digit characters, has length at least 7.

Quarantined rows are excluded from the dispatchable population but still count toward `canonical_person_count` and `raw_row_count`.

### Survivor Selection
Within a cluster, the survivor is the row with the lexicographically highest `row_id`.

### Canonical Values (Field-Level Precedence)
For multi-source merged clusters, resolve each canonical field from the source that has it, using this precedence:

| Field | Precedence (highest first) |
|-------|---------------------------|
| `canonical_name` | HR Directory → Dispatch → Identity Registry |
| `canonical_email`, `canonical_phone_digits` | Identity Registry → Dispatch → HR Directory |
| `depot_code` (region) | HR Directory → Dispatch → Identity Registry |
| `canonical_consent_status` | Identity Registry → Dispatch → HR Directory |
| `canonical_city` | Compliance Master (if present) → HR Directory → Dispatch |

For a given field, pick the value from the first source in the precedence chain that has a non-null, non-empty value for that row in the cluster. If no source in the chain has the field, the canonical value is empty/null.

### Canonical Phone
Strip all non-digit characters from the selected phone value. The result is the `canonical_phone_digits` string.

### Canonical Email
Trim whitespace and normalize to NFKC lowercase.

### Channel Readiness
- **Readiness-eligible entity**: an active person (canonical `record_status` is `ACTIVE`) who has at least one usable email or phone.
- **Channel ready**: the entity's consent status is `GRANTED`.
  - `both`: consent granted AND entity has both usable email and phone.
  - `email_only`: consent granted AND entity has usable email but no usable phone.
  - `phone_only`: consent granted AND entity has usable phone but no usable email.
  - `not_ready`: consent is not `GRANTED` (PENDING, DENIED, UNKNOWN), OR entity is inactive, OR entity has no usable contact.
- **Readiness partition**: `both` + `email_only` + `phone_only` are the channel-ready counts. `not_ready` includes all remaining readiness-eligible entities.

### Contested Identifiers
An identifier watchlist case is "contested" when the anchor row and its identity cluster members disagree on the identifier in question (e.g., the email or phone differs across cluster members). If all rows in the cluster agree, the case is not contested.

### Depot Breakdown
Group canonical persons by their `depot_code` (canonical region). For each depot, count:
- `total_person_count`: all canonical people in that depot.
- `dispatchable_person_count`: people who are ready (active, has contact, consent GRANTED).
- `blocked_consent_count`: active, has contact, consent is not GRANTED.
- `blocked_no_contact_count`: active, no usable contact.
- `blocked_inactive_count`: inactive, has usable contact.

The four disposition counts sum to `total_person_count`.

---

## Fuel Transactions

### Category Recognition
Each fuel transaction has a `description` field (free text) and an `expected_fuel_type` field (the category the submitting system believes the transaction belongs to).

Match `description` against `/api/reference/aliases`. For each alias where `canonical_category` is one of the five fuel types, check whether the `description` contains the `alias_text` (case-insensitive substring match). The recognized fuel type is the `canonical_category` of the matching alias.

- **Recognized**: exactly one alias matches → assign that alias's `canonical_category`.
- **Unrecognized (zero-match)**: no alias matches → the transaction has no recognized category.
- **Ambiguous**: multiple aliases match AND they resolve to more than one distinct `canonical_category`.
- **Mismatch**: recognized category differs from `expected_fuel_type`.

### Invalid Quantity
A transaction has an invalid quantity when its `volume` is null, zero, or negative.

### Quarantine
Transactions are quarantined for:
- Unrecognized description (zero-match OR ambiguous)
- Invalid quantity

Quarantined transactions do not enter normalized totals. They still count toward `raw_row_count` and `logical_transaction_count`.

### Normalization
1. Convert volume to liters (L) using `/api/reference/conversions` (from `volume_unit` to `L`).
2. Convert spend to USD using `/api/reference/fx` (from `spend_currency` to `USD`).

Valid (non-quarantined) transactions contribute to normalized totals.

### Merchant Exception Ranking
A merchant exception is a logical transaction that has either a category mismatch or a quarantine condition. Count `exception_count`, `mismatch_count`, and `quarantine_count` per merchant. Rank by `exception_count` descending, then `merchant_id` ascending.

---

## Freight Charges

### Service Class Recognition
Each freight charge has a `description` field and an `expected_service_class` field.

Match `description` against `/api/reference/aliases`. For each alias where `canonical_category` is one of the five service classes (`EXPRESS`, `HAZMAT`, `OVERSIZE`, `REFRIGERATED`, `STANDARD`), check whether the `description` contains the `alias_text` (case-insensitive substring match).

- **Recognized**: exactly one alias matches → assign that alias's `canonical_category`.
- **Unrecognized (zero-match)**: no alias matches.
- **Ambiguous**: multiple aliases match AND resolve to more than one distinct service class.
- **Mismatch**: recognized category differs from `expected_service_class`.

### Quarantine
A charge is quarantined for:
- Unrecognized alias (zero-match)
- Ambiguous alias
- Invalid distance: `distance` is null, zero, or negative
- Invalid weight: `billed_weight` is null, zero, or negative

Quarantined charges do not enter normalized totals.

### Quarantine Reason Counts
Count quarantines by reason:
- `unrecognized_alias`: no matching alias
- `ambiguous_alias`: multiple distinct canonical categories
- `invalid_distance`: non-positive distance
- `invalid_weight`: non-positive weight

A charge may have multiple quarantine reasons. Count each distinct reason once per charge. The sum of reason counts may exceed `quarantine_count`.

### Normalization
1. Convert billed weight to KG using `/api/reference/conversions` (from `weight_unit` to `KG`).
2. Convert distance to KM using `/api/reference/conversions` (from `distance_unit` to `KM`).
3. Convert spend to USD using `/api/reference/fx` (from `spend_currency` to `USD`).

### Carrier Ranking
Accrual exposure is the normalized USD spend on valid charges whose recognized service class differs from the expected class. Rank carriers by `mismatch_spend_usd` descending, then `carrier_id` ascending. Report `mismatch_count`, `mismatch_spend_usd`, `quarantine_count`, and `exception_count` (mismatch + quarantine) per carrier.

---

## Maintenance Events

### Duplicate Resolution
A logical event (`logical_event_id`) may appear in multiple snapshots. Retain the certified occurrence. The `retained_event_id` is the specific raw `event_id` from the retained snapshot.

For duplicate groups: report the `logical_event_id`, the set of `snapshot_ids` that contain it, and the `retained_snapshot_id`. Sort by `logical_event_id` ascending, `snapshot_ids` lexicographically ascending.

### Invalid Events
An event is invalid (rejected) for any of:
- **Missing timestamp**: `event_timestamp` is null or empty.
- **Invalid timestamp**: `event_timestamp` is unparsable as a ISO-8601 datetime.
- **Invalid odometer**: `odometer_reading` is null, negative, or exceeds an implausible upper bound.
- **Negative labor**: `labor_hours` is negative.
- **Extreme labor**: `labor_hours` exceeds an implausible upper bound.

Invalid events are fully excluded from the corrected history. Count each issue type separately; a single event may contribute to multiple counts.

### Odometer Regression
After sorting a single asset's valid events by `event_timestamp` ascending, check: for each consecutive pair, if the later event's `odometer_reading` is strictly less than the earlier event's, the later event is flagged as a regression.

Regression events stay in the history for `valid_event_count` but their odometer reading is excluded from `total_distance_km`.

### Corrected Metrics
- `valid_event_count`: total retained events minus fully invalid events. Regression events are still counted.
- `total_distance_km`: sum across all assets of (`last_reliable_odometer` - `first_reliable_odometer`). For each asset, take the chronologically first and last valid events that are NOT regressions. Only assets with at least two non-regression valid events contribute.
- `regression_asset_ids`: unique asset IDs that have at least one regression event, sorted lexicographically.
- `regression_event_ids`: unique event IDs flagged as regressions, sorted lexicographically.

### Asset Risk Ranking
For each asset, count:
- `rejected_event_count`: number of events fully rejected (invalid).
- `regression_event_count`: number of regression events.

Rank by `rejected_event_count` DESC, then `regression_event_count` DESC, then `asset_id` ASC. Report top 5.
