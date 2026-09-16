# Quarantine Rules by Domain

Quarantined records are excluded from normalized totals and readiness counts
but remain in raw-row counts and audit summaries. Each domain has its own
quarantine conditions.

## Contacts (partner onboarding, field-service roster)

A contact row is quarantined when:
- `email` is null, empty, or contains only whitespace, AND
- `phone` is null, empty, or contains only whitespace / non-digits

Quarantined contacts do not count toward `readiness_eligible_entity_count`.
They do count toward `canonical_entity_count`.

An active person with a usable channel but `consent_status` != GRANTED is
NOT quarantined — they are blocked for readiness dispatch but remain an
eligible canonical entity.

## Fuel transactions

A fuel transaction is quarantined when:
- `quantity_liters` is null, zero, or negative (invalid quantity), OR
- The transaction description is unrecognized (zero canonical fuel category
  matches via alias mapping), OR
- The transaction description is ambiguous (matches more than one canonical
  fuel category)

Quarantined transactions do not contribute to `normalized_totals` (volume or
spend). They are counted in `invalid_quantity_count` and `unrecognized_count`
or `ambiguous_count`.

## Maintenance events

A maintenance event is rejected (quarantined) when:
- `timestamp` is missing, null, or unparsable as a datetime
- `timestamp` is outside the business period (before start or after end)
- `odometer_end` <= `odometer_start` (invalid range)
- `labor_hours` is negative
- `labor_hours` exceeds a reasonable threshold (extreme labor)

Rejected events appear in `rejected_event_ids` (maintenance) or
`invalid_event_ids`. They are excluded from `corrected_metrics`.

**Important**: Odometer regressions (odometer_end for an event is less than
the previous event's odometer_end on the same asset, when events are sorted
by timestamp) are NOT quarantined. Regression events remain in the valid
history and their distance is recorded as zero in `total_distance_km`. The
event IDs and asset IDs are reported in `regression_event_ids` and
`regression_asset_ids`.

## Freight charges

A freight charge is quarantined when:
- `weight_kg` is null, zero, or negative (invalid weight), OR
- `distance_km` is null, zero, or negative (invalid distance), OR
- The service description maps to zero recognized service classes via alias
  matching (unrecognized_alias), OR
- The service description maps to more than one recognized service class
  (ambiguous_alias)

Quarantine reasons are counted separately in `quarantine_reason_counts`.
Quarantined charges are excluded from `normalized_totals`.

## General principle

When in doubt about whether a record should be quarantined, ask: "Can this
record be used for the task's primary purpose?" If the answer is no because
the record lacks usable data in a key field, quarantine it. If the data is
usable but merely flagged (mismatch, regression, consent issue), it stays in
the working set and is reported separately.
