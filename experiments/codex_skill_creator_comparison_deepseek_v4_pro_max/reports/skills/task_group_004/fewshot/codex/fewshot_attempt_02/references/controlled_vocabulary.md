# ApexCloud Controlled Vocabulary

Every enum or code value that the API-driven task output expects. Never invent
values outside this catalog.

## risk_level

| Value | Meaning |
|---|---|
| `critical` | Multiple severe risk factors; immediate action required |
| `high` | Significant risk factors present; action needed this cycle |
| `medium` | Moderate risk; monitor and plan follow-up |
| `low` | Minimal risk factors; standard nurture |

## primary_action

| Value | Meaning |
|---|---|
| `collections_followup` | Overdue receivables; contact for payment |
| `technical_recovery` | SLA or usage degradation; engage solutions engineering |
| `renewal_save` | Renewal window open with risk; CS-led retention play |
| `executive_qbr` | Strategic account needing executive-level review |
| `nurture_monitor` | Low risk; standard cadence monitoring |
| `no_action` | Clean health; no immediate action needed |

## reason_codes

| Value | Trigger condition |
|---|---|
| `overdue_receivable` | Non-zero overdue balance (non-current AR buckets) |
| `low_tenure_high_churn` | Contract tenure <= 18 months + other risk signals |
| `sla_degradation` | SLA compliance < 90% in any month of the period, or declining trend |
| `nps_drop` | NPS dropped >= 15 points period-over-period, or latest NPS < 30 |
| `usage_decline` | Product usage declined > 5% across the period |
| `renewal_window` | Renewal date falls within 90 days of assessment date |
| `expansion_offset` | Open expansion pipeline > $0 for the account |
| `clean_billings` | No overdue balance, no SLA issues, no NPS drop — a positive signal |

Assign reason codes by reading the data; assign only those that the data
supports. Multiple codes may apply. Order them in the array from most severe
to least severe.

## metric_sources (QBR tasks)

Used in `metric_sources` objects to declare where each metric was sourced:

- `crm_closed_won` — Recognized revenue from CRM closed-won
- `support_export` — Support ticket counts from ticket export
- `sla_report` — SLA compliance from SLA reporting data
- `nps_survey` — NPS from survey responses
- `billing_snapshot` — Revenue from billing snapshot
- `ar_aging` — Financial data from AR aging report
- `pipeline_crm` — Pipeline data from CRM opportunities
- `event_dashboard` — Event data from event performance dashboard
- `hr_report` — HR data from HR summary report

## ticket_trend

| Value | Trigger |
|---|---|
| `improving` | Ticket count decreasing across the quarter (last month < first month) |
| `worsening` | Ticket count increasing across the quarter |
| `flat` | Ticket count unchanged across the quarter |

## review_owner

| Value | When to use |
|---|---|
| `customer_success` | Standard QBR; CS owns the review |
| `solutions_engineering` | Technical recovery focus |
| `finance_ops` | AR/collections focus |

## agenda_topics

Valid for QBR agenda lists: `partnership_overview`, `q2_metrics`,
`performance_highlights`, `q3_initiatives`, `technical_recovery`,
`commercial_expansion`

Pick exactly four ordered topics that match the account's situation.

## accuracy_band

| Value | Accuracy range |
|---|---|
| `below_70` | < 70% |
| `70_to_79` | 70.0% – 79.9% |
| `80_to_89` | 80.0% – 89.9% |
| `90_plus` | >= 90.0% |

## tenure_coefficient_direction / tenure_risk_direction

| Value | Meaning |
|---|---|
| `negative` | Longer tenure -> lower churn risk (inverse relationship) |
| `positive` | Longer tenure -> higher churn risk (direct relationship) |
| `zero` | No detectable relationship |
| `not_assessed` | Not evaluated in this analysis |

## link_status

| Value | Meaning |
|---|---|
| `linked` | AR customer matched to a CRM account |
| `unlinked` | No CRM account match found |

## Policy Codes

Every task includes a `policy_codes` object. Each key expects exactly one code
from its group. Choose the code whose description best fits the real data shape
observed in the API responses.

### risk_model_code

| Code | Condition |
|---|---|
| `RS-2` | Simple additive risk model with flat weights |
| `RS-6` | Multi-signal composite risk model with conditional weights |
| `RS-9` | ML-driven risk scoring model |

### arr_source_code

| Code | Condition |
|---|---|
| `REV-1` | ARR sourced from CRM closed-won only |
| `REV-4` | ARR sourced from billing snapshot (preferred) |
| `REV-8` | ARR sourced from blended CRM + billing average |

### support_hygiene_code

| Code | Condition |
|---|---|
| `SUP-3` | Basic ticket volume only |
| `SUP-8` | Clean-ticket methodology (excludes duplicates/spam) |
| `SUP-9` | Full SLA + severity-weighted ticket scoring |

### action_priority_code

| Code | Condition |
|---|---|
| `ACT-1` | Priority driven by ARR exposure only |
| `ACT-5` | Priority driven by composite risk score |
| `ACT-7` | Priority driven by revenue-at-risk ranking |

### receivable_trigger_code

| Code | Condition |
|---|---|
| `RCP-4` | Trigger on 30+ day buckets only |
| `RCP-7` | Trigger on all non-current aging buckets |
| `RCP-9` | Trigger on 90+ day buckets only |

### crm_match_code

| Code | Condition |
|---|---|
| `CM-2` | Match by legal_name only |
| `CM-5` | Match by legal_name + account_aliases |
| `CM-8` | Fuzzy match on normalized customer name |

### pipeline_window_code

| Code | Condition |
|---|---|
| `PW-3` | Pipeline window = current quarter only |
| `PW-6` | Pipeline window = current + next quarter |
| `PW-9` | Pipeline window = rolling 12 months |

### followup_scope_code

| Code | Condition |
|---|---|
| `FS-1` | Follow-ups for linked accounts only |
| `FS-4` | Follow-ups for all overdue customers (linked + unlinked) |
| `FS-8` | Follow-ups for high-value overdue only (>$10k) |

### model_protocol_code

| Code | Condition |
|---|---|
| `MOD-2` | Logistic regression base model |
| `MOD-7` | Gradient-boosted tree model |
| `MOD-9` | Neural network ensemble model |

### probability_scale_code

| Code | Condition |
|---|---|
| `PRB-1` | Raw probability 0.0–1.0 scale |
| `PRB-4` | Calibrated probability with Platt scaling |
| `PRB-8` | Log-odds transformed probability |

### deployment_rule_code

| Code | Condition |
|---|---|
| `DEP-3` | Deploy on validation accuracy >= 80% |
| `DEP-5` | Deploy on validation accuracy >= 85% |
| `DEP-9` | Always deploy regardless of accuracy |

### outreach_mapping_code

| Code | Condition |
|---|---|
| `OUT-2` | Map outreach action by primary risk reason |
| `OUT-6` | Map outreach action by churn probability tier |
| `OUT-8` | Map outreach action by composite risk + ARR |

### board_sort_code

| Code | Condition |
|---|---|
| `BORD-1` | Sort by risk score descending |
| `BORD-4` | Sort by risk level then ARR descending within level |
| `BORD-8` | Sort by overdue balance descending |

### exposure_formula_code

| Code | Condition |
|---|---|
| `EXP-2` | Net exposure = ARR at risk only |
| `EXP-6` | Net exposure = ARR at risk - open expansion pipeline |
| `EXP-9` | Net exposure = ARR at risk + overdue - pipeline |

### calendar_policy_code

| Code | Condition |
|---|---|
| `CAL-3` | Calendar = task-specified dates only |
| `CAL-5` | Calendar = task-specified dates + null for no_action |
| `CAL-7` | Calendar = uniform 30-day follow-up from assessment date |
