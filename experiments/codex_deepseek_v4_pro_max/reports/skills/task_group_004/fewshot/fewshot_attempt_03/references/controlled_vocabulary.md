## Controlled Vocabulary for Retention Operations

Every output label must be chosen from these exact enumerated values. Do not invent or approximate labels.

### Risk Levels
`critical`, `high`, `medium`, `low`

### Primary Actions
| Enum | Meaning |
|------|---------|
| `executive_qbr` | Schedule executive business review |
| `collections_followup` | Pursue overdue receivables |
| `technical_recovery` | Address SLA/compliance/usage issues |
| `renewal_save` | Proactive retention intervention |
| `nurture_monitor` | Watch; no immediate action |
| `no_action` | No action required |

### Reason Codes (Risk & Churn Drivers)
| Enum | Meaning |
|------|---------|
| `overdue_receivable` | Account has overdue balance |
| `low_tenure_high_churn` | Low tenure correlates with high churn probability |
| `sla_degradation` | SLA compliance below acceptable threshold |
| `nps_drop` | NPS score declined period-over-period |
| `usage_decline` | Product usage index trending down |
| `renewal_window` | Account is within its renewal window |
| `expansion_offset` | Expansion pipeline partially offsets risk |
| `clean_billings` | No billing/receivables issues |

### Metric Sources (for QBR source attribution)
`crm_closed_won`, `support_export`, `sla_report`, `nps_survey`, `billing_snapshot`, `ar_aging`, `pipeline_crm`, `event_dashboard`, `hr_report`

### Ticket Trend
`improving`, `worsening`, `flat`

### Review Owner
`solutions_engineering`, `customer_success`, `finance_ops`

### Agenda Topics
`partnership_overview`, `q2_metrics`, `performance_highlights`, `q3_initiatives`, `technical_recovery`, `commercial_expansion`

### Accuracy Band (Churn Model)
`below_70`, `70_to_79`, `80_to_89`, `90_plus`

### Direction Labels
`negative`, `positive`, `zero`, `not_assessed`

### Link Status (AR ↔ CRM)
`linked`, `unlinked`

### Precision Rules
- **Currency** (ARR, revenue, balances, pipeline amounts): exactly 2 decimal places
- **Percentages** (win rate, SLA, accuracy): exactly 1 decimal place
- **Counts** (tickets, accounts, headcount): integers
- **Risk scores**: integers
- **Churn probabilities**: exactly 3 decimal places
- **NPS scores**: integers

### Policy Code Conventions
Policy codes appear as pipe-delimited options in answer templates; select the single correct code from the options based on the data. Each code follows a prefix-number pattern (e.g. RS-6, REV-4, SUP-8, ACT-5).
