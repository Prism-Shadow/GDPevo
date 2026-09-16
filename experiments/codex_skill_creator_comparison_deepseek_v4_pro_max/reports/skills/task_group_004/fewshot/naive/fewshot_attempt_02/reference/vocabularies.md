# ApexCloud Retention Operations Controlled Vocabularies

Every task must use these exact string values. Never substitute, approximate, or invent labels.

---

## Risk Levels

Used in: renewal risk queue, retention action board.

| Value | Meaning |
|-------|---------|
| `critical` | Immediate action required, highest risk |
| `high` | Significant risk, needs prompt attention |
| `medium` | Moderate risk, monitor closely |
| `low` | Low risk, standard monitoring |

---

## Primary Actions

Used in: renewal risk queue, retention action board, receivables follow-ups.

| Value | When to use |
|-------|-------------|
| `collections_followup` | Overdue receivables present; primary issue is payment collection |
| `technical_recovery` | SLA degradation, usage decline, or product health issues dominate |
| `renewal_save` | Renewal is imminent and retention risk is driven by sentiment/tenure |
| `executive_qbr` | Strategic/enterprise account needs executive-level business review |
| `nurture_monitor` | Low-risk account needing standard relationship nurturing |
| `no_action` | No active intervention required |

---

## Reason Codes

Used in: renewal risk queue, churn outreach ranking, retention action board.

| Value | Trigger |
|-------|---------|
| `overdue_receivable` | Account has non-zero overdue balance in A/R aging |
| `low_tenure_high_churn` | Low contract tenure (typically <24 months) combined with other risk signals |
| `sla_degradation` | SLA compliance below acceptable threshold or declining trend |
| `nps_drop` | NPS score has trended downward or is low relative to benchmarks |
| `usage_decline` | Product usage has decreased across consecutive months |
| `renewal_window` | Renewal date falls within the near-term window (typically next 90 days) |
| `expansion_offset` | Open expansion pipeline partially offsets revenue at risk |
| `clean_billings` | No billing or receivables issues; included as a positive signal |

Use multiple reason codes when an account has several active risk signals. Order them by severity: overdue_receivable first if present, then structural risks (tenure, SLA, NPS, usage), then contextual signals (renewal_window, expansion_offset), and clean_billings last.

---

## Metric Sources

Used in: QBR metrics packet.

| Value | Source endpoint |
|-------|-----------------|
| `crm_closed_won` | Revenue from `/api/accounts/{id}/metrics` `recognized_revenue` |
| `support_export` | Ticket counts from `/api/accounts/{id}/tickets` |
| `sla_report` | SLA compliance from `/api/accounts/{id}/metrics` `sla_compliance` |
| `nps_survey` | NPS scores from `/api/accounts/{id}/nps` or metrics endpoint |
| `billing_snapshot` | ARR from `/api/billing/snapshots` |
| `ar_aging` | Receivables from `/api/finance/ar-aging` |
| `pipeline_crm` | Pipeline data from `/api/opportunities` |
| `event_dashboard` | Event data from `/api/events/performance` |
| `hr_report` | HR data from `/api/hr/summary` |

---

## Ticket Trends

Used in: QBR metrics packet.

| Value | Condition |
|-------|-----------|
| `improving` | Clean ticket count per month is trending downward |
| `worsening` | Clean ticket count per month is trending upward |
| `flat` | Clean ticket count is stable across all months |

---

## Review Owners

Used in: QBR metrics packet.

| Value | When to assign |
|-------|----------------|
| `customer_success` | Standard QBR owned by the CSM |
| `solutions_engineering` | Technical issues dominate; needs SE review |
| `finance_ops` | Financial/receivables issues are primary |

---

## Agenda Topics

Used in: QBR metrics packet. Select exactly four, ordered by relevance.

| Value | Description |
|-------|-------------|
| `partnership_overview` | Strategic partnership context |
| `q2_metrics` | Quarterly metric review |
| `performance_highlights` | Key performance achievements |
| `q3_initiatives` | Forward-looking Q3 plans |
| `technical_recovery` | Technical health and improvement plan |
| `commercial_expansion` | Expansion and growth opportunities |

---

## Link Status

Used in: receivables and pipeline operations review.

| Value | Condition |
|-------|-----------|
| `linked` | Customer name matches a CRM account by legal_name or aliases |
| `unlinked` | No CRM account match found for the customer name |

---

## Accuracy Bands

Used in: churn model validation.

| Value | Accuracy range |
|-------|---------------|
| `below_70` | < 70% |
| `70_to_79` | 70% to 79.9% |
| `80_to_89` | 80% to 89.9% |
| `90_plus` | >= 90% |

---

## Coefficient Directions

Used in: churn model validation, renewal risk model_checks.

| Value | Meaning |
|-------|---------|
| `negative` | Higher feature value decreases churn probability (e.g., longer tenure = lower risk) |
| `positive` | Higher feature value increases churn probability |
| `zero` | Feature has no directional effect |
| `not_assessed` | Direction was not evaluated in this analysis |

---

## Outreach Actions

Used in: churn model outreach ranking.

| Value | Trigger |
|-------|---------|
| `renewal_save` | High churn probability driven by tenure/attrition risk |
| `technical_recovery` | Churn risk linked to product health or SLA issues |
| `collections_followup` | Churn probability correlated with past-due invoices |
| `nurture_monitor` | Low churn probability; standard monitoring sufficient |

---

## Policy Codes

Used in: all task types. These are opaque codes that the task answer templates require. Select codes from the allowed options specified in each template's policy_codes object.

### Risk and Revenue Codes

| Code | Domain |
|------|--------|
| `RS-2`, `RS-6`, `RS-9` | Risk model codes |
| `REV-1`, `REV-4`, `REV-8` | ARR source codes |
| `SUP-3`, `SUP-8`, `SUP-9` | Support hygiene codes |
| `ACT-1`, `ACT-5`, `ACT-7` | Action priority codes |

### Receivables Codes

| Code | Domain |
|------|--------|
| `RCP-4`, `RCP-7`, `RCP-9` | Receivable trigger codes |
| `CM-2`, `CM-5`, `CM-8` | CRM match codes |
| `PW-3`, `PW-6`, `PW-9` | Pipeline window codes |
| `FS-1`, `FS-4`, `FS-8` | Followup scope codes |

### Model and Outreach Codes

| Code | Domain |
|------|--------|
| `MOD-2`, `MOD-7`, `MOD-9` | Model protocol codes |
| `PRB-1`, `PRB-4`, `PRB-8` | Probability scale codes |
| `DEP-3`, `DEP-5`, `DEP-9` | Deployment rule codes |
| `OUT-2`, `OUT-6`, `OUT-8` | Outreach mapping codes |

### Board Codes

| Code | Domain |
|------|--------|
| `BORD-1`, `BORD-4`, `BORD-8` | Board sort codes |
| `EXP-2`, `EXP-6`, `EXP-9` | Exposure formula codes |
| `CAL-3`, `CAL-5`, `CAL-7` | Calendar policy codes |

When the task template shows a policy_codes field with pipe-separated options (e.g., `"RS-2|RS-6|RS-9"`), select exactly one code from the allowed set. Choose the code that best matches the methodology used in the analysis.
