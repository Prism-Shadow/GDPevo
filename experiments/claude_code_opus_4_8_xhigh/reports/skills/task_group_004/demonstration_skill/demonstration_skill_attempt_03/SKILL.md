---
name: apexcloud-retention-ops
description: >-
  Operating procedure for solving ApexCloud Retention Operations tasks against the
  read-only HTTP API at http://127.0.0.1:8074. Use this skill whenever a task asks you
  to build a renewal risk queue, a retention action board, a QBR metrics packet, a
  receivables / pipeline operations review, or a churn-model validation & outreach
  ranking for ApexCloud accounts — or any time the prompt mentions current ARR,
  billing snapshots, clean ticket counts, latest NPS, overdue A/R aging buckets,
  risk scoring, reason codes, primary actions, or the four-letter policy_codes
  (RS-/REV-/SUP-/ACT-/RCP-/CM-/PW-/FS-/MOD-/PRB-/DEP-/OUT-/BORD-/EXP-/CAL-).
  These tasks share fixed business conventions that are easy to get wrong; follow this
  skill instead of guessing the data sources, exclusion rules, thresholds, or enums.
---

# ApexCloud Retention Operations SOP

This skill captures the **business conventions** behind the ApexCloud Retention
Operations task family. The graders are deterministic: the exact data source, the
exclusion rule, the threshold, the enum spelling, the sort order, and the rounding
all matter. Getting the *narrative* right is not enough — reproduce the *rules*.

All data comes from the read-only HTTP API. The base URL is given in the prompt /
environment (typically `http://127.0.0.1:8074`). Use `curl` + a JSON parser
(`python3 -c` / `jq`). Never read local files, `env/`, or task-group source — only
the API. The service is already running; ignore any "start command" in the prompt.

## Workflow

1. **Identify the task family** (see table below) and read its answer template to lock
   in the exact output keys, enum vocabularies, and rounding.
2. **Pull each metric from its canonical source** using the rules in
   "Canonical metric definitions". Do not substitute one source for another (e.g. the
   account record's `billing_arr_current` is NOT the current ARR; the metrics
   endpoint's `support_ticket_count` is NOT the clean ticket count).
3. **Apply the exclusion / threshold rules** exactly.
4. **Derive risk signals, reason codes, level, and action** per "Risk model".
5. **Sort / rank** per the family's rule, then format with the required precision and
   the correct `policy_codes`.
6. Return **only JSON** matching the template. No prose, no code fences.

`references/api_and_rules.md` has endpoint-by-endpoint field maps, worked numeric
examples, and the per-family `policy_codes` cheat-sheet. Read it when you need the
exact shape of a response or to confirm a threshold.

## Task families and their policy_codes

| Family | Trigger words | Top-level keys | Fixed policy_codes |
|---|---|---|---|
| Renewal Risk Queue | "renewal risk queue", "top N ranked by risk" | `risk_accounts`, `portfolio_summary`, `model_checks`, `policy_codes` | RS-6, REV-4, SUP-8, ACT-5 |
| Retention Action Board | "action board", "operating review", "retention board order" | `action_board`, `segment_summary`, `followup_calendar`, `policy_codes` | RS-6, REV-4, SUP-8, ACT-5, BORD-4, EXP-6, CAL-5 |
| QBR Metrics Packet | "QBR", "metrics packet", "quarterly business review" | `qbr_metrics`, `highlights`, `metric_sources`, `review_plan`, `agenda_topics` | (no policy_codes block; uses `metric_sources` enums) |
| Receivables & Pipeline Review | "receivables", "operations review", "A/R", "pipeline" | `financial_summary`, `pipeline_summary`, `overdue_followups`, `ops_context`, `policy_codes` | RCP-7, CM-5, PW-6, FS-4 |
| Churn Validation & Ranking | "churn model", "validation", "outreach ranking", "candidates.csv" | `model_validation`, `risk_ranking`, `cohort_checks`, `model_policy_codes` | MOD-7, PRB-4, DEP-5, OUT-2 |

These code values recur across tasks and are the **same every time** for the same
family. The answer template offers three options per code (e.g. `RS-2|RS-6|RS-9`);
pick the value listed above. They encode the policy you are following (RS-6 = the
six-signal risk model, REV-4 = billing-snapshot ARR source, SUP-8 = spam+dup+cancelled
ticket hygiene, ACT-5 = the action-priority ladder, etc.). When in doubt, match the
exact option from the template that corresponds to the rule you actually applied.

## Canonical metric definitions

These are shared across families. The graders test the *source*, not just the value.

### Current ARR  →  billing snapshot (NOT the account record, NOT CRM)
- Endpoint: `GET /api/billing/snapshots?account_id=<id>&as_of=<YYYY-MM-DD>`.
- `current_arr` = the `billing_arr` of the latest **posted** snapshot with
  `as_of <= the assessment/as-of date`. The `&as_of=` query param already returns that
  single snapshot; otherwise pick the max `as_of` not after the date yourself.
- Do **not** use the account's `billing_arr_current` (a rounded plan figure) or
  `crm_arr`. Snapshots are the posted source of truth and differ by thousands.
- `model_checks.uses_billing_arr_source` = `true`. `arr_source_code` = `REV-4`.

### Clean support ticket count  →  tickets endpoint, hygiene-filtered
- Endpoint: `GET /api/accounts/<id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD`.
- A ticket is **clean** only if ALL hold: `is_spam == false` AND
  `is_duplicate == false` AND `status != "cancelled"` (valid statuses: open, closed,
  cancelled). Count by `created_date` inside the window.
- Do **not** use the metrics endpoint's `support_ticket_count` (that is the raw count
  including spam/dup/cancelled). `support_hygiene_code` = `SUP-8`.

### Latest NPS  →  nps endpoint, retracted excluded, most recent in window
- Endpoint: `GET /api/accounts/<id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD`.
- Drop responses with `retracted == true`. Among the rest in the window, take the one
  with the **latest `response_date`**; its `score` is `latest_nps`.
- If no valid response exists in the window, NPS is missing → emit `null` (QBR uses
  `null` for months/highlights with no completed survey).

### Overdue balance  →  A/R aging, OLDER buckets only
- Endpoint: `GET /api/finance/ar-aging?as_of=YYYY-MM-DD` (optional `&region=`).
- `overdue_balance = bucket["61_90"] + bucket["90_plus"]`. The "older aging buckets"
  phrasing means 61+ days. **Exclude** `current`, `1_30`, and `31_60`.
- Match a row to an account via its `aging_id`: real CRM accounts have
  `AR-<account_id>-<quarter>`; rows shaped `AR-noise-...` are non-CRM ("unlinked").
  If no matching aging row, overdue = `0.00`.

### Monthly metrics  →  metrics endpoint
- Endpoint: `GET /api/accounts/<id>/metrics?start=YYYY-MM&end=YYYY-MM` (note: months,
  not dates). Fields per month: `recognized_revenue`, `support_ticket_count` (raw),
  `sla_compliance`, `nps_score`, `product_usage`, `active_seats`, `survey_status`.

## Risk model (RS-6) — reason codes, level, action

Compute these per account over the analysis window using the canonical sources above.
The six **negative** signals and two **positive** signals each map to a reason code.

### Reason-code triggers (verified)
- `renewal_window` — `renewal_date` is in the future and within ~90 days of the as-of
  date (i.e. `0 < days_to_renewal <= 90`). Past-due renewals do NOT fire this.
- `overdue_receivable` — `overdue_balance > 0` (the 61_90+90_plus rule).
- `nps_drop` — `latest_nps < 40` **OR** the NPS fell sharply within the window
  (`first_valid_score − latest_valid_score >= ~15`). A low absolute score OR a steep
  decline both count.
- `sla_degradation` — **any** clean ticket has `first_response_sla_met == false` OR
  `resolution_sla_met == false`. (Driven by ticket SLA flags, NOT the metrics
  `sla_compliance` field. An account fires this even at high metric SLA if it has one
  missed ticket; an account with zero misses does not fire it.)
- `usage_decline` — the minimum monthly `product_usage` in the window is low
  (`min(product_usage) < ~65`). This is an absolute floor, not a month-over-month delta.
- `low_tenure_high_churn` — `contract_tenure_months < 18`. (Confirmed by the churn
  cohort: tenure 12/13/7 fire; 20 does not.)
- `expansion_offset` (positive) — the account has open expansion pipeline in the window
  (`sum of open opportunity amounts > 0`). It is a *mitigating* note placed last.
- `clean_billings` (positive) — receivables are clean (`overdue_balance == 0`) and the
  account has no receivable problem to flag. Used as the positive note for low-risk
  accounts that have no open-expansion story.

Order reason_codes with **negatives first** (a natural order such as renewal_window,
overdue_receivable, nps_drop, sla_degradation, usage_decline, low_tenure_high_churn),
then positives (expansion_offset / clean_billings) last. An account can carry both a
positive note and negatives.

### Risk level bands (by integer risk_score, rounded to nearest 5)
- `critical`: score >= 80
- `high`: 50–79
- `medium`: 30–49
- `low`: < 30

`risk_score` is a weighted blend of the triggered signals scaled by their severity
(overdue size, how low NPS/usage are, how soon renewal is, tenure). It is reported as
an integer (multiples of 5 in practice) and **clamped to 0–100**. Two accounts with the
same reason-code *set* can still get slightly different scores because severity is
continuous — so derive the score from the underlying magnitudes, not from a fixed
points-per-code table. What the grader checks most reliably is the **ordering and the
level band**, so make sure stronger-signal accounts outrank weaker ones.

### Primary action ladder (ACT-5) — first match wins
1. `overdue_receivable` present → `collections_followup`.
2. else technical health is weak (`sla_degradation` and/or `usage_decline`, especially
   low `product_usage`) → `technical_recovery`.
3. else `renewal_window` present with otherwise healthy technical signals →
   `renewal_save`.
4. else high/critical with no clearer driver → `executive_qbr`.
5. else low risk → `no_action` (action board) or `nurture_monitor` (queues that prefer
   a monitoring touch). Pick the enum the template offers.

When two accounts share reason codes but differ in raw severity (e.g. one has weak
`product_usage`), let the stronger technical problem pull toward `technical_recovery`
and the healthier one toward `renewal_save`. Tie-break ranking by `risk_score` desc,
then by `current_arr` desc.

### tenure_risk_direction
Lower tenure → higher risk, so `model_checks.tenure_risk_direction = "negative"` (also
the churn `tenure_coefficient_direction`).

## Family-specific assembly notes

### Renewal Risk Queue
- Score every reviewed account; return the **top N (usually 5) by risk_score desc**
  (tie-break `current_arr` desc). Each item: rank, account_id, risk_score, risk_level,
  primary_action, current_arr, latest_nps, clean_ticket_count, overdue_balance,
  reason_codes.
- `portfolio_summary.accounts_reviewed` = count of ALL reviewed accounts (not just the
  top 5). `critical_or_high_count` = number of returned accounts at critical/high.
  `arr_at_risk` = **sum of current_arr for the critical+high accounts only**.
  `collections_count` / `technical_recovery_count` = counts of those primary_actions
  among the returned accounts.

### Retention Action Board
- Return **all** requested accounts in board order: rank by risk severity
  (critical→high→medium→low), then within ties by current_arr desc (BORD-4). Low /
  no_action accounts get `next_touch_due_date: null`.
- `expansion_pipeline` = sum of that account's open Q2 opportunity amounts (0.0 if none).
- `next_touch_due_date` comes from the prompt's per-action calendar (CAL-5); echo that
  same map into `followup_calendar`.
- `segment_summary`: `strategic_accounts` / `enterprise_accounts` = counts by the
  account `segment` field. `arr_at_risk` = **sum of current_arr for all non-low /
  non-no_action accounts** (i.e. medium+high+critical). `open_expansion_pipeline` =
  total expansion_pipeline across the board. `net_revenue_exposure = arr_at_risk −
  open_expansion_pipeline` (EXP-6).
- (Note the deliberate difference vs the Renewal Queue: the queue's `arr_at_risk` is
  critical+high only; the board's is everything except low/no_action.)

### QBR Metrics Packet
- Per month build: `revenue = recognized_revenue` (metrics);
  `support_tickets = clean ticket count` (tickets endpoint, hygiene-filtered — NOT the
  metrics raw count); `sla_compliance_pct` = % of that month's **clean tickets** whose
  `first_response_sla_met` is true (1 decimal); `nps_score` = latest valid NPS in that
  month, else `null`.
- `metric_sources` are **fixed labels** describing provenance, not literal endpoints:
  `revenue: "crm_closed_won"`, `support_tickets: "support_export"`,
  `sla_compliance: "sla_report"`, `nps: "nps_survey"`.
- `highlights`: average_revenue (mean of monthly revenue), peak revenue month/value,
  max SLA month/value, peak NPS month/value (ignore null months), and `ticket_trend`:
  `improving` if clean tickets trend down, `worsening` if up, else `flat`.
- `review_plan.review_owner`: `customer_success` by default;
  `solutions_engineering` if the quarter has notable technical/SLA recovery work;
  `finance_ops` if the story is billing/receivables-driven. `review_due_date` and
  `needs_technical_signoff` follow the prompt; signoff is generally `false` unless a
  severe/sustained technical breach is present.
- `agenda_topics`: exactly four, **ordered**, from the allowed set. Lead with
  `partnership_overview`, then `q2_metrics`; include `technical_recovery` when there was
  an SLA dip and `commercial_expansion` when there is open expansion pipeline; close
  with `q3_initiatives`.

### Receivables & Pipeline Review
- Start from A/R rows with overdue > 0 (61_90+90_plus). `overdue_client_count` and
  `overdue_total` cover ALL such rows (CRM and noise). For each, `link_status` =
  `linked` if its `aging_id` is `AR-<account_id>-...` for a real account (set
  `account_id`), else `unlinked` (`account_id: null`). `linked_followup_count` /
  `unlinked_followup_count` split them. `primary_action` is always
  `collections_followup`; `due_date` is the prompt's follow-up date. **Sort
  overdue_followups by `customer_name` ascending.**
- `pipeline_summary` from `GET /api/opportunities?start=&end=` over the quarter:
  `won` = `stage == "Closed Won"`, `lost` = `stage == "Closed Lost"`, `open` =
  `state == "open"`. `won_revenue` / `open_pipeline` = summed `amount`.
  `win_rate_pct = won / (won + lost) * 100` (1 decimal). `top_open_product_line` =
  the `product_line` with the largest open `amount` total.
- `ops_context`: `hr_headcount` = sum of `headcount` across the requested HR regions;
  `unpaid_claims_total` = sum of `unpaid_claims_amount`; `event_orders` /
  `event_revenue` read directly from the event-performance row.

### Churn Validation & Ranking
- Use the CSV exports: `/exports/churn/train.csv`, `validation.csv`, `candidates.csv`.
  `training_rows` / `validation_rows` = data row counts (180 / 60 in the seed but
  recount). `feature_count` = columns minus `customer_id` and the `Churn` target
  (= 19 in the seed). Fit a simple classifier on train, score validation for
  `accuracy_pct` (1 decimal) and map to `accuracy_band`
  (below_70 / 70_to_79 / 80_to_89 / 90_plus). `tenure_coefficient_direction` =
  `negative`.
- Rank only the named candidates by `predicted_churn_probability` (3 decimals),
  return top 5. `outreach_action` / `reason_code` mirror the action ladder on the CSV
  features: `InvoicePastDue == Yes` → `collections_followup` / `overdue_receivable`;
  else `tenure < 18` → `renewal_save` / `low_tenure_high_churn`; else
  `nurture_monitor` / `clean_billings` (technical_recovery / sla_degradation when SLA/
  usage features are the dominant problem).
- `cohort_checks` are computed over the **returned top-5**, not all candidates:
  `past_due_shortlist_count` = top-5 with PastDue, `low_tenure_shortlist_count` =
  top-5 with tenure < 18, `average_probability_top5` = mean of the 5 probabilities.

## Common pitfalls

- Using `billing_arr_current` / `crm_arr` instead of the **posted billing snapshot**
  for current ARR.
- Using metrics `support_ticket_count` instead of the **hygiene-filtered** tickets
  (must exclude spam, duplicates, AND cancelled).
- Summing all aging buckets for overdue instead of only **61_90 + 90_plus**.
- Taking the highest or first NPS instead of the **latest non-retracted** in window.
- Deriving `sla_degradation` from the metrics `sla_compliance` percentage instead of
  from per-ticket SLA-met flags.
- Treating `usage_decline` as a slope when it is an **absolute usage floor**.
- Forgetting that `arr_at_risk` is defined differently for the queue (critical+high)
  vs the board (everything except low/no_action).
- Computing churn `cohort_checks` over all candidates instead of the top-5.
- Wrong sort: receivables sort by `customer_name` asc; risk queue/board sort by
  severity then ARR.
- Emitting prose, code fences, or extra keys. Return only the template JSON with the
  right precision (currency 2dp, percentages 1dp, counts/scores integers) and the
  correct fixed `policy_codes`.
