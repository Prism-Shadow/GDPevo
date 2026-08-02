# Alcohol renewal manual-review queue

Output: `queue` (exactly the target size, ranks 1..N no gaps) + `summary`. Each queue
item = `rank`, `license_no`, `facility_name`, `violation_count`,
`most_recent_violation_date`, `matched_violation_ids`, `match_confidence`
(exact/close_address/uncertain), `risk_tier` (low/medium/high), `next_step_label`.

## Step 1 — inputs

- Targets = the license batch in the prompt (e.g. `AL-TR3-001..010`); the prompt gives
  the **release boundary** date and the **target queue size**.
- `GET /api/renewal/rules` → the rule whose `release_boundary` matches the prompt; its
  `details_json` confirms `use_violations_on_or_before` (= boundary),
  `alert_flag_requires_manual_review`, `unpaid_fines_require_hold`,
  `late_rows_are_distractors`.
- SQL: `alcohol_licensees WHERE license_no LIKE '<PREFIX>-%'` (each has `facility_name`,
  `address`, `active`, `successor_to`) and `alcohol_violations` for the same license
  numbers **and** for any `successor_to` predecessor license.

## Step 2 — build each target's matched violation set

For each target license:
- Take its own `alcohol_violations` rows **plus** the rows of its `successor_to`
  predecessor (if any).
- Keep only rows with `violation_date <=` boundary. **Drop everything dated after the
  boundary** (these are the `*-LATE` distractors) and never match by address to another
  license (`-DIS-`, `-TE2-`, `-TE5-` at the same address are other batches).
- `violation_count` = size of this matched set. `most_recent_violation_date` = max
  `violation_date` in it. `matched_violation_ids` = the ids, sorted by `violation_date`
  ascending then `violation_id` ascending.

## Step 3 — `match_confidence`

- `exact` — all matched rows come from the target's own `license_no`.
- `close_address` — the set includes predecessor rows (via `successor_to`) whose
  predecessor `address` equals the target's address (a confident same-site successor).
- `uncertain` — a successor/predecessor match where the addresses do **not** agree.
  (`POL-REN-001`: `exact_license_match_preferred`, `known_on_or_before_boundary_only`,
  `successor_match_mark_uncertain`.) A target with a `successor_to` but no predecessor
  violations stays `exact`.

## Step 4 — `next_step_label` (drives ranking; evaluate top-down)

Let a violation be *unresolved* if `disposition ∈ {open, pending}`.
1. **manual_ALERT_check** — **every** matched violation has `alert_flag == 1` (a pure
   alert profile). This takes precedence over the others.
2. Otherwise **board_review** — the matched set has a `serious` unresolved violation,
   **or** an anomalous large unpaid balance sitting on a closed disposition (a fine that
   remains despite the violation being e.g. a `warning` — a disputed balance routine
   collection won't clear; the observed trigger was a `warning`-disposition row with a
   large `fine_balance`). Also treat a close/uncertain successor match with unresolved
   issues as board-worthy.
3. Otherwise **manual_fine_check** — any matched violation has `fine_balance > 0`
   (an unpaid fine of any disposition).
4. Otherwise **additional_record_check** — no alert/fine/serious signal remains.

## Step 5 — `risk_tier`

- `high` — the license has a non-alert matched violation **or** a serious unresolved
  violation (i.e. anything except a pure-alert profile with no serious unresolved).
- `medium` — every matched violation is alert-flagged **and** none is a serious
  unresolved violation.
- `low` — no matched violations of concern (not seen in practice).

## Step 6 — rank the queue

Primary key = `next_step_label` priority: `board_review` (0) > `manual_fine_check` (1) >
`manual_ALERT_check` (2) > `additional_record_check` (3). Secondary key =
`most_recent_violation_date` **descending**. Assign ranks 1..N in that order (no gaps,
length = target size).

## Step 7 — `summary`

- `queue_size` = N; `boundary_date` = the boundary.
- `post_boundary_violation_ids_excluded` = every violation id (across targets and their
  predecessors) with `violation_date >` boundary that you dropped, `violation_id`
  ascending.
- `close_or_uncertain_match_license_numbers` = target license numbers whose
  `match_confidence` is `close_address` or `uncertain`, ascending.
- `board_review_license_numbers` = target license numbers whose `next_step_label` is
  `board_review`, ascending.
