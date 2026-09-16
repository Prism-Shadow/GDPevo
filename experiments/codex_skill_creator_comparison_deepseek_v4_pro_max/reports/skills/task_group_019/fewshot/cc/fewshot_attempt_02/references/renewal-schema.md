# Alcohol Renewal Queue Reference

## Join Keys

| Record type | Join field | Notes |
|-------------|-----------|-------|
| licensees | `license_no` | Primary key; also has `location_id`, `address`, `facility_name`, `successor_to` |
| violations | `license_no` | Multiple violations per license; join on exact `license_no` match |
| renewal/rules | (global) | The active rule defines the boundary date |

There is no direct foreign key between violations and licensees beyond
`license_no`. Some violations reference a different (older) `license_no` for
successor/predecessor relationships — these require address-based fuzzy
matching (see below).

## Rule Selection

Read the renewal/rules endpoint. Identify the active rule by matching the
boundary date from the prompt with the rule's `release_boundary` field.
The prompt states the release boundary explicitly (e.g., "2025-04-10").

The active rule's `details_json` (parse as JSON) contains:
- `use_violations_on_or_before`: the boundary date string (matches
  `release_boundary`)
- `alert_flag_requires_manual_review`: true — only violations with
  `alert_flag` = 1 matter for the queue
- `late_rows_are_distractors`: true — violations from
  `post_boundary_feed` source are excluded from queue scoring
- `unpaid_fines_require_hold`: true — unpaid fines contribute to risk

## Boundary Filtering

The boundary date from the prompt (e.g., "2025-04-10") is the dividing line:

1. **Include**: Violations with `violation_date` on or before the boundary
   date. These count toward `violation_count` and determine rank.
2. **Exclude**: Violations with `violation_date` after the boundary date.
   These go in the summary's `post_boundary_violation_ids_excluded` list.
3. **Source-based exclusion**: Even if a violation's date is before the
   boundary, if its `source_name` is `post_boundary_feed`, exclude it
   from queue scoring (it is a distractor).

## License-to-Violation Matching

Match violations to licenses in three confidence tiers:

### Exact match (confidence: `exact`)
- `violations[].license_no` exactly equals `licensees[].license_no`
- Most common and reliable match type

### Close address match (confidence: `close_address`)
- `violations[].license_no` does NOT exactly equal any target
  `licensees[].license_no`
- But `violations[].address` closely matches a licensee's `address`
  (same street number and street name, or same building name, ignoring
  minor formatting differences like "Ave" vs "Avenue")
- AND the facility names are recognizably the same entity
- Common for successor licenses where an old license number was retired

### Uncertain match (confidence: `uncertain`)
- Address matches partially but facility name differs significantly
- OR a `successor_to` field on the licensee points to an old license
  that has violations, and the address matches weakly
- Mark as uncertain when the connection is plausible but not solid

Only the first two tiers (`exact` and `close_address`) should normally
appear in the queue. The `uncertain` tier goes in the summary under
`close_or_uncertain_match_license_numbers`.

## Violation Sorting Within Each License

For each license, collect all matched pre-boundary violations. Sort them
by `violation_date` ascending, then by `violation_id` ascending. This
sorted list becomes `matched_violation_ids` for that queue entry.

The `most_recent_violation_date` is the latest date among those matched
violations.

## Ranking Algorithm

Rank licenses from highest priority (rank 1) to lowest. Use these
criteria in order:

1. **Board review candidates first**: Licenses where any matched
   violation has `severity` = "serious" AND `disposition` = "open" OR
   `fine_balance` > 0 AND the violation theme involves public safety.
   These get `next_step_label` = `board_review`.

2. **Unpaid fines**: Licenses with violations having `fine_balance` > 0
   and `disposition` not "paid". These get `next_step_label` =
   `manual_fine_check`.

3. **Alert-flagged only**: Licenses where violations have `alert_flag` = 1
   but no unpaid fines or serious open violations. These get
   `next_step_label` = `manual_ALERT_check`.

4. **Everything else**: Remaining licenses get `next_step_label` =
   `additional_record_check`.

Within each next_step_label group, sort by:
- `violation_count` descending (more violations = higher priority)
- Then `most_recent_violation_date` descending (more recent = higher
  priority)
- Then `license_no` ascending (tiebreaker)

## Risk Tier

- **high**: Every license that has at least one matched pre-boundary
  violation. This is the norm in renewal queue tasks where all target
  licenses have violations.
- **medium**: License has violations but they are all minor/administrative
  (e.g., only "late renewal" themes with paid fines).
- **low**: License has no matched violations before the boundary.

In practice, the renewal queue tasks typically have all licenses at
`high` risk because the queue is built from licenses with active
violations.

## Next-Step Label Assignment

| Condition | Label |
|-----------|-------|
| Any matched violation has `severity` = "serious" AND `disposition` is "open" or "pending" | `board_review` |
| Any matched violation has `fine_balance` > 0 AND `disposition` is not "paid" (and no serious open violations) | `manual_fine_check` |
| Matched violations exist but all fines paid and no serious open violations | `manual_ALERT_check` |
| No matched violations (empty queue entry) | `additional_record_check` |

## Summary Construction

Build the summary after all queue entries are determined:

- `queue_size`: Number of entries in the queue (should match the target
  from the prompt, typically 10)
- `boundary_date`: The boundary date from the prompt, as YYYY-MM-DD
- `post_boundary_violation_ids_excluded`: All violation_ids with
  `violation_date` after the boundary, sorted by violation_id ascending.
  Include the _LATE suffixed IDs for all target licenses.
- `close_or_uncertain_match_license_numbers`: License numbers that had
  only close_address or uncertain match confidence, sorted ascending.
- `board_review_license_numbers`: License numbers that received
  `board_review` as next_step_label, sorted ascending.

## Policy Routing

One renewal policy governs the queue:

- **POL-REN-001** (REN-BOUNDARY): `exact_license_match_preferred: true`,
  `known_on_or_before_boundary_only: true`,
  `successor_match_mark_uncertain: true`. This means prefer exact license
  matches, only use violations on/before the boundary, and mark
  successor/predecessor matches as uncertain.
