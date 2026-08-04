## Controlled Vocabularies

Every enumerable field must use one of the values listed below. Never invent a new label.

### Risk Levels

- `critical`
- `high`
- `medium`
- `low`

### Primary Actions

- `executive_qbr` — Escalate to executive quarterly business review
- `collections_followup` — Pursue overdue receivables
- `technical_recovery` — Engage technical team to recover account health
- `renewal_save` — Prioritize for renewal intervention
- `nurture_monitor` — Watch and maintain, no escalated action needed
- `no_action` — No intervention required

### Reason Codes

- `overdue_receivable` — Account has overdue A/R balance
- `low_tenure_high_churn` — Low tenure with elevated churn probability
- `sla_degradation` — SLA compliance has degraded
- `nps_drop` — NPS score has dropped materially
- `usage_decline` — Product usage is declining
- `renewal_window` — Account is within its renewal window
- `expansion_offset` — Expansion pipeline offsets at-risk revenue
- `clean_billings` — No billing or receivable issues detected

### Ticket Trend

- `improving`
- `worsening`
- `flat`

### Metric Sources

- `crm_closed_won`
- `support_export`
- `sla_report`
- `nps_survey`
- `billing_snapshot`
- `ar_aging`
- `pipeline_crm`
- `event_dashboard`
- `hr_report`

### Review Owner

- `solutions_engineering`
- `customer_success`
- `finance_ops`

### Agenda Topics

- `partnership_overview`
- `q2_metrics`
- `performance_highlights`
- `q3_initiatives`
- `technical_recovery`
- `commercial_expansion`

### Link Status

- `linked`
- `unlinked`

### Accuracy Band

- `below_70`
- `70_to_79`
- `80_to_89`
- `90_plus`

### Tenure Coefficient / Risk Direction

- `negative` — Longer tenure correlates with lower risk
- `positive` — Longer tenure correlates with higher risk
- `zero` — No tenure effect detected
- `not_assessed` — Relationship was not evaluated

### Outreach Action (churn model)

- `renewal_save`
- `technical_recovery`
- `collections_followup`
- `nurture_monitor`

### Board Sort Order

Standard retention board order: accounts are ranked by composite risk (overdue + SLA + NPS + usage + tenure) with critical accounts first, then high, then medium.
