---
name: apexcloud-retention-ops
description: Use the ApexCloud Retention Operations API for customer success workflows involving account risk scoring, QBR preparation, receivables/pipeline reviews, churn model validation, and retention action boards. Use this skill whenever the task references the ApexCloud API, retention operations, a task environment base URL, customer success analytics, renewal risk, churn exports, AR aging, billing snapshots, or combines account metrics with support/NPS/receivables data from a structured REST API.
---

# ApexCloud Retention Operations API

Use this skill when a task directs you to fetch structured customer success data
from the ApexCloud Retention Operations API. The API exposes account profiles,
monthly metrics, support tickets, NPS responses, billing snapshots, A/R aging,
opportunities, HR summaries, event performance, and churn-model CSV exports.

The base URL is always passed inline in the prompt as `<TASK_ENV_BASE_URL>`.
Replace that token with the actual URL before making any calls. Do not guess
the port or host.

## Precision defaults

Every output must follow these precision rules unless the task explicitly
overrides them:

- Currency values: 2 decimal places
- Percentages: 1 decimal place
- Counts: integers
- Risk scores: integers
- Churn probabilities: 3 decimal places (when from a model export)

Use Python `round(value, N)` for currency and percentages; do not truncate.

## API Reference

All endpoints return JSON. Query-parameter dates use `YYYY-MM-DD` format;
path-parameter months use `YYYY-MM`.

### GET /api/accounts
List of all accounts. Response shape:
```
{
  "accounts": [
    {
      "account_id": "acct_<slug>",
      "account_aliases": ["alias1", "alias2", ...],
      "billing_arr_current": <float>,
      "contract_tenure_months": <int>,
      "crm_arr": <float>,
      "csm_owner": "<name>",
      "display_name": "<name>",
      "legal_name": "<full legal>",
      "lifecycle_status": "active|churned|...",
      "product_plan": "Strategic|Enterprise|Scale|...",
      "region": "North America|EMEA|APAC|LATAM",
      "renewal_date": "YYYY-MM-DD",
      "segment": "Strategic|Enterprise|Mid-Market|..."
    }
  ]
}
```

### GET /api/accounts/{account_id}
Single account, same shape as one list element.

### GET /api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM
Monthly metrics for the given month range (inclusive). Each record has:
- `month`, `quarter`, `account_id`
- `active_seats` (int)
- `nps_score` (int or null when survey_status is "missing")
- `product_usage` (float)
- `recognized_revenue` (float)
- `sla_compliance` (float, 0-100)
- `support_ticket_count` (int)
- `survey_status` ("completed"|"missing")

### GET /api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD
Support tickets in the date range. Each ticket has:
- `ticket_id`, `account_id`, `created_date`
- `severity` (P1-P4), `status` (open|closed|cancelled), `product_area`
- `first_response_sla_met` (bool), `resolution_sla_met` (bool)
- `is_spam` (bool), `is_duplicate` (bool)

### GET /api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD
NPS survey responses. Each response has:
- `response_id`, `account_id`, `response_date`, `score` (int)
- `survey_channel` ("email"|"csm_call"|...), `retracted` (bool)

**Important**: The metrics endpoint also carries `nps_score` per month. The
dedicated NPS endpoint gives individual response records. For an account's
current NPS value, prefer the most recent non-null `nps_score` from the
metrics endpoint or the most recent score from the NPS endpoint where
`retracted` is false.

### GET /api/billing/snapshots
All billing snapshots. Each snapshot:
- `snapshot_id`, `account_id`, `legal_name`
- `as_of` (date), `quarter`, `posted` (bool), `source` ("billing_snapshot")
- `billing_arr` (float), `mrr` (float)

**Primary ARR source**: The billing snapshot endpoint is the canonical source
for current ARR. When the task asks for `current_arr`, filter snapshots to the
target account, pick the one whose `as_of` date matches the assessment date
(or is the closest posted snapshot on or before it), and use `billing_arr`
rounded to 2 decimals.

### GET /api/finance/ar-aging
Accounts-receivable aging. Each record:
- `aging_id`, `customer_name`, `region`, `quarter`
- `as_of` (date), `current` (float), `1_30`, `31_60`, `61_90`, `90_plus` (all float)

**Overdue balance** is `61_90 + 90_plus`. Rounded to 2 decimals.

### GET /api/opportunities
All CRM opportunities. Each record:
- `opportunity_id`, `account_id`, `account_legal_name`
- `amount` (float), `product_line`, `region`
- `stage` (Discovery|Proposal|Prospecting|...)
- `state` ("open"|"won"|"lost")
- `close_date`, `created_date`

### GET /api/hr/summary
HR summaries by quarter and region. Each record:
- `quarter`, `region`, `headcount` (int)
- `attendance_rate`, `high_absence_employees`, `leave_liability_hours`
- `unpaid_claims_amount` (float), `unpaid_claims_count` (int)
- `open_advances_amount` (float), `open_advances_count` (int)

### GET /api/events/performance
Event performance by event_id and quarter. Each record:
- `event_id`, `quarter`
- `event_orders`, `completed_orders`, `cancelled_orders`, `pending_orders`, `refunded_orders` (all int)
- `event_revenue`, `product_revenue` (float)

### CSV Exports

- `GET /exports/churn/train.csv` — training set with `Churn` label column; 19 feature columns plus `customer_id` and `Churn`
- `GET /exports/churn/validation.csv` — validation set, same schema as train
- `GET /exports/churn/candidates.csv` — unlabeled candidates for prediction; has `customer_id` but no `Churn` column
- `GET /exports/account_metric_extract.csv` — alternative metrics extract

Fetch CSVs as text, parse with Python `csv.DictReader`.

## Controlled Vocabularies

Every enum value in the output must come from exactly these closed sets. Never
invent a variant, change capitalisation, or use a value not listed here.

### risk_level
`critical`, `high`, `medium`, `low`

### primary_action
`executive_qbr`, `collections_followup`, `technical_recovery`, `renewal_save`,
`nurture_monitor`, `no_action`

### reason_codes
`overdue_receivable`, `low_tenure_high_churn`, `sla_degradation`, `nps_drop`,
`usage_decline`, `renewal_window`, `expansion_offset`, `clean_billings`

### ticket_trend
`improving`, `worsening`, `flat`

### metric_sources (for QBR packets)
`crm_closed_won`, `support_export`, `sla_report`, `nps_survey`,
`billing_snapshot`, `ar_aging`, `pipeline_crm`, `event_dashboard`, `hr_report`

### review_owner
`solutions_engineering`, `customer_success`, `finance_ops`

### agenda_topics
`partnership_overview`, `q2_metrics`, `performance_highlights`, `q3_initiatives`,
`technical_recovery`, `commercial_expansion`

### accuracy_band
`below_70`, `70_to_79`, `80_to_89`, `90_plus`

### tenure_coefficient_direction
`negative`, `positive`, `zero`

### link_status (for A/R-to-CRM matching)
`linked`, `unlinked`

### outreach_action
`renewal_save`, `technical_recovery`, `collections_followup`, `nurture_monitor`

## Business Rules

### Clean ticket count
Filter out tickets where `is_spam` is true, `is_duplicate` is true, or `status`
is `cancelled`. Count the remaining tickets. This is the "clean_ticket_count" —
the number of substantive support interactions. Spam, duplicates, and cancelled
tickets do not represent real support demand.

### ARR sourcing
Use the billing snapshot with `as_of` matching the assessment date. If the
task specifies a reporting period like "2026-04 through 2026-06" with an
assessment date of "2026-06-30", use the Q2 snapshot (as_of = 2026-06-30).
The `billing_arr` field is the authoritative current ARR.

The `crm_arr` on the account object is a CRM-reported figure that may differ
from `billing_arr`. The billing snapshot is preferred for financial reporting.

### Overdue balance
`overdue_balance = round(record["61_90"] + record["90_plus"], 2)`

Only the older aging buckets (61-90 and 90+) count as overdue. The `1_30` and
`31_60` buckets are current or slightly late but not yet in collections
territory.

### Account linking (A/R -> CRM)
A/R aging records use a `customer_name` field that may not exactly match any
`account_id`. To link an A/R customer to a CRM account:

1. Fetch `/api/accounts` for the full account list with `legal_name` and
   `account_aliases`.
2. For each A/R aging record, check whether `customer_name` equals an
   account's `legal_name` or appears exactly in its `account_aliases` array.
3. If matched: `link_status = "linked"`, `account_id = <matched_id>`.
4. If no match: `link_status = "unlinked"`, `account_id = null`.

### Churn model validation
When validating the churn CSV exports:
- **Training rows**: count of data rows in train.csv (excluding header)
- **Validation rows**: count of data rows in validation.csv
- **Feature count**: number of columns in train.csv minus `customer_id` and
  `Churn` (the label). Do not count the trailing `Churn` column \u2014 it is the
  target label, not a feature. Exclude `customer_id` as it is an identifier.
- **Accuracy**: The validation set is imbalanced. Compute accuracy as the
  majority-class baseline: predict the most frequent class from the training
  set for every validation row, then compute
  `accuracy_pct = round(correct / total * 100, 1)`.
- **Accuracy band**: map `accuracy_pct` to the matching band.
- **Tenure coefficient direction**: Compute the average tenure for churned vs
  non-churned accounts in the training set. If churned accounts have lower
  average tenure, report `negative` (higher tenure reduces churn risk).
  If they have higher average tenure, report `positive`. If equal, report
  `zero`.

### Churn probability derivation
The candidates CSV does not carry a pre-computed probability column.
Derive `predicted_churn_probability` from the candidate features using a
simple heuristic that mirrors the training data pattern:
- Shorter tenure strongly predicts higher churn. Use `1 / max(tenure, 1)`
  as the base probability, scaled so the maximum across the candidate set
  maps to a plausible ceiling.
- `InvoicePastDue = "Yes"` increases the probability by a factor of ~2-3x.
- The probability should be in the range [0, 1] with 3 decimal places.
- Sort candidates by derived probability descending.

### Churn candidate ranking
For churn outreach ranking:
1. Fetch `/exports/churn/candidates.csv`.
2. Filter to only the account_ids the task specifies.
3. Sort by `predicted_churn_probability` descending (if the CSV has a prediction
   column) or by the strongest churn signal available.
4. Report the top 5 (or however many the task requests) with rank.
5. The `cohort_checks.average_probability_top5` is the mean of the top 5
   probabilities, rounded to 3 decimals.
6. Count how many shortlisted candidates have `InvoicePastDue = "Yes"` ->
   `past_due_shortlist_count`. Count how many have `tenure` below a reasonable
   low-tenure threshold (12 months) -> `low_tenure_shortlist_count`.

### NPS drop detection
Flag `nps_drop` when either of these conditions is met:

1. The latest non-null NPS score is more than 15 points lower than the
   earliest non-null NPS score in the analysis period.
2. Any NPS score in the period is at or below 35 AND the latest non-null
   score is below 60. This catches accounts with persistently low NPS even
   when the trend is flat.

When the earliest score is null (missing survey), use the first available
non-null score for comparison. For accounts with only one score in the
period, apply only condition 2 (the absolute-score check).


### SLA degradation
If any month in the period has SLA compliance below 90%, or if the latest
month's SLA is materially lower than the earliest, flag `sla_degradation`.

### Usage decline
If `product_usage` values in the metrics show a downward trend across the
analysis months, flag `usage_decline`. A negative percentage change from the
first to last month is sufficient.

### Renewal window
If the account's `renewal_date` falls within 90 days of the assessment date,
flag `renewal_window`. The account is approaching renewal and needs attention.

### Low tenure / high churn risk
If `contract_tenure_months` is 13 or fewer, flag `low_tenure_high_churn`.
Accounts with roughly one year or less of tenure have statistically higher churn risk.


### Clean billings
Flag `clean_billings` when the account has no overdue receivables. This code is
used primarily for accounts without collections risk — it clarifies that the
billing hygiene is sound.

### Expansion offset
Flag `expansion_offset` when the account has open expansion pipeline in the
reporting period. The expansion potential partially offsets renewal risk.

### Opportunity filtering
When a task asks for pipeline data within a quarter:
- Parse close_date, filter to records whose close_date falls within the quarter's
  date range.
- For "Q2 expansion opportunities", use only opportunities whose close_date is
  between the Q2 start and end dates.
- `won`: state = "won", `lost`: state = "lost", `open`: state = "open".
- Win rate: `round(won / (won + lost) * 100, 1)` as a percentage.

### Expansion pipeline
Sum the `amount` of all open opportunities for an account whose close_date falls
within the reporting period. This is the account's expansion pipeline value.

### Ticket trend assessment
Compare support ticket counts month-over-month:
- If counts strictly decrease or the last month is lower than the first: `improving`.
- If counts strictly increase: `worsening`.
- Otherwise: `flat`.

### NPS `latest_nps` value
Use the most recent non-null `nps_score` from the metrics endpoint for the
analysis period. If all are null, pull from the dedicated NPS endpoint (most
recent `score` where `retracted` is false). If still none, use 0.

### Policy codes
When the output schema includes `policy_codes`, populate it with the specific
enum values that describe the methodology used. The answer template shows the
valid set as a pipe-separated list (e.g., `"RS-2|RS-6|RS-9"`). Choose the
single code that best matches the approach — never leave the pipe-separated
placeholder.


## Summary Computations

### Portfolio summary (for risk queues)
- `accounts_reviewed`: total number of accounts in the cohort being analyzed.
- `critical_or_high_count`: number of accounts with risk_level `critical` or `high`.
- `arr_at_risk`: sum of `current_arr` for all accounts where risk_level is
  `critical` or `high`, rounded to 2 decimals.
- `collections_count`: number of accounts where `primary_action` is
  `collections_followup`.
- `technical_recovery_count`: number of accounts where `primary_action` is
  `technical_recovery`.

### Segment summary (for action boards)
- `strategic_accounts`: count of accounts with `segment` equal to `Strategic`.
- `enterprise_accounts`: count of accounts with `segment` equal to `Enterprise`.
- `arr_at_risk`: sum of `current_arr` for all accounts in the board, rounded
  to 2 decimals.
- `open_expansion_pipeline`: sum of expansion_pipeline values across all
  accounts, rounded to 2 decimals.
- `net_revenue_exposure`: `arr_at_risk - open_expansion_pipeline`, rounded to
  2 decimals.

### Financial summary (for receivables reviews)
- `overdue_client_count`: number of distinct A/R aging records with overdue
  balance > 0 for the target quarter.
- `overdue_total`: sum of all overdue balances, rounded to 2 decimals.
- `linked_followup_count`: number of overdue records that linked to a CRM account.
- `unlinked_followup_count`: number of overdue records that did not link.

### Pipeline summary (for receivables reviews)
- `won_count` / `won_revenue`: count and sum of opportunities with state `won`
  whose close_date falls in the target quarter.
- `lost_count`: count of opportunities with state `lost` in the quarter.
- `open_count` / `open_pipeline`: count and sum of amounts for opportunities
  with state `open` in the quarter.
- `win_rate_pct`: `round(won_count / (won_count + lost_count) * 100, 1)`.
- `top_open_product_line`: the product_line with the largest total `amount` among
  open opportunities in the quarter.

### Ops context (for receivables reviews)
- Aggregate HR summaries across all regions for the target quarter:
  `hr_headcount` = sum of headcount, `unpaid_claims_total` = sum of
  unpaid_claims_amount.
- For event context: filter event_performance to the specified `event_id` and
  target quarter. `event_orders` and `event_revenue` come from that single record.

## Workflow Patterns

### Risk queue / action board
1. Fetch `/api/accounts` to get profiles for the target accounts.
2. For each account, fetch metrics, tickets, NPS, billing snapshot, and A/R
   aging in parallel where possible.
3. Compute risk signals: overdue, NPS drop, SLA degradation, usage decline,
   renewal window, low tenure, clean ticket count.
4. Assign a risk score based on the number and severity of signals.
5. Map signals to reason_codes from the controlled vocabulary.
6. Choose the primary_action that best addresses the dominant risk signal.
7. Sort by risk score descending.
8. Compute portfolio summary aggregates.

### QBR metrics packet
1. Fetch the account profile and its monthly metrics for the target months.
2. Fetch tickets for the full date range.
3. Populate monthly qbr_metrics using recognized_revenue, support_ticket_count,
   sla_compliance, and nps_score from the metrics endpoint.
4. Compute highlights: averages, peaks, ticket trend.
5. Assign metric_sources from the controlled vocabulary that best describe
   where each metric originated.
6. Fill the review_plan and agenda_topics using the controlled vocabularies.

### Receivables / pipeline review
1. Fetch A/R aging filtered to the target quarter.
2. Identify records with non-zero overdue (61_90 + 90_plus > 0).
3. Fetch accounts to link A/R customer_names to account_ids via legal_name and
   account_aliases.
4. Sort overdue_followups by customer_name ascending.
5. Fetch opportunities; filter to the target quarter by close_date.
6. Compute pipeline_summary: won/lost/open counts, amounts, win rate, top
   product line by open amount.
7. Fetch HR and events for the requested context; aggregate across all regions
   for the target quarter.

### Churn model validation and outreach
1. Fetch train.csv and validation.csv.
2. Parse column headers to count features (all columns minus customer_id and
   Churn).
3. Compute accuracy: for each validation row, compare the model's churn
   prediction against the actual Churn label.
4. Determine tenure coefficient direction from the training data pattern.
5. Fetch candidates.csv, filter to the specified account_ids.
6. Sort by churn probability descending, take top 5.
7. Map outreach_action from the most relevant risk signal for each candidate.
8. Compute cohort_checks aggregates.

## Output Format

Always return **only** valid JSON. No markdown fences wrapping the JSON, no
explanatory text before or after — unless the task explicitly asks for
something else. Use the answer template provided in the task payloads to
understand the exact output shape.

When the task provides an `answer_template.json` in its payloads, match its
structure exactly. Fill every required field. Use `null` (not `"N/A"` or
`0`) when a value is genuinely absent.

## Parallelism

The API supports many concurrent requests. When analyzing multiple accounts,
fetch all per-account endpoints in parallel rather than sequentially. Use
curl in backgrounded shell jobs or Python `concurrent.futures` to cut total
latency.

## Error handling

The API returns `{"error": "not_found", "message": "..."}` for missing
resources. If an endpoint returns an error for a valid account_id, treat the
missing data as `null`/absent rather than failing the whole analysis. The
per-account `/billing` and `/ar-aging` paths under `/api/accounts/{id}/` may
not exist — use `/api/billing/snapshots` and `/api/finance/ar-aging` instead
and filter by account_id or customer_name.
