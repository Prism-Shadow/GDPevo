# Alcohol Renewal Manual-Review Queue Rules

## Boundary Date

The boundary date is either given in the prompt or sourced from the renewal rules endpoint (`GET /api/renewal/rules`). Violations dated after this boundary are excluded from scoring but still tracked.

## Violation Matching

Match violations to licensees using these confidence levels:

| Confidence | When to Use |
|---|---|
| `exact` | Violation's license number exactly matches the licensee's license number |
| `close_address` | License numbers differ but facility addresses are substantially similar (same street, nearby number) |
| `uncertain` | License number partially matches or address is similar but key details differ |

When a `close_address` match exists, include that license number in the summary's `close_or_uncertain_match_license_numbers`.

## Post-Boundary Violations

Violations with dates strictly after the boundary date must be:

1. Excluded from the violation count for ranking purposes
2. Excluded from `matched_violation_ids` in queue entries
3. Excluded from `most_recent_violation_date` calculation
4. Listed in the summary's `post_boundary_violation_ids_excluded`, sorted ascending

## Ranking Algorithm

### Priority Tier (Primary Sort)

Licenses are grouped by `next_step_label` in this precedence order:

1. `board_review` (highest priority)
2. `manual_fine_check`
3. `manual_ALERT_check`
4. `additional_record_check` (lowest priority)

### Within-Tier Sorting (Secondary Sorts)

Within the same `next_step_label` tier:

1. **Sort by most_recent_violation_date descending** — more recent violations rank higher
2. **Break ties by violation_count descending** — higher count ranks higher
3. **Break remaining ties by license_no ascending** — deterministic fallback

### Next-Step Label Assignment

Assign `next_step_label` based on the violation profile:

**board_review** when:
- Violation count ≥ 3 AND most recent violation is within ~90 days of the boundary AND match confidence is `exact`
- OR match confidence is `close_address` with any violation count (escrowed for board verification)
- OR match confidence is `uncertain` with high violation count (≥3)

**manual_fine_check** when:
- Violation count ≥ 3 but violations are older (more than ~90 days from boundary)
- OR violation count ≥ 2 with recent violations where the renewal rules indicate fine-eligible charges

**manual_ALERT_check** when:
- Violation count is 1-2, violations are not recent, and no board-level concern
- OR match confidence is `uncertain` with low count (1-2)

**additional_record_check** when:
- Violation count is 0 or 1, and the single violation is old/minor

## Risk Tier Assignment

| Next Step Label | Default Risk Tier | Exception |
|---|---|---|
| `board_review` | `high` | — |
| `manual_fine_check` | `high` | May be `medium` if violations are old and low-severity |
| `manual_ALERT_check` | `medium` | May be `high` if match is uncertain |
| `additional_record_check` | `low` | — |

When all licenses in the queue share the same next_step_label type, differentiate risk tiers by violation recency and count: the highest-ranked within a tier get `high`, middle get `medium`, bottom get `low`.

## Matched Violation IDs Sorting

Within each queue entry, sort `matched_violation_ids` by violation date ascending, then by violation_id ascending as a tiebreaker. This means the oldest violation appears first.

## Queue Construction Rules

1. Queue must have exactly the size specified in the prompt/template
2. Ranks must be consecutive integers starting at 1 with no gaps
3. Only include licenses from the target range in the prompt
4. Licenses with no matched violations may still appear in the queue if the target count demands it; rank them last

## Summary Construction

| Field | Value |
|---|---|
| `queue_size` | Number of entries in the queue |
| `boundary_date` | The boundary date from the prompt or renewal rules |
| `post_boundary_violation_ids_excluded` | All violation IDs with dates after the boundary, sorted ascending |
| `close_or_uncertain_match_license_numbers` | License numbers with non-exact match confidence, sorted ascending |
| `board_review_license_numbers` | License numbers assigned `board_review` next step, sorted ascending |
