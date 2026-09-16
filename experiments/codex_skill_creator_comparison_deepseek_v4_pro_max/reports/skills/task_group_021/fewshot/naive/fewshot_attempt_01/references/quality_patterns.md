# Data Quality Patterns

This reference covers the data-quality classification rules, quarantine
conditions, computation formulas, and reconciliation patterns observed across
all Asteria Fleet Data Quality Hub task domains.

## Quarantine Conditions

A record is **quarantined** (excluded from normalized totals but counted in
quality summaries) when it meets any of the following conditions. Each record
is quarantined for exactly one reason; check reasons in the order listed.

### Contact Records

| Condition | Detection | Effect |
|---|---|---|
| No usable contact | After canonical resolution, `canonical_email` is null/empty/not containing `@` AND `canonical_phone_digits` is null/empty. | Row ID added to `quarantine_row_ids`; excluded from readiness. |

### Fuel Transactions

| Condition | Detection | Effect |
|---|---|---|
| Unrecognized description | `description` maps to zero entries in the aliases table. | Excluded from normalized totals; counted in `unrecognized_count`. |
| Ambiguous description | `description` maps to more than one entry in the aliases table. | Excluded from normalized totals; counted in `ambiguous_count`. |
| Invalid quantity | `quantity` is null, zero, or negative. | Excluded from normalized totals; counted in `invalid_quantity_count`. |

The total unrecognized category count is `unrecognized_count + ambiguous_count`.

### Freight Charges

| Condition | Detection | Effect |
|---|---|---|
| Unrecognized alias | `service_alias` maps to zero entries in the aliases table. | Excluded from normalized totals; counted in `quarantine_reason_counts.unrecognized_alias`. |
| Ambiguous alias | `service_alias` maps to more than one entry in the aliases table. | Excluded from normalized totals; counted in `quarantine_reason_counts.ambiguous_alias`. |
| Invalid weight | `billed_weight_kg` is null, zero, or negative. | Excluded from normalized totals; counted in `quarantine_reason_counts.invalid_weight`. |
| Invalid distance | `distance_km` is null, zero, or negative. | Excluded from normalized totals; counted in `quarantine_reason_counts.invalid_distance`. |

### Maintenance Events

| Condition | Detection | Effect |
|---|---|---|
| Missing timestamp | `event_timestamp` is null. | Added to `invalid_event_ids`; excluded from `valid_event_count` and corrected metrics. |
| Invalid timestamp | `event_timestamp` cannot be parsed or falls outside the business period. | Added to `invalid_event_ids`; excluded from valid metrics. |
| Invalid odometer | `odometer_reading` is null, negative, or exceeds a reasonable bound. | Added to `invalid_event_ids`; excluded from valid metrics. |
| Negative labor | `labor_hours` is strictly negative. | Added to `invalid_event_ids`; excluded from valid metrics. |
| Extreme labor | `labor_hours` exceeds 24. | Added to `invalid_event_ids`; excluded from valid metrics. |
| Odometer regression | For a given asset ordered by timestamp, a valid event has a strictly lower odometer reading than the preceding valid event. | NOT added to invalid_event_ids; still in valid_event_count; odometer values excluded from min/max for distance; reported in `regression_event_ids`. |

## Category and Class Mismatches

A **mismatch** is not a quarantine. It is a valid record whose recognized
category/class (from alias resolution) differs from the expected
category/class. Mismatched records:

- Are included in normalized totals.
- Are listed in `mismatch_transaction_ids` / `class_mismatch_charge_ids`.
- Count toward `exception_transaction_count` / `exception_count`.

## Exception Counting

An **exception** is a retained logical record that is EITHER a mismatch OR
quarantined. A record cannot be counted as both a mismatch and a quarantine
for exception purposes; it contributes once. For rankings, report separate
`mismatch_count` and `quarantine_count` components, with `exception_count`
being their sum.

## Entity Resolution

### Multi-Source Merge (Contact/Roster)

When the same real-world person appears in multiple source-system rows:

1. Group rows by deterministic identifier matching (shared ID, or
   name+email/name+phone equivalence after normalization).
2. For each group, select canonical values using the field-level precedence
   table in the main skill.
3. The survivor (master) row is the highest-precedence source-system row.
   Break ties by lowest lexicographic row ID.
4. Report all member row IDs in `member_row_ids`, sorted lexicographically.

### Cross-Snapshot Deduplication (Transaction/Event)

When an entity ID appears in both certified and provisional snapshots:

1. Retain the certified occurrence.
2. Discard the provisional occurrence and increment `duplicate_raw_count`.
3. Report the duplicate group in the answer.

## Computation Formulas

### Contact Quality Summary

```
raw_row_count = total rows in collection at cutoff
canonical_entity_count = distinct resolved entities (people/contacts)
duplicate_cluster_count = multi-row clusters (size >= 2)
readiness_eligible_entity_count = canonical entities that are active with
  at least one usable channel
quarantine_rate = quarantine_row_count / canonical_entity_count
  (rounded to 4 decimal places)
```

### Fuel Audit Summary

```
raw_row_count = total rows across all snapshots
logical_transaction_count = distinct transaction IDs across all snapshots
duplicate_raw_count = raw_row_count - logical_transaction_count
valid_transaction_count = logical count minus quarantine count
mismatch_count = valid transactions with expected != recognized category
unrecognized_count = transactions with zero alias matches
ambiguous_count = transactions with multiple alias matches
invalid_quantity_count = transactions with invalid quantity
exception_transaction_count = distinct transactions that are mismatched OR
  quarantined
```

### Freight Audit Summary

```
raw_row_count = total rows across all snapshots
logical_charge_count = distinct charge IDs across all snapshots
duplicate_raw_count = raw_row_count - logical_charge_count
valid_charge_count = logical count minus quarantine count
mismatch_count = valid charges with expected != recognized class
quarantine_count = sum of the four quarantine reason counts
```

### Maintenance Corrected Distance

```
For each asset:
  valid_events = events for asset sorted by timestamp ASC, excluding
    invalid events
  first_reliable = first event in valid_events whose odometer passes all
    checks (non-null, non-negative, not a regression)
  last_reliable = last event in valid_events whose odometer passes all
    checks
  asset_distance = last_reliable.odometer - first_reliable.odometer

total_distance_km = sum(asset_distance for all assets)
```

## Ordering Rules

All arrays in the answer follow these conventions unless the answer template
or case scope specifies otherwise:

- Lists of IDs: lexicographic ascending.
- Lists of objects: sorted by the primary key field ascending, with
  tie-breakers as declared.
- Rankings: sorted by the primary metric descending, with enumerated
  tie-breakers applying in order.

## Numeric Precision

- All counts are exact integers.
- Monetary values: rounded to 2 decimal places.
- Volume/weight/distance: rounded to 2 decimal places.
- Quarantine rate: rounded to 4 decimal places (contact tasks only).
- Use standard rounding (round half up).
