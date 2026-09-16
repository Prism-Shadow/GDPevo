# Alcohol Renewal Manual Review Queue

## Overview

Build a ranked manual-review queue for alcohol licensees by matching licensee records against violation records, filtering by a boundary date, and assigning ranks based on recency, severity, and count of pre-boundary violations. The output is a JSON object with a `queue` array and a `summary` object, both conforming strictly to the task's answer template.

## Data-Fetching Sequence

1. GET /api/renewal/rules -- renewal boundary date, screening thresholds, and ranking criteria.
2. GET /api/alcohol/licensees -- all target licensees (license_no, facility_name, address, type, status).
3. GET /api/alcohol/violations -- all violation records with violation_id, related license numbers, facility address, date, type, and severity.
4. POST /api/sql -- use when license-to-violation matching requires a join that the direct endpoints do not support (e.g., matching by legacy license numbers or fuzzy address matching).

## Violation Matching

For each target licensee, find all violation records that can be attributed to that licensee:

1. **Exact match**: The violation's license_no field matches the target license_no directly. Match confidence is `exact`.
2. **Close address match**: The violation references a different or legacy license number but the facility address matches the target licensee's address. Match confidence is `close_address`.
3. **Uncertain match**: The violation shares a partial identifier or address element but the link is ambiguous. Match confidence is `uncertain`.

## Boundary Date Filtering

The boundary date (e.g., 2025-04-10) is the release cutoff. Violations with dates on or after the boundary date are excluded from the queue's violation counts and matched_violation_ids. These post-boundary violations are collected separately for the summary's `post_boundary_violation_ids_excluded` field.

Violations strictly before the boundary date are included in the queue's per-licensee violation counts.

## Ranking Logic

Rank licensees 1 through N (N = target queue size from prompt) in descending priority:

1. **Primary sort**: Risk tier (high before medium before low).
2. **Secondary sort**: Next-step label priority:
   - `board_review` ranks highest within a tier.
   - `manual_fine_check` and `manual_ALERT_check` come next (order depends on violation severity and count).
   - `additional_record_check` ranks lowest within a tier.
3. **Tertiary sort**: Most recent violation date (more recent ranks higher).
4. **Quaternary sort**: Violation count (higher count ranks higher).
5. **Quinary sort**: License_no ascending as tiebreaker.

## Risk Tier Assignment

- **high**: 3+ pre-boundary violations, or any violation within the most recent 60 days before the boundary, or any serious-severity violation, or a close_address/uncertain match with high-count violations.
- **medium**: 1-2 pre-boundary violations with no recent (last 60 days) violations and no serious violations.
- **low**: 0 pre-boundary violations (not typically present in a manual review queue unless forced).

From the train evidence, all licensees in the reviewed queue were rated high except one medium outlier. Let the actual violation data drive tier assignment rather than assuming a default.

## Next-Step Label Assignment

- **board_review**: The licensee has close_address or uncertain match confidence, OR 3+ violations including serious ones, OR a violation within 10 days of the boundary date.
- **manual_fine_check**: High violation count (3+) with exact match and no match-uncertainty concerns; the primary concern is administrative fine processing.
- **manual_ALERT_check**: Moderate violation count (2-3) with exact match and older violation dates; the primary concern is ALERT system flagging.
- **additional_record_check**: Low violation count or uncertain match; additional records review needed before action.

## matched_violation_ids Ordering

Within each queue entry, sort matched_violation_ids by violation date ascending, then by violation_id ascending within the same date.

## Summary Construction

- `queue_size`: The number of queue entries (typically 10).
- `boundary_date`: The boundary date from the task prompt or renewal rules, in YYYY-MM-DD format.
- `post_boundary_violation_ids_excluded`: All violation IDs with dates on or after the boundary date, sorted by violation_id ascending.
- `close_or_uncertain_match_license_numbers`: License numbers for which any violation match confidence is `close_address` or `uncertain`, sorted ascending.
- `board_review_license_numbers`: License numbers whose next_step_label is `board_review`, sorted ascending.
