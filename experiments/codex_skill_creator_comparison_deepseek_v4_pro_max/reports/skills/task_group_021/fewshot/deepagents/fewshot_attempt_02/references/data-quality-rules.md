# Data Quality Rules by Domain

## Contacts Collection (v_contacts)

### Logical Keys

The logical identity key is row_id. Rows with the same row_id in multiple snapshots are duplicates.

### Quarantine Rules

A row is quarantined (unusable) when it has no usable email AND no usable phone. An email is usable when it is non-empty, non-null, and contains an @ character. A phone is usable when it is non-empty and non-null.

### Duplicate Clustering (Person Resolution)

Rows that reference the same real person form a cluster. The canonical person is formed by merging fields across cluster members. Use master_hint to identify which clusters to inspect; it encodes the seed row. The cluster includes the seed and all rows whose person_or_org_name normalization matches and whose city/contact evidence overlaps.

### Canonical Values

- **Name**: Use the name from the most authoritative source system. Source precedence: HR Directory > Identity Registry > Dispatch > CRM > Compliance Master > Partner Portal > Dealer Portal.
- **Email and phone**: Use non-empty values from the most authoritative source that provides them.
- **City**: Use the city from the most authoritative source that provides a non-empty value.
- **Depot/region**: Use the region from the most authoritative source.
- **Consent status**: Use consent from the most authoritative source; map to GRANTED, PENDING, DENIED, or UNKNOWN. A source with GRANTED overrides PENDING across all cluster members.
- **Record status**: Use record_status from the most authoritative source; if any cluster member is INACTIVE and from the most authoritative sources, canonical is INACTIVE.
- **Survivor/master ID**: The row_id of the cluster member from the most authoritative source that has the most complete contact data.

### Contested Identifiers

When a watchlist anchor row falls within a cluster but identifier evidence (name/contact) from that anchor suggests a different person than the cluster canonical, the identifier case is contested. If the anchor resolves cleanly into the cluster, it is not contested.

### Readiness

An entity is readiness-eligible when it is ACTIVE and has at least one usable email or phone. An entity is dispatchable when it is readiness-eligible AND its consent status is GRANTED. Channel-readiness partitions count by channels present: email+phone = both, email only, phone only, neither = not_ready.

## Fuel Transactions (v_fuel_transactions)

### Logical Keys

The logical key is transaction_id. Rows with the same transaction_id in multiple snapshots are duplicates; retain the authoritative-snapshot row.

### Category Recognition

Match purchased_description against reference aliases (domain=fuel):
- Normalize the description to lowercase, strip leading/trailing whitespace.
- Find all alias rows where alias_text (lowercased, stripped) equals the normalized description AND reference_status=ACTIVE.
- If zero matches: unrecognized.
- If one match: recognized as canonical_value.
- If multiple matches with different canonical values: ambiguous (unrecognized).

### Mismatch Detection

A mismatch occurs when the recognized canonical_value differs from expected_fuel_type.

### Quarantine Rules

Quarantine a transaction when:
- Its description is unrecognized (zero-match or ambiguous).
- Its quantity is nonpositive (null, zero, or negative).

### Normalization

- Convert quantity * quantity_unit to liters (L) using conversion factors from /api/reference/conversions?kind=volume.
- Convert amount * currency to USD using CERTIFIED FX rates for the purchased_at date.
- Use round(value, 2) for all normalized totals.

### Valid Transaction

A valid transaction is one that is NOT quarantined. Valid transactions enter normalized totals. Valid mismatches also enter normalized totals.

## Freight Charges (v_freight_charges)

### Logical Keys

The logical key is charge_id. Rows with the same charge_id in multiple snapshots are duplicates; retain the authoritative-snapshot row.

### Class Recognition

Match description against reference aliases (domain=service_class):
- Normalize the description to lowercase, strip whitespace.
- Find all alias rows where alias_text (lowercased, stripped) equals the normalized description AND reference_status=ACTIVE.
- If zero matches: unrecognized (cannot enter accrual).
- If one match: recognized as canonical_value.
- If multiple matches with different canonical values: ambiguous (unrecognized).

### Mismatch Detection

A mismatch occurs when the recognized canonical_value differs from expected_service_class.

### Quarantine Rules

Quarantine a charge when:
- Its description has an unrecognized alias.
- Its billed_weight is nonpositive (null, zero, or negative).
- Its distance is nonpositive (null, zero, or negative).

### Normalization

- Convert billed_weight * weight_unit to KG using /api/reference/conversions?kind=weight.
- Convert distance * distance_unit to KM using /api/reference/conversions?kind=distance.
- Convert amount * currency to USD using CERTIFIED FX rates for service_date.
- Use round(value, 2) for all normalized totals.

### Valid Charge

A valid charge is one that is NOT quarantined. Valid charges enter normalized totals. Valid class mismatches DO enter normalized totals.

## Maintenance Events (v_maintenance_events)

### Logical Keys

The logical key is event_id. Duplicate resolution retains the authoritative-snapshot row.

### Rejection Rules

An event is rejected (invalid) when ANY of these hold:
- event_time_raw is null, empty, or unparsable as a datetime.
- event_time_raw parses but the time is outside the business period defined in the case scope.
- odometer_value is null, zero, or negative.
- labor_hours is negative.
- labor_hours is extreme (> 100).

### Odometer Regression

For each asset, sort valid events by event_time_raw ascending. An odometer regression is detected when a later odometer_value is strictly less than an earlier value. A regression event is valid (not rejected) but flagged. Record both the regression event IDs and the affected asset IDs.

### Corrected Distance

For each asset, compute distance traveled as: last valid odometer reading minus first valid odometer reading, across valid events in the business period. Sum across all assets.

### Invalid Event IDs

The full list of rejected event IDs excludes regression-only events. Regression events go in regression_event_ids.
