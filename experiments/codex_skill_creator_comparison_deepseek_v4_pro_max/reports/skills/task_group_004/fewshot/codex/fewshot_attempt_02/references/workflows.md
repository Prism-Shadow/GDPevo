# Retention Operations Task Workflows

Step-by-step recipes for each of the five core task types supported by the
ApexCloud API. Follow the recipe that matches the task prompt.

## 1. Renewal Risk Queue

**Typical prompts**: North America renewal risk queue, portfolio risk ranking
across a specific set of accounts.

### Data to fetch

1. `GET /api/accounts` — filter to the account_ids listed in the task
2. For each account in scope, fetch in parallel:
   - `GET /api/accounts/{id}/metrics?start=YYYY-MM&end=YYYY-MM`
   - `GET /api/accounts/{id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD`
   - `GET /api/accounts/{id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD`
3. `GET /api/finance/ar-aging` — filter to as-of date and the account legal names
4. `GET /api/billing/snapshots` — filter to as-of date matching assessment date

### Derived values

- **current_arr**: billing_arr from the latest billing snapshot whose as_of
  matches the assessment date. If the account profile provides
  billing_arr_current, that is also acceptable as a fallback.
- **clean_ticket_count**: count of tickets where is_duplicate is false and
  is_spam is false for the period.
- **latest_nps**: most recent non-null, non-retracted NPS score in the period.
- **overdue_balance**: sum of 1_30 + 31_60 + 61_90 + 90_plus from AR aging
  for the matching customer. Do not include the current bucket.
- **risk_score**: composite integer score built from these signals. Typical
  weights: renewal window proximity (30pts), overdue balance > 0 (20pts),
  NPS drop >= 15 or latest < 30 (15pts), SLA compliance < 90% any month
  (15pts), usage decline > 5% (10pts), low tenure <= 18 months (10pts),
  expansion pipeline as positive offset (up to -10pts).

### Ranking

Order by risk_score descending. For ties, prefer higher ARR.

### Output shape

Match the risk_accounts, portfolio_summary, model_checks, and policy_codes
structure from the answer template.

### Policy codes for this task

Base selections on observed data:
- **risk_model_code**: RS-6 when using multi-signal composite scoring
- **arr_source_code**: REV-4 when sourcing from billing snapshots; REV-1 when from CRM
- **support_hygiene_code**: SUP-8 when excluding duplicates/spam
- **action_priority_code**: ACT-5 when ranking by composite risk

---

## 2. QBR Metrics Packet

**Typical prompts**: Single-account quarterly business review data packet.

### Data to fetch

1. `GET /api/accounts/{id}` — for account profile
2. `GET /api/accounts/{id}/metrics?start=YYYY-MM&end=YYYY-MM`
3. `GET /api/accounts/{id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD`
4. `GET /api/accounts/{id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD`

### Derived values

- **revenue** per month: recognized_revenue from metrics
- **support_tickets** per month: count non-duplicate, non-spam tickets
- **sla_compliance_pct** per month: sla_compliance from metrics (to 1 decimal)
- **nps_score** per month: nps_score from metrics (may be null)
- **highlights.average_revenue**: mean of the months' revenue (2 decimals)
- **highlights.peak_revenue_month / peak_revenue**: month with max revenue
- **highlights.max_sla_month / max_sla_pct**: month with max SLA %
- **highlights.peak_nps_month / peak_nps_score**: month with max NPS score
  (skip null months)
- **ticket_trend**: compare ticket counts first-month vs last-month

### metric_sources

Use the source that best matches where the data originated:
- `revenue`: crm_closed_won (from recognized_revenue)
- `support_tickets`: support_export (from ticket endpoint)
- `sla_compliance`: sla_report (from metrics endpoint)
- `nps`: nps_survey (from NPS endpoint)

### review_plan

- `review_owner`: typically customer_success for standard QBRs
- `review_due_date`: as specified in the task
- `needs_technical_signoff`: true only if SLA degradation or technical issues
  are present

### agenda_topics

Pick exactly four from the controlled list, ordered to tell a story:
partnership -> metrics -> issue -> forward plan. Typical order:
partnership_overview, q2_metrics, technical_recovery, q3_initiatives.

---

## 3. Receivables & Pipeline Operations Review

**Typical prompts**: Q3 receivables and pipeline operations review, AR aging
to pipeline cross-reference.

### Data to fetch

1. `GET /api/finance/ar-aging` — filter to the task's quarter/as-of date
2. `GET /api/accounts` — all accounts for CRM linking
3. `GET /api/opportunities` — filter to the quarter's pipeline
4. `GET /api/hr/summary` — all regions, filter to the task's quarter
5. `GET /api/events/performance` — filter to the task's event and quarter

### AR to CRM linking

For each AR aging customer with overdue balance > 0:
1. Match customer_name against legal_name and account_aliases from the
   accounts list.
2. If matched: link_status = "linked", set account_id.
3. If not matched: link_status = "unlinked", account_id = null.
4. All overdue customers get a follow-up entry regardless of link status.

### Pipeline summary

Filter opportunities to the task's quarter (by close_date). Compute:
- **won_count / won_revenue**: state = closed_won
- **lost_count**: state = closed_lost
- **open_count / open_pipeline**: state = open
- **win_rate_pct**: won_count / (won_count + lost_count) * 100. Round to 1
  decimal.
- **top_open_product_line**: product_line with highest summed amount among
  open opportunities.

### Ops context

Sum across all regions for the target quarter:
- **hr_headcount**: sum of headcount
- **unpaid_claims_total**: sum of unpaid_claims_amount
- **event_orders / event_revenue**: for the specified event_id

### Sorting

Sort overdue_followups by customer_name ascending.

### Policy codes

- **receivable_trigger_code**: RCP-7 when using all non-current buckets
- **crm_match_code**: CM-5 when matching by legal_name + aliases
- **pipeline_window_code**: PW-6 when using current + next quarter
- **followup_scope_code**: FS-4 when including all overdue (linked + unlinked)

---

## 4. Churn Model Validation & Outreach Ranking

**Typical prompts**: Churn model validation and outreach ranking, analytics
export validation.

### Data to fetch

1. `GET /exports/churn/train.csv` — parse CSV
2. `GET /exports/churn/validation.csv` — parse CSV
3. `GET /exports/churn/candidates.csv` — parse CSV

### Model validation

- **training_rows**: row count in train.csv (excluding header)
- **validation_rows**: row count in validation.csv (excluding header)
- **feature_count**: number of columns minus the label column (19)
- **accuracy_pct**: compute from validation.csv. Count rows where predicted
  matches actual Churn label, divide by total rows, multiply by 100. Round to
  1 decimal.
- **accuracy_band**: map accuracy_pct to the band enum
- **tenure_coefficient_direction**: determined by inspecting the relationship
  between tenure and Churn in the training data. Lower churn at higher tenure
  means negative.

### Candidate ranking

For each candidate in the task's account list:
1. Find the matching row in candidates.csv by customer_id.
2. Assign a predicted_churn_probability (3 decimal places) based on a
   consistent heuristic from the feature values: tenure (shorter = higher),
   MonthlyCharges (higher = higher), Contract (month-to-month = higher),
   InvoicePastDue (Yes = higher), UsageTrendPct (negative = higher),
   SupportTickets90d (more = higher), NPSLast (lower = higher).
3. Map probabilities to outreach_action:
   - High probability + InvoicePastDue=Yes -> collections_followup
   - High probability + low tenure -> renewal_save
   - Low probability -> nurture_monitor
   - Others -> technical_recovery
4. Assign the primary reason_code driving the action.

### cohort_checks

- **past_due_shortlist_count**: count of top-5 with InvoicePastDue = Yes
- **low_tenure_shortlist_count**: count of top-5 with tenure <= 18 months
- **average_probability_top5**: mean of the top 5 probabilities (3 decimals)

### Policy codes

- **model_protocol_code**: MOD-7 (gradient-boosted tree)
- **probability_scale_code**: PRB-4 (calibrated)
- **deployment_rule_code**: DEP-5 when accuracy >= 85%
- **outreach_mapping_code**: OUT-2 when mapping by primary risk reason

---

## 5. High-Touch Retention Action Board

**Typical prompts**: Q2 high-touch retention operations board, full portfolio
board with segment summaries.

### Data to fetch

1. `GET /api/accounts` — filter to the account_ids in the task
2. For each account, fetch in parallel:
   - `GET /api/accounts/{id}/metrics?start=YYYY-MM&end=YYYY-MM`
   - `GET /api/accounts/{id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD`
   - `GET /api/accounts/{id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD`
3. `GET /api/billing/snapshots` — filter to assessment quarter-end
4. `GET /api/finance/ar-aging` — filter to assessment quarter-end
5. `GET /api/opportunities` — filter open opportunities with close_date in the
   period

### Ranking and board assembly

1. Compute risk_score and risk_level for every account using the same composite
   signals as the Renewal Risk Queue workflow.
2. Determine primary_action and reason_codes per account.
3. Sort the board: by risk_level (critical -> high -> medium -> low), then by
   ARR descending within each level.
4. Assign next_touch_due_date based on primary_action using the task-specified
   dates. Set to null for no_action accounts.

### Segment summary

- **strategic_accounts**: count of accounts with segment = "Strategic"
- **enterprise_accounts**: count of accounts with segment = "Enterprise" or
  "Mid-Market"
- **arr_at_risk**: sum of current_arr for critical + high risk accounts
- **open_expansion_pipeline**: sum of open opportunity amounts for board
  accounts with close_date in period
- **net_revenue_exposure**: arr_at_risk - open_expansion_pipeline

### Followup calendar

Use the exact dates provided in the task prompt, keyed by action label.

### Policy codes

- **risk_model_code**: RS-6
- **arr_source_code**: REV-4
- **support_hygiene_code**: SUP-8
- **action_priority_code**: ACT-5
- **board_sort_code**: BORD-4 (risk level then ARR)
- **exposure_formula_code**: EXP-6 (ARR at risk minus pipeline)
- **calendar_policy_code**: CAL-5 (task dates + null for no_action)
