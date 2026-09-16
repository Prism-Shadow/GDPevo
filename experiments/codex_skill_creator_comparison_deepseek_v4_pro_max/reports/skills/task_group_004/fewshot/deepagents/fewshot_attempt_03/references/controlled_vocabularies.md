# Controlled Vocabularies

Every enumerated field in ApexCloud retention outputs must use exactly one of the values listed below. Do not invent new labels.

## Risk Levels

Used in `risk_level` fields:

- `critical`
- `high`
- `medium`
- `low`

Assignment rule: derive from the risk score. Critical = highest risk tier (score >= 80), high = (60-79), medium = (30-59), low = (<30). Scale to a 0-100 integer range.

## Primary Actions

Used in `primary_action` fields:

- `executive_qbr` — executive QBR escalation needed
- `collections_followup` — overdue receivables follow-up
- `technical_recovery` — SLA/product health intervention
- `renewal_save` — renewal is approaching with risk signals
- `nurture_monitor` — monitor, low risk but stay engaged
- `no_action` — no immediate action needed

Selection priority (highest to lowest by business urgency):
1. `collections_followup` — if overdue_balance > 0
2. `technical_recovery` — if SLA degradation or usage decline is the dominant signal and no overdue balance
3. `renewal_save` — if renewal window is the dominant signal
4. `executive_qbr` — if a strategic account needs escalation (Strategic segment + critical/high risk)
5. `nurture_monitor` — moderate risk but no acute signals
6. `no_action` — low risk with no actionable signals

## Reason Codes

Used in `reason_codes` arrays:

- `overdue_receivable` — account has overdue A/R balance
- `low_tenure_high_churn` — low contract tenure, statistically higher churn risk
- `sla_degradation` — SLA compliance below acceptable threshold or trending down
- `nps_drop` — latest NPS is low or declining
- `usage_decline` — product usage trending downward
- `renewal_window` — renewal date falls within the analysis period or shortly after
- `expansion_offset` — open expansion pipeline partially offsets risk
- `clean_billings` — no billing/receivables issues

Include every applicable reason code for each account. Order them by severity: overdue_receivable first, then low_tenure_high_churn, sla_degradation, nps_drop, usage_decline, renewal_window, expansion_offset, clean_billings last.

## Outreach Actions (Churn Model)

Used in `outreach_action` fields for the churn model task:

- `renewal_save`
- `technical_recovery`
- `collections_followup`
- `nurture_monitor`

## Metric Sources

Used in `metric_sources` objects and `source_enum` fields:

- `crm_closed_won` — revenue from CRM closed-won data
- `support_export` — support ticket counts from ticket export
- `sla_report` — SLA compliance from SLA reporting system
- `nps_survey` — NPS from survey system
- `billing_snapshot` — data from billing snapshots
- `ar_aging` — A/R aging data
- `pipeline_crm` — pipeline data from CRM
- `event_dashboard` — event performance dashboard
- `hr_report` — HR reporting system

For QBR metrics: `revenue` should use `crm_closed_won` (recognized_revenue comes from the metrics endpoint), `support_tickets` uses `support_export`, `sla_compliance` uses `sla_report`, and `nps` uses `nps_survey`.

## Review Owners

Used in `review_owner` fields:

- `solutions_engineering`
- `customer_success`
- `finance_ops`

For standard QBR packets, use `customer_success`.

## Agenda Topics

Used in `agenda_topics` arrays:

- `partnership_overview`
- `q2_metrics`
- `performance_highlights`
- `q3_initiatives`
- `technical_recovery`
- `commercial_expansion`

Choose exactly four. For a standard QBR, the canonical set is: `partnership_overview`, `q2_metrics`, `technical_recovery`, `q3_initiatives`. Adjust based on account context if performance highlights or commercial expansion are more relevant than technical recovery.

## Ticket Trend

Used in `ticket_trend` fields:

- `improving` — ticket count decreased over the period
- `worsening` — ticket count increased over the period
- `flat` — ticket count stayed the same

Compare the first month's clean ticket count to the last month's.

## Link Status

Used in `link_status` fields:

- `linked` — A/R customer matched to a CRM account
- `unlinked` — no match found; `account_id` must be `null`

## Accuracy Band

Used in `accuracy_band` fields:

- `below_70`
- `70_to_79`
- `80_to_89`
- `90_plus`

## Tenure / Coefficient Direction

Used in `tenure_risk_direction` and `tenure_coefficient_direction` fields:

- `negative` — tenure negatively correlated with risk (higher tenure = lower risk)
- `positive` — tenure positively correlated with risk
- `not_assessed` — not evaluated in this analysis
- `zero` — no meaningful correlation

In the ApexCloud domain, tenure is consistently negatively correlated with churn, so use `"negative"`.

## Policy Codes

Each task output includes a `policy_codes` block with codes that trace the methodology used. Select the single code that best describes the approach taken.

### Risk Model Codes (risk_model_code)

Appears in: Renewal Risk Queue, Retention Board.

- `RS-2` — Revenue-weighted risk model with NPS primary
- `RS-6` — Multi-factor composite risk model (renewal timing, revenue, NPS, SLA, usage, receivables, tenure)
- `RS-9` — Usage-centric risk model

Select `RS-6` when the analysis uses a balanced multi-factor approach across all available signals. This is the default for comprehensive retention analysis.

### ARR Source Codes (arr_source_code)

Appears in: Renewal Risk Queue, Retention Board.

- `REV-1` — CRM ARR as primary source
- `REV-4` — Billing snapshot ARR as primary source
- `REV-8` — Blended ARR (CRM + billing average)

Select `REV-4` when using `billing_arr_current` or the most recent billing snapshot as the authoritative ARR source.

### Support Hygiene Codes (support_hygiene_code)

Appears in: Renewal Risk Queue, Retention Board.

- `SUP-3` — Raw ticket count (includes spam/duplicates)
- `SUP-8` — Clean ticket count (excludes spam/duplicates)
- `SUP-9` — SLA-only assessment (ticket count not used)

Select `SUP-8` when filtering out duplicate and spam tickets.

### Action Priority Codes (action_priority_code)

Appears in: Renewal Risk Queue, Retention Board.

- `ACT-1` — Collections-first priority
- `ACT-5` — Risk-weighted priority (collections > technical > renewal)
- `ACT-7` — Renewal-first priority

Select `ACT-5` when using the standard priority ordering: collections, then technical recovery, then renewal save.

### Receivable Trigger Codes (receivable_trigger_code)

Appears in: Receivables Review.

- `RCP-4` — Only 90+-day overdue triggers
- `RCP-7` — All overdue buckets (31-60, 61-90, 90+) trigger
- `RCP-9` — Current + all aging buckets trigger

Select `RCP-7` when using the standard overdue definition (31_60 + 61_90 + 90_plus).

### CRM Match Codes (crm_match_code)

Appears in: Receivables Review.

- `CM-2` — Exact legal name match only
- `CM-5` — Legal name + alias fuzzy match
- `CM-8` — Manual review match

Select `CM-5` when matching against both `legal_name` and `account_aliases`.

### Pipeline Window Codes (pipeline_window_code)

Appears in: Receivables Review.

- `PW-3` — Calendar quarter window
- `PW-6` — Date-range window (close_date within analysis period)
- `PW-9` — Rolling 90-day window

Select `PW-6` when filtering by close_date within the specified analysis date range.

### Followup Scope Codes (followup_scope_code)

Appears in: Receivables Review.

- `FS-1` — Top-10 overdue only
- `FS-4` — All overdue with balance above zero
- `FS-8` — All customers regardless of balance

Select `FS-4` when including every A/R entry with non-zero overdue balance for the as-of quarter.

### Model Protocol Codes (model_protocol_code)

Appears in: Churn Model.

- `MOD-2` — Train/validation split validation only
- `MOD-7` — Standard model validation protocol (train/validation + feature audit + accuracy)
- `MOD-9` — Full cross-validation protocol

Select `MOD-7` when performing standard validation with row counts, feature count, and accuracy computation.

### Probability Scale Codes (probability_scale_code)

Appears in: Churn Model.

- `PRB-1` — Raw model scores (uncalibrated)
- `PRB-4` — Calibrated probabilities (0-1 scale, 3 decimal)
- `PRB-8` — Logarithmic scale

Select `PRB-4` when outputting probabilities as 0-1 scaled values with 3 decimal precision.

### Deployment Rule Codes (deployment_rule_code)

Appears in: Churn Model.

- `DEP-3` — Threshold-based deployment (0.5 cutoff)
- `DEP-5` — Ranked deployment (top-N by probability)
- `DEP-9` — Ensemble deployment

Select `DEP-5` when ranking candidates by descending churn probability and taking top 5.

### Outreach Mapping Codes (outreach_mapping_code)

Appears in: Churn Model.

- `OUT-2` — Probability-to-action direct mapping
- `OUT-6` — Probability + cohort signal mapping
- `OUT-8` — Manual outreach assignment

Select `OUT-2` when mapping churn probability directly to outreach actions.

### Board Sort Codes (board_sort_code)

Appears in: Retention Board.

- `BORD-1` — Alphabetical sort
- `BORD-4` — Risk-weighted descending sort (critical > high > medium > low; ARR tiebreaker)
- `BORD-8` — Segment-tiered sort

Select `BORD-4` when ranking by risk severity with ARR as tiebreaker.

### Exposure Formula Codes (exposure_formula_code)

Appears in: Retention Board.

- `EXP-2` — ARR minus expansion (net exposure)
- `EXP-6` — ARR at risk = sum of ARR for critical/high accounts; net exposure = ARR at risk minus expansion pipeline
- `EXP-9` — Full exposure including pipeline offsets

Select `EXP-6` when computing arr_at_risk from critical/high accounts and net_revenue_exposure as arr_at_risk minus open_expansion_pipeline.

### Calendar Policy Codes (calendar_policy_code)

Appears in: Retention Board.

- `CAL-3` — Fixed calendar (hardcoded dates)
- `CAL-5` — Task-specified calendar (dates from prompt)
- `CAL-7` — Computed calendar (offset from analysis date)

Select `CAL-5` when using the due dates explicitly provided in the task prompt.

## Segmentation

Used in `segment` output fields:

- `Strategic`
- `Enterprise`
- `Mid-Market`
- `SMB`

For `segment_summary` in the retention board:
- `strategic_accounts`: count of accounts with segment `Strategic`
- `enterprise_accounts`: count of accounts with segment `Enterprise` or `Mid-Market` or `SMB`
