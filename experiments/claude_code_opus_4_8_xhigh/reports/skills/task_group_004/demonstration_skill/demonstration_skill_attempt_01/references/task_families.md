# Task-family procedures

Step-by-step recipes per family. All shared metric definitions (current_arr, clean
tickets, latest NPS, overdue balance, reason codes, actions, sort order, roll-ups)
live in `SKILL.md` sections 2–5 — this file covers the family-specific assembly and
the field-by-field sourcing. Always re-read the actual `answer_template.json` for the
task; shapes evolve.

## Endpoint reference

| Endpoint | Returns |
|---|---|
| `GET /api/health` | row counts per dataset (sanity check) |
| `GET /api/accounts` | all account profiles (segment, region, tenure, renewal_date, lifecycle_status, legal_name, account_aliases, billing_arr_current, crm_arr, csm_owner) |
| `GET /api/accounts/<id>` | one account profile |
| `GET /api/accounts/<id>/metrics?start=YYYY-MM&end=YYYY-MM` | monthly rows: recognized_revenue, product_usage, sla_compliance, nps_score, support_ticket_count, active_seats, survey_status |
| `GET /api/accounts/<id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` | tickets: created_date, status, is_spam, is_duplicate, severity, first_response_sla_met, resolution_sla_met, product_area |
| `GET /api/accounts/<id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` | responses: response_date, score, retracted, survey_channel |
| `GET /api/billing/snapshots?account_id=<id>&as_of=YYYY-MM-DD` | snapshots: as_of, billing_arr, mrr, posted, source, legal_name |
| `GET /api/finance/ar-aging?as_of=YYYY-MM-DD[&region=]` | aging rows: customer_name, region, current, 1_30, 31_60, 61_90, 90_plus, quarter |
| `GET /api/opportunities?start=YYYY-MM-DD&end=YYYY-MM-DD[&region=]` | opps: account_id, account_legal_name, amount, stage, state, product_line, close_date, region |
| `GET /api/hr/summary?quarter=YYYY-QN[&region=]` | per-region HR rows: headcount, unpaid_claims_amount/_count, open_advances_*, attendance_rate, leave_liability_hours, high_absence_employees |
| `GET /api/events/performance?event=<id>&quarter=YYYY-QN` | event row: event_orders, event_revenue, completed/cancelled/pending/refunded_orders, product_revenue |
| `GET /exports/churn/{train,validation,candidates}.csv` | churn datasets |
| `GET /exports/account_metric_extract.csv` | flat account×month metric extract |

Date windows: metrics use `YYYY-MM`; tickets/nps/ar/opps use `YYYY-MM-DD`. A quarter
maps to its three months and a quarter-end date (Q2→Apr–Jun, end 06-30; Q3→Jul–Sep,
end 09-30). Billing `as_of` must be the quarter-end exactly.

---

## RISK QUEUE  (e.g. "renewal risk queue", top-N by risk)

Output: `risk_accounts` (top N), `portfolio_summary`, `model_checks`, `policy_codes`.

For each requested account:
1. `current_arr` = posted billing snapshot at quarter-end (SKILL §2).
2. `latest_nps` (SKILL §2; `null` if none).
3. `clean_ticket_count` (SKILL §2 exclusion rule).
4. `overdue_balance` = `61_90 + 90_plus` from AR aging at the as-of date.
5. Pull monthly metrics for SLA / usage / nps-series.
6. Compute reason_codes (SKILL §3) and risk_score / risk_level / primary_action
   (SKILL §4).
7. Rank by risk_score descending; keep the top N (usually 5).

`portfolio_summary`: `accounts_reviewed` = number of accounts you assessed (all
requested, not just the top N); `critical_or_high_count`; `arr_at_risk` (Σ ARR of
critical/high/medium among the **returned** ranked accounts); `collections_count`
and `technical_recovery_count` over the returned accounts.

`model_checks`: `uses_billing_arr_source` = `true`; `tenure_risk_direction` =
`negative`.

---

## QBR  (quarterly business review metrics packet)

Output: `qbr_metrics` (one row per month), `highlights`, `metric_sources`,
`review_plan`, `agenda_topics`, (and `policy_codes` if present).

Per month (the three quarter months):
- `revenue` = `recognized_revenue` from the monthly **metrics** endpoint.
- `support_tickets` = **clean** ticket count for that month from the **tickets**
  endpoint (exclude spam/duplicate/cancelled), NOT `metric.support_ticket_count`.
- `sla_compliance_pct` = **first-response SLA met %** among that month's clean
  tickets: `100 * count(first_response_sla_met == true) / count(clean tickets)`
  (1 decimal). This is first-response, not resolution and not the metric's
  `sla_compliance`.
- `nps_score` = that month's `nps_score` from the metrics endpoint; `null` if the
  survey was missing/retracted that month.

`highlights`: `average_revenue` (mean of the three), `peak_revenue_month`/value,
`max_sla_month`/value, `peak_nps_month`/value (ignore null months), and
`ticket_trend` ∈ {improving, worsening, flat}: compare last-month vs first-month
clean ticket count — **fewer tickets ⇒ improving**, more ⇒ worsening, equal ⇒ flat.

`metric_sources` are fixed source labels (the value, not where the number came from):
`revenue: crm_closed_won`, `support_tickets: support_export`,
`sla_compliance: sla_report`, `nps: nps_survey`.

`review_plan`: `review_owner` ∈ {solutions_engineering, customer_success,
finance_ops} — pick `customer_success` for a standard CS-led QBR; choose
`solutions_engineering` and set `needs_technical_signoff: true` only when technical
recovery dominates the quarter (severe SLA breaches). Honor any due date the prompt
fixes.

`agenda_topics`: exactly the number requested (usually 4), ordered, from
{partnership_overview, q2_metrics, performance_highlights, q3_initiatives,
technical_recovery, commercial_expansion}. Default arc:
`partnership_overview → q2_metrics → {technical_recovery if SLA dipped, else
performance_highlights} → q3_initiatives`. Use `commercial_expansion` when there is
notable open expansion pipeline.

---

## RECEIVABLES  (Q-x receivables & pipeline operations review)

Output: `financial_summary`, `pipeline_summary`, `overdue_followups`, `ops_context`,
`policy_codes`.

1. **Overdue clients:** AR aging at the as-of date; keep rows with
   `61_90 + 90_plus > 0`. `overdue_client_count` = how many; `overdue_total` = Σ of
   their `(61_90 + 90_plus)`.
2. **CRM linking:** for each overdue client, match its `customer_name` **exactly**
   to a CRM account's `legal_name` (from `/api/accounts`). Match → `link_status:
   "linked"`, fill `account_id`; no match → `link_status: "unlinked"`,
   `account_id: null`. `linked_followup_count` / `unlinked_followup_count` accordingly.
   (Distinct legal entities like "…Subsidiary LLC" or "North Star Finance Services"
   that aren't CRM accounts stay unlinked.)
3. Each follow-up: `overdue_balance` = its `(61_90 + 90_plus)`, `due_date` = the
   fixed follow-up date from the prompt, `primary_action` = `collections_followup`.
   **Sort `overdue_followups` by `customer_name` ascending.**
4. **Pipeline** from `/api/opportunities` in the quarter window:
   - `won_count` / `won_revenue` = stage `Closed Won` (count, Σ amount).
   - `lost_count` = stage `Closed Lost`.
   - `open_count` / `open_pipeline` = rows with `state == "open"` (count, Σ amount).
   - `win_rate_pct` = `100 * won_count / (won_count + lost_count)` (1 decimal).
   - `top_open_product_line` = the `product_line` with the **largest Σ open amount**
     (by dollar value, not by count).
5. **ops_context:** if region is "all", HR returns one row per region — **sum**
   across regions: `hr_headcount` = Σ headcount; `unpaid_claims_total` = Σ
   unpaid_claims_amount. Event context: `event_orders` / `event_revenue` straight
   from the single event row.

---

## CHURN  (churn-model validation + outreach ranking)

Output: `model_validation`, `risk_ranking` (top 5 of the candidate set),
`cohort_checks`, `model_policy_codes`.

CSV columns: `customer_id`, 19 feature columns, and `Churn` (target, in train &
validation only). Candidates lack `Churn`.

1. **model_validation:** `training_rows` = train.csv data rows; `validation_rows` =
   validation.csv data rows; `feature_count` = columns minus `customer_id` and
   `Churn` (= 19). Train a logistic-regression classifier on train.csv (one-hot or
   ordinal encode the categorical columns; standardize numerics), evaluate on
   validation.csv: `accuracy_pct` = correct/total ×100 (1 decimal); `accuracy_band`
   ∈ {below_70, 70_to_79, 80_to_89, 90_plus}; `tenure_coefficient_direction` =
   `negative` (higher tenure ⇒ lower churn). Expect a strong model (~90+ band).
   *Note:* exact predicted probabilities are model-implementation specific; the
   **ranking order** and the deterministic fields are what matter. Use a standard
   scikit-learn `LogisticRegression`.
2. **risk_ranking:** score the requested candidate accounts, rank by predicted
   churn probability descending, keep top 5. For each, derive `reason_code` and
   `outreach_action` by this priority (first match wins), driven by the candidate's
   features (`InvoicePastDue`, `tenure`, `NPSLast`, `UsageTrendPct`, SLA):
   - `InvoicePastDue == "Yes"` → `overdue_receivable` / `collections_followup`
   - low `tenure` (≤ ~18) → `low_tenure_high_churn` / `renewal_save`
   - weak NPS / SLA → `nps_drop` or `sla_degradation` / `technical_recovery`
   - usage decline → `usage_decline` / `technical_recovery`
   - otherwise clean → `clean_billings` / `nurture_monitor`
3. **cohort_checks** are computed **over the top-5 returned**, not the full set:
   `past_due_shortlist_count` = how many of the top 5 are past-due;
   `low_tenure_shortlist_count` = how many of the top 5 are low-tenure (≤ ~18);
   `average_probability_top5` = mean predicted probability of the 5 (3 decimals).

---

## BOARD  (high-touch retention action board)

Output: `action_board` (all requested accounts, ranked), `segment_summary`,
`followup_calendar`, `policy_codes`.

For each requested account, compute the same per-account fields as the risk queue
plus `expansion_pipeline` = Σ `amount` of **open** opportunities whose `close_date`
falls in the quarter window (per account). Then:
- `risk_level`, `primary_action`, `reason_codes` per SKILL §3–4.
- `next_touch_due_date` = look up the prompt's per-action follow-up date by the
  account's `primary_action`; for `no_action` / low-risk accounts use `null`.
- **Order** by risk_level (critical>high>medium>low), then `current_arr` descending
  within a level. Assign `rank` 1..N in that order. Include every requested account.

`segment_summary`: `strategic_accounts` / `enterprise_accounts` (segment counts),
`arr_at_risk` (Σ current_arr for critical/high/medium), `open_expansion_pipeline`
(Σ expansion_pipeline), `net_revenue_exposure` = `arr_at_risk −
open_expansion_pipeline`.

`followup_calendar`: echo the prompt's action→date mapping verbatim.
