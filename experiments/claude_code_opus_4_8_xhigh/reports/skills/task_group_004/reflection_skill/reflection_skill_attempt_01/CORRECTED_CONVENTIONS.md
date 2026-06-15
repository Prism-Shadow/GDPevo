# Corrected conventions (verified against gold) — internal scratch

## Data sources
- current_arr / current ARR = billing snapshot `billing_arr` as-of assessment date (NOT billing_arr_current round number, NOT crm_arr). uses_billing_arr_source=true; arr_source_code=REV-4.
- recognized monthly revenue (QBR) = metrics `recognized_revenue`. metric_sources.revenue label = `crm_closed_won` (canonical SoR label, even though queried from metrics).
- latest_nps = latest NON-RETRACTED response by response_date from /nps (field `score`). Ignore retracted; ignore metrics nps_score for retracted-survey months.

## Clean tickets (CONFIRMED)
- clean_ticket_count = tickets NOT spam AND NOT duplicate AND status != 'cancelled'. (Open tickets DO count.)
- QBR support_tickets per month = same clean-count rule, grouped by created_date month.
- QBR sla_compliance_pct per month = (clean tickets with first_response_sla_met) / clean tickets * 100, 1 decimal. (NOT metrics sla_compliance.)

## Overdue (CONFIRMED — biggest blind error)
- overdue_balance (risk/board) AND train_003 per-customer overdue = 61_90 + 90_plus ONLY (older buckets). NOT full non-current.
- train_003 trigger "older aging buckets" = 61_90 + 90_plus > 0 (shortlist of 13: 8 linked/5 unlinked). overdue_total = sum of (61_90+90_plus).
- AR row id = aging_id `AR-<account_id>-<quarter>`. Linking = EXACT AR customer_name == account legal_name; noise/near-dup names -> unlinked/null.

## Risk score model (additive, cap 100) — reproduces train_001 EXACT + train_005 levels/order
Triggers and weights:
- renewal_window (0<=days_to_renewal<=90): +25
- overdue_receivable (older-bucket overdue >0): +20
- nps_drop: +10
- sla_degradation: +15
- usage_decline: +15
- low_tenure_high_churn: +15 if tenure<=12, +10 if 13<=tenure<=18
- lifecycle renewal_risk: +5  (paused/implementation: +0 in chosen solution)
Triggers (definitions):
- renewal_window: 0 <= (renewal_date - assessment_date in days) <= 90
- overdue_receivable: (61_90+90_plus) > 0
- nps_drop: latest_nps < 40  OR  (latest_nps < 50 AND latest_nps <= min(earlier valid scores))
- sla_degradation: ANY clean ticket missed first_response_sla_met OR resolution_sla_met (clean-ticket SLA < 100%)
- usage_decline: latest-month (Jun) product_usage < 65  (absolute LOW level, NOT a trend!)
- low_tenure_high_churn: tenure <= 18
Bands: critical >=70, high >=45, medium >=30, low <30.
Tie-break / sort: risk_score DESC, then current_arr DESC.

## primary_action ladder (CONFIRMED all 13)
core (queue tasks, e.g. risk queue):
1. overdue_older>0 -> collections_followup
2. first_response SLA miss (fr<100%) -> technical_recovery
3. resolution SLA miss AND (nps_drop OR usage_decline) -> technical_recovery
4. renewal_window -> renewal_save
5. resolution SLA miss (alone) -> technical_recovery
6. else -> nurture_monitor
Board tasks: if risk_level == low -> no_action (override), next_touch_due_date=null.
(Risk-queue/shortlist tasks: assign best-fit remediation even to low risk; do NOT use no_action.)
executive_qbr was NEVER used in gold; blind over-used it.

## reason_codes (canonical order, append informational last)
order: renewal_window, overdue_receivable, nps_drop, sla_degradation, usage_decline, low_tenure_high_churn, [expansion_offset | clean_billings]
- expansion_offset: Q2 open expansion>0 (board/exposure tasks; in queue task only added to the overdue/critical account)
- clean_billings: overdue_older==0 (queue task positive signal)

## Aggregates
- arr_at_risk = sum current_arr where risk_level in {critical, high, medium} (NOT low). [Blind used {critical,high} only — matched train_001 by luck (no mediums) but FAILED train_005.]
- open_expansion_pipeline = sum Q2 open expansion (close_date in quarter, state==open) over all accounts.
- net_revenue_exposure = arr_at_risk - open_expansion_pipeline.
- portfolio counts (collections_count/technical_recovery_count) = count over ALL reviewed accounts by primary_action.
- segment counts: count accounts by `segment` field (Strategic/Enterprise).

## train_003 pipeline/ops (all CONFIRMED correct in blind)
- win_rate = won/(won+lost)*100, 1 dp. open_pipeline=sum open amounts. top_open_product_line=product_line with max summed OPEN amount.
- hr_headcount = sum all-region headcount; unpaid_claims_total = sum all-region unpaid_claims_amount.
- event_orders/event_revenue = top-line event fields (NOT completed_orders/product_revenue).
- overdue_followups sorted by customer_name asc; primary_action=collections_followup; due_date as given.

## Churn (train_004)
- training_rows=180, validation_rows=60, feature_count=19 (21 cols - customer_id - Churn).
- LogisticRegression with StandardScaler(numeric)+OneHotEncoder(categorical). USE REGULARIZATION C=0.1 -> validation accuracy 93.3% (band 90_plus). Default C=1.0 gives 91.7% (WRONG vs gold).
- tenure_coefficient_direction = negative.
- Exact probabilities / ranks 2-5 are NOT reliably reproducible (unspecified spec). Report band + direction confidently; probabilities are best-effort.
- average_probability_top5 = mean of the 5 reported probs (3 dp).
- cohort counts computed over the TOP5: past_due_shortlist_count = #InvoicePastDue==Yes; low_tenure_shortlist_count = #tenure<=18.
- outreach mapping (priority): InvoicePastDue=Yes->collections_followup/overdue_receivable; elif tenure<=18->renewal_save/low_tenure_high_churn; elif UsageTrendPct<0->renewal_save/usage_decline; elif NPSLast<30->technical_recovery/nps_drop; else nurture_monitor/clean_billings.

## QBR (train_002) specifics
- ticket_trend: improving if last-month clean count < first-month; worsening if >; flat if ==.
- agenda (exactly 4, ordered): partnership_overview, q2_metrics, [slot3], q3_initiatives.
  slot3 = technical_recovery if any SLA breach in period (fr or res miss) else performance_highlights; commercial_expansion if Q2 expansion pipeline>0 (replaces/added per task).
- review_owner = customer_success (default healthy); needs_technical_signoff keys off resolution-SLA breaches (Globex 0 -> false).
- metric_sources: revenue=crm_closed_won, support_tickets=support_export, sla_compliance=sla_report, nps=nps_survey.

## Policy codes (3-way enums) — LEARNED
- DEFAULT = the MIDDLE option of the three (14 of 15 codes).
  RS-6, REV-4, SUP-8, ACT-5, BORD-4, EXP-6, CAL-5, RCP-7, CM-5, PW-6, FS-4, MOD-7, PRB-4, DEP-5.
- EXCEPTION: outreach_mapping_code (churn) = OUT-2 (the FIRST option), not middle.
- Always include a top-level `policy_codes` object if the answer_template has one, even if the prompt key-list omits it.
