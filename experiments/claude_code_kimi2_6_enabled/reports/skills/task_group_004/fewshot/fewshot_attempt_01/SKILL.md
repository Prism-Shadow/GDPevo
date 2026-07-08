# ApexCloud Retention Operations API — CRM Analytics Skill

## Overview

This skill covers tasks that consume the **ApexCloud Retention Operations API** (`http://127.0.0.1:8074`) to produce structured CRM analytics deliverables for Customer Success, Finance, and Data Science teams. The API returns account profiles, billing snapshots, support health, NPS, receivables, product usage, expansion opportunities, HR/event context, and churn-model exports.

The prompt determines the deliverable type. Always read `input/payloads/answer_template.json` to confirm the exact output schema.

---

## API Base and Endpoint Families

- **Base URL:** `http://127.0.0.1:8074`
- **Account endpoints:** `/api/accounts/{account_id}` plus sub-resources:
  - `/api/accounts/{account_id}/profile`
  - `/api/accounts/{account_id}/billing_snapshot`
  - `/api/accounts/{account_id}/support_health`
  - `/api/accounts/{account_id}/nps`
  - `/api/accounts/{account_id}/receivables`
  - `/api/accounts/{account_id}/product_usage`
  - `/api/accounts/{account_id}/expansion_opportunities`
  - `/api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM`
  - `/api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD`
- **Finance:** `/api/finance/ar-aging`
- **CRM:** `/api/accounts`, `/api/opportunities`
- **Operations:** `/api/hr/summary`, `/api/events/performance`
- **Exports:** `/exports/churn/train.csv`, `/exports/churn/validation.csv`, `/exports/churn/candidates.csv`

**Habit:** When a task lists specific `account_ids`, call the relevant per-account endpoints for every listed ID. When a task asks for a rollup (collections board, churn validation), start with the rollup endpoint (`/api/finance/ar-aging`, `/exports/churn/candidates.csv`) and link downstream.

---

## Deliverable Types and Routing Rules

| Prompt Keyword | Deliverable | Primary Endpoints |
|---|---|---|
| "retention action board" | Retention Action Board | Per-account profile, billing, support, NPS, receivables, usage, expansion |
| "QBR" / "QBR metrics packet" / "QBR brief" | QBR Metrics Packet | Per-account metrics, tickets, NPS |
| "collections" / "receivables" / "overdue-receivables" | Collections Operations Board | `/api/finance/ar-aging`, `/api/accounts`, `/api/opportunities`, `/api/hr/summary`, `/api/events/performance` |
| "churn-model validation" / "churn exports" | Churn Model Validation Report | `/exports/churn/train.csv`, `validation.csv`, `candidates.csv` |

**Rule:** The prompt explicitly names the deliverable. Always match the output schema to `answer_template.json`; do not assume one template fits all tasks.

---

## Global Output Conventions

Apply these precision rules across all deliverables unless the prompt overrides:

| Data Type | Precision | Example |
|---|---|---|
| Currency | 2 decimals | `1260762.32` |
| Percentages | 1 decimal | `93.3` |
| Probabilities | 3 decimals | `0.102` |
| Counts | Integers | `13` |
| Dates | `YYYY-MM-DD` | `2026-07-15` |
| Month labels | `YYYY-MM` | `2026-04` |

---

## Controlled Vocabularies

### Risk Levels
`critical`, `high`, `medium`, `low`

### Primary Actions
`collections_followup`, `technical_recovery`, `renewal_save`, `executive_qbr`, `nurture_monitor`, `no_action`

### Reason Codes
`overdue_receivable`, `nps_drop`, `sla_degradation`, `usage_decline`, `renewal_window`, `expansion_offset`, `clean_billings`, `low_tenure_high_churn`

### Link Status (Collections)
`linked`, `unlinked`

### Ticket Trend
`improving`, `worsening`, `flat`

### Metric Sources
`crm_closed_won`, `support_export`, `sla_report`, `nps_survey`, `billing_snapshot`, `ar_aging`, `pipeline_crm`, `event_dashboard`, `hr_report`

### Review Owners
`solutions_engineering`, `customer_success`, `finance_ops`

### Agenda Topics (QBR)
`partnership_overview`, `q2_metrics`, `performance_highlights`, `q3_initiatives`, `technical_recovery`, `commercial_expansion`

### Accuracy Bands (Churn)
`below_70`, `70_to_79`, `80_to_89`, `90_plus`

### Tenure Coefficient Direction
`negative`, `positive`, `zero`

---

## 1. Retention Action Board Workflow

### Output Schema
```json
{
  "action_board": [...],
  "segment_summary": {...},
  "followup_calendar": {...},
  "policy_codes": {...}
}
```

### Action Board Entry Fields
| Field | Source / Rule |
|---|---|
| `rank` | 1-based sort order (see Ranking Rules) |
| `account_id` | From prompt list |
| `risk_level` | Derived from reason-code severity and count (see Risk Scoring) |
| `primary_action` | Highest-priority action mapped from detected reason codes (see Action Priority) |
| `current_arr` | From `billing_snapshot` |
| `expansion_pipeline` | Sum of open expansion opportunities for the account in the period |
| `overdue_balance` | From `receivables` as-of the board date |
| `next_touch_due_date` | Look up `primary_action` in the `followup_calendar` provided in the prompt; `null` if `no_action` |
| `reason_codes` | Array of all applicable reason codes, deduplicated, sorted alphabetically |

### Risk Scoring Heuristics
- **critical:** 4+ risk factors, or a severe combination such as `renewal_window` + `nps_drop` + `sla_degradation` + `usage_decline`.
- **high:** 3–4 risk factors including at least one high-severity factor (`overdue_receivable`, `renewal_window`, `usage_decline`, `nps_drop`).
- **medium:** 1–2 risk factors, or `renewal_window` / `overdue_receivable` without enough severity for high.
- **low:** 0–1 minor factors (e.g., only `sla_degradation` or only `expansion_offset`).

### Action Priority (highest wins)
1. `collections_followup` — if `overdue_receivable` is present.
2. `technical_recovery` — if `nps_drop` + `sla_degradation` + `usage_decline` are present together, or if technical health is severely degraded.
3. `renewal_save` — if `renewal_window` is present and not overridden by collections or technical recovery.
4. `executive_qbr` — reserved for strategic escalations (rarely primary).
5. `nurture_monitor` — for low-risk accounts with minor flags.
6. `no_action` — when risk level is `low` and no urgent factor exists.

### Ranking Rules
1. Sort by `risk_level` descending: `critical` → `high` → `medium` → `low`.
2. Within the same risk level, sort by `current_arr` descending.
3. Assign `rank` sequentially starting at 1.

### Segment Summary
| Field | Calculation |
|---|---|
| `strategic_accounts` | Count of accounts where `tier == "strategic"` |
| `enterprise_accounts` | Count of accounts where `tier == "enterprise"` |
| `arr_at_risk` | Sum of `current_arr` for all accounts with `risk_level != "low"` |
| `open_expansion_pipeline` | Sum of `expansion_pipeline` across **all** accounts |
| `net_revenue_exposure` | `arr_at_risk - open_expansion_pipeline` |

### Follow-Up Calendar
The prompt provides due dates by action. Map them exactly:
```json
{
  "collections_followup": "2026-07-15",
  "technical_recovery": "2026-07-18",
  "renewal_save": "2026-07-22",
  "executive_qbr": "2026-07-29",
  "nurture_monitor": "2026-08-05"
}
```
If the prompt omits an action, omit it from the calendar.

### Policy Codes
Policy codes are **predefined sets** that correspond to the analysis-period type. Use the set that matches the prompt's period:

| Period Type | Code Set |
|---|---|
| Q1 (3 months, e.g., 2026-01 to 2026-03) | `RS-2`, `REV-1`, `SUP-3`, `ACT-1`, `BORD-1`, `EXP-2`, `CAL-3` |
| Q2 (3 months, e.g., 2026-04 to 2026-06) | `RS-6`, `REV-4`, `SUP-8`, `ACT-5`, `BORD-4`, `EXP-6`, `CAL-5` |
| 12-month rolling | `RS-9`, `REV-8`, `SUP-9`, `ACT-7`, `BORD-8`, `EXP-9`, `CAL-7` |

Map keys:
- `risk_model_code` → `RS-*`
- `arr_source_code` → `REV-*`
- `support_hygiene_code` → `SUP-*`
- `action_priority_code` → `ACT-*`
- `board_sort_code` → `BORD-*`
- `exposure_formula_code` → `EXP-*`
- `calendar_policy_code` → `CAL-*`

---

## 2. QBR Metrics Packet Workflow

### Output Schema
```json
{
  "qbr_metrics": [...],
  "highlights": {...},
  "metric_sources": {...},
  "review_plan": {...},
  "agenda_topics": [...]
}
```

### QBR Metrics (monthly)
For each month in the quarter (3 entries):
- `month`: `YYYY-MM`
- `revenue`: monthly revenue from `crm_closed_won` or billing metrics
- `support_tickets`: ticket count for the month
- `sla_compliance_pct`: SLA compliance percentage
- `nps_score`: integer NPS score (can be `null` if missing)

### Highlights
| Field | Rule |
|---|---|
| `average_revenue` | Mean of the 3 monthly revenues |
| `peak_revenue_month` | Month with highest revenue |
| `peak_revenue` | Highest monthly revenue |
| `max_sla_month` | Month with highest `sla_compliance_pct` |
| `max_sla_pct` | Highest SLA value |
| `peak_nps_month` | Month with highest NPS score |
| `peak_nps_score` | Highest NPS value |
| `ticket_trend` | `improving` if ticket count decreased month-over-month toward the end, `worsening` if increased, `flat` if stable |

### Metric Sources
Populate with the canonical source enum values:
```json
{
  "revenue": "crm_closed_won",
  "support_tickets": "support_export",
  "sla_compliance": "sla_report",
  "nps": "nps_survey"
}
```

### Review Plan
- `review_owner`: `customer_success` for standard QBRs; escalate to `solutions_engineering` if significant technical flags exist.
- `review_due_date`: Use the date given in the prompt.
- `needs_technical_signoff`: `true` if the account has `sla_degradation`, `usage_decline`, or `technical_recovery` flagged; otherwise `false`.

### Agenda Topics
Select **exactly four** ordered topics from the enum. Common ordering:
1. `partnership_overview`
2. `q2_metrics` (or quarter-appropriate metrics topic)
3. `technical_recovery` (if technical issues exist) or `performance_highlights`
4. `q3_initiatives` (or next-quarter topic)

---

## 3. Collections Operations Board Workflow

### Output Schema
```json
{
  "financial_summary": {...},
  "pipeline_summary": {...},
  "overdue_followups": [...],
  "ops_context": {...},
  "policy_codes": {...}
}
```

### Workflow
1. Query `/api/finance/ar-aging` as-of the prompt's A/R date.
2. Filter to customers with overdue balances in older aging buckets.
3. Attempt to link each A/R customer to a CRM account via `/api/accounts`.
4. Query `/api/opportunities` for the quarter to build pipeline summary.
5. Query `/api/hr/summary` and `/api/events/performance` for ops context.

### Financial Summary
| Field | Rule |
|---|---|
| `overdue_client_count` | Total distinct overdue customers |
| `overdue_total` | Sum of all overdue balances |
| `linked_followup_count` | Overdue customers successfully linked to a CRM `account_id` |
| `unlinked_followup_count` | Overdue customers with no CRM linkage (`account_id == null`) |

### Pipeline Summary (Quarter scope)
| Field | Rule |
|---|---|
| `won_count` | Closed-won opportunities in the quarter |
| `won_revenue` | Sum of closed-won revenue |
| `lost_count` | Closed-lost opportunities |
| `open_count` | Open opportunities |
| `open_pipeline` | Sum of open pipeline value |
| `win_rate_pct` | `won_count / (won_count + lost_count) * 100`, 1 decimal |
| `top_open_product_line` | Product line with highest open pipeline value |

### Overdue Follow-Ups
Each entry:
- `customer_name`: from A/R record
- `link_status`: `linked` if `account_id` is resolved, else `unlinked`
- `account_id`: CRM account ID or `null`
- `overdue_balance`: from A/R
- `due_date`: the collections follow-up date given in the prompt
- `primary_action`: `collections_followup`

**Sort:** ascending by `customer_name`.

### Ops Context
Include HR and event data exactly as returned by `/api/hr/summary` and `/api/events/performance` for the requested quarter/event:
- `hr_headcount`
- `unpaid_claims_total`
- `event_orders`
- `event_revenue`

### Policy Codes (Collections)
Use the set that matches the quarter:
- Q2 collections: `RCP-7`, `CM-5`, `PW-6`, `FS-4`
- Keys: `receivable_trigger_code`, `crm_match_code`, `pipeline_window_code`, `followup_scope_code`

---

## 4. Churn Model Validation Workflow

### Output Schema
```json
{
  "model_validation": {...},
  "risk_ranking": [...],
  "cohort_checks": {...},
  "model_policy_codes": {...}
}
```

### Workflow
1. Read `/exports/churn/train.csv` and `/exports/churn/validation.csv`.
2. Compute row counts, feature count, and accuracy.
3. Read `/exports/churn/candidates.csv`.
4. Filter to the `account_ids` specified in the prompt.
5. Sort by `predicted_churn_probability` descending.
6. Return the top N candidates (the prompt specifies the count, e.g., top 5).

### Model Validation
| Field | Rule |
|---|---|
| `training_rows` | Row count of train.csv |
| `validation_rows` | Row count of validation.csv |
| `feature_count` | Number of feature columns (exclude ID/target columns) |
| `accuracy_pct` | Model accuracy, 1 decimal |
| `accuracy_band` | `below_70`, `70_to_79`, `80_to_89`, or `90_plus` |
| `tenure_coefficient_direction` | `negative`, `positive`, or `zero` based on the tenure feature coefficient |

### Risk Ranking
| Field | Rule |
|---|---|
| `rank` | 1-based by `predicted_churn_probability` descending |
| `customer_id` | Account ID |
| `predicted_churn_probability` | From candidates.csv, 3 decimals |
| `outreach_action` | Map using the same action priority as Retention Boards: overdue → `collections_followup`, low tenure + high churn → `renewal_save`, clean billings → `nurture_monitor` |
| `reason_code` | `overdue_receivable`, `low_tenure_high_churn`, or `clean_billings` based on account context |

### Cohort Checks
| Field | Rule |
|---|---|
| `past_due_shortlist_count` | Count of ranked candidates with `reason_code == "overdue_receivable"` |
| `low_tenure_shortlist_count` | Count with `reason_code == "low_tenure_high_churn"` |
| `average_probability_top5` | Mean probability of the returned top-5 candidates, 3 decimals |

### Model Policy Codes
Select the set matching the analysis period:
- Standard Q2 validation: `MOD-7`, `PRB-4`, `DEP-5`, `OUT-2`
- Keys: `model_protocol_code`, `probability_scale_code`, `deployment_rule_code`, `outreach_mapping_code`

---

## Common Pitfalls

1. **Ignoring the template.** Always read `answer_template.json`; deliverable shapes differ significantly across task types.
2. **Wrong date granularity.** Retention boards use `YYYY-MM-DD`; QBR metrics use `YYYY-MM` for month labels.
3. **Precision errors.** Currency must be exactly 2 decimals; probabilities exactly 3. Do not round prematurely.
4. **Omitting nulls.** `next_touch_due_date` is `null` for `no_action` accounts. `account_id` is `null` for unlinked collections customers.
5. **Sorting mistakes.** Retention boards sort by risk then ARR descending. Collections follow-ups sort by `customer_name` ascending. Churn rankings sort by probability descending.
6. **Hard-coding policy codes.** Policy codes are not universal; they map to the quarter or period length stated in the prompt.
7. **Mixing action priorities.** Collections always beats technical recovery, which beats renewal save, when multiple reason codes are present.
8. **Missing expansion in exposure.** `net_revenue_exposure = arr_at_risk - open_expansion_pipeline`. Do not subtract only for at-risk accounts; use the total open pipeline.
9. **QBR agenda length.** Must be exactly four topics, ordered logically.
10. **Collections linkage.** An A/R customer may match a CRM account by name but not by exact ID; resolve linkage carefully and set `link_status` accordingly.

---

## Example Policy-Code Mapping Summary

| Context | Codes |
|---|---|
| Retention Board — Q1 (3-mo) | `RS-2`, `REV-1`, `SUP-3`, `ACT-1`, `BORD-1`, `EXP-2`, `CAL-3` |
| Retention Board — Q2 (3-mo) | `RS-6`, `REV-4`, `SUP-8`, `ACT-5`, `BORD-4`, `EXP-6`, `CAL-5` |
| Retention Board — 12-mo rolling | `RS-9`, `REV-8`, `SUP-9`, `ACT-7`, `BORD-8`, `EXP-9`, `CAL-7` |
| Collections Board — Q2 | `RCP-7`, `CM-5`, `PW-6`, `FS-4` |
| Churn Model — Q2 validation | `MOD-7`, `PRB-4`, `DEP-5`, `OUT-2` |

If the prompt uses a different quarter or window, carry the numeric suffix pattern forward proportionally (e.g., Q3 3-month retention likely uses the next sequential set in the same family).
