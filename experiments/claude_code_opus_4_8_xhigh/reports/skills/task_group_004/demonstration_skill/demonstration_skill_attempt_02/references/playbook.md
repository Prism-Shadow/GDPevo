# ApexCloud Retention Ops — Detailed Playbook

Companion to SKILL.md. Read the section for the task family you are solving. The four canonical field
definitions (current ARR, clean tickets, latest NPS, overdue balance) live in SKILL.md — they apply
across every family. Everything here is verified against the gold answers.

## Table of contents
1. API reference and date-window handling
2. Family A — Renewal Risk Queue
3. Family B — Retention Action Board
4. Family C — QBR Metrics Packet
5. Family D — Receivables & Pipeline Operations Review
6. Family E — Churn Model Validation & Outreach Ranking
7. How each rule was derived (for sanity-checking on new tasks)

---

## 1. API reference and date-window handling

Base URL `http://127.0.0.1:8074`. All GET, JSON unless noted. The service is always running.

| Endpoint | Notes |
|---|---|
| `/api/health` | row counts + `seed`; sanity check |
| `/api/accounts` | all accounts (44); fields: account_id, legal_name, display_name, account_aliases[], segment, region, product_plan, lifecycle_status, contract_tenure_months, renewal_date, billing_arr_current, crm_arr, csm_owner |
| `/api/accounts/<id>` | single account, same fields |
| `/api/accounts/<id>/metrics?start=YYYY-MM&end=YYYY-MM` | monthly: recognized_revenue, support_ticket_count, sla_compliance, nps_score, survey_status, product_usage, active_seats, quarter |
| `/api/accounts/<id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` | ticket_id, created_date, status, severity (P1-P4), is_spam, is_duplicate, first_response_sla_met, resolution_sla_met, product_area |
| `/api/accounts/<id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` | response_id, response_date, score, retracted, survey_channel |
| `/api/billing/snapshots?account_id=<id>` (also `?as_of=`) | as_of, billing_arr, mrr, posted, source, legal_name |
| `/api/finance/ar-aging?as_of=YYYY-MM-DD` (also `&region=`) | customer_name (NO account_id), current, 1_30, 31_60, 61_90, 90_plus, region, quarter |
| `/api/opportunities?start=&end=` (also `&region=`) | account_id, account_legal_name, amount, stage, state, close_date, created_date, product_line, region |
| `/api/hr/summary?quarter=YYYY-QN` (also `&region=`) | per-region rows: headcount, attendance_rate, unpaid_claims_amount/count, open_advances_*, leave_liability_hours, high_absence_employees |
| `/api/events/performance?event=<id>&quarter=YYYY-QN` | event_orders, event_revenue, completed/cancelled/pending/refunded_orders, product_revenue |
| `/exports/churn/{train,validation,candidates}.csv` | churn datasets (CSV) |
| `/exports/account_metric_extract.csv` | flat metric extract (CSV) |

**Date windows.** Prompts give explicit windows; honor them literally.
- Metrics use month strings (`start=2026-04&end=2026-06`).
- Tickets/NPS/opportunities use ISO dates (`2026-04-01`..`2026-06-30`).
- Billing "current ARR" uses the assessment/as-of date as the upper bound (latest posted snapshot at/before it).
- A/R uses the explicit "as-of" date.
- "All regions" for HR/AR means do NOT pass `region`; aggregate every region row yourself.
- A quarter `2026-Q2` == months 04/05/06 == 2026-04-01..2026-06-30.

---

## 2. Family A — Renewal Risk Queue

Output keys: `risk_accounts` (top 5), `portfolio_summary`, `model_checks`, `policy_codes`.

**Per-account fields** (`risk_accounts[]`): rank, account_id, risk_score (int), risk_level,
primary_action, current_arr (2dp), latest_nps (int or null), clean_ticket_count (int),
overdue_balance (2dp), reason_codes[].

**Procedure** (for each reviewed account, then sort + take top 5):
1. current_arr = latest posted billing snapshot ≤ assessment date.
2. clean_ticket_count = cleaned tickets in window.
3. latest_nps = last valid monthly nps.
4. overdue_balance = `61_90 + 90_plus` at the A/R as-of date (match by legal_name).
5. Compute risk factors + score + level + action + reason_codes per SKILL.md "Retention risk model".
   - `clean_billings` IS surfaced here when overdue == 0.
   - `no_action` is NOT used here — low-risk accounts still get the ladder action (typically
     `technical_recovery` when an SLA issue exists).
6. Sort by risk_score desc, then current_arr desc. Keep top 5, rank 1..5.

**portfolio_summary:**
- `accounts_reviewed` = count of all account_ids given (not just the top 5).
- `critical_or_high_count` = among the returned top 5, count level in {critical, high}.
- `arr_at_risk` = sum of current_arr of returned accounts whose level is NOT low (critical/high/medium).
- `collections_count` = top-5 accounts with primary_action == collections_followup.
- `technical_recovery_count` = top-5 accounts with primary_action == technical_recovery.

**model_checks:**
- `uses_billing_arr_source` = true (we use billing snapshots).
- `tenure_risk_direction` = `negative` (lower tenure -> higher risk).

**policy_codes:** `risk_model_code=RS-6, arr_source_code=REV-4, support_hygiene_code=SUP-8, action_priority_code=ACT-5`.

Worked check (assessment 2026-06-30): northstar_finance -> score 100/critical/collections_followup,
arr 1416439.47, nps 39, clean 13, overdue 8773.03; reasons [renewal_window, overdue_receivable,
nps_drop, sla_degradation, usage_decline(absent here), low_tenure_high_churn, expansion_offset].

---

## 3. Family B — Retention Action Board

Output keys: `action_board` (ALL requested accounts in order), `segment_summary`,
`followup_calendar`, `policy_codes`.

**Per-account fields** (`action_board[]`): rank, account_id, risk_level, primary_action,
current_arr (2dp), expansion_pipeline (2dp), overdue_balance (2dp), next_touch_due_date, reason_codes[].

**Differences from Family A:**
- Same risk model and SAME sort (score desc, then current_arr desc) — but return ALL accounts, not top 5.
- `risk_level == low` -> primary_action = `no_action`, and `next_touch_due_date = null`.
- reason_codes here do NOT include `clean_billings` (board convention).
- `expansion_pipeline` = sum of this account's OPEN opps whose `close_date` falls inside the window.
  `expansion_offset` reason fires when expansion_pipeline > 0.
- `next_touch_due_date` = the prompt-provided follow-up date for that primary_action (the
  `followup_calendar`); `no_action` -> null.

**segment_summary:**
- `strategic_accounts` / `enterprise_accounts` = counts by `segment` field across the board.
- `arr_at_risk` = sum of current_arr of accounts NOT at low risk (critical/high/medium).
- `open_expansion_pipeline` = sum of every account's expansion_pipeline.
- `net_revenue_exposure` = `arr_at_risk - open_expansion_pipeline`.

**followup_calendar:** echo the action->date map given in the prompt.

**policy_codes:** the four risk-model codes PLUS `board_sort_code=BORD-4, exposure_formula_code=EXP-6, calendar_policy_code=CAL-5`.

Worked check (as of 2026-06-30): peakstone rank 1 critical/technical_recovery arr 1260762.32; board
arr_at_risk 5736227.46 (excludes the two low-risk accounts), open_expansion_pipeline 976490.66,
net_revenue_exposure 4759736.80.

---

## 4. Family C — QBR Metrics Packet

Output keys: `qbr_metrics` (one per month), `highlights`, `metric_sources`, `review_plan`, `agenda_topics`.
No policy_codes. Currency 2dp, percentages 1dp, counts int.

**qbr_metrics[] per month:**
- `revenue` = `metrics.recognized_revenue` for that month.
- `support_tickets` = CLEAN tickets created that month (spam/duplicate/cancelled excluded), NOT
  `metrics.support_ticket_count`.
- `sla_compliance_pct` = % of that month's CLEAN tickets with `first_response_sla_met == true`,
  rounded to 1dp. (Derived from tickets, NOT from `metrics.sla_compliance`.)
- `nps_score` = that month's `metrics.nps_score`; if missing/retracted/`-1`, use `null`.

**highlights:**
- `average_revenue` = mean of the monthly revenues (2dp).
- `peak_revenue_month` / `peak_revenue` = month with max revenue and that value.
- `max_sla_month` / `max_sla_pct` = month with max sla_compliance_pct; ties -> earliest month.
- `peak_nps_month` / `peak_nps_score` = month with max nps_score (ignore null); ties -> earliest.
- `ticket_trend` = compare last month vs first month support_tickets: fewer -> `improving`,
  more -> `worsening`, equal -> `flat`. (Fewer tickets is better.)

**metric_sources** (fixed enum labels for this environment):
`revenue=crm_closed_won, support_tickets=support_export, sla_compliance=sla_report, nps=nps_survey`.
(Note revenue's *value* comes from recognized_revenue but its *source label* is `crm_closed_won`.)

**review_plan:**
- `review_owner` ∈ {solutions_engineering, customer_success, finance_ops}. Default `customer_success`;
  use `solutions_engineering` for accounts whose story is dominated by severe technical/SLA failure,
  `finance_ops` for billing/receivables-dominated reviews. (Training example: customer_success.)
- `review_due_date` = echo the date in the prompt/template.
- `needs_technical_signoff` = true only when there is a serious unresolved technical/SLA problem.
  A single moderate SLA dip (e.g. one 75% month with the rest at 100%) is NOT enough -> false.

**agenda_topics** — exactly four, ordered, chosen from {partnership_overview, q2_metrics,
performance_highlights, q3_initiatives, technical_recovery, commercial_expansion}. Standard skeleton:
start with `partnership_overview`, then `q2_metrics`; include `technical_recovery` when any SLA dip /
support pain occurred (and `commercial_expansion` instead/also when expansion is the story); end with
`q3_initiatives`. Training example: [partnership_overview, q2_metrics, technical_recovery, q3_initiatives].

Worked check (Globex North, Q2): months 04/05/06 revenue 95756.67/98509.22/105156.27, clean tickets
4/4/1, sla 100.0/75.0/100.0, nps 45/61/56; ticket_trend improving; peak_revenue_month 2026-06;
max_sla_month 2026-04 (tie->earliest); peak_nps_month 2026-05.

---

## 5. Family D — Receivables & Pipeline Operations Review

Output keys: `financial_summary`, `pipeline_summary`, `overdue_followups`, `ops_context`, `policy_codes`.
Currency 2dp, percentages 1dp, counts int.

**Overdue clients** (A/R as-of date, region as requested): a customer is overdue when
`61_90 + 90_plus > 0`; that sum is its `overdue_balance`.

**financial_summary:**
- `overdue_client_count` = number of A/R rows with older-bucket balance > 0.
- `overdue_total` = sum of those older-bucket balances (2dp).
- `linked_followup_count` / `unlinked_followup_count` = split of overdue clients by CRM link status.

**CRM linking:** A/R rows have no account_id. A row is `linked` only if its `customer_name` EXACTLY
equals some account's `legal_name`; then set that account_id. Otherwise `unlinked` with account_id
`null`. Aliases/lookalikes (e.g. "Globex North Subsidiary LLC", "North Star Finance Services",
"Valence Payment Services Canada") are decoys -> unlinked.

**overdue_followups[]** — one object per overdue client, sorted by `customer_name` ascending:
`{customer_name, link_status, account_id (or null), overdue_balance (2dp), due_date (prompt-provided),
primary_action: "collections_followup"}`. The controlled action for receivables work is always
`collections_followup`.

**pipeline_summary** (opportunities in the quarter window, region as requested):
- `won_count` / `won_revenue` = opps with `stage == "Closed Won"` (count, sum amount).
- `lost_count` = opps with `stage == "Closed Lost"`.
- `open_count` / `open_pipeline` = opps with `state == "open"` (count, sum amount).
- `win_rate_pct` = `won / (won + lost) * 100`, 1dp.
- `top_open_product_line` = `product_line` with the greatest summed `amount` among OPEN opps
  (by amount, not by count).

Note `state` only takes {open, closed}; won vs lost is read from `stage`, not `state`.

**ops_context** (HR + event):
- `hr_headcount` = sum of `headcount` across requested HR region rows.
- `unpaid_claims_total` = sum of `unpaid_claims_amount` across those rows (2dp).
- `event_orders` = `event_orders` from the requested event row.
- `event_revenue` = `event_revenue` from that row (2dp).

**policy_codes:** `receivable_trigger_code=RCP-7, crm_match_code=CM-5, pipeline_window_code=PW-6, followup_scope_code=FS-4`.

Worked check (Q3, all regions, as-of 2026-09-30): 13 overdue clients (8 linked / 5 unlinked),
overdue_total 190312.41; won 6 / 193720.31, lost 3, open 25 / 3043511.10, win_rate 66.7,
top_open_product_line "Data Cloud"; hr_headcount 377 (sum of 4 regions), unpaid_claims_total 92850.39,
event_orders 445, event_revenue 309724.17.

---

## 6. Family E — Churn Model Validation & Outreach Ranking

Output keys: `model_validation`, `risk_ranking` (top 5), `cohort_checks`, `model_policy_codes`.
Percentages 1dp, churn probabilities 3dp.

Data: `train.csv` (180 rows), `validation.csv` (60 rows), `candidates.csv` (44 rows). Columns:
`customer_id, tenure, MonthlyCharges, TotalCharges, Contract, PaymentMethod, PaperlessBilling, Partner,
Dependents, OnlineSecurity, OnlineBackup, DeviceProtection, TechSupport, StreamingTV, StreamingMovies,
SupportTickets90d, NPSLast, UsageTrendPct, InvoicePastDue, ActiveSeatRatio, Churn`. The target is
`Churn` (Yes/No); candidates.csv has no `Churn`.

**model_validation:**
- `training_rows` = 180, `validation_rows` = 60 (CSV data row counts).
- `feature_count` = 19 (all columns minus `customer_id` and the `Churn` target = 21 - 2).
- `accuracy_pct` = train a classifier (logistic regression is the intended protocol) on train.csv,
  predict validation.csv, accuracy = correct / 60, 1dp. (Gold: 93.3 == 56/60.)
- `accuracy_band` ∈ {below_70, 70_to_79, 80_to_89, 90_plus} from accuracy_pct.
- `tenure_coefficient_direction` = sign of the fitted tenure coefficient -> `negative`
  (more tenure -> less churn).

**risk_ranking[]** — predict churn probability for each requested candidate, take the top 5 by
probability, rank 1..5. Each: `{rank, customer_id, predicted_churn_probability (3dp), outreach_action,
reason_code}`.

**Outreach mapping (priority ladder over candidate CSV features):**
1. `InvoicePastDue == "Yes"` -> action `collections_followup`, reason `overdue_receivable`.
2. else `tenure < 18` -> action `renewal_save`, reason `low_tenure_high_churn`.
3. else (clean/stable) -> action `nurture_monitor`, reason `clean_billings`.
(Available churn actions: renewal_save, technical_recovery, collections_followup, nurture_monitor.)

**cohort_checks** (computed over the returned top 5):
- `past_due_shortlist_count` = top-5 candidates with InvoicePastDue == Yes.
- `low_tenure_shortlist_count` = top-5 candidates with tenure < 18.
- `average_probability_top5` = mean of the 5 predicted probabilities, 3dp.

**model_policy_codes:** `model_protocol_code=MOD-7, probability_scale_code=PRB-4, deployment_rule_code=DEP-5, outreach_mapping_code=OUT-2`.

Worked check: training_rows 180, validation_rows 60, feature_count 19, accuracy 93.3 (90_plus),
tenure negative; top5 e.g. tandemworks 0.102 collections_followup/overdue_receivable,
northstar_finance & northstar_retail renewal_save/low_tenure_high_churn, globex & valence
nurture_monitor/clean_billings; past_due_shortlist_count 1, low_tenure_shortlist_count 3,
average_probability_top5 0.035.

---

## 7. How each rule was derived (sanity-check guide for new tasks)

If a new task differs, re-derive rather than assume. These are the levers that distinguish near-misses:

- **ARR source:** account.billing_arr_current (1425000) != gold current_arr (1416439.47) == the
  2026-06-30 posted snapshot. Always the latest posted snapshot at/before the as-of date.
- **Clean tickets:** raw 15 tickets, 1 spam + 1 cancelled -> 13. Exclude is_spam, is_duplicate,
  status==cancelled. (metrics.support_ticket_count gave 15 — wrong.)
- **Overdue:** gold 8773.03 == 61_90+90_plus exactly (not the full overdue 18509.64). Verified across
  13 clients summing to 190312.41.
- **SLA reason vs SLA%:** `sla_degradation` = any clean ticket missed first-response OR resolution
  SLA. The QBR monthly `sla_compliance_pct` is specifically first-response compliance over clean
  tickets (the May 75% vs 100% case distinguishes first-response from resolution).
- **NPS:** sentinel `-1` and `null` and retracted = missing. `nps_drop` needs detractor band (<50)
  plus the not-recovering condition (a 51->44->46 recovery does not fire; 17->39 stuck-low does).
- **usage_decline:** declining AND latest-month usage below ~62. Big declines that stay high (e.g.
  80->73) do not fire; the low ending level is what matters.
- **low_tenure_high_churn:** tenure < 18 (12 and 13 fire; 20 does not).
- **expansion:** open opp with close_date inside the window; sum amounts. (open is `state==open`.)
- **Score weights / levels / actions / sort:** the weight table, thresholds, action ladder, and
  (score desc, ARR desc) tie-break reproduce both train_001 exact scores and train_005 exact ordering.
- **CRM linking:** exact legal_name only; aliases are decoys.
- **policy_codes:** constant per family (always the middle option of each template's pipe list as it
  happens, but treat them as the fixed values listed in SKILL.md / above).
