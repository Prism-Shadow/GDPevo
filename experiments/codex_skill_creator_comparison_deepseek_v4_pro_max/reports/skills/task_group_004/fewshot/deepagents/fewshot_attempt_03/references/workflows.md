# Workflows

Step-by-step procedures for each ApexCloud retention analysis type. Every workflow follows the same pattern: fetch data, reconcile sources, compute aggregates, assign controlled vocabularies, and return JSON.

## 1. Renewal Risk Queue

**When the task asks to:** rank accounts by renewal risk, produce a risk queue, or build a retention risk report for a list of account_ids.

### Step 1: Fetch Account Profiles

```
GET /api/accounts
```

Filter to only the specified account_ids. Extract for each: `account_id`, `billing_arr_current`, `contract_tenure_months`, `renewal_date`, `lifecycle_status`, `segment`, `product_plan`, `legal_name`, `account_aliases`.

### Step 2: Fetch Account Metrics

For each account_id:
```
GET /api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM
```

Extract per-month: `recognized_revenue`, `sla_compliance`, `nps_score`, `product_usage`.

### Step 3: Fetch Support Tickets

For each account_id:
```
GET /api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD
```

Compute clean ticket count: filter `is_duplicate=false AND is_spam=false`, count remaining.

### Step 4: Fetch NPS Responses

For each account_id:
```
GET /api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD
```

Get latest NPS: sort by `response_date` descending, take first non-null `score` where `retracted=false`.

### Step 5: Fetch A/R Aging

```
GET /api/finance/ar-aging
```

Filter to the as-of date specified in the task. Match `customer_name` against the account's `legal_name` and `account_aliases`. Compute `overdue_balance = 31_60 + 61_90 + 90_plus`.

### Step 6: Compute Risk Scores

See output_conventions.md for the composite risk model. Compute for each account.

### Step 7: Assign Fields

For each account, assign:
- `risk_level`: from risk score tier
- `primary_action`: using priority ordering (collections_followup if overdue > 0, else technical_recovery if SLA/usage issues, else renewal_save if in renewal window, else nurture_monitor)
- `reason_codes`: all applicable codes, ordered by severity
- `current_arr`: from `billing_arr_current`
- `latest_nps`: from step 4
- `clean_ticket_count`: from step 3
- `overdue_balance`: from step 5

### Step 8: Rank and Select Top 5

Sort by risk_score descending, then current_arr descending. Take top 5.

### Step 9: Compute Portfolio Summary

- `accounts_reviewed`: total number of account_ids in the task
- `critical_or_high_count`: count of top-5 accounts with risk_level critical or high
- `arr_at_risk`: sum of current_arr for all reviewed accounts (not just top 5)
- `collections_count`: count of top-5 accounts with primary_action collections_followup
- `technical_recovery_count`: count of top-5 accounts with primary_action technical_recovery

### Step 10: Model Checks

- `uses_billing_arr_source`: true (when using billing_arr_current)
- `tenure_risk_direction`: "negative" (lower tenure = higher risk)

### Step 11: Policy Codes

Select from controlled_vocabularies.md based on methodology used. Standard: `RS-6`, `REV-4`, `SUP-8`, `ACT-5`.

### Step 12: Assemble JSON

Build the final object with keys: `risk_accounts`, `portfolio_summary`, `model_checks`, `policy_codes`.

---

## 2. QBR Metrics Packet

**When the task asks to:** build a QBR packet, quarterly business review metrics, or monthly breakdown for a single account.

### Step 1: Fetch Account Metrics

```
GET /api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM
```

Extract per month: `recognized_revenue`, `sla_compliance`, `nps_score`.

### Step 2: Fetch Support Tickets

```
GET /api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD
```

Filter and count clean tickets per month (by `created_date` month).

### Step 3: Build Monthly Arrays

For each month in the analysis period, create a `qbr_metrics` entry:
- `month`: "YYYY-MM"
- `revenue`: `recognized_revenue` from metrics
- `support_tickets`: clean ticket count for that month
- `sla_compliance_pct`: `sla_compliance` from metrics (already 1 decimal)
- `nps_score`: `nps_score` from metrics (may be null)

### Step 4: Compute Highlights

- `average_revenue`: mean of monthly revenue values, rounded to 2 decimals
- `peak_revenue_month`: month with highest revenue
- `peak_revenue`: that month's revenue value
- `max_sla_month`: month with highest sla_compliance
- `max_sla_pct`: that month's sla_compliance value
- `peak_nps_month`: month with highest nps_score (ignore nulls)
- `peak_nps_score`: that month's nps_score
- `ticket_trend`: compare first month clean count to last month clean count (improving if decreasing, worsening if increasing, flat if same)

### Step 5: Assign Metric Sources

- `revenue`: "crm_closed_won"
- `support_tickets`: "support_export"
- `sla_compliance`: "sla_report"
- `nps`: "nps_survey"

### Step 6: Build Review Plan

- `review_owner`: "customer_success"
- `review_due_date`: from task prompt (default "2026-07-22")
- `needs_technical_signoff`: false (unless account has SLA issues)

### Step 7: Select Agenda Topics

Choose exactly four from the agenda topic vocabulary:
- Canonical: "partnership_overview", "q2_metrics", "technical_recovery", "q3_initiatives"
- If account has no technical issues, swap "technical_recovery" for "commercial_expansion" or "performance_highlights"

### Step 8: Assemble JSON

Build the final object with keys: `qbr_metrics`, `highlights`, `metric_sources`, `review_plan`, `agenda_topics`.

---

## 3. Receivables and Pipeline Operations Review

**When the task asks to:** prepare a receivables review, A/R + pipeline operations review, or Q3 receivables and pipeline report.

### Step 1: Fetch A/R Aging

```
GET /api/finance/ar-aging
```

Filter to the specified quarter. Compute overdue balance for each entry: `31_60 + 61_90 + 90_plus`. Keep only entries with `overdue > 0`.

### Step 2: Fetch All Accounts

```
GET /api/accounts
```

Build a lookup map: for each account, collect `legal_name` and all `account_aliases`.

### Step 3: Link A/R to CRM

For each overdue A/R entry:
- Match `customer_name` against account `legal_name` (exact match) and `account_aliases` (case-insensitive substring or exact match)
- If matched: `link_status = "linked"`, set `account_id`
- If not matched: `link_status = "unlinked"`, `account_id = null`

### Step 4: Sort Followups

Sort overdue followups by `customer_name` ascending (case-insensitive alphabetical).

### Step 5: Build Financial Summary

- `overdue_client_count`: number of overdue A/R entries
- `overdue_total`: sum of all overdue balances
- `linked_followup_count`: count of linked entries
- `unlinked_followup_count`: count of unlinked entries

### Step 6: Fetch Pipeline

```
GET /api/opportunities
```

Filter by the specified quarter's date range (close_date within range). Compute:
- `won_count`, `won_revenue`: state=won, sum amount
- `lost_count`: state=lost
- `open_count`, `open_pipeline`: state=open, sum amount
- `win_rate_pct`: won_count / (won_count + lost_count) * 100, 1 decimal
- `top_open_product_line`: most frequent product_line among open opps (alphabetical tiebreak)

### Step 7: Fetch HR Context

```
GET /api/hr/summary
```

Filter by the specified quarter, sum across all regions:
- `hr_headcount`: sum of headcount
- `unpaid_claims_total`: sum of unpaid_claims_amount

### Step 8: Fetch Event Context

```
GET /api/events/performance
```

Filter by the specified event_id and quarter:
- `event_orders`
- `event_revenue`

### Step 9: Assign Policy Codes

Standard: `RCP-7`, `CM-5`, `PW-6`, `FS-4`.

### Step 10: Assemble JSON

Build the final object with keys: `financial_summary`, `pipeline_summary`, `overdue_followups`, `ops_context`, `policy_codes`.

---

## 4. Churn Model Validation and Outreach Ranking

**When the task asks to:** validate churn model exports, produce an outreach ranking, or evaluate churn predictions.

### Step 1: Fetch Training Data

```
GET /exports/churn/train.csv
```

Count rows (excluding header): `training_rows`. Count features: exclude `customer_id` and `Churn` = 19 features.

### Step 2: Fetch Validation Data

```
GET /exports/churn/validation.csv
```

Count rows: `validation_rows`.

### Step 3: Compute Accuracy

Parse validation CSV. The `Churn` column is the ground truth. Compute accuracy from the validation set data. The `accuracy_pct` should be the percentage of correct predictions (1 decimal).

### Step 4: Determine Accuracy Band

- `< 70`: "below_70"
- `70-79.9`: "70_to_79"
- `80-89.9`: "80_to_89"
- `>= 90`: "90_plus"

### Step 5: Tenure Coefficient Direction

Always "negative" (lower tenure = higher churn risk in this domain).

### Step 6: Fetch Candidate Data

```
GET /exports/churn/candidates.csv
```

Filter to only the specified account_ids (match on `customer_id` field).

### Step 7: Rank by Churn Probability

Parse the candidate CSV and derive predicted churn probabilities. Sort by probability descending. Take top 5.

### Step 8: Assign Outreach Actions

For each top-5 candidate:
- `rank`: 1-5
- `customer_id`: from CSV
- `predicted_churn_probability`: 3 decimal places
- `outreach_action`: map probability to action (highest probabilities = collections_followup if past due, renewal_save if low tenure, nurture_monitor for low probabilities)
- `reason_code`: based on candidate's data (InvoicePastDue=Yes → overdue_receivable, low tenure → low_tenure_high_churn, clean billings → clean_billings)

### Step 9: Compute Cohort Checks

- `past_due_shortlist_count`: among top 5, count with InvoicePastDue=Yes
- `low_tenure_shortlist_count`: among top 5, count with tenure <= 12
- `average_probability_top5`: mean of top 5 probabilities, 3 decimals

### Step 10: Assign Policy Codes

Standard: `MOD-7`, `PRB-4`, `DEP-5`, `OUT-2`.

### Step 11: Assemble JSON

Build the final object with keys: `model_validation`, `risk_ranking`, `cohort_checks`, `model_policy_codes`.

---

## 5. High-Touch Retention Operations Board

**When the task asks to:** build a retention action board, high-touch retention board, or operating review board for the CS leadership team.

### Step 1: Fetch Account Profiles

```
GET /api/accounts
```

Filter to the specified account_ids. Extract all profile fields.

### Step 2: Fetch Account Metrics

For each account_id:
```
GET /api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM
```

Extract per-month SLA and usage data.

### Step 3: Fetch Support Tickets

For each account_id:
```
GET /api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD
```

Compute clean ticket counts and SLA from tickets.

### Step 4: Fetch NPS Responses

For each account_id:
```
GET /api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD
```

Get latest NPS scores.

### Step 5: Fetch A/R Aging

```
GET /api/finance/ar-aging
```

Filter to the as-of date. Match by customer_name to account aliases/legal_name. Compute overdue balances.

### Step 6: Fetch Billing Snapshots

```
GET /api/billing/snapshots
```

Filter to the as-of date for each account. Use `billing_arr` as fallback for current_arr.

### Step 7: Fetch Expansion Opportunities

```
GET /api/opportunities
```

For each account_id, sum `amount` where `state=open` and `close_date` within analysis period. This is `expansion_pipeline`.

### Step 8: Compute Risk and Assign Fields

For each account, compute risk_score using the composite model. Assign:
- `risk_level`: from score tier
- `primary_action`: using priority ordering
- `current_arr`: from billing_arr_current
- `expansion_pipeline`: from step 7
- `overdue_balance`: from step 5
- `next_touch_due_date`: from the followup calendar in the task prompt, based on primary_action
- `reason_codes`: all applicable codes

### Step 9: Sort the Board

Sort by risk severity: critical > high > medium > low. Within each tier, sort by current_arr descending.

### Step 10: Assign Ranks

Sequential 1, 2, 3, ... after sorting.

### Step 11: Compute Segment Summary

- `strategic_accounts`: count of reviewed accounts with segment=Strategic
- `enterprise_accounts`: count with segment=Enterprise, Mid-Market, or SMB
- `arr_at_risk`: sum of current_arr for all reviewed accounts
- `open_expansion_pipeline`: sum of expansion_pipeline across all accounts
- `net_revenue_exposure`: arr_at_risk - open_expansion_pipeline

### Step 12: Build Followup Calendar

Use the dates provided in the task prompt:
- `collections_followup`: task-specified date
- `technical_recovery`: task-specified date
- `renewal_save`: task-specified date
- `executive_qbr`: task-specified date
- `nurture_monitor`: task-specified date

### Step 13: Assign Policy Codes

Standard: `RS-6`, `REV-4`, `SUP-8`, `ACT-5`, `BORD-4`, `EXP-6`, `CAL-5`.

### Step 14: Assemble JSON

Build the final object with keys: `action_board`, `segment_summary`, `followup_calendar`, `policy_codes`.
