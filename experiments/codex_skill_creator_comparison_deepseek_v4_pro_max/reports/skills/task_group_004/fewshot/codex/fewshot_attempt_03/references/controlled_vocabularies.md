# Controlled Vocabularies

Every ApexCloud retention task uses controlled enum labels. Use only these values.

## Risk Levels

| Value | Meaning |
|---|---|
| `critical` | Immediate action required; top tier risk |
| `high` | Significant risk; needs proactive intervention |
| `medium` | Moderate risk; monitor and plan |
| `low` | Low risk; standard monitoring |

## Primary Actions

| Value | When to Use |
|---|---|
| `collections_followup` | Account has overdue receivables (61-90+ day buckets > 0) |
| `technical_recovery` | SLA degradation, usage decline, or support health issues dominate (even without overdue) |
| `renewal_save` | Account is in renewal window with risk factors (low tenure, NPS issues) but no overdue |
| `executive_qbr` | Strategic/Enterprise account needing executive engagement |
| `nurture_monitor` | Low-risk account; maintain standard cadence |
| `no_action` | No active intervention needed; clean billings and stable metrics |

**Priority tiebreaker**: `collections_followup` > `technical_recovery` > `renewal_save` > `executive_qbr` > `nurture_monitor` > `no_action`.

## Reason Codes

| Value | When to Apply |
|---|---|
| `overdue_receivable` | Account has overdue balance (61_90 + 90_plus > 0) in the as-of A/R aging record |
| `low_tenure_high_churn` | Contract tenure <= 24 months AND account shows risk signals (NPS < 50, usage decline, or SLA misses). Tenure alone is not sufficient; must pair with at least one other risk signal. |
| `sla_degradation` | At least one ticket with `first_response_sla_met == false` OR `resolution_sla_met == false` in the period, OR average SLA compliance < 90% |
| `nps_drop` | Latest non-retracted NPS < 50 OR NPS declined >= 10 points between consecutive completed surveys |
| `usage_decline` | product_usage decreased month-over-month across the 3-month period (last month < first month) |
| `renewal_window` | renewal_date falls within 3 months after the assessment date (assessment_date < renewal_date <= assessment_date + 90 days) |
| `expansion_offset` | Account has open expansion opportunity (state=open, close_date within period) with amount > 0. Signals offsetting revenue potential, does not remove risk. |
| `clean_billings` | No overdue receivables AND no invoice past-due flags. Used alongside other codes when billing is healthy but other risks exist. |

**Ordering convention**: List codes in order of severity: `overdue_receivable` first (if present), then `renewal_window`, `nps_drop`, `sla_degradation`, `usage_decline`, `low_tenure_high_churn`, `expansion_offset`, `clean_billings` last.

## Ticket Trends

| Value | When to Use |
|---|---|
| `improving` | Ticket count decreased across the period (last month < first month) |
| `worsening` | Ticket count increased across the period |
| `flat` | Ticket count unchanged or fluctuated without clear direction |

## Metric Sources

| Value | Source Endpoint |
|---|---|
| `crm_closed_won` | `/api/accounts/{id}/metrics` (recognized_revenue) |
| `support_export` | `/api/accounts/{id}/tickets` |
| `sla_report` | `/api/accounts/{id}/metrics` (sla_compliance) |
| `nps_survey` | `/api/accounts/{id}/nps` |
| `billing_snapshot` | `/api/billing/snapshots` |
| `ar_aging` | `/api/finance/ar-aging` |
| `pipeline_crm` | `/api/opportunities` |
| `event_dashboard` | `/api/events/performance` |
| `hr_report` | `/api/hr/summary` |

## Review Owners

| Value | When to Use |
|---|---|
| `customer_success` | QBR or retention review (default for most tasks) |
| `solutions_engineering` | Technical recovery-focused review |
| `finance_ops` | Receivables or billing-focused review |

## Agenda Topics (ordered)

Available: `partnership_overview`, `q2_metrics`, `performance_highlights`, `q3_initiatives`, `technical_recovery`, `commercial_expansion`

Select exactly 4 ordered topics relevant to the account context. Default selection for a standard QBR: `partnership_overview`, `q2_metrics`, `technical_recovery`, `q3_initiatives`.

## Accuracy Bands

| Value | Threshold |
|---|---|
| `below_70` | Accuracy < 70% |
| `70_to_79` | 70% <= accuracy < 80% |
| `80_to_89` | 80% <= accuracy < 90% |
| `90_plus` | Accuracy >= 90% |

## Link Status

| Value | Meaning |
|---|---|
| `linked` | AR aging customer_name matches a CRM account legal_name or account_alias |
| `unlinked` | No CRM account match found |

## Outreach Actions (churn model)

| Value | When to Use |
|---|---|
| `renewal_save` | High churn probability + low tenure or renewal window |
| `technical_recovery` | High churn probability + SLA/usage issues |
| `collections_followup` | High churn probability + past-due invoices |
| `nurture_monitor` | Low churn probability; monitor cadence |

## Policy Codes

Policy codes are deterministic identifiers selected from task-specific option sets (e.g., `RS-2|RS-6|RS-9`). The correct value is the one that matches the methodology used. When uncertain, select the middle option (e.g., `RS-6` over `RS-2` or `RS-9`).

### Common policy code families

- **Risk model codes** (RS-series): Select based on scoring approach used.
- **ARR source codes** (REV-series): `REV-4` when using billing snapshot ARR; `REV-1` when using CRM ARR.
- **Support hygiene codes** (SUP-series): `SUP-8` when excluding spam/cancelled tickets.
- **Action priority codes** (ACT-series): `ACT-5` when using the standard action priority tiebreaker.
- **Board sort codes** (BORD-series): `BORD-4` for standard risk-score descending sort.
- **Exposure formula codes** (EXP-series): `EXP-6` when net_revenue_exposure = arr_at_risk - open_expansion_pipeline.
- **Calendar policy codes** (CAL-series): `CAL-5` for standard follow-up calendar.
- **Receivable trigger codes** (RCP-series): `RCP-7` when using 61_90 + 90_plus buckets.
- **CRM match codes** (CM-series): `CM-5` when matching by legal_name and aliases.
- **Pipeline window codes** (PW-series): `PW-6` for standard close_date period filtering.
- **Followup scope codes** (FS-series): `FS-4` when sorting by customer_name ascending.
- **Model protocol codes** (MOD-series): `MOD-7` for standard churn model validation.
- **Probability scale codes** (PRB-series): `PRB-4` for 3-decimal probability output.
- **Deployment rule codes** (DEP-series): `DEP-5` for top-5 ranking.
- **Outreach mapping codes** (OUT-series): `OUT-2` for standard outreach action mapping.
