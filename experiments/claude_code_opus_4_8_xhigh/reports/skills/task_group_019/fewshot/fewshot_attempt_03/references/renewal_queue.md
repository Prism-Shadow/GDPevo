# Alcohol renewal manual-review queue

Output: `queue` (one entry per target `license_no`, ranked `1..N` with no gaps)
+ `summary`. The prompt gives the target `license_no`s, the release **boundary
date**, and the target **queue size**.

## Data to pull (filtered SQL)

- `renewal_rules` — read `release_boundary` (should match the prompt's boundary)
  and `details_json` (`use_violations_on_or_before`,
  `alert_flag_requires_manual_review`, `unpaid_fines_require_hold`,
  `late_rows_are_distractors`).
- `alcohol_licensees` for the target `license_no`s — note `facility_name`,
  `address`, and `successor_to`.
- `alcohol_violations` for the targets **and** for any `successor_to` predecessor
  license numbers (filter by both sets of `license_no`).

## Match violations to each target license

For a target license, its **matched** violations are the `alcohol_violations`
rows with `violation_date <= boundary` that belong to it:
- **exact** match: `violation_id`'s `license_no == target`.
- **close_address** match: rows that belong to the target's `successor_to`
  predecessor (or a same-address different license). Include those rows in the
  matched set.
- Violations dated **after** the boundary (e.g. `*-LATE` rows) are **excluded**;
  collect their `violation_id`s for the summary.

Per entry:
- `matched_violation_ids` — the matched rows, sorted by `violation_date` ascending,
  then `violation_id` ascending.
- `violation_count` — number of matched rows.
- `most_recent_violation_date` — the max `violation_date` among matched rows.
- `match_confidence`:
  - `exact` — all matched rows are exact-license matches.
  - `close_address` — the matched set includes any predecessor/same-address row.
  - `uncertain` — an ambiguous/weak address-only match with no clear successor link.

## risk_tier

- **high** if either: a matched **serious** violation is not fully cleared —
  `severity == "serious"` and (`disposition in {open, pending}` **or**
  `fine_balance > 0`) — **or** the total matched `fine_balance` is `>= 500`.
- **medium** if there are matched violations but neither high condition holds.
- **low** if there are no matched violations.

## next_step_label (evaluate in this priority order)

1. **manual_ALERT_check** — every matched violation has `alert_flag == 1`.
2. **board_review** — there is a matched "sale to minor" themed violation
   (`theme == "sale to minor"`) whose `disposition` is not fully resolved
   (i.e. not `paid`/`dismissed`).
3. **manual_fine_check** — any matched violation has `fine_balance > 0`.
4. **additional_record_check** — otherwise (violations exist but no alert/board/
   fine trigger).

## Ranking

Sort entries into ranks `1..N`:
1. Primary: by `next_step_label` tier — `board_review` first, then
   `manual_fine_check`, then `manual_ALERT_check`, then `additional_record_check`.
2. Within a tier: by `most_recent_violation_date` **descending** (most recent first).

Then assign `rank = 1, 2, 3, …` in that order (integers, no gaps). The number of
entries equals the target queue size named in the prompt.

## summary

- `queue_size` — number of queue entries.
- `boundary_date` — the release boundary (YYYY-MM-DD).
- `post_boundary_violation_ids_excluded` — every violation for the targets/their
  predecessors dated **after** the boundary, `violation_id` ascending.
- `close_or_uncertain_match_license_numbers` — license numbers whose
  `match_confidence` is `close_address` or `uncertain`, sorted ascending.
- `board_review_license_numbers` — license numbers whose `next_step_label ==
  board_review`, sorted ascending.
