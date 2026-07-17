# SKILL: ApexCloud Retention Operations — CRM Analytics SOP

A reusable procedure for solving ApexCloud Retention Operations analytics tasks
(renewal-risk queues, QBR metric packets, receivables/pipeline reviews, churn
validation/ranking, and high-touch retention boards). Every task gives you one
prompt plus an `answer_template.json`; your job is to fill every template field
exactly, with the right values, precision, enum strings, and controlled
`policy_codes`. This file captures the company's standard conventions for each.

---

## 1. Data access (the remote API is the ONLY source of truth)

Use the ApexCloud Retention Operations HTTP API. A prompt may name a localhost
URL or an `env/setup.sh`; ignore that and use the live base URL configured for
your run. Do not start a local service.

Read-only endpoints (HTTP GET, return JSON unless noted):

- `GET /api/health` — row counts + seed (sanity check the dataset is loaded).
- `GET /api/accounts` — all account profiles (44). Each: `account_id`,
  `legal_name`, `display_name`, `account_aliases[]`, `billing_arr_current`,
  `crm_arr`, `contract_tenure_months`, `renewal_date`, `segment`,
  `lifecycle_status`, `region`, `product_plan`, `csm_owner`.
- `GET /api/accounts/<id>` — one account profile.
- `GET /api/accounts/<id>/metrics?start=YYYY-MM&end=YYYY-MM` — monthly metrics:
  `month`, `recognized_revenue`, `support_ticket_count`, `sla_compliance`,
  `nps_score` (may be null in a month with no survey), `product_usage`,
  `active_seats`, `survey_status`, `quarter`.
- `GET /api/accounts/<id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` — ticket rows:
  `ticket_id`, `created_date`, `severity` (P1..P4), `status` (open/closed),
  `is_duplicate`, `is_spam`, `first_response_sla_met`, `resolution_sla_met`,
  `product_area`.
- `GET /api/accounts/<id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` — NPS rows:
  `response_id`, `response_date`, `score`, `retracted`, `survey_channel`.
- `GET /api/billing/snapshots?account_id=<id>` — quarterly billing snapshots:
  `as_of`, `billing_arr`, `mrr`, `posted`, `legal_name`, `source`.
- `GET /api/finance/ar-aging?as_of=YYYY-MM-DD` — A/R aging rows keyed by
  `customer_name` (a LEGAL name, not an account_id): `current`, `1_30`, `31_60`,
  `61_90`, `90_plus`, `region`, `quarter`.
- `GET /api/opportunities?start=YYYY-MM-DD&end=YYYY-MM-DD` — pipeline,
  pre-filtered to the date window: `account_id`, `account_legal_name`, `amount`,
  `close_date`, `created_date`, `product_line`, `region`, `stage`
  (Prospecting / Discovery / Proposal / Negotiation / Closed Won / Closed Lost),
  `state` (open / closed).
- `GET /api/hr/summary?quarter=YYYY-Qn` — one row per region: `headcount`,
  `unpaid_claims_amount`, `unpaid_claims_count`, `open_advances_amount`,
  `attendance_rate`, `leave_liability_hours`, `high_absence_employees`.
- `GET /api/events/performance?event=<id>&quarter=YYYY-Qn` — event totals:
  `event_orders`, `event_revenue`, `completed_orders`, `cancelled_orders`,
  `pending_orders`, `refunded_orders`, `product_revenue`.
- `GET /exports/churn/train.csv`, `/validation.csv`, `/candidates.csv` — churn ML
  exports (Telco-style schema).

Performance note: per-account endpoints are slow one-by-one. Download all needed
account endpoints in parallel (background curls into files), then compute locally.

---

## 2. Output conventions (apply to EVERY task)

- Currency: 2 decimals. Percentages: 1 decimal. Counts, NPS, risk scores: integers.
- Churn probabilities: 3 decimals, on a 0..1 scale.
- Use the controlled enum strings exactly as printed in the template (lowercase
  snake_case). Never invent enum values.
- When a template field is `null` or a month has no survey, preserve `null`
  rather than coercing to 0.
- Echo provided constants (due dates, quarter, as-of dates) verbatim.

---

## 3. Source-precedence and data-hygiene rules

### Revenue / ARR sources
- **Account ARR for risk/board tasks (`current_arr`)** = `billing_arr_current`
  from the account profile. This is the "billing ARR source" (NOT `crm_arr`).
  When a task has a `uses_billing_arr_source` flag, set it `true`.
  `tenure_risk_direction` = `negative` (longer tenure ⇒ lower risk).
- **Monthly revenue for a QBR packet** = `recognized_revenue` from the monthly
  metrics endpoint. Its source enum is `crm_closed_won` (do NOT use
  `billing_snapshot` for monthly recognized revenue).
- `crm_arr` is the CRM figure and is generally LOWER than billing ARR for some
  accounts; only use it if a task explicitly asks for the CRM value.
- Billing snapshots (`/api/billing/snapshots`) are point-in-time quarterly ARR;
  use them only when a task explicitly wants snapshot ARR.

### Support-ticket hygiene
- A "clean" ticket count EXCLUDES rows where `is_duplicate == true` OR
  `is_spam == true`. (Open vs closed does NOT affect the clean count.)
- The metrics endpoint `support_ticket_count` is the RAW monthly count; for a
  QBR "support_tickets" per month, use the metrics endpoint value directly.
  For a risk/board "clean_ticket_count", compute it from the tickets endpoint
  excluding duplicates and spam over the analysis window.
- `sla_compliance` for a QBR comes from the metrics endpoint (the canonical SLA
  report). Do NOT recompute SLA% from individual ticket flags — it will not match.

### NPS hygiene
- Ignore NPS responses where `retracted == true`.
- "latest_nps" = the score of the most recent non-retracted response by
  `response_date` within the window. (This matches the last populated monthly
  `nps_score`; months with no survey carry `null`.)

### A/R overdue definition (CRITICAL — confirmed)
- "Overdue" / "older aging buckets" = `61_90 + 90_plus` ONLY.
- Do NOT include `current`, `1_30`, or `31_60` in the overdue/`overdue_balance`
  figure. This applies to the receivables review AND to the `overdue_balance`
  field on risk queues and retention boards.

---

## 4. CRM legal-name vs alias matching (receivables linking)

When linking A/R `customer_name` rows to CRM accounts:
- Match by EXACT `legal_name` equality to `accounts[].legal_name`.
- Do NOT fuzzy-match, normalize, or match on `account_aliases` / `display_name`.
  Distinct legal entities such as "...Subsidiary LLC", "North Star Finance
  Services" (two words), "...Claims Ltd.", "...Canada", "...Foundation" must
  remain UNLINKED even though they resemble a parent account.
- `link_status` = `"linked"` (exact legal-name hit) or `"unlinked"` (no hit).
- `account_id` = the matched id, or `null` when unlinked.

---

## 5. Pipeline / win-rate / open-pipeline rules

Call `/api/opportunities` with the task's date window (it returns only opps in
that window — no extra filtering needed). Then:
- `won_count` = stage == "Closed Won"; `won_revenue` = sum of their `amount`.
- `lost_count` = stage == "Closed Lost".
- `open_count` = `state == "open"`; `open_pipeline` = sum of open `amount`.
- `win_rate_pct` = 100 * won / (won + lost), 1 decimal. EXCLUDE open deals from
  the denominator.
- `top_open_product_line` = the `product_line` with the largest summed `amount`
  among OPEN opps.

### Expansion pipeline (retention board)
- `expansion_pipeline` per account = sum of `amount` for that account's OPEN opps
  whose `close_date` falls inside the task's quarter window.
- `open_expansion_pipeline` (summary) = sum of those across all board accounts.
- An account with an open in-window opp earns the `expansion_offset` reason code.

---

## 6. Retention risk model + action/reason mapping

Use a transparent additive score over the analysis window, then derive level and
action. Signals (each contributes; presence also emits a reason code):

| Signal | Condition | Reason code |
|---|---|---|
| Overdue receivable | `overdue_balance` (61+ buckets) material (> ~5k strong, > 0 mild) | `overdue_receivable` |
| Low tenure | `contract_tenure_months <= 12` | `low_tenure_high_churn` |
| SLA degradation | avg monthly `sla_compliance` < 90 | `sla_degradation` |
| NPS drop | latest non-retracted NPS < 40 | `nps_drop` |
| Usage decline | last-month `product_usage` < first-month | `usage_decline` |
| Renewal window | `renewal_date` within ~90 days of the assessment date | `renewal_window` |
| Expansion present | open in-window expansion opp exists | `expansion_offset` |
| None of the above | — | `clean_billings` |

Also treat `lifecycle_status` of `renewal_risk` or `paused` as an elevating
factor when present.

- `risk_level` (controlled enum) bands by score: highest band `critical`, then
  `high`, `medium`, `low`. Higher cumulative distress ⇒ higher level.
- Ranking / board order: sort by descending risk (score / level), tie-break by
  `current_arr` descending. Renewal-risk queues return the TOP 5; retention
  boards return ALL requested accounts in this order.

### Primary-action mapping (priority order, first match wins)
1. Material overdue (61+ balance) ⇒ `collections_followup`
2. SLA degraded (avg < 90) / technical distress ⇒ `technical_recovery`
3. Critical + high-ARR account ⇒ `executive_qbr`
4. Inside renewal window ⇒ `renewal_save`
5. Otherwise ⇒ `nurture_monitor`

Action enum: `executive_qbr | collections_followup | technical_recovery |
renewal_save | nurture_monitor | no_action`.
Reason-code enum: `overdue_receivable | low_tenure_high_churn | sla_degradation |
nps_drop | usage_decline | renewal_window | expansion_offset | clean_billings`.

### Portfolio / segment summaries
- `accounts_reviewed` = count of accounts in scope.
- `critical_or_high_count` = accounts whose level is critical or high.
- `arr_at_risk` = sum of `current_arr` for critical/high accounts.
- `collections_count` / `technical_recovery_count` = accounts whose primary
  action is that value.
- `strategic_accounts` / `enterprise_accounts` = count by `segment` field.
- `open_expansion_pipeline` = sum of all expansion pipelines.
- `net_revenue_exposure` = `arr_at_risk` net of the open expansion pipeline
  (exposure reduced by expansion that offsets it).

### Follow-up calendar / due dates
- When the prompt gives a due date per action, build `followup_calendar` from
  those verbatim, and set each row's `next_touch_due_date` to the due date that
  matches that row's `primary_action`.

---

## 7. QBR metrics packet rules

- Build `qbr_metrics` per month from the metrics endpoint: `revenue` =
  `recognized_revenue` (2 dp), `support_tickets` = `support_ticket_count`,
  `sla_compliance_pct` = `sla_compliance` (1 dp), `nps_score` = `nps_score`
  (integer, or `null` if no survey that month).
- `highlights`: `average_revenue` = mean of monthly revenue (2 dp);
  `peak_revenue_month`/`peak_revenue` from max revenue; `max_sla_month`/
  `max_sla_pct` from max SLA; `peak_nps_month`/`peak_nps_score` from max NPS;
  `ticket_trend` = compare last vs first month support_tickets — fewer ⇒
  `improving`, more ⇒ `worsening`, equal ⇒ `flat`.
- `metric_sources` (source enum vocabulary: `crm_closed_won`, `support_export`,
  `sla_report`, `nps_survey`, `billing_snapshot`, `ar_aging`, `pipeline_crm`,
  `event_dashboard`, `hr_report`): map revenue ⇒ `crm_closed_won`,
  support_tickets ⇒ `support_export`, sla_compliance ⇒ `sla_report`,
  nps ⇒ `nps_survey`.
- `review_plan`: `review_owner` from `solutions_engineering | customer_success |
  finance_ops` — default `customer_success` for a healthy account, escalate to
  `solutions_engineering` only when there is unresolved technical/SLA distress;
  echo the provided `review_due_date`; `needs_technical_signoff` = true only when
  the account has real technical distress (SLA below target / unresolved
  high-severity incidents), otherwise false.
- `agenda_topics`: exactly four ordered values from `partnership_overview,
  q2_metrics, performance_highlights, q3_initiatives, technical_recovery,
  commercial_expansion`. Always lead with `partnership_overview, q2_metrics,
  performance_highlights`; choose the 4th by account posture — growing/healthy ⇒
  `commercial_expansion`, support-distressed ⇒ `technical_recovery`, otherwise
  `q3_initiatives`.

---

## 8. Churn model validation + ranking procedure

Exports schema (Telco-style): `customer_id`, `tenure`, `MonthlyCharges`,
`TotalCharges`, `Contract`, `PaymentMethod`, `PaperlessBilling`, `Partner`,
`Dependents`, `OnlineSecurity`, `OnlineBackup`, `DeviceProtection`, `TechSupport`,
`StreamingTV`, `StreamingMovies`, `SupportTickets90d`, `NPSLast`, `UsageTrendPct`,
`InvoicePastDue`, `ActiveSeatRatio`, and `Churn` (target, train/validation only).

`model_validation`:
- `training_rows` = data rows in train.csv; `validation_rows` = rows in
  validation.csv (typically 180 and 60).
- `feature_count` = number of feature columns = total columns minus
  `customer_id` and `Churn` (= 19 for this schema).
- Fit a standard logistic-regression classifier: one-hot encode the categorical
  columns, standardize the numeric columns, fit on train, score on validation.
- `accuracy_pct` = validation accuracy (1 dp). `accuracy_band` from
  `below_70 | 70_to_79 | 80_to_89 | 90_plus`. NOTE: the validation set is highly
  imbalanced (~93% are non-churn), so any reasonable model lands in the
  **`90_plus`** band — verify, but expect `90_plus`.
- `tenure_coefficient_direction` = `negative` (the tenure coefficient is
  negative — more tenure, less churn).

`risk_ranking` (top 5 of the requested candidates by predicted churn probability):
- Score the candidate rows with the trained model; `predicted_churn_probability`
  is the model's positive-class probability, 3 dp, sorted descending.
- The strongest churn signals are: short `tenure`, `InvoicePastDue == Yes`,
  low `NPSLast`, negative `UsageTrendPct`, Month-to-month `Contract`. A
  short-tenure month-to-month account with past-due invoices and low NPS is the
  clear top risk.
- `outreach_action` / `reason_code` mapping (priority order):
  past due ⇒ `collections_followup` / `overdue_receivable`; low tenure (<=12) ⇒
  `renewal_save` / `low_tenure_high_churn`; negative usage ⇒ `technical_recovery`
  / `usage_decline`; low NPS ⇒ `renewal_save` / `nps_drop`; else
  `nurture_monitor` / `clean_billings`.

`cohort_checks`:
- `past_due_shortlist_count` = candidates with `InvoicePastDue == Yes`.
- `low_tenure_shortlist_count` = candidates with `tenure <= 12`.
- `average_probability_top5` = mean of the top-5 predicted probabilities (3 dp).

---

## 9. HR / event operations context

- `hr_headcount` = SUM of `headcount` across ALL regions for the quarter.
- `unpaid_claims_total` = SUM of `unpaid_claims_amount` across all regions.
- `event_orders` / `event_revenue` = read directly from the event-performance
  endpoint row for the requested event/quarter.

---

## 10. Controlled `policy_codes` by scenario family

Set the `policy_codes` block exactly as below for each family. These codes encode
the company's standard policy for each scenario; use these exact values.

- **Renewal-risk queue / retention board (risk family)**:
  - `risk_model_code`: `RS-6`
  - `arr_source_code`: `REV-4`
  - `support_hygiene_code`: `SUP-8`
  - `action_priority_code`: `ACT-5`
  - (board only) `board_sort_code`: `BORD-4`
  - (board only) `exposure_formula_code`: `EXP-6`
  - (board only) `calendar_policy_code`: `CAL-5`

- **Receivables & pipeline review**:
  - `receivable_trigger_code`: `RCP-7`
  - `crm_match_code`: `CM-5`
  - `pipeline_window_code`: `PW-6`
  - `followup_scope_code`: `FS-4`

- **Churn validation & ranking**:
  - `model_protocol_code`: `MOD-7`
  - `probability_scale_code`: `PRB-4`
  - `deployment_rule_code`: `DEP-5`
  - `outreach_mapping_code`: `OUT-6`

(QBR metric packets have no `policy_codes` block.)

---

## 11. Common pitfalls / exclusion rules

- Overdue = 61+ buckets only. Including `31_60` or `1_30` inflates totals and is
  wrong.
- CRM linking is EXACT legal-name only — subsidiaries and look-alike entities
  stay unlinked with `account_id: null`.
- Use `billing_arr_current` (not `crm_arr`) for account ARR in risk/board tasks;
  use monthly `recognized_revenue` (source `crm_closed_won`) for QBR revenue.
- Clean ticket count excludes duplicates and spam (not open/closed status). Do
  not recompute SLA% from ticket flags for a QBR — use the metrics SLA value.
- Drop retracted NPS responses; take the latest non-retracted by date.
- Win-rate excludes open deals from the denominator.
- HR/headcount and unpaid-claims totals are sums across ALL regions unless a
  single region is requested.
- Respect precision (currency 2 dp, pct 1 dp, probabilities 3 dp) and exact enum
  strings; preserve `null`s.
- Return JSON only, matching the template's keys and shape exactly; sort lists as
  instructed (e.g., receivables follow-ups by `customer_name` ascending; risk
  queues/boards by descending risk then ARR).
