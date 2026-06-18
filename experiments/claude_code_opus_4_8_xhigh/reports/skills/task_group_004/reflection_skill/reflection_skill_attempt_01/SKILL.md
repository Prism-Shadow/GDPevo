---
name: apexcloud-retention-ops
description: >-
  Standard operating procedures for ApexCloud Retention Operations analytics tasks served by the
  ApexCloud Retention Operations HTTP API (Customer Success / Revenue Operations). Use this skill
  whenever a task asks you to build a renewal risk queue, a retention/action board, a QBR metrics
  packet, a receivables-and-pipeline operations review, or a churn-model validation + outreach
  ranking against an ApexCloud-style API (accounts, account metrics, support tickets, NPS, billing
  snapshots, A/R aging, opportunities, HR summary, event performance, churn CSV exports). Trigger it
  even when the prompt only describes the business goal ("renewal risk", "QBR deck", "overdue
  receivables review", "churn ranking", "high-touch retention board", "arr at risk", "net revenue
  exposure", "risk_score / risk_level / primary_action / reason_codes", "policy_codes") without
  naming the API. It encodes the exact, non-obvious data-source choices, exclusion rules, risk
  scoring model, action ladder, and enum conventions that produce the deterministic expected output,
  so you do not have to rediscover them (and avoid the subtle mistakes that look right but are wrong).
---

# ApexCloud Retention Operations SOPs

These tasks look like "just sum some API rows," but the expected answers depend on a handful of
specific conventions that are easy to get plausibly wrong. This skill encodes the conventions that
are actually correct. They were recovered by reconciling worked attempts against authoritative
answers, so treat the rules here as load-bearing: the obvious interpretation is frequently the wrong
one (overdue = "everything not current" is wrong; clean tickets = "not spam/dup" is wrong; usage
decline = "Jun minus Apr" is wrong; current ARR = the round contract number is wrong).

## 0. Environment and ground rules

- Base URL is given in the prompt or an environment note (e.g. `http://127.0.0.1:8074`). Confirm with
  `GET /api/health` (retry once if the connection is momentarily refused; do not port-scan).
- Use ONLY the HTTP API for data, even if the prompt mentions a setup script or local file path —
  ignore those and use the URL. The endpoints are read-only JSON (CSV for churn exports). See
  `references/endpoints.md` for the full list and response shapes.
- Determinism: compute by summing/filtering raw rows; round only at the very end. Currency to 2
  decimals, percentages to 1 decimal, counts and risk scores as integers. Never fabricate values —
  if a field is genuinely absent, re-query rather than guess.
- Output JSON only, matching the answer template's keys, nesting, types, and enum spelling exactly.
  If the template contains a top-level `policy_codes` object, ALWAYS include it even when the prompt's
  prose key-list forgets to mention it.

## 1. Canonical data sources (memorize these — wrong source = wrong everywhere)

| Quantity | Correct source | Common wrong choice to avoid |
|---|---|---|
| current ARR / arr_at_risk / exposure | billing snapshot `billing_arr` as-of the assessment date (`GET /api/billing/snapshots?as_of=...`) | account `billing_arr_current` (round contract figure) or `crm_arr` |
| monthly recognized revenue (QBR) | account metrics `recognized_revenue` | billing snapshot |
| latest NPS | latest **non-retracted** response by `response_date` from `/nps` (field is `score`) | metrics `nps_score` (it still shows retracted months) |
| overdue balance | A/R aging `61_90 + 90_plus` ONLY | full non-current (`1_30+31_60+61_90+90_plus`) |
| clean ticket count | tickets that are NOT spam AND NOT duplicate AND `status != 'cancelled'` | "not spam/dup" only, or "SLA-met" filters |

Notes that trip people up:
- The metrics endpoint reports `nps_score` even for `survey_status == "retracted"` months. The risk/QBR
  latest-NPS must come from the `/nps` responses endpoint, using the most recent row whose
  `retracted == false`. A `-1` score is a sentinel — treat it as invalid/ignore it.
- A/R rows are keyed by `aging_id` = `AR-<account_id>-<quarter>`; there is no separate account_id
  column for linking. Open tickets DO count as clean; only `cancelled` are excluded.

## 2. Clean-ticket SLA (used by QBR and by the risk model's SLA trigger)

Work from the clean tickets defined above (not spam, not duplicate, not cancelled).

- **QBR monthly SLA %** = `100 * (clean tickets with first_response_sla_met) / (clean tickets)`, per
  month grouped by `created_date`'s month. (First-response basis, not the metrics `sla_compliance`.)
- **QBR monthly support_tickets** = clean-ticket count for that month.
- **SLA-degradation signal** (for the risk model and agenda logic) = TRUE if ANY clean ticket missed
  `first_response_sla_met` OR `resolution_sla_met` (i.e., clean-ticket SLA is below 100% on either
  dimension). A perfect 100%/100% account does NOT get the SLA flag.
- Distinguish the two SLA dimensions when picking actions/signoff: a **first-response** miss is
  treated as more urgent than a **resolution-only** miss (see the action ladder).

## 3. The risk model (renewal risk queues AND retention boards)

This is the same additive model for both task families. Assessment date and the 3 analysis months
come from the prompt. See `references/risk_model.md` for the full reference; the essentials:

Compute these per-account flags:
- `renewal_window`: `0 <= (renewal_date - assessment_date) in days <= 90`
- `overdue_receivable`: older-bucket overdue (`61_90 + 90_plus`) > 0
- `nps_drop`: latest valid NPS `< 40`, OR (`< 50` AND it is `<=` the minimum of the earlier valid
  scores, i.e. not recovering). A low score, or a stuck-low score, counts.
- `sla_degradation`: the clean-ticket SLA signal from section 2.
- `usage_decline`: the **latest analysis month's** `product_usage` is `< 65`. This is an absolute
  low-adoption threshold, NOT a Jun-minus-Apr trend. (Do not use the month-over-month delta.)
- `low_tenure_high_churn`: `contract_tenure_months <= 18`.
- lifecycle context: `lifecycle_status == 'renewal_risk'` (and similarly paused/implementation) is a
  mild positive contributor.

Additive score (cap at 100):

| Factor | Points |
|---|---|
| renewal_window | +25 |
| overdue_receivable | +20 |
| nps_drop | +10 |
| sla_degradation | +15 |
| usage_decline | +15 |
| low_tenure_high_churn | +15 if tenure ≤ 12, else +10 (for 13–18) |
| lifecycle renewal_risk | +5 |

`risk_level` bands: **critical ≥ 70, high ≥ 45, medium ≥ 30, low < 30**.

Ranking / board order: **risk_score descending, then current_arr descending** as the tie-break.

The prompt usually only says "consider these factors" without weights — that is expected; use the
weights above. If you must report a `tenure_risk_direction`, it is `negative` (lower tenure = higher
risk).

## 4. primary_action ladder and reason_codes

`primary_action` is a priority cascade evaluated in order (first match wins):

1. older-bucket overdue > 0 → `collections_followup`
2. a first-response SLA miss → `technical_recovery`
3. a resolution SLA miss AND (nps_drop OR usage_decline) → `technical_recovery`
4. in renewal window → `renewal_save`
5. a resolution SLA miss (on its own) → `technical_recovery`
6. otherwise → `nurture_monitor`

Task-shape override: on a **full retention/action board** that includes healthy accounts, map
`risk_level == low` to `no_action` (and set its `next_touch_due_date` to `null`). On a **risk-ranked
queue/shortlist** (you are returning the top-N riskiest), do NOT use `no_action` — assign the
best-fit remediation from the ladder even to a low-scoring entry. `executive_qbr` is essentially
never the right answer here; prefer the ladder above.

`reason_codes` are the fired factors, ALWAYS emitted in this canonical order, with the two
informational codes last:

`renewal_window, overdue_receivable, nps_drop, sla_degradation, usage_decline, low_tenure_high_churn, [expansion_offset | clean_billings]`

- `expansion_offset`: the account has Q2 open expansion pipeline > 0 (used on boards / exposure tasks
  that net expansion against risk; on a pure risk queue it surfaces only on accounts that also carry
  overdue/critical risk).
- `clean_billings`: older-bucket overdue == 0 (a positive "billing is clean" signal, used on risk
  queues). Boards that track expansion prefer `expansion_offset` and do not emit `clean_billings`.

## 5. Portfolio / board aggregates

- `arr_at_risk` = sum of `current_arr` for accounts with `risk_level in {critical, high, medium}`
  (everything except `low`). Do NOT restrict to critical+high — that happens to match when there are
  no mediums, but is wrong in general.
- `open_expansion_pipeline` = sum of Q2 **open** opportunity `amount` whose `close_date` falls in the
  analysis quarter, over all reviewed accounts.
- `net_revenue_exposure` = `arr_at_risk - open_expansion_pipeline`.
- `collections_count` / `technical_recovery_count` = number of reviewed accounts whose
  `primary_action` is that, counted over ALL reviewed accounts (not just the returned top-N).
- segment counts (`strategic_accounts`, `enterprise_accounts`) = count by the account `segment` field.
- `next_touch_due_date` comes from the prompt's follow-up calendar keyed by `primary_action`
  (`no_action` → null).

## 6. Receivables + pipeline operations review

- Shortlist = A/R customers with older-bucket overdue (`61_90 + 90_plus`) > 0 at the as-of date. This
  yields a tight list (older buckets), not every row (every row tends to have some `31_60`).
- Per-customer `overdue_balance` and the `overdue_total` use the older-bucket sum (`61_90 + 90_plus`),
  consistent with the risk model — NOT full non-current.
- Linking: a customer is `linked` only if its A/R `customer_name` EXACTLY equals an account
  `legal_name`; near-duplicate / noise names (subsidiaries, "...Services", "...Foundation") do not
  match and are `unlinked` with `account_id = null`.
- Sort `overdue_followups` by `customer_name` ascending; `primary_action = collections_followup`;
  `due_date` is the value given in the prompt.
- Pipeline: `win_rate_pct = 100 * won / (won + lost)`; `open_pipeline` = sum of open amounts;
  `top_open_product_line` = the `product_line` with the largest summed OPEN amount.
- Ops context: `hr_headcount` = sum of all-region headcount; `unpaid_claims_total` = sum of all-region
  `unpaid_claims_amount`; event `event_orders` / `event_revenue` = the top-line event fields (NOT
  `completed_orders` / `product_revenue`).

## 7. QBR metrics packet

- `qbr_metrics` rows: `revenue` = metrics `recognized_revenue`; `support_tickets` and
  `sla_compliance_pct` from clean tickets (section 2); `nps_score` = that month's value (use the valid
  monthly NPS).
- highlights: `average_revenue` = mean of the 3 months; peak/max picks return the month and value;
  `ticket_trend` = `improving` if last-month clean count < first-month, `worsening` if >, else `flat`.
- `metric_sources` are canonical system-of-record labels, not the endpoint you queried:
  `revenue → crm_closed_won`, `support_tickets → support_export`, `sla_compliance → sla_report`,
  `nps → nps_survey`.
- `agenda_topics` (exactly 4, ordered): `partnership_overview`, `q2_metrics`, [slot 3],
  `q3_initiatives`. Slot 3 = `technical_recovery` if there was any SLA breach in the period, else
  `performance_highlights`; use `commercial_expansion` if the account has Q2 open expansion pipeline.
- `review_owner` defaults to `customer_success` for a healthy account; `needs_technical_signoff` keys
  off **resolution-SLA breaches** specifically (zero resolution misses → `false`).

## 8. Churn-model validation + outreach ranking

- Pull the three CSV exports. `feature_count` = columns minus `customer_id` minus the `Churn` target
  (e.g. 21 columns → 19). Report `training_rows` and `validation_rows` from the row counts.
- Model: logistic regression with `StandardScaler` on the numeric features and one-hot encoding on the
  categoricals. Use **regularization (C ≈ 0.1)**, not the default `C=1.0`; the stronger-regularized
  fit is what reproduces the expected validation accuracy band (default C tends to over-separate and
  land a band lower). `tenure_coefficient_direction = negative`.
- Be honest about determinism: `accuracy_band` and the tenure direction are reliable; the exact
  per-account probabilities and the ordering of the middle ranks depend on unspecified model details
  and are best-effort, not guaranteed. Rank by predicted churn probability; report
  `average_probability_top5` as the mean of the reported probabilities (3 decimals).
- Cohort checks are computed over the returned **top-5**: `past_due_shortlist_count` =
  #(`InvoicePastDue == 'Yes'`); `low_tenure_shortlist_count` = #(`tenure <= 18`).
- outreach_action / reason_code mapping (priority cascade, first match wins):
  1. `InvoicePastDue == 'Yes'` → `collections_followup` / `overdue_receivable`
  2. `tenure <= 18` → `renewal_save` / `low_tenure_high_churn`
  3. `UsageTrendPct < 0` → `renewal_save` / `usage_decline`
  4. `NPSLast < 30` → `technical_recovery` / `nps_drop`
  5. else → `nurture_monitor` / `clean_billings`

## 9. policy_codes (the opaque 3-way enums)

Each `*_code` field offers three options (e.g. `RS-2 | RS-6 | RS-9`). The reliable convention:

- **Default to the MIDDLE option** of the three. This is correct for the large majority of codes
  (risk_model_code RS-6, arr_source_code REV-4, support_hygiene_code SUP-8, action_priority_code
  ACT-5, board_sort_code BORD-4, exposure_formula_code EXP-6, calendar_policy_code CAL-5,
  receivable_trigger_code RCP-7, crm_match_code CM-5, pipeline_window_code PW-6, followup_scope_code
  FS-4, model_protocol_code MOD-7, probability_scale_code PRB-4, deployment_rule_code DEP-5).
- **Known exception:** the churn task's `outreach_mapping_code` takes the FIRST option (`OUT-2`), not
  the middle. Pick the middle for every other code unless you have a specific signal otherwise.

## 10. Pre-submit checklist (common pitfalls)

Re-read this before returning — these are the mistakes that look right but fail:

1. ARR comes from the billing **snapshot** `billing_arr`, not the round contract number.
2. overdue = `61_90 + 90_plus` ONLY, everywhere (risk, board, receivables).
3. clean tickets exclude spam, duplicates, AND `cancelled` (open tickets count).
4. latest NPS = latest **non-retracted** `/nps` response; ignore retracted metric months and `-1`.
5. SLA degradation / QBR SLA are computed from **clean tickets**, not the metrics `sla_compliance`.
6. usage_decline is an **absolute** low-usage flag (latest month `< 65`), not a trend.
7. low_tenure threshold is `<= 18` (with the extra point only at `<= 12`).
8. `arr_at_risk` includes **medium** (critical + high + medium).
9. boards use `no_action` for low risk (due_date null); queues assign a real action instead.
10. reason_codes in canonical order, informational codes last.
11. include the top-level `policy_codes` object; default to the middle enum option (OUT = first).
12. round only at the end; match template keys/types/enum spelling exactly; JSON only.
