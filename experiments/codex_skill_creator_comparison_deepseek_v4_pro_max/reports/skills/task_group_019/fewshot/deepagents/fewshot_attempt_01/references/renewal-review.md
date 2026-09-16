# Alcohol Renewal Queue Review

## Endpoints

| Endpoint | What It Supplies |
|----------|-----------------|
| GET /api/alcohol/licensees | License identity, facility_name, address |
| GET /api/alcohol/violations | Violation records with dates and severity |
| GET /api/renewal/rules | Renewal risk thresholds and boundary rules |
| POST /api/sql | Targeted queries (use X-Task-Token header) |

## Boundary Date

The task provides a release boundary date (e.g. 2025-04-10). Violations with
a `violation_date` on or before the boundary are eligible for queue ranking.
Violations with a date after the boundary must be excluded from the queue and
listed in `post_boundary_violation_ids_excluded`.

## Licensee Matching

For each target license, look up the licensee record from
`/api/alcohol/licensees`. Record the `facility_name` for queue output.

## Violation Matching Strategy

Match violations to licensees using a three-tier confidence system:

### Exact Match (match_confidence: "exact")

A violation's identifier or related field directly references the license
number (violation IDs following the format `AV-license_no-seq`). This is the default
when the violation ID string contains the license number substring.

### Close Address Match (match_confidence: "close_address")

When a violation record references an older or variant identifier (e.g.
`AV-license_no-OLD-seq` for `license_no`), match by proximity: the violation
address or facility name is close to the licensee's address. These are
typically legacy or predecessor records.

### Uncertain Match (match_confidence: "uncertain")

When the connection is ambiguous -- there is some geographic or name overlap
but not enough for exact or close_address confidence. Use sparingly.

## Violation Count and Dates

For each licensee, count only pre-boundary matched violations. The
`most_recent_violation_date` is the latest violation date among matched
violations (still before or on the boundary).

## Queue Ranking

Rank licensees by priority in descending order:

1. Higher `violation_count` ranks higher
2. Ties broken by more recent `most_recent_violation_date`
3. Further ties broken by `match_confidence` precision (exact > close_address > uncertain)
4. Last tiebreak: ascending `license_no`

The top of the queue (rank 1) is the highest priority for manual review.

## Risk Tier Assignment

- `high`: Three or more violations, any serious violation, or close_address match
- `medium`: Two violations or older incidents with exact match
- `low`: Single violation, older date, no special flags

Note: licensees with multiple violations or serious incidents should receive `high`
risk tier when violations are significant. Apply conservatively.

## Next-Step Label Assignment

- `board_review`: serious violations present, close_address matches, or three
  or more violations requiring board-level attention
- `manual_fine_check`: violations that are primarily fine-related (less
  severe, resolved violations may also map here when count is high)
- `manual_ALERT_check`: cases flagged by the renewal rules endpoint as
  needing specialized alert review
- `additional_record_check`: lower-severity or borderline cases

Rank the most severe cases (highest counts, most recent, close_address) as
`board_review`, moderate-high as `manual_fine_check`, and the rest as
`manual_ALERT_check` or `additional_record_check`.

## Summary Construction

- `queue_size`: must equal the number of queue entries
- `boundary_date`: the release boundary date from the task
- `post_boundary_violation_ids_excluded`: all violation IDs with dates after
  the boundary, sorted ascending by violation_id
- `close_or_uncertain_match_license_numbers`: license numbers with
  match_confidence other than "exact", sorted ascending
- `board_review_license_numbers`: license numbers whose next_step_label is
  "board_review", sorted ascending
