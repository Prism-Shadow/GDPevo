# Controlled Vocabularies

Every string field in the answer template that appears as `"option1|option2|option3"`
in the prompt or template must be filled with exactly one of the options.
Never invent a new value.

---

## Risk Level

| Value | Range (risk_score) | Meaning |
|---|---|---|
| `critical` | 80–100 | Immediate action required; multiple severe signals |
| `high` | 40–79 | Significant risk; needs active intervention |
| `medium` | 20–39 | Watch closely; one or two concerning signals |
| `low` | 0–19 | Stable; routine monitoring sufficient |

---

## Primary Actions

| Value | Use when |
|---|---|
| `collections_followup` | Account has overdue receivables (61+ days) |
| `technical_recovery` | SLA degradation or usage decline without overdue payments |
| `renewal_save` | Approaching renewal with churn signals but no collections issue |
| `executive_qbr` | Strategic account with large ARR and mixed signals |
| `nurture_monitor` | Low risk; continue monitoring |
| `no_action` | No concerning signals; standard cadence |

When both overdue and SLA/usage issues exist, `collections_followup` takes priority
because cash collection is the most time-sensitive action.

---

## Reason Codes

| Code | Trigger condition |
|---|---|
| `overdue_receivable` | `overdue_balance` > 0 (any amount in 61+ day buckets) |
| `low_tenure_high_churn` | `contract_tenure_months` <= 18 and the account has other risk signals |
| `sla_degradation` | One or more SLA breaches (first-response or resolution) in the period |
| `nps_drop` | Latest NPS dropped by 20+ points or latest NPS < 35 |
| `usage_decline` | `product_usage` decreased by 3+ percentage points across the period |
| `renewal_window` | `renewal_date` falls within 90 days of the assessment date (past or future) |
| `expansion_offset` | Account has open expansion pipeline (include alongside risk codes) |
| `clean_billings` | Zero overdue balance; used when other risk signals exist but billing is healthy |

Reason codes are additive: include every code whose condition is met. Order them
from most to least severe: overdue, tenure, SLA, NPS, usage, renewal, expansion,
clean_billings.

---

## Ticket Trend

| Value | Condition |
|---|---|
| `improving` | Ticket count decreased by end of period vs start |
| `worsening` | Ticket count increased by end of period vs start |
| `flat` | Ticket count unchanged or fluctuating without clear direction |

---

## Metric Sources

| Value | Data origin |
|---|---|
| `crm_closed_won` | CRM recognized revenue (metrics endpoint `recognized_revenue`) |
| `support_export` | Support ticket system (tickets endpoint) |
| `sla_report` | SLA compliance data (metrics endpoint `sla_compliance`) |
| `nps_survey` | NPS survey responses (NPS or metrics endpoint `nps_score`) |
| `billing_snapshot` | Billing system snapshots (`/api/billing/snapshots`) |
| `ar_aging` | Accounts receivable aging (`/api/finance/ar-aging`) |
| `pipeline_crm` | CRM pipeline (`/api/opportunities`) |
| `event_dashboard` | Event performance data (`/api/events/performance`) |
| `hr_report` | HR operations data (`/api/hr/summary`) |

---

## Review Owner

| Value | Context |
|---|---|
| `customer_success` | Standard CS-owned QBR or retention review |
| `solutions_engineering` | Technical recovery or architecture review needed |
| `finance_ops` | Collections, A/R, or billing-focused review |

---

## Agenda Topics

| Value | Include when |
|---|---|
| `partnership_overview` | Always include as the first topic |
| `q2_metrics` | (or appropriate quarter) Always include |
| `performance_highlights` | Include when metrics are mostly positive |
| `q3_initiatives` | (or next quarter) Always include as a forward-looking topic |
| `technical_recovery` | Include when SLA or usage issues are present |
| `commercial_expansion` | Include when expansion pipeline exists |

---

## Churn Accuracy Bands

| Value | Range |
|---|---|
| `below_70` | accuracy < 70% |
| `70_to_79` | 70% <= accuracy < 80% |
| `80_to_89` | 80% <= accuracy < 90% |
| `90_plus` | accuracy >= 90% |

---

## Churn Outreach Actions

| Value | Use when |
|---|---|
| `renewal_save` | High churn probability + other retention signals |
| `technical_recovery` | SLA or usage issues dominate |
| `collections_followup` | Overdue receivables present |
| `nurture_monitor` | Low churn probability; continue monitoring |

---

## Churn Reason Codes

Same as retention reason codes but singular (one per candidate in churn ranking).

---

## Link Status

| Value | Condition |
|---|---|
| `linked` | A/R `customer_name` matches an account's `legal_name` or any `account_alias` |
| `unlinked` | No match found; `account_id` must be `null` |

---

## Tenure Risk Direction

| Value | Meaning |
|---|---|
| `negative` | Longer tenure correlates with lower risk (standard pattern) |
| `positive` | Longer tenure correlates with higher risk (unusual) |
| `not_assessed` | Tenure was not factored into the model |

---

## Accuracy / Validation Flags

| Value | Usage |
|---|---|
| `negative` | Tenure coefficient is negative (longer tenure -> lower churn) |
| `positive` | Tenure coefficient is positive |
| `zero` | Tenure coefficient is effectively zero |

---

## Policy Codes

Policy codes appear in templates as pipe-delimited choices (e.g. `RS-2|RS-6|RS-9`).
Select exactly one code from each set.

**Default rule**: when the task provides no specific selection criteria, choose
the middle option from the pipe-delimited set. For example, from `RS-2|RS-6|RS-9`
select `RS-6`. This matches the standard ApexCloud model configuration.

**When to deviate**: deviate from the middle only when the prompt or data clearly
indicates a different approach. For example, if you use CRM ARR instead of billing
ARR, select a different `arr_source_code`.
