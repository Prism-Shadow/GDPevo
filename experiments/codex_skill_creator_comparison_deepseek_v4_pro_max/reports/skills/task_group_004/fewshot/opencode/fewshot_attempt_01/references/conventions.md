# Computation Conventions

Deterministic rules for every derived field. Apply these after all API data is
fetched.

---

## Precision

| Data type | Precision | Example |
|---|---|---|
| Currency (ARR, revenue, overdue, pipeline) | 2 decimal places | `1416439.47` |
| Percentages (SLA, accuracy, usage, win rate) | 1 decimal place | `93.3` |
| Churn probabilities | 3 decimal places | `0.102` |
| Risk scores | Integer | `60` |
| Counts (tickets, accounts, headcount) | Integer | `13` |
| NPS scores | Integer | `39` |

Use Python's `round(value, N)` for rounding. Sum before rounding when computing
aggregates.

---

## ARR Source

For `current_arr` in retention risk tasks:

1. **Preferred**: `billing_arr` from `/api/billing/snapshots` for the snapshot
   whose `as_of` date matches the assessment date. This is the quarter-close
   authoritative value.

2. **Fallback**: `billing_arr_current` from `/api/accounts/{id}` when no
   snapshot exists for the assessment date.

When using billing snapshots, set `model_checks.uses_billing_arr_source` to
`true`. Set the `arr_source_code` policy code accordingly (default middle:
usually `REV-4`).

For QBR `revenue`: use `recognized_revenue` from the metrics endpoint. This is
monthly recognized revenue, distinct from ARR.

---

## Overdue Balance

```
overdue_balance = ar_aging["61_90"] + ar_aging["90_plus"]
```

The 1-30 and 31-60 buckets are current-to-moderately-late; only 61+ day buckets
constitute "overdue" for retention purposes.

For A/R records that do NOT match an account in the accounts list: treat them
as `unlinked` entries with `account_id: null`. Their overdue balance is still
real and should be reported.

---

## Clean Ticket Count

```
clean_ticket_count = count of tickets where:
  is_spam == false AND is_duplicate == false
```

Do not filter by status — closed, open, and pending tickets all count toward
support volume. Filter only on quality flags.

---

## SLA Compliance

SLA compliance comes from the metrics endpoint (`sla_compliance` field) as a
percentage already computed. No additional calculation needed.

For SLA degradation flagging, inspect individual tickets from the tickets
endpoint: one or more tickets with `first_response_sla_met: false` OR
`resolution_sla_met: false` in the period qualifies as SLA degradation.

---

## NPS

**For QBR monthly NPS**: use `nps_score` from the metrics endpoint.

**For "latest NPS" in risk profiles**: use the most recent `score` from
`/api/accounts/{id}/nps` where `retracted` is `false`. Fall back to the
most recent non-null `nps_score` from the metrics endpoint if the NPS endpoint
has no valid responses.

**NPS drop detection**: compare the latest valid NPS to the previous valid NPS
(same source endpoint). A drop of 20+ points OR a latest score below 35 triggers
the `nps_drop` reason code.

**Peak NPS**: the maximum `nps_score` across the analysis months (from metrics).

---

## Usage Decline

Compute from the metrics endpoint `product_usage` field. If the value drops by
3 or more percentage points from the first month to the last month in the
analysis period, flag `usage_decline`.

---

## Ticket Trend

Compare ticket counts from the first month to the last month of the period:
- Count decreased -> `improving`
- Count increased -> `worsening`
- Count unchanged -> `flat`

Use the `support_ticket_count` from the metrics endpoint (not the raw ticket
list, since metrics already aggregates by month).

---

## Renewal Window

An account is in the renewal window when its `renewal_date` falls within 90 days
before or after the assessment date. Accounts renewing soon need attention;
accounts that recently renewed but still show risk signals are also flagged.

---

## Risk Scoring Rubric

Build `risk_score` (integer 0-100) as a composite. The rubric below is derived
from the train evidence and should be applied consistently:

**Base signals (additive, up to 100):**

| Signal | Points |
|---|---|
| Overdue balance > 0 | +35 |
| NPS below 35 or dropped 20+ points | +25 |
| SLA degradation (any breach in period) | +20 |
| Usage decline >= 3pp | +10 |
| Low tenure (<= 18 months) AND other signals present | +15 |
| In renewal window (within 90 days) | +15 |
| Expansion pipeline > 0 (offset, not risk) | -10 (mitigates) |

**Cap at 100, floor at 0.** The expansion offset reduces risk because it
represents commercial engagement that may anchor the account.

**Risk level mapping:**

| Risk score | Risk level |
|---|---|
| 80-100 | `critical` |
| 40-79 | `high` |
| 20-39 | `medium` |
| 0-19 | `low` |

When multiple accounts share the same risk score, rank by current_arr descending
as the tiebreaker.

---

## Account Matching for A/R

Given an A/R record with `customer_name`, determine link status:

1. Collect all accounts (from `/api/accounts`).
2. For each account, build a match set: `legal_name` plus every entry in
   `account_aliases`.
3. Normalize both sides: lowercase, strip trailing whitespace and periods.
4. If the A/R `customer_name` (normalized) is an exact match for any entry in
   any account's match set, the record is `linked` with that `account_id`.
5. Otherwise `unlinked` with `account_id: null`.

The matching is name-based and some A/R customers simply are not CRM accounts.

---

## Win Rate

```
win_rate_pct = (won_count / (won_count + lost_count)) * 100
```

Rounded to 1 decimal place. Only count closed opportunities (`state: "closed"`)
with stages `"Closed Won"` or `"Closed Lost"`.

---

## Segment Classification

For segment summaries:

- `strategic_accounts`: count of accounts with `segment: "Strategic"`
- `enterprise_accounts`: count of accounts with `segment: "Enterprise"`,
  `"Mid-Market"`, or `"Scale"` (everything non-Strategic)

---

## arr_at_risk

```
arr_at_risk = sum of current_arr for all accounts whose risk_level is "critical" or "high"
```

---

## Net Revenue Exposure

```
net_revenue_exposure = arr_at_risk - open_expansion_pipeline
```

Positive means more ARR at risk than pipeline can offset.

---

## Average Probability (top 5)

```
average_probability_top5 = mean of predicted_churn_probability for the top 5 ranked candidates
```

Rounded to 3 decimal places.

---

## Top Open Product Line

Among all open opportunities (`state: "open"`), group by `product_line` and sum
`amount`. The product line with the highest total amount is the top open product
line.

---

## Churn Feature Count

Total columns in the train/validation CSV minus `customer_id` (identifier) and
`Churn` (target variable). From the data: 21 total columns - 2 = 19 features.

---

## Churn accuracy_band

Map `accuracy_pct` to the band:
- `below_70`: < 70
- `70_to_79`: 70 to < 80
- `80_to_89`: 80 to < 90
- `90_plus`: >= 90

---

## Churn Tenure Coefficient Direction

Compare average tenure of churners (Churn = "Yes") vs non-churners (Churn = "No")
in the training data. If churners have lower average tenure, the direction is
`negative` (the standard pattern — longer tenure reduces churn risk).

---

## Churn Past-Due and Low-Tenure Shortlist Counts

- `past_due_shortlist_count`: number of top-5 candidates with overdue
  receivables (InvoicePastDue = "Yes" in candidates.csv, or determined from
  A/R aging data).
- `low_tenure_shortlist_count`: number of top-5 candidates with
  contract_tenure_months <= 18 and other risk signals present.

---

## Churn Outreach Action Mapping

For each candidate in the ranking, assign `outreach_action`:
- If overdue receivables exist: `collections_followup`
- Else if tenure <= 18 and churn probability is above cohort median: `renewal_save`
- Else if SLA or usage issues exist: `technical_recovery`
- Otherwise: `nurture_monitor`

## Churn Reason Code Mapping

One per candidate, pick the most dominant signal:
- `overdue_receivable` if past-due
- `low_tenure_high_churn` if tenure <= 18 and no past-due
- `sla_degradation` if SLA breaches exist
- `nps_drop` if NPS is low
- `usage_decline` if usage dropped
- `renewal_window` if renewing soon
- `expansion_offset` if expansion pipeline exists
- `clean_billings` if none of the above and billing is clean
