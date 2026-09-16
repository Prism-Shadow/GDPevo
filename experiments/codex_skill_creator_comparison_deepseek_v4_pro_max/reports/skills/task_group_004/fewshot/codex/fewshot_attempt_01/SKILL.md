---
name: apexcloud-retention-ops
description: Working with the ApexCloud Retention Operations API to build renewal risk queues, QBR packets, receivables reviews, churn model validation, and retention action boards. Use when the task references ApexCloud, the Retention Operations API, renewal risk analysis, churn exports, or specific retention workflows like risk ranking, QBR preparation, AR aging reconciliation, or retention action boards.
---

# ApexCloud Retention Operations

## Overview

This skill enables retention operations analysis against the ApexCloud Retention Operations API. It covers the full API surface, controlled vocabulary, and reusable workflow patterns for building risk queues, QBR packets, receivables reviews, churn validation, and retention action boards.

## API

Base URL is provided as `TASK_ENV_BASE_URL`. The API is read-only, no authentication required.

See [references/api_reference.md](references/api_reference.md) for the full endpoint catalogue: URL patterns, query parameters, response shapes, and field coverage. Load it when endpoint details are unclear.

### Key data sources by domain

| Domain | Endpoints |
|--------|----------|
| Account profile | `/api/accounts`, `/api/accounts/{id}` |
| Monthly metrics | `/api/accounts/{id}/metrics?start=YYYY-MM&end=YYYY-MM` |
| Support tickets | `/api/accounts/{id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` |
| NPS responses | `/api/accounts/{id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` |
| Billing / ARR | `/api/billing/snapshots` |
| A/R aging | `/api/finance/ar-aging` |
| CRM pipeline | `/api/opportunities` |
| HR context | `/api/hr/summary` |
| Events | `/api/events/performance` |
| Churn exports | `/exports/churn/train.csv`, `/exports/churn/validation.csv`, `/exports/churn/candidates.csv` |
| Metric extract | `/exports/account_metric_extract.csv` |

## Controlled Vocabulary

Every output must use the exact enum values listed in [references/vocabulary.md](references/vocabulary.md). Never invent risk levels, action labels, reason codes, metric sources, or policy codes. Load vocabulary.md when the task requires any controlled label.

## Precision Rules

Apply these rules to every output regardless of task type:

- Currency values: 2 decimal places (e.g., 1416439.47)
- Percentage values: 1 decimal place (e.g., 93.3)
- Counts: integers
- Churn probabilities: 3 decimal places (e.g., 0.102)
- Risk scores: integers
- Sort accounts in risk/priority descending order unless the task specifies another order
- Sort overdue followups by customer_name ascending
- Dates in YYYY-MM-DD format

## Common Computations

### ARR source selection

When both `crm_arr` (account endpoint) and `billing_arr_current` (account endpoint) are present, prefer `billing_arr_current` as the canonical ARR. When the task also needs a quarterly point-in-time ARR, use `billing_arr` from `/api/billing/snapshots` for the closest as_of date. Set `uses_billing_arr_source` to `true` when any billing ARR is used.

### Overdue balance

Sum the aging buckets that are past-due: `31_60` + `61_90` + `90_plus`. The `current` and `1_30` buckets are not overdue. All buckets are currency values in 2-decimal precision.

### Support hygiene / clean tickets

From the tickets endpoint, filter to closed tickets, then exclude duplicates (`is_duplicate: true`) and spam (`is_spam: true`). Cancelled tickets are not clean. Count remaining tickets per account for `clean_ticket_count`.

SLA compliance percentage comes directly from the metrics endpoint (`sla_compliance` field), not computed from raw tickets.

### NPS

Use the most recent non-retracted NPS response for `latest_nps`. For NPS trend/drop, compare the latest score against the prior non-retracted score in the period. If only one score exists, no trend can be assessed. Null/missing NPS scores (from metrics when `survey_status: "missing"`) should be ignored.

### Tenure risk

Accounts with `contract_tenure_months` <= 24 are high-tenure-churn risk. Tenure risk direction is `negative` when younger accounts carry higher churn risk in the portfolio.

### Renewal window

An account is in its renewal window when its `renewal_date` falls within the analysis period or the following 90 days.

### Usage trend

Compare the last month's `product_usage` from metrics against the first month's in the period. A decline is a risk signal.

### Cross-referencing AR aging to accounts

AR aging records have `customer_name`. Match to accounts via `legal_name` or entries in `account_aliases`. Records that match are `linked`, with the `account_id` populated. Unmatched records are `unlinked`, with `account_id: null`.

## Workflow Patterns

### Risk Queue (renewal risk ranking)

1. Fetch account profiles for the specified account_ids from `/api/accounts`
2. For each account, fetch metrics, tickets, NPS, billing snapshot, and AR aging
3. For each account, compute: overdue balance, clean ticket count, latest NPS, SLA compliance trend, usage trend, tenure risk flag, renewal proximity
4. Assign risk signals (reason codes) cumulatively
5. Compute a risk score as a composite integer
6. Assign risk_level based on score thresholds
7. Assign primary_action by choosing the highest-priority action that matches the risk profile
8. Rank by risk score descending, take the top N
9. Fill portfolio_summary and model_checks

See [references/vocabulary.md](references/vocabulary.md) for reason codes and actions.

### QBR Packet (single-account quarterly review)

1. Fetch account profile from `/api/accounts/{id}`
2. Fetch monthly metrics for the quarter
3. Fetch tickets and NPS for the quarter
4. Populate month-by-month qbr_metrics from the metrics endpoint
5. Compute highlights (averages, peaks, trends)
6. Assign metric_sources using controlled source enums
7. Build agenda_topics from the controlled agenda enum list
8. Set review_plan fields

### Receivables and Pipeline Review

1. Fetch AR aging for the target quarter from `/api/finance/ar-aging`
2. Filter to records with non-zero overdue balance (31_60 + 61_90 + 90_plus > 0)
3. Fetch all accounts from `/api/accounts`
4. Link each AR record to an account by matching customer_name to legal_name or aliases
5. Fetch opportunities for the target quarter from `/api/opportunities`
6. Summarize pipeline (won, lost, open, win_rate, top open product line)
7. Fetch HR and events context if requested
8. Build overdue_followups sorted by customer_name ascending

### Churn Model Validation and Ranking

1. Fetch `/exports/churn/train.csv` and `/exports/churn/validation.csv`
2. Count rows, count feature columns (exclude customer_id and Churn label)
3. Compute accuracy: the validation dataset has a predicted vs actual churn comparison; use the proportion of correct predictions
4. Assign accuracy_band from the thresholds
5. Fetch `/exports/churn/candidates.csv`
6. Filter to the specified candidate account_ids
7. Rank by predicted churn probability descending, take top N
8. Assign outreach_action and reason_code for each based on candidate data columns

### Retention Action Board

1. Fetch account profiles for specified account_ids
2. For each: metrics, tickets, NPS, billing snapshot, AR aging, opportunities
3. Build risk assessment per account with all reason codes
4. Rank all accounts (not just top N) by risk priority
5. Assign primary_action and next_touch_due_date using the followup calendar from the task
6. Compute segment_summary (strategic vs enterprise, ARR at risk, expansion pipeline, net revenue exposure)
7. Fill the followup_calendar object

## Policy Codes

Policy codes are methodology tags that document which approach was used. Select exactly one from each code group based on the methodology applied:

| Code Group | Values | Selection Rule |
|-----------|--------|---------------|
| risk_model_code | RS-2, RS-6, RS-9 | RS-6 for multi-factor composite risk scoring |
| arr_source_code | REV-1, REV-4, REV-8 | REV-4 when billing snapshots are the ARR source |
| support_hygiene_code | SUP-3, SUP-8, SUP-9 | SUP-8 when clean-ticket-count hygiene is used |
| action_priority_code | ACT-1, ACT-5, ACT-7 | ACT-5 for hybrid overdue+sentiment+technical prioritization |
| receivable_trigger_code | RCP-4, RCP-7, RCP-9 | RCP-7 for combined-bucket overdue trigger |
| crm_match_code | CM-2, CM-5, CM-8 | CM-5 for name+alias cross-reference matching |
| pipeline_window_code | PW-3, PW-6, PW-9 | PW-6 for quarter-boundary pipeline window |
| followup_scope_code | FS-1, FS-4, FS-8 | FS-4 for overdue-only followup scope |
| model_protocol_code | MOD-2, MOD-7, MOD-9 | MOD-7 for export-based validation protocol |
| probability_scale_code | PRB-1, PRB-4, PRB-8 | PRB-4 for 0-1 probability scale |
| deployment_rule_code | DEP-3, DEP-5, DEP-9 | DEP-5 for top-5 deployment rule |
| outreach_mapping_code | OUT-2, OUT-6, OUT-8 | OUT-2 for candidate-data-driven outreach mapping |
| board_sort_code | BORD-1, BORD-4, BORD-8 | BORD-4 for risk-priority board sort |
| exposure_formula_code | EXP-2, EXP-6, EXP-9 | EXP-6 for ARR-minus-expansion exposure formula |
| calendar_policy_code | CAL-3, CAL-5, CAL-7 | CAL-5 for action-anchored followup calendar |

## API Aggregation Note

Some endpoints return paginated or full lists. `/api/accounts` returns all accounts in an `accounts` array. Filter in code by `account_id`. Similarly filter `/api/billing/snapshots`, `/api/finance/ar-aging`, and `/api/opportunities` by account_id, date range, or quarter as needed. The metrics, tickets, and NPS endpoints are already account-scoped.
