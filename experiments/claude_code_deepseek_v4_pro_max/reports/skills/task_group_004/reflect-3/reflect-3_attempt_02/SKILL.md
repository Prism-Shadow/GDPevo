# ApexCloud Retention Operations — Skill Reference

## Overview

This skill covers the ApexCloud Retention Operations API, a multi-source customer-success data platform. Tasks span renewal-risk queueing, QBR metrics packets, receivables-and-pipeline operations reviews, churn-model validation with outreach ranking, and high-touch retention action boards.

---

## API Base URL

Always read `environment_access.md` first. Use the `GDPEVO_ENV_BASE_URL` from that file as the API root. Never use `localhost`, `127.0.0.1`, or paths from `env/setup.sh` unless the environment-access file itself points there. Do not start the service locally.

---

## Core Endpoint Catalogue

### Account profile
- `GET /api/accounts` — list all accounts
- `GET /api/accounts/<account_id>` — single account detail

Key fields returned: `account_id`, `legal_name`, `display_name`, `billing_arr_current`, `crm_arr`, `contract_tenure_months`, `renewal_date`, `lifecycle_status` (`active` / `renewal_risk` / `implementation` / `paused`), `segment`, `product_plan`, `region`, `csm_owner`.

### Monthly metrics
- `GET /api/accounts/<account_id>/metrics?start=YYYY-MM&end=YYYY-MM`

Returns per-month records with: `month`, `recognized_revenue`, `support_ticket_count`, `sla_compliance` (percentage, raw precision from API), `nps_score` (may be `null` when no survey was fielded that month), `product_usage` (percentage), `active_seats`, `survey_status`.

**Important**: `support_ticket_count` in metrics includes spam and duplicate tickets. The tickets endpoint must be consulted separately for clean counts.

### Support tickets
- `GET /api/accounts/<account_id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD`

Each ticket has: `ticket_id`, `created_date`, `severity` (P1–P4), `product_area`, `first_response_sla_met`, `resolution_sla_met`, `is_spam`, `is_duplicate`, `status` (`closed` / `cancelled`).

**Clean ticket count** = total tickets minus those where `is_spam=true` or `is_duplicate=true`.

### NPS surveys
- `GET /api/accounts/<account_id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD`

Each response has: `response_id`, `response_date`, `score` (integer, −100 to +100), `survey_channel`, `retracted` (boolean).

**Latest NPS**: the most recent non-retracted survey within the analysis period, determined by `response_date`.

### AR aging
- `GET /api/finance/ar-aging?as_of=YYYY-MM-DD`

Returns entries with `aging_id` (contains the account_id), `customer_name`, `current`, `1_30`, `31_60`, `61_90`, `90_plus`, `region`, `quarter`.

**Matching to CRM accounts**: use the `aging_id` field — it embeds the account_id in the pattern `AR-<account_id>-<quarter>`. Entries with `AR-noise-` in the aging_id are AR-only noise records that do NOT link to CRM accounts.

**Older aging buckets** = sum of `61_90` + `90_plus`. These represent seriously past-due receivables.
**Total overdue** = `1_30` + `31_60` + `61_90` + `90_plus`.

### Billing snapshots
- `GET /api/billing/snapshots?account_id=<id>&as_of=YYYY-MM-DD`

Returns `billing_arr` (point-in-time ARR), `mrr`, `snapshot_id`, `source` (`"billing_snapshot"`), `posted`.

**ARR source differences**: the billing snapshot's `billing_arr` often differs from the accounts endpoint's `billing_arr_current` and `crm_arr`. All three are legitimate data sources; which one to use depends on the task's `arr_source_code` policy.

### Opportunities / pipeline
- `GET /api/opportunities?start=YYYY-MM-DD&end=YYYY-MM-DD`

Each opportunity: `opportunity_id`, `account_id`, `amount`, `stage` (e.g. `Prospecting`, `Discovery`, `Proposal`, `Negotiation`, `Closed Won`, `Closed Lost`), `state` (`open` / `closed`), `product_line`, `close_date`, `created_date`.

**Pipeline summary**: filter `state=closed` for won/lost counts; `state=open` for open pipeline. Win rate = won / (won + lost).

### HR summary
- `GET /api/hr/summary?quarter=YYYY-QN`

Returns per-region records with `headcount`, `unpaid_claims_amount`, `unpaid_claims_count`, `attendance_rate`, `open_advances_amount`, `high_absence_employees`, `leave_liability_hours`.

When the task says "all regions", sum numeric fields across all region records.

### Event performance
- `GET /api/events/performance?event=<event_id>&quarter=YYYY-QN`

Returns `event_orders`, `event_revenue`, `completed_orders`, `cancelled_orders`, `refunded_orders`, `pending_orders`, `product_revenue`.

### Churn exports (CSV)
- `GET /exports/churn/train.csv` — training data with `Churn` label
- `GET /exports/churn/validation.csv` — validation data with `Churn` label
- `GET /exports/churn/candidates.csv` — unlabelled candidates (no Churn column)

Features (19 total): `tenure`, `MonthlyCharges`, `TotalCharges`, `Contract`, `PaymentMethod`, `PaperlessBilling`, `Partner`, `Dependents`, `OnlineSecurity`, `OnlineBackup`, `DeviceProtection`, `TechSupport`, `StreamingTV`, `StreamingMovies`, `SupportTickets90d`, `NPSLast`, `UsageTrendPct`, `InvoicePastDue`, `ActiveSeatRatio`. Exclude `customer_id` (identifier) and `Churn` (target) from the feature count.

---

## Controlled Vocabularies

### Risk levels
`critical` | `high` | `medium` | `low`

### Primary actions
`executive_qbr` | `collections_followup` | `technical_recovery` | `renewal_save` | `nurture_monitor` | `no_action`

**Action mapping rules:**
- `collections_followup` → primary issue is overdue receivables (especially 61-90 or 90+ day buckets)
- `technical_recovery` → primary issue is SLA degradation or support hygiene
- `renewal_save` → account is in active renewal window (approaching or past due) with risk signals
- `executive_qbr` → strategic account with multiple complex risk factors requiring leadership engagement
- `nurture_monitor` → stable account needing only routine attention
- `no_action` → account with no material risk signals

### Reason codes
`overdue_receivable` | `low_tenure_high_churn` | `sla_degradation` | `nps_drop` | `usage_decline` | `renewal_window` | `expansion_offset` | `clean_billings`

**Code usage rules:**
- `renewal_window` — account is approaching or past its renewal date within the analysis scope
- `low_tenure_high_churn` — contract tenure < 24 months, statistically higher churn risk
- `nps_drop` — NPS score is in detractor range (< 30) or showed a significant decline period-over-period
- `sla_degradation` — SLA compliance declined ≥ 3 percentage points across the analysis months, or resolution SLA failures are present
- `usage_decline` — product usage trended downward across the analysis period
- `overdue_receivable` — account has older-bucket (61-90 or 90+) past-due balances in AR aging
- `expansion_offset` — account has open expansion pipeline that partially offsets churn risk
- `clean_billings` — account has no billing/receivable concerns; used for low-risk accounts

### Ticket trend (QBR)
`improving` | `worsening` | `flat`

A change of ≤ 1 ticket across the quarter is `flat`; a decrease of ≥ 2 is `improving`; an increase of ≥ 2 is `worsening`.

### Metric sources (QBR)
`crm_closed_won` | `support_export` | `sla_report` | `nps_survey` | `billing_snapshot` | `ar_aging` | `pipeline_crm` | `event_dashboard` | `hr_report`

Standard mapping: revenue → `crm_closed_won` or `billing_snapshot`, support_tickets → `support_export`, sla_compliance → `sla_report`, nps → `nps_survey`.

### Review owner (QBR)
`solutions_engineering` | `customer_success` | `finance_ops`

### Agenda topics (QBR)
`partnership_overview` | `q2_metrics` | `performance_highlights` | `q3_initiatives` | `technical_recovery` | `commercial_expansion`

### Accuracy band (churn model)
`below_70` | `70_to_79` | `80_to_89` | `90_plus`

### Tenure risk direction
`negative` — higher tenure is associated with lower churn risk. This is the standard finding: longer-tenured customers are more loyal.

### Link status (receivables)
`linked` — the AR customer name matches a CRM account. `unlinked` — no CRM match exists (typically AR-noise entries).

### Outreach action (churn)
`renewal_save` | `technical_recovery` | `collections_followup` | `nurture_monitor`

### Churn model reason code
Uses the same reason-code vocabulary as the risk-accounts tasks.

---

## Precision Rules

| Data type | Format | Example |
|-----------|--------|---------|
| Currency (ARR, revenue, overdue, pipeline) | 2 decimal places | `540000.00` |
| Percentages (SLA, win rate, accuracy) | 1 decimal place | `95.4` |
| Counts (tickets, accounts, rows) | integer | `14` |
| Risk scores | integer | `85` |
| Churn probabilities | 3 decimal places | `0.526` |
| NPS scores | integer (or `null` when no data) | `45` |

**SLA rounding**: when the metrics endpoint returns SLA values like `94.67`, round to 1 decimal (`94.7`). Use the rounded values consistently (including for max/min computations).

---

## Business-Policy Rules

### Renewal risk assessment
1. **Lifecycle status is the strongest signal**: `renewal_risk` > `paused` > `implementation` > `active`.
2. **Renewal proximity**: accounts past their renewal date with unresolved status are high risk. Accounts within 60 days of renewal with other risk factors are elevated.
3. **NPS detractor threshold**: scores < 30 are detractor-range and significantly increase risk. A NPS drop of ≥ 20 points between any two months in the period is a risk flag.
4. **AR aging severity**: 90+ day balances are the most urgent; 61-90 day balances are elevated. Both trigger `overdue_receivable` reason code.
5. **Tenure below 24 months** is a churn-risk multiplier, especially when combined with any other risk signal.

### QBR metrics construction
- Use the metrics endpoint directly for monthly values (`recognized_revenue`, `support_ticket_count`, `sla_compliance`, `nps_score`).
- Compute highlights arithmetically from the three monthly rows.
- For `ticket_trend`, compare the first-month count to the last-month count.
- For `needs_technical_signoff`, review whether any resolution SLA was missed or SLA compliance dipped below 90%.

### Receivables-and-pipeline operations review
1. Query AR aging for the as-of date. Filter to entries where `61_90 + 90_plus > 0` ("older aging buckets").
2. Match each AR customer to a CRM account via the `aging_id` field (real matches contain the account_id; noise entries have `AR-noise-` prefix).
3. Linked accounts become `overdue_followups` with `link_status: "linked"` and `primary_action: "collections_followup"`.
4. Unlinked (noise) entries are counted but not included in followups.
5. Sort followups by `customer_name` ascending.
6. `overdue_client_count` counts only linked CRM accounts with older-bucket overdue.
7. `overdue_total` sums total overdue (all buckets) for those linked accounts.

### Churn model protocol
1. **Training rows** = rows in train.csv (excluding header). **Validation rows** = rows in validation.csv (excluding header).
2. **Feature count** = total CSV columns minus identifier column (`customer_id`) minus target column (`Churn`). Count carefully: the exports have 19 features.
3. **Tenure coefficient direction** is `negative` (higher tenure → lower churn probability). This is consistent with the training-data pattern: the 0-11 month bucket has the highest churn rate, while 60+ month buckets have lower rates.
4. **Strongest churn predictors** in order: Contract type (Month-to-month), InvoicePastDue (Yes), low NPSLast, low tenure, negative UsageTrendPct, high SupportTickets90d, low ActiveSeatRatio.
5. **Segment-based baselines** from training: Month-to-month+PastDue=Yes ~27%, Month-to-month+PastDue=No ~20%, Two-year+PastDue=Yes ~25%, Two-year+PastDue=No ~10%, One-year+PastDue=Yes ~18%, One-year+PastDue=No ~2%.
6. Rank candidate accounts by predicted churn probability descending. Take the top 5.

### Retention board construction
1. Include ALL specified accounts in the action board, not just a top-N subset.
2. Sort by risk priority (the "standard retention board order"): lifecycle status first, then AR aging severity, then NPS trend, then renewal proximity.
3. `arr_at_risk` = sum of ARR for all board accounts.
4. `open_expansion_pipeline` = sum of all open opportunity amounts for the board accounts whose close dates fall within the analysis period.
5. `net_revenue_exposure` = `arr_at_risk` − `open_expansion_pipeline`.
6. `next_touch_due_date` maps from primary_action to the corresponding follow-up date (provided in the task prompt).

---

## Exclusion Rules

1. **Spam and duplicate tickets**: always exclude `is_spam=true` and `is_duplicate=true` tickets when computing "clean" ticket counts. The metrics endpoint's `support_ticket_count` includes them.
2. **Retracted NPS responses**: exclude surveys where `retracted=true` from latest-NPS determination.
3. **AR noise entries**: entries whose `aging_id` starts with `AR-noise-` are NOT CRM accounts. Count them as unlinked but do not include them as followup entries.
4. **Cancelled tickets**: tickets with `status=cancelled` are still "clean" unless also marked spam/duplicate. They count toward clean ticket totals.
5. **Non-target accounts**: when a task provides an explicit account_id list, only those accounts go into the output. Other accounts from API responses are excluded.

---

## Common Pitfalls

1. **Feature count off-by-one**: always subtract both the identifier column AND the target column from the CSV header count. Verify by listing the header.
2. **SLA precision mismatch**: the metrics endpoint returns SLA with varying decimals (e.g. `94.67`, `95.43`). Round to 1 decimal place before use in output fields.
3. **ARR source confusion**: the accounts endpoint has two ARR fields (`billing_arr_current`, `crm_arr`) and the billing snapshot has a third (`billing_arr`). They differ. Check which source the task/model-check expects.
4. **AR aging matching by name**: customer names in AR aging do not always exactly match legal names in CRM. Always match by `aging_id` (which embeds the account_id), not by customer_name string comparison.
5. **NPS null handling**: when the metrics endpoint shows `nps_score: null` for a month, no survey was fielded. The "latest NPS" should be the most recent non-null, non-retracted survey from the NPS endpoint within the period.
6. **Ticket count discrepancy**: the metrics endpoint's `support_ticket_count` equals total tickets including spam/duplicates. The tickets endpoint must be consulted for clean counts.
7. **Win rate calculation**: denominator is won + lost (closed deals only). Open opportunities are excluded from the rate.
8. **Overdue balance scope**: "older aging buckets" (61-90 + 90+) is the filter criterion for identifying at-risk AR customers. Whether the `overdue_balance` output field uses older-buckets-only or total-overdue depends on the specific task context.
9. **Policy codes are enumerations**: each policy-code field has a specific set of allowed values (shown as pipe-separated options in templates). Always select exactly one valid value per field.
10. **Sort order for receivables followups**: ascending by `customer_name`, not by overdue amount or account_id.

---

## Workflow Pattern

For any ApexCloud task:
1. Read `environment_access.md` for the correct API base URL.
2. Identify which endpoint families the task requires from the prompt.
3. Fetch all needed data in parallel (account profiles, metrics, tickets, NPS, AR aging, billing snapshots, opportunities, HR, events, exports).
4. Match/link entities by account_id, using `aging_id` for AR-to-CRM matching.
5. Apply exclusion rules (spam, duplicates, retracted surveys, noise entries).
6. Apply precision rules to all numeric outputs.
7. Use controlled vocabulary values exactly as defined — do not invent new labels.
8. Sort output collections as specified (by rank, by customer_name ascending, by churn probability descending).
