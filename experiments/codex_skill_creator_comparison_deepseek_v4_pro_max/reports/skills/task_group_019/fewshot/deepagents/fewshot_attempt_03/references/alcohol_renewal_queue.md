# Alcohol Renewal Manual-Review Queue

## Data Sources

Fetch all records before building the queue:

1. `GET /api/alcohol/licensees` — license records: license number, facility name, address, status
2. `GET /api/alcohol/violations` — violation records: violation ID, license link, date, severity, fine/ALERT status
3. `GET /api/renewal/rules` — renewal scoring rules, boundary date, matching rules, risk thresholds
4. `POST /api/sql` — additional queries when authorized by the prompt

Use `POST /api/sql` with header `X-Task-Token` set to the credential from the prompt or environment instructions.

## Boundary Date

The prompt specifies a boundary date (often called "release boundary"). Violations on or before this date are in scope for the queue ranking. Violations after this date must be excluded and listed in `post_boundary_violation_ids_excluded` in the summary.

## Matching Licensees to Violations

Violations link to licensees through identifiers. Determine match confidence for each violation-to-license relationship:

- **`exact`**: violation record directly references the target license number
- **`close_address`**: violation references a different license number but matches by facility address or old license identifier
- **`uncertain`**: possible match based on partial information but not confirmed

When a violation matches a licensee on a close-address or uncertain basis, include the violation in the count but flag the match confidence accordingly. Licenses with any non-exact matches appear in `close_or_uncertain_match_license_numbers` in the summary.

## Ranking Logic

Build a queue of the target licenses (up to the specified queue size) ranked for manual review. Ranking priority, from highest to lowest:

1. **Violation count** (pre-boundary, matched): more violations → higher rank
2. **Violation recency**: more recent most-recent-violation date → higher rank for ties on count
3. **Severity or risk signals**: serious violations, fines, ALERT flags → higher rank for ties on count and recency

Use all pre-boundary matched violations when counting. Do not exclude violations just because they are close-address matches; include them and reflect the confidence.

## Risk Tier Assignment

- **`high`**: any serious violation, fine outstanding, ALERT flag, or close-address match in the violation set
- **`medium`**: only non-serious violations with exact matches, no fines/ALERTs
- **`low`**: zero pre-boundary violations (such licenses typically appear lower in the queue or may not appear if the queue is size-limited)

## Next-Step Labels

Assign the appropriate next step for each queue entry:

- **`board_review`**: the licensee has serious violations, close-address matches, or patterns that warrant board attention. Typically assigned to the highest-priority entries.
- **`manual_fine_check`**: the licensee has a history with potential fines that need staff verification.
- **`manual_ALERT_check`**: the licensee has ALERT-relevant violations or flags that require staff screening.
- **`additional_record_check`**: the licensee has uncertain matches or incomplete records that need further investigation.

## Sorting Within Queue Entries

- **`matched_violation_ids`**: sort by violation date ascending, then by violation_id ascending
- **Queue entries**: sort by ascending rank (1 to N)

## Summary Construction

- `queue_size`: number of entries in the queue (integer)
- `boundary_date`: the release boundary date from the prompt (`YYYY-MM-DD`)
- `post_boundary_violation_ids_excluded`: all violation IDs with dates after the boundary that are associated with any of the target licensees, sorted by violation_id ascending
- `close_or_uncertain_match_license_numbers`: all license numbers where at least one matched violation has `close_address` or `uncertain` confidence, sorted ascending
- `board_review_license_numbers`: all license numbers where `next_step_label` is `board_review`, sorted ascending
