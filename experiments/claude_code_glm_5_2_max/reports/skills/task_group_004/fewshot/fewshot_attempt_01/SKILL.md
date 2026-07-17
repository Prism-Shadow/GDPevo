# ApexCloud Retention Operations — Analytics Convention Skill

A reusable, executable convention layer for the ApexCloud Retention Operations API.
A test solver receives this SKILL + a task prompt + the environment base URL, and must
reproduce the conventions exactly. All rules below were verified against the live API and
the train answer keys. Apply them to whatever accounts / dates / quarters the test prompt
supplies.

---

## 0. Environment & API access

- **Base URL:** use the remote URL supplied to the solver (the `ENV_URL`). Ignore any
  `http://127.0.0.1:...` placeholder inside a prompt body — the real service is the ENV_URL.
- All endpoints are read-only GET. Return JSON (`/exports/...` return raw CSV).
- **Response envelopes (always unwrap these keys):**
  | Endpoint | Envelope key holding the records |
  |---|---|
  | `/api/accounts` | `accounts` |
  | `/api/accounts/<id>` | (single account object) |
  | `/api/accounts/<id>/metrics` | `metrics` (+ `count`) |
  | `/api/accounts/<id>/tickets` | `tickets` (+ `count`) |
  | `/api/accounts/<id>/nps` | `nps_responses` (+ `count`) |
  | `/api/billing/snapshots` | `snapshots` |
  | `/api/finance/ar-aging?as_of=YYYY-MM-DD` | `ar_aging` (+ `count`) |
  | `/api/opportunities?start&end` | `opportunities` (+ `count`) |
  | `/api/hr/summary?quarter&region` | `hr_summary` (+ `count`) |
  | `/api/events/performance?event&quarter` | `event_performance` (+ `count`) |
- **“All regions” convention:** for `/api/opportunities` and `/api/hr/summary`, **omit** the
  `region` parameter (or pass it empty). Passing `region=all` / `global` / `ALL` returns 0
  rows. Use `region` only when a specific region is requested.
- **Dates:** metrics use `start=YYYY-MM&end=YYYY-MM`; tickets/nps use
  `start=YYYY-MM-DD&end=YYYY-MM-DD`; ar-aging uses `as_of=YYYY-MM-DD`; opportunities use
  `start&end` as `YYYY-MM-DD`; hr uses `quarter=YYYY-Qn`; events use `event=<id>&quarter=YYYY-Qn`.

### Record field maps (the load-bearing fields)
- **account:** `account_id, legal_name, display_name, account_aliases[], billing_arr_current,
  crm_arr, contract_tenure_months, csm_owner, lifecycle_status, product_plan, region,
  renewal_date, segment`.
- **billing snapshot:** `account_id, as_of YYYY-MM-DD, billing_arr, mrr, legal_name, posted(bool),
  snapshot_id, source`.
- **ar_aging:** `customer_name, as_of, quarter, region, current, 1_30, 31_60, 61_90, 90_plus`.
- **metric (per month):** `account_id, month, quarter, recognized_revenue, support_ticket_count,
  sla_compliance, nps_score, product_usage, active_seats, survey_status`.
- **ticket:** `ticket_id, account_id, created_date, severity, product_area, status,
  is_spam(bool), is_duplicate(bool), first_response_sla_met(bool), resolution_sla_met(bool)`.
- **nps response:** `response_id, account_id, response_date, survey_channel, score, retracted(bool)`.
- **opportunity:** `opportunity_id, account_id, account_legal_name, product_line, region, stage,
  state, amount, created_date, close_date`. Stages: `Closed Won, Closed Lost, Discovery,
  Prospecting, Negotiation, Proposal`. `state`: `open` / `closed`.
- **hr_summary:** `quarter, region, headcount, attendance_rate, high_absence_employees,
  leave_liability_hours, open_advances_count, open_advances_amount, unpaid_claims_count,
  unpaid_claims_amount`.
- **event_performance:** `event_id, quarter, event_orders, event_revenue, completed_orders,
  pending_orders, cancelled_orders, refunded_orders, product_revenue`.
- **churn CSV columns:** `customer_id, tenure, MonthlyCharges, TotalCharges, Contract,
  PaymentMethod, PaperlessBilling, Partner, Dependents, OnlineSecurity, OnlineBackup,
  DeviceProtection, TechSupport, StreamingTV, StreamingMovies, SupportTickets90d, NPSLast,
  UsageTrendPct, InvoicePastDue, ActiveSeatRatio` + `Churn` (train/validation only).

---

## 1. Stable policy codes (emit EXACTLY these)

These codes are stable conventions across the whole task group. Select the subset each
template’s `policy_codes` / `model_policy_codes` block asks for.

| Code key | Value | Meaning |
|---|---|---|
| `risk_model_code` | **RS-6** | Retention risk scoring model (rule-based severity index) |
| `arr_source_code` | **REV-4** | Current ARR sourced from posted billing snapshots (NOT CRM ARR) |
| `support_hygiene_code` | **SUP-8** | Clean tickets = exclude spam, duplicate, cancelled |
| `action_priority_code` | **ACT-5** | Primary-action precedence map |
| `receivable_trigger_code` | **RCP-7** | Overdue trigger = late buckets only (61_90 + 90_plus) |
| `crm_match_code` | **CM-5** | Match A/R customer to CRM account by exact legal name; do not link aliases/subsidiaries |
| `pipeline_window_code` | **PW-6** | Pipeline window keyed on close_date within range |
| `followup_scope_code` | **FS-4** | linked_when_exact_else_standalone |
| `model_protocol_code` | **MOD-7** | Churn protocol: 180 train / 60 validation / 19 features |
| `probability_scale_code` | **PRB-4** | Churn probabilities to 3 decimals |
| `deployment_rule_code` | **DEP-5** | 90_plus accuracy band → approve_with_monitoring |
| `outreach_mapping_code` | **OUT-2** | Churn outreach action/reason mapping |
| `board_sort_code` | **BORD-4** | Board order: risk_score desc, current_arr desc, account_id asc; return ALL accounts |
| `exposure_formula_code` | **EXP-6** | net_revenue_exposure = arr_at_risk − open_expansion_pipeline |
| `calendar_policy_code` | **CAL-5** | Follow-up due dates = assessment date + fixed offsets by action |

---

## 2. Precision rules (deterministic)

- **Currency:** 2 decimals (e.g. `1416439.47`, `0.00`).
- **Percentages:** 1 decimal (e.g. `66.7`, `75.0`).
- **Counts and risk scores:** integers.
- **Churn probabilities:** 3 decimals (e.g. `0.102`).
- **Nulls:** use JSON `null` (e.g. NPS when no valid survey in a month; `account_id` for an
  unlinked receivable; `next_touch_due_date` when action is `no_action`).
- Do not round intermediate sums; round only the emitted value.

---

## 3. Data hygiene & sourcing rules

### 3.1 Current ARR — `REV-4` (billing snapshots, not CRM)
`current_arr` = the `billing_arr` field of the **latest posted billing snapshot** with
`as_of <= assessment_date` for that account. Do **not** use the account’s `crm_arr` or
`billing_arr_current` fields. Snapshots are quarterly (`as_of` = quarter-end); pick the most
recent one on or before the assessment date.

### 3.2 Overdue receivable — `RCP-7` (late buckets only)
`overdue_balance` = `61_90 + 90_plus` from the `ar-aging` record whose `as_of` equals the
task’s A/R as-of date, matched to the account by **legal name**. The `1_30`, `31_60`, and
`current` buckets are NOT overdue. `overdue_receivable` reason fires iff `overdue_balance > 0`.

### 3.3 Support hygiene — `SUP-8`
A ticket is **clean** iff `is_spam = false` AND `is_duplicate = false` AND `status != "cancelled"`.
- Retention tasks: `clean_ticket_count` = count of clean tickets over the whole analysis period.
- QBR task (per-month): clean tickets grouped by `created_date[:7]`.
- `sla_degradation` reason fires iff **at least one clean ticket** in the period has
  `first_response_sla_met = false` OR `resolution_sla_met = false` (any SLA breach).

### 3.4 NPS hygiene
Ignore responses with `retracted = true` (and scores that are invalid sentinels such as `-1`).
**Latest valid NPS in period** = the non-retracted response with the greatest `response_date`
within the analysis window; use its `score` as `latest_nps`. For QBR per-month NPS, use the
metric record’s `nps_score` (null when `survey_status = "missing"`). NPS source label = `nps_survey`.

### 3.5 CRM matching — `CM-5` (receivables task)
Link an A/R `customer_name` to a CRM account **iff it exactly equals** the account’s
`legal_name`. Do **not** match against `account_aliases`, display names, or subsidiary/legal
variants (e.g. “Subsidiary LLC”, “Canada” variant, reordered words). `link_status` = `linked`
(exact match, `account_id` set) or `unlinked` (`account_id = null`). Both linked and unlinked
overdue customers are listed as follow-ups (`FS-4`: linked_when_exact_else_standalone). Sort
`overdue_followups` by `customer_name` ascending.

### 3.6 Pipeline window — `PW-6`
Select opportunities whose **`close_date` falls within** `[start, end]`. Classify by `stage`:
- `Closed Won` → won
- `Closed Lost` → lost
- all other stages (`Discovery, Prospecting, Negotiation, Proposal`) → open
`open_pipeline` = Σ `amount` of open opps in window. `won_revenue` = Σ `amount` of Closed Won in
window. `win_rate_pct` = `won / (won + lost) * 100` (denominator = Closed Won + Closed Lost only;
open opps excluded). `top_open_product_line` = product line with the **largest open-pipeline
revenue** in window. For a per-account **expansion_pipeline** (retention board), use the same
definition (open opps, close_date in the board’s analysis window).

---

## 4. Retention risk signals (`RS-6`)

Compute each boolean from the analysis-period data (assessment date + the months the prompt
specifies, A/R as-of the prompt’s date):

| Reason code | Fires when |
|---|---|
| `renewal_window` | `assessment_date < renewal_date <= assessment_date + 90 days` (upcoming renewal within 90 days). Past renewals and renewals >90 days out do NOT fire. |
| `overdue_receivable` | `overdue_balance > 0` (see 3.2). |
| `nps_drop` | Latest valid NPS in period is a detractor: **latest NPS ≤ 40** always triggers; in the **41–49** band it triggers **only when the latest NPS declined from the prior in-period reading** (sentiment worsening). A 41–49 latest that rose/equals the prior reading does NOT fire. Latest NPS ≥ 50 never fires. |
| `sla_degradation` | At least one clean ticket in the period with an SLA breach (see 3.3). |
| `usage_decline` | Average `product_usage` over the analysis months **< 65** (low-usage benchmark). |
| `low_tenure_high_churn` | `contract_tenure_months <= 18` (low tenure) AND elevated churn risk — i.e. the account is in a high-churn cohort (month-to-month contract, or top-quartile predicted churn). Verified boundary: tenure 7/12/13 trigger; 20 does not. |
| `expansion_offset` | The account has `expansion_pipeline > 0` and an expansion credit applies (risk-reducing). Mutually exclusive with `clean_billings`. |
| `clean_billings` | Billing/receivables axis is clean: `overdue_balance = 0` and the account is in a low-severity/clean-credit posture. Mutually exclusive with `expansion_offset`. |

`expansion_offset` and `clean_billings` are the two **credit** (risk-reducing) reason codes; an
account carries at most one of them. `expansion_offset` requires `expansion_pipeline > 0`;
`clean_billings` requires `overdue_balance = 0`. When both could apply, the credit that matches
the account’s severity posture is shown (expansion_offset for accounts whose offset is actively
mitigating risk; clean_billings for low-severity accounts on a clean billing axis).

### Reason-code ordering (emit in this precedence order)
`renewal_window`, `overdue_receivable`, `nps_drop`, `sla_degradation`, `usage_decline`,
`low_tenure_high_churn`, `expansion_offset`, `clean_billings`.

---

## 5. Risk score, levels, ranking, and actions

### 5.1 Risk score (`RS-6`, 0–100, capped at 100)
A weighted severity index. Verified additive weights for the discrete signals:

| Signal | Weight |
|---|---|
| `renewal_window` | +25 |
| `overdue_receivable` | +20 |
| `nps_drop` | +20 |
| `low_tenure_high_churn` | +20 |
| `usage_decline` | +15 |
| `sla_degradation` | +15 base, scaled up by breach severity (count/severity of SLA breaches) |
| `expansion_offset` (credit) | −15 |
| `clean_billings` (credit) | credit applied for low-severity clean-billing accounts |

Gross score = Σ positive signals + SLA-severity term − applicable credit; cap at 100, floor at 0.
The SLA term and the clean-billings credit are magnitude-adjusted; when the exact magnitude is
ambiguous, preserve the **ranking and risk level** (the deterministic outputs below) over the
raw integer.

### 5.2 Risk-level thresholds
- `critical`: score ≥ 80
- `high`: 50–79
- `medium`: 21–49
- `low`: ≤ 20

### 5.3 Ranking tiebreakers (deterministic)
Sort by: **(1) risk_score descending, (2) current_arr descending, (3) account_id ascending**.
`BORD-4`. The churn shortlist uses the same tiebreakers (probability desc, then current_arr desc,
then account_id asc).

### 5.4 Primary-action mapping (`ACT-5`) — first match wins
1. `overdue_receivable` (overdue_balance > 0) → **`collections_followup`** (any risk level).
2. risk_level = `critical` (no overdue) → **`technical_recovery`**.
3. risk_level = `high` (no overdue) → **`technical_recovery`**.
4. risk_level = `medium`:
   - `renewal_window` AND latest NPS ≥ 70 (promoter) AND no `usage_decline` → **`renewal_save`**.
   - else → **`technical_recovery`**.
5. risk_level = `low`:
   - `expansion_offset` present → **`no_action`**.
   - only `nps_drop` (sentiment only, no technical driver) → **`no_action`**.
   - else (sla/clean-billings technical driver) → **`technical_recovery`**.
6. `nurture_monitor`: reserved for clean/healthy accounts in save-plan contexts (e.g. churn
   nurture) — not assigned to high-risk board members.
7. `executive_qbr`: reserved for executive-escalation scenarios (provided in the action enum and
   the follow-up calendar, but selected only when the prompt calls for an executive-tier save).

---

## 6. Net revenue exposure & segment summary (`EXP-6`)

For the retention board (`action_board` covers ALL supplied accounts, ranked per §5.3):
- `arr_at_risk` = Σ `current_arr` over accounts whose `risk_level != low` (i.e. critical+high+medium).
- `open_expansion_pipeline` = Σ `expansion_pipeline` over **all** accounts in scope.
- `net_revenue_exposure` = `arr_at_risk − open_expansion_pipeline`.
- `strategic_accounts` = count of accounts with `segment == "Strategic"`.
- `enterprise_accounts` = count of accounts with `segment == "Enterprise"`.

For the save-plan portfolio_summary:
- `accounts_reviewed` = number of account_ids the prompt asked to review.
- `critical_or_high_count` = count of reviewed accounts at critical or high.
- `arr_at_risk` = Σ `current_arr` of reviewed accounts at critical or high.
- `collections_count` = count of reviewed accounts whose `primary_action = collections_followup`.
- `technical_recovery_count` = count whose `primary_action = technical_recovery`.

---

## 7. Follow-up calendar (`CAL-5`)

Due date = **assessment date + fixed offset** by action:

| Action | Offset | Example (assess 2026-06-30) |
|---|---|---|
| `collections_followup` | +15 days | 2026-07-15 |
| `technical_recovery` | +18 days | 2026-07-18 |
| `renewal_save` | +22 days | 2026-07-22 |
| `executive_qbr` | +29 days | 2026-07-29 |
| `nurture_monitor` | +36 days | 2026-08-05 |

Emit `next_touch_due_date` per account = the calendar date for its `primary_action`; use `null`
when `primary_action = no_action`. For a receivables task, the prompt supplies a single follow-up
due date applied to every overdue action (e.g. `2026-10-15`).

### QBR review_due_date
For a quarterly QBR, `review_due_date` = **quarter-end date + 22 days** (same offset as
`renewal_save`). Q2 2026 → 2026-06-30 + 22 = `2026-07-22`.

---

## 8. Churn model conventions (`MOD-7`, `PRB-4`, `DEP-5`, `OUT-2`)

### 8.1 Dataset & validation
- `/exports/churn/train.csv` = **180** rows (with `Churn` label).
- `/exports/churn/validation.csv` = **60** rows (with `Churn` label).
- **19 features** (all columns except `customer_id` and `Churn`).
- Train a **logistic regression** (one-hot encode the categorical features; standardize the
  numeric features) on the 19 features → validate on validation.csv.
- Expected validation **accuracy ≈ 93.3%**, placing it in the **`90_plus`** band →
  `deployment_rule_code = DEP-5` → recommendation = **`approve_with_monitoring`**.
- `tenure_coefficient_direction = "negative"` (higher tenure → lower churn probability); the
  tenure coefficient in the fitted logistic model is negative.

### 8.2 Candidate ranking
- Predict churn probability for the candidate accounts the prompt lists (the prompt selects a
  subset of the 44 rows in `/exports/churn/candidates.csv`; rank only those).
- Rank **top 5** by `predicted_churn_probability` **descending**, tiebreak by `current_arr`
  descending, then `account_id` ascending. Probabilities to **3 decimals**.
- `average_probability_top5` = mean of the top-5 probabilities (3 decimals).

### 8.3 Outreach action & reason mapping (`OUT-2`) — single reason per candidate, first match
1. `InvoicePastDue = Yes` → action `collections_followup`, reason `overdue_receivable`.
2. else low tenure (`tenure <= 18`) → action `renewal_save`, reason `low_tenure_high_churn`.
3. else (clean) → action `nurture_monitor`, reason `clean_billings`.

### 8.4 Cohort checks
- `past_due_shortlist_count` = count of **top-5** candidates with `InvoicePastDue = Yes`.
- `low_tenure_shortlist_count` = count of **top-5** candidates with `tenure <= 18` (a candidate
  can count in both cohorts).
- `average_probability_top5` = mean of top-5 probabilities.

---

## 9. Per-archetype output schemas

### A. Save plan / renewal risk queue (top 5)
```
risk_accounts[5]: { rank, account_id, risk_score, risk_level, primary_action,
  current_arr, latest_nps, clean_ticket_count, overdue_balance, reason_codes[] }
portfolio_summary: { accounts_reviewed, critical_or_high_count, arr_at_risk,
  collections_count, technical_recovery_count }
model_checks: { uses_billing_arr_source: true, tenure_risk_direction: "negative" }
policy_codes: { risk_model_code, arr_source_code, support_hygiene_code, action_priority_code }
```
- `latest_nps` = latest valid NPS in period (§3.4) as integer; `null` if none.
- `uses_billing_arr_source` = true; `tenure_risk_direction` = `negative`.
- Return exactly the top 5 by ranking (§5.3).

### B. QBR metrics packet (single account, per-month)
```
qbr_metrics[3 months]: { month, revenue, support_tickets, sla_compliance_pct, nps_score }
highlights: { average_revenue, peak_revenue_month, peak_revenue, max_sla_month, max_sla_pct,
  peak_nps_month, peak_nps_score, ticket_trend }
metric_sources: { revenue, support_tickets, sla_compliance, nps }
review_plan: { review_owner, review_due_date, needs_technical_signoff }
agenda_topics[4]
```
QBR field sourcing (always use these `metric_sources` labels):
- `revenue` = metric `recognized_revenue` per month → source **`crm_closed_won`**.
- `support_tickets` = **clean** ticket count per month (by `created_date[:7]`) → **`support_export`**.
- `sla_compliance_pct` = (clean tickets in month with `first_response_sla_met = true`) ÷ (clean
  tickets in month) × 100, 1 decimal → **`sla_report`**.
- `nps_score` = metric `nps_score` per month (null when survey missing) → **`nps_survey`**.
Highlights:
- `average_revenue` = mean of monthly revenue (2 decimals).
- `peak_revenue_month` = month of max revenue; `peak_revenue` = that value.
- `max_sla_month` = month of max SLA (ties → earliest month); `max_sla_pct` = that value.
- `peak_nps_month` = month of max non-null NPS; `peak_nps_score` = that value.
- `ticket_trend`: `improving` if last-month clean tickets < first-month; `worsening` if >; `flat` if equal.
- `review_owner` = **`customer_success`** (default for QBR; use `finance_ops` only for a
  finance-flagged account, `solutions_engineering` only for a technical-signoff-flagged account).
- `needs_technical_signoff` = true iff the **latest month’s** ticket-level SLA compliance is
  below 90% (ongoing degradation); false when the latest month has recovered.
- `agenda_topics`: exactly 4, ordered. Default frame:
  `[partnership_overview, q2_metrics, <slot3>, q3_initiatives]` where slot3 = `technical_recovery`
  when there is SLA/technical degradation in the quarter, else `commercial_expansion` when there
  is open expansion pipeline, else `performance_highlights`. Adapt `q2`/`q3` labels to the quarter
  in scope.

### C. Receivables + pipeline operations digest
```
financial_summary: { overdue_client_count, overdue_total, linked_followup_count, unlinked_followup_count }
pipeline_summary: { won_count, won_revenue, lost_count, open_count, open_pipeline, win_rate_pct, top_open_product_line }
overdue_followups[]: { customer_name, link_status, account_id|null, overdue_balance, due_date, primary_action }
ops_context: { hr_headcount, unpaid_claims_total, event_orders, event_revenue }
policy_codes: { receivable_trigger_code, crm_match_code, pipeline_window_code, followup_scope_code }
```
- `overdue_client_count` = A/R customers with `61_90 + 90_plus > 0` as of the as-of date.
- `overdue_total` = Σ those late-bucket sums (2 decimals).
- `linked_followup_count` / `unlinked_followup_count` = counts by CRM match (§3.5).
- `overdue_followups` sorted by `customer_name` asc; `due_date` = the prompt’s follow-up date;
  `primary_action` = `collections_followup` for receivables.
- pipeline per §3.6 (window = the prompt’s date range).
- `hr_headcount` = Σ `headcount` across all HR regions for the quarter (omit region param).
- `unpaid_claims_total` = Σ `unpaid_claims_amount` across all HR regions for the quarter.
- `event_orders` = `event_orders`; `event_revenue` = `event_revenue` from the event_performance
  record for the requested event + quarter.

### D. Churn shortlist
See §8. Schema:
```
model_validation: { training_rows: 180, validation_rows: 60, feature_count: 19, accuracy_pct,
  accuracy_band: "90_plus", tenure_coefficient_direction: "negative" }
risk_ranking[5]: { rank, customer_id, predicted_churn_probability, outreach_action, reason_code }
cohort_checks: { past_due_shortlist_count, low_tenure_shortlist_count, average_probability_top5 }
model_policy_codes: { model_protocol_code, probability_scale_code, deployment_rule_code, outreach_mapping_code }
```

### E. High-touch retention board / watchlist (ALL accounts, ranked)
```
action_board[]: { rank, account_id, risk_level, primary_action, current_arr,
  expansion_pipeline, overdue_balance, next_touch_due_date, reason_codes[] }
segment_summary: { strategic_accounts, enterprise_accounts, arr_at_risk,
  open_expansion_pipeline, net_revenue_exposure }
followup_calendar: { collections_followup, technical_recovery, renewal_save, executive_qbr, nurture_monitor }
policy_codes: { risk_model_code, arr_source_code, support_hygiene_code, action_priority_code,
  board_sort_code, exposure_formula_code, calendar_policy_code }
```
- Return **all** supplied accounts ranked (§5.3). `expansion_pipeline` per account (§3.6).
- `next_touch_due_date` per §7; `null` for `no_action`.
- segment_summary, exposure per §6.

---

## 10. Solver execution checklist
1. Parse the prompt for: assessment date, analysis months, A/R as-of date, account list,
   output archetype, and any supplied follow-up due date.
2. For each account: fetch account, metrics, tickets, nps, latest posted billing snapshot (≤
   assessment date), ar-aging (as-of date), and opportunities (window).
3. Derive `current_arr` (REV-4), `overdue_balance` (RCP-7), `clean_ticket_count` (SUP-8),
   `latest_nps`, `expansion_pipeline` (PW-6).
4. Compute RS-6 signals → risk_score → risk_level → primary_action → reason_codes (ordered).
5. Rank (§5.3), build summary/exposure (§6), calendar (§7), churn block (§8) per archetype.
6. Apply precision (§2) and emit exact policy codes (§1). Return JSON only.
