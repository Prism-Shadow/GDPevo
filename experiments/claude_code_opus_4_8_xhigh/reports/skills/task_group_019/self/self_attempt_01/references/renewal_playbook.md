# Family C — Alcohol renewal manual-review queue

Goal: a ranked `queue` (length = the target queue size in the prompt, ranks
`1..N` with no gaps) plus a `summary`. Each queue item: `rank`, `license_no`,
`facility_name`, `violation_count`, `most_recent_violation_date`,
`matched_violation_ids`, `match_confidence`, `risk_tier`, `next_step_label`.

## Setup

1. Read the prompt's **release boundary** date and **target queue size**.
2. Load `renewal_rules`, select the rule whose `release_boundary` equals the
   prompt boundary, and read `details_json`:
   - `use_violations_on_or_before` (= boundary) — filter `violation_date`.
   - `alert_flag_requires_manual_review`, `unpaid_fines_require_hold`,
     `late_rows_are_distractors`.
3. Load `alcohol_licensees` and `alcohol_violations`.

## Per target license

1. **Match violations to the licensee.**
   - `license_no` exact equality → `match_confidence = exact`.
   - No exact hit but same `address` → `close_address`.
   - Match via a `successor_to` relationship → `uncertain`.
2. **Apply the boundary by date.** Keep only violations with
   `violation_date <= boundary`. Violations dated after the boundary are
   **excluded** — collect their `violation_id`s for
   `summary.post_boundary_violation_ids_excluded`.
   Filter on the **date**, not on `source_name`; `post_boundary_feed` is a
   distractor label and can contain on-or-before rows, while other feeds can
   contain after-boundary rows.
3. **Drop distractor rows.** With `late_rows_are_distractors`, `theme =
   'late renewal'` rows do not by themselves justify manual review — exclude them
   from the review signal/count.
4. **Count and date.** `violation_count` = number of matched, pre-boundary,
   non-distractor violations. `most_recent_violation_date` = the latest such
   `violation_date`. `matched_violation_ids` = those IDs sorted by
   `violation_date` ascending, then `violation_id` ascending.
5. **next_step_label** (template enum):
   - Unpaid fine (`fine_balance > 0`, `unpaid_fines_require_hold`) →
     `manual_fine_check`.
   - `alert_flag = 1` (`alert_flag_requires_manual_review`) →
     `manual_ALERT_check`.
   - Serious/major severity or disposition warranting the board → `board_review`.
   - Close/uncertain match or otherwise needing corroboration →
     `additional_record_check`.
   Apply the rule toggles in priority order and pick the single most appropriate
   label for the item.
6. **risk_tier** — from severity mix, count, alert/fine signals: `high`
   (serious + open/unpaid or multiple hits), `medium` (some matched signal),
   `low` (minor/isolated).

## Ranking

Rank the target licenses into `1..N` (N = target queue size), ordered by review
priority — higher risk first, breaking ties by `violation_count`, then
`most_recent_violation_date` (more recent first), then `license_no`. Ranks are
consecutive integers with no gaps; the queue length equals the target size.

## Summary

- `queue_size` = queue length (= target size).
- `boundary_date` = the release boundary (`YYYY-MM-DD`).
- `post_boundary_violation_ids_excluded` = after-boundary violation IDs (from
  step 2), sorted by `violation_id` ascending.
- `close_or_uncertain_match_license_numbers` = licenses whose
  `match_confidence` is `close_address` or `uncertain`, sorted ascending.
- `board_review_license_numbers` = licenses whose `next_step_label` is
  `board_review`, sorted ascending.
