# Output contract — counts, ordering, status, and self-check

The `answer_template.json` is authoritative. It comes in two shapes:

- **JSON Schema** (draft 2020-12): honor `required`, `additionalProperties:
  false`, `enum`, `minItems`/`maxItems`, `uniqueItems`, `pattern`, and numeric
  `multipleOf`/`minimum`/`maximum`.
- **Custom `field_contract`**: honor `required_top_level_keys`,
  `additional_top_level_keys_allowed: false`, per-field `type`/`length`/
  `ordering`/`allowed_values`, and any stated `count_partition_rule` /
  `numeric_precision`.

Match whichever is present exactly. Never add keys, never omit required keys.

## Count definitions (keep these consistent)

- `raw_row_count` / `scoped_raw_row_count` — in-scope raw rows fed into
  reconciliation (post cutoff filter), before dedup.
- `logical_* / canonical_entity_count / canonical_person_count` — distinct
  logical records/entities after dedup; **includes** quarantined entities unless
  the field description says otherwise.
- `duplicate_raw_count = raw − logical`; `duplicate_cluster_count` /
  `merged_duplicate_cluster_count` = number of clusters/ids with ≥2 raw members.
- `valid_* ` — logical records that passed integrity checks (mismatches count as
  valid).
- `quarantine_count` — logical records excluded as unusable.
- `readiness_eligible_entity_count` — active entities with ≥1 usable channel.
- Rollups (region/depot, fuel_type/service_class): emit **one row per
  represented / enumerated value**, including zero-count rows when the contract
  fixes the array length to the full enum.

## Ordering & uniqueness

- Plain id lists: **deduplicate** and sort **lexicographically ascending**
  unless told otherwise.
- Object arrays: sort by the key the contract names (e.g. `cluster_id` /
  `event_id` / `charge_id` / `asset_id` / `depot_code` ascending).
- Nested lists (e.g. `member_row_ids`, `snapshot_ids`) also deduped + sorted.
- **Rankings**: apply the case-scope primary sort (usually a metric
  **descending**), then each tie-break in order (commonly the id **ascending**),
  then truncate to the limit. Populate `rank` starting at 1 when the contract has
  a rank field.
- Report focus/anchor/control panels in the exact order the contract states
  (usually ascending by the focus/case id), one entry per requested item — no
  more, no fewer.

## Numeric precision

- Round only at the end, to the stated decimals (totals typically 2 dp;
  `quarantine_rate` typically 4 dp). Honor `multipleOf` (e.g. `0.01`, `0.0001`).
- Keep phone as a **digits-only string**, not a number.
- Where the contract says all counts are integers, emit no floats there.

## Status / action decision

1. **Compute the gate metric.** Usually
   `quarantine_rate = quarantine_count / canonical_entity_count`, rounded to the
   contract's decimals.
2. **Apply `status_thresholds` from the case scope**:
   - `quarantine_rate ≤ pass_max_quarantine_rate` → `PASS`
   - `≤ pass_with_exceptions_max_quarantine_rate` → `PASS_WITH_EXCEPTIONS`
   - otherwise → `HOLD`
3. **Hard gates override.** If the case scope declares a gate (e.g. a
   `certification_gate` firing on any odometer regression), and its condition
   holds, force the gate's status/action regardless of the rate.
4. **When no thresholds are supplied** (some transaction/close tasks): derive
   status from exception presence/severity — no exceptions → `PASS`; exceptions
   present but non-blocking → `PASS_WITH_EXCEPTIONS`; blocking integrity failure →
   `HOLD`. Follow any wording in `prompt.txt`.
5. **Map status → action** via the case scope's `status_action_map` if present,
   else the standard mapping:
   - `PASS` → `RELEASE`
   - `PASS_WITH_EXCEPTIONS` → `REVIEW_EXCEPTIONS`
   - `HOLD` → `BLOCK_AND_REMEDIATE`

   (The action key may be named `action`, `next_action`, or `routing` — use the
   contract's name.)

## Pre-submit checklist

- [ ] Output is a single JSON object — **no** Markdown, prose, or code fences.
- [ ] Every required top-level key present; no extra keys anywhere
      (`additionalProperties:false` / `additional_top_level_keys_allowed:false`).
- [ ] Every enum value (statuses, actions, source systems, categories, and every
      control code) is drawn from the current template's enum.
- [ ] Fixed-length arrays match exactly (`minItems`/`maxItems`, `length`); one
      entry per requested focus/anchor/control case and per enumerated rollup
      value.
- [ ] All lists deduped and sorted per the ordering rules; rankings sorted +
      tie-broken + truncated to the limit; `rank` starts at 1.
- [ ] Counts are internally consistent: `raw = logical + duplicate_raw`;
      partitions sum to their totals; quarantined rows are excluded from
      normalized totals but included in `canonical_entity_count`.
- [ ] Numbers rounded to the stated precision; phones are digit strings; emails
      normalized (NFKC, trimmed, lowercase).
- [ ] `quarantine_rate` recomputed and thresholds/gates applied; status→action
      consistent with the map.
- [ ] All IDs are real stable IDs from the hub or the case scope — none invented.
