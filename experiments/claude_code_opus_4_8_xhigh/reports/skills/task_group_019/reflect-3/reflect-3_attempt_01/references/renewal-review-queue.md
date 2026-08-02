# Alcohol renewal manual-review queue

Build a ranked review queue over the target licenses, plus a `summary`. Each queue entry carries a
`rank`, the license identity, matched-violation info, `match_confidence`, `risk_tier`, and a
`next_step_label`.

## Datasets (renewal family)

- `renewal_rules`: each has a `release_boundary` and a `details_json` with `use_violations_on_or_before`,
  `late_rows_are_distractors`, `alert_flag_requires_manual_review`, `unpaid_fines_require_hold`. **Pick
  the rule whose `release_boundary` equals the boundary date in the prompt.**
- `alcohol_licensees`: `license_no`, `facility_name`, `address`, `active`, `successor_to`.
- `alcohol_violations`: `license_no`, `address`, `violation_id`, `violation_date`, `severity`
  (minor/medium/serious), `disposition` (open/pending/paid/settled/warning/dismissed), `fine_balance`,
  `alert_flag` (0/1), `theme`, `source_name`.
- A prior-comparison policy notes: exact license match preferred, known-on-or-before-boundary only,
  successor match → mark uncertain.

## Deterministic scaffolding (reliable)

- **Boundary:** only use violations with `violation_date <= boundary`. Rows dated after the boundary
  (typically `source_name = post_boundary_feed`, ids ending `-LATE`) are distractors — exclude them and
  list their `violation_id`s (sorted ascending) in `post_boundary_violation_ids_excluded`.
- **Matching:** attach a violation to a license by **exact `license_no`** (preferred). If the licensee
  has a `successor_to` predecessor with violations, those are **successor matches** →
  `match_confidence = "uncertain"`. Use `close_address` only when there is no exact match. Same-address
  rows carrying a **different license prefix** (other tasks' licenses) are distractors — never
  address-match them when an exact match exists.
- **Per-entry fields:** `matched_violation_ids` sorted by `violation_date` asc then `violation_id` asc;
  `most_recent_violation_date` = latest matched date; `violation_count` = number of matched rows.
- **Summary:** `queue_size` = target size; `boundary_date` = the boundary; `close_or_uncertain_match_
  license_numbers` = licenses whose confidence is uncertain/close (sorted ascending).

## Matched-set filter (get this right first)

The queue is a **manual-review** queue, so the matched set that drives `violation_count`,
`most_recent_violation_date`, and `matched_violation_ids` is very likely **not** every historical
pre-boundary violation. The `details_json` flags are filters, not just annotations:
`alert_flag_requires_manual_review` and `unpaid_fines_require_hold` point to counting the
**review-triggering** rows (alert-flagged and/or unresolved `open`/`pending`, and/or those carrying an
unpaid `fine_balance`) rather than resolved history. Determine the intended filter from the rule flags
and the template's field descriptions before computing counts — an "all pre-boundary" reading tends to
be wrong.

## Risk tier, next step, ranking (judgment)

- **`next_step_label`** maps to the dominant triggered rule: an uncertain/successor match →
  additional-record-check; an unresolved serious/major issue → board-review; an unpaid fine →
  manual-fine-check; an alert flag → manual-ALERT-check. Establish the priority order from the flags.
- **`risk_tier`**: escalate for unresolved serious violations, uncertain matches, or unpaid-fine holds;
  mid for other unresolved/fined rows; low when everything is resolved and unfined.
- **`board_review_license_numbers`** (summary) = licenses whose `next_step_label` is board-review.
- **Ranking:** ranks are `1..N` with no gaps, ordered by review priority. The queue is scored by
  matching entries on `license_no` (order is not the scoring lever), so getting each entry's computed
  **values** right matters far more than the exact rank order; still assign a sensible priority order
  (higher risk / more recent / higher unpaid balance first).
