# Maintenance History Rules

Use these rules for maintenance-event integrity, odometer history, and reliability-history tasks.

## Retention and Scope

Fetch all maintenance rows for the scoped collection, then group by `event_id`. Retain one row per event id using snapshot status precedence. Report all cross-snapshot duplicates when the template asks for duplicate groups.

Use source snapshot metadata for:

- authoritative snapshot id
- snapshot status
- authoritative row count
- scoped raw row count

## Event Validity

Classify retained events before building corrected metrics.

Reject an event into invalid-event outputs when any of these hold:

- `event_time_raw` is missing, empty, unparsable, or outside the business period when the scope provides one.
- `odometer_value` is missing, nonnumeric, or nonpositive after unit handling.
- `odometer_unit` cannot be converted to the requested distance unit.
- `labor_hours` is missing, nonnumeric, negative, or extreme. Use a practical operations cap such as more than 24 hours unless the task or schema gives another threshold.

Count issue types separately. One event can contribute to multiple issue counts, but invalid event id arrays are unique and sorted.

## Odometer Regression

Sequence-only odometer regressions are not ordinary invalid-event ids. After removing rejected events, sort retained events per asset by event time, then event id. Convert odometer readings to kilometers or the requested canonical distance unit. If a reading decreases from the previous reliable reading for that asset, mark that event as a regression:

- add its event id to regression outputs
- add the asset id to regression asset outputs
- increment odometer regression issue count
- route it with the regression history code when requested
- exclude it from corrected valid-event count and reliable-distance calculations

For corrected distance, use reliable retained events only. For each asset, subtract the first reliable odometer from the last reliable odometer, then sum across assets. Round the final total as the template requires.

## Rankings and Decisions

Asset risk rankings usually combine rejected invalid events and regression events. Follow the case-scope sort keys exactly; common ordering is rejected count descending, regression count descending, then asset id ascending. Assign explicit `rank` values after sorting.

Certification status comes from the task's gate. If the scope states that any odometer regression causes a hold, apply the stated status and action when regressions exist.

Use `references/codes.md` for maintenance source and history route code panels.
