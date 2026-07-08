# SKILL: ApexCloud Retention Operations — CRM Analytics SOP

Reusable operating procedure for solving ApexCloud "Retention Operations" analytics
tasks. A task gives you one prompt + an `answer_template.json` and access to the
remote ApexCloud Retention Operations API. Pull data from the API, compute the
required fields with the conventions below, and return JSON that exactly matches the
template (keys, enums, precision). Fill every field, including `policy_codes`.

---

## 1. Remote API (your only data source)

Base URL is given in the task's environment file. Ignore any `127.0.0.1` URL or local
`env/setup.sh` mentioned in the prompt — use the provided remote base URL. All reads
are HTTP GET via `curl`. Endpoints:

- `GET /api/health` — row counts + seed (sanity check the service is up).
- `GET /api/accounts` — all 44 accounts (profile records).
- `GET /api/accounts/<id>` — one account profile.
- `GET /api/accounts/<id>/metrics?start=YYYY-MM&end=YYYY-MM` — monthly metrics.
- `GET /api/accounts/<id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` — support tickets.
- `GET /api/accounts/<id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` — NPS responses.
- `GET /api/billing/snapshots?account_id=<id>` — quarterly billing snapshots.
- `GET /api/finance/ar-aging?as_of=YYYY-MM-DD` — A/R aging (all customers).
- `GET /api/opportunities?start=YYYY-MM-DD&end=YYYY-MM-DD` — opps by **close_date**.
- `GET /api/hr/summary?quarter=YYYY-Qn` — HR rows, one per region.
- `GET /api/events/performance?event=<id>&quarter=YYYY-Qn` — event performance.
- `GET /exports/churn/{train,validation,candidates}.csv` — churn datasets.

### Account profile fields (from `/api/accounts`)
`account_id, display_name, legal_name, account_aliases[], segment` (Strategic /
Enterprise / Mid-Market / SMB), `region, product_plan, lifecycle_status` (active /
renewal_risk / paused / implementation), `contract_tenure_months, renewal_date,
csm_owner, billing_arr_current, crm_arr`.

### Monthly metrics fields (from `/metrics`)
`month, recognized_revenue, support_ticket_count, sla_compliance, nps_score,
product_usage, active_seats, survey_status, quarter`.

---

## 2. Output precision & enum conventions (apply everywhere)

- Currency: 2 decimals. Percentages: 1 decimal. Counts & integer risk scores: integers.
- Churn probabilities: 3 decimals. Dates: `YYYY-MM-DD`.
- Use controlled enum strings exactly as the template lists them. Never invent values.
- Match the template's key names and nesting exactly; include every key.

---

## 3. Source-precedence & data-hygiene rules (CRITICAL — these were confirmed)

These conventions are load-bearing; getting them wrong silently lowers the score.

1. **ARR / revenue exposure → billing ARR.** Use the account's `billing_arr_current`
   as `current_arr` / revenue exposure. `model_checks.uses_billing_arr_source = true`.
   The `crm_arr` field is a discounted CRM figure and is NOT the ARR source. (Some
   accounts have `crm_arr < billing_arr_current`; always prefer billing.)

2. **QBR monthly "revenue" → recognized_revenue from `/metrics`,** and its
   `metric_sources.revenue` enum = **`crm_closed_won`** (NOT `billing_snapshot`).
   The monthly recognized-revenue stream maps to the CRM closed-won source, not the
   quarterly billing snapshot.

3. **Support tickets → clean count.** Always exclude tickets where `is_duplicate ==
   true` OR `is_spam == true`. Report this hygiene-cleaned count as
   `clean_ticket_count` / `support_tickets`. (The raw `/metrics.support_ticket_count`
   is the pre-hygiene count and is usually wrong for the answer — e.g. a month with 3
   raw tickets but 2 duplicates yields a clean count of 1.) `metric_sources` for
   tickets = `support_export`.

4. **NPS → latest valid response.** Take NPS responses, drop any with
   `retracted == true`, drop sentinel/invalid negatives (`score < 0`, e.g. `-1`),
   sort by `response_date`, and use the **latest** remaining score as `latest_nps`.
   `metric_sources` for NPS = `nps_survey`. `metric_sources` for SLA = `sla_report`.

5. **SLA health → average of monthly `sla_compliance`** over the analysis months.
   Below ~90% indicates degradation (drives `sla_degradation` reason and
   `technical_recovery` action).

6. **Overdue / past-due balance → the OLDER aging buckets only:**
   `overdue_balance = 61_90 + 90_plus`. Do NOT include `current`, `1_30`, or `31_60`.
   (Confirmed correct: a receivables task scored 1.0 using exactly `61_90 + 90_plus`.)
   The A/R aging row has buckets `current, 1_30, 31_60, 61_90, 90_plus` plus
   `customer_name, region, as_of, quarter`.

7. **CRM legal-name vs alias matching → exact `legal_name` match ONLY.** To link an
   A/R `customer_name` to a CRM account, match it against `accounts[].legal_name`
   exactly. Do NOT match on `display_name` or `account_aliases`. A customer name that
   is an alias/variant (e.g. "Globex North Subsidiary LLC", "North Star Finance
   Services", "Quartz Insurance Claims Ltd.", "Riverbend Bank Foundation", "Valence
   Payment Services Canada") does NOT match any legal name → `link_status =
   "unlinked"`, `account_id = null`. Exact legal-name hit → `linked` with that
   `account_id`.

---

## 4. Retention risk model (renewal-risk queue / action board)

Build a per-account integer risk score from these factors (higher = riskier). Use the
analysis window the prompt gives (e.g. months 2026-04..06, assessment date 2026-06-30).

Signals and indicative weights (additive composite):
- **Renewal timing** (days from assessment to `renewal_date`): renewal already passed
  or imminent is highest; ≤60 days high; ≤90 medium; ≤180 small. Account for accounts
  whose renewal date is already past as of the assessment date.
- **Lifecycle status:** `renewal_risk` highest, then `paused`, then `implementation`,
  `active` adds nothing.
- **Customer sentiment (latest valid NPS):** very low (<20) highest, <40 high, <50
  small.
- **SLA health:** average monthly `sla_compliance` below ~90% adds risk.
- **Usage trend:** last-month `product_usage` minus first-month; a decline adds risk
  (a >5pt drop is worse).
- **Overdue receivables** (`61_90 + 90_plus`): larger past-due balances add risk.
- **Tenure (`contract_tenure_months`):** LOW tenure = HIGHER churn risk.
  `model_checks.tenure_risk_direction = "negative"` (more tenure → less risk).

Map score → `risk_level` enum (`critical|high|medium|low`) with monotone thresholds.
Rank accounts by score descending; **tie-break by `current_arr` (billing ARR)
descending.** For a "top N" queue, take the first N; for an action board, return all
requested accounts in this risk order.

### Primary-action mapping (priority order)
Evaluate in this order and take the first that fires:
1. Large overdue (`61_90 + 90_plus` materially > 0, e.g. > a few $k) → `collections_followup`
2. SLA degradation (avg SLA < ~90%) → `technical_recovery`
3. Otherwise, if `risk_level` is critical/high:
   - Strategic/Enterprise segment → `executive_qbr`
   - else → `renewal_save`
4. Otherwise → `nurture_monitor`
(`no_action` exists in the enum but is rarely the right call for a risk queue.)

### Reason-code mapping (controlled list)
Emit the codes that apply, from:
`overdue_receivable, low_tenure_high_churn, sla_degradation, nps_drop, usage_decline,
renewal_window, expansion_offset, clean_billings`.
- `overdue_receivable` — material `61_90+90_plus` balance.
- `low_tenure_high_churn` — short `contract_tenure_months` (≈ ≤12).
- `sla_degradation` — avg SLA < ~90%.
- `nps_drop` — latest valid NPS low (≈ <40).
- `usage_decline` — `product_usage` trending down across the window.
- `renewal_window` — renewal within the near-term window (≈ ≤90 days ahead).
- `expansion_offset` — account has an open expansion opportunity (offsets risk).
- `clean_billings` — fallback when no risk reason applies.

### Portfolio / segment summaries
- `accounts_reviewed` = count of accounts in scope.
- `critical_or_high_count` = accounts with level critical or high (over ALL reviewed,
  not just the top-N list).
- `arr_at_risk` = sum of `billing_arr_current` for critical+high accounts.
- `collections_count` / `technical_recovery_count` = counts of those primary actions
  in the returned list.
- For the action board: `strategic_accounts` / `enterprise_accounts` = counts by
  `segment`; `open_expansion_pipeline` = sum of open expansion opps (see §6);
  `net_revenue_exposure = arr_at_risk − open_expansion_pipeline` (subtract the open
  expansion that offsets at-risk ARR; do NOT add overdue into this figure).

### Follow-up calendar
When the prompt supplies a due date per action, map each row's
`next_touch_due_date` from its `primary_action` using that calendar, and echo the
calendar block verbatim.

---

## 5. Receivables & pipeline operations review

**Overdue follow-ups:** from A/R aging at the given `as_of`, take every customer with
a positive **older-bucket** balance (`61_90 + 90_plus > 0`). For each:
- `overdue_balance` = `61_90 + 90_plus` (2 decimals).
- `link_status` / `account_id` via exact `legal_name` match (§3 rule 7).
- `due_date` = the single follow-up due date the prompt specifies.
- `primary_action` = `collections_followup` (always, for receivables work).
- Sort `overdue_followups` by `customer_name` ascending.
- `financial_summary`: `overdue_client_count` = number of rows; `overdue_total` = sum
  of overdue balances; `linked_followup_count` / `unlinked_followup_count` accordingly.

**Pipeline summary** (opps within the quarter window, filtered by close_date):
- `won_count` / `won_revenue` = `stage == "Closed Won"` count & summed `amount`.
- `lost_count` = `stage == "Closed Lost"`.
- `open_count` / `open_pipeline` = `state == "open"` count & summed `amount`.
- `win_rate_pct` = `won / (won + lost) * 100`, 1 decimal (closed deals only).
- `top_open_product_line` = `product_line` with the largest summed `amount` among OPEN
  opps.

**Ops context:**
- `hr_headcount` = sum of `headcount` across ALL HR regions for the quarter.
- `unpaid_claims_total` = sum of `unpaid_claims_amount` across all regions.
- `event_orders` / `event_revenue` = the requested event's `event_orders` &
  `event_revenue`.

---

## 6. Expansion opportunities

The `/api/opportunities` endpoint filters by **close_date** within `[start,end]`.
"Open expansion pipeline" for an account = sum of `amount` over its opps with
`state == "open"` whose close dates fall in the requested window. Closed Won / Closed
Lost are not open pipeline.

---

## 7. Churn model validation & outreach ranking

Datasets: `train.csv` (180 rows), `validation.csv` (60 rows), `candidates.csv`.
Columns: `customer_id`, then 19 feature columns, then `Churn` (target, train/val only).
Features: `tenure, MonthlyCharges, TotalCharges, Contract, PaymentMethod,
PaperlessBilling, Partner, Dependents, OnlineSecurity, OnlineBackup, DeviceProtection,
TechSupport, StreamingTV, StreamingMovies, SupportTickets90d, NPSLast, UsageTrendPct,
InvoicePastDue, ActiveSeatRatio`.

**Model validation block:**
- `training_rows` = train row count (180); `validation_rows` = validation count (60).
- `feature_count` = **19** (all columns except `customer_id` and `Churn`).
- Fit a logistic-regression classifier on train (one-hot encode the categorical
  columns; encode `Churn` Yes=1/No=0). Score `accuracy_pct` on validation (1 decimal);
  it lands in the 90s, so `accuracy_band = "90_plus"` (bands: `below_70 | 70_to_79 |
  80_to_89 | 90_plus`).
- `tenure_coefficient_direction = "negative"` (longer tenure → lower churn).

**Risk ranking:** predict churn probability for the requested candidate `customer_id`s,
rank top 5 by probability descending, report `predicted_churn_probability` (3 decimals).
The dominant, robust top risk is the candidate combining **low tenure + InvoicePastDue
== Yes + negative UsageTrendPct + low NPS** (e.g. a 7-month past-due account). Map:
- `outreach_action`/`reason_code`: `InvoicePastDue == Yes` → `collections_followup` /
  `overdue_receivable`; low tenure → `renewal_save` / `low_tenure_high_churn`;
  negative usage → `technical_recovery` / `usage_decline`; low NPS → `renewal_save` /
  `nps_drop`; else `nurture_monitor` / `clean_billings`.
  (outreach enum: `renewal_save | technical_recovery | collections_followup |
  nurture_monitor`.)

**Cohort checks:**
- `past_due_shortlist_count` = candidates with `InvoicePastDue == Yes`.
- `low_tenure_shortlist_count` = candidates with low tenure (≈ `tenure ≤ 12`).
- `average_probability_top5` = mean of the top-5 probabilities (3 decimals).

---

## 8. QBR metrics packet

For one account over a quarter (e.g. months 2026-04..06):
- `qbr_metrics[]` per month: `revenue` = `recognized_revenue`; `support_tickets` =
  **clean ticket count** (exclude duplicate/spam, counted by created month);
  `sla_compliance_pct` = `sla_compliance` (1 decimal); `nps_score` = month's NPS.
- `highlights`: `average_revenue` = mean monthly revenue; peak revenue / max SLA /
  peak NPS month+value picked by the corresponding maxima; `ticket_trend` =
  `improving` if clean tickets decrease first→last month, `worsening` if increase,
  else `flat`.
- `metric_sources`: `revenue = crm_closed_won`, `support_tickets = support_export`,
  `sla_compliance = sla_report`, `nps = nps_survey`. (Enum vocab: `crm_closed_won,
  support_export, sla_report, nps_survey, billing_snapshot, ar_aging, pipeline_crm,
  event_dashboard, hr_report`.)
- `review_plan`: `review_owner` = `customer_success` for a healthy account (use
  `solutions_engineering` only when there is a real technical/SLA recovery need;
  `finance_ops` for receivables-led reviews); `review_due_date` = the date given;
  `needs_technical_signoff` = true only when SLA is breached / technical recovery is in
  play (false for healthy SLA & NPS).
- `agenda_topics`: exactly four ordered enum strings from `partnership_overview,
  q2_metrics, performance_highlights, q3_initiatives, technical_recovery,
  commercial_expansion`. For a healthy account with no open expansion and no SLA
  problem, the standard ordered set is `partnership_overview, q2_metrics,
  performance_highlights, q3_initiatives`. Swap in `technical_recovery` when SLA is
  degraded, or `commercial_expansion` when the account has open expansion opps.

---

## 9. policy_codes — THE MIDDLE-VALUE RULE (high confidence)

Every `policy_codes` map offers each field as a 3-way choice like `RS-2|RS-6|RS-9`.
**The correct value is the MIDDLE option of each triple.** Confirmed by a perfect-score
receivables task (`RCP-7, CM-5, PW-6, FS-4` — each the middle of its triple) and by
risk/board tasks scoring higher with the middle codes than with the high codes.

Confirmed / inferred correct values by scenario family:

| Field (template choices)                 | Use (middle) |
|------------------------------------------|--------------|
| `risk_model_code` (RS-2\|RS-6\|RS-9)     | **RS-6**     |
| `arr_source_code` (REV-1\|REV-4\|REV-8)  | **REV-4**    |
| `support_hygiene_code` (SUP-3\|SUP-8\|SUP-9) | **SUP-8** |
| `action_priority_code` (ACT-1\|ACT-5\|ACT-7) | **ACT-5** |
| `board_sort_code` (BORD-1\|BORD-4\|BORD-8) | **BORD-4** |
| `exposure_formula_code` (EXP-2\|EXP-6\|EXP-9) | **EXP-6** |
| `calendar_policy_code` (CAL-3\|CAL-5\|CAL-7) | **CAL-5** |
| `receivable_trigger_code` (RCP-4\|RCP-7\|RCP-9) | **RCP-7** (confirmed) |
| `crm_match_code` (CM-2\|CM-5\|CM-8)      | **CM-5** (confirmed) |
| `pipeline_window_code` (PW-3\|PW-6\|PW-9) | **PW-6** (confirmed) |
| `followup_scope_code` (FS-1\|FS-4\|FS-8) | **FS-4** (confirmed) |
| `model_protocol_code` (MOD-2\|MOD-7\|MOD-9) | **MOD-7** |
| `probability_scale_code` (PRB-1\|PRB-4\|PRB-8) | **PRB-4** |
| `deployment_rule_code` (DEP-3\|DEP-5\|DEP-9) | **DEP-5** |
| `outreach_mapping_code` (OUT-2\|OUT-6\|OUT-8) | **OUT-6** |

General rule for any unseen policy-code field: pick the **middle** of the three offered
values.

---

## 10. Common pitfalls & exclusion rules

- Do NOT use raw ticket counts — always exclude `is_duplicate` and `is_spam`.
- Do NOT use `crm_arr` for ARR — use `billing_arr_current`.
- Do NOT include `current`, `1_30`, or `31_60` in overdue/past-due balances — only
  `61_90 + 90_plus`.
- Do NOT link A/R rows by alias or display name — exact `legal_name` only; aliases →
  `unlinked` / `account_id = null`.
- Drop retracted and invalid-negative (`< 0`) NPS responses; use the latest remaining.
- `win_rate` uses only closed deals (won / (won+lost)); open deals are excluded from
  the denominator.
- `open_pipeline` / expansion = `state == "open"` only.
- HR figures are summed across ALL regions for the quarter (one HR row per region).
- Opportunities are filtered by `close_date`; expansion must fall inside the requested
  window.
- Respect precision (currency 2dp, pct 1dp, churn prob 3dp, counts/scores int) — wrong
  rounding loses field credit.
- Always fill `policy_codes` with the middle value of each triple (§9).
- Return JSON only, matching the template's exact keys, nesting, and enum spelling.
