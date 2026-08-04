## Controlled Enum Vocabulary for ApexCloud Retention Operations

Every enum-valued field in an output template must use one of the values listed below. Never invent or combine values.

---

### Risk Levels

| Enum | Meaning |
|------|---------|
| `critical` | Immediate executive attention required; imminent churn or severe receivable |
| `high` | Strong risk indicators across multiple dimensions |
| `medium` | Moderate concern; monitor and engage |
| `low` | Healthy account; routine nurture |

---

### Primary Actions

| Enum | When to Assign |
|------|----------------|
| `executive_qbr` | Strategic/enterprise account with renewal within the quarter, or critical risk level requiring VP-level engagement |
| `collections_followup` | Overdue balance above threshold; A/R aging indicates payment delinquency |
| `technical_recovery` | SLA degradation, high ticket volume, or systemic product issues |
| `renewal_save` | Renewal window approaching with declining NPS, usage drop, or competitive risk |
| `nurture_monitor` | Low risk, stable; maintain relationship health |
| `no_action` | Account is clean; no intervention needed |

---

### Reason Codes

| Enum | Trigger |
|------|---------|
| `overdue_receivable` | Overdue balance > 0 or past-due aging bucket populated |
| `low_tenure_high_churn` | Account tenure below typical threshold with elevated churn probability |
| `sla_degradation` | SLA compliance below acceptable threshold or trending downward |
| `nps_drop` | NPS score declined significantly period-over-period or is negative |
| `usage_decline` | Product usage metrics trending downward |
| `renewal_window` | Renewal date falls within the current or next quarter |
| `expansion_offset` | Expansion pipeline exists that could offset renewal risk |
| `clean_billings` | All receivables current; no billing concerns |

---

### Metric Sources

Use these to populate `metric_sources` fields (e.g., in QBR packets):

| Enum | Endpoint Used |
|------|---------------|
| `crm_closed_won` | Opportunities / CRM pipeline data |
| `support_export` | Support tickets endpoint |
| `sla_report` | SLA compliance derived from ticket data |
| `nps_survey` | NPS survey endpoint |
| `billing_snapshot` | Billing snapshots endpoint |
| `ar_aging` | A/R aging endpoint |
| `pipeline_crm` | CRM opportunity pipeline |
| `event_dashboard` | Event performance endpoint |
| `hr_report` | HR summary endpoint |

---

### Review Owners

| Enum | Role |
|------|------|
| `solutions_engineering` | Technical review; architecture and product fit |
| `customer_success` | Relationship owner; adoption and value realization |
| `finance_ops` | Billing, collections, and commercial terms |

---

### Agenda Topics

Select exactly four ordered topics for QBR agendas:

| Enum |
|------|
| `partnership_overview` |
| `q2_metrics` |
| `performance_highlights` |
| `q3_initiatives` |
| `technical_recovery` |
| `commercial_health` |
| `product_roadmap` |
| `expansion_pipeline` |
| `mutual_success_plan` |

---

### Ticket Trend

| Enum | Condition |
|------|-----------|
| `improving` | Ticket count decreasing period-over-period |
| `worsening` | Ticket count increasing period-over-period |
| `flat` | Ticket count stable across the analysis period |

---

### Accuracy Band (Churn Model)

| Enum | Accuracy Range |
|------|----------------|
| `below_70` | < 70% |
| `70_to_79` | 70% – 79.9% |
| `80_to_89` | 80% – 89.9% |
| `90_plus` | ≥ 90% |

---

### Tenure Direction

| Enum | Meaning |
|------|---------|
| `negative` | Higher tenure correlates with lower churn risk (protective) |
| `positive` | Higher tenure correlates with higher churn risk |
| `not_assessed` | Relationship not evaluated |
| `zero` | No detectable tenure effect |

---

### Outreach Actions (Churn Ranking)

| Enum |
|------|
| `renewal_save` |
| `technical_recovery` |
| `collections_followup` |
| `nurture_monitor` |

---

### Link Status (Collections Dossier)

| Enum | Meaning |
|------|---------|
| `linked` | Overdue account matched to a CRM opportunity record |
| `unlinked` | No CRM match found for the overdue account |

---

### Billing Status

| Enum |
|------|
| `active` |
| `delinquent` |
| `closed` |

---

### Account Segments

| Enum |
|------|
| `strategic` |
| `enterprise` |

---

### Policy Codes

These are opaque policy identifiers used in `policy_codes` blocks. Select one value from each set per output.

#### Risk Model Code
- `RS-2`, `RS-6`, `RS-9`

#### ARR Source Code
- `REV-1`, `REV-4`, `REV-8`

#### Support Hygiene Code
- `SUP-3`, `SUP-8`, `SUP-9`

#### Action Priority Code
- `ACT-1`, `ACT-5`, `ACT-7`

#### Receivable Trigger Code
- `RCP-4`, `RCP-7`, `RCP-9`

#### CRM Match Code
- `CM-2`, `CM-5`, `CM-8`

#### Pipeline Window Code
- `PW-3`, `PW-6`, `PW-9`

#### Followup Scope Code
- `FS-1`, `FS-4`, `FS-8`

#### Model Protocol Code
- `MOD-2`, `MOD-7`, `MOD-9`

#### Probability Scale Code
- `PRB-1`, `PRB-4`, `PRB-8`

#### Deployment Rule Code
- `DEP-3`, `DEP-5`, `DEP-9`

#### Outreach Mapping Code
- `OUT-2`, `OUT-6`, `OUT-8`

#### Board Sort Code
- `BORD-1`, `BORD-4`, `BORD-8`

#### Exposure Formula Code
- `EXP-2`, `EXP-6`, `EXP-9`

#### Calendar Policy Code
- `CAL-3`, `CAL-5`, `CAL-7`

---

### Follow-Up Calendar Actions

Used in `followup_calendar` and for mapping `primary_action` to `next_touch_due_date`:

| Enum |
|------|
| `collections_followup` |
| `technical_recovery` |
| `renewal_save` |
| `executive_qbr` |
| `nurture_monitor` |

---

### Net Revenue Exposure Formula

`net_revenue_exposure = arr_at_risk - open_expansion_pipeline` (both values to 2 decimal places).

---

### Web of Enums / Cross-Reference

| Context | Fields | Vocabulary |
|---------|--------|------------|
| Risk classification | `risk_level` | critical, high, medium, low |
| Risk classification | `primary_action` | executive_qbr, collections_followup, technical_recovery, renewal_save, nurture_monitor, no_action |
| Risk classification | `reason_codes` | overdue_receivable, low_tenure_high_churn, sla_degradation, nps_drop, usage_decline, renewal_window, expansion_offset, clean_billings |
| QBR metrics | `ticket_trend` | improving, worsening, flat |
| QBR metrics | `metric_sources.*` | crm_closed_won, support_export, sla_report, nps_survey, billing_snapshot, ar_aging, pipeline_crm, event_dashboard, hr_report |
| QBR metrics | `review_plan.review_owner` | solutions_engineering, customer_success, finance_ops |
| QBR metrics | `agenda_topics[]` | partnership_overview, q2_metrics, performance_highlights, q3_initiatives, technical_recovery, commercial_health, product_roadmap, expansion_pipeline, mutual_success_plan |
| Collections | `link_status` | linked, unlinked |
| Collections | `billing_status` | active, delinquent, closed |
| Churn validation | `accuracy_band` | below_70, 70_to_79, 80_to_89, 90_plus |
| Churn validation | `tenure_coefficient_direction` | negative, positive, zero |
| Churn validation | `tenure_risk_direction` | negative, positive, not_assessed |
| Churn validation | `outreach_action` | renewal_save, technical_recovery, collections_followup, nurture_monitor |
| Board | `segment_summary` | strategic_accounts, enterprise_accounts |
| Board | `followup_calendar` | collections_followup, technical_recovery, renewal_save, executive_qbr, nurture_monitor |
