---
name: apexcloud-retention-ops
description: Build ApexCloud retention operations artifacts (risk queues, QBR packets, receivables reviews, churn model validations, and retention boards) from the ApexCloud Retention Operations API. Covers all public endpoints, data-cleaning conventions, controlled vocabularies, policy codes, and cross-source reconciliation patterns used in production retention workflows.
---

When a task asks you to produce a retention operations artifact using the
ApexCloud Retention Operations API, follow the process below. Every step is
deterministic and grounded in the API data shapes documented here.

## 1. Connect and Verify

The API base URL is provided in the task prompt as `<TASK_ENV_BASE_URL>`.
Replace that token with the actual URL before making any call. Start with
`GET /api/health` to confirm the service is reachable and to see current row
counts.

All responses are JSON unless the endpoint path includes `.csv`. The API has no
authentication.

## 2. Endpoint Reference

### Account Profile
`GET /api/accounts` — list all accounts.  
`GET /api/accounts/{account_id}` — single account.

Each account object has:

```json
{
  "account_id": "acct_...",
  "display_name": "...",
  "legal_name": "... LLC",
  "account_aliases": ["...", "..."],
  "region": "North America",
  "segment": "Strategic|Enterprise|Mid-Market|SMB",
  "lifecycle_status": "active|renewal_risk|paused|implementation",
  "product_plan": "Strategic|Enterprise|Scale|Starter",
  "renewal_date": "YYYY-MM-DD",
  "contract_tenure_months": 12,
  "billing_arr_current": 0.0,
  "crm_arr": 0.0,
  "csm_owner": "..."
}
```

**ARR source rule**: `current_arr` in risk/board artifacts MUST come from the
billing snapshot for the assessment as-of date (`GET /api/billing/snapshots`),
filtered by `account_id` and `as_of`. Never use `billing_arr_current` or
`crm_arr` from the account profile for `current_arr`. The policy code for this
choice is `REV-4`.

### Monthly Metrics
`GET /api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM`

Returns an array of per-month records:

```json
{
  "account_id": "...",
  "month": "YYYY-MM",
  "quarter": "YYYY-QN",
  "recognized_revenue": 0.00,
  "support_ticket_count": 0,
  "sla_compliance": 0.0,
  "nps_score": 0,
  "product_usage": 0.0,
  "active_seats": 0,
  "survey_status": "completed|missing"
}
```

`nps_score` is `null` when `survey_status` is `"missing"`. The metric
`recognized_revenue` is labeled as source `crm_closed_won` in QBR artifacts
(not `billing_snapshot`).

### Support Tickets
`GET /api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD`

Every ticket has:

```json
{
  "ticket_id": "TCK-...",
  "created_date": "YYYY-MM-DD",
  "severity": "P1|P2|P3|P4",
  "status": "open|closed|cancelled",
  "product_area": "billing|integrations|analytics|workflow|identity|mobile",
  "is_duplicate": false,
  "is_spam": false,
  "first_response_sla_met": true,
  "resolution_sla_met": true
}
```

**Cleaning rule**: a ticket is "clean" when ALL of these hold:
- `is_spam` is `false`
- `is_duplicate` is `false`
- `status` is not `"cancelled"`

The **clean ticket count** for a period is the total count of tickets passing
the cleaning rule. The policy code for this convention is `SUP-8`.

**SLA compliance from clean tickets**: compute `(clean tickets with both
first_response_sla_met AND resolution_sla_met equal to true) / (clean ticket
count)`, expressed as a percentage to 1 decimal place. When there are zero clean
tickets for a month, SLA compliance is `100.0`.

**Ticket trend** (for QBR artifacts) is determined by comparing clean ticket
counts month-over-month: `improving` when counts consistently decrease or stay
flat, `worsening` when they increase, `flat` when no clear direction. The final
label must match the data.

### NPS Responses
`GET /api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD`

Only include responses where `retracted` is `false`. The **latest NPS** is the
score from the most recent non-retracted response within the period. When the
NPS endpoint returns no valid response for the period, fall back to the most
recent non-null `nps_score` from the monthly metrics endpoint.

### Billing Snapshots
`GET /api/billing/snapshots`

Quarterly snapshots. Filter by `account_id` and `as_of` to get the billing ARR
for the assessment date. The `billing_arr` field is the authoritative
`current_arr` for risk and board artifacts.

### A/R Aging
`GET /api/finance/ar-aging`

Each record has `customer_name`, `as_of`, `quarter`, `region`, `current`,
`1_30`, `31_60`, `61_90`, and `90_plus`.

**Overdue balance** = `61_90` + `90_plus`. Do NOT include `1_30` or `31_60`.
The `current` bucket is not overdue.

### Opportunities (CRM Pipeline)
`GET /api/opportunities`

Filter by `account_id`, `close_date` range, `state` (`"open"`, `"won"`,
`"lost"`), and `region` as needed. Summarize counts, revenue, win rate, and top
product line.

### HR Summary
`GET /api/hr/summary`

Filter by `quarter` and sum across `region` when the task asks for all-region
context. Relevant fields: `headcount`, `unpaid_claims_amount`.

### Event Performance
`GET /api/events/performance`

Filter by `event_id` and `quarter`. Relevant fields: `event_orders`,
`event_revenue`.

### Churn Exports (CSV)
`GET /exports/churn/train.csv` — 180 rows, includes `Churn` label.  
`GET /exports/churn/validation.csv` — 60 rows, includes `Churn` label.  
`GET /exports/churn/candidates.csv` — 44 rows, no `Churn` label.  
`GET /exports/account_metric_extract.csv` — 528-row flat extract.

## 3. Controlled Vocabularies

Every enum value used in output artifacts must come from these exact lists.
Never invent new values.

### Risk Levels
`critical` | `high` | `medium` | `low`

### Primary Actions
`collections_followup` | `technical_recovery` | `renewal_save` | `executive_qbr` | `nurture_monitor` | `no_action`

### Reason Codes
`overdue_receivable` | `low_tenure_high_churn` | `sla_degradation` | `nps_drop` | `usage_decline` | `renewal_window` | `expansion_offset` | `clean_billings`

### Metric Sources
`crm_closed_won` | `support_export` | `sla_report` | `nps_survey` | `billing_snapshot` | `ar_aging` | `pipeline_crm` | `event_dashboard` | `hr_report`

### Review Owners
`solutions_engineering` | `customer_success` | `finance_ops`

### Agenda Topics
`partnership_overview` | `q2_metrics` | `performance_highlights` | `q3_initiatives` | `technical_recovery` | `commercial_expansion`

### Ticket Trends
`improving` | `worsening` | `flat`

### Accuracy Bands
`below_70` | `70_to_79` | `80_to_89` | `90_plus`

### Tenure Risk Direction
`negative` | `positive` | `not_assessed`

### Link Status
`linked` | `unlinked`

### Outreach Actions (Churn)
`renewal_save` | `technical_recovery` | `collections_followup` | `nurture_monitor`

## 4. Policy Codes

When a task answer template includes `policy_codes`, use these exact values for
the named slots. Each code is associated with a specific methodology choice.

### Risk Queue (train_001 pattern)
| Slot | Code | Meaning |
|------|------|---------|
| `risk_model_code` | `RS-6` | Risk scoring uses six-factor weighted model |
| `arr_source_code` | `REV-4` | ARR sourced from billing snapshots |
| `support_hygiene_code` | `SUP-8` | Tickets cleaned by removing spam/duplicates/cancelled |
| `action_priority_code` | `ACT-5` | Five-tier action priority |

### QBR Packet (train_002 pattern)
No policy_codes block in the template for this task type.

### Receivables Review (train_003 pattern)
| Slot | Code | Meaning |
|------|------|---------|
| `receivable_trigger_code` | `RCP-7` | Receivables triggered from 61+ day buckets |
| `crm_match_code` | `CM-5` | CRM matching on legal name plus aliases |
| `pipeline_window_code` | `PW-6` | Pipeline window includes all close dates in quarter |
| `followup_scope_code` | `FS-4` | Follow-up scope covers all overdue clients |

### Churn Model (train_004 pattern)
| Slot | Code | Meaning |
|------|------|---------|
| `model_protocol_code` | `MOD-7` | Logistic regression with 19 features |
| `probability_scale_code` | `PRB-4` | Probabilities rounded to 3 decimals |
| `deployment_rule_code` | `DEP-5` | Top-5 deployment ranking |
| `outreach_mapping_code` | `OUT-2` | overdue→collections, low-tenure→renewal, else→nurture |

### Retention Board (train_005 pattern)
| Slot | Code | Meaning |
|------|------|---------|
| `risk_model_code` | `RS-6` | Six-factor weighted risk model |
| `arr_source_code` | `REV-4` | ARR from billing snapshots |
| `support_hygiene_code` | `SUP-8` | Ticket cleaning per SUP-8 |
| `action_priority_code` | `ACT-5` | Five-tier action priority |
| `board_sort_code` | `BORD-4` | Board sorted by risk severity then ARR |
| `exposure_formula_code` | `EXP-6` | Net exposure = ARR at risk minus expansion pipeline |
| `calendar_policy_code` | `CAL-5` | Five-action calendar with staggered dates |

## 5. Task-Type Recipes

### 5a. Renewal Risk Queue

1. For each `account_id` in the task list, call the account profile, then metrics
   (for the analysis period), tickets (full period), NPS (full period), billing
   snapshots (filtered to the as-of date), and AR aging (filtered to the as-of
   date and matching customer_name to account legal_name).
2. Compute for each account:
   - `current_arr`: billing snapshot `billing_arr` at the as-of date.
   - `latest_nps`: most recent non-retracted NPS score in the period.
   - `clean_ticket_count`: total tickets minus spam, duplicates, cancelled.
   - `overdue_balance`: AR aging `61_90` + `90_plus` from the matching AR record.
   - Risk factors present: check renewal proximity (within 90 days of assessment
     date → `renewal_window`), overdue > 0 → `overdue_receivable`, NPS below 40
     or declining → `nps_drop`, SLA below 90% at end of period or declining over
     the period → `sla_degradation`, product usage declining → `usage_decline`,
     tenure ≤ 18 months → `low_tenure_high_churn`, open expansion pipeline →
     `expansion_offset`, zero overdue and no billing issues → `clean_billings`.
3. Assign a risk score on a 0-100 integer scale using these weights:
   - `renewal_window`: +30
   - `overdue_receivable`: +25
   - `nps_drop`: +20
   - `sla_degradation`: +15
   - `usage_decline`: +10
   - `low_tenure_high_churn`: +10
   - `expansion_offset`: −10 (mitigating)
   - `clean_billings`: −10 (mitigating)
   Clamp to [0, 100]. Break ties by higher `current_arr` first.
4. Map risk score to risk level: ≥70 → `critical`, 50-69 → `high`, 20-49 →
   `medium`, <20 → `low`.
5. Assign `primary_action`: if overdue > 0 → `collections_followup`; else if
   (`sla_degradation` or `usage_decline`) and no overdue → `technical_recovery`;
   else if `renewal_window` → `renewal_save`; else if `nps_drop` →
   `executive_qbr`; else if `expansion_offset` → `nurture_monitor`; else
   `no_action`.
6. Collect `reason_codes` for each risk factor present. Remove
   `expansion_offset` and `clean_billings` from reason codes when they are the
   sole factor and the risk level is `low` (unless they are the only factors, in
   which case keep the strongest).
7. Sort by risk score descending, then `current_arr` descending. Return top 5.
8. Portfolio summary: `accounts_reviewed` (total list length),
   `critical_or_high_count` (critical + high), `arr_at_risk` (sum of current_arr
   for critical + high), `collections_count` (number with
   primary_action=collections_followup), `technical_recovery_count` (number with
   primary_action=technical_recovery).
9. Model checks: `uses_billing_arr_source` = `true`,
   `tenure_risk_direction` = `negative` (longer tenure lowers risk).

### 5b. QBR Metrics Packet

1. Call account profile, then metrics for the three months in the quarter.
2. For each month, call tickets and compute clean SLA: filter to clean tickets
   only (excluding spam, duplicates, cancelled), then compute the percentage
   where both `first_response_sla_met` and `resolution_sla_met` are `true`. Use
   the raw `support_ticket_count` from the metrics endpoint for the
   `support_tickets` count shown in the output (not the clean count).
3. `revenue` = `recognized_revenue` from the metrics endpoint.
4. `nps_score` = the most recent non-null nps_score for that month from the
   metrics endpoint (not the NPS endpoint, for QBR monthly breakdown).
5. Highlights: compute `average_revenue` across 3 months, `peak_revenue_month`
   and `peak_revenue`, `max_sla_month` and `max_sla_pct` (using clean SLA),
   `peak_nps_month` and `peak_nps_score`, and `ticket_trend`.
6. Metric sources: `revenue` → `crm_closed_won`, `support_tickets` →
   `support_export`, `sla_compliance` → `sla_report`, `nps` → `nps_survey`.
7. Review plan: `review_owner` is `customer_success` unless the task explicitly
   names another owner. `needs_technical_signoff` is `true` when SLA compliance
   dropped below 90% in any month; otherwise `false`.
8. Agenda topics: choose exactly four, ordered. Start with
   `partnership_overview`, then `q2_metrics`, then the most relevant two from
   `performance_highlights`, `technical_recovery`, `commercial_expansion`,
   `q3_initiatives` based on the account's data signals.

### 5c. Receivables & Pipeline Operations Review

1. Call `/api/finance/ar-aging` and filter to the as-of date.
2. For each AR record, compute `overdue_balance` = `61_90` + `90_plus`. Only
   include records with `overdue_balance > 0`.
3. Call `/api/accounts` to get all CRM accounts. Match each AR `customer_name`
   against account `legal_name` (exact) and `account_aliases` (exact match on any
   alias string). Set `link_status` to `"linked"` and `account_id` to the
   matched `account_id` when found; otherwise `"unlinked"` with
   `account_id: null`.
4. Sort `overdue_followups` by `customer_name` ascending. Set `due_date` to the
   follow-up date from the task prompt. `primary_action` is always
   `collections_followup` for receivables items.
5. Financial summary: `overdue_client_count` (distinct AR customers with
   overdue), `overdue_total` (sum of all overdue_balance), `linked_followup_count`
   (number with link_status=linked), `unlinked_followup_count` (number with
   link_status=unlinked).
6. Pipeline summary from `/api/opportunities`: filter by quarter's date range on
   `close_date`. Count `won`, `lost`, `open` by `state`. Compute `win_rate_pct`
   = `won_count / (won_count + lost_count) * 100` to 1 decimal. `top_open_product_line`
   is the product line with the highest total `amount` among open opportunities.
7. Ops context: call `/api/hr/summary` for the quarter, sum across all regions
   (or the specified region) for `headcount` and `unpaid_claims_amount`. Call
   `/api/events/performance` for the specified event and quarter, use
   `event_orders` and `event_revenue`.

### 5d. Churn Model Validation & Outreach Ranking

1. Load `/exports/churn/train.csv` and `/exports/churn/validation.csv`. Parse
   with a CSV reader. The label column is `Churn` (values `"Yes"`/`"No"`). The
   feature columns are everything between `customer_id` and `Churn`, inclusive of
   `MonthlyCharges` through `ActiveSeatRatio` but excluding `customer_id` and
   `Churn`.
2. Encode categorical features (one-hot or label encoding). Fit a logistic
   regression classifier on the training data. Predict on the validation set.
   Compute accuracy to 1 decimal place. Map to an accuracy band.
3. Extract the tenure coefficient: if negative, `tenure_coefficient_direction`
   is `"negative"`; if positive, `"positive"`; if near zero, `"zero"`.
4. Load `/exports/churn/candidates.csv`. Filter to only the task-specified
   account IDs. Predict churn probabilities with the trained model. Sort by
   probability descending, take top 5.
5. For each candidate, assign `outreach_action` and `reason_code`:
   - If the candidate's `InvoicePastDue` is `"Yes"` → `collections_followup`,
     `overdue_receivable`
   - Else if `tenure` ≤ 18 → `renewal_save`, `low_tenure_high_churn`
   - Else → `nurture_monitor`, `clean_billings`
6. Cohort checks: `past_due_shortlist_count` (number of top 5 with
   InvoicePastDue=Yes), `low_tenure_shortlist_count` (number of top 5 with
   tenure ≤ 18), `average_probability_top5` (mean of top 5 probabilities,
   rounded to 3 decimals).
7. Probabilities rounded to 3 decimals.

### 5e. High-Touch Retention Action Board

1. For each account in the task list, call the account profile, metrics (for the
   analysis period), tickets (full period), NPS (full period), billing snapshots
   (as-of date), and AR aging (as-of date).
2. Call `/api/opportunities` and filter for the account's open expansion
   opportunities whose `close_date` falls in the analysis period. Sum their
   `amount` as `expansion_pipeline`.
3. Compute risk factors and risk score per the risk queue recipe (5a). Compute
   `current_arr` from billing snapshots. Compute `overdue_balance` from AR aging.
4. Assign `primary_action` and `next_touch_due_date`:
   - `collections_followup` → next touch = collections_followup date from prompt
   - `technical_recovery` → next touch = technical_recovery date from prompt
   - `renewal_save` → next touch = renewal_save date from prompt
   - `executive_qbr` → next touch = executive_qbr date from prompt
   - `nurture_monitor` → next touch = nurture_monitor date from prompt
   - `no_action` → `next_touch_due_date` is `null`
5. Sort the action board by risk score descending, then `current_arr` descending.
   Include ALL accounts in the list (not just top-N). Number ranks sequentially.
6. Segment summary:
   - `strategic_accounts`: count of accounts with `segment` = `"Strategic"`
   - `enterprise_accounts`: count with `segment` = `"Enterprise"`
   - `arr_at_risk`: sum of `current_arr` for all accounts where
     `risk_level` is `critical` or `high`
   - `open_expansion_pipeline`: sum of `expansion_pipeline` across all accounts
   - `net_revenue_exposure`: `arr_at_risk` - `open_expansion_pipeline`
7. Follow-up calendar: use the exact dates from the task prompt.

## 6. Precision and Formatting Rules

- Currency values (revenue, ARR, balances, amounts): always 2 decimal places.
- Percentages (SLA, win rate, accuracy): always 1 decimal place.
- Counts (tickets, accounts, headcount): integers.
- Risk scores: integers 0-100.
- Churn probabilities: 3 decimal places.
- Dates: `YYYY-MM-DD` strings.
- Months: `YYYY-MM` strings.

## 7. Output Discipline

- Return **only** valid JSON. No markdown fences, no explanatory text, no trailing
  commas.
- Match the exact JSON shape from the task's `answer_template.json`. Do not add,
  remove, or rename keys.
- Order arrays exactly as specified (e.g. risk ranking by rank ascending, overdue
  followups by customer_name ascending, action board by rank ascending).
- Use `null` (not `"null"`, not `0`, not empty string) for missing values where
  the template shows `null`.
- Every controlled enum field must contain exactly one of the allowed values
  listed in Section 3, never a composite or free-text value.

## 8. API Call Pattern

When a task lists multiple accounts, make one API call per account endpoint
family, not one mega-call. For endpoints that return all records
(`/api/accounts`, `/api/billing/snapshots`, `/api/finance/ar-aging`,
`/api/opportunities`), fetch once and filter client-side. For per-account
endpoints (`/metrics`, `/tickets`, `/nps`), call once per account.

Use `start` and `end` query parameters exactly as shown in the task prompt.
Date formats: `YYYY-MM-DD` for tickets and NPS endpoints; `YYYY-MM` for metrics.
