# ApexCloud Retention Operations — Reusable Skill

## 1. API Endpoint Reference

All data comes from the ApexCloud Retention Operations API. Key endpoints:

| Endpoint | Query Params | Returns |
|---|---|---|
| `/api/accounts` | none | All account profiles (billing_arr_current, crm_arr, tenure, renewal_date, lifecycle_status, segment, region, aliases) |
| `/api/accounts/{id}` | none | Single account profile |
| `/api/accounts/{id}/metrics` | `?start=YYYY-MM&end=YYYY-MM` | Monthly recognized_revenue, nps_score, product_usage, sla_compliance, support_ticket_count, active_seats, survey_status |
| `/api/accounts/{id}/tickets` | `?start=YYYY-MM-DD&end=YYYY-MM-DD` | Support tickets with SLA fields, spam/duplicate flags, severity |
| `/api/accounts/{id}/nps` | `?start=YYYY-MM-DD&end=YYYY-MM-DD` | Individual NPS survey responses with retracted flag and survey_channel |
| `/api/finance/ar-aging` | none | AR aging by quarter for all customers (1_30, 31_60, 61_90, 90_plus, current buckets) |
| `/api/billing/snapshots` | `?start=YYYY-MM-DD&end=YYYY-MM-DD` | Quarterly billing ARR snapshots per account with source field |
| `/api/opportunities` | none | CRM opportunities with state, stage, amount, close_date, product_line |
| `/api/hr/summary` | none | HR headcount, unpaid claims by quarter and region |
| `/api/events/performance` | none | Event orders and revenue by event_id and quarter |
| `/exports/churn/train.csv` | none | Churn model training data (180 rows) |
| `/exports/churn/validation.csv` | none | Churn model validation data (60 rows) |
| `/exports/churn/candidates.csv` | none | Candidate accounts for churn prediction (44 rows) |

**Metrics date format:** `?start=YYYY-MM&end=YYYY-MM` (month precision).
**Tickets/NPS date format:** `?start=YYYY-MM-DD&end=YYYY-MM-DD` (day precision).

---

## 2. ARR / Revenue Source Convention

Two ARR fields exist on every account:

- **`billing_arr_current`** — from the billing system. Use this when the task says "uses billing ARR source" or references billing-snapshot data.
- **`crm_arr`** — from the CRM. Use this when the task references CRM-sourced ARR.

Monthly revenue comes from `recognized_revenue` in the metrics endpoint (not the billing snapshot MRR). The billing snapshot shows quarter-end ARR snapshots, not monthly flow.

For metric source attribution in QBR-style packets, use the controlled vocabulary: `crm_closed_won`, `billing_snapshot`, `support_export`, `sla_report`, `nps_survey`, `ar_aging`, `pipeline_crm`, `event_dashboard`, `hr_report`.

---

## 3. CRM / AR Customer Matching

AR aging entries have a `customer_name` field (legal name). To link an AR customer to a CRM account:

1. Match `customer_name` exactly against `legal_name` on the accounts list.
2. Match `customer_name` exactly against any entry in `account_aliases` on the accounts list.
3. If neither matches, the customer is **unlinked** and `account_id` is `null`.

Matching is exact string comparison — subsidiary names like "Globex North Subsidiary LLC" do NOT match the alias "Globex North Subsidiary" because of the "LLC" suffix. Similarly, "North Star Finance Services" does NOT match "Northstar Finance Subsidiary" due to the space difference.

---

## 4. NPS Conventions

**latest_nps:** The most recent non-null, non-retracted NPS score within the analysis period.

- Use the NPS endpoint for individual survey responses; check `retracted: false`.
- Use the metrics endpoint for monthly aggregates; check `survey_status != "retracted"`.
- When the latest month has `survey_status: "retracted"`, fall back to the previous month's valid score.
- If a month has `survey_status: "missing"`, the monthly `nps_score` is null — skip it.

---

## 5. Clean Ticket Counting

A ticket is **clean** when:
- `is_spam` is `false`
- `is_duplicate` is `false`

Do NOT additionally filter by SLA status, ticket status (open/closed/cancelled), or resolution outcome. Spam and duplicate flags are the only exclusion criteria.

---

## 6. Overdue Balance Calculation

Total overdue = `1_30 + 31_60 + 61_90 + 90_plus` from the AR aging entry for the correct quarter.

- **"Older aging buckets"** refers to the `61_90` and `90_plus` buckets specifically.
- Use the AR aging `quarter` field to filter to the correct period (e.g., `2026-Q2` for a June 30 as-of date, `2026-Q3` for September 30).

---

## 7. Pipeline Analysis

CRM opportunities have two key fields: `state` (open/closed) and `stage` (Proposal, Discovery, Negotiation, Closed Won, Closed Lost).

- **Won:** `stage == "Closed Won"` (NOT just `state == "closed"`)
- **Lost:** `stage == "Closed Lost"` (NOT just `state == "closed"`)
- **Open:** `state == "open"` (regardless of stage)
- **Win rate:** `won_count / (won_count + lost_count) * 100`

Only count opportunities whose `close_date` falls within the analysis quarter.

---

## 8. Risk Assessment Framework

When ranking accounts by renewal/retention risk, weight these factors:

### Primary risk drivers (highest to lowest weight):
1. **Renewal timing** — Past renewal date > renewal within 60 days > renewal far out. A past renewal date combined with `lifecycle_status: "renewal_risk"` is the strongest risk signal.
2. **Overdue receivables** — 90+ day bucket > 61-90 day bucket > 31-60 > 1-30. Large overdue balances in older buckets indicate collections risk.
3. **NPS trajectory** — Drops of 20+ points within the quarter are severe. Consistently low NPS (< 30) is a moderate concern.
4. **Usage decline** — Sustained downward trend across all 3 months (not just one dip).
5. **SLA degradation** — SLA compliance falling below 90%, or failed resolution SLAs.
6. **Low tenure** — Contract tenure < 24 months correlates with higher churn risk. Tenure < 12 months is highest risk.

### Controlled risk levels:
`critical` > `high` > `medium` > `low`

### Controlled primary actions:
`collections_followup` — overdue receivables is the dominant issue.
`renewal_save` — past/near renewal date is the dominant issue.
`executive_qbr` — high ARR account with multiple risk factors, needs executive intervention.
`technical_recovery` — SLA/resolution failures are the dominant issue.
`nurture_monitor` — low to moderate risk, no immediate action needed.
`no_action` — no risk factors present.

### Controlled reason codes:
`overdue_receivable` — has overdue balance, especially in older buckets.
`low_tenure_high_churn` — tenure < 24 months.
`sla_degradation` — SLA compliance declining or resolution failures.
`nps_drop` — NPS declined significantly.
`usage_decline` — product usage trending down.
`renewal_window` — renewal date is past or within 60 days.
`expansion_offset` — open expansion pipeline offsets risk.
`clean_billings` — no billing/receivables issues.

### Risk score convention:
Integer from 0-100. Higher = more risk. The score should reflect the weighted combination of the factors above.

---

## 9. Churn Model Methodology

### Data shape:
- Training: 180 rows, 19 features + target (Churn)
- Validation: 60 rows
- Candidates: 44 rows, same features minus Churn target

### Feature categories:
- **Numerical:** tenure, MonthlyCharges, TotalCharges, SupportTickets90d, NPSLast, UsageTrendPct, ActiveSeatRatio
- **Categorical (one-hot):** Contract, PaymentMethod, PaperlessBilling, Partner, Dependents, OnlineSecurity, OnlineBackup, DeviceProtection, TechSupport, StreamingTV, StreamingMovies, InvoicePastDue

### Key churn relationships (from training data):
- **Contract=Month-to-month:** ~22% churn rate (baseline ~15.6%)
- **Contract=One year:** ~6% churn rate
- **InvoicePastDue=Yes:** ~24% churn rate
- **Tenure < 12 months:** ~25% churn rate
- **UsageTrendPct < 0:** ~23-24% churn rate
- **UsageTrendPct > 0:** ~7% churn rate
- **NPSLast < 30:** ~21-24% churn rate
- **NPSLast > 60:** ~6% churn rate

### Model validation:
- Feature count: 19 (all CSV columns except customer_id and Churn)
- Tenure coefficient direction: **negative** (higher tenure reduces churn probability — this is a universal pattern in churn models)
- Accuracy band thresholds: below_70, 70_to_79, 80_to_89, 90_plus

### Outreach action mapping for churn candidates:
- High probability + InvoicePastDue=Yes → `collections_followup`, reason: `overdue_receivable`
- High probability + tenure < 24 + Month-to-month → `renewal_save`, reason: `low_tenure_high_churn`
- Moderate probability → `nurture_monitor`
- Low probability + clean profile → `nurture_monitor`, reason: `clean_billings`

### Cohort checks:
- `past_due_shortlist_count`: number of the 8 selected candidates with InvoicePastDue=Yes
- `low_tenure_shortlist_count`: number of the 8 selected candidates with tenure < 24
- `average_probability_top5`: mean of predicted churn probabilities for the top 5 ranked candidates

---

## 10. Output Precision Rules (Deterministic)

Apply these precision rules to every numeric output field:

| Type | Precision |
|---|---|
| Currency (revenue, ARR, balances, pipeline) | 2 decimal places |
| Percentages (SLA, win rate, accuracy) | 1 decimal place |
| Counts (tickets, accounts, headcount) | integers |
| Risk scores | integers (0-100) |
| Churn probabilities | 3 decimal places |
| NPS scores | integers |

Always round using standard rounding (0.5 rounds up).

---

## 11. Follow-Up Calendar Convention

When a task specifies follow-up due dates by action type, use this priority order (earliest to latest):

1. `collections_followup` — earliest date (highest urgency)
2. `technical_recovery` — second
3. `renewal_save` — third
4. `executive_qbr` — fourth
5. `nurture_monitor` — latest date (lowest urgency)

---

## 12. Portfolio / Segment Summary Construction

- **accounts_reviewed:** Total number of accounts in the analysis scope.
- **critical_or_high_count:** Number of accounts with risk level `critical` or `high`.
- **arr_at_risk:** Sum of `current_arr` (billing_arr_current) for all `critical` + `high` accounts.
- **collections_count:** Number of accounts whose `primary_action` is `collections_followup`.
- **technical_recovery_count:** Number of accounts whose `primary_action` is `technical_recovery`.
- **strategic_accounts / enterprise_accounts:** Count by account `segment` field.
- **open_expansion_pipeline:** Sum of amounts for all open (state=open) expansion opportunities in the analysis period.
- **net_revenue_exposure:** Total ARR across all reviewed accounts (not just at-risk).

---

## 13. QBR Metric Packet Construction

For single-account QBR packets:

- **qbr_metrics:** One entry per month with revenue (recognized_revenue), support_tickets (count from metrics), sla_compliance_pct (1 decimal), nps_score (integer, null if missing).
- **average_revenue:** Mean of the 3 monthly recognized_revenue values, rounded to 2 decimals.
- **peak_revenue_month / peak_revenue:** Month with the highest recognized_revenue.
- **max_sla_month / max_sla_pct:** Month with the highest sla_compliance (use 1-decimal-rounded values for comparison).
- **peak_nps_month / peak_nps_score:** Month with the highest non-null nps_score.
- **ticket_trend:** `improving` if ticket count decreases over the quarter, `worsening` if it increases, `flat` if it stays the same.
- **review_owner:** Pick from the controlled set: `solutions_engineering`, `customer_success`, `finance_ops`. Match to the task context (e.g., "customer success director" → `customer_success`).
- **agenda_topics:** Exactly 4 ordered enum strings from: `partnership_overview`, `q2_metrics`, `performance_highlights`, `q3_initiatives`, `technical_recovery`, `commercial_expansion`. Choose the 4 most relevant to the review context.

---

## 14. Common Pitfalls

1. **Using localhost URLs from task prompts.** Always use the remote API URL provided in the environment config — ignore any `127.0.0.1` references in task text.

2. **Confusing `state` and `stage` in opportunities.** `state=closed` does NOT mean won. Won/Lost is in the `stage` field.

3. **Fuzzy CRM name matching.** Subsidiary names with extra suffixes (LLC, Ltd, Inc) do NOT match aliases. Exact string comparison only.

4. **Including retracted NPS surveys.** Always filter out `retracted: true` surveys and months with `survey_status: "retracted"`.

5. **Using crm_arr when billing_arr is the source.** Check the task's ARR source expectation — the account profile has both fields and they can differ.

6. **Computing overdue_total across wrong quarter.** Always filter AR aging by the correct quarter matching the as-of date.

7. **Counting spam/duplicate tickets as clean.** Only exclude `is_spam=true` and `is_duplicate=true`.

8. **Including the target column in feature count.** For churn model validation, feature_count excludes both customer_id and Churn (the target).

9. **Using wrong date formats for API calls.** Metrics use month precision (`YYYY-MM`); tickets and NPS use day precision (`YYYY-MM-DD`).

10. **Overlooking policy codes.** Every task template includes `policy_codes` — these are required fields and encode business-routing rules. Always populate them with valid enum values from the template.

---

## 15. Controlled Vocabulary Quick Reference

**Risk levels:** `critical`, `high`, `medium`, `low`

**Primary actions:** `executive_qbr`, `collections_followup`, `technical_recovery`, `renewal_save`, `nurture_monitor`, `no_action`

**Reason codes:** `overdue_receivable`, `low_tenure_high_churn`, `sla_degradation`, `nps_drop`, `usage_decline`, `renewal_window`, `expansion_offset`, `clean_billings`

**Metric sources:** `crm_closed_won`, `support_export`, `sla_report`, `nps_survey`, `billing_snapshot`, `ar_aging`, `pipeline_crm`, `event_dashboard`, `hr_report`

**Ticket trends:** `improving`, `worsening`, `flat`

**Accuracy bands:** `below_70`, `70_to_79`, `80_to_89`, `90_plus`

**Coefficient directions:** `negative`, `positive`, `zero`, `not_assessed`

**Outreach actions (churn):** `renewal_save`, `technical_recovery`, `collections_followup`, `nurture_monitor`

**Agenda topics:** `partnership_overview`, `q2_metrics`, `performance_highlights`, `q3_initiatives`, `technical_recovery`, `commercial_expansion`

**Review owners:** `solutions_engineering`, `customer_success`, `finance_ops`

**Link status:** `linked`, `unlinked`
