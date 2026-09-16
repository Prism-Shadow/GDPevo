## Controlled Vocabularies

### Risk Levels

| Value | Meaning |
|-------|---------|
| `critical` | Immediate action required; multi-signal failure |
| `high` | Strong risk signals; action needed this quarter |
| `medium` | Moderate concern; needs scheduled touch |
| `low` | Manageable; monitor or light-touch nurture |

### Primary Actions

| Value | When to Use |
|-------|------------|
| `collections_followup` | Account has a non-zero overdue balance (> 0.00) |
| `executive_qbr` | Strategic account with renewal + revenue at risk |
| `technical_recovery` | SLA breaches dominate; no overdue balance |
| `renewal_save` | Renewal is near + low tenure or NPS issues |
| `nurture_monitor` | Low risk; watch and maintain relationship |
| `no_action` | Very low risk; no active intervention needed |

**Priority tiebreaker**: `collections_followup` > `executive_qbr` > `technical_recovery` > `renewal_save` > `nurture_monitor` > `no_action`

### Reason Codes

| Value | Trigger |
|-------|---------|
| `overdue_receivable` | Overdue balance > 0.00 |
| `low_tenure_high_churn` | contract_tenure_months <= 24 AND churn risk factors present |
| `sla_degradation` | Any month's SLA compliance < 90.0% in the period |
| `nps_drop` | Latest NPS < 50 or month-over-month NPS decline >= 10 points |
| `usage_decline` | product_usage shows a downward trend across the period |
| `renewal_window` | renewal_date is within 90 days of the assessment date |
| `expansion_offset` | An open expansion opportunity exists for the account in the period |
| `clean_billings` | Overdue balance == 0.00 (positive signal, used when no negative billing signals) |

### Risk Model Codes

| Value | Meaning |
|-------|---------|
| `RS-2` | Rule-based scoring, high-volume (many signals) |
| `RS-6` | Composite scoring: ARR-weighted with tenure, NPS, SLA, overdue, usage, renewal |
| `RS-9` | Statistical model scoring (churn probability via logistic regression) |

### ARR Source Codes

| Value | Meaning |
|-------|---------|
| `REV-1` | CRM-reported ARR (crm_arr from /api/accounts) |
| `REV-4` | Billing snapshot ARR (billing_arr from /api/billing/snapshots, as-of-date matched) |
| `REV-8` | Account-level billing_arr_current (/api/accounts) |

### Support Hygiene Codes

| Value | Meaning |
|-------|---------|
| `SUP-3` | Raw ticket count (includes duplicates/spam) |
| `SUP-8` | Clean ticket count (excludes spam and duplicates from /api/accounts/{id}/tickets) |
| `SUP-9` | SLA-only check without ticket volume |

### Action Priority Codes

| Value | Meaning |
|-------|---------|
| `ACT-1` | Risk-score-only prioritization |
| `ACT-5` | Composite: risk_score, then ARR, then overdue balance |
| `ACT-7` | ARR-weighted only |

### CRM Match Codes

| Value | Meaning |
|-------|---------|
| `CM-2` | Exact legal_name match only |
| `CM-5` | Legal name or alias match (includes fuzzy suffix variants) |
| `CM-8` | Case-insensitive substring match |

### Pipeline Window Codes

| Value | Meaning |
|-------|---------|
| `PW-3` | Current-quarter close dates only |
| `PW-6` | Quarter match (close_date falls within specified quarter) |
| `PW-9` | Trailing 12-month window |

### Followup Scope Codes

| Value | Meaning |
|-------|---------|
| `FS-1` | All overdue regardless of link status |
| `FS-4` | Overdue with link status tracked, sorted by customer_name |
| `FS-8` | Linked only |

### Receivable Trigger Codes

| Value | Meaning |
|-------|---------|
| `RCP-4` | 61-90 and 90+ buckets only |
| `RCP-7` | 31-60, 61-90, and 90+ combined |
| `RCP-9` | Any non-zero in any aging bucket |

### Board Sort Codes

| Value | Meaning |
|-------|---------|
| `BORD-1` | Alphabetical by account_id |
| `BORD-4` | By risk severity (critical → high → medium → low), then ARR descending within each tier |
| `BORD-8` | By overdue balance descending |

### Exposure Formula Codes

| Value | Meaning |
|-------|---------|
| `EXP-2` | Net exposure = ARR at risk |
| `EXP-6` | Net exposure = ARR at risk − open expansion pipeline |
| `EXP-9` | Gross exposure = ARR at risk + open expansion pipeline |

### Calendar Policy Codes

| Value | Meaning |
|-------|---------|
| `CAL-3` | Fixed +7 days from assessment date for all actions |
| `CAL-5` | Per-action tiered due dates |
| `CAL-7` | Earliest possible date across all actions |

### Metric Sources

| Value | Endpoint Used |
|-------|---------------|
| `crm_closed_won` | /api/accounts/{id}/metrics (recognized_revenue) |
| `support_export` | /api/accounts/{id}/tickets (clean count) |
| `sla_report` | /api/accounts/{id}/metrics (sla_compliance) |
| `nps_survey` | /api/accounts/{id}/nps or /api/accounts/{id}/metrics |
| `billing_snapshot` | /api/billing/snapshots |
| `ar_aging` | /api/finance/ar-aging |
| `pipeline_crm` | /api/opportunities |
| `event_dashboard` | /api/events/performance |
| `hr_report` | /api/hr/summary |

### Ticket Trend

| Value | Condition |
|-------|-----------|
| `improving` | Clean ticket counts decrease across the period |
| `worsening` | Clean ticket counts increase across the period |
| `flat` | Clean ticket counts remain unchanged across the period |

### Review Owner

| Value | When to Choose |
|-------|----------------|
| `customer_success` | Default for QBR/metrics packets |
| `solutions_engineering` | When technical recovery dominates the account picture |
| `finance_ops` | When overdue receivables are the primary concern |

### Agenda Topics (QBR)

| Value |
|-------|
| `partnership_overview` |
| `q2_metrics` |
| `performance_highlights` |
| `q3_initiatives` |
| `technical_recovery` |
| `commercial_expansion` |

### Outreach Actions (Churn Model)

| Value | When to Use |
|-------|------------|
| `renewal_save` | Top churn probability + renewal window or low tenure |
| `technical_recovery` | SLA issues present |
| `collections_followup` | InvoicePastDue == \"Yes\" in candidate CSV |
| `nurture_monitor` | Low churn probability, no immediate risk signals |

### Churn Reason Codes

| Value | Trigger |
|-------|---------|
| `overdue_receivable` | InvoicePastDue == \"Yes\" in candidates CSV |
| `low_tenure_high_churn` | tenure <= 24 and churn probability is top-ranked |
| `clean_billings` | InvoicePastDue == \"No\" |

### Model Protocol Codes

| Value | Meaning |
|-------|---------|
| `MOD-2` | Basic logistic regression, default hyperparameters |
| `MOD-7` | Logistic regression with one-hot encoding for categoricals, unscaled numeric features |
| `MOD-9` | Gradient-boosted trees |

### Probability Scale Codes

| Value | Meaning |
|-------|---------|
| `PRB-1` | Raw log-odds conversion |
| `PRB-4` | Logistic regression predict_proba (sklearn standard) |
| `PRB-8` | Platt-scaled posterior |

### Deployment Rule Codes

| Value | Meaning |
|-------|---------|
| `DEP-3` | Single threshold (p >= 0.5) |
| `DEP-5` | Ranked list (top-N by probability), no fixed threshold |
| `DEP-9` | Multi-threshold tiers |

### Outreach Mapping Codes

| Value | Meaning |
|-------|---------|
| `OUT-2` | InvoicePastDue → collections; low tenure → renewal_save; else nurture_monitor |
| `OUT-6` | Probability-band mapping only |
| `OUT-8` | Single action for all candidates |

### Accuracy Bands

| Value | Range |
|-------|-------|
| `below_70` | accuracy < 70% |
| `70_to_79` | 70% <= accuracy < 80% |
| `80_to_89` | 80% <= accuracy < 90% |
| `90_plus` | accuracy >= 90% |

### Tenure Coefficient Direction

| Value | Meaning |
|-------|---------|
| `negative` | Higher tenure → lower churn risk (standard expected relationship) |
| `positive` | Higher tenure → higher churn risk (unusual) |
| `zero` | Coefficient near zero |
| `not_assessed` | Tenure not part of the risk model |

### Account Lifecycle

| Value |
|-------|
| `active` |
| `inactive` |
| `churned` |

### Segments

| Value |
|-------|
| `Strategic` |
| `Enterprise` |
| `Mid-Market` |

### Product Plans

| Value |
|-------|
| `Strategic` |
| `Enterprise` |
| `Scale` |
