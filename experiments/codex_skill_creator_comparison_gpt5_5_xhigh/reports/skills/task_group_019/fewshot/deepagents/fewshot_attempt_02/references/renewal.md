# Alcohol Renewal Manual-Review Queues

Use this reference for alcohol renewal queue tasks built from licensee and violation exports.

## Boundary And Matching

Read the prompt's release boundary and target queue size. Fetch renewal rules and select the rule with the matching `release_boundary` when present. Parse `details_json`; `use_violations_on_or_before` is the cutoff for matched violations.

Filter target licensees by the explicit license list or range in the prompt. Include active target licensees unless the prompt says otherwise. Match violations by:

- Exact `license_no` match to the target license.
- `successor_to` match when the target licensee points to a former license. Include former-license violations only when the address or successor relationship supports the match.
- Address/name-only matches only as uncertain evidence; do not mix unrelated distractors into a license's matched violations.

Exclude violations dated after the boundary from the queue metrics. Put their IDs in `post_boundary_violation_ids_excluded` when the template asks for it, sorted as instructed.

## Queue Metrics

For each queued license:

- `violation_count`: number of matched pre-boundary violations.
- `most_recent_violation_date`: latest matched pre-boundary violation date.
- `matched_violation_ids`: matched pre-boundary IDs sorted by violation date ascending, then violation ID ascending.
- `match_confidence`: `exact` when all matched rows are exact-license rows; `close_address` when successor/former-license rows are included with address support; `uncertain` when only weak name/address evidence supports inclusion.
- Facility identity fields come from the current target licensee row, not former-license rows.

## Risk And Next Step

Use the renewal rule plus the violation cluster:

- `board_review`: close or uncertain successor matches, serious open/pending violations, very recent boundary-adjacent issues, or high-count/high-severity clusters needing board attention.
- `manual_fine_check`: unresolved fine balances, unpaid-fine themes, or open/pending fine-related records that do not rise to board review.
- `manual_ALERT_check`: alert-flagged records needing manual release review when no stronger fine or board category applies.
- `additional_record_check`: weak or incomplete records with no stronger label.

Set risk tier consistently with the next step and cluster:

- `high`: board-review cases, high-count clusters, serious unresolved issues, or close/uncertain successor matches with material violations.
- `medium`: multiple lower-severity alert/fine issues requiring manual review.
- `low`: only isolated low-severity issues, if the template permits such rows in the queue.

## Ranking

Assign ranks 1 through the target queue size with no gaps. A robust ranking pattern is:

1. Board-review bucket first.
2. Manual-fine-check bucket next.
3. Manual-alert-check bucket next.
4. Additional-record-check bucket last.

Within a bucket, sort by higher risk, most recent violation date descending, higher violation count, stronger match confidence, then license number ascending unless the prompt or renewal rule gives a different priority. After sorting, trim or fill to the requested queue size exactly.

## Summary

Compute `queue_size` from the final queue length. Copy the boundary date used. Build:

- `close_or_uncertain_match_license_numbers` from queue entries whose `match_confidence` is not `exact`.
- `board_review_license_numbers` from queue entries whose `next_step_label` is `board_review`.
- Post-boundary excluded IDs from matched target or successor rows after the cutoff.

Sort summary ID arrays according to the template.
