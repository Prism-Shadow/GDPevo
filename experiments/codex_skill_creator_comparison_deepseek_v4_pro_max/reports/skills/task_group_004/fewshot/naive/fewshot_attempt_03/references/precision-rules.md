# Precision and Formatting Rules

## Currency values

All monetary values use exactly 2 decimal places. This includes:
- `current_arr`
- `revenue` (monthly and aggregate)
- `overdue_balance`
- `arr_at_risk`
- `won_revenue`, `open_pipeline`
- `event_revenue`, `unpaid_claims_total`
- `expansion_pipeline`, `net_revenue_exposure`
- Any other field representing a dollar amount

Round using standard half-up rounding. Always include two decimal digits even when the value is a whole number (e.g., `0.00`, not `0` or `0.0`).

## Percentage values

All percentage values use exactly 1 decimal place. This includes:
- `sla_compliance_pct`
- `win_rate_pct`
- `accuracy_pct`
- Any other field suffixed with `_pct` or described as a percentage

Round using standard half-up rounding. Include one decimal digit even for whole-number percentages (e.g., `100.0`, not `100`).

## Counts

All counts are integers with no decimal places. This includes:
- Ticket counts, account counts, row counts, feature counts
- `accounts_reviewed`, `critical_or_high_count`, `collections_count`, `technical_recovery_count`
- `won_count`, `lost_count`, `open_count`
- `overdue_client_count`, `linked_followup_count`, `unlinked_followup_count`
- `hr_headcount`, `event_orders`
- `past_due_shortlist_count`, `low_tenure_shortlist_count`
- `strategic_accounts`, `enterprise_accounts`

## Risk scores

Risk scores are integers (e.g., `100`, `60`, `50`, `20`, `15`).

## Churn probabilities

Churn probabilities use exactly 3 decimal places (e.g., `0.102`, `0.039`, `0.001`).

## Special values

- NPS scores: integers (can be negative).
- `null` is used for `account_id` when a customer is unlinked, and for `next_touch_due_date` on `no_action` entries.
- `true`/`false` for boolean fields (lowercase, no quotes around the value in JSON).

## General JSON rules

- Return only valid JSON conforming to RFC 8259.
- Do not include trailing commas.
- Key names must match the template exactly (case-sensitive).
- Arrays must be ordered as specified (risk ranking by rank ascending, overdue followups by customer_name ascending).
- When a field is optional in the template, include it with the appropriate typed null/empty value rather than omitting it.
