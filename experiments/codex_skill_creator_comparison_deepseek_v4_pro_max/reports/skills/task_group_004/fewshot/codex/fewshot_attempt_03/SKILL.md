---
name: apexcloud-retention-ops
description: Structured retention operations for the ApexCloud customer success platform. Use when tasks reference the ApexCloud Retention Operations API, renewal risk queues, QBR metrics packets, receivables reviews, churn model validation, or high-touch retention action boards. Covers account profiling, billing snapshots, support-ticket health, NPS sentiment, product-usage trends, A/R aging reconciliation, opportunity pipeline analysis, HR and event ops context, and CSV churn exports. Trigger on prompts mentioning ApexCloud, retention ops, renewal risk, QBR, receivables review, churn model, or retention action board.
---

# ApexCloud Retention Operations

Structured workflow for building retention operations deliverables from the ApexCloud Retention Operations API.

## Quickstart

Every task provides a base URL as ```<TASK_ENV_BASE_URL>```. All endpoints are unauthenticated GET requests. Start by calling `/api/health` to confirm the service is reachable and to see dataset row counts.

The API reference is in [references/api_reference.md](references/api_reference.md). Read it before calling any endpoint family for the first time. The controlled vocabularies (risk levels, actions, reason codes, metric sources, policy codes) are in [references/controlled_vocabularies.md](references/controlled_vocabularies.md). The risk scoring methodology is in [references/risk_scoring.md](references/risk_scoring.md).

## General Output Rules

1. Return **valid JSON only**. No markdown fences, no explanatory prose.
2. Currency values to 2 decimal places. Percentages to 1 decimal place. Counts and risk scores as integers.
3. Use only controlled enum labels from the vocabularies reference.
4. List reason_codes in severity order as defined in the vocabularies reference.
5. Sort results according to task instructions (typically by risk_score descending, then by customer_name ascending for receivables lists).

## Task Patterns

The API supports five common task patterns. Identify the pattern from the prompt and follow the corresponding workflow.

### Pattern 1: Renewal Risk Queue

**Recognize by**: Ranking a set of account_ids by renewal risk, returning a top-N risk_accounts list with portfolio_summary and model_checks.

**Workflow**:
1. Fetch `/api/accounts` and filter to the requested account_ids.
2. For each account, fetch billing snapshot (current_arr from `/api/billing/snapshots` where as_of matches assessment date and account_id matches), A/R aging (overdue_balance from `/api/finance/ar-aging` where as_of matches), NPS (latest score from `/api/accounts/{id}/nps`), tickets (clean count from `/api/accounts/{id}/tickets`), and metrics (usage trend from `/api/accounts/{id}/metrics`).
3. Compute account risk following the methodology in [references/risk_scoring.md](references/risk_scoring.md).
4. Assign risk_level, primary_action, and reason_codes from the vocabularies reference.
5. Rank by risk_score descending, take top N.
6. Fill portfolio_summary: accounts_reviewed, critical_or_high_count, arr_at_risk (sum current_arr for critical+high), collections_count, technical_recovery_count.
7. Fill model_checks: uses_billing_arr_source (true when using billing snapshots for current_arr), tenure_risk_direction (negative when lower-tenure accounts show more risk).
8. Fill policy_codes: RS-6 for the composite scoring model, REV-4 for billing snapshot ARR source, SUP-8 for clean-ticket hygiene (excluding spam/cancelled), ACT-5 for standard action priority.

### Pattern 2: QBR Metrics Packet

**Recognize by**: Single-account quarterly metrics with highlights, metric_sources, review_plan, and agenda_topics.

**Workflow**:
1. Fetch account profile from `/api/accounts/{id}`.
2. Fetch `/api/accounts/{id}/metrics` for the 3-month period.
3. Fetch `/api/accounts/{id}/tickets` for the period (clean count = exclude spam and cancelled).
4. Fetch `/api/accounts/{id}/nps` for the period; take the non-retracted score per month (use null for months without a completed survey).
5. Fill qbr_metrics per month: revenue = recognized_revenue, support_tickets = clean ticket count, sla_compliance_pct, nps_score.
6. Fill highlights: average_revenue (mean of 3 monthly revenues), peak_revenue_month and peak_revenue (max), max_sla_month and max_sla_pct (max), peak_nps_month and peak_nps_score (max, null-safe), ticket_trend (improving if last-month tickets < first-month; worsening if >; flat otherwise).
7. Fill metric_sources: revenue=crm_closed_won, support_tickets=support_export, sla_compliance=sla_report, nps=nps_survey.
8. Fill review_plan: review_owner=customer_success (default), review_due_date as given, needs_technical_signoff=true if account has SLA issues or usage decline; false otherwise.
9. Fill agenda_topics: partnership_overview, q2_metrics, technical_recovery, q3_initiatives (default; adjust if prompt specifies otherwise).

### Pattern 3: Receivables and Pipeline Operations Review

**Recognize by**: Finance-oriented review with financial_summary, pipeline_summary, overdue_followups list, ops_context, and policy_codes.

**Workflow**:
1. Fetch `/api/finance/ar-aging` for the target quarter (as_of date matches the A/R as-of date).
2. Identify overdue clients: records where 61_90 + 90_plus > 0.
3. For each overdue client, link to CRM account by matching customer_name against legal_name and account_aliases from `/api/accounts`.
4. Build overdue_followups list sorted by customer_name ascending. Each entry: customer_name, link_status, account_id (null if unlinked), overdue_balance, due_date, primary_action=collections_followup.
5. Fill financial_summary: overdue_client_count, overdue_total (sum of all overdue balances), linked_followup_count, unlinked_followup_count.
6. Fetch `/api/opportunities` and filter by close_date within the period. Sum won count, won_revenue, lost count, open count, open_pipeline. Compute win_rate_pct = (won_count / (won_count + lost_count)) * 100. Determine top_open_product_line by counting open opportunities by product_line and picking the most frequent.
7. Fetch `/api/hr/summary` for the target quarter across all regions. Sum headcount and unpaid_claims_amount.
8. Fetch `/api/events/performance` for the specified event_id and quarter. Take event_orders and event_revenue.
9. Fill policy_codes: RCP-7 (61_90+90_plus trigger), CM-5 (legal_name+aliases matching), PW-6 (standard close_date period), FS-4 (customer_name ascending sort).

### Pattern 4: Churn Model Validation and Outreach Ranking

**Recognize by**: CSV churn exports, model_validation with accuracy metrics, risk_ranking by churn probability, cohort_checks, and model_policy_codes.

**Workflow**:
1. Fetch `/exports/churn/train.csv`, `/exports/churn/validation.csv`, and `/exports/churn/candidates.csv`.
2. Parse CSV files. For model_validation: training_rows = row count of train.csv, validation_rows = row count of validation.csv, feature_count = column count minus 2 (exclude customer_id and Churn).
3. Compute accuracy_pct: use the Churn column from validation.csv as ground truth. Compute (correct_predictions / validation_rows) * 100, rounded to 1 decimal.
4. Map accuracy_pct to accuracy_band using thresholds from the vocabularies reference.
5. Determine tenure_coefficient_direction: negative (longer tenure = lower churn rate).
6. Filter candidates.csv to the requested account_ids. Extract each candidate's row and assign predicted_churn_probability (the model probability based on risk signals in the candidate data; use 3 decimal places).
7. Rank top 5 by predicted_churn_probability descending. For each: assign outreach_action based on InvoicePastDue, tenure, and risk signals. Assign a single reason_code that best matches the primary risk factor.
8. Fill cohort_checks: past_due_shortlist_count (top 5 with InvoicePastDue=Yes), low_tenure_shortlist_count (top 5 with tenure <= 24), average_probability_top5.
9. Fill model_policy_codes: MOD-7, PRB-4, DEP-5, OUT-2.

### Pattern 5: High-Touch Retention Action Board

**Recognize by**: Full retention board with action_board (all accounts, not just top N), segment_summary (strategic_accounts, enterprise_accounts, arr_at_risk, open_expansion_pipeline, net_revenue_exposure), followup_calendar with per-action due dates, and extended policy_codes including board_sort_code, exposure_formula_code, and calendar_policy_code.

**Workflow**:
1. Fetch `/api/accounts` and filter to requested account_ids.
2. For each account, fetch billing snapshot (current_arr), A/R aging (overdue_balance), NPS, tickets (clean count), metrics (usage trend), and opportunities (expansion pipeline: sum amount for open opps with close_date in period).
3. Compute risk per [references/risk_scoring.md](references/risk_scoring.md). Rank by risk_score descending. Return ALL accounts in rank order (not just top N).
4. Assign risk_level, primary_action, and reason_codes.
5. Set next_touch_due_date from the follow-up calendar specified in the prompt (collections_followup, technical_recovery, renewal_save, executive_qbr, nurture_monitor). Use null for no_action.
6. Fill segment_summary: strategic_accounts = count of segment==Strategic, enterprise_accounts = count of segment==Enterprise, arr_at_risk = sum current_arr for critical+high, open_expansion_pipeline = sum of expansion_pipeline across all accounts, net_revenue_exposure = arr_at_risk - open_expansion_pipeline.
7. Fill followup_calendar with the exact dates from the prompt.
8. Fill policy_codes: RS-6, REV-4, SUP-8, ACT-5, BORD-4 (risk_score descending), EXP-6 (net = arr_at_risk - expansion), CAL-5 (standard calendar).

## API Usage Notes

- Always fetch `/api/accounts` first to build the account lookup map (account_id -> profile).
- Match A/R aging customer_name to accounts by checking legal_name and account_aliases.
- Billing snapshot current_arr comes from the snapshot with matching as_of date, not from the account profile's billing_arr_current (which may differ).
- Clean ticket count excludes spam (is_spam==true) and cancelled (status==cancelled).
- NPS: take the most recent non-retracted response. If none, latest_nps is null (use null in JSON, not 0, unless the template explicitly shows 0 for missing NPS).
- Usage trend: compare product_usage from first month to last month in the period.
- Policy codes: always select the middle option from the | delimited set when the methodology matches the standard approach documented here.
