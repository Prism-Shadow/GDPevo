 # ApexCloud Retention Operations Skill

 ## Overview

 This skill covers the ApexCloud Retention Operations API, a multi-tenant customer success platform. It provides patterns for querying account data, building retention risk assessments, constructing QBR metrics packets, processing receivables reviews, validating churn models, and assembling high-touch retention action boards.

 ## API Conventions

 - **Base URL**: `{TASK_ENV_BASE_URL}` (no trailing slash).
 - **Auth**: No headers required for GET endpoints.
 - **Query strings**: Most list endpoints accept `?start=YYYY-MM-DD&end=YYYY-MM-DD` or `?start=YYYY-MM&end=YYYY-MM` date-range filters.
 - **Response shapes**: Endpoints return JSON objects; list results are nested under a parent key (e.g., `metrics`, `tickets`, `nps_responses`, `ar_aging`, `snapshots`, `opportunities`, `event_performance`, `hr_summary`).

 ### Core Endpoint Families

 | Endpoint | Purpose | Notes |
 |---|---|---|
 | `GET /api/accounts` | List all CRM accounts | Used for account name → ID mapping |
 | `GET /api/accounts/{id}` | Single account profile | Contains `billing_arr_current`, `crm_arr`, `contract_tenure_months`, `lifecycle_status`, `renewal_date`, `segment`, `region`, `product_plan`, `legal_name`, `display_name`, `account_aliases` |
 | `GET /api/accounts/{id}/metrics?start=YYYY-MM&end=YYYY-MM` | Monthly operational metrics | Returns `recognized_revenue`, `support_ticket_count`, `sla_compliance`, `nps_score`, `product_usage`, `active_seats`, `survey_status`, `quarter`, `month` |
 | `GET /api/accounts/{id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` | Support tickets | Fields: `ticket_id`, `is_spam`, `is_duplicate`, `first_response_sla_met`, `resolution_sla_met`, `severity`, `status`, `product_area`, `created_date` |
 | `GET /api/accounts/{id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` | NPS survey responses | Fields: `response_id`, `score`, `retracted`, `survey_channel`, `response_date` |
 | `GET /api/billing/snapshots` | Quarterly billing snapshots | Contains `billing_arr`, `mrr`, `as_of`, `snapshot_id`, `source`, `posted` |
 | `GET /api/finance/ar-aging` | Accounts receivable aging | Contains `customer_name`, `as_of`, `quarter`, `current`, `1_30`, `31_60`, `61_90`, `90_plus`, `aging_id`, `region` |
 | `GET /api/opportunities` | CRM pipeline opportunities | Fields: `account_id`, `amount`, `stage`, `close_date`, `product_line`, `opportunity_id` |
 | `GET /api/hr/summary` | HR operational data | Fields: `quarter`, `region`, `headcount`, `unpaid_claims_amount`, `unpaid_claims_count` |
 | `GET /api/events/performance` | Event performance metrics | Fields: `event_id`, `quarter`, `event_orders`, `event_revenue` |
 | `GET /exports/churn/train.csv` | Churn model training export | CSV with customer_id, features, and Churn target |
 | `GET /exports/churn/validation.csv` | Churn model validation export | Same schema as train.csv |
 | `GET /exports/churn/candidates.csv` | Candidate accounts for churn scoring | Same feature columns, no Churn target |

 ## Data Cleaning Rules

 ### Tickets

 Exclude tickets where `is_spam` is `true` OR `is_duplicate` is `true` when computing clean/actionable ticket counts. Use raw counts only when the task explicitly asks for totals.

 ### NPS

 Exclude responses where `retracted` is `true`. The latest valid (non-retracted) score by `response_date` is the canonical latest NPS for an account.

 ### AR Aging: Real vs. Noise Customers

 The `/api/finance/ar-aging` endpoint returns entries for real CRM accounts AND noise/distractor entries. Identify noise entries by:
- `aging_id` contains the substring `noise-`
- The `customer_name` does NOT match any `legal_name`, `display_name`, or `account_alias` in `/api/accounts`

 Only real (linked) entries should be associated with CRM `account_id` values. Noise entries get `link_status: "unlinked"` and `account_id: null`.

 ### Account Name Matching

 Build a lookup from `/api/accounts` using all three fields: `legal_name` (case-insensitive), `display_name` (case-insensitive), and every entry in `account_aliases` (case-insensitive). Use this to match AR `customer_name` strings to account IDs.

 ## Risk Assessment Methodology

 When ranking accounts by renewal or retention risk, weigh these dimensions:

 1. **Lifecycle status**: `renewal_risk` > `paused` > `implementation` > `active`. This is the strongest single signal.
 2. **Renewal timing**: How close is `renewal_date` to the assessment date? Already-past renewals signal highest risk.
 3. **ARR exposure**: Higher `billing_arr_current` amplifies the impact of churn. Weighted by magnitude.
 4. **Overdue receivables**: Sum of `1_30` + `31_60` + `61_90` + `90_plus` from the AR aging entry matching the assessment as-of date. Higher overdue → collections risk.
 5. **Customer sentiment**: Latest valid NPS score. Scores below 30 indicate detractors; dropping trends signal deteriorating relationships.
 6. **Support health**: SLA compliance trends (declining below 90% is concerning); clean ticket volume (exclude spam/duplicates).
 7. **Usage trend**: Compare `product_usage` across the analysis period. Consistent decline > 3 points indicates disengagement.
 8. **Tenure**: `contract_tenure_months` below 18 months correlates with higher churn probability.

 ### Churn Model Features

 The churn export CSVs contain these feature columns: `tenure`, `MonthlyCharges`, `TotalCharges`, `Contract`, `PaymentMethod`, `PaperlessBilling`, `Partner`, `Dependents`, `OnlineSecurity`, `OnlineBackup`, `DeviceProtection`, `TechSupport`, `StreamingTV`, `StreamingMovies`, `SupportTickets90d`, `NPSLast`, `UsageTrendPct`, `InvoicePastDue`, `ActiveSeatRatio`. The target column is `Churn` (Yes/No). Key risk indicators:
- `Contract`: Month-to-month → higher churn
- `InvoicePastDue`: Yes → higher churn
- Low `tenure`, low `NPSLast`, negative `UsageTrendPct`, high `SupportTickets90d`, low `ActiveSeatRatio` all increase churn probability.
- The tenure coefficient direction is **negative** (higher tenure → lower churn risk).

 ## Output Precision Conventions

- **Currency values**: exactly 2 decimal places (e.g., `1425000.00`)
- **Percentage values**: exactly 1 decimal place (e.g., `93.3`)
- **Counts**: integers
- **Risk scores**: integers
- **Churn probabilities**: 3 decimal places (e.g., `0.924`)

 ## Controlled Vocabulary

 ### Risk Levels
 `critical`, `high`, `medium`, `low`

 ### Primary Actions
 `collections_followup` — overdue receivables require payment follow-up
 `renewal_save` — at-risk renewal needs executive intervention
 `technical_recovery` — paused/disengaged account needs technical re-engagement
 `executive_qbr` — strategic account needs executive business review
 `nurture_monitor` — healthy account, continue monitoring

 ### Reason Codes
 `overdue_receivable` — significant past-due balance
 `low_tenure_high_churn` — short contract tenure with elevated churn risk
 `sla_degradation` — SLA compliance declining or breached
 `nps_drop` — NPS score decline or detractor-level score
 `usage_decline` — product usage trending downward
 `renewal_window` — renewal date is approaching or has passed
 `expansion_offset` — open expansion pipeline offsets some risk
 `clean_billings` — no negative indicators detected

 ### Metric Sources (for QBR attribution)
 `billing_snapshot` — recognized revenue from billing system
 `support_export` — ticket counts from support platform
 `sla_report` — SLA compliance from operations reporting
 `nps_survey` — NPS scores from survey platform
 `crm_closed_won` — revenue from CRM won opportunities
 `ar_aging` — receivables from AR aging reports
 `pipeline_crm` — pipeline data from CRM
 `event_dashboard` — event metrics from events platform
 `hr_report` — HR data from HRIS

 ### Ticket Trends
 `improving` — clean ticket count decreasing across period
 `worsening` — clean ticket count increasing across period
 `flat` — clean ticket count stable across period

 ### Review Owners
 `customer_success` — CS-led review
 `solutions_engineering` — SE-led review
 `finance_ops` — Finance operations-led review

 ### QBR Agenda Topics
 `partnership_overview`, `q2_metrics`, `performance_highlights`, `q3_initiatives`, `technical_recovery`, `commercial_expansion`

 ### Churn Accuracy Bands
 `below_70`, `70_to_79`, `80_to_89`, `90_plus`

 ### Tenure Risk Direction
 `negative` — higher tenure correlates with lower risk
 `positive` — higher tenure correlates with higher risk
 `not_assessed` — relationship not evaluated

 ### CRM Link Status
 `linked` — AR customer matches a CRM account
 `unlinked` — AR customer is a noise/distractor entry

 ## Common Patterns

 ### Building a Retention Risk Queue
 1. Fetch account profiles, metrics, tickets, NPS, billing snapshots, and AR aging for the target account list.
 2. Filter AR aging to the assessment as-of date and match customer names to CRM accounts.
 3. Compute clean ticket counts (exclude spam/duplicates).
 4. Derive latest valid NPS (exclude retracted).
 5. Assess usage trend across the analysis period.
 6. Score each account across all risk dimensions and rank.
 7. Assign risk levels, primary actions, and reason codes from the controlled vocabulary.
 8. Aggregate portfolio-level metrics (ARR at risk, counts by severity, etc.).

 ### Building a QBR Metrics Packet
 1. Fetch metrics for the target account across the quarter months.
 2. Fetch tickets and NPS for the same date range.
 3. Use clean ticket counts (exclude spam/duplicates) for the support_tickets values.
 4. Compute highlights: average revenue, peaks, SLA max, NPS peak, ticket trend.
 5. Attribute each metric to its source system using the metric_sources vocabulary.
 6. Select appropriate review_owner and agenda topics.

 ### Processing a Receivables Review
 1. Fetch AR aging filtered to the quarter-end as-of date.
 2. Filter to customers with overdue balances in older buckets (61_90 or 90_plus > 0).
 3. Match each AR customer to CRM accounts via name matching.
 4. Classify as linked or unlinked.
 5. Build sorted overdue_followups list.
 6. Compute pipeline summary by filtering opportunities whose close_date falls in the quarter.
 7. Aggregate HR headcount and unpaid claims across all regions for the quarter.
 8. Pull event metrics for the specified event and quarter.

 ### Validating a Churn Model
 1. Count training rows, validation rows, and features from the CSV exports.
 2. Determine accuracy baseline (majority-class accuracy on validation set).
 3. Select accuracy_band from the controlled vocabulary.
 4. Determine tenure_coefficient_direction by comparing average tenure of churned vs. non-churned accounts in training data.
 5. Score candidate accounts using feature-based heuristics (contract type, payment method, past-due status, tenure, NPS, usage trend, support tickets, seat ratio).
 6. Rank by descending churn probability and assign outreach actions and reason codes.

 ### Building a High-Touch Retention Action Board
 1. Fetch full account data, metrics, tickets, NPS, AR aging, billing snapshots, and opportunities for the target account list.
 2. Rank all accounts by retention risk.
 3. For each account, determine: risk_level, primary_action, current_arr, expansion_pipeline (Q2 open opps with close dates in period), overdue_balance, next_touch_due_date, and reason_codes.
 4. Compute segment_summary: count strategic and enterprise accounts, sum ARR at risk, sum open expansion pipeline, compute net revenue exposure.
 5. Populate followup_calendar with the prescribed due dates by action type.
