# Quarantine Rules by Collection Family

## Contacts / Roster Family

An entity is **quarantined** when it has no usable email AND no usable phone across all its source rows.

### Null Detection
Treat the following as absent (not usable):
- `None`, `none`, `NULL`, `null` (string literals)
- `N/A`, `n/a`, `NA`
- Empty string `""`
- Whitespace-only `   `

### Usable Channel
- **Email**: after NFKC normalisation, lowercase, trim — must be non-empty
- **Phone**: after extracting digits only — must have at least some digits

### Quarantine Rate
`quarantine_rate = quarantined_entity_count / canonical_entity_count` (rounded to 4 decimal places)

### Readiness Eligibility
An entity is readiness-eligible if it is ACTIVE and has at least one usable channel.

### Channel Readiness Partitions (among eligible entities only)
- **both**: usable email + usable phone AND consent = GRANTED
- **email_only**: usable email only AND consent = GRANTED
- **phone_only**: usable phone only AND consent = GRANTED
- **not_ready**: eligible but consent ≠ GRANTED

## Fuel / Freight Transaction Family

A transaction/charge is **quarantined** if ANY of:
1. Its description matches **zero** reference aliases (unrecognized)
2. Its description matches **more than one** distinct canonical value (ambiguous)
3. Its quantity/weight/distance is ≤ 0 (invalid physical measure)

A transaction whose recognised category **differs from expected** is a **mismatch** — it is NOT quarantined and still enters normalized totals.

### Quarantine Reason Counting (freight only)
- `ambiguous_alias`: matched >1 canonical service class
- `unrecognized_alias`: matched 0 aliases
- `invalid_weight`: billed_weight ≤ 0
- `invalid_distance`: distance ≤ 0

## Maintenance Event Family

An event is **invalid** if ANY of:
1. Missing or unparseable timestamp (`event_time_raw`)
2. Negative odometer value
3. Negative labor hours
4. Extreme labor hours (> 1000 threshold)

**Odometer regression** is tracked separately: when a later event (by timestamp) for the same asset has a lower odometer reading than an earlier event. Regression events are reported in `corrected_metrics.regression_event_ids` and `corrected_metrics.regression_asset_ids`, NOT in `invalid_event_ids`.

### Corrected Distance Metric
Sum across assets of (last reliable odometer reading − first reliable odometer reading), in km, rounded to 2 decimal places. Only use events that are NOT in `invalid_event_ids`.

## Certification Decision

Apply thresholds from `case_scope.json`:
- `pass_max_quarantine_rate`: if quarantine_rate ≤ this → PASS
- `pass_with_exceptions_max_quarantine_rate`: if ≤ this → PASS_WITH_EXCEPTIONS
- Otherwise → HOLD

Map status through `status_action_map`:
- PASS → RELEASE
- PASS_WITH_EXCEPTIONS → REVIEW_EXCEPTIONS
- HOLD → BLOCK_AND_REMEDIATE

For maintenance: check `certification_gate` — if odometer regressions exist, use the regression-specific status/action.
