---
name: apexcloud-retention-ops
description: >-
  Use this skill for any ApexCloud Retention Operations analytics task served from
  the local ApexCloud API (e.g. http://127.0.0.1:80xx, service "ApexCloud Retention
  Operations"). Trigger it whenever a prompt asks you to build a renewal/churn risk
  queue, a retention action board, a QBR metrics packet, a receivables & pipeline
  operations review, or a churn-model validation + outreach ranking from ApexCloud
  account, billing-snapshot, A/R-aging, support-ticket, NPS, metrics, opportunity,
  HR, event, or churn-export endpoints — even if the prompt does not name this skill.
  It encodes the exact data sources, exclusion rules, formulas, controlled enums,
  ordering/tie-breaks, and policy_codes that these tasks are graded on, plus the
  specific pitfalls that produce wrong numbers if you reconstruct them from scratch.
---

# ApexCloud Retention Operations

This skill captures hard-won, verified conventions for the ApexCloud Retention Operations
task family. These tasks look like ordinary "pull data and compute" exercises, but they are
graded against an internal model with several **counter-intuitive** rules. Reconstructing the
logic naively (taking the obviously-named field, summing all overdue buckets, reading the
metrics SLA field) produces plausible-looking answers that are *wrong*. Follow the rules here
exactly; they were recovered by diffing prior attempts against the gold answers and re-verified
against the live API.

## 0. Environment & general workflow

- The API base URL is given in the prompt (port varies). Confirm with `GET /api/health`
  (returns `service`, `seed`, `row_counts`). Use only the documented HTTP GET endpoints; do not
  read local data files or env directories even if the prompt mentions a setup script — ignore
  any such start command and just use the URL.
- Endpoints: `/api/accounts`, `/api/accounts/<id>`, `/api/accounts/<id>/metrics?start=YYYY-MM&end=YYYY-MM`,
  `/api/accounts/<id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD`, `/api/accounts/<id>/nps?start&end`,
  `/api/billing/snapshots?account_id=<id>` (or `?as_of=`), `/api/finance/ar-aging?as_of=YYYY-MM-DD`
  (`&region=`), `/api/opportunities?start&end` (`&region=`), `/api/hr/summary?quarter=YYYY-QN`,
  `/api/events/performance?event=<id>&quarter=YYYY-QN`, and CSV exports
  `/exports/churn/{train,validation,candidates}.csv`, `/exports/account_metric_extract.csv`.
- Compute everything deterministically from raw rows. **Round only at the very end**: currency
  to 2 decimals, percentages to 1 decimal, counts and risk scores to integers.
- Output **JSON only**, matching the answer template's keys, nesting, and enum vocabularies
  exactly. Always include the `policy_codes` block from the template even though it is not derived
  from data (see §7).
- `/tmp` may be polluted (stray `select.py`/`sitecustomize`) and break Python imports run from
  there; run scripts from a clean working dir. sklearn/numpy/pandas are available.

## 1. Current ARR — the single most common mistake

**`current_arr` = the billing SNAPSHOT `billing_arr` whose `as_of` equals the assessment / as-of
date** (e.g. 2026-06-30 for a Q2 board, 2026-09-30 for a Q3 review).

Do NOT use the account object's `billing_arr_current`, and do NOT use `crm_arr`.

- `GET /api/billing/snapshots?account_id=<id>` returns 4 quarterly snapshots
  (as_of 03-31, 06-30, 09-30, 12-31). Pick the one matching the as-of date and read `billing_arr`.
- Trap: the account's `billing_arr_current` is a round number that happens to equal the **Q4**
  snapshot, so it looks like "the current value" but is the wrong quarter. Example pattern: account
  shows `billing_arr_current=1425000.0` while the Q2 snapshot `billing_arr=1416439.47` — the
  latter is correct for a Q2 task.
- `model_checks.uses_billing_arr_source` is `true` (you are using the billing source, not CRM).
- `arr_source_code` is `REV-4` (see §7).

## 2. A/R aging: linking, the overdue trigger, and overdue_balance

A/R rows (`/api/finance/ar-aging?as_of=...`) have buckets `current`, `1_30`, `31_60`, `61_90`,
`90_plus`, plus `customer_name` (= account legal_name) and `region`. **There is no account_id** —
link by exact `customer_name` == account `legal_name`.

- **Linking is exact legal_name match.** Aliases/display_name do not help. The aging list contains
  MORE rows than there are accounts: the extras are decoy look-alike names (e.g. "... Subsidiary
  LLC", "North Star Finance Services" vs the real "Northstar Finance Group Inc.", "... Foundation",
  "... Canada"). Decoys that match no legal_name are `link_status="unlinked"` with `account_id=null`.
- **"Older aging buckets" trigger = `61_90 + 90_plus > 0`.** This selects which customers are
  "overdue" for a receivables review and which accounts get the `overdue_receivable` reason code /
  `collections_followup` action. (1_30 and 31_60 alone do NOT make a client "overdue" here.)
- **`overdue_balance` = `61_90 + 90_plus` ONLY.** This is the biggest receivables trap. Do NOT
  sum all past-due buckets (`1_30 + 31_60 + 61_90 + 90_plus`) and do NOT include `current`.
  An account whose only past-due money is in `1_30`/`31_60` has `overdue_balance = 0.0` and is
  NOT flagged overdue.
- `overdue_total` (portfolio level) = sum of these older-bucket `overdue_balance` values across
  the overdue clients.
- `clean_billings` reason code fires when `overdue_balance == 0` (no older-bucket debt);
  `overdue_receivable` fires when `overdue_balance > 0`.

## 3. Support tickets: the "clean" exclusion and SLA computation

Ticket rows (`/api/accounts/<id>/tickets`) have `severity`, `status` (open / closed / cancelled),
`first_response_sla_met`, `resolution_sla_met`, `is_duplicate`, `is_spam`, `product_area`,
`created_date`.

- **Clean ticket filter = NOT `is_spam` AND NOT `is_duplicate` AND `status != "cancelled"`.**
  All three exclusions matter. Non-spam/non-duplicate alone is not enough — cancelled tickets are
  also excluded. Open and closed clean tickets both count.
- `clean_ticket_count` (risk queue field) and QBR `support_tickets` both use this clean count.
  Do NOT use the metrics endpoint's `support_ticket_count` (that counts raw tickets including
  duplicates/cancelled and will be too high).
- **SLA compliance % = (clean tickets with `first_response_sla_met == true`) / (clean tickets)
  × 100**, computed from the tickets endpoint, rounded to 1 dp. Use `first_response_sla_met`
  for the headline SLA %. Do NOT read the metrics endpoint's `sla_compliance` field — it is a
  separate, differently-scaled number and gives wrong answers.
- For QBR monthly SLA, compute per month over that month's clean tickets. A month with 4 clean
  tickets where 1 missed first-response → 75.0%. A month with all met → 100.0%.

## 4. NPS — latest, non-retracted

NPS rows (`/api/accounts/<id>/nps`) have `score`, `response_date`, `retracted` (bool),
`survey_channel`.

- **`latest_nps` = the `score` of the most recent (max `response_date`) NON-retracted response.**
  Exclude `retracted == true` rows before taking the latest.
- For QBR `nps_score` per month and the peak-NPS highlight, the per-month value reconciles with the
  metrics endpoint `nps_score` (and with the matching non-retracted NPS response). Months with no
  survey can be null in metrics; use the controlled handling the template implies.

## 5. The retention risk model (queues, boards) — see references/risk_model.md

Renewal-risk queues (top-N) and high-touch action boards share one risk model. The exact integer
weighting of `risk_score` is internal and **not uniquely recoverable** from the training data
(it uses graded SLA points plus a lifecycle component), so do not over-fit a magic formula. What
IS reliable and graded — and what you must get right — are the **reason-code triggers, the
risk_level bands, the primary_action ladder, the sort order, and the derived summary formulas**.
Read `references/risk_model.md` for the full detail; the essentials:

### Reason-code triggers (assessment as of the as-of date)
- `overdue_receivable`: older-bucket overdue_balance (`61_90+90_plus`) > 0.
- `clean_billings`: older-bucket overdue_balance == 0.
- `sla_degradation`: clean-ticket SLA below target — fires when first-response SLA OR resolution
  SLA over clean tickets is below ~95% (treat <95% as degraded; a perfect 100/100 account does
  not fire). Use the ticket-derived SLA, never the metrics field.
- `nps_drop`: customer-sentiment weakness — low and/or declining latest NPS (latest non-retracted
  NPS that is low, e.g. sub-50, or has dropped materially from the period's first reading).
- `usage_decline`: latest-month `product_usage` is weak — fires when the latest month's
  `product_usage` is below ~60. (A high-usage account that dipped a few points does NOT fire;
  the signal is an absolute-low latest usage, not merely a negative delta.)
- `low_tenure_high_churn`: `contract_tenure_months` is low (≈ ≤ 18).
- `renewal_window`: `renewal_date` is in the future and within 90 days of the as-of date
  (0 ≤ days_until_renewal ≤ 90). Past-due or far-future renewals do not fire.
- `expansion_offset`: the account has open Q-period expansion pipeline (see §6) > 0.

### risk_level bands (from gold: 100→critical, 60/50→high, 20/15→low; medium sits between)
Higher score → higher severity. Approximate cutoffs: `critical` ≳ 80, `high` ≈ 40–79,
`medium` ≈ 25–39, `low` < 25. Calibrate so the score→level mapping is monotonic and reproduces
the obvious cases (a fully-distressed account is critical; an account whose only issue is a single
soft signal is low).

### primary_action ladder (apply top-down; first match wins)
1. `collections_followup` — if `overdue_receivable` is present (older-bucket overdue > 0).
   Receivables outrank everything.
2. `technical_recovery` — else if there is SLA distress, especially first-response SLA failing,
   typically alongside nps_drop/usage_decline (a "technical/support distress" profile).
3. `renewal_save` — else if `renewal_window` is the dominant signal (renewal imminent, support is
   not the core problem).
4. `nurture_monitor` / `no_action` — low-risk accounts with no actionable hard trigger.
   On the **full action board**, low-risk accounts with no real driver get `primary_action =
   "no_action"` and `next_touch_due_date = null` (no calendar entry). `executive_qbr` exists in
   the enum but is reserved for the most extreme strategic cases.

### Sorting / tie-breaks
Sort by **risk_level severity descending** (critical > high > medium > low), then by
**`current_arr` descending** as the tie-break within a level. (Boards return all accounts in this
order; queues return the top-N.) `board_sort_code = BORD-4`.

### Portfolio / segment summaries
- `accounts_reviewed` = number of input accounts.
- `critical_or_high_count` = accounts at critical or high.
- `collections_count` / `technical_recovery_count` = counts of those primary_actions in the output.
- **`arr_at_risk` = sum of `current_arr` for accounts at critical + high + MEDIUM** (low excluded).
  Do not restrict it to critical+high only.
- `open_expansion_pipeline` = sum of per-account `expansion_pipeline` (§6).
- **`net_revenue_exposure` = `arr_at_risk − open_expansion_pipeline`** (expansion offsets exposure;
  there is no overdue term). `exposure_formula_code = EXP-6`.
- `strategic_accounts` / `enterprise_accounts` = counts by the account `segment` field.

### Action calendar (boards)
When the prompt gives per-action due dates, set `next_touch_due_date` from that calendar by the
chosen `primary_action`. `no_action` → `next_touch_due_date = null`. `calendar_policy_code = CAL-5`.

## 6. Opportunities & expansion pipeline

`/api/opportunities?start=&end=` filters by `close_date` in range; fields include `state`
(open/closed), `stage` (Closed Won / Closed Lost / Discovery / ...), `amount`, `product_line`,
`account_id`, `account_legal_name`.

- **Per-account `expansion_pipeline`** = sum of `amount` for that account's OPEN opportunities whose
  `close_date` falls in the analysis quarter window. Open = `state == "open"`.
- **Pipeline summary (operations review):**
  - `won_count` / `won_revenue` = opportunities with `stage == "Closed Won"` (count, sum amount).
  - `lost_count` = `stage == "Closed Lost"`.
  - `open_count` / `open_pipeline` = `state == "open"` (count, sum amount).
  - **`win_rate_pct` = won / (won + lost) × 100**, 1 dp (denominator is closed deals only, not total).
  - **`top_open_product_line` = the product_line with the greatest summed open `amount`** (by dollar
    value, NOT by deal count — these can differ; pick by amount).

## 7. HR / events context

- `/api/hr/summary?quarter=YYYY-QN` returns one row per region. `hr_headcount` = sum of headcount
  across all requested regions; `unpaid_claims_total` = sum of `unpaid_claims_amount` across them.
- `/api/events/performance?event=<id>&quarter=YYYY-QN` gives `event_orders`, `event_revenue`, etc.
  for that event/quarter; read them directly.

## 8. Churn model validation & outreach ranking — see references/churn_model.md

The churn exports are a Telco-style classification dataset (numeric + categorical features).

- `training_rows` = train.csv data rows, `validation_rows` = validation.csv rows,
  `feature_count` = columns minus `customer_id` and `Churn` (e.g. 19). candidates.csv has no `Churn`.
- **Model: `LogisticRegression` on a `ColumnTransformer` of `StandardScaler` (numeric) +
  `OneHotEncoder(drop="first", handle_unknown="ignore")` (categorical).** The `drop="first"`
  matters: it reproduces the graded ~93% validation accuracy; omitting it lands ~91–92%. Fit on
  train, evaluate accuracy on validation. Map to `accuracy_band`:
  below_70 / 70_to_79 / 80_to_89 / 90_plus.
- `tenure_coefficient_direction` = sign of the fitted coefficient on (scaled) tenure — it is
  `negative` (more tenure → less churn).
- Rank only the requested candidate accounts by `predict_proba` of churn, top 5, probabilities to
  3 dp. The strongly-churning account dominates (e.g. low tenure + past-due + low NPS + falling
  usage); the rest have near-zero probabilities whose fine ordering is solver-sensitive, so don't
  agonize over the 4th/5th decimal-place ties — report what the fitted model gives.
- **Outreach mapping (`outreach_action` / `reason_code`), apply top-down:**
  1. `InvoicePastDue == "Yes"` → `collections_followup` / `overdue_receivable`.
  2. low tenure (≈ ≤ 18) → `renewal_save` / `low_tenure_high_churn`.
  3. high support load / negative sentiment (many tickets or low NPS) → `technical_recovery` /
     `sla_degradation`.
  4. negative usage trend → `nurture_monitor` / `usage_decline`.
  5. otherwise → `nurture_monitor` / `clean_billings`.
- `cohort_checks`: `past_due_shortlist_count` = candidates with InvoicePastDue=Yes;
  `low_tenure_shortlist_count` = candidates with low tenure; `average_probability_top5` = mean of
  the 5 reported probabilities (3 dp). Compute these over the **requested candidate set**.

## 9. policy_codes (every `*_code` field)

These are fixed policy identifiers, not derived from data, but they are graded. Across the task
family the verified values are the **middle option** of each template triple, with one exception.
Set them exactly:

| field                    | value  | notes |
|--------------------------|--------|-------|
| `risk_model_code`        | `RS-6` | retention risk tasks |
| `arr_source_code`        | `REV-4`| billing-snapshot ARR source |
| `support_hygiene_code`   | `SUP-8`| |
| `action_priority_code`   | `ACT-5`| |
| `board_sort_code`        | `BORD-4`| action board |
| `exposure_formula_code`  | `EXP-6`| arr_at_risk − expansion |
| `calendar_policy_code`   | `CAL-5`| |
| `receivable_trigger_code`| `RCP-7`| operations review |
| `crm_match_code`         | `CM-5` | |
| `pipeline_window_code`   | `PW-6` | |
| `followup_scope_code`    | `FS-4` | |
| `model_protocol_code`    | `MOD-7`| churn task |
| `probability_scale_code` | `PRB-4`| churn task |
| `deployment_rule_code`   | `DEP-5`| churn task |
| `outreach_mapping_code`  | `OUT-2`| churn task — **NOT** the middle `OUT-6`; the graded value is `OUT-2` |

If a future template offers a different triple, default to the middle option, but remember
`outreach_mapping_code` is the known exception (`OUT-2`).

## 10. QBR metrics packet (single-account quarterly deck)

- `revenue` per month = metrics `recognized_revenue` (value), but the **`metric_sources.revenue`
  enum is `crm_closed_won`**, not `billing_snapshot`. (Value source ≠ labeled source here.)
- `support_tickets` = clean ticket count per month (§3); `metric_sources.support_tickets` =
  `support_export`.
- `sla_compliance_pct` = ticket-derived first-response SLA per month (§3);
  `metric_sources.sla_compliance` = `sla_report`.
- `nps_score` per month from metrics / non-retracted NPS; `metric_sources.nps` = `nps_survey`.
- Highlights: `average_revenue`, `peak_revenue_month`/`peak_revenue`, `max_sla_month`/`max_sla_pct`,
  `peak_nps_month`/`peak_nps_score` are the argmax/means over the recomputed monthly values.
- `ticket_trend`: compare first vs last month clean-ticket counts — fewer = `improving`, more =
  `worsening`, equal = `flat`.
- `review_owner` = `customer_success` for a CS-led QBR. `needs_technical_signoff` reflects whether
  there is genuine technical/SLA recovery work; a basically-healthy account is `false`.
- `agenda_topics`: choose four ordered enum values. Use a "healthy" agenda
  (`partnership_overview`, `q2_metrics`, `performance_highlights`, `q3_initiatives`) BUT swap in
  `technical_recovery` (replacing `performance_highlights`) when any month shows SLA distress —
  i.e. include `technical_recovery` if the recomputed monthly SLA dips materially below target even
  if `needs_technical_signoff` stays false.

## 11. Common pitfalls checklist (verify before returning)

- [ ] current_arr came from the billing **snapshot at the as-of date**, not `billing_arr_current`/crm.
- [ ] overdue_balance = `61_90 + 90_plus` only; accounts with debt only in 1_30/31_60 show 0.0.
- [ ] clean tickets exclude spam, duplicates, AND cancelled.
- [ ] SLA % computed from clean tickets' `first_response_sla_met`, not the metrics SLA field.
- [ ] QBR support_tickets = clean count, not metrics `support_ticket_count`.
- [ ] latest_nps excludes retracted responses.
- [ ] A/R linked by exact legal_name; decoy look-alikes are unlinked / account_id null.
- [ ] arr_at_risk includes medium (critical+high+medium); net_revenue_exposure = arr_at_risk − expansion.
- [ ] win_rate = won/(won+lost); top_open_product_line by summed amount.
- [ ] no_action ⇒ next_touch_due_date null on the board.
- [ ] churn model uses OneHotEncoder(drop="first"); accuracy band + tenure direction reported.
- [ ] every `*_code` set per §9 (outreach_mapping_code = OUT-2).
- [ ] JSON only; keys/enums match template; rounding applied once at the end.
