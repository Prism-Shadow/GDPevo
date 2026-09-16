# Output Conventions

## Format

Return only valid JSON. No surrounding text, markdown fences, or commentary.

## Precision

| Data type | Decimal places | Example |
|-----------|---------------|---------|
| Currency (ARR, revenue, balances, pipeline) | 2 | `1000000.00` |
| Percentages (SLA, win rate, accuracy) | 1 | `93.3` |
| Counts (tickets, accounts, headcount) | integer | `13` |
| Risk scores | integer | `100` |
| Churn probabilities | 3 | `0.102` |

Use standard rounding (round half up).

## Null Handling

- `latest_nps`: if no NPS responses exist in the period, use `null`. If responses exist but all scores are null, use `null`.
- `nps_score` in monthly metrics: may be `null` when `survey_status == "missing"`.
- `account_id` in overdue followups: `null` when `link_status == "unlinked"`.
- `next_touch_due_date`: `null` when `primary_action == "no_action"`.
- `expansion_pipeline`: `0.00` when no open opportunities exist for the account in the period.

## ARR Source Selection

The `current_arr` field in risk ranking and retention board outputs uses ARR from the billing system, not CRM:

1. Primary: `billing_arr_current` from the account endpoint (`GET /api/accounts/{account_id}`)
2. Fallback: most recent `billing_arr` from billing snapshots (`GET /api/billing/snapshots`) for the as-of date

Set `uses_billing_arr_source: true` when using billing-derived ARR.

## Ticket Counting

**Clean ticket count** filters out spam and duplicates:

```
clean = [t for t in tickets if not t.is_duplicate and not t.is_spam]
count = len(clean)
```

Use the `clean_ticket_count` field from `/exports/account_metric_extract.csv` as a shortcut when appropriate.

## SLA Computation

Primary source: `sla_compliance` field from the account metrics endpoint (already a percentage, 1 decimal).

Alternative (when metrics unavailable): compute from tickets as `count(tickets with resolution_sla_met == true) / clean_ticket_count * 100`.

## Overdue Balance

```
overdue = ar_entry["31_60"] + ar_entry["61_90"] + ar_entry["90_plus"]
```

Do NOT include `current` or `1_30`.

For risk ranking, use the A/R entry with `as_of` matching the assessment date. For the receivables review, use the A/R entries for the specified quarter.

## NPS Selection

**Latest NPS for risk ranking:** From the NPS endpoint, take the most recent response by `response_date` where `retracted == false`. Use the `score` field. If the most recent has a null score, take the next most recent non-null score.

**Monthly NPS for QBR:** Use `nps_score` from the account metrics endpoint. May be null.

**NPS drop detection:** Compare latest NPS to the second-most-recent NPS. A drop of 20+ points qualifies as `nps_drop`.

## Usage Trend

From account metrics `product_usage` field. Compare first month to last month in the analysis period. If declining, add `usage_decline` reason code.

## Renewal Window Detection

An account is in the renewal window if its `renewal_date` falls within the analysis period or within 90 days after the assessment date.

## Risk Score Computation

Risk scoring uses a composite model. Derive risk score from these weighted factors:

1. **Overdue receivables** (highest weight): if overdue_balance > 0, add 25 points
2. **NPS drop** (high weight): if latest NPS is 30+ points lower than prior, add 20 points; if 15-29 points lower, add 10 points
3. **Low tenure** (medium weight): if contract_tenure_months <= 12, add 15 points
4. **SLA degradation** (medium weight): if any month SLA < 90%, add 10 points; if all months SLA < 85%, add 5 more
5. **Usage decline** (medium weight): if usage declining over the period, add 10 points
6. **Renewal window** (medium weight): if renewal_date is within 90 days of assessment date, add 15 points; if within the period, add 10 more
7. **Expansion offset** (negative weight): for each open expansion opportunity with close_date in period, subtract 5 points (max -10)

Scale the final score to 0-100. Cap at 100, floor at 0.

## Ranking and Sorting

- **Risk ranking**: Sort by risk_score descending. Break ties by current_arr descending.
- **Churn outreach ranking**: Sort by predicted_churn_probability descending.
- **Overdue followups**: Sort by customer_name ascending (alphabetical, case-insensitive).
- **Retention board**: Sort by risk severity (critical > high > medium > low), then by current_arr descending within each tier.

## Policy Code Selection

Choose the single policy code that best describes the methodology used. The mapping in controlled_vocabularies.md explains what each code means. Do not randomly select; pick the code that matches the actual data pipeline used.
