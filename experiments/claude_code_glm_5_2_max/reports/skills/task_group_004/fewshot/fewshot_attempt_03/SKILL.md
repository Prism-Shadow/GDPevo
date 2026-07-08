---
name: apexcloud-retention-ops
description: Solve ApexCloud Retention Operations analytics tasks against the remote Retention Operations API. Encode and reproduce the exact business rules, data-hygiene conventions, policy codes, ranking/precision rules, churn-model spec, and per-archetype output schemas. Use for any CRM retention task (renewal risk queue / save plan, QBR metrics packet, receivables + pipeline operations digest, churn model validation + outreach ranking, high-touch retention action board / watchlist).
---

# ApexCloud Retention Operations — Solver Skill

This skill is the executable experience for the ApexCloud CRM retention-analytics evaluation. A future solver receives ONLY this file + a test prompt + the env URL and must reproduce every convention exactly. Read the test prompt, identify the archetype, apply the universal rules below, then the archetype-specific section.

## 0. Environment

- The API base URL is the REMOTE ApexCloud Retention Operations API. Read it from `ENV_URL.txt` in the task staging directory (a single line like `http://host:port`). Do NOT assume the `http://127.0.0.1:8074` written inside prompt bodies — that is a placeholder; the real base is in `ENV_URL.txt`.
- All endpoints are JSON over HTTP GET unless noted. Append paths to the base URL.

### Endpoints (all confirmed against the live schema)
| Endpoint | Returns | Key fields |
|---|---|---|
| `/api/health` | row_counts + status | sanity check; confirms dataset sizes |
| `/api/accounts` | `{accounts:[...]}` | `account_id`, `legal_name`, `account_aliases`, `segment`, `region`, `renewal_date`, `contract_tenure_months`, `crm_arr`, `billing_arr_current`, `lifecycle_status`, `product_plan` |
| `/api/accounts/<id>` | single account object | same fields as above |
| `/api/accounts/<id>/metrics?start=YYYY-MM&end=YYYY-MM` | list of monthly metric rows | `month`, `recognized_revenue`, `sla_compliance` (account-level, NOT used for QBR), `product_usage`, `active_seats`, `support_ticket_count` (raw, NOT used for QBR), `nps_score`, `survey_status` |
| `/api/accounts/<id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` | list of tickets | `created_date`, `status` (`closed`/`open`/`cancelled`), `is_spam`, `is_duplicate`, `first_response_sla_met`, `resolution_sla_met`, `severity`, `product_area` |
| `/api/accounts/<id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` | list of NPS responses | `response_date`, `score`, `retracted` (bool), `survey_channel` |
| `/api/billing/snapshots` | `{count, snapshots:[...]}` | `account_id`, `as_of` (YYYY-MM-DD), `billing_arr`, `posted` (bool), `legal_name`, `mrr`, `source` |
| `/api/finance/ar-aging?as_of=YYYY-MM-DD` | `{ar_aging:[...]}` | `customer_name`, `as_of`, `current`, `1_30`, `31_60`, `61_90`, `90_plus`, `region`, `quarter` |
| `/api/opportunities?start=YYYY-MM-DD&end=YYYY-MM-DD&region=` | list of opps | `account_id`, `account_legal_name`, `amount`, `close_date`, `stage`, `state` (`open`/`closed`), `product_line`, `region` |
| `/api/hr/summary?quarter=YYYY-QN&region=<Region>` | `{count, hr_summary:[...]}` | per-region row: `region`, `quarter`, `headcount`, `unpaid_claims_amount`, `unpaid_claims_count`, `open_advances_amount`, `open_advances_count`, `attendance_rate`, `high_absence_employees`, `leave_liability_hours`. **PITFALL: `region=all` returns EMPTY (count 0).** For "all regions", either omit `region` (returns all 4 rows) or query each of `North America`/`EMEA`/`APAC`/`LATAM` and SUM the metric across rows. |
| `/api/events/performance?event=<slug>&quarter=YYYY-QN` | `{count, event_performance:[...]}` | `event_id`, `quarter`, `event_orders`, `event_revenue`, `completed_orders`, `pending_orders`, `cancelled_orders`, `refunded_orders`, `product_revenue` |
| `/exports/churn/train.csv` | 180 rows + header | 19 features + `Churn` target |
| `/exports/churn/validation.csv` | 60 rows + header | 19 features + `Churn` target |
| `/exports/churn/candidates.csv` | 44 rows + header | 19 features (no Churn); has `customer_id` |
| `/exports/account_metric_extract.csv` | 528 rows | account metric extract |

Opportunity stage → outcome mapping: `stage == "Closed Won"` (state `closed`) = **won**; `stage == "Closed Lost"` (state `closed`) = **lost**; every other stage (`Discovery`, `Prospecting`, `Proposal`, `Negotiation`, state `open`) = **open**. Pipeline window = `close_date` falls within the requested `[start, end]` inclusive. **PITFALL: `region=all` returns EMPTY for opportunities too** — for "all regions" either omit `region` (returns all rows) or query specific regions and combine.

## 1. Universal precision & formatting rules
- **Currency**: 2 decimals (e.g. `1416439.47`).
- **Percentages**: 1 decimal (e.g. `66.7`, `75.0`). `win_rate_pct` and `sla_compliance_pct` are percentages.
- **Integer counts**: no decimals (`risk_score`, `rank`, ticket counts, headcount, orders, account counts).
- **Probabilities (churn)**: 3 decimals (e.g. `0.102`). `average_probability_top5` also 3 decimals.
- **Dates**: `YYYY-MM-DD` (or `YYYY-MM` for months). Use null for a missing monthly NPS or for `next_touch_due_date` when action is `no_action`.
- Output is **JSON only**, following the answer template shape exactly (key order and nesting). Use controlled enum strings verbatim, including the misspelling `nurture_monitor` (do NOT "fix" it to nurture).

## 2. Universal data-hygiene conventions

### ARR source (policy `REV-4`)
`current_arr` = the **posted billing snapshot** `billing_arr` whose `as_of` equals the assessment date and `posted == true`.
- Do NOT use `account.crm_arr`.
- Do NOT use `account.billing_arr_current`.
- There is one posted snapshot per quarter (`as_of` = quarter-end date: `2026-03-31`, `2026-06-30`, `2026-09-30`, `2026-12-31`). Pick the one whose `as_of` == the task's assessment/as-of date.
- Example: northstar_finance as of 2026-06-30 → snapshot `billing_arr=1416439.47` (while `crm_arr=1268250.0`, `billing_arr_current=1425000.0` — both wrong).

### Overdue receivables (policy `RCP-7`)
`overdue_balance` = `ar_aging.61_90 + ar_aging.90_plus` for that customer/account as of the as-of date.
- `current`, `1_30`, `31_60` are NOT overdue.
- Example: northstar_finance 2026-06-30 → `61_90=8773.03 + 90_plus=0.0 = 8773.03`.
- polaris_health → `4561.21 + 3792.22 = 8353.43`.

### CRM receivable matching (policy `CM-5`)
For each A/R overdue `customer_name`, link to a CRM account by **exact case-sensitive string equality** between `ar_aging.customer_name` and `account.legal_name`.
- Exact match → `link_status: "linked"`, `account_id` set.
- No exact match → `link_status: "unlinked"`, `account_id: null`.
- Subsidiaries and aliases do NOT match even if similar. Confirmed unlinked: `"Globex North Subsidiary LLC"` (vs `Globex North Holdings LLC`), `"North Star Finance Services"` (vs `Northstar Finance Group Inc.`), `"Valence Payment Services Canada"` (vs `Valence Payment Services LLC`). `account_aliases` are IGNORED for matching (exact legal name only).

### Support ticket hygiene (policy `SUP-8`)
"Clean" tickets EXCLUDE tickets where `is_spam == true` OR `is_duplicate == true` OR `status == "cancelled"`.
- `clean_ticket_count` (per period) = count of remaining tickets.
- Monthly support-ticket counts (QBR) use the same cleaning, grouped by `created_date[:7]`.
- Example: globex_north 2026-06 raw=3, but 2 are duplicates → clean=1.

### NPS hygiene
Use only NPS responses with `retracted == false`. Ignore retracted/invalid responses.
- Monthly `nps_score` = the latest valid (non-retracted) response whose `response_date` falls in that month; `null` if none.
- `latest_nps` (period) = the latest valid response within the whole analysis period.
- These match `metrics.nps_score` for months that have a valid survey.

### SLA "sla_report" source
`sla_compliance_pct` (monthly) = `100 * (count of clean tickets that month with first_response_sla_met == true) / (clean ticket count that month)`.
- This is COMPUTED FROM TICKETS, not `metrics.sla_compliance` (which is a different account-level figure, e.g. 95.2 — do not use it for QBR/reason codes).
- Example: globex_north May has 4 clean tickets, 3 met first-response SLA → `75.0`. April 4/4 → `100.0`. June 1/1 → `100.0`.
- Use 1 decimal. If a month has 0 clean tickets, treat as `null`/100.0 per template.

### Pipeline window & win rate (policy `PW-6`)
- Filter opportunities to `close_date` within `[start, end]` inclusive.
- `won_count` / `won_revenue` = sum over Closed Won; `lost_count` = Closed Lost; `open_count` / `open_pipeline` = sum over all open stages.
- `win_rate_pct = won_count / (won_count + lost_count) * 100`, 1 decimal. (e.g. 6/(6+3)=66.7)
- `top_open_product_line` = the `product_line` with the largest sum of `amount` among OPEN opportunities (tie → unspecified, pick largest sum).

## 3. Reason codes (definitions + fixed ordering)

Reason codes are the controlled vocabulary used everywhere:
`overdue_receivable`, `low_tenure_high_churn`, `sla_degradation`, `nps_drop`, `usage_decline`, `renewal_window`, `expansion_offset`, `clean_billings`.

### Derivation rules (from live account data)
- `overdue_receivable` — `overdue_balance > 0` (61_90+90_plus > 0).
- `clean_billings` — `overdue_balance == 0` (billings clean). Mutually exclusive with `overdue_receivable`.
- `expansion_offset` — open expansion pipeline in the period > 0 (sum of open opportunity `amount` for this account with `close_date` in window). This is an OFFSET (positive) code, present whenever expansion pipeline exists, regardless of risk level.
- `renewal_window` — `account.renewal_date` is strictly AFTER the assessment date AND within 90 days after it. (Confirmed: flagged at 41–75 days out; NOT flagged for past renewals or >149 days out. Example: assessment 2026-06-30, renewal 2026-08-27 → 58 days → flagged; renewal 2026-06-11 → past → not flagged; renewal 2026-11-26 → 149 days → not flagged.)
- `low_tenure_high_churn` — `account.contract_tenure_months` is low (first-year, `tenure ≤ 13` months) AND elevated churn risk. (Confirmed flagged at tenure 7, 12, 13; not flagged at ≥20. In the churn export the same `≤ 13` rule applies.)
- `nps_drop` — latest valid NPS in period `< 40` (detractor threshold). (Confirmed: flagged at NPS 39 and 18; not flagged at 46, 53, 65.)
- `sla_degradation` — at least one clean ticket in the period missed first-response SLA (equivalently min monthly `sla_compliance_pct < 100`). Common; absence means all clean tickets met first-response SLA.
- `usage_decline` — usage trend is negative over the period (candidate `UsageTrendPct < 0`, or `metrics.product_usage` declining month-over-month). (northstar_finance `UsageTrendPct=-1.72` → decline; globex `+2.56` → no decline.)

### Fixed ordering of the reason_codes array (save plan & board)
When emitting a `reason_codes` array, order by this priority:
1. `renewal_window`
2. `overdue_receivable`
3. `nps_drop`
4. `sla_degradation`
5. `usage_decline`
6. `low_tenure_high_churn`
7. `expansion_offset`
8. `clean_billings`

(Verified against all gold arrays. `overdue_receivable` and `clean_billings` are mutually exclusive; `clean_billings` is only used in some archetypes — see §5.)

## 4. Risk model, actions, exposure, calendar

### Risk model RS-6
`risk_score` is an additive 0–100 composite. Each active risk driver contributes its base weight **scaled by severity** (the actual contribution ranges from 0 up to the base weight depending on how severely the condition is present for that account, computed from the underlying data). Credits offset the score. Then clamp.

**Base driver weights (RS-6):**
| Driver (reason code) | Base weight |
|---|---|
| `renewal_window` | +25 |
| `overdue_receivable` | +20 |
| `nps_drop` | +20 |
| `low_tenure_high_churn` | +20 |
| `usage_decline` | +15 |
| `sla_degradation` | +15 |

**Credits (offset / mitigating):** `expansion_offset` (open expansion pipeline in window), `clean_billings` (no overdue receivables). These reduce the score and are also emitted as reason-code flags per §3/archetype rules.

**Clamp:** `risk_score = max(0, min(100, sum_of_driver_contributions − credits))`. Emit as an **integer**.

The reason-code flags (§3) mark which dimensions are active; compute the flags, apply the severity-scaled weights + credits, clamp, then assign level + rank per the rules below.
- `tenure_risk_direction = "negative"` (higher tenure → lower churn/risk). Always `negative` for `model_checks.tenure_risk_direction`.
- `uses_billing_arr_source = true` (ARR is the posted billing snapshot, REV-4). Always `true`.

### Risk-level thresholds (authoritative, gold-confirmed)
- `critical`: score ≥ 80
- `high`: score 50–79
- `medium`: score 21–49
- `low`: score ≤ 20

### Ranking / sort order
- Retention risk queue / save plan (top-5): sort all reviewed accounts by `risk_score` desc, then `current_arr` desc, then `account_id` asc; return the top 5.
- Action board (all accounts): sort by `risk_level` (critical > high > medium > low), then `current_arr` desc, then `account_id` asc. (policy `BORD-4`). Equivalent to score-desc since level bins score.

### Primary action mapping (policy `ACT-5`)
**Save plan / board** `primary_action` priority:
1. `overdue_receivable` present (overdue_balance > 0) → `collections_followup`
2. else critical OR high OR medium with a technical/sentiment driver (`sla_degradation`, `nps_drop`, `usage_decline`) → `technical_recovery`
3. else `renewal_window` is the dominant driver (renewal imminent, no overdue, mild/none technical) → `renewal_save`
4. else low risk and no overdue → `no_action` (board) / `nurture_monitor` (when watchable)
5. `executive_qbr` is reserved for the highest-ARR critical accounts needing executive escalation (not always used; include its calendar date even if unused).

Confirmed gold:
- overdue>0 → `collections_followup` (northstar_finance, polaris_health, lumen_rail, valence).
- critical/high/medium without overdue but with nps/sla/usage → `technical_recovery` (peakstone critical, quartz_insure high, northstar_retail high, arcstone/summit_grid low-with-sla).
- low risk, no overdue → `no_action` with `next_touch_due_date: null` (bayside_bio, apexia) on the board.
- Medium with `renewal_window` + only mild `sla_degradation` → `renewal_save` (metrobyte) vs `technical_recovery` (solstice) — decided by whether renewal-timing or SLA severity dominates; when ambiguous, the stronger technical magnitude wins `technical_recovery`, a clean renewal-timing case wins `renewal_save`.

**Churn shortlist** `outreach_action` maps directly from the single `reason_code` (policy `OUT-2`):
- `overdue_receivable` → `collections_followup`
- `low_tenure_high_churn` → `renewal_save`
- `sla_degradation` / `nps_drop` / `usage_decline` → `technical_recovery`
- `expansion_offset` → `nurture_monitor`
- `clean_billings` → `nurture_monitor`

### Net revenue exposure (policy `EXP-6`)
- `arr_at_risk` = sum of `current_arr` over all reviewed accounts EXCLUDING low-risk accounts (i.e. critical + high + medium). Low-risk accounts are excluded.
- `open_expansion_pipeline` = sum of `expansion_pipeline` over ALL reviewed accounts (including low).
- `net_revenue_exposure = arr_at_risk - open_expansion_pipeline` (2 decimals).
- Verified: train 005 → 5736227.46 − 976490.66 = 4759736.80. train 001 → 1416439.47+705648.74+237281.77 = 2359369.98.

### Next-touch due-date calendar (policy `CAL-5`)
`next_touch_due_date` = assessment date + offset, by `primary_action`:
| action | offset | example (assess 2026-06-30) |
|---|---|---|
| `collections_followup` | +15 days | 2026-07-15 |
| `technical_recovery` | +18 days | 2026-07-18 |
| `renewal_save` | +22 days | 2026-07-22 |
| `executive_qbr` | +29 days | 2026-07-29 |
| `nurture_monitor` | +36 days | 2026-08-05 |
| `no_action` | — | `null` |
The `followup_calendar` object always lists the 5 action dates (exclude `no_action`).

### Segment counts (board)
`strategic_accounts` = count where `account.segment == "Strategic"`.
`enterprise_accounts` = count where `account.segment == "Enterprise"`.
(Segment values also include `Mid-Market`, `SMB` — only Strategic/Enterprise are tallied in these two fields; the board examples use accounts that are all Strategic/Enterprise.)

## 5. Archetype field definitions & computation

Identify the archetype from the prompt, then apply its schema. Use the answer template's exact key names and nesting.

### Archetype A — Renewal risk queue / save plan (train 001)
Prompt shape: "renewal risk queue", "top 5 ranked accounts by renewal risk", assessment date + analysis period + a list of account_ids.
```
{
  "risk_accounts": [ {rank, account_id, risk_score, risk_level, primary_action,
                      current_arr, latest_nps, clean_ticket_count, overdue_balance,
                      reason_codes:[...] } x5 ],
  "portfolio_summary": { accounts_reviewed, critical_or_high_count, arr_at_risk,
                         collections_count, technical_recovery_count },
  "model_checks": { uses_billing_arr_source, tenure_risk_direction },
  "policy_codes": { risk_model_code, arr_source_code, support_hygiene_code, action_priority_code }
}
```
Rules:
- Return exactly the **top 5** by risk_score desc / current_arr desc / account_id asc.
- `accounts_reviewed` = total number of account_ids given (e.g. 8), not just the top 5.
- `current_arr` = posted billing snapshot as of assessment date (REV-4).
- `latest_nps` = latest valid (non-retracted) NPS in period (integer).
- `clean_ticket_count` = clean tickets in period (SUP-8).
- `overdue_balance` = 61_90+90_plus as of assessment date (2 decimals).
- `reason_codes`: ordered per §3. **In this archetype, include `clean_billings` at the end when `overdue_balance == 0`** (and omit `overdue_receivable`). Include `expansion_offset` when expansion pipeline > 0. (Verified: arcstone/summit_grid/northstar_retail carry `clean_billings`; northstar_finance/polaris_health do not.)
- `risk_level`: critical/high/medium/low per §4 thresholds. (All 5 gold: critical, high, high, low, low — no medium in this example.)
- `primary_action`: per §4 ACT-5 priority.
- `arr_at_risk` = sum of `current_arr` for critical+high+medium (excludes low). Verified 2359369.98.
- `collections_count` = # of the 5 with `primary_action == collections_followup`.
- `technical_recovery_count` = # of the 5 with `primary_action == technical_recovery`.
- `critical_or_high_count` = # of the 5 that are critical or high.
- `model_checks`: `uses_billing_arr_source: true`, `tenure_risk_direction: "negative"`.
- `policy_codes`: RS-6, REV-4, SUP-8, ACT-5.

### Archetype B — QBR metrics packet (train 002)
Prompt shape: "QBR metrics packet", one account, one quarter, 3 months.
```
{
  "qbr_metrics":[ {month, revenue, support_tickets, sla_compliance_pct, nps_score} x3 ],
  "highlights": { average_revenue, peak_revenue_month, peak_revenue, max_sla_month,
                  max_sla_pct, peak_nps_month, peak_nps_score, ticket_trend },
  "metric_sources": { revenue, support_tickets, sla_compliance, nps },
  "review_plan": { review_owner, review_due_date, needs_technical_signoff },
  "agenda_topics": [4 enum strings]
}
```
Field computation (verified against globex_north 2026-Q2):
- `revenue` (month) = `metrics.recognized_revenue` for that month (2 decimals). Source label `"crm_closed_won"`.
- `support_tickets` (month) = clean ticket count that month (SUP-8). Source label `"support_export"`.
- `sla_compliance_pct` (month) = `100 * clean_tickets_with(first_response_sla_met) / clean_tickets` (1 decimal). Source label `"sla_report"`. (NOT `metrics.sla_compliance`.)
- `nps_score` (month) = latest valid NPS response that month (`null` if none). Source label `"nps_survey"`.
- `metric_sources` is the FIXED mapping: revenue→`crm_closed_won`, support_tickets→`support_export`, sla_compliance→`sla_report`, nps→`nps_survey`. (Available vocab: crm_closed_won, support_export, sla_report, nps_survey, billing_snapshot, ar_aging, pipeline_crm, event_dashboard, hr_report.)
- `average_revenue` = mean of the 3 monthly revenues (2 decimals).
- `peak_revenue_month` = month with max revenue; `peak_revenue` = that value.
- `max_sla_month` = month with max sla_compliance_pct (first month wins ties); `max_sla_pct` = that value.
- `peak_nps_month` = month with max nps_score (first wins ties, ignore null); `peak_nps_score` = that value (integer).
- `ticket_trend`: `improving` if tickets decrease overall (last month count < first month), `worsening` if increase, `flat` if equal. (4,4,1 → improving.)
- `review_owner`: `customer_success` for a standard QBR. Override to `solutions_engineering` only for severe technical-recovery-led reviews, `finance_ops` for receivables-led reviews. (Vocab: solutions_engineering, customer_success, finance_ops.)
- `review_due_date` = quarter-end date + 22 days (Q2 2026 → 2026-06-30 + 22 = 2026-07-22). (Matches the template pre-fill; compute as assessment/quarter-end + 22.)
- `needs_technical_signoff`: boolean. `false` unless SLA compliance falls below a severe floor (e.g. a month < ~70%) or engineering signoff is explicitly required. (Observed `false` with min SLA 75%.)
- `agenda_topics`: exactly 4 ordered enums from: partnership_overview, q2_metrics, performance_highlights, q3_initiatives, technical_recovery, commercial_expansion. Standard order: [`partnership_overview`, `q2_metrics`, <slot3>, `q3_initiatives`]. Slot 3 = `technical_recovery` if SLA degraded in period (any month <100), else `performance_highlights` if performance strong, else `commercial_expansion` if expansion pipeline exists. (globex chose `technical_recovery` due to 75% SLA month.)

### Archetype C — Receivables + pipeline operations digest (train 003)
Prompt shape: "operations review", "Q3 receivables and pipeline", A/R as-of date, region, HR/event context, a follow-up due date for overdue actions.
```
{
  "financial_summary": { overdue_client_count, overdue_total, linked_followup_count, unlinked_followup_count },
  "pipeline_summary": { won_count, won_revenue, lost_count, open_count, open_pipeline, win_rate_pct, top_open_product_line },
  "overdue_followups": [ {customer_name, link_status, account_id, overdue_balance, due_date, primary_action} ],
  "ops_context": { hr_headcount, unpaid_claims_total, event_orders, event_revenue },
  "policy_codes": { receivable_trigger_code, crm_match_code, pipeline_window_code, followup_scope_code }
}
```
Field computation (verified against 2026-Q3):
- Start from `/api/finance/ar-aging?as_of=<as_of>`. A customer is overdue if `61_90 + 90_plus > 0`.
- `overdue_client_count` = # of overdue customers. `overdue_total` = sum of their overdue balances (2 dp). (Gold: 13, 190312.41.)
- For each overdue customer, match to CRM by exact legal name (CM-5): `linked`/`unlinked` + `account_id` (null if unlinked).
- `linked_followup_count` / `unlinked_followup_count` = counts thereof. (Gold: 8 / 5.)
- `overdue_followups`: one object per overdue customer, fields `customer_name` (the ar-aging customer_name), `link_status`, `account_id` (null if unlinked), `overdue_balance` (61_90+90_plus, 2 dp), `due_date` (the follow-up due date stated in the prompt, e.g. 2026-10-15), `primary_action` = `"collections_followup"` for all. **Sort by `customer_name` ascending.**
- `pipeline_summary` from `/api/opportunities?start=<q_start>&end=<q_end>` (close_date in quarter, PW-6): `won_count`/`won_revenue`, `lost_count`, `open_count`/`open_pipeline`, `win_rate_pct` (1 dp), `top_open_product_line` (max open amount by product_line). (Gold: 6 / 193720.31 / 3 / 25 / 3043511.10 / 66.7 / "Data Cloud".)
- `ops_context`: `hr_headcount` = SUM of `headcount` across the 4 regional HR rows (do NOT pass `region=all` — it returns empty; omit `region` or query each region); `unpaid_claims_total` = SUM of regional `unpaid_claims_amount` (output field is named `unpaid_claims_total`; source field is `unpaid_claims_amount`); `event_orders` = `event_performance.event_orders`; `event_revenue` = `event_performance.event_revenue` from `/api/events/performance?event=<slug>&quarter=<Q>`. (Gold: 377 / 92850.39 / 445 / 309724.17.)
- `policy_codes`: RCP-7, CM-5, PW-6, FS-4.

### Archetype D — Churn model validation + outreach ranking (train 004)
Prompt shape: "churn model validation", "outreach ranking", lists candidate account_ids, asks for top 5 by predicted churn probability. Exports: `/exports/churn/{train,validation,candidates}.csv`.
```
{
  "model_validation": { training_rows, validation_rows, feature_count, accuracy_pct, accuracy_band, tenure_coefficient_direction },
  "risk_ranking": [ {rank, customer_id, predicted_churn_probability, outreach_action, reason_code} x5 ],
  "cohort_checks": { past_due_shortlist_count, low_tenure_shortlist_count, average_probability_top5 },
  "model_policy_codes": { model_protocol_code, probability_scale_code, deployment_rule_code, outreach_mapping_code }
}
```
Churn model spec (EXACT — produces 93.3% accuracy; do not vary):
- `sklearn.linear_model.LogisticRegression(C=1.0, solver="lbfgs")`
- Numeric features → `StandardScaler`; categorical features → `OneHotEncoder(drop="first")`. **`drop="first"` is REQUIRED** (drop=None yields 91.7%, wrong).
- Features = 19 (exclude `customer_id` as it is the row id; exclude `Churn` target). Train rows = 180, validation rows = 60.
- `accuracy_pct` = 93.3 (1 dp). `accuracy_band` = `"90_plus"` (bands: below_70, 70_to_79, 80_to_89, 90_plus).
- `tenure_coefficient_direction` = `"negative"` (higher tenure lowers churn probability).
- Train on train.csv, evaluate on validation.csv, then `predict_proba` on candidates.csv for the positive (churn) class.
- `deployment_rule_code` DEP-5 = **approve_with_monitoring** (the model is approved for deployment with monitoring).
Candidate ranking:
- `predicted_churn_probability` = `predict_proba` positive class, **3 decimals** (PRB-4).
- Rank the given candidate account_ids by `predicted_churn_probability` DESC; return top 5. Tie-break by higher probability then `customer_id` asc.
- `reason_code` (single) — derived from the candidate row's features in candidates.csv (NOT from live ar-aging), by this priority:
  1. `InvoicePastDue == "Yes"` → `overdue_receivable`
  2. `tenure` ≤ 13 (low, first-year) → `low_tenure_high_churn`
  3. `NPSLast` < 40 → `nps_drop`
  4. `SupportTickets90d` high (SLA stress) → `sla_degradation`
  5. `UsageTrendPct` < 0 → `usage_decline`
  6. otherwise → `clean_billings`
  (Confirmed: globex_north `InvoicePastDue=No, tenure=29, NPSLast=72, UsageTrendPct=2.56` → `clean_billings`; northstar_finance `tenure=12, InvoicePastDue=No` → `low_tenure_high_churn`; tandemworks `InvoicePastDue=Yes` → `overdue_receivable`.)
- `outreach_action` = map from `reason_code` per §4 OUT-2.
- `cohort_checks` are counted over the **TOP-5 shortlist (the returned `risk_ranking` list)**, NOT the full candidate set:
  - `past_due_shortlist_count` = # of the top-5 with `InvoicePastDue == "Yes"`. (Gold: 1 — only tandemworks; quartz_insure is also past-due but is NOT in the top 5, proving the scope is the shortlist.)
  - `low_tenure_shortlist_count` = # of the top-5 with `tenure ≤ 13`. (Gold: 3 — tandemworks(7), northstar_finance(12), northstar_retail(13).)
  - `average_probability_top5` = mean of the 5 ranked probabilities, 3 decimals. (Gold: (0.102+0.039+0.032+0.001+0.001)/5 = 0.035.)
- `model_policy_codes`: MOD-7, PRB-4, DEP-5, OUT-2.
- Note: the candidate export's overdue/usage signals are independent of the live A/R aging — a candidate may show `clean_billings` even if live ar-aging shows overdue (different data source/as-of). Always use the candidate row features for the churn `reason_code`.

### Archetype E — High-touch retention action board / watchlist (train 005)
Prompt shape: "retention action board", "operating review", lists account_ids, gives follow-up due dates per action, says "return all accounts in standard retention board order".
```
{
  "action_board": [ {rank, account_id, risk_level, primary_action, current_arr,
                      expansion_pipeline, overdue_balance, next_touch_due_date, reason_codes:[...]} x N ],
  "segment_summary": { strategic_accounts, enterprise_accounts, arr_at_risk, open_expansion_pipeline, net_revenue_exposure },
  "followup_calendar": { collections_followup, technical_recovery, renewal_save, executive_qbr, nurture_monitor },
  "policy_codes": { risk_model_code, arr_source_code, support_hygiene_code, action_priority_code,
                    board_sort_code, exposure_formula_code, calendar_policy_code }
}
```
Rules:
- Return ALL listed accounts (not just top 5), ranked by risk_level (critical>high>medium>low) → current_arr desc → account_id asc (BORD-4).
- `current_arr` = posted billing snapshot as of assessment date (REV-4).
- `expansion_pipeline` = sum of OPEN opportunity `amount` for the account with `close_date` in the analysis period (2 dp).
- `overdue_balance` = 61_90+90_plus as of assessment date (2 dp).
- `risk_level` per §4 thresholds.
- `primary_action` per §4 ACT-5 priority; `no_action` for low-risk accounts without overdue (and `next_touch_due_date: null`).
- `next_touch_due_date` = assessment date + offset per §4 CAL-5 by `primary_action`; `null` for `no_action`.
- `reason_codes`: ordered per §3. **In this archetype, do NOT include `clean_billings`** — list only the active risk/offset codes (renewal_window, overdue_receivable, nps_drop, sla_degradation, usage_decline, low_tenure_high_churn, expansion_offset). `expansion_offset` IS included when expansion_pipeline > 0 (even for low-risk/no_action accounts). (Verified: bayside_bio [sla_degradation, expansion_offset]; apexia [nps_drop]; none carry clean_billings.)
- `segment_summary.strategic_accounts` = count `segment=="Strategic"`; `enterprise_accounts` = count `segment=="Enterprise"`; `arr_at_risk` = sum current_arr excluding low-risk; `open_expansion_pipeline` = sum expansion_pipeline over all; `net_revenue_exposure` = arr_at_risk − open_expansion_pipeline (EXP-6).
- `followup_calendar` = all 5 action due dates from the prompt's stated map (or assessment date + offsets per §4).
- `policy_codes`: RS-6, REV-4, SUP-8, ACT-5, BORD-4, EXP-6, CAL-5.

## 6. Policy-code dictionary (EXACT values — emit these verbatim)

When the answer template shows a multiple-choice like `"RS-2|RS-6|RS-9"`, emit the single gold value below.

| Code field | Options (template) | GOLD value | Meaning |
|---|---|---|---|
| `risk_model_code` | RS-2 \| RS-6 \| RS-9 | **RS-6** | retention risk model (0–100 composite, level thresholds, ranking) |
| `arr_source_code` | REV-1 \| REV-4 \| REV-8 | **REV-4** | ARR = posted billing snapshot as of assessment date |
| `support_hygiene_code` | SUP-3 \| SUP-8 \| SUP-9 | **SUP-8** | clean tickets exclude spam/duplicate/cancelled |
| `action_priority_code` | ACT-1 \| ACT-5 \| ACT-7 | **ACT-5** | primary-action priority model |
| `receivable_trigger_code` | RCP-4 \| RCP-7 \| RCP-9 | **RCP-7** | overdue = 61_90 + 90_plus buckets |
| `crm_match_code` | CM-2 \| CM-5 \| CM-8 | **CM-5** | exact legal-name match (subsidiaries/aliases unlinked) |
| `pipeline_window_code` | PW-3 \| PW-6 \| PW-9 | **PW-6** | pipeline = opportunities with close_date in range |
| `followup_scope_code` | FS-1 \| FS-4 \| FS-8 | **FS-4** | follow-up scope (overdue receivables follow-ups) |
| `model_protocol_code` | MOD-2 \| MOD-7 \| MOD-9 | **MOD-7** | LogReg(C=1.0,lbfgs)+StandardScaler+OneHot(drop="first"), 19 features |
| `probability_scale_code` | PRB-1 \| PRB-4 \| PRB-8 | **PRB-4** | churn probability to 3 decimals |
| `deployment_rule_code` | DEP-3 \| DEP-5 \| DEP-9 | **DEP-5** | approve_with_monitoring |
| `outreach_mapping_code` | OUT-2 \| OUT-6 \| OUT-8 | **OUT-2** | outreach_action mapped from reason_code |
| `board_sort_code` | BORD-1 \| BORD-4 \| BORD-8 | **BORD-4** | board sort: risk_level desc → current_arr desc → account_id asc |
| `exposure_formula_code` | EXP-2 \| EXP-6 \| EXP-9 | **EXP-6** | net_revenue_exposure = arr_at_risk − open_expansion_pipeline (arr_at_risk exch. low) |
| `calendar_policy_code` | CAL-3 \| CAL-5 \| CAL-7 | **CAL-5** | next-touch due-date offsets by action |

## 7. Worked gold reference (for self-check)

Reproduce these exactly when running the train prompts:
- **001** (save plan, assess 2026-06-30): top5 = northstar_finance(100,critical,collections,1416439.47,nps39,tickets13,overdue8773.03), polaris_health(60,high,collections,705648.74,53,14,8353.43), northstar_retail(50,high,technical,237281.77,18,14,0.0), arcstone(20,low,technical,536552.47,65,12,0.0), summit_grid(15,low,technical,141895.58,46,4,0.0). portfolio: reviewed 8, crit/high 3, arr_at_risk 2359369.98, collections 2, technical 3. model_checks: billing true, tenure negative. codes RS-6/REV-4/SUP-8/ACT-5.
- **002** (QBR globex_north 2026-Q2): metrics Apr(95756.67,4,100.0,45) May(98509.22,4,75.0,61) Jun(105156.27,1,100.0,56); avg_revenue 99807.39; peak_rev Jun 105156.27; max_sla Apr 100.0; peak_nps May 61; ticket_trend improving; sources crm_closed_won/support_export/sla_report/nps_survey; review_plan customer_success / 2026-07-22 / false; agenda [partnership_overview, q2_metrics, technical_recovery, q3_initiatives].
- **003** (ops digest 2026-Q3, as-of 2026-09-30, due 2026-10-15): overdue_client_count 13, overdue_total 190312.41, linked 8, unlinked 5; pipeline 6/193720.31/3/25/3043511.10/66.7/"Data Cloud"; ops 377/92850.39/445/309724.17; codes RCP-7/CM-5/PW-6/FS-4. overdue_followups sorted by customer_name asc (Aurora Textiles → Valence Payment Services LLC).
- **004** (churn): train 180 / val 60 / features 19 / acc 93.3 / 90_plus / tenure negative; top5 tandemworks(0.102,collections,overdue_receivable), northstar_finance(0.039,renewal_save,low_tenure_high_churn), northstar_retail(0.032,renewal_save,low_tenure_high_churn), globex_north(0.001,nurture_monitor,clean_billings), valence(0.001,nurture_monitor,clean_billings); cohort 1/3/0.035; codes MOD-7/PRB-4/DEP-5/OUT-2.
- **005** (board assess 2026-06-30): peakstone(critical,technical,1260762.32,0,0,2026-07-18), lumen_rail(high,collections,1147391.72,0,9183.05,2026-07-15), quartz_insure(high,technical,1080112.29,793202.42,0,2026-07-18), metrobyte(medium,renewal_save,871896.76,0,0,2026-07-22), solstice(medium,technical,849883.74,0,0,2026-07-18), valence(medium,collections,526180.63,64483.34,10044.4,2026-07-15), bayside_bio(low,no_action,564466.38,118804.9,0,null), apexia(low,no_action,511314.88,0,0,null); segment 3/5; arr_at_risk 5736227.46; open_expansion 976490.66; net_exposure 4759736.80; codes RS-6/REV-4/SUP-8/ACT-5/BORD-4/EXP-6/CAL-5.

## 8. Execution checklist
1. Read `ENV_URL.txt` → set BASE.
2. Parse prompt → identify archetype (A–E) and parameters (account_ids, dates, as-of, region, event slug).
3. `GET /api/health` once to confirm reachability (optional).
4. Fetch only the endpoints the archetype needs. Apply hygiene (REV-4, RCP-7, CM-5, SUP-8, NPS retracted, PW-6) before computing.
5. Compute reason codes (§3), risk level/thresholds (§4), action mapping (§4), exposure/calendar (§4).
6. For churn (D): train the LogReg model exactly per §5-D; do not change hyperparameters or `drop`.
7. Round per §1 (currency 2dp, pct 1dp, int counts, prob 3dp).
8. Emit JSON matching the template key order; fill the policy_codes with the §6 gold values; preserve controlled enum strings exactly (incl. `nurture_monitor`).
