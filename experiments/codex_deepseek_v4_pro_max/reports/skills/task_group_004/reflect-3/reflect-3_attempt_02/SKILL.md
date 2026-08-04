 # ApexCloud Retention Operations Skill

 ## Overview

 Use this skill when working with the ApexCloud Retention Operations API to solve customer success, retention risk, churn prediction, QBR metrics, receivables, or pipeline review tasks. The API is a RESTful service at `<TASK_ENV_BASE_URL>` with no required headers.

 ## API Endpoints

 ### Account Data

 - `GET /api/accounts` — list all accounts
 - `GET /api/accounts/{account_id}` — single account detail (includes `billing_arr_current`, `crm_arr`, `contract_tenure_months`, `renewal_date`, `lifecycle_status`, `segment`, `product_plan`, `region`, `legal_name`, `csm_owner`)

 ### Account Metrics (Time-Series)

 - `GET /api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM` — monthly metrics including `recognized_revenue`, `support_ticket_count`, `sla_compliance`, `nps_score`, `product_usage`, `active_seats`, `survey_status`

 **Important:** Do NOT use the metrics endpoint's `sla_compliance` or `support_ticket_count` for SLA or ticket counts. These are aggregated values that may include spam/duplicates. Compute SLA and clean ticket counts from raw ticket data instead (see below).

 ### Support Tickets

 - `GET /api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` — individual tickets with `is_spam`, `is_duplicate`, `resolution_sla_met`, `first_response_sla_met`, `severity`, `status`, `product_area`

 ### NPS

 - `GET /api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` — NPS survey responses with `score`, `retracted`, `response_date`, `survey_channel`

 ### Billing

 - `GET /api/billing/snapshots` — quarterly billing snapshots with `billing_arr`, `mrr`, `as_of` date. Filter by `as_of` for the assessment date.

 ### Accounts Receivable

 - `GET /api/finance/ar-aging` — A/R aging with `1_30`, `31_60`, `61_90`, `90_plus`, `current`, `customer_name`, `region`, `quarter`, `as_of`. Filter by `as_of` for the assessment date.

 ### Opportunities / Pipeline

 - `GET /api/opportunities` — CRM opportunities with `account_id`, `account_legal_name`, `amount`, `close_date`, `created_date`, `stage`, `state`, `product_line`, `region`. Use `stage` (not `state`) for Closed Won / Closed Lost.

 ### HR

 - `GET /api/hr/summary` — HR operational data by quarter and region: `headcount`, `unpaid_claims_amount`, `attendance_rate`, etc.

 ### Events

 - `GET /api/events/performance` — event performance by quarter and event_id: `event_orders`, `event_revenue`, `completed_orders`, etc.

 ### Exports

 - `GET /exports/churn/train.csv` — churn training data (180 rows)
 - `GET /exports/churn/validation.csv` — churn validation data (60 rows)
 - `GET /exports/churn/candidates.csv` — candidate accounts for churn prediction
 - `GET /exports/account_metric_extract.csv` — pre-computed monthly account metrics extract

 ## Data Extraction Rules

 ### Clean Ticket Count

 Always compute from the raw tickets endpoint. Exclude tickets where `is_spam` is `true` OR `is_duplicate` is `true`. Count all remaining tickets.

 ```python
 clean = [t for t in tickets if not t.get('is_spam') and not t.get('is_duplicate')]
 clean_count = len(clean)
 ```

 ### SLA Compliance / SLA Failures

 Compute from raw tickets (clean tickets only). A ticket has an SLA failure if EITHER `resolution_sla_met` is `false` OR `first_response_sla_met` is `false`:

 ```python
 sla_fails = sum(1 for t in clean if not (t.get('resolution_sla_met', True) and t.get('first_response_sla_met', True)))
 ```

 For SLA compliance percentage: `(clean_count - sla_fails) / clean_count * 100` (rounded to 1 decimal).

 ### NPS Score

 Use the latest non-retracted NPS response from the NPS endpoint. If multiple responses exist in a period, use the most recent by `response_date`. If none, score is 0.

 ### Current ARR

 Use the billing snapshot for the assessment date (`billing_arr` from `/api/billing/snapshots` filtered by `as_of`). The `billing_arr_current` from the accounts endpoint may differ from the snapshot value — prefer the snapshot.

 ### Overdue Balance

 From `/api/finance/ar-aging`, filter by `as_of` date. Match `customer_name` to account `legal_name` (or aliases) for linking.

 Overdue balance = `31_60` + `61_90` + `90_plus` for total overdue; or `61_90` + `90_plus` for "older aging buckets" tasks. Read the task description carefully to determine which to use.

 ### Pipeline

 Opportunities have `state` ("open" or "closed") and `stage` ("Closed Won", "Closed Lost", "Discovery", "Proposal", "Negotiation", "Prospecting"). Use `stage` to identify won/lost, not `state`. Filter by `close_date` within the task's date range for period-specific reporting.

 For "open pipeline": use ALL opportunities with `state == "open"` regardless of close_date, unless the task specifies a period filter.

 ### Account Matching

 AR aging uses `customer_name` (legal name). Match to accounts via `legal_name` or any entry in `account_aliases`. If no match exists, `link_status` is "unlinked".

 ## Controlled Vocabularies

 Always use these exact enum strings — never invent variants:

 **Risk Levels:** `critical`, `high`, `medium`, `low`

 **Primary Actions:** `executive_qbr`, `collections_followup`, `technical_recovery`, `renewal_save`, `nurture_monitor`, `no_action`

 **Reason Codes:** `overdue_receivable`, `low_tenure_high_churn`, `sla_degradation`, `nps_drop`, `usage_decline`, `renewal_window`, `expansion_offset`, `clean_billings`

 **Metric Sources:** `crm_closed_won`, `support_export`, `sla_report`, `nps_survey`, `billing_snapshot`, `ar_aging`, `pipeline_crm`, `event_dashboard`, `hr_report`

 **Review Owners:** `solutions_engineering`, `customer_success`, `finance_ops`

 **Agenda Topics:** `partnership_overview`, `q2_metrics`, `performance_highlights`, `q3_initiatives`, `technical_recovery`, `commercial_expansion`

 **Ticket Trends:** `improving`, `worsening`, `flat`

 **Accuracy Bands:** `below_70`, `70_to_79`, `80_to_89`, `90_plus`

 **Link Status:** `linked`, `unlinked`

 **Tenure Direction:** `negative`, `positive`, `zero`, `not_assessed`

 **Outreach Actions (churn):** `renewal_save`, `technical_recovery`, `collections_followup`, `nurture_monitor`

 ## Output Formatting Rules

 - **Currency values**: exactly 2 decimal places (e.g., `1416439.47`)
 - **Percentage values**: exactly 1 decimal place (e.g., `66.7`)
 - **Counts**: integers
 - **Risk scores**: integers
 - **Churn probabilities**: 3 decimal places (e.g., `0.581`)
 - Round using standard rounding (not floor/ceil)

 ## Policy Codes

 Task templates include `policy_codes` or `model_policy_codes` sections with pipe-delimited options (e.g., `"RS-2|RS-6|RS-9"`). The pipe separates enumerated choices — select exactly one value for each key.

 When selecting among the available combinations, choose codes that align with the data sources and methodology applied:
 - Match `arr_source_code` to the actual ARR source used (e.g., billing snapshot vs CRM)
 - Match `risk_model_code` to the risk factors and scoring approach
 - Match `support_hygiene_code` to how SLA/support data was computed
 - Match `action_priority_code` / `outreach_mapping_code` to the prioritization logic

 The same pattern applies to task-specific code families (e.g., `receivable_trigger_code`, `pipeline_window_code`, `model_protocol_code`, etc.).

 ## Risk Assessment Patterns

 When building renewal risk or retention action boards:

 1. **Extract factual data first**: current_arr (billing snapshot), clean_ticket_count (raw tickets), latest_nps (NPS endpoint), overdue_balance (AR aging), tenure, renewal_date, lifecycle_status.

 2. **Compute risk factors as binary flags** based on data thresholds:
    - `overdue_receivable`: overdue_balance > 0
    - `low_tenure_high_churn`: tenure < 24 months
    - `sla_degradation`: any SLA failures in clean tickets
    - `nps_drop`: latest NPS > 0 and < 40
    - `usage_decline`: product_usage trend decreasing (last < first in period)
    - `renewal_window`: renewal_date within 90 days of assessment date (or past)

 3. **Rank by risk factor count**, breaking ties by ARR (descending).

 4. **Map risk_level**: 5+ factors → critical, 4 → high, 2-3 → medium, 0-1 → low.

 5. **Determine primary_action**: prioritize collections (overdue > 5000) > renewal_save (past-due renewal or renewal_risk) > technical_recovery (SLA/usage issues) > nurture_monitor. Executive QBR for critical accounts with ARR > 500000.

 ## Churn Model Pattern

 When building churn models from CSV exports:

 1. Parse CSVs using `csv.DictReader`
 2. Extract features from all columns (tenure, charges, contract type, payment method, services, NPS, usage trend, past due, seat ratio)
 3. One-hot encode categorical features
 4. Normalize numeric features (z-score)
 5. Train logistic regression with gradient descent (200 epochs, lr=0.1)
 6. Evaluate on validation set for accuracy
 7. Predict probabilities for candidate accounts
 8. Rank by predicted churn probability descending
 9. Assign outreach actions based on the candidate's strongest risk indicator:
    - InvoicePastDue=Yes → `collections_followup` / `overdue_receivable`
    - tenure < 24 → `renewal_save` / `low_tenure_high_churn`
    - SupportTickets90d > 5 → `technical_recovery` / `sla_degradation`
    - NPSLast < 40 → `renewal_save` / `nps_drop`
    - UsageTrendPct < 0 → `technical_recovery` / `usage_decline`
    - Otherwise → `nurture_monitor` / `clean_billings`

 ## Common Pitfalls

 - **Do NOT use metrics endpoint sla_compliance** for SLA assessment. Compute from raw tickets.
 - **Do NOT use metrics endpoint support_ticket_count** for clean ticket counts. Filter raw tickets for spam/duplicates.
 - **Use billing snapshot ARR** (not account billing_arr_current) when `uses_billing_arr_source` is true.
 - **Use stage (not state)** for opportunity won/lost determination.
 - **Match customer_name to legal_name AND aliases** when linking AR to accounts.
 - **Always return valid JSON only** — no markdown wrappers, no explanatory text.
 - **Follow precision rules exactly**: 2 decimals for currency, 1 decimal for percentages, integers for counts, 3 decimals for churn probabilities.
 - **Use controlled enums exactly as listed** — never abbreviate, rephrase, or invent.
 - **When in doubt, compute from raw endpoints** (tickets, NPS, billing snapshots, AR aging) rather than aggregated extracts.
