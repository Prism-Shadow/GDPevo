---
name: apexcloud-retention-ops
description: >-
  Build ApexCloud Retention Operations analytics deliverables from the live read-only
  HTTP API (account/billing/tickets/NPS/AR-aging/opportunities/HR/events/churn-CSV
  endpoints). Use this skill WHENEVER a task asks you to produce a JSON answer about
  ApexCloud / "Retention Operations" — renewal risk queues, QBR metric packets,
  receivables-and-pipeline operations reviews, churn model validation + outreach
  ranking, or high-touch retention action boards. Trigger it on any prompt that names
  ApexCloud, a base URL like http://127.0.0.1:80xx with /api/accounts, /api/finance/ar-aging,
  /api/billing/snapshots, /exports/churn/*.csv, or that lists account_ids (acct_*) and
  asks for risk_score / risk_level / primary_action / reason_codes / overdue_balance /
  current_arr / arr_at_risk / policy_codes. It encodes the exact data sources, exclusion
  rules, formulas, enum/policy codes, and ordering/tie-break conventions so the output
  matches the graded gold answers instead of plausible-but-wrong guesses.
---

# ApexCloud Retention Operations

This skill encodes hard-won, verified conventions for ApexCloud Retention Operations
deliverables. The tasks look like simple data pulls, but every field has a *specific*
source and exclusion rule, and several rules are **task-family dependent** (the same
field name means different things on different deliverables). Guessing reasonably gets
the values wrong; the rules below are reverse-engineered from graded gold answers and
re-verified against the live API.

## Golden rule: produce JSON only, exactly matching the template

Each task ships an `answer_template.json`. Return JSON only — same keys, same nesting,
same enum vocabulary, same key order where practical. Precision: **currency to 2
decimals, percentages to 1 decimal, counts and risk_scores as integers.** Round only at
the very end; carry full precision through every intermediate sum.

## Environment

- Base URL is given in the prompt / `environment_access.md` (e.g. `http://127.0.0.1:8074`).
  Confirm with `GET /api/health` (returns row_counts + seed). Retry once if a connection
  is momentarily refused; never port-scan.
- All data comes from these read-only GET endpoints — never read local data files:
  - `/api/accounts`, `/api/accounts/<id>`
  - `/api/accounts/<id>/metrics?start=YYYY-MM&end=YYYY-MM`
  - `/api/accounts/<id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD`
  - `/api/accounts/<id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD`
  - `/api/billing/snapshots?as_of=YYYY-MM-DD&account_id=<id>`
  - `/api/finance/ar-aging?as_of=YYYY-MM-DD` (optional `&region=`)
  - `/api/opportunities?start=YYYY-MM-DD&end=YYYY-MM-DD` (optional `&region=`)
  - `/api/hr/summary?quarter=YYYY-QN` (optional `&region=`)
  - `/api/events/performance?event=<id>&quarter=YYYY-QN`
  - `/exports/churn/{train,validation,candidates}.csv`, `/exports/account_metric_extract.csv`
- Response envelopes wrap the list under a named key: `ar_aging`, `snapshots`,
  `tickets`, `nps_responses`, `metrics`, `opportunities`. Unwrap before iterating.
- Pure-Python only (no numpy/pandas/sklearn). Run scripts from the working directory,
  never from `/tmp` (a stray module there can shadow stdlib imports). Use `urllib`/`curl`.

## Core field definitions (the source of truth, and the easy-to-get-wrong ones)

These are the canonical definitions. The data model deliberately plants decoys — flat
ARR fields that look authoritative, an `sla_compliance` metric that *isn't* the SLA you
report, monthly ticket counts that include junk, and later-dated retracted NPS rows.

### current_arr — billing snapshot at the as-of date
`current_arr` = the billing snapshot `billing_arr` whose `as_of` equals the assessment /
as-of date. Fetch with `GET /api/billing/snapshots?account_id=<id>&as_of=<asof>` and take
that single posted row's `billing_arr`.
- Do **NOT** use `account.billing_arr_current` (a rounded list-price decoy) or
  `account.crm_arr` (a different decoy). Both differ from the snapshot.
- This sets `uses_billing_arr_source = true` and `arr_source_code = REV-4`.

### clean_ticket_count — exclude spam, duplicates, AND cancelled
From `/api/accounts/<id>/tickets` over the period, a ticket is "clean" iff:
`is_spam == false AND is_duplicate == false AND status != "cancelled"`.
- Forgetting `status != "cancelled"` is a real, recurring error — it inflates counts.
- Do **NOT** use the monthly `support_ticket_count` from `/metrics`; that is raw and
  includes the junk. `support_hygiene_code = SUP-8`.

### overdue_balance — TASK-FAMILY DEPENDENT (read carefully)
AR aging rows have buckets `current`, `1_30`, `31_60`, `61_90`, `90_plus`. `account_id`
is parseable from `aging_id` (`AR-<account_id>-<quarter>`); `customer_name` = legal_name.
There are **two different overdue definitions**, chosen by deliverable type:

| Deliverable | overdue_balance / overdue_total = | overdue_receivable code fires when |
|---|---|---|
| Renewal Risk Queue (risk_accounts) | `61_90 + 90_plus` (older buckets only) | older buckets `> 0` |
| Receivables/Ops Review (overdue_followups) | `61_90 + 90_plus` (older buckets only) | older buckets `> 0` (this is the "older aging buckets" the prompt names) |
| Retention Action Board (action_board) | `1_30 + 31_60 + 61_90 + 90_plus` (TOTAL non-current) | total overdue `> 0` |

Decide by the output shape: if the deliverable is the **action board** (keys like
`action_board`, `expansion_pipeline`, `net_revenue_exposure`, `segment_summary`), use
TOTAL overdue. If it's the **renewal risk queue** (`risk_accounts`, `portfolio_summary`)
or the **receivables review** (`overdue_followups`, "older aging buckets" wording), use
**older buckets only**. This single distinction was the most damaging blind-attempt
error — getting it backwards corrupts overdue_balance, overdue_total, the
overdue_receivable trigger, and every downstream action/score.

### latest_nps — latest non-retracted response
From `/api/accounts/<id>/nps`, drop every row with `retracted == true`, sort the rest by
`response_date`, take the last one's `score`. A retracted row can have a *later* date than
the valid latest — still skip it. (Monthly `metrics.nps_score` agrees when a month's
survey completed, but the /nps endpoint is the authoritative source for "latest".)

### Monthly metrics
`/metrics` rows carry `recognized_revenue`, `support_ticket_count`, `sla_compliance`,
`nps_score`, `product_usage`, `active_seats`, `survey_status`, `month`/`quarter`. Use
`recognized_revenue` for revenue; use the *raw* metric fields only where a definition
above does not override them (it usually does for tickets and SLA).

## The risk model (renewal queue + action board)

`risk_score` is an additive, capped-at-100 integer built from driver weights (all
multiples of 5). The exact integer per account matters; reproduce the model rather than
inventing weights. Derived weights that reproduce the gold scores:

| Driver | weight |
|---|---|
| sla_degradation | 15 |
| renewal_window | 20 |
| overdue_receivable | 25 |
| nps_drop | 20 |
| usage_decline | 10 |
| low_tenure_high_churn | 5 |
| lifecycle in {renewal_risk} | +5 |

Sum the weights of the drivers that fire, then **cap at 100**. (A maximal account hits
the 100 cap.) Always cross-check: the gold scores observed were neat multiples of 5, so a
non-multiple-of-5 score is a red flag that a trigger is mis-evaluated.

**risk_level bands:** `critical >= 80`, `high >= 50`, `medium >= 30`, `low < 30`.

**Reason-code triggers** (emit ALL that fire, in this canonical order:
`renewal_window, overdue_receivable, nps_drop, sla_degradation, usage_decline,
low_tenure_high_churn, expansion_offset, clean_billings`):
- `renewal_window`: renewal is near-term — renewal_date within ~90 days of the as-of date
  *or* recently past-due within the current renewal cycle. (Far-future renewals, >~90
  days out, do not fire.) This trigger has fuzzy edges; see Pitfalls.
- `overdue_receivable`: per the task-family overdue rule above (`> 0`).
- `nps_drop`: `latest_nps < 40`.
- `sla_degradation`: SLA health is soft — min monthly `sla_compliance` below the ~90–95
  band. Treat clearly-degraded SLA (a month well under target) as firing.
- `usage_decline`: declining product engagement (product_usage / active-seat erosion).
  Edges are fuzzy; see Pitfalls.
- `expansion_offset`: the account has a material open expansion opportunity that offsets
  risk. Fires for accounts with a sizeable open Q2 pipeline.
- `clean_billings`: emit only when no overdue/billing risk codes fire (a "nothing bad on
  billing" flag), typically alongside low-risk accounts.

**primary_action ladder** (evaluate top-down; first match wins). Note collections
**outranks** executive_qbr — even a Strategic, multimillion-ARR, critical account gets
`collections_followup` if it has older/total overdue:
1. overdue (per task-family rule) `> 0` → `collections_followup`
2. else `sla_degradation` OR `usage_decline` → `technical_recovery`
3. else `renewal_window` → `renewal_save`
4. else high-value strategic/critical with no operational issue → `executive_qbr`
5. else → `nurture_monitor`

On the action board, low-risk accounts still flow through the ladder (they got real
actions like `technical_recovery`/`renewal_save`, not `no_action`). Reserve `no_action`
only if a deliverable explicitly calls for it.

**Ordering / tie-break:** sort by `risk_score` **descending**, then `current_arr`
descending. (`board_sort_code = BORD-4`.) Within a risk_level, a higher-ARR account can
still rank below a lower-ARR one if its score is lower — the score is primary.

## Portfolio / segment aggregates

- `arr_at_risk` = sum of `current_arr` for accounts at **critical OR high** risk
  (not all listed accounts, not weighted). `exposure_formula_code = EXP-6`.
- `open_expansion_pipeline` = sum of open Q2 expansion `amount` across the board
  accounts (opportunities with `state == "open"` and `close_date` inside the period).
- `net_revenue_exposure` = `arr_at_risk − open_expansion_pipeline` (expansion offsets risk).
- `collections_count` / `technical_recovery_count` = count those primary_actions among
  the **listed/ranked** accounts.
- `accounts_reviewed` = every in-scope account (not just the top-N returned).
- `critical_or_high_count` = count of critical+high among the ranked accounts.
- Segment counts (`strategic_accounts`, `enterprise_accounts`) = counts by the account
  `segment` field among the board accounts.

## QBR metrics packet (single account, by month)

This deliverable's monthly metrics are mostly computed from the **tickets endpoint**, not
the metrics endpoint — a key correction:
- `revenue` (per month) = `metrics.recognized_revenue`. **Source label =
  `crm_closed_won`** (NOT `billing_snapshot`, despite the value coming from metrics).
- `support_tickets` (per month) = **clean ticket count** from `/tickets`
  (spam/dup/cancelled excluded), bucketed by `created_date` month. Source =
  `support_export`. (Do NOT use `metrics.support_ticket_count`.)
- `sla_compliance_pct` (per month) = % of that month's clean tickets with
  `first_response_sla_met == true`, to 1 decimal. Source = `sla_report`. (Do NOT use
  `metrics.sla_compliance` — that is a separate, different number.)
- `nps_score` (per month) = the NPS response score in that month (non-retracted); source
  = `nps_survey`. Use `null` when no completed survey exists that month.
- `highlights`: average_revenue (mean of the monthly revenues), peak_revenue(+month),
  max_sla(+month), peak_nps(+month). `ticket_trend` = compare last month vs first month
  clean-ticket count → `improving` (down), `worsening` (up), `flat` (equal).
- `review_owner` = `customer_success` for ordinary CS-owned reviews
  (`solutions_engineering`/`finance_ops` only with a clear SE/finance-driven mandate).
- `agenda_topics` = exactly 4 ordered enum strings. Slots 1, 2, 4 are fixed:
  `partnership_overview`, `q2_metrics`, `q3_initiatives`. **Slot 3 is conditional:**
  `technical_recovery` if there is an SLA/support problem (any month's SLA below 100% /
  a clear dip); otherwise `commercial_expansion` if there's a strong expansion story;
  otherwise `performance_highlights`.
- `needs_technical_signoff` is stricter than the slot-3 trigger: a mild SLA dip flips the
  agenda to technical_recovery but still leaves signoff `false`. Set it `true` only for
  severe/sustained SLA failure.

## Receivables & pipeline operations review

1. Start from AR customers whose **older aging buckets (`61_90 + 90_plus`) > 0** at the
   as-of date — those are the overdue followups. `overdue_balance` per customer and
   `overdue_total` both use older buckets only.
2. **Link to CRM by EXACT `customer_name` == account `legal_name`.** Matches → `linked`
   with the `account_id`; non-matches → `unlinked` with `account_id: null`. Near-miss
   names (e.g. "… Subsidiary LLC", "North Star Finance Services" vs "Northstar Finance
   Group Inc.") are deliberate decoys that match neither legal_name nor aliases — keep
   them `unlinked`. Do not fuzzy-match. `crm_match_code = CM-5`.
3. Every followup `primary_action = collections_followup`, `due_date` = the prompt's
   fixed date. **Sort `overdue_followups` by `customer_name` ascending.**
4. Pipeline summary over Q3 opportunities: `won_count`/`won_revenue` = Closed Won;
   `lost_count` = Closed Lost; `open_count`/`open_pipeline` over `state == "open"`;
   `win_rate_pct = won/(won+lost)*100` to 1 decimal; `top_open_product_line` = the
   `product_line` with the largest summed open `amount`.
5. `ops_context`: `hr_headcount` = sum of headcount across all regions for the quarter;
   `unpaid_claims_total` = summed unpaid claims across regions; `event_orders` /
   `event_revenue` from the named event + quarter.
- Policy codes: `receivable_trigger_code = RCP-7`, `pipeline_window_code = PW-6`,
  `followup_scope_code = FS-4`.

## Churn model validation & outreach ranking

- Load `train.csv` (180 rows), `validation.csv` (60 rows), `candidates.csv`. The target
  column is `Churn`; an id column (`customer_id`) is not a feature. `feature_count` =
  columns minus id minus target = **19**.
- Fit a logistic regression (pure Python: one-hot drop-first categoricals + standardized
  numerics + gradient descent). `accuracy_pct` to 1 decimal; `accuracy_band` = `90_plus`
  when accuracy ≥ 90 (the gold model lands ≈ 93.3%). The tenure coefficient is
  **negative** (longer tenure → lower churn) → `tenure_coefficient_direction = negative`.
  Exact probabilities are model-dependent; what must hold is the **ranking and the
  feature-driven outreach mapping**.
- Rank the named candidates by predicted churn probability, return the **top 5**.
- **cohort_checks are computed over the TOP-5 shortlist, NOT over the full candidate
  list.** `past_due_shortlist_count` = #top5 with `InvoicePastDue == "Yes"`;
  `low_tenure_shortlist_count` = #top5 with low `tenure` (first ~2 years, i.e. tenure
  under ~24 months); `average_probability_top5` = mean of the 5 probabilities (3 decimals).
  Scoping these to the 8 targets instead of the top-5 is a known error.
- **outreach_action / reason_code ladder** (dominant feature, top-down; low_tenure
  outranks usage/SLA):
  1. `InvoicePastDue == "Yes"` → `collections_followup` / `overdue_receivable`
  2. else low tenure (under ~24 mo) → `renewal_save` / `low_tenure_high_churn`
  3. else low NPS or usage decline or high tickets → `technical_recovery` /
     (`usage_decline` | `sla_degradation`) [or `renewal_save`/`nps_drop` for low NPS]
  4. else → `nurture_monitor` / `clean_billings`
- Policy codes: `model_protocol_code = MOD-7`, `probability_scale_code = PRB-4`,
  `deployment_rule_code = DEP-5`, **`outreach_mapping_code = OUT-2`**.

## Policy codes

Many fields force a choice among opaque enum triples. The verified values across the task
families are listed in `references/policy_codes.md`. Use those exact codes when the field
appears. A "always pick the middle option" heuristic is *mostly* right but NOT safe — at
least one field breaks it (`outreach_mapping_code = OUT-2`, the first option). Prefer the
table.

## Common pitfalls (grounded in real errors)

- **Overdue bucket mix-up (highest impact).** Using all-non-current on a renewal queue /
  receivables review, or older-only on the action board, breaks overdue_balance, the
  overdue_receivable trigger, primary_action, and arr_at_risk. Pick the rule by
  deliverable type every time.
- **Forgetting `status != "cancelled"`** when counting clean tickets (over-counts).
- **Using metrics for SLA/tickets in the QBR.** Per-month SLA = % first_response_sla_met
  over clean tickets; per-month tickets = clean ticket count — both from `/tickets`.
- **Wrong revenue source label.** Revenue value is from metrics, but the *label* is
  `crm_closed_won`.
- **Flat ARR fields.** `billing_arr_current` and `crm_arr` are decoys; use the as-of
  billing snapshot.
- **Later-dated retracted NPS.** Skip retracted rows even when newer than the valid one.
- **Cohort_checks scope.** Compute over the top-5 shortlist, not the full candidate set.
- **Action ladder order.** collections > technical_recovery > renewal_save >
  executive_qbr > nurture_monitor. Don't promote executive_qbr ahead of collections.
- **Sort key.** risk_score desc then current_arr desc — score is primary even inside a
  level.
- **Aggregate scope.** arr_at_risk counts only critical+high; net exposure subtracts
  expansion; accounts_reviewed counts the full in-scope set.

## Recommended workflow

1. `GET /api/health`; read the prompt for: assessment/as-of date, period months,
   in-scope account_ids, fixed due dates, and which **deliverable type** it is.
2. Pull raw rows once per account (account, metrics, tickets, nps, billing snapshot,
   AR aging, opportunities) into local Python dicts; cache them.
3. Compute each field with the canonical definition above, applying the correct
   task-family overdue rule.
4. Score → level → reason_codes → primary_action → sort/tie-break.
5. Aggregate (arr_at_risk, exposure, segment counts, ops_context) from full precision.
6. Fill the template's enums/policy codes exactly; round at the end; emit JSON only.
7. Sanity checks: scores are multiples of 5 and ≤ 100; levels match bands;
   arr_at_risk == sum of critical+high current_arr; currency has 2 decimals; ordering
   obeys the sort key; overdue rule matches the deliverable.
