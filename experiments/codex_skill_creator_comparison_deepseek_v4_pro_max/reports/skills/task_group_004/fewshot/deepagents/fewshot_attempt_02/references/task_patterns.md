## Task Archetypes

### 1. Renewal Risk Queue (Portfolio Ranking)

**What it does**: Ranks a list of accounts by composite renewal risk and produces a top-N risk queue.

**Typical inputs**: list of account_ids, assessment date, analysis period (months + date range), A/R as-of date.

**Data needed per account**:
- Account profile (GET /api/accounts/{id}): contract_tenure_months, renewal_date, segment, region, product_plan, billing_arr_current
- Billing snapshot (GET /api/billing/snapshots): billing_arr for as-of date
- Metrics (GET /api/accounts/{id}/metrics): recognized_revenue, sla_compliance, product_usage, nps_score
- Tickets (GET /api/accounts/{id}/tickets): clean count (exclude spam/duplicates)
- NPS (GET /api/accounts/{id}/nps): latest non-retracted score
- A/R aging (GET /api/finance/ar-aging): overdue balance (31-60 + 61-90 + 90+)

**Scoring approach (RS-6 composite)**:
1. Start from a base score and add/subtract per signal.
2. Key risk signals: renewal within 90 days, overdue > 0, NPS < 50 or drop >= 10, SLA < 90%, usage decline, tenure <= 24.
3. Order by risk_score descending, take top N.
4. Assign risk_level: critical >= 80, high 40-79, medium 20-39, low < 20.

**Primary action assignment**:
- overdue > 0 → collections_followup (unless higher-priority action applies)
- critical + strategic → executive_qbr
- SLA issues dominant + overdue == 0 → technical_recovery
- renewal_window dominant → renewal_save
- low risk → nurture_monitor or no_action

**Policy codes**: RS-6, REV-4, SUP-8, ACT-5.

### 2. QBR Metrics Packet (Single-Account Deep Dive)

**What it does**: Builds a quarterly business review packet for one account with month-by-month metrics.

**Typical inputs**: account_id, legal_name, quarter, months, date range.

**Data needed**:
- Metrics (GET /api/accounts/{id}/metrics): per-month revenue, support_ticket_count, sla_compliance, nps_score
- Tickets (GET /api/accounts/{id}/tickets): clean count per month
- NPS (GET /api/accounts/{id}/nps): per-response scores

**Output construction**:
- `qbr_metrics`: array of {month, revenue, support_tickets, sla_compliance_pct, nps_score} for each month
- `highlights`: averages, peaks, and ticket_trend (improving/worsening/flat)
- `metric_sources`: map each metric to its source enum
- `review_plan`: review_owner, due_date, needs_technical_signoff
- `agenda_topics`: exactly 4 ordered topics from the agenda enum

**Ticket trend**: Compare clean ticket counts across months. If decreasing → improving, increasing → worsening, unchanged → flat.

### 3. Receivables and Pipeline Operations Review

**What it does**: Cross-references A/R aging with CRM accounts, summarizes pipeline, and adds HR/event context.

**Typical inputs**: quarter, date range, A/R as-of date, region (or all), follow-up due date, event filter.

**Data needed**:
- A/R aging (GET /api/finance/ar-aging): all records for the quarter
- Accounts (GET /api/accounts): for name/alias matching
- Opportunities (GET /api/opportunities): pipeline summary for the quarter
- HR (GET /api/hr/summary): all regions for the quarter
- Events (GET /api/events/performance): filtered by event_id for the quarter

**Key logic**:
- `overdue_followups`: start from A/R records with overdue > 0 (31-60 + 61-90 + 90+), sorted by customer_name ascending
- Link each to a CRM account by matching customer_name to legal_name or aliases
- `financial_summary`: overdue_client_count, overdue_total, linked vs unlinked counts
- `pipeline_summary`: won/lost/open counts and amounts, win_rate_pct, top_open_product_line (by sum of open amounts)
- `ops_context`: sum hr_headcount, unpaid_claims_total, event_orders, event_revenue across all regions
- All follow-ups get primary_action: collections_followup and due_date as specified

**Policy codes**: RCP-7, CM-5, PW-6, FS-4.

### 4. Churn Model Validation and Outreach Ranking

**What it does**: Validates exported churn model data, trains a logistic regression model, and ranks candidate accounts by predicted churn probability.

**Data needed**:
- /exports/churn/train.csv: 19 features + Churn label
- /exports/churn/validation.csv: same features + label (for accuracy)
- /exports/churn/candidates.csv: same features, no label (for scoring)

**Procedure**:
1. Load CSVs. Features = all columns except customer_id and Churn.
2. One-hot encode categoricals. Leave numerics unscaled.
3. Train LogisticRegression(solver='lbfgs', max_iter=1000) on train set.
4. Predict validation set, compute accuracy_pct, map to accuracy_band.
5. Extract tenure coefficient for tenure_coefficient_direction.
6. Score candidates: predict_proba, filter to specified IDs, rank top 5.
7. Map outreach_action and reason_code per OUT-2 rules.
8. Compute cohort_checks.

**Policy codes**: MOD-7, PRB-4, DEP-5, OUT-2.

### 5. High-Touch Retention Action Board

**What it does**: Full retention board with ranked accounts, segment summary, and follow-up calendar for a leadership review.

**Typical inputs**: list of account_ids, assessment date, analysis period, months, A/R as-of date, follow-up due dates by action type.

**Data needed**: Same as renewal risk queue, plus:
- Opportunities (GET /api/opportunities): open expansion pipeline for each account

**Output construction**:
- `action_board`: all accounts, ranked by risk severity then ARR descending (BORD-4)
- Include expansion_pipeline from open opportunities closing within the period
- next_touch_due_date by primary_action; null for no_action
- `segment_summary`: strategic_accounts, enterprise_accounts, arr_at_risk, open_expansion_pipeline, net_revenue_exposure (EXP-6)
- `followup_calendar`: the per-action due dates as provided
- `policy_codes`: RS-6, REV-4, SUP-8, ACT-5, BORD-4, EXP-6, CAL-5

**Risk scoring**: Same RS-6 composite approach as renewal risk queue.
**Board sort (BORD-4)**: critical first, then high, medium, low. Within each tier, descending by current_arr.
