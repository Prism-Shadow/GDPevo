# ApexCloud Controlled Vocabulary

Every output field that accepts a controlled value must use one of the exact strings listed below. Never invent or approximate these labels.

## Risk Levels

- `critical`
- `high`
- `medium`
- `low`

## Primary Actions

- `executive_qbr` — Schedule an executive business review
- `collections_followup` — Pursue overdue receivables
- `technical_recovery` — Address SLA, usage, or technical health issues
- `renewal_save` — Proactive renewal intervention
- `nurture_monitor` — Watch and maintain; low immediate risk
- `no_action` — No intervention required

## Outreach Actions (churn ranking)

- `renewal_save`
- `technical_recovery`
- `collections_followup`
- `nurture_monitor`

## Reason Codes

- `overdue_receivable` — Account has past-due balance (31+ days)
- `low_tenure_high_churn` — Tenure <= 24 months, elevated churn risk
- `sla_degradation` — SLA compliance below acceptable threshold or declining
- `nps_drop` — Latest NPS is lower than the prior score in the period
- `usage_decline` — Product usage declined across the analysis period
- `renewal_window` — Renewal date falls within or near the analysis window
- `expansion_offset` — Open expansion pipeline partially offsets risk
- `clean_billings` — No overdue balance; billing in good standing

Reason codes are additive: include all that apply to the account. Order them by severity: `overdue_receivable` first if present, then `low_tenure_high_churn`, then `sla_degradation`, `nps_drop`, `usage_decline`, `renewal_window`, `expansion_offset`, and `clean_billings` last and only if no negative billing codes apply.

## Metric Sources

- `crm_closed_won`
- `support_export`
- `sla_report`
- `nps_survey`
- `billing_snapshot`
- `ar_aging`
- `pipeline_crm`
- `event_dashboard`
- `hr_report`

## Review Owners

- `solutions_engineering`
- `customer_success`
- `finance_ops`

## Agenda Topics

- `partnership_overview`
- `q2_metrics`
- `performance_highlights`
- `q3_initiatives`
- `technical_recovery`
- `commercial_expansion`

## Ticket Trend

- `improving`
- `worsening`
- `flat`

## Accuracy Bands

- `below_70`
- `70_to_79`
- `80_to_89`
- `90_plus`

## Tenure Risk Direction

- `negative` — Younger accounts carry higher risk
- `positive` — Older accounts carry higher risk
- `not_assessed`
- `zero` — No direction detected

## Link Status

- `linked`
- `unlinked`

## Policy Codes

### Risk Model Codes

- `RS-2`
- `RS-6`
- `RS-9`

### ARR Source Codes

- `REV-1`
- `REV-4`
- `REV-8`

### Support Hygiene Codes

- `SUP-3`
- `SUP-8`
- `SUP-9`

### Action Priority Codes

- `ACT-1`
- `ACT-5`
- `ACT-7`

### Receivable Trigger Codes

- `RCP-4`
- `RCP-7`
- `RCP-9`

### CRM Match Codes

- `CM-2`
- `CM-5`
- `CM-8`

### Pipeline Window Codes

- `PW-3`
- `PW-6`
- `PW-9`

### Followup Scope Codes

- `FS-1`
- `FS-4`
- `FS-8`

### Model Protocol Codes

- `MOD-2`
- `MOD-7`
- `MOD-9`

### Probability Scale Codes

- `PRB-1`
- `PRB-4`
- `PRB-8`

### Deployment Rule Codes

- `DEP-3`
- `DEP-5`
- `DEP-9`

### Outreach Mapping Codes

- `OUT-2`
- `OUT-6`
- `OUT-8`

### Board Sort Codes

- `BORD-1`
- `BORD-4`
- `BORD-8`

### Exposure Formula Codes

- `EXP-2`
- `EXP-6`
- `EXP-9`

### Calendar Policy Codes

- `CAL-3`
- `CAL-5`
- `CAL-7`

## Product Plans

- `Strategic`
- `Enterprise`
- `Scale`
- `Growth`
- `Starter`

## Segments

- `Strategic`
- `Enterprise`
- `Mid-Market`

## Regions

- `North America`
- `EMEA`
- `APAC`

## Lifecycle Status

- `active`
- `churned`
