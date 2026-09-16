# Alcohol License Renewal Manual-Review Queue

## Data Sources

Fetch these endpoints (use fetch_data.py --domain alcohol and --domain renewal):

- `/api/alcohol/licensees` - Licensee records with license_no, facility_name,
  address, and other identity fields.
- `/api/alcohol/violations` - Violation records, each with a violation_id,
  license_no or address fields, violation_date, and severity classification.
- `/api/renewal/rules` - Renewal rules that define the boundary date, risk-tier
  criteria, ranking methodology, next-step routing, and queue-size target.

Use `POST /api/sql` for complex matching when the REST endpoints do not directly
join licensees to violations by license_no alone. Send the SQL as a JSON body
with a `query` key.

## Violation Matching

For each target license, match violation records to the licensee. Matching
priority:

1. **Exact match** (`exact`): Violation record has a license_no field that
   matches the target license_no exactly.

2. **Close address** (`close_address`): Violation has an address that partially
   matches the licensee address but the license_no field is missing, different,
   or references an older license number. Use close_address when the address
   match is strong but the license identifier is not exact.

3. **Uncertain** (`uncertain`): Violation has a weak address match with no
   confirming identifier. Use sparingly and only when plausible.

Only include violations with a violation_date on or before the boundary date
(from renewal rules or the prompt). Violations dated after the boundary date
must be excluded from the queue and listed separately in the summary under
post_boundary_violation_ids_excluded.

## Boundary Date

The boundary date is provided in the prompt (e.g., 2025-04-10) or derivable
from `/api/renewal/rules`. All violations with violation_date strictly after
the boundary date are excluded from the queue.

## Ranking

Rank licensees from 1 to N (targeting the queue size, typically 10) by
descending priority:

1. **Severity-weighted violation count**: Licensees with more matched violations
   rank higher. Within the same count, more recent violations rank higher.

2. **Recency**: The most_recent_violation_date is the latest matched violation
   date. When two licensees have the same violation count, the one with the
   more recent violation ranks higher.

3. **Match confidence tiebreaker**: When violation counts and recency are
   equivalent, prefer exact matches over close_address, and close_address over
   uncertain.

4. **Board review candidates**: Licensees whose violation records contain
   severity or type indicators requiring board review should be ranked at the
   top of their count group.

Ranks must be consecutive integers 1 through the queue size with no gaps.

## Violation ID Ordering

Within each queue entry, sort matched_violation_ids by violation_date
ascending, then by violation_id ascending for ties.

## Risk Tier

- **high**: Any licensee with a matched violation that has a severity, fine, or
  classification indicator requiring board review or manual escalation. OR any
  licensee whose match_confidence is close_address or uncertain.
- **medium**: Licensees with violations but no high-severity indicators, and
  match_confidence is exact.
- **low**: Licensees with zero matched pre-boundary violations.

## Next Step Label

- **board_review**: Matched violations include a severity classification
  requiring board-level action (e.g., a specific severity flag, fine threshold,
  or alert indicator). OR match_confidence is close_address or uncertain AND
  violation severity is material.
- **manual_fine_check**: Violations have fine amounts that need manual
  verification against the renewal rules.
- **manual_ALERT_check**: Violations have alert flags that need manual review
  but do not require board-level escalation.
- **additional_record_check**: Violation records have inconsistencies or
  incomplete data requiring additional record pull.

## Summary Construction

- `queue_size`: Number of entries in the queue (integer).
- `boundary_date`: The boundary date in YYYY-MM-DD format.
- `post_boundary_violation_ids_excluded`: All violation IDs with dates after the
  boundary, sorted by violation_id ascending.
- `close_or_uncertain_match_license_numbers`: Every license_no in the queue
  where match_confidence is close_address or uncertain, sorted ascending.
- `board_review_license_numbers`: Every license_no in the queue where
  next_step_label is board_review, sorted ascending.

## Output Ordering

- Queue entries ordered by rank ascending (1, 2, 3, ..., N).
- matched_violation_ids sorted by violation_date ascending, then violation_id
  ascending.
- All summary ID lists sorted ascending.
