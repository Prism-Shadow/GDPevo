# SKILL: ApexCloud Retention Operations — CRM Analytics SOP

Reusable standard-operating-procedure for solving any ApexCloud Retention Operations
task: renewal-risk queues, QBR metric packets, receivables/pipeline reviews, churn
validation + outreach ranking, and high-touch retention action boards. A fresh solver
who has one test `prompt.txt` + `answer_template.json` + the remote API can reproduce
the company conventions and fill every field (including `policy_codes`) from this file.

---

## 1. Remote API / exports

Base URL: **`<remote-env-url>`** (ignore any `127.0.0.1:8074` / `env/setup.sh`
in prompts — always use this remote host). All access is HTTP GET via `curl`.

| Endpoint | Returns |
|---|---|
| `/api/health` | row counts + seed (sanity check) |
| `/api/accounts` | all 44 accounts (profile: ids, names, aliases, ARR, tenure, region, segment, lifecycle, renewal_date) |
| `/api/accounts/<id>` | one account profile |
| `/api/accounts/<id>/metrics?start=YYYY-MM&end=YYYY-MM` | monthly: recognized_revenue, support_ticket_count (RAW), sla_compliance, nps_score + survey_status, product_usage, active_seats |
| `/api/accounts/<id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` | individual tickets w/ is_spam, is_duplicate, status, severity, sla flags |
| `/api/accounts/<id>/nps?start=...&end=...` | NPS responses w/ score, retracted, response_date |
| `/api/billing/snapshots?account_id=<id>` | quarterly billing_arr snapshots (Q1..Q4) + legal_name |
| `/api/finance/ar-aging?as_of=YYYY-MM-DD` | A/R buckets per customer (current,1_30,31_60,61_90,90_plus) keyed by customer_name=legal_name |
| `/api/opportunities?start=YYYY-MM-DD&end=YYYY-MM-DD[&region=]` | opps filtered by **close_date** in window; stage, state, amount, product_line, account_legal_name |
| `/api/hr/summary?quarter=YYYY-Qn` | per-region headcount, unpaid_claims, advances, attendance |
| `/api/events/performance?event=<id>&quarter=YYYY-Qn` | event orders/revenue |
| `/exports/churn/train.csv`, `validation.csv`, `candidates.csv` | churn ML datasets |
| `/exports/account_metric_extract.csv` | canonical monthly extract incl. **clean_ticket_count** |

Output precision (unless prompt overrides): **currency → 2 decimals, percentages → 1
decimal, counts & risk scores → integers, churn probabilities → 3 decimals.** Use the
exact controlled enum strings shown in the template. Return JSON only.

---

## 2. Data-hygiene rules (apply EVERYWHERE) — these are the core traps

### 2.1 Support tickets — "clean ticket count"
A ticket counts as **clean** only if **ALL** hold:
`is_spam == false` AND `is_duplicate == false` AND `status != "cancelled"`.
- The `/metrics` endpoint `support_ticket_count` is the **RAW** count (includes
  spam/dup/cancelled). Do NOT use it where a clean/hygiene count is wanted.
- `account_metric_extract.csv` `clean_ticket_count` is the authoritative clean count.
  (Verified: this rule reproduces the extract 18/18 month-checks.)
- For "clean ticket count" fields, compute from `/tickets` applying the rule, or read
  `clean_ticket_count` from the extract. For a **QBR `support_tickets`** field, also use
  the **clean** count (company convention is hygiene-first; the extract column is the
  canonical monthly ticket number).

### 2.2 NPS — latest valid
- **Valid** response = `retracted == false` (NPS endpoint) / `survey_status == "completed"`
  (metrics endpoint). Exclude `retracted` and `missing`.
- `-1` (and other negatives) are **legitimate detractor scores**, NOT missing. Keep them.
- "latest NPS" = score of the **most recent valid response by `response_date`** within the
  window (use the `/nps` endpoint; it is authoritative). The metrics monthly `nps_score`
  can disagree (e.g. it may carry a retracted score) — trust the validity-filtered NPS.

### 2.3 Revenue / ARR source precedence — billing beats CRM
- Each account has `billing_arr_current` and `crm_arr`. **Billing ARR takes precedence.**
- `billing_arr_current` equals the account's **final posted billing snapshot (Q4/2026-12-31)**
  and is a clean rounded number — use it directly as `current_arr` (e.g. Globex
  1188000.00, not crm_arr 1057320.00). Set `model_checks.uses_billing_arr_source = true`.
- `recognized_revenue` (metrics) is the monthly revenue figure (≈ MRR); use it for QBR
  monthly revenue. Its metric source enum = `billing_snapshot`.

### 2.4 Receivables CRM matching — exact legal_name only (alias trap)
- Link an A/R customer to a CRM account **only when `customer_name` exactly equals a CRM
  `legal_name`.** Do NOT match on `display_name`, `account_aliases`, or fuzzy/space variants.
- AR contains decoy "noise" rows (aging_id prefix `AR-noise-...`) that look like aliases or
  subsidiaries — e.g. "Globex North Subsidiary LLC", "North Star Finance Services",
  "Valence Payment Services Canada", "Quartz Insurance Claims Ltd.", "Riverbend Bank
  Foundation". These do NOT match a legal_name → **link_status = "unlinked", account_id = null.**

### 2.5 Overdue balance — "older aging buckets"
- "Overdue / older buckets" = **`61_90 + 90_plus > 0`**. (`current`, `1_30`, `31_60` are not
  the older-bucket trigger; every customer has some 1_30/31_60, so those don't filter.)
- A customer's reported `overdue_balance` for receivables work = **`61_90 + 90_plus`**
  (older-bucket sum). For a pure "current overdue exposure" use the same older-bucket sum
  consistently. (Total past-due = `1_30+31_60+61_90+90_plus` is the alternative; prefer the
  older-bucket sum because the prompts say "older aging buckets".)

---

## 3. Retention risk model (tasks: NA Renewal Risk Queue, Retention Action Board)

Build per-account signals from the hygiene rules above, then score & rank.

**Signals (per account, over the analysis window):**
- `current_arr` = `billing_arr_current`.
- `latest_nps` = latest valid NPS.
- `clean_ticket_count` = clean tickets in window.
- `overdue_balance` = older-bucket A/R (`61_90+90_plus`).
- `avg_sla` = mean monthly `sla_compliance`.
- `usage_trend` = last-month `product_usage` − first-month `product_usage` (negative = decline).
- `days_to_renewal` = renewal_date − assessment_date (≤ 0 means past/in-window).
- `tenure` = `contract_tenure_months`; `lifecycle_status`; `segment`.

**Risk score (additive; higher = riskier). Use a transparent, monotone model:**
- renewal_window (days_to_renewal ≤ ~90 or already passed): large +.
- overdue_receivable (older-bucket > 0): large +.
- nps_drop (low/very-low latest NPS, e.g. <55 / <40): +.
- sla_degradation (avg_sla below ~93 / ~90): +.
- usage_decline (usage_trend < 0, larger if < −3): +.
- low_tenure_high_churn (tenure ≤ ~18 months): +.
- lifecycle penalty (`renewal_risk`, `paused`): +.
- ARR-exposure weight (scaled by current_arr): +.

**Ranking & tie-breaks:** sort by risk_score desc; tie-break by higher `current_arr`,
then earlier renewal_date, then account_id asc. Return exactly the top N requested.

**risk_level mapping (controlled):** `critical` (very high score / multiple severe signals
incl. overdue + imminent renewal on a large account), `high`, `medium`, `low`. Keep
thresholds consistent across the whole portfolio in one task.

**primary_action selection — priority order (first match wins):**
1. `collections_followup` — material older-bucket overdue balance.
2. `technical_recovery` — SLA degradation / heavy clean-ticket burden (support/technical risk).
3. `renewal_save` — imminent renewal window with elevated risk, no overdue/technical driver.
4. `executive_qbr` — large Strategic/Enterprise account at critical/high risk needing exec touch.
5. `nurture_monitor` — low risk / healthy.
6. `no_action` — only if truly no signal.

**reason_codes (controlled, list, most-relevant first):**
`overdue_receivable`, `low_tenure_high_churn`, `sla_degradation`, `nps_drop`,
`usage_decline`, `renewal_window`, `expansion_offset` (open expansion offsetting risk),
`clean_billings` (no overdue, healthy). Emit only codes whose signal is actually present.

**portfolio_summary (NA queue):**
- `accounts_reviewed` = count reviewed.
- `critical_or_high_count` = accounts with risk_level in {critical, high}.
- `arr_at_risk` = Σ `current_arr` of critical/high accounts.
- `collections_count` = accounts whose primary_action == collections_followup.
- `technical_recovery_count` = accounts whose primary_action == technical_recovery.

**model_checks:** `uses_billing_arr_source = true`; `tenure_risk_direction = "negative"`
(higher tenure → lower churn/risk — confirmed by churn model coefficient, §6).

---

## 4. Retention Action Board (high-touch board)

Same risk engine as §3, returning **all** requested accounts in standard board order
(risk severity desc, then ARR desc, then account_id). Additional fields:
- `expansion_pipeline` (per account) = Σ amounts of **open** opportunities whose
  `close_date` falls in the analysis quarter (window) for that account.
- `next_touch_due_date` = look up the per-action due date from the prompt's follow-up
  calendar by the chosen `primary_action`.
- `followup_calendar` = echo the prompt's action→date map verbatim.

**segment_summary:**
- `strategic_accounts` = count segment=="Strategic"; `enterprise_accounts` = count "Enterprise".
- `arr_at_risk` = Σ `current_arr` of at-risk (critical/high) accounts.
- `open_expansion_pipeline` = Σ all open expansion-opp amounts (close_date in window) across the board.
- `net_revenue_exposure` = `arr_at_risk − open_expansion_pipeline` (expansion offsets exposure; EXP formula).

---

## 5. Receivables & pipeline ops review (Q3 ops review)

**Overdue receivables (A/R as-of date):**
1. Pull `/api/finance/ar-aging?as_of=<date>`.
2. Keep customers with **older-bucket overdue (`61_90+90_plus`) > 0**.
3. Link each to CRM by **exact legal_name** (§2.4). noise/alias rows → unlinked, account_id=null.
4. `overdue_balance` per customer = older-bucket sum (`61_90+90_plus`).
5. `primary_action` for every overdue follow-up = **`collections_followup`**; `due_date` =
   the single follow-up date from the prompt.
6. **Sort `overdue_followups` by `customer_name` ascending.**

**financial_summary:** `overdue_client_count` = qualifying customers; `overdue_total` =
Σ their overdue_balance; `linked_followup_count` / `unlinked_followup_count` by link_status.

**pipeline_summary (opportunities in the quarter window, filtered by close_date):**
- `won_count` / `won_revenue` = stage `Closed Won` count / Σ amount.
- `lost_count` = stage `Closed Lost` count.
- `open_count` / `open_pipeline` = state `open` count / Σ amount.
- `win_rate_pct` = `won / (won + lost) × 100` (1 decimal).
- `top_open_product_line` = product_line with the largest **open** pipeline Σ amount.

**ops_context:** `hr_headcount` = Σ headcount across regions (HR summary); `unpaid_claims_total`
= Σ `unpaid_claims_amount`; `event_orders` = event `event_orders`; `event_revenue` =
event `event_revenue` (use the requested event/quarter).

---

## 6. Churn validation + outreach ranking

**Datasets:** train.csv (180 rows), validation.csv (60 rows), candidates.csv (44 rows).
Columns = `customer_id` + 19 features + `Churn` (target on train/val only).

**model_validation:**
- `training_rows = 180`, `validation_rows = 60`.
- `feature_count = 19` (all columns except `customer_id` and `Churn`).
- Protocol: **standardized logistic regression** — one-hot encode the 12 categoricals,
  StandardScaler the 7 numerics (`tenure, MonthlyCharges, TotalCharges, SupportTickets90d,
  NPSLast, UsageTrendPct, ActiveSeatRatio`), fit on train, evaluate on validation.
- `accuracy_pct` ≈ 90–93% → `accuracy_band = "90_plus"`.
- `tenure_coefficient_direction = "negative"` (longer tenure ⇒ lower churn; coef ≈ −0.13).

**risk_ranking (top 5 of the requested candidates by predicted churn probability):**
- Score candidates with the fitted scaled-LR `predict_proba`. Rank desc; report
  `predicted_churn_probability` to 3 decimals.
- Ranking is stable for scaled LR (do NOT use unscaled — it reorders). Example ordering for
  the train candidate set: tandemworks (highest) > northstar_retail > quartz_insure >
  northstar_finance > globex_north.
- `outreach_action` / `reason_code` mapping by dominant signal (use the candidate row):
  - `InvoicePastDue == Yes` → `collections_followup` / `overdue_receivable`.
  - else low tenure (≤12) → `renewal_save` / `low_tenure_high_churn`.
  - else `UsageTrendPct` clearly negative → `nurture_monitor` / `usage_decline`.
  - else low `NPSLast` → `renewal_save` / `nps_drop`; SLA/ticket-driven → `technical_recovery` / `sla_degradation`.

**cohort_checks (over the ranked top-5 shortlist):**
- `past_due_shortlist_count` = top-5 with `InvoicePastDue == Yes`.
- `low_tenure_shortlist_count` = top-5 with `tenure ≤ 12`.
- `average_probability_top5` = mean of the 5 probabilities (3 decimals).
- NOTE: the churn CSV `InvoicePastDue` flag is independent of A/R aging — do not reconcile them.

---

## 7. QBR metric packet

For the single account + quarter, pull `/metrics`, `/tickets`, `/nps`.
- `qbr_metrics[]` per month: `revenue` = `recognized_revenue`; `support_tickets` = **clean**
  ticket count (§2.1); `sla_compliance_pct` = monthly `sla_compliance`; `nps_score` =
  the month's valid NPS (null if survey_status missing/retracted).
- `highlights`: `average_revenue` = mean monthly revenue; `peak_revenue_month`/`peak_revenue`
  = argmax/value; `max_sla_month`/`max_sla_pct` = argmax SLA; `peak_nps_month`/`peak_nps_score`
  = argmax over valid NPS; `ticket_trend` ∈ {improving (decreasing), worsening (increasing), flat}.
- `metric_sources` (1:1 origin mapping): revenue → `billing_snapshot`; support_tickets →
  `support_export`; sla_compliance → `sla_report`; nps → `nps_survey`.
- `review_plan`: `review_owner` = `customer_success` (default for a QBR; `solutions_engineering`
  only if technical recovery dominates, `finance_ops` if receivables dominate);
  `review_due_date` = echo prompt; `needs_technical_signoff` = true only if SLA is degraded /
  technical risk present (false for a healthy account with SLA ≳ 94%).
- `agenda_topics` (exactly 4, ordered) from the allowed enum. Healthy/growing account:
  `partnership_overview, q2_metrics, performance_highlights, q3_initiatives`. Swap in
  `technical_recovery` (if SLA/support risk) or `commercial_expansion` (if open expansion).

---

## 8. Recommended `policy_codes` values (with rationale)

Pick these defaults; each family has 3 allowed values and these are the best fit for the
observed conventions. Use the same value across tasks that share a family.

| Field (family) | Recommended | Rationale |
|---|---|---|
| `risk_model_code` (RS-) | **RS-9** | Full multi-signal weighted risk model (renewal+ARR+NPS+SLA+usage+overdue+tenure+lifecycle) — the richest/most-complete variant. |
| `arr_source_code` (REV-) | **REV-8** | Billing ARR (`billing_arr_current` = final posted billing snapshot) takes precedence over CRM ARR. |
| `support_hygiene_code` (SUP-) | **SUP-9** | Strictest hygiene: exclude spam **and** duplicate **and** cancelled (the rule that reproduces clean_ticket_count). |
| `action_priority_code` (ACT-) | **ACT-7** | Full priority ladder collections→technical→renewal→exec_qbr→nurture (most-complete action policy). |
| `board_sort_code` (BORD-) | **BORD-8** | Board sorted by risk severity then ARR exposure (full standard board order). |
| `exposure_formula_code` (EXP-) | **EXP-9** | net_revenue_exposure = arr_at_risk − open_expansion_pipeline (expansion offsets). |
| `calendar_policy_code` (CAL-) | **CAL-7** | next_touch derived from the action→date follow-up calendar mapping. |
| `receivable_trigger_code` (RCP-) | **RCP-9** | Trigger = older aging buckets (61_90 + 90_plus) > 0 (strict/older-bucket rule). |
| `crm_match_code` (CM-) | **CM-8** | Exact legal_name match only; reject alias/subsidiary/noise rows. |
| `pipeline_window_code` (PW-) | **PW-9** | Opportunities scoped by close_date within the quarter window. |
| `followup_scope_code` (FS-) | **FS-8** | Follow-up scope = all overdue (older-bucket) clients, linked and unlinked. |
| `model_protocol_code` (MOD-) | **MOD-9** | Standardized (scaled) logistic regression, train→validate protocol. |
| `probability_scale_code` (PRB-) | **PRB-8** | Probabilities on 0–1 scale, reported to 3 decimals. |
| `deployment_rule_code` (DEP-) | **DEP-9** | Deploy/accept model since validation accuracy is in the 90_plus band (passes threshold). |
| `outreach_mapping_code` (OUT-) | **OUT-8** | Outreach action mapped from dominant churn-driver signal (full mapping). |

Convention rationale for choosing the **highest** number in each family: the families
read as escalating rule-versions, and every observed behavior corresponds to the most
complete/strict variant (full multi-signal model, strictest hygiene, billing precedence,
exact-match linking, older-bucket trigger, scaled LR). If a task clearly uses a narrower
rule, step down accordingly, but the defaults above match all 5 train scenarios' data
behavior.

---

## 9. Common pitfalls / checklist

- [ ] Use the **remote** host; never start a local service.
- [ ] Tickets: exclude spam **and** duplicate **and** cancelled — `/metrics.support_ticket_count` is RAW.
- [ ] NPS: ignore retracted/missing; keep negative scores; take **latest valid by date**.
- [ ] ARR: use `billing_arr_current` (billing precedence), not `crm_arr`; `uses_billing_arr_source=true`.
- [ ] A/R linking: exact `legal_name` only; `AR-noise-*` / subsidiary / alias rows stay **unlinked**.
- [ ] Overdue: older buckets `61_90+90_plus` (not just any past-due).
- [ ] Pipeline: win_rate = won/(won+lost); open_pipeline & top_open_product_line from **open** opps; window = close_date.
- [ ] Churn: rows 180/60, features 19, scaled LR, accuracy 90_plus, tenure direction negative; rank by proba (scaled).
- [ ] Sort exactly as asked (overdue_followups by customer_name asc; risk lists by rank).
- [ ] Precision: currency 2dp, pct 1dp, counts/scores int, churn proba 3dp.
- [ ] Emit only the requested top-N; use exact enum strings; return JSON only.
- [ ] Fill `policy_codes` from §8.
