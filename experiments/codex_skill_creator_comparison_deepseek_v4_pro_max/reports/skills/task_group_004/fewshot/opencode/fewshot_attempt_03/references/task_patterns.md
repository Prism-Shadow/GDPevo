# Task-Specific Workflows

Each task type follows a predictable pipeline. Start by identifying which task type the prompt matches, then follow the corresponding workflow.

## 1. Renewal Risk Queue

**Example**: "Q2 2026 renewal risk queue for the North America portfolio"

**Inputs**: Account list, assessment date, analysis period, months, A/R as-of date.

**Pipeline**:

1. Read the answer template to understand the output shape.
2. Fetch `/api/accounts` and filter to the specified account_ids or region.
3. For each account, fetch in parallel:
   - `/api/accounts/{id}/metrics?start=...&end=...` for monthly metrics
   - `/api/accounts/{id}/tickets?start=...&end=...` for support tickets
   - `/api/accounts/{id}/nps?start=...&end=...` for NPS responses
4. Fetch global datasets:
   - `/api/billing/snapshots` for quarterly billing ARR
   - `/api/finance/ar-aging` for receivables
5. For each account, compute:
   - `current_arr`: From billing snapshot for assessment quarter (fallback: billing_arr_current)
   - `clean_ticket_count`: From tickets endpoint (exclude spam/duplicate)
   - `latest_nps`: Most recent non-null NPS score in the period
   - `overdue_balance`: From A/R aging (31_60 + 61_90 + 90_plus)
   - `risk_score`: Using the risk score computation rules
   - `risk_level`: Mapped from risk_score
   - `primary_action`: Chosen by action priority tiebreak
   - `reason_codes`: All applicable codes
6. Sort accounts by risk_score descending, take top N (typically 5).
7. Compute portfolio_summary:
   - `accounts_reviewed`: Total accounts evaluated
   - `critical_or_high_count`: Count of accounts with critical or high risk_level
   - `arr_at_risk`: Sum of current_arr for all reviewed accounts
   - `collections_count`: Count where primary_action is collections_followup
   - `technical_recovery_count`: Count where primary_action is technical_recovery
8. Set model_checks:
   - `uses_billing_arr_source`: true (when using billing snapshots)
   - `tenure_risk_direction`: "negative" (standard finding)
9. Select policy codes based on methodology used.
10. Output JSON with keys: risk_accounts, portfolio_summary, model_checks, policy_codes.

## 2. QBR Metrics Packet

**Example**: "Q2 QBR metrics packet for Globex North"

**Inputs**: Single account_id, quarter, months, date range.

**Pipeline**:

1. Read the answer template.
2. Fetch `/api/accounts/{id}` for account metadata.
3. Fetch `/api/accounts/{id}/metrics?start=...&end=...` for monthly metrics.
4. For each month, populate qbr_metrics with:
   - `revenue`: `recognized_revenue`
   - `support_tickets`: `support_ticket_count`
   - `sla_compliance_pct`: `sla_compliance`
   - `nps_score`: `nps_score` (or null if missing)
5. Compute highlights:
   - `average_revenue`: Mean of recognized_revenue across months
   - `peak_revenue_month` and `peak_revenue`: Month with max recognized_revenue
   - `max_sla_month` and `max_sla_pct`: Month with max sla_compliance
   - `peak_nps_month` and `peak_nps_score`: Month with max nps_score (non-null)
   - `ticket_trend`: improving/worsening/flat from month-over-month comparison
6. Assign metric_sources:
   - `revenue`: `crm_closed_won` (recognized_revenue is CRM-based)
   - `support_tickets`: `support_export`
   - `sla_compliance`: `sla_report`
   - `nps`: `nps_survey`
7. Set review_plan:
   - `review_owner`: `customer_success` (default for QBR)
   - `review_due_date`: As specified in prompt or template
   - `needs_technical_signoff`: true if SLA degradation detected, false otherwise
8. Build agenda_topics: Choose exactly 4 topics. Start with partnership_overview, q2_metrics. Add technical_recovery if SLA issues, else performance_highlights. Add q3_initiatives or commercial_expansion as the forward-looking topic.
9. Output JSON with keys: qbr_metrics, highlights, metric_sources, review_plan, agenda_topics.

## 3. Receivables & Pipeline Review

**Example**: "Q3 Receivables And Pipeline Operations Review"

**Inputs**: Quarter, date range, A/R as-of date, region, event context, follow-up due date.

**Pipeline**:

1. Read the answer template.
2. Fetch `/api/finance/ar-aging` and filter to records where:
   - `quarter` matches target quarter
   - Overdue balance exists: `31_60 + 61_90 + 90_plus > 0`
3. Fetch `/api/accounts` for linking.
4. For each overdue A/R customer:
   - Try to match `customer_name` against account `legal_name` (exact match)
   - If no exact match, try against `account_aliases`
   - If matched: `link_status = "linked"`, set `account_id`
   - If unmatched: `link_status = "unlinked"`, `account_id = null`
5. Sort overdue_followups by `customer_name` ascending.
6. Set `due_date` and `primary_action` as specified (typically `collections_followup`).
7. Compute financial_summary:
   - `overdue_client_count`: Count of all overdue follow-ups
   - `overdue_total`: Sum of all overdue balances
   - `linked_followup_count`: Count with link_status "linked"
   - `unlinked_followup_count`: Count with link_status "unlinked"
8. Fetch `/api/opportunities` and filter for target quarter:
   - `won_count`: state == "won" and close_date within quarter
   - `won_revenue`: Sum of amounts for won
   - `lost_count`: state == "lost" and close_date within quarter
   - `open_count`: state == "open" (all open, regardless of close_date)
   - `open_pipeline`: Sum of amounts for open
   - `win_rate_pct`: won_count / (won_count + lost_count) * 100
   - `top_open_product_line`: Product line with most open opportunities
9. Fetch `/api/hr/summary` for target quarter (all regions):
   - `hr_headcount`: Sum of headcount across all regions
   - `unpaid_claims_total`: Sum of unpaid_claims_amount across all regions
10. Fetch `/api/events/performance` for target event_id and quarter:
    - `event_orders`: From matching record
    - `event_revenue`: From matching record
11. Select policy codes.
12. Output JSON with keys: financial_summary, pipeline_summary, overdue_followups, ops_context, policy_codes.

## 4. Churn Model Validation & Ranking

**Example**: "Churn Model Validation And Outreach Ranking"

**Inputs**: Candidate account list.

**Pipeline**:

1. Read the answer template.
2. Fetch `/exports/churn/train.csv` and `/exports/churn/validation.csv`.
3. Parse CSVs: count rows, identify feature columns.
4. Compute model_validation:
   - `training_rows`: Row count of train.csv
   - `validation_rows`: Row count of validation.csv
   - `feature_count`: Count of feature columns (exclude customer_id and Churn)
   - `accuracy_pct`: Compute accuracy by comparing predicted vs actual Churn labels
   - `accuracy_band`: Map accuracy_pct to band
   - `tenure_coefficient_direction`: Analyze tenure-churn relationship (typically "negative")
5. Fetch `/exports/churn/candidates.csv`.
6. Parse to get `customer_id` and churn probability for each candidate.
7. Filter to the specified candidate account_ids.
8. Sort by predicted churn probability descending.
9. For each ranked candidate, determine:
   - `outreach_action`: Based on risk profile (collections_followup for past due, renewal_save for low tenure, nurture_monitor otherwise)
   - `reason_code`: Single most relevant reason code
10. Add top 5 candidates (ranked 1-5) to risk_ranking.
11. Compute cohort_checks:
    - `past_due_shortlist_count`: Count of ranked candidates with overdue reason
    - `low_tenure_shortlist_count`: Count with low_tenure reason
    - `average_probability_top5`: Mean probability of top 5
12. Select model_policy_codes.
13. Output JSON with keys: model_validation, risk_ranking, cohort_checks, model_policy_codes.

## 5. Retention Action Board

**Example**: "High-Touch Retention Operations Board"

**Inputs**: Account list, assessment date, analysis period, months, A/R as-of date, follow-up due dates per action.

**Pipeline**:

1. Read the answer template.
2. Fetch all accounts, billing snapshots, tickets, NPS, A/R aging, and opportunities for the specified account_ids.
3. For each account, compute the full risk profile (ARR, tickets, NPS, overdue, usage, tenure, renewal, expansion).
4. Determine risk_level and primary_action per the standard rules.
5. Compute expansion_pipeline: Sum of open opportunity amounts for the account where close_date falls within the analysis period or the following quarter.
6. Assign next_touch_due_date based on primary_action (use the due dates provided in the prompt). null for no_action.
7. Sort the action board in retention board order: by risk_level severity (critical first, then high, medium, low), then by current_arr descending within each level.
8. Compute segment_summary:
   - `strategic_accounts`: Count of Strategic segment accounts
   - `enterprise_accounts`: Count of Enterprise + Mid-Market accounts
   - `arr_at_risk`: Sum of current_arr for all board accounts
   - `open_expansion_pipeline`: Sum of all expansion_pipeline values
   - `net_revenue_exposure`: arr_at_risk - open_expansion_pipeline (min 0)
9. Populate followup_calendar with due dates per action (from prompt).
10. Select policy_codes including board_sort_code, exposure_formula_code, and calendar_policy_code.
11. Output JSON with keys: action_board, segment_summary, followup_calendar, policy_codes.
