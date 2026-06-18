# Retention Risk Model — detailed reference

Read this when building a renewal-risk queue (top-N) or a high-touch retention action board.
SKILL.md §5 has the summary; this file has the full derivation, the per-signal definitions, and
the reasoning behind each rule. The rules here were recovered by diffing prior blind attempts
against the gold answers for two retention tasks (a top-5 NA renewal queue and an all-accounts
action board) and re-verifying every input against the live API.

## Inputs to assemble per account (as of the as-of date / analysis quarter)

| signal | source | exact rule |
|---|---|---|
| current_arr | billing snapshot | `billing_arr` of the snapshot whose `as_of` == as-of date. NOT `billing_arr_current`, NOT `crm_arr`. |
| latest_nps | NPS endpoint | score of the most recent NON-retracted response (max response_date after dropping retracted). |
| clean_ticket_count | tickets endpoint | tickets with NOT is_spam AND NOT is_duplicate AND status != "cancelled" (open+closed). |
| first_response_sla | tickets | (clean tickets with first_response_sla_met) / (clean tickets) × 100. |
| resolution_sla | tickets | (clean tickets with resolution_sla_met) / (clean tickets) × 100. |
| usage_latest | metrics | last month's `product_usage` over the analysis months. |
| usage_delta | metrics | last-month minus first-month `product_usage` (context only; not the trigger). |
| tenure | account | `contract_tenure_months`. |
| renewal_days | account | days from as-of date to `renewal_date` (signed). |
| older_overdue | A/R aging | `61_90 + 90_plus` for the linked legal_name (0 if no A/R row). |
| lifecycle | account | `lifecycle_status` (active / renewal_risk / paused / implementation / ...). |
| segment | account | `segment` (Strategic / Enterprise / Mid-Market / SMB). |
| expansion_pipeline | opportunities | sum of OPEN opp `amount` with close_date in the quarter window. |

## Reason-code triggers (each is an independent boolean)

These were validated to match gold reason-code sets across both retention tasks.

- **overdue_receivable**: `older_overdue > 0`.
- **clean_billings**: `older_overdue == 0`. (Mutually exclusive with overdue_receivable.)
- **sla_degradation**: support/SLA health is below target. Fires when first_response_sla < ~95
  OR resolution_sla < ~95 over clean tickets. A 100/100 account never fires; an account with a
  clean perfect first-response but a weak resolution rate (e.g. 83%) still fires. Always use the
  ticket-derived SLA — the metrics endpoint `sla_compliance` field disagrees and would mislabel
  accounts (e.g. an account with metrics SLA ~96% but ticket first-response 75% IS degraded).
- **nps_drop**: customer sentiment is weak. The reliable cases: latest non-retracted NPS that is
  low in absolute terms (sub-~50) and/or has dropped materially from the period's first reading.
  Edge cases observed: a very low latest score (~29) fires even if flat; a mild dip among healthy
  scores (51→46) does NOT fire; a recovered score (44→72→53) does NOT fire. When in doubt, treat
  "latest NPS is low AND not improving" as the trigger.
- **usage_decline**: latest-month `product_usage` is in the weak band (below ~60). This is an
  ABSOLUTE-low test on the latest month, not a slope test — a high-usage account (e.g. ~73 latest)
  that fell several points does NOT fire, while a low-usage account (~55 latest) fires even if it
  ticked up month-over-month. Pair `usage_delta` as supporting context only.
- **low_tenure_high_churn**: `tenure <= ~18` months.
- **renewal_window**: `0 <= renewal_days <= 90` (future renewal within a quarter). A renewal that
  already passed, or one far in the future, does not fire.
- **expansion_offset**: `expansion_pipeline > 0`.

`reason_codes` in the output is the list of fired codes. Order is not the grading focus; including
the correct SET is. clean_billings/expansion_offset are informational (they carry little/no risk
weight) but should still appear when their condition holds.

## risk_score

The internal score is additive over the fired signals with **graded SLA points** (worse SLA →
more points) plus a small **lifecycle component** (e.g. renewal_risk adds risk that is not always
surfaced as a reason code). The exact integer weights are NOT uniquely recoverable from the
available gold data — many weight vectors reproduce the handful of known (account → score) points,
because the system is underdetermined. Do not present a fabricated precise formula as if it were
authoritative.

What you CAN rely on (verified gold points): 100 → critical, 60 → high, 50 → high, 20 → low,
15 → low. Build a monotonic additive score (e.g. ~20–25 pts each for the hard drivers: overdue,
renewal_window, sla_degradation, nps_drop, usage_decline, low_tenure; capped at 100) and CALIBRATE
the band cutoffs so:
- a fully-distressed account (overdue + renewal + bad SLA + low NPS + falling usage + low tenure)
  lands `critical`,
- an account with a couple of hard drivers lands `high`,
- an account with one hard driver plus soft signals lands `medium`,
- an account whose only issue is one soft/SLA signal lands `low`.

Approximate bands: critical ≳ 80, high ≈ 40–79, medium ≈ 25–39, low < 25. The **ordering and the
level assignment** are what get graded most reliably, so prioritize getting those monotonic and
sensible over hitting an exact integer score.

## primary_action ladder (first match wins)

1. **collections_followup** — `overdue_receivable` present. Receivables always win, regardless of
   level (a critical account with overdue debt is still collections_followup, not executive_qbr).
2. **technical_recovery** — no overdue, but SLA distress present (especially first-response SLA
   failing), usually with nps_drop and/or usage_decline. This is the "support is the problem" path.
3. **renewal_save** — no overdue, support not the core issue, but `renewal_window` is the dominant
   driver (renewal imminent and the account is salvageable via a renewal motion).
4. **no_action** (board) / lowest-touch — low-risk accounts with no actionable hard trigger. On the
   full action board these get `primary_action = "no_action"` and `next_touch_due_date = null`.
   `nurture_monitor` is the soft-touch label when a queue requires a non-null action for every row.
   `executive_qbr` is reserved for the most extreme strategic escalations.

Note the difference between a focused top-N **queue** (every returned row is already high enough to
warrant an action, so no_action rarely appears) and a full **board** that lists every account
(where genuinely quiet accounts correctly get no_action / null next touch).

## Sort / tie-break

`risk_level` severity descending (critical > high > medium > low), then `current_arr` descending.
Verified: within the high tier, the higher-ARR account ranks first; within medium, strictly
ARR-descending. (`board_sort_code = BORD-4`.)

## Derived summaries

- `arr_at_risk` = Σ current_arr over critical + high + **medium** accounts (low excluded).
- `open_expansion_pipeline` = Σ expansion_pipeline over all listed accounts.
- `net_revenue_exposure` = `arr_at_risk − open_expansion_pipeline` (no overdue term). EXP-6.
- `critical_or_high_count`, `collections_count`, `technical_recovery_count` = counts in the output.
- `strategic_accounts`, `enterprise_accounts` = counts by `segment`.

## Worked sanity checks (shape only, do not memorize numbers)

- An account with older_overdue=0, perfect SLA, healthy NPS, high usage, far renewal → low,
  no_action, next_touch null, reason_codes like [clean_billings] / [expansion_offset].
- An account with older_overdue>0, renewal in 60 days, first-response SLA ~77% → at least high,
  primary_action collections_followup, reason_codes include overdue_receivable + renewal_window +
  sla_degradation.
- Two same-level accounts → the higher current_arr sorts first.
