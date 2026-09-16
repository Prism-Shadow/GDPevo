# Alcohol License Renewal Review — Domain Reference

Load this reference when the task involves building a ranked manual-review
queue for alcohol license renewals, matching licensees to violation records,
or constructing renewal screening outputs. Use it alongside the main SKILL.md
workflow.

## Endpoints

| Endpoint | What it returns |
|---|---|
| GET /api/alcohol/licensees | Licensee records with license_no, facility_name, address |
| GET /api/alcohol/violations | Violation records with violation_id, license_no, date, description |
| GET /api/renewal/rules | Renewal screening rules including boundary date and ranking logic |
| POST /api/sql | Arbitrary SQL when needed for cross-referencing |

## Ranking Logic

Build a ranked queue where position 1 is the highest-priority review candidate
and position N is the lowest. The ranking should reflect risk severity following
these principles:

1. **Violation count** — more matched violations generally means higher rank,
   but this is not the only factor
2. **Recency** — more recent violations weigh more heavily than older ones,
   especially violations near the boundary date
3. **Match confidence** — exact matches are more reliable than close_address or
   uncertain matches; exact matches with many violations rank above close
   matches with the same count
4. **Severity** — board-level concerns (board_review) rank above fine or ALERT
   checks

When two licensees have similar severity profiles, use most_recent_violation_date
as the tiebreaker: more recent dates rank higher.

## Boundary Date

The boundary date is the release date specified in the prompt. All violation
matching uses only violations on or before this date. Violations after the
boundary must be listed in post_boundary_violation_ids_excluded but must not
influence the ranking.

## Match Confidence

When cross-referencing licensees against violations:

- **exact** — the violation record's license identifier exactly matches the
  licensee's license_no
- **close_address** — the license identifier does not match but the address
  or facility name strongly suggests the same entity (e.g., records from
  a predecessor license at the same location)
- **uncertain** — the connection is suggestive but cannot be confirmed with
  the available data

## Next-Step Labels

Assign next_step_label based on the highest-severity concern for each queue
entry:

- **board_review** — the application requires board-level review, typically
  due to high violation count with recency, exact match confidence, and
  severity indicators
- **manual_fine_check** — the application needs a manual review of
  outstanding fines
- **manual_ALERT_check** — the application needs an ALERT system check
- **additional_record_check** — additional records need to be pulled and
  reviewed

## Risk Tiering

- **high** — three or more matched violations, or any board-level concern
- **medium** — one or two matched violations with no board-level concern
- **low** — zero matched violations (unlikely to appear in a manual-review
  queue)

## Matched Violation IDs

List all violation IDs matched for each licensee, sorted by violation date
ascending, then by violation_id ascending as a secondary sort. Only include
violations on or before the boundary date.

## Summary Construction

- queue_size: number of entries in the queue (should match the target)
- boundary_date: the release boundary date from the prompt in YYYY-MM-DD
- post_boundary_violation_ids_excluded: all violation IDs with dates after
  the boundary, sorted by violation_id ascending
- close_or_uncertain_match_license_numbers: license numbers for any queue
  entries whose match_confidence is not "exact", sorted ascending
- board_review_license_numbers: license numbers for all queue entries with
  next_step_label "board_review", sorted ascending
