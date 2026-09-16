# Controlled Vocabularies

Every enum value in this catalog is the exact string that must appear in JSON output. Do not use synonyms, abbreviations, or alternative casing.

## Risk levels

`critical` | `high` | `medium` | `low`

- `critical`: imminent renewal risk with multiple severe signals (overdue receivables, NPS collapse, SLA breakdown, usage decline, low tenure).
- `high`: renewal window active with overdue receivables or multiple degradation signals.
- `medium`: renewal window active or moderate degradation signals without overdue receivables.
- `low`: isolated issues, clean billing history, no overdue receivables.

## Primary actions

`executive_qbr` | `collections_followup` | `technical_recovery` | `renewal_save` | `nurture_monitor` | `no_action`

- `executive_qbr`: strategic account requiring executive-level quarterly business review.
- `collections_followup`: overdue receivables present; immediate collections action needed.
- `technical_recovery`: SLA degradation, usage decline, or support hygiene issues; technical intervention needed.
- `renewal_save`: account in renewal window with churn risk; proactive save motion needed.
- `nurture_monitor`: low risk but requires ongoing monitoring and nurturing.
- `no_action`: minimal or no risk; no active intervention required.

## Reason codes

`overdue_receivable` | `low_tenure_high_churn` | `sla_degradation` | `nps_drop` | `usage_decline` | `renewal_window` | `expansion_offset` | `clean_billings`

- `overdue_receivable`: account has an outstanding overdue balance in A/R aging.
- `low_tenure_high_churn`: low tenure correlates with elevated churn risk for this account.
- `sla_degradation`: support SLA compliance has dropped below acceptable thresholds, or tickets with SLA breaches are present.
- `nps_drop`: NPS score has declined meaningfully (typically 10+ points drop period-over-period).
- `usage_decline`: product usage metrics show a downward trend across the analysis period.
- `renewal_window`: account's renewal date falls within or near the analysis window.
- `expansion_offset`: open expansion pipeline partially offsets risk, or expansion opportunity exists.
- `clean_billings`: billing history and payments are current with no issues.

## Ticket trends

`improving` | `worsening` | `flat`

- `improving`: ticket count decreased from the first month to the last month of the period.
- `worsening`: ticket count increased from the first month to the last month of the period.
- `flat`: ticket count remained the same across the period.

## Metric sources

`crm_closed_won` | `support_export` | `sla_report` | `nps_survey` | `billing_snapshot` | `ar_aging` | `pipeline_crm` | `event_dashboard` | `hr_report`

- `crm_closed_won`: revenue data sourced from CRM closed-won opportunities.
- `support_export`: ticket data sourced from support system exports.
- `sla_report`: SLA compliance data sourced from SLA reporting dashboards.
- `nps_survey`: NPS data sourced from NPS survey platform.
- `billing_snapshot`: data sourced from billing snapshot records.
- `ar_aging`: data sourced from accounts receivable aging reports.
- `pipeline_crm`: data sourced from CRM pipeline/opportunity records.
- `event_dashboard`: data sourced from event performance dashboards.
- `hr_report`: data sourced from HR reporting systems.

## Review owners

`solutions_engineering` | `customer_success` | `finance_ops`

- `solutions_engineering`: review owned by the solutions engineering team.
- `customer_success`: review owned by the customer success team.
- `finance_ops`: review owned by finance operations.

## Agenda topics

`partnership_overview` | `q2_metrics` | `performance_highlights` | `q3_initiatives` | `technical_recovery` | `commercial_expansion`

Use exactly four topics, ordered to reflect the natural flow of a QBR agenda. When the task specifies a different quarter, mentally remap the quarter-specific topics (`q2_metrics`, `q3_initiatives`) to the relevant quarter, but use the exact enum strings from this list.

## Link status

`linked` | `unlinked`

- `linked`: A/R customer name matched to a CRM account.
- `unlinked`: no matching CRM account found.

## Accuracy bands

`below_70` | `70_to_79` | `80_to_89` | `90_plus`

Map model accuracy percentage to the correct band by the lower bound: below 70 goes to `below_70`, 70-79.9 to `70_to_79`, 80-89.9 to `80_to_89`, 90 and above to `90_plus`.

## Tenure coefficient direction

`negative` | `positive` | `zero`

- `negative`: higher tenure correlates with lower churn risk (standard expectation).
- `positive`: higher tenure correlates with higher churn risk.
- `zero`: no detectable relationship between tenure and churn risk.

## Outreach actions (churn model)

`renewal_save` | `technical_recovery` | `collections_followup` | `nurture_monitor`

Same semantics as the primary actions above. Map the predicted churn probability and account context to the most appropriate outreach action.
