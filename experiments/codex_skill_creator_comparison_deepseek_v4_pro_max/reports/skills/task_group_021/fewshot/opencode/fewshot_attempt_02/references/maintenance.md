# Maintenance events reference

## Relevant logical view

`v_maintenance_events` — fields: `collection_id`, `snapshot_id`, `event_id`, `work_order_id`, `asset_id`, `event_type`, `event_time_raw`, `odometer_value`, `odometer_unit`, `labor_hours`, `parts_cost`, `currency`, `technician_id`, `event_status`, `business_updated_at`, `ingested_at`.

## Snapshot resolution

Maintenance events typically appear across two snapshots: a CERTIFIED snapshot and a PROVISIONAL snapshot. The CERTIFIED snapshot is authoritative. Use its `business_cutoff` as the effective as-of date.

When the same `event_id` appears in both snapshots, retain the CERTIFIED occurrence. Report all such cross-snapshot duplicate groups sorted by `event_id` ascending.

If the task scope says "ALL_COLLECTION_ROWS" or equivalent, all snapshot rows are in scope for duplicate detection but only CERTIFIED row values enter the reconciled dataset.

## Data validation rules

Validate every event row (from all snapshots) against these rules:

### Timestamp validation
- `event_time_raw` is **missing/null/empty** → `missing_timestamp` count incremented
- `event_time_raw` is present but cannot be parsed as an ISO-8601 datetime → `invalid_timestamp` count incremented
- If missing or invalid, the event is **rejected** (goes to `invalid_event_ids`)

### Odometer validation
- `odometer_value` is null, negative, or beyond a reasonable maximum (treat > 999,999 as invalid) → `invalid_odometer` count incremented
- If invalid odometer, the event is **rejected** (goes to `invalid_event_ids`)
- `odometer_unit` must be either `mi` or `km`. Convert mi to km using the distance conversion factor from the reference data.

### Labor hours validation
- `labor_hours` is negative → `negative_labor` count incremented; event rejected
- `labor_hours` exceeds a reasonable maximum (> 100 hours for a single event) → `extreme_labor` count incremented; event rejected

## Odometer regression detection

After rejecting invalid events and deduplicating snapshots, for each asset:
1. Sort retained valid events by `event_time_raw` ascending.
2. Compare consecutive `odometer_value` (in km) readings.
3. If a later event has a lower odometer reading than an earlier event for the same asset, flag it as a regression.

Regressions are reported separately:
- `regression_asset_ids` — unique assets with at least one regression, sorted lexicographically
- `regression_event_ids` — unique events that are regression endpoints (the later event in a regression pair), sorted lexicographically

Regressed events are **not rejected** — they remain in the valid set (unlike invalid timestamp/odometer/labor events). But regression is a certification gate.

## Corrected distance metric

`total_distance_km` = sum across assets of (`last_reliable_odometer_km` - `first_reliable_odometer_km`), where "reliable" means the event was not rejected for missing/invalid timestamp, invalid odometer, or invalid labor. Only valid (non-rejected, deduplicated) events contribute. Round to 2 decimal places.

`valid_event_count` = number of non-rejected, deduplicated events in scope.

## Asset risk ranking

Rank assets by:
1. `rejected_event_count` descending (events rejected for that asset across all snapshots)
2. `regression_event_count` descending (tie-break)
3. `asset_id` ascending (final tie-break)

Take the top `limit` (typically 5). Rank starts at 1.

## Certification gate

If `odometer_regression > 0`, the certification status is `HOLD` with action `BLOCK_AND_REMEDIATE` regardless of other metrics. This is a hard gate that overrides rate thresholds.

## Control code assignment for maintenance

See [control-codes.md](control-codes.md). Assign MS and HR codes per scoped event IDs:
- **MS codes**: based on which source system the event originated from and the snapshot_status of its source
- **HR codes**: based on whether the event is in the certified or provisional snapshot, and whether it was rejected, regressed, or clean
