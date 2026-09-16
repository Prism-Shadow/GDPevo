## Precision and Calculation Rules

### Numeric Precision

| Measure | Precision | Example |
|----------|-----------|---------|
| Currency (ARR, revenue, overdue, amounts) | 2 decimal places | `1500000.00` |
| Percentages (SLA, win rate, accuracy) | 1 decimal place | `95.0` |
| Counts (tickets, seats, accounts) | Integers | `25` |
| Risk scores | Integers | `85` |
| Churn probabilities | 3 decimal places | `0.100` |

### Rounding

Use `round(value, N)` with banker's rounding (Python default). Do not floor or ceil.

### Business Logic Rules

#### ARR Source

- **Primary**: `/api/billing/snapshots` filtered to `as_of` matching the assessment date. Use `billing_arr` from the snapshot.
- **Fallback**: `billing_arr_current` from `/api/accounts` or `/api/accounts/{id}`.
- When using billing snapshots, set `uses_billing_arr_source: true` and `arr_source_code: "REV-4"`.

#### Clean Ticket Count

- Fetch tickets from `/api/accounts/{id}/tickets`.
- **Exclude** tickets where `is_spam == true` OR `is_duplicate == true`.
- Count the remaining tickets.
- This is the "clean" count; use code `SUP-8`.

#### SLA Compliance

- From `/api/accounts/{id}/metrics`, use the `sla_compliance` field directly.
- To check for degradation: any month where `sla_compliance < 90.0` triggers `sla_degradation` reason code.

#### NPS

- Fetch latest NPS from `/api/accounts/{id}/nps`. Exclude retracted responses (`retracted == true`).
- The latest non-retracted score is the `latest_nps`.
- If no NPS responses exist in the period, fall back to the most recent non-null `nps_score` from the metrics endpoint.
- `nps_drop` reason code triggers when latest NPS < 50 OR a month-over-month NPS decline of at least 10 points is observed.

#### Overdue Balance

- Use `/api/finance/ar-aging`. Match by `customer_name` to account `legal_name` or `account_aliases`.
- Overdue = `31_60 + 61_90 + 90_plus`. Do NOT include `1_30` or `current`.
- Use the aging record whose `as_of` matches the task's A/R as-of date.

#### Renewal Window

- `renewal_date` is within **90 days** of the assessment date triggers `renewal_window` reason code.
- Compute as: `(renewal_date - assessment_date).days <= 90 AND renewal_date >= assessment_date`.

#### Low Tenure + Churn Risk

- `contract_tenure_months <= 24` AND other risk factors present triggers `low_tenure_high_churn`.
- Tenure risk direction is `negative` when higher tenure correlates with lower risk.

#### Usage Decline

- Product usage values across months show a downward trend.
- Use linear regression slope on `product_usage` values or check: last month < first month by a meaningful margin.

#### Expansion Offset

- An open opportunity exists for the account with `close_date` within the analysis period.
- Filter `/api/opportunities` by account_id, `state == "open"`, and close_date within the period range.

#### Clean Billings

- Overdue balance == 0.00 gives `clean_billings` reason code (positive signal).

#### ARR at Risk

- Sum of `current_arr` for all accounts in the portfolio with risk_level == `critical` OR `high`.

#### Net Revenue Exposure

- `arr_at_risk - open_expansion_pipeline` (code `EXP-6`).

#### Strategic vs Enterprise Counts

- `strategic_accounts`: count of accounts with `segment == "Strategic"` in the portfolio.
- `enterprise_accounts`: count of accounts with `segment == "Enterprise"` or `segment == "Mid-Market"`.

### Churn Model Procedures

#### Training and Validation

1. Load `/exports/churn/train.csv` and `/exports/churn/validation.csv`.
2. Features: all columns except `customer_id` and `Churn`.
3. One-hot encode categorical features. Leave numeric features unscaled.
4. Fit `sklearn.linear_model.LogisticRegression(solver='lbfgs', max_iter=1000)`.
5. Evaluate accuracy on validation set.
6. Extract the `tenure` coefficient to determine `tenure_coefficient_direction`.

#### Candidate Scoring

1. Load `/exports/churn/candidates.csv`.
2. Apply the same encoding as training.
3. Use `model.predict_proba()` for churn probabilities.
4. Filter to specified candidate account_ids only.
5. Rank by probability descending, take top 5.

#### Outreach Mapping (OUT-2)

1. If `InvoicePastDue == "Yes"` then `collections_followup`, reason `overdue_receivable`.
2. Else if `tenure <= 24` and probability is top-ranked then `renewal_save`, reason `low_tenure_high_churn`.
3. Else `nurture_monitor`, reason `clean_billings`.

#### Cohort Checks

- `past_due_shortlist_count`: top-5 count where InvoicePastDue == "Yes".
- `low_tenure_shortlist_count`: top-5 count where tenure <= 24.
- `average_probability_top5`: mean of the 5 predicted probabilities.

### Cross-Entity Name Matching

1. Load all accounts from `/api/accounts`.
2. For each A/R `customer_name`, check if it matches any account's `legal_name` OR is in `account_aliases`.
3. Match = `"linked"` with `account_id` populated. No match = `"unlinked"` with `account_id: null`.

### Policy Code Selection Summary

| Domain | Code | When |
|--------|------|------|
| Risk model | `RS-6` | Composite scoring (ARR, tenure, NPS, SLA, overdue, usage, renewal) |
| Risk model | `RS-9` | Churn probability via logistic regression |
| ARR source | `REV-4` | Billing snapshots used as primary source |
| Support hygiene | `SUP-8` | Clean ticket count (spam/duplicates excluded) |
| Action priority | `ACT-5` | Composite: risk score then ARR then overdue |
| CRM match | `CM-5` | Legal name or alias match |
| Pipeline window | `PW-6` | Quarter-matched close dates |
| Followup scope | `FS-4` | All overdue, sorted by customer_name |
| Receivable trigger | `RCP-7` | 31-60 + 61-90 + 90+ combined |
| Board sort | `BORD-4` | Risk severity then ARR descending |
| Exposure formula | `EXP-6` | Net exposure (ARR minus pipeline) |
| Calendar policy | `CAL-5` | Per-action tiered due dates |
| Model protocol | `MOD-7` | Logistic regression with one-hot encoding |
| Probability scale | `PRB-4` | sklearn predict_proba |
| Deployment rule | `DEP-5` | Ranked list, no fixed threshold |
| Outreach mapping | `OUT-2` | InvoicePastDue then low_tenure then nurture |
