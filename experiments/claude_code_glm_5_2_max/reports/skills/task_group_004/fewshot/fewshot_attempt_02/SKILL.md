# ApexCloud Retention Operations — CRM Retention Analytics Skill

Executable experience for solving ApexCloud CRM retention-analytics tasks against the
ApexCloud Retention Operations API. A solver receiving only this file + a task prompt +
the environment URL must reproduce every convention below exactly.

## 0. Environment & endpoint usage

- The API base URL is given in the task's `ENV_URL.txt` (a remote HTTP endpoint). Task
  prompts may print `http://127.0.0.1:8074` as an example — **ignore that literal** and use
  the URL from `ENV_URL.txt`. Do not attempt to run any `setup.sh`.
- Public endpoints:
  - `GET /api/health` — service/row-count sanity check.
  - `GET /api/accounts` — list all accounts (44).
  - `GET /api/accounts/<id>` — one account profile.
  - `GET /api/accounts/<id>/metrics?start=YYYY-MM&end=YYYY-MM` — monthly recognized_revenue,
    clean_ticket_count, sla_compliance (weighted), nps_score, product_usage, active_seats.
  - `GET /api/accounts/<id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` — raw support tickets.
  - `GET /api/accounts/<id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` — raw NPS responses.
  - `GET /api/billing/snapshots` — quarterly posted billing snapshots (ARR/MRR).
  - `GET /api/finance/ar-aging?as_of=YYYY-MM-DD` — A/R aging buckets per customer.
  - `GET /api/opportunities?start=YYYY-MM-DD&end=YYYY-MM-DD` — CRM pipeline.
  - `GET /api/hr/summary?quarter=YYYY-Qn` — HR summary per region.
  - `GET /api/events/performance?event=<id>&quarter=YYYY-Qn` — event performance.
  - `GET /exports/churn/{train,validation,candidates}.csv` — churn model dataset.
  - `GET /exports/account_metric_extract.csv` — 12-month metric extract (44 accounts).
- **Region parameter rule:** to retrieve ALL regions, **omit** `region` entirely. Passing
  `region=all` returns an empty result (opportunities, HR). For a single region pass the
  literal region name (e.g. `North%20America`).
- Opportunities are matched by `close_date` within `[start, end]`. Each opportunity has
  `stage` and `state` (`open` for any non-closed stage; `closed` for Closed Won / Closed Lost).
- Dates: assessment date and A/R as-of date are always quarter-end boundaries
  (e.g. 2026-06-30, 2026-09-30). Analysis periods are full quarters.

## 1. Global output conventions (deterministic precision)

- Currency: **2 decimals**.
- Percentages: **1 decimal**.
- Counts and risk scores: **integers**.
- Churn probabilities: **3 decimals**.
- NPS scores: integers (per-response 0–100; `-1` is an invalid placeholder — ignore it).
- Return **only** the JSON object matching the task's answer template; no prose, no markdown.
- Use the controlled enum values exactly as shown in each template.

## 2. Stable policy-code dictionary (emit exactly these values)

These codes are constant across this task group. Each task template shows a `|`-separated
option list; always select the value below.

| Code field | Value | Meaning |
|---|---|---|
| `risk_model_code` | **RS-6** | retention risk model |
| `arr_source_code` | **REV-4** | ARR taken from posted billing snapshots (as-of assessment date) |
| `support_hygiene_code` | **SUP-8** | clean tickets exclude spam, duplicate, cancelled |
| `action_priority_code` | **ACT-5** | primary-action precedence |
| `receivable_trigger_code` | **RCP-7** | overdue = late buckets only (61_90 + 90_plus) |
| `crm_match_code` | **CM-5** | exact legal-name match only |
| `pipeline_window_code` | **PW-6** | pipeline selected by close_date in analysis window |
| `followup_scope_code` | **FS-4** | linked_when_exact_else_standalone |
| `model_protocol_code` | **MOD-7** | churn training protocol (logistic, 19 features) |
| `probability_scale_code` | **PRB-4** | probability on 0–1 scale, 3 decimals |
| `deployment_rule_code` | **DEP-5** | approve_with_monitoring (accuracy band 90_plus) |
| `outreach_mapping_code` | **OUT-2** | churn outreach action/reason mapping |
| `board_sort_code` | **BORD-4** | board order: risk_level desc, current_arr desc, account_id asc |
| `exposure_formula_code` | **EXP-6** | net_revenue_exposure = arr_at_risk − open_expansion_pipeline |
| `calendar_policy_code` | **CAL-5** | next-touch due-date mapping by primary_action |

Only emit the `policy_codes` / `model_policy_codes` block that the task's template includes.

## 3. Data-source & hygiene rules

### 3.1 Current ARR (REV-4)
- `current_arr` = the `billing_arr` field of the **posted** billing snapshot whose `as_of`
  equals the assessment date (NOT the account's `billing_arr_current`, NOT `crm_arr`).
- Snapshots are quarterly (`as_of` = quarter-end). Pick the one matching the assessment date.
- Example: assessment 2026-06-30 → snapshot `BILL-...-2026-Q2`, `billing_arr`.

### 3.2 Support tickets (SUP-8)
- A **clean ticket** = `is_spam == false` AND `is_duplicate == false` AND `status != "cancelled"`.
- `clean_ticket_count` (per period) = count of clean tickets with `created_date` in
  `[start, end]`.
- The `metrics`/extract `support_ticket_count`/`clean_ticket_count` field already reflects
  cleaning; for QBR monthly counts use the extract's `clean_ticket_count`.
- SLA fields per ticket: `first_response_sla_met`, `resolution_sla_met` (booleans).
  - **sla_degradation reason** fires if ANY clean ticket in the period has
    `first_response_sla_met == false` OR `resolution_sla_met == false` (i.e. not 100% of
    clean tickets meet both SLAs).
  - **QBR `sla_compliance_pct`** (per month) = 100 * (clean tickets in month with
    `first_response_sla_met == true`) / (clean tickets in month), to 1 decimal. (Use
    ticket-level data; do NOT use the extract's weighted `sla_compliance`.)

### 3.3 NPS (nps_survey)
- Ignore responses with `retracted == true` (and invalid scores like `-1`).
- **`latest_nps`** (single value for a period) = score of the most recent (by
  `response_date`) non-retracted, valid response within `[start, end]`.
- Monthly NPS = that month's latest valid response score (= extract `nps_score`).

### 3.4 A/R aging & overdue (RCP-7)
- `overdue_balance` = `61_90` + `90_plus` buckets from `ar-aging` at the as-of date
  (late buckets only; exclude `current`, `1_30`, `31_60`).
- `overdue_receivable` reason fires iff `overdue_balance > 0`.
- `clean_billings` reason fires iff `overdue_balance == 0` (mutually exclusive with
  `overdue_receivable`).

### 3.5 CRM matching (CM-5, FS-4)
- Link an A/R `customer_name` to a CRM account **only on exact equality** with the account's
  `legal_name`. Aliases (`account_aliases`), subsidiaries, regional variants, and
  near-matches are **never** linked (`do_not_link_aliases`).
- Linked → `link_status: "linked"`, `account_id` set. Otherwise `link_status: "unlinked"`,
  `account_id: null`.
- Examples observed: "Globex North Holdings LLC"→linked(acct_globex_north) but
  "Globex North Subsidiary LLC"→unlinked; "Northstar Finance Group Inc."→linked but
  "North Star Finance Services"→unlinked; "Valence Payment Services LLC"→linked but
  "Valence Payment Services Canada"→unlinked.

### 3.6 Pipeline / opportunities (PW-6)
- Window: opportunity `close_date` within `[start, end]`.
- Outcomes: **Closed Won** and **Closed Lost** are closed (`state: "closed"`); every other
  stage (Discovery, Prospecting, Proposal, Negotiation) is open (`state: "open"`).
- `open_pipeline` = sum of `amount` over open opportunities with close_date in window.
- `expansion_pipeline` (per account) = sum of `amount` over the account's **open**
  opportunities with close_date in the analysis window.
- `won_count`/`won_revenue`, `lost_count`, `open_count` over the same window.
- `win_rate_pct` = 100 * `won_count` / (`won_count` + `lost_count`), 1 decimal.
  (Denominator = Closed Won + Closed Lost only.)
- `top_open_product_line` = product line with the greatest total open-pipeline amount.
- `expansion_offset` reason fires iff the account's `expansion_pipeline` > 0 (open
  expansion opportunities in window offset the risk).

### 3.7 HR & events
- `GET /api/hr/summary?quarter=<Q>` (omit region) returns one row per region.
  - `hr_headcount` = sum of `headcount` across all regions.
  - `unpaid_claims_total` = sum of `unpaid_claims_amount` across all regions.
- `GET /api/events/performance?event=<id>&quarter=<Q>`:
  - `event_orders` = `event_orders`; `event_revenue` = `event_revenue`.

## 4. Retention risk model (RS-6) — reason codes

For each reviewed account compute these reason triggers over the analysis period. Risk
reasons (count toward level) and mitigating reasons (do not count) are separated.

### 4.1 Risk reasons
- **renewal_window**: account `renewal_date` is on/after the assessment date and within the
  next quarter (≈ next 90 days). (Assessment dates are quarter-ends, so this = renewal in
  the immediately following quarter.)
- **overdue_receivable**: `overdue_balance` (61_90 + 90_plus) > 0.
- **nps_drop**: latest valid NPS in period is a strong detractor OR a clear in-period
  decline. Rule: `latest_nps < 40` OR (`latest_nps < 50` AND `latest_nps` < the previous
  valid in-period response). (Recovering-but-still-low scores < 40 still fire; a score that
  rose from a prior low does not fire unless < 40.)
- **sla_degradation**: any clean ticket in period has `first_response_sla_met == false` OR
  `resolution_sla_met == false`.
- **usage_decline**: period-average `product_usage` below ~65 (low absolute usage; not a
  trend — a dipping-then-recovering account above 65 does not fire).
- **low_tenure_high_churn**: `contract_tenure_months < 24` AND the churn-data `Contract` is
  `Month-to-month`. (Per the candidates export; indicates high intrinsic churn risk.)

### 4.2 Mitigating / positive reasons (do not count toward level)
- **expansion_offset**: `expansion_pipeline` (open opps in window) > 0.
- **clean_billings**: `overdue_balance == 0`.

### 4.3 Risk level (BORD-4 input)
Let `risk_reason_count` = number of triggered reasons among the six risk reasons above
(excluding `expansion_offset` and `clean_billings`).

- **critical** iff `renewal_window` AND `nps_drop` AND `usage_decline` all fire
  (renewal + sentiment + usage crisis).
- else **high** iff `risk_reason_count >= 3`.
- else **medium** iff `risk_reason_count == 2`.
- else **low** iff `risk_reason_count <= 1`.

This rule reproduces all train accounts.

### 4.4 Risk score (numeric, integer, cap 100)
`risk_score` is a weighted RS-6 risk index; heavy weights apply to `renewal_window` and
`overdue_receivable`, medium to `nps_drop`/`usage_decline`/`low_tenure_high_churn`, light to
`sla_degradation`, with a revenue-exposure term from `current_arr`, mitigated by
`expansion_offset`/`clean_billings`, capped at 100. The score is monotonic with (a) level
and (b) `current_arr` within a level. Reference train values: critical = 100; high band
≈ 50–60; medium band ≈ 20–39; low band ≈ 15–20. When an exact numeric score is required and
the precise weighting is uncertain, assign a score in the level's band that preserves the
**within-level order by `current_arr` desc** so the ranking is correct.

### 4.5 Ranking (risk queue and board)
- **Risk queue (top-N) and retention board:** order by `risk_level` severity desc
  (critical > high > medium > low), then `current_arr` desc, then `account_id` asc.
  (Equivalent to the documented "score desc, current_arr desc, account_id asc" once scores
  follow §4.4.) Verified against both the queue and the board.

## 5. Primary action mapping (ACT-5) and next-touch calendar (CAL-5)

Evaluate in this precedence; first match wins.

1. **collections_followup** — `overdue_receivable` fires (overdue_balance > 0). Any level.
2. **At low level only** (and no overdue):
   - **technical_recovery** iff `sla_degradation` fires AND `expansion_offset` does NOT
     fire.
   - else **no_action**. (Low + nps_drop alone → no_action; low + sla_degradation +
     expansion_offset → no_action — the expansion offsets it.)
3. **At medium/high/critical** (and no overdue):
   - **renewal_save** iff `renewal_window` fires AND there is **no** strong technical
     signal — i.e. no `nps_drop`, no `usage_decline`, and no first-response SLA breach
     (`first_response_sla_met` is true for all clean tickets). (A resolution-only SLA
     breach still allows renewal_save; a first-response breach sends the account to
     technical_recovery.)
   - else **technical_recovery** iff any of `nps_drop`, `usage_decline`, or
     `sla_degradation` fires.
   - else **nurture_monitor** iff `expansion_offset` fires (no other driver).
   - else **no_action**.
4. **executive_qbr** is reserved for strategic accounts needing executive attention when no
   higher-priority driver applies (not triggered in train data).

### Next-touch due-date mapping (CAL-5) — board task
- `collections_followup` → assessment_date + 15 days (e.g. 2026-07-15 for 2026-06-30)
- `technical_recovery` → +18 days (2026-07-18)
- `renewal_save` → +22 days (2026-07-22)
- `executive_qbr` → +29 days (2026-07-29)
- `nurture_monitor` → +36 days (2026-08-05)
- `no_action` → `next_touch_due_date: null`

(When the task prompt gives explicit due dates, use those exact dates verbatim — they
encode CAL-5.)

## 6. Task archetypes & output field definitions

### A. Renewal Risk Queue (top-N) — RS-6
Output keys: `risk_accounts` (ordered list of N), `portfolio_summary`, `model_checks`,
`policy_codes`. Each risk_account: `rank`, `account_id`, `risk_score`, `risk_level`,
`primary_action`, `current_arr`, `latest_nps`, `clean_ticket_count`, `overdue_balance`,
`reason_codes`.
- `clean_ticket_count` = total clean tickets across the analysis period (sum of monthly).
- `reason_codes` = all triggered reasons (risk + mitigating), in this canonical order:
  `renewal_window`, `overdue_receivable`, `nps_drop`, `sla_degradation`, `usage_decline`,
  `low_tenure_high_churn`, `expansion_offset`, `clean_billings` (omit any that do not fire;
  keep relative order).
- `portfolio_summary`:
  - `accounts_reviewed` = size of the provided account set.
  - `critical_or_high_count` = # reviewed accounts at critical or high.
  - `arr_at_risk` = sum of `current_arr` over reviewed accounts with level != low, 2dp.
  - `collections_count` = # risk_accounts with `primary_action == collections_followup`.
  - `technical_recovery_count` = # risk_accounts with `primary_action == technical_recovery`.
- `model_checks`: `uses_billing_arr_source: true` (REV-4), `tenure_risk_direction:
  "negative"` (low tenure raises churn risk).

### B. QBR Metrics Packet — single account, one quarter
Output keys: `qbr_metrics` (one per month), `highlights`, `metric_sources`, `review_plan`,
`agenda_topics`. Per month: `month`, `revenue`, `support_tickets`, `sla_compliance_pct`,
`nps_score`.
- `revenue` = extract `recognized_revenue` for the month (source label `crm_closed_won`),
  2dp.
- `support_tickets` = extract `clean_ticket_count` for the month (source label
  `support_export`).
- `sla_compliance_pct` = monthly first-response SLA % from ticket-level data
  (source label `sla_report`), 1dp. (Not the extract's weighted sla_compliance.)
- `nps_score` = extract `nps_score` for the month (source label `nps_survey`); `null` if no
  valid response that month.
- `highlights`: `average_revenue` (mean of monthly revenue, 2dp), `peak_revenue_month`/
  `peak_revenue` (max), `max_sla_month`/`max_sla_pct` (max sla_compliance_pct), 
  `peak_nps_month`/`peak_nps_score` (max nps_score), `ticket_trend` = `improving` if monthly
  clean-ticket count is non-increasing and ends lower; `worsening` if non-decreasing and
  ends higher; else `flat`.
- `metric_sources` always: `revenue: crm_closed_won`, `support_tickets: support_export`,
  `sla_compliance: sla_report`, `nps: nps_survey`.
- `review_plan`: `review_owner: customer_success`; `review_due_date` = the date stated in
  the prompt (e.g. 2026-07-22); `needs_technical_signoff: true` iff `ticket_trend ==
  worsening` (i.e. a degrading support situation), else `false`.
- `agenda_topics`: exactly four, ordered:
  [`partnership_overview`, `q2_metrics`, `<technical_recovery | commercial_expansion>`,
  `q3_initiatives`]. Use `technical_recovery` as the 3rd topic when the account has SLA
  degradation / a worsening ticket trend; otherwise `commercial_expansion`. (Adjust the
  quarter label to the prompt's quarter, e.g. `q3_metrics`, `q4_initiatives`.)

### C. Receivables & Pipeline Operations Review (RCM/PW) — one quarter, all regions
Output keys: `financial_summary`, `pipeline_summary`, `overdue_followups`, `ops_context`,
`policy_codes`.
- Start from `ar-aging` at the as-of date; **overdue customers** = those with
  (61_90 + 90_plus) > 0. `overdue_client_count` = their count; `overdue_total` = sum of
  their overdue balances (2dp).
- `overdue_followups`: one per overdue customer, sorted by `customer_name` ascending. Each:
  `customer_name`, `link_status` (linked/unlinked per CM-5), `account_id` (or null),
  `overdue_balance` (61_90+90_plus, 2dp), `due_date` (the date stated in the prompt, e.g.
  2026-10-15), `primary_action: collections_followup`.
  - `linked_followup_count` = # linked; `unlinked_followup_count` = # unlinked.
- `pipeline_summary` (opportunities with close_date in the quarter, all regions):
  `won_count`, `won_revenue` (2dp), `lost_count`, `open_count`, `open_pipeline` (2dp),
  `win_rate_pct` = 100*won/(won+lost) (1dp), `top_open_product_line`.
- `ops_context`: `hr_headcount` (sum across regions), `unpaid_claims_total` (sum of
  `unpaid_claims_amount`, 2dp), `event_orders`, `event_revenue` (2dp).
- `policy_codes`: `receivable_trigger_code: RCP-7`, `crm_match_code: CM-5`,
  `pipeline_window_code: PW-6`, `followup_scope_code: FS-4`.

### D. Churn Model Validation & Outreach Ranking (MOD-7)
Output keys: `model_validation`, `risk_ranking`, `cohort_checks`, `model_policy_codes`.
- Train on `/exports/churn/train.csv` (180 rows, 19 features, label `Churn`), evaluate on
  `/exports/churn/validation.csv` (60 rows). Feature columns = the 19 fields after
  `customer_id` up to `ActiveSeatRatio` (exclude `customer_id` and `Churn`).
  - `training_rows: 180`, `validation_rows: 60`, `feature_count: 19`.
  - `accuracy_pct: 93.3` (1dp), `accuracy_band: "90_plus"`
    (bands: below_70 / 70_to_79 / 80_to_89 / 90_plus).
  - `tenure_coefficient_direction: "negative"` (higher tenure → lower churn probability).
- Predict churn probability for the prompted candidate `account_id`s from
  `/exports/churn/candidates.csv` (same 19 features; no `Churn` column).
- `risk_ranking`: top 5 by `predicted_churn_probability` **desc** (3 decimals), tie-break by
  `customer_id` asc. Each: `rank`, `customer_id`, `predicted_churn_probability`,
  `outreach_action`, `reason_code`.
- **Outreach mapping (OUT-2)** — first match:
  1. `InvoicePastDue == "Yes"` → action `collections_followup`, reason `overdue_receivable`.
  2. `Contract == "Month-to-month"` AND `tenure < 24` → action `renewal_save`, reason
     `low_tenure_high_churn`.
  3. otherwise → action `nurture_monitor`, reason `clean_billings`.
- `cohort_checks`:
  - `past_due_shortlist_count` = # of the **top-5** ranked candidates with
    `InvoicePastDue == "Yes"`.
  - `low_tenure_shortlist_count` = # of the top-5 with `tenure < 24`.
  - `average_probability_top5` = mean of the top-5 probabilities (3 decimals).
- `model_policy_codes`: `model_protocol_code: MOD-7`, `probability_scale_code: PRB-4`,
  `deployment_rule_code: DEP-5`, `outreach_mapping_code: OUT-2`.

### E. High-Touch Retention Operations Board — full set, all accounts
Output keys: `action_board` (all reviewed accounts, ordered by BORD-4), `segment_summary`,
`followup_calendar`, `policy_codes`. Each board row: `rank`, `account_id`, `risk_level`,
`primary_action`, `current_arr`, `expansion_pipeline`, `overdue_balance`,
`next_touch_due_date`, `reason_codes`.
- `current_arr` = posted billing snapshot `billing_arr` at assessment date (REV-4).
- `expansion_pipeline` = sum of the account's open opportunities (close_date in window).
- `overdue_balance` = 61_90 + 90_plus at as-of date.
- `next_touch_due_date` = CAL-5 date for the `primary_action` (`null` for `no_action`).
- `reason_codes` as in §4.3 (all triggered, canonical order).
- Order: risk_level desc, current_arr desc, account_id asc.
- `segment_summary`:
  - `strategic_accounts` = # reviewed accounts with `segment == "Strategic"`.
  - `enterprise_accounts` = # reviewed with `segment == "Enterprise"`.
  - `arr_at_risk` = sum of `current_arr` over reviewed accounts with `risk_level != low`
    (2dp).
  - `open_expansion_pipeline` = sum of `expansion_pipeline` over **all** reviewed accounts
    (2dp).
  - `net_revenue_exposure` = `arr_at_risk` − `open_expansion_pipeline` (2dp). (EXP-6 —
    segment-level; no overdue term.)
- `followup_calendar`: the five action→due-date mappings from the prompt (CAL-5).
- `policy_codes`: `risk_model_code: RS-6`, `arr_source_code: REV-4`,
  `support_hygiene_code: SUP-8`, `action_priority_code: ACT-5`, `board_sort_code: BORD-4`,
  `exposure_formula_code: EXP-6`, `calendar_policy_code: CAL-5`.

## 7. Reason-code canonical order (emit in this relative order)

`renewal_window`, `overdue_receivable`, `nps_drop`, `sla_degradation`, `usage_decline`,
`low_tenure_high_churn`, `expansion_offset`, `clean_billings`.

## 8. Quick checklist before returning JSON
- URL from ENV_URL.txt (not 127.0.0.1); region omitted for "all".
- currency 2dp, pct 1dp, counts/scores int, churn prob 3dp.
- `current_arr` from posted billing snapshot at assessment date.
- overdue = 61_90 + 90_plus only; clean_billings/overdue_receivable mutually exclusive.
- CRM link on exact legal_name only.
- pipeline by close_date in window; win_rate denominator = won+lost.
- reason codes in canonical order; risk level per §4.3; action per §5; ranking per §4.5.
- emit only the policy_codes block the template requests, with the exact §2 values.
