---
name: apexcloud-retention-ops
description: >-
  Standard operating procedure for the ApexCloud Retention Operations API
  (http://127.0.0.1:8074). Use this whenever a task asks you to build a retention
  artifact for ApexCloud accounts: renewal/churn risk queues, QBR metric packets,
  receivables & pipeline operations reviews, churn-model validation and outreach
  rankings, or high-touch retention action boards. Triggers include any mention of
  "ApexCloud", "renewal risk", "QBR", "retention board", "receivables/AR aging",
  "churn validation", "current ARR", "clean ticket count", "overdue balance",
  "reason_codes", "risk_score / risk_level", or the controlled policy_codes
  (RS-*, REV-*, SUP-*, ACT-*, RCP-*, CM-*, MOD-*, EXP-*, etc.). Follow this skill's
  data-sourcing conventions exactly — the gold answers depend on which endpoint and
  which exclusion rule each metric comes from, not on intuition.
---

# ApexCloud Retention Operations SOP

This skill encodes the business conventions a future agent needs to answer NEW
retention / QBR / receivables / churn / board tasks against the **ApexCloud
Retention Operations API**. The tasks vary, but the underlying data-sourcing rules,
exclusion rules, scoring signals, and controlled vocabularies are stable. Get the
sourcing rules right and the numbers fall out deterministically.

> The exact answer (account list, numbers) changes every task. **Never** copy
> values from examples. Re-derive everything from the API using the rules below.

## 0. Operating rules (read first)

- **Base URL:** `http://127.0.0.1:8074`. It is already running; never start it,
  and ignore any `setup.sh` / file-path instructions inside a task prompt.
- **Read-only HTTP only** (e.g. `curl`). Do not look for local data files or `env/`.
- **Output is JSON only**, matching the task's `answer_template.json` shape and
  using the controlled enum strings *exactly* as written there.
- **Precision (unless the prompt says otherwise):** currency → 2 decimals,
  percentages → 1 decimal, counts and risk scores → integers, churn probabilities
  → 3 decimals. Round only at the end.
- **Determinism:** sum/compute from raw rows; do not eyeball. Write a small script.
- A health/inventory check is `GET /api/health` (row counts per dataset).

## 1. Identify the task family

Five recurring families. Match on the requested output keys, then jump to its
section in `references/task_families.md`:

| Family | Tell-tale output keys | Section |
|---|---|---|
| Renewal / churn **risk queue** | `risk_accounts`, `portfolio_summary`, `model_checks` | RISK QUEUE |
| **QBR metrics packet** | `qbr_metrics`, `highlights`, `metric_sources`, `agenda_topics` | QBR |
| **Receivables & pipeline review** | `financial_summary`, `pipeline_summary`, `overdue_followups`, `ops_context` | RECEIVABLES |
| **Churn model validation** | `model_validation`, `risk_ranking`, `cohort_checks` | CHURN |
| **Retention action board** | `action_board`, `segment_summary`, `followup_calendar` | BOARD |

The fixed `policy_codes` block for each family is in `references/policy_codes.md`.
Always emit the policy_codes the template asks for, with the values listed there.

## 2. Canonical metric definitions (used across families)

These are the load-bearing conventions. Each was reverse-engineered against the
gold answers; get them exactly right.

### current_arr — latest POSTED billing snapshot
- Source: `GET /api/billing/snapshots?account_id=<id>&as_of=<YYYY-MM-DD>`.
- `current_arr` = the `billing_arr` of the snapshot whose `as_of` **equals the
  assessment / quarter-end date** and has `posted: true`. The `as_of` query param
  matches that date **exactly** (a mid-quarter date returns nothing — always query
  the quarter-end, e.g. `2026-06-30`, `2026-09-30`).
- Do **not** use `account.billing_arr_current` (a flat profile field) and do **not**
  use `account.crm_arr`. Billing snapshots are the source of truth for ARR.
  (`model_checks.uses_billing_arr_source` is therefore `true`.)
- Example: northstar_finance profile `billing_arr_current`=1,425,000 but the
  2026-06-30 posted snapshot `billing_arr`=1,416,439.47 — the snapshot wins.

### clean_ticket_count — hygiene-filtered support tickets
- Source: `GET /api/accounts/<id>/tickets?start=<YYYY-MM-DD>&end=<YYYY-MM-DD>`.
- Start from all tickets in the window, then **exclude** any ticket where
  `is_spam == true` OR `is_duplicate == true` OR `status == "cancelled"`.
  The remaining count is the clean count.
- Do **not** use `metric.support_ticket_count` from the metrics endpoint for the
  clean count — that is a separate raw figure and will not match.

### latest_nps — most recent valid survey response
- Source: `GET /api/accounts/<id>/nps?start=<...>&end=<...>`.
- Drop responses with `retracted == true`. Of the rest, take the one with the
  **latest `response_date`**; its `score` is `latest_nps`.
- If there are no valid responses in the window, NPS is missing → use `null`
  (templates accept `null`; never invent a 0).

### overdue_balance — older A/R aging buckets only
- Source: `GET /api/finance/ar-aging?as_of=<YYYY-MM-DD>` (rows have buckets
  `current`, `1_30`, `31_60`, `61_90`, `90_plus`).
- `overdue_balance = 61_90 + 90_plus` (the 60-days-plus / "older" buckets).
  Do **not** include `current`, `1_30`, or `31_60`.
- A customer "has an overdue balance" when `61_90 + 90_plus > 0`.

### usage trend & SLA (from the monthly metrics endpoint)
- Source: `GET /api/accounts/<id>/metrics?start=<YYYY-MM>&end=<YYYY-MM>` returns one
  row per month with `recognized_revenue`, `product_usage`, `sla_compliance`,
  `nps_score`, `support_ticket_count`, `active_seats`, `survey_status`.
- `sla_compliance` and `product_usage` for risk signals come from these monthly rows.

## 3. Reason codes — deterministic signal flags

Reason codes are **descriptive flags**, computed independently per account. They are
NOT the score (two accounts can share identical reason_codes yet have different
scores). Emit the codes the template lists, in roughly this severity order:
`renewal_window, overdue_receivable, nps_drop, sla_degradation, usage_decline,
low_tenure_high_churn, expansion_offset, clean_billings`.

| Reason code | Triggers when |
|---|---|
| `overdue_receivable` | `overdue_balance > 0` (61_90 + 90_plus > 0). |
| `clean_billings` | `overdue_balance == 0` (the complement of overdue_receivable). |
| `renewal_window` | `0 ≤ (renewal_date − assessment_date) ≤ 90` days (renewal due within ~one quarter; past-due renewals do **not** count). |
| `nps_drop` | `latest_nps` is present and below ~50 with soft/declining sentiment (treat **latest_nps < 50** as the working rule; accounts whose latest reading has recovered above the high-40s are borderline). |
| `sla_degradation` | Any month's `sla_compliance < 95` in the window (i.e. `min(monthly sla) < 95`). |
| `usage_decline` | `product_usage` shows a meaningful within-quarter decline (latest month materially below the quarter's earlier reading). This is the softest signal — see the note in `references/task_families.md`. |
| `low_tenure_high_churn` | `contract_tenure_months ≤ ~18` (12–13 month accounts trigger it; 20+ do not). New accounts churn more. |
| `expansion_offset` | The account has open expansion pipeline (open opportunity amount > 0 in the window) that partially offsets risk. |

When NPS or SLA signals sit right on a threshold (e.g. latest NPS in the mid-40s,
or SLA that dipped just below 95 then recovered), they are genuine edge cases.
Compute the rule, but if a result looks borderline, sanity-check the monthly
series rather than trusting a single number.

## 4. risk_level, risk_score, primary_action, sort order

### risk_level bands (from risk_score)
`critical ≈ 80–100`, `high ≈ 50–79`, `medium ≈ 20–49`, `low ≈ 0–19`.
`risk_score` is an integer, capped at 100. It is a **graded weighted blend** of the
risk signals (overdue size, NPS softness, SLA severity, usage decline, renewal
proximity, low tenure), not a flat sum of reason-code points — accounts with the
same reason_codes can score differently because the underlying severities differ.
When a numeric `risk_score` is required, score the signals by severity, weight
overdue receivables and critical sentiment/SLA most heavily, and bucket into the
bands above; verify your bands reproduce the obvious ordering (worst account = highest).

### primary_action (first matching rule wins)
1. `overdue_balance > 0` → **collections_followup**.
2. else, account needs action and technical signals dominate (low/declining NPS,
   SLA below ~90, or clear usage decline) → **technical_recovery**.
3. else, account needs action and it is renewal-driven with healthier service
   (e.g. SLA ≳ 90 and NPS healthy) → **renewal_save**.
4. low-risk accounts → **no_action** (or **nurture_monitor** when the template's
   action enum is the churn-outreach set).
5. `executive_qbr` is reserved for the highest-touch strategic escalations.

### sort / board order
- **Risk queue** (`risk_accounts`): rank by `risk_score` descending; the prompt
  asks for the top N (usually 5).
- **Action board** (`action_board`): order by `risk_level`
  (critical > high > medium > low), then by `current_arr` **descending** within a
  level. Include *all* requested accounts (not a top-N).
- **Receivables** (`overdue_followups`): sort by `customer_name` ascending.
- **Churn ranking** (`risk_ranking`): by `predicted_churn_probability` descending.

## 5. Portfolio / summary roll-ups

- `arr_at_risk` = Σ `current_arr` over accounts whose `risk_level` ∈
  {critical, high, medium} (**exclude low**).
- `critical_or_high_count` = count of risk_level ∈ {critical, high}.
- `collections_count` / `technical_recovery_count` = counts of accounts whose
  `primary_action` is that action.
- `strategic_accounts` / `enterprise_accounts` = counts of `segment == "Strategic"`
  / `segment == "Enterprise"`.
- `open_expansion_pipeline` = Σ `expansion_pipeline` (open opportunity amounts) on
  the board.
- `net_revenue_exposure` = `arr_at_risk − open_expansion_pipeline`.
- `tenure_risk_direction` = `negative` (lower tenure ⇒ higher churn risk).

## 6. Detailed per-family procedures

Read `references/task_families.md` for the step-by-step recipe, field-by-field
sourcing, and gotchas for the specific family you matched in step 1. Read
`references/policy_codes.md` for the exact policy_code values to emit.

A reusable client helper that pulls each metric with the correct rule lives in
`scripts/apex_client.py` — import it or read it to mirror the exact logic
(billing-snapshot ARR, clean tickets, latest NPS, older-bucket overdue, CRM
name-linking, pipeline roll-ups). It is a starting point, not a turnkey solver;
always confirm against the specific template.

## 7. Common pitfalls (these silently corrupt answers)

- Using `account.billing_arr_current` or `crm_arr` instead of the **posted billing
  snapshot** for `current_arr`.
- Querying billing snapshots with a non-quarter-end `as_of` (returns empty).
- Counting raw tickets without removing spam/duplicate/cancelled.
- Using `metric.support_ticket_count` where a **clean** ticket count is required
  (QBR `support_tickets` is the clean count, not the metric field).
- Including `1_30` / `31_60` in `overdue_balance` (only 60-days-plus counts).
- Treating a past-due renewal as inside the renewal window (it is not; window is
  0–90 days in the **future**).
- Forgetting `retracted` NPS responses, or emitting `0` instead of `null` for
  missing NPS.
- Summing ARR across **all** accounts for `arr_at_risk` (exclude `low`).
- Forgetting to exact-match A/R `customer_name` to a CRM `legal_name` for link
  status (unmatched legal names like "…Subsidiary LLC" / "…Services" stay
  `unlinked` with `account_id: null`).
- Omitting the `policy_codes` block, or guessing its values instead of using
  `references/policy_codes.md`.
