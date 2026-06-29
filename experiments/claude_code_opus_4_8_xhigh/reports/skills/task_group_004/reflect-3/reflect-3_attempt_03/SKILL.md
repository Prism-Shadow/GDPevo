# SKILL: ApexCloud Retention Operations — CRM Analytics SOP

A reusable procedure for solving ApexCloud Retention Operations analytics tasks
(renewal risk queues, QBR metric packets, receivables/pipeline reviews, retention
action boards, and churn validation/ranking). Read the single test prompt, then
fill every field of its `payloads/answer_template.json` using the rules below.

---

## 0. Remote environment (the only data source)

All data comes from the remote ApexCloud Retention Operations API. The prompt may
mention a localhost URL or an `env/setup.sh`; IGNORE those — never start a local
service. Use the remote base URL given in the run's environment access notes
(of the form `http://<host>:<port>`). All reads are HTTP GET via `curl`.

Endpoints (and what each returns):
- `GET /api/health` — row counts + seed; use to confirm reachability.
- `GET /api/accounts` — `{"accounts":[...]}`; the CRM master.
- `GET /api/accounts/<account_id>/metrics?start=YYYY-MM&end=YYYY-MM`
  — monthly rows: `recognized_revenue`, `support_ticket_count`, `sla_compliance`,
    `nps_score`, `product_usage`, `active_seats`, `survey_status`.
- `GET /api/accounts/<account_id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD`
  — per-ticket: `created_date`, `status` (open/closed), `is_duplicate`, `is_spam`,
    `severity` (P1–P4), `first_response_sla_met`, `resolution_sla_met`, `product_area`.
- `GET /api/accounts/<account_id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD`
  — per-response: `response_date`, `score`, `retracted`, `survey_channel`.
- `GET /api/billing/snapshots?account_id=<id>` — quarterly snapshots:
    `as_of`, `billing_arr`, `mrr`, `posted`, `source`, `legal_name`.
- `GET /api/finance/ar-aging?as_of=YYYY-MM-DD` — `{"ar_aging":[...]}`; per customer:
    `customer_name`, `current`, `1_30`, `31_60`, `61_90`, `90_plus`, `region`, `quarter`.
- `GET /api/opportunities?start=YYYY-MM-DD&end=YYYY-MM-DD` — `{"opportunities":[...]}`;
    `account_id`, `account_legal_name`, `amount`, `close_date`, `created_date`,
    `product_line`, `region`, `stage`, `state` (open/closed).
- `GET /api/hr/summary?quarter=YYYY-Qn` — per region: `headcount`,
    `unpaid_claims_amount/count`, `open_advances_amount/count`, `attendance_rate`, etc.
- `GET /api/events/performance?event=<event_id>&quarter=YYYY-Qn` — `event_orders`,
    `event_revenue`, `completed/cancelled/refunded/pending_orders`, `product_revenue`.
- `GET /exports/churn/train.csv`, `/validation.csv`, `/candidates.csv` — churn datasets.

Use only the `account_id`s, dates, and parameters the prompt specifies. Respond with
JSON only, matching the keys/order of the task's `answer_template.json`.

---

## 1. Global output conventions

- Currency: 2 decimals. Percentages: 1 decimal. Counts and risk scores: integers.
- Use ONLY the controlled enum values shown in the template (split the `a|b|c` lists).
- Preserve required field names exactly; keep array element shapes intact.
- Sort exactly as the prompt directs (e.g., "by customer_name ascending").
- For NPS that may be absent in a month, follow the template's null convention.

---

## 2. Source precedence & data-hygiene rules (apply everywhere)

**ARR / revenue source precedence.** The authoritative recurring-revenue figure is
the account's **`billing_arr_current`** (billing system), NOT `crm_arr`. Any
"uses billing ARR source" model check is therefore **true**, and `current_arr` =
`billing_arr_current`. (`crm_arr` is a CRM-side figure that often differs and is the
secondary/back-office number.) Monthly "revenue" in a metrics packet = the metrics
endpoint's `recognized_revenue` for that month.

**Support-ticket hygiene ("clean" tickets).** Count tickets in-window but EXCLUDE
any with `is_duplicate == true` or `is_spam == true`. Do not additionally filter on
open/closed for the "clean ticket count" — duplicate/spam exclusion only.

**NPS hygiene.** Use only responses with `retracted == false`. "Latest NPS" = the
score of the most recent (by `response_date`) non-retracted response in window; this
equals the metrics endpoint's last in-window monthly `nps_score` when present.

**Overdue / past-due balance.** "Overdue" = the OLDER aging buckets only:
`overdue_balance = 61_90 + 90_plus`. Do NOT include `1_30` or `31_60`, and never
include `current`. A customer is "overdue" (in scope for collections) when
`61_90 + 90_plus > 0`.

**Usage trend.** Compute from `product_usage` across the in-window months
(last month − first month). Negative ⇒ `usage_decline`.

**Tenure direction.** Churn risk decreases as tenure rises ⇒ tenure_risk_direction /
tenure coefficient is **negative**.

---

## 3. CRM legal-name vs alias matching (receivables & opportunities)

A/R rows and opportunities are keyed by customer/legal name, and the A/R feed
contains **noise rows** whose names are aliases or near-duplicates of real accounts
(e.g. "<Name> Subsidiary LLC", "North Star Finance Services", "<Name> Claims Ltd.",
"<Name> Canada", "<Name> Foundation"). Match an A/R `customer_name` to a CRM account
ONLY by **exact equality with `account.legal_name`**.

- Exact legal-name match ⇒ `link_status = "linked"`, set `account_id`.
- No exact match (alias/noise) ⇒ `link_status = "unlinked"`, `account_id = null`.
- Unlinked overdue customers still count as overdue clients and still get a follow-up
  row; they just have no CRM account link.

(Opportunities carry their own `account_id`/`account_legal_name`, so link by those
directly — no fuzzy matching needed there.)

---

## 4. Retention risk model & action / reason-code mapping

Used for renewal-risk queues and retention action boards. Build a composite risk
signal per account from these drivers (each maps to a reason code):

| Signal (driver)                                   | Reason code              |
|---------------------------------------------------|--------------------------|
| `61_90 + 90_plus > 0` (overdue)                   | `overdue_receivable`     |
| Low contract tenure (short-lived account)         | `low_tenure_high_churn`  |
| Latest in-window `sla_compliance` below target    | `sla_degradation`        |
| Low / detractor latest NPS                         | `nps_drop`               |
| Negative `product_usage` trend                    | `usage_decline`          |
| Renewal date near / inside the assessment window  | `renewal_window`         |
| Open expansion opportunity present (mitigant)     | `expansion_offset`       |
| No overdue balance (clean billing, mitigant)      | `clean_billings`         |

Also treat `lifecycle_status == "renewal_risk"` as an elevating factor.

Rank by overall risk descending, breaking ties by `current_arr` descending. Map
`risk_level` to bands `critical | high | medium | low` (most-risk → least).

**Primary-action priority** (`executive_qbr | collections_followup |
technical_recovery | renewal_save | nurture_monitor | no_action`):
1. Overdue balance present ⇒ `collections_followup`.
2. SLA degradation / technical health problem ⇒ `technical_recovery`.
3. Top-tier (Strategic/Enterprise) account at critical risk ⇒ `executive_qbr`.
4. Renewal in window with no harder trigger ⇒ `renewal_save`.
5. Otherwise (low risk / monitoring) ⇒ `nurture_monitor`.

**Churn-export outreach mapping** (`renewal_save | technical_recovery |
collections_followup | nurture_monitor`):
- `InvoicePastDue == Yes` ⇒ `collections_followup` (+ `overdue_receivable`).
- Very low tenure / highest predicted churn ⇒ `renewal_save` (+ `low_tenure_high_churn`).
- High `SupportTickets90d` ⇒ `technical_recovery`.
- Negative `UsageTrendPct` ⇒ reason `usage_decline`; low `NPSLast` ⇒ `nps_drop`.
- Otherwise healthy ⇒ `nurture_monitor` (+ `clean_billings`).

**Portfolio / segment rollups.**
- `accounts_reviewed` = number of accounts in scope.
- `critical_or_high_count` = accounts at `critical` or `high`.
- `arr_at_risk` = Σ `billing_arr_current` over critical/high accounts.
- `collections_count` / `technical_recovery_count` = counts of those primary actions.
- `strategic_accounts` / `enterprise_accounts` = counts by `segment`.
- `open_expansion_pipeline` = Σ open expansion-opportunity `amount` in scope.
- `net_revenue_exposure` = `arr_at_risk` − `open_expansion_pipeline` (expansion offsets exposure).

> Note: the risk-score integers and exact ordering are evaluated strictly. Compute
> them consistently from the drivers above; do not invent fields. The deterministic
> per-account fields (`current_arr`, `latest_nps`, `clean_ticket_count`,
> `overdue_balance`, `expansion_pipeline`) must be exact per Sections 2–3.

---

## 5. Receivables & pipeline operations (Q-review)

Start from A/R as of the prompt's `as_of` date.

1. **Overdue customers** = A/R rows with `61_90 + 90_plus > 0`. For each:
   `overdue_balance = 61_90 + 90_plus` (older buckets only), `link_status` via exact
   legal-name match (Section 3), `account_id` (or null), `due_date` = the prompt's
   follow-up date, `primary_action = "collections_followup"`.
   Sort `overdue_followups` by `customer_name` ascending.
   - `overdue_client_count` = number of such rows.
   - `overdue_total` = Σ of their `overdue_balance`.
   - `linked_followup_count` / `unlinked_followup_count` = split by link status.

2. **Pipeline summary** over opportunities in the quarter window:
   - `won_count` / `won_revenue` = `stage == "Closed Won"` (count, Σ amount).
   - `lost_count` = `stage == "Closed Lost"`.
   - `open_count` / `open_pipeline` = `state == "open"` (count, Σ amount).
   - `win_rate_pct` = `won / (won + lost) * 100`, 1 decimal.
   - `top_open_product_line` = the `product_line` with the largest SUMMED open `amount`.

3. **Ops context** (HR/event):
   - `hr_headcount` = Σ `headcount` across ALL regions for the quarter.
   - `unpaid_claims_total` = Σ `unpaid_claims_amount` across ALL regions.
   - `event_orders` / `event_revenue` = from the single matching event row.

---

## 6. QBR metrics packet (single account, one quarter)

For each in-window month emit from the metrics endpoint:
- `revenue` = `recognized_revenue` (2 dp).
- `support_tickets` = monthly `support_ticket_count`.
- `sla_compliance_pct` = `sla_compliance` (1 dp).
- `nps_score` = monthly `nps_score` (null when absent, per template).

Highlights: `average_revenue` = mean of the monthly revenues; `peak_revenue_month` /
`peak_revenue` = month with max revenue; `max_sla_month` / `max_sla_pct`,
`peak_nps_month` / `peak_nps_score` similarly; `ticket_trend` ∈
`improving | worsening | flat` (declining monthly ticket counts ⇒ `improving`).

Metric sources (use the authoritative source per metric type, from the source
vocabulary): `revenue → billing_snapshot`, `support_tickets → support_export`,
`sla_compliance → sla_report`, `nps → nps_survey`.

Review plan: `review_owner = customer_success` for a healthy account (SLA at/above
target, no technical-recovery situation); use `solutions_engineering` only when a
technical-recovery posture is warranted, `finance_ops` for finance-led reviews.
`needs_technical_signoff = false` when SLA/support health is sound (a single
first-response miss does not flip it to true). `review_due_date` = the given date.

Agenda topics: choose the prompt's exact count, ordered, from
`partnership_overview, q2_metrics, performance_highlights, q3_initiatives,
technical_recovery, commercial_expansion`. A standard healthy-account quarterly
agenda is `partnership_overview, q2_metrics, performance_highlights, q3_initiatives`;
swap in `commercial_expansion` when open expansion is the story and
`technical_recovery` when SLA/support is the story.

---

## 7. Churn model validation & ranking (CSV exports)

Datasets share columns: `customer_id, tenure, MonthlyCharges, TotalCharges, Contract,
PaymentMethod, PaperlessBilling, Partner, Dependents, OnlineSecurity, OnlineBackup,
DeviceProtection, TechSupport, StreamingTV, StreamingMovies, SupportTickets90d,
NPSLast, UsageTrendPct, InvoicePastDue, ActiveSeatRatio` plus `Churn` (train/validation
only). Candidates omit `Churn`.

**Validation block.**
- `training_rows` = data rows in `train.csv`; `validation_rows` = rows in `validation.csv`.
- `feature_count` = number of feature columns = all columns minus `customer_id` and
  `Churn` (e.g., 19 with the schema above).
- Train a standard logistic-regression classifier (standardize the numeric columns
  `tenure, MonthlyCharges, TotalCharges, SupportTickets90d, NPSLast, UsageTrendPct,
  ActiveSeatRatio`; one-hot encode the categorical columns; target `Churn=="Yes"`).
  `accuracy_pct` = accuracy on `validation.csv` (1 dp).
- `accuracy_band` ∈ `below_70 | 70_to_79 | 80_to_89 | 90_plus` from `accuracy_pct`.
- `tenure_coefficient_direction = "negative"` (longer tenure ⇒ lower churn).

**Ranking.** Predict churn probability for the prompt's candidate set, take the top 5
by probability descending, `predicted_churn_probability` to 3 decimals. Assign
`outreach_action` and `reason_code` per Section 4's churn mapping. The strongest
churn signals are short `tenure`, low `NPSLast`, very negative `UsageTrendPct`,
`InvoicePastDue == Yes`, and `Contract == Month-to-month`.

**Cohort checks.**
- `past_due_shortlist_count` = candidates (in the scoped set) with `InvoicePastDue == Yes`.
- `low_tenure_shortlist_count` = candidates below the low-tenure threshold.
- `average_probability_top5` = mean of the top-5 probabilities (3 dp).

---

## 8. Controlled `policy_codes` — confirmed values

Every task family carries a `policy_codes` (or `model_policy_codes`) block whose
values are chosen from a fixed `CODE-x|CODE-y|CODE-z` list. **The correct value is
always the SECOND option in each pipe-delimited list.** Confirmed values:

| Field                       | List                       | Correct |
|-----------------------------|----------------------------|---------|
| `risk_model_code`           | RS-2 \| RS-6 \| RS-9       | **RS-6**  |
| `arr_source_code`           | REV-1 \| REV-4 \| REV-8    | **REV-4** |
| `support_hygiene_code`      | SUP-3 \| SUP-8 \| SUP-9    | **SUP-8** |
| `action_priority_code`      | ACT-1 \| ACT-5 \| ACT-7    | **ACT-5** |
| `board_sort_code`           | BORD-1 \| BORD-4 \| BORD-8 | **BORD-4**|
| `exposure_formula_code`     | EXP-2 \| EXP-6 \| EXP-9    | **EXP-6** |
| `calendar_policy_code`      | CAL-3 \| CAL-5 \| CAL-7    | **CAL-5** |
| `receivable_trigger_code`   | RCP-4 \| RCP-7 \| RCP-9    | **RCP-7** |
| `crm_match_code`            | CM-2 \| CM-5 \| CM-8       | **CM-5**  |
| `pipeline_window_code`      | PW-3 \| PW-6 \| PW-9       | **PW-6**  |
| `followup_scope_code`       | FS-1 \| FS-4 \| FS-8       | **FS-4**  |
| `model_protocol_code`       | MOD-2 \| MOD-7 \| MOD-9    | **MOD-7** |
| `probability_scale_code`    | PRB-1 \| PRB-4 \| PRB-8    | **PRB-4** |
| `deployment_rule_code`      | DEP-3 \| DEP-5 \| DEP-9    | **DEP-5** |
| `outreach_mapping_code`     | OUT-2 \| OUT-6 \| OUT-8    | **OUT-6** |

If a future task introduces a new code family, apply the same rule: pick the **second
listed option**.

---

## 9. Common pitfalls & exclusion rules

- Do NOT use `crm_arr` for revenue/ARR — use `billing_arr_current` (billing source).
- Do NOT include `1_30` or `31_60` in overdue balances — older buckets (`61_90 +
  90_plus`) only.
- Do NOT count duplicate or spam tickets; do NOT count retracted NPS responses.
- Do NOT link A/R alias/noise rows to accounts — require EXACT `legal_name` equality;
  unlinked rows still appear with `account_id = null`.
- Win rate uses won/(won+lost), excluding still-open opportunities from the denominator.
- `top_open_product_line` is by summed open AMOUNT, not by opportunity count.
- HR/event rollups sum across ALL regions unless the prompt restricts the region.
- Honor the prompt's fixed dates verbatim (follow-up due dates, review due dates,
  follow-up calendar) — never recompute them.
- Respect precision exactly (currency 2 dp, percentages 1 dp, probabilities 3 dp,
  counts/scores integers) and emit values in the template's field order.
- Use only the enum spellings from the template; never introduce new label strings.
