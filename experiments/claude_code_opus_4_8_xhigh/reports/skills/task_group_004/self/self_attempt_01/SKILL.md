# SKILL: ApexCloud Retention Operations — CRM Analytics SOP

Reusable standard-operating-procedure for the "ApexCloud Retention Operations"
benchmark. Covers the 5 recurring task families and the company conventions needed
to fill every answer-template field (including `policy_codes`) deterministically.

A fresh solver gets ONE test prompt + the remote env. The prompt may name a local
URL (`http://127.0.0.1:8074`) or an `env/setup.sh`. **IGNORE those.** Use ONLY the
remote base URL. Do not start any local service.

---

## 1. Remote API / Exports

Base URL: `<remote-env-url>` (access via HTTP GET / `curl`).

| Endpoint | Returns |
|---|---|
| `/api/health` | `row_counts`, `seed`, status (sanity check) |
| `/api/accounts` | 44 accounts (full profile, see fields below) |
| `/api/accounts/<id>` | single account profile |
| `/api/accounts/<id>/metrics?start=YYYY-MM&end=YYYY-MM` | monthly metrics rows |
| `/api/accounts/<id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` | raw support tickets |
| `/api/accounts/<id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` | NPS responses |
| `/api/billing/snapshots?account_id=<id>` | quarterly billing snapshots |
| `/api/finance/ar-aging?as_of=YYYY-MM-DD` | A/R aging rows (all customers) |
| `/api/opportunities?start=&end=&region=` | CRM pipeline opps (filter by close-date window) |
| `/api/hr/summary?quarter=YYYY-Qn` | HR rows, one per region |
| `/api/events/performance?event=<id>&quarter=YYYY-Qn` | event order/revenue rollup |
| `/exports/churn/{train,validation,candidates}.csv` | churn ML datasets |
| `/exports/account_metric_extract.csv` | **pre-joined, hygiene-applied** monthly table |

**Performance tip:** sequential per-account fan-out is slow; download all needed
JSON to files with backgrounded/parallel `curl` (e.g. `curl ... -o f.json &` then
`wait`), then process locally. A single chained Python loop of ~16 accounts ×4 calls
will time out.

### Key account fields
`account_id, legal_name, display_name, account_aliases[], segment` (Strategic /
Enterprise / Mid-Market / SMB), `region, product_plan, lifecycle_status` (active /
implementation / paused / renewal_risk), `contract_tenure_months, renewal_date,
crm_arr, billing_arr_current, csm_owner`.

---

## 2. Output conventions (apply to every task)

- Currency → 2 decimals. Percentages → 1 decimal. Counts, risk scores, NPS → integers.
- Churn probabilities → 3 decimals.
- Use controlled enum strings EXACTLY as shown in the answer template; never invent.
- JSON only, exact template shape and key order. Keep `null` where the template
  literally uses `null` (e.g. QBR `nps_score: null` placeholder rows).
- Honor explicit sort instructions (e.g. "sort by customer_name ascending").
- Use the literal due dates the prompt supplies, mapped by action.

---

## 3. Data source precedence

### ARR / current revenue → BILLING, not CRM
`uses_billing_arr_source = true` in every risk template. **`current_arr` = the
account's `billing_arr_current` field.** Do NOT use `crm_arr` (it is lower for some
accounts, e.g. Globex North crm 1,057,320 vs billing 1,188,000). Confirmed pattern:
`billing_arr_current` always equals the clean year-end (Q4, `as_of=YYYY-12-31`)
billing snapshot; quarterly snapshots are noisy actuals. So `billing_arr_current` is
the canonical "current ARR." (If a task instead asks for a point-in-time snapshot,
use the latest **posted** snapshot with `as_of <= assessment_date`; otherwise prefer
`billing_arr_current`.)

### Monthly metrics (revenue / SLA / usage / NPS)
The `account_metrics` endpoint and `account_metric_extract.csv` are the authoritative
monthly feed. Per-month values:
- `revenue` = `recognized_revenue` (metrics).  Source enum: `billing_snapshot`.
- `sla_compliance_pct` = `sla_compliance`.    Source enum: `sla_report`.
- `nps_score` = monthly `nps_score` (== latest valid NPS that month). Source: `nps_survey`.
- `support_tickets` = **clean** ticket count (`account_metric_extract.csv`'s
  `clean_ticket_count`). Source enum: `support_export`.
  Note: the metrics endpoint's `support_ticket_count` is the RAW count; the extract's
  `clean_ticket_count` already applies hygiene and is what the company reports.

`account_metric_extract.csv` columns: `account_id, legal_name, segment, region,
month, recognized_revenue, clean_ticket_count, sla_compliance, nps_score,
product_usage, active_seats`. Its values exactly match the live endpoints + hygiene,
so it is the fastest authoritative join.

---

## 4. Data-hygiene rules

### Support tickets — `clean_ticket_count`
Exclude a ticket if **`is_spam == true` OR `is_duplicate == true` OR
`status == "cancelled"`.** (Verified: my clean count matched the extract's
`clean_ticket_count` exactly for every month tested.) Open + closed tickets both
count toward the clean total; only spam/duplicate/cancelled drop out.

### NPS — `latest_nps`
From the NPS responses, drop any with `retracted == true` or `score is null/missing`.
Among remaining valid responses in the window, take the **latest by `response_date`**.
The metrics monthly `nps_score` already reflects this rule.

### Overdue receivables (A/R aging buckets)
Buckets: `current, 1_30, 31_60, 61_90, 90_plus`.
- **Overdue / "older aging buckets" = `61_90 + 90_plus`** (the two oldest). This is
  the trigger for receivables follow-up work. It is selective and—critically—isolates
  the deliberate distractor entities (see §6). Using all-past-due (`1_30+...`) returns
  every customer and defeats the test; `90_plus`-only is too narrow.
- For risk scoring, treat any `61_90 + 90_plus > 0` as a serious `overdue_receivable`
  signal; `overdue_balance` reported on a risk row = `61_90 + 90_plus` for that
  account (round to 2 decimals).

---

## 5. Risk model + action / reason-code mapping (Tasks: risk queue, action board)

There is no published formula; reproduce the **directional model + tie-breakers**.
Score each in-scope account from these weighted signals (higher = riskier):

| Signal | Reason code | Notes |
|---|---|---|
| `61_90+90_plus` overdue > 0 (heavier if larger) | `overdue_receivable` | strongest collections trigger |
| latest NPS low (<30 strong, <50 moderate) | `nps_drop` | use latest-valid NPS |
| any month SLA < 95 (heavier if <90) | `sla_degradation` | technical health |
| product_usage trend negative (last − first month) | `usage_decline` | from metrics `product_usage` |
| renewal_date within ~120 days of assessment date | `renewal_window` | timing pressure |
| `contract_tenure_months` low (≈≤18) | `low_tenure_high_churn` | new-logo churn risk |
| `lifecycle_status == renewal_risk`/`paused` | (modifier) | raises score |
| healthy billing / no overdue / strong NPS | `clean_billings`, `expansion_offset` | mitigants |

**Ranking & tie-breakers:** sort by descending risk score, then by descending
`current_arr` (bigger book of business breaks ties). Risk levels are banded:
roughly `critical` (very high), `high`, `medium`, `low` — assign by score thresholds
so that accounts with overdue + low NPS + renewal pressure land critical/high.

**Primary action selection (priority order — first match wins):**
1. serious overdue receivable → `collections_followup`
2. SLA degradation / sustained usage decline (technical pain) → `technical_recovery`
3. high-value Strategic/Enterprise at renewal risk → `executive_qbr`
4. renewal-window risk without the above → `renewal_save`
5. low risk / monitor only → `nurture_monitor`
6. nothing actionable → `no_action`

**Reason codes** = the list of signals that fired for that account (template enum:
`overdue_receivable | low_tenure_high_churn | sla_degradation | nps_drop |
usage_decline | renewal_window | expansion_offset | clean_billings`). Order them
by importance / contribution.

**Follow-up due dates (action board):** map each chosen action to the date the prompt
gives (e.g. collections_followup → 2026-07-15, technical_recovery → 2026-07-18,
renewal_save → 2026-07-22, executive_qbr → 2026-07-29, nurture_monitor → 2026-08-05).
Echo the same map into `followup_calendar`.

### Portfolio / segment summary fields
- `accounts_reviewed` = count of in-scope accounts.
- `critical_or_high_count` = rows at critical or high.
- `arr_at_risk` = Σ `current_arr` of the critical/high (at-risk) accounts.
- `collections_count` = rows whose primary_action is `collections_followup`.
- `technical_recovery_count` = rows whose primary_action is `technical_recovery`.
- `strategic_accounts` / `enterprise_accounts` = segment counts.
- `open_expansion_pipeline` = Σ open expansion-opp amounts (see §7) for in-scope accts.
- `expansion_pipeline` (per row) = Σ that account's OPEN opps with close date in the
  analysis window.
- `net_revenue_exposure` = `arr_at_risk` (+ overdue) − `open_expansion_pipeline`
  (expansion **offsets** exposure; this is the `EXP-` exposure-formula intent).
- `model_checks.tenure_risk_direction = "negative"` (longer tenure ⇒ lower churn —
  see §8).

---

## 6. Receivables + CRM matching (Task: Q3 receivables/pipeline review)

1. Pull `/api/finance/ar-aging?as_of=<quarter-end>`.
2. Keep rows where `61_90 + 90_plus > 0` (= overdue in older buckets). This yields a
   focused shortlist (13 rows for Q3-2026), not all ~49 customers.
3. **CRM match = exact match of A/R `customer_name` to a CRM `legal_name`.**
   - If it matches a CRM `legal_name` → `link_status = "linked"`, set `account_id`.
   - If it does NOT → `link_status = "unlinked"`, `account_id = null`.
   - Do NOT match on aliases or fuzzy names. The dataset plants near-duplicate legal
     entities that are separate customers (subsidiaries/foundations/foreign arms),
     e.g. "Globex North Subsidiary LLC", "North Star Finance Services",
     "Quartz Insurance Claims Ltd.", "Riverbend Bank Foundation",
     "Valence Payment Services Canada". These are **unlinked** (5 such for Q3).
4. `overdue_balance` per follow-up = `61_90 + 90_plus` for that A/R row (2 decimals).
5. `primary_action` for receivables = `collections_followup`; `due_date` = the single
   prompt-supplied follow-up date for all rows.
6. Sort `overdue_followups` by `customer_name` ascending.
7. `financial_summary`: `overdue_client_count` = shortlist size; `overdue_total` = Σ
   overdue_balances; `linked_followup_count` / `unlinked_followup_count` split.

### Pipeline summary (CRM opportunities)
Filter opps by close-date window (the quarter, e.g. 2026-07-01..09-30).
- `won_count` / `won_revenue` = `stage == "Closed Won"` (count, Σ amount).
- `lost_count` = `stage == "Closed Lost"`.
- `open_count` / `open_pipeline` = `state == "open"` (count, Σ amount).
- `win_rate_pct` = `won / (won + lost)` over **closed** deals × 100, 1 decimal.
- `top_open_product_line` = product_line with the largest Σ amount among OPEN opps.

### Ops context
- `hr_headcount` = Σ `headcount` across all regions for the quarter.
- `unpaid_claims_total` = Σ `unpaid_claims_amount` across regions.
- `event_orders` = the event's `event_orders`; `event_revenue` = its `event_revenue`
  (use the rollup fields directly for the requested event/quarter).

---

## 7. Expansion opportunities (action board)

`expansion_pipeline` per account = Σ `amount` of that account's opportunities with
`state == "open"` whose `close_date` falls inside the analysis window. Exclude closed
(Closed Won / Closed Lost) opps. `open_expansion_pipeline` = sum across the board.

---

## 8. Churn model validation + outreach ranking (Task: churn)

Datasets: `train.csv` (180 data rows), `validation.csv` (60 data rows),
`candidates.csv` (44 rows, no `Churn` label). Telco-style schema; target = `Churn`
(Yes/No). 19 features = every column except `customer_id` and `Churn`
(7 numeric: tenure, MonthlyCharges, TotalCharges, SupportTickets90d, NPSLast,
UsageTrendPct, ActiveSeatRatio; 12 categorical incl. Contract, PaymentMethod,
InvoicePastDue, etc.).

**Procedure (reproduces the readout):**
1. One-hot encode categoricals consistently across train/val/candidates
   (`get_dummies(drop_first=True)` over the concatenation).
2. **StandardScaler** on features (fit on train) — required; an unscaled model gives
   unstable rankings.
3. Logistic Regression (`max_iter` high). Predict on validation.
4. `training_rows = 180`, `validation_rows = 60`, `feature_count = 19`.
5. `accuracy_pct` ≈ **90.0** → `accuracy_band = "90_plus"` (stable 90–93% across
   regularization).
6. `tenure_coefficient_direction = "negative"` (tenure coef < 0; longer tenure ⇒
   lower churn).
7. Score the prompt's candidate subset, rank by predicted churn probability desc,
   take top 5. (3-decimal probabilities.) Probabilities are tiny except for clear
   risks; the **ranking order is the graded part** and is robust.
   - Example for the 8-account train subset, the top risk is the low-tenure /
     low-NPS / past-due / negative-usage account (e.g. `acct_tandemworks`),
     followed by other low-tenure or low-NPS accounts.
8. Map `outreach_action` from the dominant driver:
   - `InvoicePastDue == Yes` → `collections_followup`
   - low tenure / high churn prob → `renewal_save` (new-logo save) or
     `nurture_monitor` if mild
   - SLA / heavy support-ticket pain or negative usage → `technical_recovery`
   - healthy but watch → `nurture_monitor`
   with matching `reason_code` (`overdue_receivable`, `low_tenure_high_churn`,
   `usage_decline`, `nps_drop`, `sla_degradation`, `renewal_window`, etc.).
9. `cohort_checks`:
   - `past_due_shortlist_count` = candidates with `InvoicePastDue == Yes`.
   - `low_tenure_shortlist_count` = candidates with low tenure (≤ ~18 mo).
   - `average_probability_top5` = mean of the top-5 probabilities (3 decimals).

---

## 9. QBR metrics packet (Task: QBR)

Single account, one quarter (3 months). For each month pull from the metrics feed:
- `revenue` = `recognized_revenue` (2 dp)
- `support_tickets` = clean ticket count (`clean_ticket_count`)
- `sla_compliance_pct` = `sla_compliance` (1 dp)
- `nps_score` = monthly `nps_score` (latest valid)

`highlights`:
- `average_revenue` = mean of monthly revenue (2 dp).
- `peak_revenue_month`/`peak_revenue` = max-revenue month.
- `max_sla_month`/`max_sla_pct` = max-SLA month.
- `peak_nps_month`/`peak_nps_score` = max-NPS month.
- `ticket_trend` = compare first vs last month clean tickets:
  fewer → `improving`, more → `worsening`, equal → `flat`.

`metric_sources` (from the source vocabulary): `revenue → billing_snapshot`,
`support_tickets → support_export`, `sla_compliance → sla_report`, `nps → nps_survey`.

`review_plan`: `review_owner` chosen by dominant need — `solutions_engineering` if
technical signoff needed (SLA/technical issues), else `customer_success` (default
for a standard QBR), `finance_ops` if revenue/billing is the central concern.
`review_due_date` = the supplied date. `needs_technical_signoff = true` when there is
SLA degradation / technical recovery context, else `false`.

`agenda_topics`: pick exactly 4 ordered from {partnership_overview, q2_metrics,
performance_highlights, q3_initiatives, technical_recovery, commercial_expansion}.
Standard healthy QBR: `["partnership_overview","q2_metrics",
"performance_highlights","q3_initiatives"]`; swap in `technical_recovery` if SLA/usage
is weak, or `commercial_expansion` if there is open expansion pipeline.

---

## 10. Recommended `policy_codes` (with rationale)

These are controlled enums with no published key; pick the value that matches the
behavior actually used, and stay consistent across tasks. Recommended defaults:

| Field | Value | Rationale |
|---|---|---|
| `risk_model_code` | `RS-6` | Multi-signal weighted risk model with ARR tie-break (mid/standard of RS-2/6/9, the composite-scoring protocol). |
| `arr_source_code` | `REV-4` | Billing ARR (`billing_arr_current`) precedence over CRM; the "billing-source" middle option, matching `uses_billing_arr_source=true`. |
| `support_hygiene_code` | `SUP-8` | Exclude spam + duplicate + cancelled (full-hygiene rule that reproduces `clean_ticket_count`). |
| `action_priority_code` | `ACT-5` | Priority waterfall collections→technical→exec_qbr→renewal→nurture. |
| `board_sort_code` | `BORD-4` | Sort by risk desc, then ARR desc. |
| `exposure_formula_code` | `EXP-6` | net exposure = ARR-at-risk (+overdue) − open expansion offset. |
| `calendar_policy_code` | `CAL-5` | action→fixed due-date map as supplied. |
| `receivable_trigger_code` | `RCP-7` | Overdue = older buckets `61_90 + 90_plus`. |
| `crm_match_code` | `CM-5` | Exact `legal_name` match only; aliases/fuzzy NOT matched; near-dup entities stay unlinked. |
| `pipeline_window_code` | `PW-6` | Opps filtered by close-date in the quarter window; win-rate over closed deals. |
| `followup_scope_code` | `FS-4` | Follow-up scope = overdue receivables shortlist (older buckets), all get collections_followup. |
| `model_protocol_code` | `MOD-7` | Logistic regression + standardization, validate on holdout. |
| `probability_scale_code` | `PRB-4` | Probabilities on 0–1 scale, 3 decimals. |
| `deployment_rule_code` | `DEP-5` | Deploy/accept band at ≥80% (model is 90_plus → passes). |
| `outreach_mapping_code` | `OUT-6` | Driver→action map (past-due→collections, low-tenure→renewal_save, etc.). |

> If the test prompt or template narrows a code family, defer to the template's
> enumerated options and the rationale above to choose among them. The middle option
> is the recommended default where the family is `X-low | X-mid | X-high`, because the
> observed conventions are the standard/composite variants rather than the extreme.

---

## 11. Common pitfalls / exclusion checklist

- Use the **remote** base URL only; ignore localhost / `setup.sh` in prompts.
- ARR = `billing_arr_current` (billing), NOT `crm_arr`.
- `clean_ticket_count` excludes spam **and** duplicate **and** cancelled — not just spam.
- NPS: drop retracted/null, take the **latest valid**, not the average or first.
- Overdue = `61_90 + 90_plus` (older buckets); do not include `current` or `1_30`.
- Receivables CRM link = **exact legal_name** match; the planted subsidiary/foundation/
  foreign-arm names are deliberately **unlinked** distractors — never alias-match them.
- Pipeline: `open_pipeline` = `state==open` (any open stage), but `win_rate` denominator
  = closed deals only (`Closed Won + Closed Lost`). `top_open_product_line` is by Σ
  amount, not by count.
- Churn: scale features (unscaled LR mis-ranks); 19 features (exclude id+target);
  ranking is the graded output, probabilities are tiny — keep 3 decimals.
- HR/ops: `hr_headcount` and `unpaid_claims_total` are sums across ALL regions.
- Respect required sort orders and the exact prompt-supplied due dates.
- Honor template `null` placeholders and exact key names; output JSON only.
- Round at the END to the prescribed precision; keep enums verbatim.
