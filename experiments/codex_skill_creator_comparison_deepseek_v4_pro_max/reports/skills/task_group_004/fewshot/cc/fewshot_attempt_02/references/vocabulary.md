# Controlled Vocabulary

Every enum field in ApexCloud retention operations output must use exactly
one of the labels listed here. Do not invent new values.

## Risk Levels

| Value | Meaning |
|-------|--------|
| `critical` | Extreme risk, immediate action required (score 80-100) |
| `high` | Significant risk, needs prompt attention (score 50-79) |
| `medium` | Moderate risk, monitor and plan (score 20-49) |
| `low` | Minimal risk, routine monitoring (score 0-19) |

## Primary Actions

| Value | Meaning |
|-------|--------|
| `collections_followup` | Overdue receivables is the dominant risk |
| `technical_recovery` | SLA or usage degradation dominates |
| `renewal_save` | Renewal timing or low tenure is the primary concern |
| `executive_qbr` | Strategic account requiring executive-level review |
| `nurture_monitor` | Low risk, routine check-in |
| `no_action` | No immediate action needed |

## Reason Codes

| Value | Meaning |
|-------|--------|
| `overdue_receivable` | Account has overdue balance in aging buckets 31+ days |
| `low_tenure_high_churn` | Tenure under 24 months with renewal approaching |
| `sla_degradation` | SLA compliance declining or below 90% |
| `nps_drop` | NPS below 50 or declining from prior reading |
| `usage_decline` | Product usage declining across the analysis period |
| `renewal_window` | Renewal date within 90 days of assessment date |
| `expansion_offset` | Open expansion pipeline exists (risk mitigation) |
| `clean_billings` | No overdue receivables (positive signal) |

## Metric Sources

| Value | Meaning |
|-------|--------|
| `crm_closed_won` | Revenue from CRM closed-won data |
| `support_export` | Support ticket data from export/system |
| `sla_report` | SLA compliance from operations reporting |
| `nps_survey` | NPS scores from survey platform |
| `billing_snapshot` | ARR from billing snapshot system |
| `ar_aging` | Receivables from A/R aging system |
| `pipeline_crm` | Pipeline data from CRM |
| `event_dashboard` | Event data from operations dashboard |
| `hr_report` | HR data from HR system |

## Review Owners

| Value | Meaning |
|-------|--------|
| `customer_success` | CSM-led review |
| `solutions_engineering` | SE-led technical review |
| `finance_ops` | Finance-led operational review |

## Ticket Trends

| Value | Meaning |
|-------|--------|
| `improving` | Ticket count decreasing over the period |
| `worsening` | Ticket count increasing over the period |
| `flat` | No change in ticket count |

## Agenda Topics

| Value | Meaning |
|-------|--------|
| `partnership_overview` | Relationship and strategic alignment |
| `q2_metrics` | Quarterly metrics review (adapt quarter label) |
| `q3_initiatives` | Next-quarter initiatives (adapt quarter label) |
| `performance_highlights` | Key wins and achievements |
| `technical_recovery` | Technical health and recovery plan |
| `commercial_expansion` | Upsell and expansion opportunities |

Note: The quarter number in agenda topics should match the actual review
quarter (Q1, Q2, Q3, Q4). The values above are labels, not templates.

## Link Status

| Value | Meaning |
|-------|--------|
| `linked` | A/R customer matched to a CRM account |
| `unlinked` | A/R customer could not be matched |

## Accuracy Bands

| Value | Meaning |
|-------|--------|
| `below_70` | Accuracy below 70% |
| `70_to_79` | Accuracy 70-79.9% |
| `80_to_89` | Accuracy 80-89.9% |
| `90_plus` | Accuracy 90% or above |

## Tenure Risk Direction

| Value | Meaning |
|-------|--------|
| `negative` | Inverse relationship: lower tenure implies higher risk |
| `positive` | Direct relationship: lower tenure implies lower risk |
| `not_assessed` | Relationship not evaluated |
| `zero` | No relationship detected |

## Outreach Actions (Churn)

| Value | Meaning |
|-------|--------|
| `renewal_save` | High risk, immediate renewal intervention |
| `technical_recovery` | Moderate risk, support-driven recovery |
| `collections_followup` | Past-due account, billing intervention |
| `nurture_monitor` | Low risk, routine monitoring |

## Model Checks

`uses_billing_arr_source` is `true` when ARR was sourced from billing
snapshots. `false` when sourced from account profile.

## Policy Codes

### Risk Model Codes

| Code | Description |
|------|-------------|
| `RS-2` | Simple model with 2 dimensions |
| `RS-6` | Standard composite model with all seven dimensions |
| `RS-9` | Extended model with additional dimensions |

### ARR Source Codes

| Code | Description |
|------|-------------|
| `REV-1` | Account profile billing_arr_current |
| `REV-4` | Billing snapshot billing_arr |
| `REV-8` | CRM crm_arr |

### Support Hygiene Codes

| Code | Description |
|------|-------------|
| `SUP-3` | Raw ticket count from metrics |
| `SUP-8` | Clean ticket count (spam/dupe/cancelled excluded) |
| `SUP-9` | Weighted ticket count by severity |

### Action Priority Codes

| Code | Description |
|------|-------------|
| `ACT-1` | Revenue-priority ordering |
| `ACT-5` | Composite risk-priority ordering |
| `ACT-7` | Collections-first ordering |

### Receivable Trigger Codes

| Code | Description |
|------|-------------|
| `RCP-4` | All buckets including current |
| `RCP-7` | Older buckets only (31+ days) |
| `RCP-9` | 90+ days only |

### CRM Match Codes

| Code | Description |
|------|-------------|
| `CM-2` | Legal name exact match only |
| `CM-5` | Legal name + aliases exact match |
| `CM-8` | Legal name + aliases fuzzy match |

### Pipeline Window Codes

| Code | Description |
|------|-------------|
| `PW-3` | Calendar quarter bounded |
| `PW-6` | Close-date quarter bounded |
| `PW-9` | Entire pipeline unbounded |

### Followup Scope Codes

| Code | Description |
|------|-------------|
| `FS-1` | Linked accounts only |
| `FS-4` | All overdue customers (linked + unlinked) |
| `FS-8` | Critical bucket (90+ days) only |

### Model Protocol Codes

| Code | Description |
|------|-------------|
| `MOD-2` | Heuristic rules-based model |
| `MOD-7` | Logistic regression trained on provided data |
| `MOD-9` | Ensemble model |

### Probability Scale Codes

| Code | Description |
|------|-------------|
| `PRB-1` | 0-100 integer scale |
| `PRB-4` | 0-1 decimal scale (3 decimals) |
| `PRB-8` | Log-odds scale |

### Deployment Rule Codes

| Code | Description |
|------|-------------|
| `DEP-3` | Full candidate set |
| `DEP-5` | Filtered candidate shortlist |
| `DEP-9` | Threshold-gated deployment |

### Outreach Mapping Codes

| Code | Description |
|------|-------------|
| `OUT-2` | Probability-ordered outreach |
| `OUT-6` | Signal-weighted outreach |
| `OUT-8` | Segment-prioritized outreach |

### Board Sort Codes

| Code | Description |
|------|-------------|
| `BORD-1` | Alphabetical by account_id |
| `BORD-4` | Risk-ranked descending |
| `BORD-8` | ARR-ranked descending |

### Exposure Formula Codes

| Code | Description |
|------|-------------|
| `EXP-2` | Gross ARR exposure |
| `EXP-6` | Net exposure (ARR minus expansion) |
| `EXP-9` | Risk-weighted exposure |

### Calendar Policy Codes

| Code | Description |
|------|-------------|
| `CAL-3` | Single uniform due date |
| `CAL-5` | Action-specific due dates from task spec |
| `CAL-7` | Rolling 30-day calendar |
