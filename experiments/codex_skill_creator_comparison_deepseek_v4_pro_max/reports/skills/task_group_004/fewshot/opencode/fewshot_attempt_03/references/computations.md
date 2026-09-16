# Derived Field Computations

All formulas below are deterministic. Apply them exactly as described.

## Current ARR

**Primary source**: Billing snapshot `billing_arr` for the assessment quarter.

Find the billing snapshot where `account_id` matches and `as_of` equals the assessment date (quarter-end: `2026-03-31` for Q1, `2026-06-30` for Q2, `2026-09-30` for Q3, `2026-12-31` for Q4).

**Fallback**: If no snapshot exists for the quarter, use `billing_arr_current` from `/api/accounts/{id}`.

**When `uses_billing_arr_source` is false**: Use `crm_arr` from the account endpoint instead.

Higher ARR amplifies risk -- a critical account with $1.4M ARR is bigger exposure than one with $140K.

## Clean Ticket Count

Count tickets in the analysis period excluding spam and duplicates:

```
clean_count = sum(1 for t in tickets if not t.is_duplicate and not t.is_spam)
```

The `/api/accounts/{id}/metrics` endpoint provides `support_ticket_count` per month (may differ from direct counting). The QBR task uses metric endpoint counts. Retention risk tasks compute clean ticket counts directly from the tickets endpoint for accurate hygiene assessment.

## SLA Degradation Detection

SLA degradation is triggered when **any** month in the analysis period has `sla_compliance < 90.0`:

```
has_sla_degradation = any(m.sla_compliance < 90.0 for m in monthly_metrics)
```

The percentage is already in percent form (e.g., 85.9 means 85.9%, not 0.859). Compare against 90, not 0.90.

## Latest NPS

```
latest_nps = max by month: m.nps_score where m.survey_status != "missing" and m.nps_score is not null
```

If all months have missing surveys or null scores, latest_nps is `null` and NPS-based codes (nps_drop) are not triggered.

## NPS Drop Detection

```
earliest_nps = min by month: m.nps_score where m.nps_score is not null
nps_dropped = latest_nps < earliest_nps  OR  (latest_nps is not null and latest_nps < 40)
```

A null earliest_nps (all months missing) means no comparison possible -- do not flag nps_drop.

## Overdue Balance

From A/R aging, match account to customer_name:

```
overdue = ar.31_60 + ar.61_90 + ar.90_plus
```

The `1_30` bucket is NOT included in overdue. Find the A/R record where:
- `ar.customer_name` matches account's `legal_name` or any `account_alias`
- `ar.quarter` matches the assessment quarter (or `ar.as_of` matches the assessment date)

If no matching A/R record exists: overdue_balance = `0.0`, and flag `clean_billings`.

## Usage Decline

Compare the last month's `product_usage` to the first month's:

```
first_usage = metrics sorted by month ascending -> first.product_usage
last_usage = metrics sorted by month ascending -> last.product_usage
usage_declining = last_usage < first_usage
```

## Ticket Trend

```
monthly_counts = [m.support_ticket_count for m in metrics sorted by month]
trend = "improving" if decreasing, "worsening" if increasing, "flat" if stable
```

To determine trend: compare each consecutive pair. If all pairs show decrease, it's improving. If all show increase, it's worsening. Mixed or stable across all = flat.

## Tenure Risk

Standard finding is `negative` (shorter tenure -> higher risk):

```
tenure_risk_direction = "negative"
low_tenure_high_churn applies when: contract_tenure_months <= 18
```

If analysis finds the opposite, use `positive`. If not enough data, use `not_assessed`.

## Renewal Window

```
in_renewal_window = days_between(assessment_date, renewal_date) <= 90
```

The renewal_date must be in the future relative to the assessment date.

## Expansion Offset

```
has_expansion_offset = any open opportunity where
    opp.account_id == account_id
    AND opp.state == "open"
    AND opp.close_date is within or near the analysis period
```

Count opportunities where close_date falls in the quarter or the following quarter.

## Risk Score Computation

Risk scores are integers. Components (positive = higher risk):

| Factor | Weight | Condition |
|---|---|---|
| overdue_receivable | +30 | Overdue balance > 0 |
| nps_drop | +25 | NPS dropped or below 40 |
| sla_degradation | +20 | Any month SLA < 90% |
| usage_decline | +15 | Usage declining |
| low_tenure_high_churn | +10 | Tenure <= 18 months |
| renewal_window | +5 | Within 90 days of renewal |

Offsets (negative = lower risk):

| Factor | Weight | Condition |
|---|---|---|
| expansion_offset | -10 | Open expansion opportunities |
| clean_billings | -5 | No overdue, no billing issues |

ARR magnitude adjusts the base score for enterprise risk exposure. Higher ARR accounts get proportionally higher risk scores. The rank order (not absolute score) is what matters.

## Risk Level Mapping

Map risk_score to risk_level:

| Score range | Level |
|---|---|
| >= 75 | critical |
| 50-74 | high |
| 20-49 | medium |
| < 20 | low |

## Average Revenue (QBR)

```
avg_revenue = sum(m.recognized_revenue for m in metrics) / count(metrics)
```

Round to 2 decimal places.

## Peak Detection

For any metric across months: find the month with the maximum value.

```
peak_revenue_month = month where recognized_revenue is max
peak_revenue = max(recognized_revenue)
```

If tie, take the later month.

## Win Rate

```
win_rate_pct = (won_count / (won_count + lost_count)) * 100
```

Round to 1 decimal place. If denominator is 0, win_rate_pct = 0.0.

## Top Open Product Line

```
Count open opportunities grouped by product_line.
top_open_product_line = product_line with the highest count.
```

On tie: pick the product_line with highest total amount.

## Segment Classification

Accounts classified for segment_summary:

- **Strategic accounts**: `segment == "Strategic"` OR `product_plan == "Strategic"`
- **Enterprise accounts**: `segment == "Enterprise"` OR (Mid-Market excluded from strategic)

## Net Revenue Exposure

```
net_revenue_exposure = arr_at_risk - open_expansion_pipeline
```

If negative, cap at 0.0 (expansion offsets risk, doesn't create negative exposure).

## Churn Model Accuracy

```
accuracy_pct = (correct_predictions / total_predictions) * 100
```

Where correct_predictions are validation rows where predicted label matches actual Churn label. Round to 1 decimal.

## Feature Count

Count feature columns in churn CSVs. Exclude `customer_id` and `Churn` (the label). Standard count is 19 features.

## Average Probability Top 5

```
avg_prob = sum(top_5[i].predicted_churn_probability for i in 1..5) / 5
```

Round to 3 decimal places.

## Cohort Checks

- **past_due_shortlist_count**: Count of ranked candidates with reason_code `overdue_receivable`
- **low_tenure_shortlist_count**: Count of ranked candidates with reason_code `low_tenure_high_churn`

## HR Headcount (all regions)

```
hr_headcount = sum(r.headcount for r in hr_summary where r.quarter == target_quarter)
```

## Unpaid Claims Total (all regions)

```
unpaid_claims_total = sum(r.unpaid_claims_amount for r in hr_summary where r.quarter == target_quarter)
```

## Event Orders/Revenue

Filter event_performance for the target event_id and quarter:

```
event_orders = e.event_orders
event_revenue = e.event_revenue
```
