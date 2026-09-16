# Controlled Vocabulary

Every enum field must use exactly one of these values. Never invent variants or approximate with similar words.

## Risk Levels

Used in: risk_level, primary risk classification fields.

| Value | Meaning |
|---|---|
| `critical` | Immediate retention threat; multiple severe risk signals |
| `high` | Significant risk; requires proactive intervention |
| `medium` | Moderate risk; needs monitoring and planned outreach |
| `low` | Minimal risk; standard nurture sufficient |

## Primary Actions

Used in: primary_action, outreach_action.

| Value | When to use |
|---|---|
| `executive_qbr` | Strategic account with renewal approaching and significant ARR; needs exec-level business review |
| `collections_followup` | Account has overdue receivables (31+ days); primary need is payment collection |
| `technical_recovery` | SLA degradation or usage decline is the dominant risk factor; need technical intervention to stabilize |
| `renewal_save` | Account in renewal window with elevated churn probability; needs dedicated save play |
| `nurture_monitor` | Low-risk account; routine CSM monitoring and periodic check-ins |
| `no_action` | No intervention needed; account is healthy with no risk signals |

**Priority tiebreak**: collections_followup > technical_recovery > renewal_save > executive_qbr > nurture_monitor > no_action. When multiple actions could apply, choose the highest-priority action whose condition is met.

## Reason Codes

Used in: reason_codes arrays. Each code flags a distinct risk factor.

| Code | Trigger condition |
|---|---|
| `overdue_receivable` | Account has overdue balance > 0 (31_60 + 61_90 + 90_plus > 0) in the assessment quarter |
| `low_tenure_high_churn` | contract_tenure_months <= 18 (low tenure correlates with higher churn) |
| `sla_degradation` | SLA compliance fell below 90% in any month of the analysis period |
| `nps_drop` | Latest NPS is lower than earliest NPS in the period, OR latest NPS < 40 |
| `usage_decline` | Product usage declined over the period (last month < first month) |
| `renewal_window` | renewal_date is within 90 days of the assessment date |
| `expansion_offset` | Account has open expansion opportunities with close_date within the analysis period or near future (mitigating factor) |
| `clean_billings` | No overdue balance (0.0) and no billing issues detected (positive signal) |

## Metric Sources

Used in: metric_sources object (QBR tasks).

| Value | Maps to |
|---|---|
| `crm_closed_won` | Revenue from CRM closed-won deals |
| `support_export` | Support ticket counts |
| `sla_report` | SLA compliance percentages |
| `nps_survey` | NPS scores from survey responses |
| `billing_snapshot` | Revenue/ARR from billing snapshots |
| `ar_aging` | Receivables data from A/R aging |
| `pipeline_crm` | Pipeline data from CRM opportunities |
| `event_dashboard` | Event data from performance endpoint |
| `hr_report` | HR data from summary endpoint |

Assignment rules:
- **revenue**: `billing_snapshot` when using billing_arr; `crm_closed_won` when using recognized_revenue (monthly metrics)
- **support_tickets**: `support_export`
- **sla_compliance**: `sla_report`
- **nps**: `nps_survey`

## Review Owners

Used in: review_owner.

| Value | When |
|---|---|
| `customer_success` | QBR/metrics review (default for retention work) |
| `solutions_engineering` | Technical recovery focus |
| `finance_ops` | Receivables/pipeline focus |

## Agenda Topics

Used in: agenda_topics array. Choose exactly four ordered strings.

| Value | Description |
|---|---|
| `partnership_overview` | Strategic relationship context |
| `q2_metrics` | Quarterly metrics review |
| `performance_highlights` | Key wins and achievements |
| `q3_initiatives` | Forward-looking initiatives |
| `technical_recovery` | Technical stabilization plan |
| `commercial_expansion` | Growth and expansion opportunities |

## Ticket Trend

Used in: ticket_trend.

| Value | Condition |
|---|---|
| `improving` | Ticket counts decreasing month-over-month |
| `worsening` | Ticket counts increasing month-over-month |
| `flat` | Counts stable across months |

## Link Status

Used in: link_status.

| Value | Condition |
|---|---|
| `linked` | A/R customer_name matches an account legal_name or alias |
| `unlinked` | No match found |

## Accuracy Bands

Used in: accuracy_band.

| Value | Range |
|---|---|
| `below_70` | accuracy_pct < 70 |
| `70_to_79` | 70 <= accuracy_pct < 80 |
| `80_to_89` | 80 <= accuracy_pct < 90 |
| `90_plus` | accuracy_pct >= 90 |

## Tenure / Coefficient Direction

Used in: tenure_risk_direction, tenure_coefficient_direction.

| Value | Meaning |
|---|---|
| `negative` | Inverse relationship: lower tenure -> higher risk (the expected finding) |
| `positive` | Direct relationship: higher tenure -> higher risk (unusual) |
| `zero` | No relationship detected |
| `not_assessed` | Not evaluated in this analysis |

## Policy Codes

Each output template lists pipe-delimited options for each policy code key. Choose exactly one value from the listed options. Do not invent codes.

The policy codes encode methodological choices made during computation. After completing the analysis, select the code that best describes the methodology actually used:

- **Risk model codes** (RS-2, RS-6, RS-9): Chosen based on scoring methodology. RS-6 for multi-factor scoring with billing-sourced ARR. RS-2 for CRM-sourced. RS-9 for churn-model-driven.
- **ARR source codes** (REV-1, REV-4, REV-8): REV-4 when using billing snapshots. REV-1 for CRM. REV-8 for recognized revenue.
- **Support hygiene codes** (SUP-3, SUP-8, SUP-9): SUP-8 when using clean ticket counts with duplicate/spam exclusion.
- **Action priority codes** (ACT-1, ACT-5, ACT-7): ACT-5 when using the standard action priority tiebreak order.
- Other code families follow analogous selection logic based on the methodology actually applied.
