# Alcohol renewal manual-review queue rules

Build a ranked queue of target licensees (size given by the prompt, e.g. 10) for the
release boundary named in the prompt. Read `renewal_rules` for the active rule; its
`details_json` carries the key flags.

## Matching violations to licensees

For each target `license_no`, collect violations that are **on or before the release
boundary** (`violation_date <= boundary_date`) and match the licensee:

1. **Exact match** — `violation.license_no == licensee.license_no`. Confidence `exact`.
2. **Successor match** — the violation's `license_no` equals the licensee's
   `successor_to` (an old permit that rolled into this one). Confidence `uncertain`.
3. **Address collision (other license number)** — `violation.address ==
   licensee.address` but a **different** `license_no` that is **not** the successor old
   permit. Treat these as **distractors** by default: do **not** match them. (Mixing in
   same-address rows from unrelated licenses collapses the queue and is a known
   catastrophic-score trap.) Only deviate from this if the prompt or the active rule
   explicitly instructs address-based matching at `close_address` confidence.

`source_name == "post_boundary_feed"` (the `*-LATE` rows) are **distractors** — they record
post-boundary events and must be excluded from the queue; collect their ids for the summary
exclusion list. `late_rows_are_distractors: true` confirms this.

## Per-queue entry fields

- `rank`: integer 1..N, no gaps, ordered by the ranking below.
- `license_no`: the target licensee.
- `facility_name`: from the licensee record.
- `violation_count`: number of pre-boundary matched violations.
- `most_recent_violation_date`: latest matched `violation_date` (`YYYY-MM-DD`).
- `matched_violation_ids`: sorted by violation date ascending, then `violation_id`
  ascending (per the template).
- `match_confidence`: `exact` if the licensee has any exact match; otherwise `uncertain`
  (successor-only) or `close_address` (only if address matching was actually warranted).
  A licensee that relies on a successor permit for any match should appear in the summary's
  close/uncertain list.
- `risk_tier`: `high` for licensees with an open/pending **serious** matched violation;
  otherwise `medium`/`low` by rules below.
- `next_step_label`: `board_review` for an open/pending serious violation (and any case the
  risk-matrix policy escalates); `manual_fine_check` when there is an unpaid fine
  (`fine_balance > 0` and `disposition` not `paid`/`settled`); `manual_ALERT_check` when
  `alert_flag == 1` and no unpaid fine; else `additional_record_check`.
  (`alert_flag_requires_manual_review` and `unpaid_fines_require_hold` from the rule's
  `details_json` gate the manual steps.)

## Ranking (rank 1 = highest priority)

Order by, in descending priority:
1. `violation_count` (more violations = higher priority).
2. presence of an **open/pending serious** matched violation.
3. `alert_flag == 1` among matched violations.
4. `most_recent_violation_date` (more recent = higher priority).
5. lower numeric suffix of `license_no` (stable tiebreak).

Apply the template's exact ordering text if it differs.

## summary

- `queue_size`: the required queue length (e.g. 10).
- `boundary_date`: the release boundary (`YYYY-MM-DD`) from the prompt/rule.
- `post_boundary_violation_ids_excluded`: all excluded post-boundary (`*-LATE`) violation
  ids that would otherwise have matched a target, sorted by `violation_id` ascending. (Use
  only the target license's own `*-LATE` rows; do not include unrelated same-address
  distractors unless they genuinely correspond to a target.)
- `close_or_uncertain_match_license_numbers`: target license numbers whose
  `match_confidence` is `close_address` or `uncertain`, sorted ascending.
- `board_review_license_numbers`: target license numbers whose `next_step_label` is
  `board_review`, sorted ascending.

## Common pitfalls
- Including same-address violations from **other** license numbers (`*-TE2-*`, `*-TE5-*`,
  etc.) as matches — these are distractors. Match by exact `license_no` (plus successor)
  only.
- Forgetting to exclude post-boundary `*-LATE` rows from `violation_count` while still
  listing them in the exclusion summary.
- Marking a successor-only licensee `exact` (it is `uncertain`) and omitting it from the
  close/uncertain summary list.
- Mis-sorting `matched_violation_ids` (date ascending then id ascending, not license-id
  order).
