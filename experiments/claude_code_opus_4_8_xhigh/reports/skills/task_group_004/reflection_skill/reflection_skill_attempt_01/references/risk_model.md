# Risk model reference (renewal queues + retention boards)

Use this when a task asks for `risk_score`, `risk_level`, `primary_action`, `reason_codes`, or a
board/queue ordered by retention risk. The model below is additive and deterministic. The driver
script `scripts/retention_model.py` implements all of it — read it for the exact, runnable logic.

## Inputs per account (assessment date and 3 months from the prompt)

- `days_to_renewal = renewal_date - assessment_date` (in days)
- `overdue_older = ar.61_90 + ar.90_plus` (at the A/R as-of date)
- `latest_nps` = latest non-retracted `/nps` score (skip `-1` sentinels); keep the earlier valid
  scores too for the "not recovering" test
- `sla_miss_fr` / `sla_miss_res` = whether any clean ticket missed first_response / resolution SLA
- `usage_latest` = product_usage in the latest analysis month
- `tenure` = contract_tenure_months
- `lifecycle` = lifecycle_status
- `current_arr` = billing snapshot billing_arr (as-of date)
- `expansion` = sum of open opps with close_date in the quarter

## Flags

```
renewal_window         = 0 <= days_to_renewal <= 90
overdue_receivable     = overdue_older > 0
nps_drop               = latest_nps < 40
                         or (latest_nps < 50 and latest_nps <= min(earlier_valid_scores))
sla_degradation        = sla_miss_fr or sla_miss_res
usage_decline          = usage_latest < 65
low_tenure_high_churn  = tenure <= 18
lifecycle_bonus        = lifecycle == 'renewal_risk'  (paused/implementation similar, minor)
```

Why these (so you can adapt to wording variants): nps_drop is a low/stuck-low absolute signal, not a
month-over-month delta; usage_decline is a low-adoption absolute threshold, not a trend; sla flags
come from the ticket export, not the metrics `sla_compliance` field.

## Score (cap 100)

```
score  = 25*renewal_window
       + 20*overdue_receivable
       + 10*nps_drop
       + 15*sla_degradation
       + 15*usage_decline
       + (15 if tenure<=12 else 10) * low_tenure_high_churn
       +  5*lifecycle_bonus
score  = min(score, 100)
```

## Bands and ordering

```
risk_level = critical if score>=70 else high if score>=45 else medium if score>=30 else low
order: sort by (score desc, current_arr desc)
```

## primary_action (priority cascade)

```
if task is a full board and risk_level == low:  no_action   (next_touch_due_date = null)
elif overdue_older > 0:                          collections_followup
elif sla_miss_fr:                                technical_recovery
elif sla_miss_res and (nps_drop or usage_decline): technical_recovery
elif renewal_window:                             renewal_save
elif sla_miss_res:                               technical_recovery
else:                                            nurture_monitor
```

On a risk-ranked queue/shortlist (returning the top-N riskiest), skip the `no_action` branch and let
even low scorers receive the best-fit remediation action.

## reason_codes (canonical order)

Emit the fired flags in this order, then the informational codes:
```
renewal_window, overdue_receivable, nps_drop, sla_degradation, usage_decline,
low_tenure_high_churn, [expansion_offset if expansion>0], [clean_billings if overdue_older==0]
```
On boards/exposure tasks prefer `expansion_offset` (expansion>0) and omit `clean_billings`. On a
risk queue, `clean_billings` marks overdue_older==0; `expansion_offset` there appears mainly on
accounts that also carry overdue/critical risk.

## Aggregates

```
arr_at_risk            = sum(current_arr for risk_level in {critical, high, medium})
open_expansion_pipeline= sum(expansion over all reviewed accounts)
net_revenue_exposure   = arr_at_risk - open_expansion_pipeline
collections_count      = #accounts with primary_action == collections_followup (all reviewed)
technical_recovery_count = #accounts with primary_action == technical_recovery (all reviewed)
critical_or_high_count = #accounts with risk_level in {critical, high}
```

## Self-check

The model is intentionally weight-specific because the expected outputs are deterministic. After
computing, sanity-check: an account with an upcoming renewal + overdue + an SLA miss should land
critical/high; a healthy account (no overdue, perfect SLA, healthy NPS, high usage, long tenure)
should land low. If your low-risk accounts are getting non-trivial scores, re-check that usage_decline
is the absolute `< 65` rule and that sla_degradation is the any-miss rule (not the metrics field).
