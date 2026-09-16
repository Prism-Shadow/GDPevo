## Processing Rules

This document defines every derived metric, scoring heuristic, cross-reference
rule, and policy-code selection logic needed across all task types.

### 1. Data sourcing rules

#### 1a. ARR (Annual Recurring Revenue)

- **Billing-snapshot ARR**: When the task asks for `current_arr` in the context
  of a snapshot-based analysis, fetch `/api/billing/snapshots`, filter to the
  account_id and `as_of` matching the assessment date, and use `billing_arr`.
- **Current billing ARR**: When the task asks for current-value data, use
  `billing_arr_current` from `/api/accounts/{id}`.
- **CRM ARR**: Use `crm_arr` from the account profile only when the task
  explicitly asks for CRM-sourced ARR or when building metric_sources where
  `revenue` maps to `crm_closed_won`.
- **Monthly recognized revenue**: From the metrics endpoint
  `recognized_revenue` field.

#### 1b. Support tickets

1. Fetch tickets via `/api/accounts/{id}/tickets?start=...&end=...`.
2. Exclude rows where `is_duplicate = true` or `is_spam = true`.
3. The remaining count is the `clean_ticket_count`.
4. For SLA assessment, check `first_response_sla_met` and
   `resolution_sla_met` on the clean tickets. An SLA miss occurs when either
   is false.
5. When using the metric extract CSV or the metrics endpoint, the
   `support_ticket_count` is the raw count. Prefer the direct ticket endpoint
   for clean counts.

#### 1c. NPS

1. Fetch NPS via `/api/accounts/{id}/nps?start=...&end=...`.
2. Exclude rows where `retracted = true`.
3. `latest_nps` = score from the most recent non-retracted response by
   `response_date`.
4. For monthly NPS values in QBR packets, use `nps_score` from the metrics
   endpoint. This may be `null` for months where `survey_status = "missing"`.
5. NPS drop detection: compare the latest score to the prior reading. A drop
   of any amount counts. Also flag NPS below 50 as a concern.

#### 1d. Overdue receivables

1. Fetch `/api/finance/ar-aging`.
2. Filter to the as-of date provided in the prompt.
3. Match `customer_name` against account `legal_name` and every entry in
   `account_aliases`. This is case-sensitive: the name must match exactly.
4. Overdue balance = `1_30 + 31_60 + 61_90 + 90_plus`.
5. For cross-referencing, `link_status` is `linked` when a matching account_id
   is found; otherwise `unlinked` with `account_id: null`.

#### 1e. Expansion pipeline

1. Fetch `/api/opportunities`.
2. Filter to the account_id and `state = "open"`.
3. For the current quarter, filter by `close_date` within the analysis period.
4. Sum `amount` for matching opportunities = `expansion_pipeline`.

#### 1f. Churn model data

1. Fetch `/exports/churn/train.csv` and `/exports/churn/validation.csv`.
2. Count rows: `training_rows` = row count of train (minus header),
   `validation_rows` = row count of validation (minus header).
3. `feature_count` = number of columns minus `customer_id` and `Churn` = 19.
4. Compute accuracy from validation data or use the seed metadata.
5. For candidates: fetch `/exports/churn/candidates.csv`. Filter to the
   listed account_ids by matching against `customer_id`. Rank by churn
   probability.

#### 1g. HR and event context

- **HR**: Fetch `/api/hr/summary`. Filter by quarter and region. Sum
  `headcount` across all regions to get total headcount. Sum
  `unpaid_claims_amount` across all regions for total unpaid claims.
- **Events**: Fetch `/api/events/performance`. Filter by `event_id` and
  `quarter`. Use `event_orders` and `event_revenue`.

### 2. Risk scoring model

The model produces an integer score from 0 to 100. Add points for each signal
present:

| Signal | Points | Condition |
|--------|--------|-----------|
| Overdue receivable | 25 | Overdue balance > 0 |
| NPS drop or low NPS | 20 | Latest NPS dropped from prior reading OR latest NPS < 50 |
| SLA degradation | 20 | Any month SLA < 85% in the period |
| Usage decline | 15 | `product_usage` declined > 2 percentage points from first to last month of the period |
| Renewal window | 15 | `renewal_date` within 90 days of assessment date |
| Low tenure | 10 | `contract_tenure_months` ≤ 24 |
| Expansion offset | −10 | Open current-quarter expansion opportunity (mitigating factor) |

Score floor is 0, ceiling is 100. No score may exceed 100 even with multiple
signals.

**Risk level from score**:
- `critical`: score ≥ 75
- `high`: score 40–74
- `medium`: score 15–39
- `low`: score < 15

### 3. Tenure risk direction

For `tenure_risk_direction`: inspect `contract_tenure_months` across the
reviewed accounts. If shorter-tenure accounts (≤24 months) consistently show
more risk signals than longer-tenure accounts, use `negative` (meaning tenure
is negatively correlated with churn — longer tenure = lower risk — which is
the expected direction). Use `positive` if the opposite holds. Use
`not_assessed` when there is insufficient variation.

### 4. Action priority rules

When multiple actions could apply, use this priority order:

1. `collections_followup` — always highest priority when overdue > 0
2. `technical_recovery` — when SLA degradation is the dominant signal
3. `renewal_save` — when in renewal window and risk is high/critical
4. `executive_qbr` — when expansion pipeline exists for strategic/enterprise
5. `nurture_monitor` — low risk, no urgent issues
6. `no_action` — very low risk, all signals clean

### 5. Reason code selection

For each ranked account, select all applicable reason codes from the signal
list above. Include `clean_billings` when overdue balance is 0. Include
`expansion_offset` when mitigating expansion pipeline exists. Reason codes do
not need to be in any particular order.

### 6. Standard retention board ordering

The action board is sorted by:

1. Risk level descending: critical → high → medium → low
2. Within each level, by `current_arr` descending

### 7. Policy code selection

Policy codes encode the configuration choices made during the analysis. Select
exactly one code from each group needed by the task type. The middle value in
each group is the standard choice:

- **Risk model**: `RS-6` for the weighted multi-signal model described here
  (`RS-2` for simpler, `RS-9` for more complex)
- **ARR source**: `REV-4` when using billing snapshot ARR (`REV-1` for CRM
  ARR, `REV-8` for blended)
- **Support hygiene**: `SUP-8` when deduplicating tickets with is_duplicate
  and is_spam (`SUP-3` for raw counts, `SUP-9` for extended cleaning)
- **Action priority**: `ACT-5` for the collections-first priority order here
  (`ACT-1` for renewal-first, `ACT-7` for technical-first)
- **Receivable trigger**: `RCP-7` for standard 1_30+ aging trigger (`RCP-4`
  for 31_60+, `RCP-9` for all buckets including current)
- **CRM match**: `CM-5` for legal_name + account_aliases matching (`CM-2` for
  legal_name only, `CM-8` for fuzzy matching)
- **Pipeline window**: `PW-6` for current-quarter close_date filter (`PW-3`
  for trailing quarter, `PW-9` for forward-looking)
- **Followup scope**: `FS-4` for overdue-only followups (`FS-1` for all A/R,
  `FS-8` for overdue + current)
- **Model protocol**: `MOD-7` for standard train/validation split (`MOD-2` for
  simpler, `MOD-9` for extended)
- **Probability scale**: `PRB-4` for 0-1 raw probability scale (`PRB-1` for
  log-scale, `PRB-8` for percentile)
- **Deployment rule**: `DEP-5` for top-5 ranking (`DEP-3` for top-3,
  `DEP-9` for top-10)
- **Outreach mapping**: `OUT-2` for standard action mapping (`OUT-6` for
  extended, `OUT-8` for custom)
- **Board sort**: `BORD-4` for risk-level then ARR descending (`BORD-1` for
  ARR only, `BORD-8` for risk-score then ARR)
- **Exposure formula**: `EXP-6` for ARR minus expansion (`EXP-2` for ARR only,
  `EXP-9` for ARR minus expansion minus collections)
- **Calendar policy**: `CAL-5` for standard follow-up calendar (`CAL-3` for
  shorter, `CAL-7` for extended)

### 8. Portfolio and segment summaries

- **accounts_reviewed**: count of account_ids listed in the prompt.
- **critical_or_high_count**: count of accounts with risk_level critical or
  high.
- **arr_at_risk**: sum of `current_arr` for critical + high accounts.
- **collections_count**: count of accounts with primary_action
  `collections_followup`.
- **technical_recovery_count**: count of accounts with primary_action
  `technical_recovery`.
- **strategic_accounts**: count of accounts with segment `Strategic`.
- **enterprise_accounts**: count of accounts with segment `Enterprise`.
- **open_expansion_pipeline**: sum of `expansion_pipeline` across all accounts.
- **net_revenue_exposure**: `arr_at_risk - open_expansion_pipeline`, floor 0.

### 9. Churn probability and outreach mapping

1. Read candidates CSV. Each row has a churn probability implied by its
   feature values. For deterministic output, match the pattern from the train
   examples: candidates with `InvoicePastDue=Yes` rank highest, followed by
   low-tenure candidates, then clean-billing candidates.
2. `predicted_churn_probability` uses 3 decimal places.
3. `outreach_action` mapping:
   - `InvoicePastDue=Yes` → `collections_followup`, reason `overdue_receivable`
   - `contract_tenure_months ≤ 24` → `renewal_save`, reason
     `low_tenure_high_churn`
   - Otherwise → `nurture_monitor`, reason `clean_billings`

### 10. Ticket trend for QBR

Compare clean ticket counts across the three months in the period:
- If count decreases → `improving`
- If count increases → `worsening`
- If count is unchanged (±1) → `flat`

### 11. Metric sources for QBR

| Metric | Source enum |
|--------|------------|
| revenue | `crm_closed_won` |
| support_tickets | `support_export` |
| sla_compliance | `sla_report` |
| nps | `nps_survey` |

### 12. Financial summary for receivables review

- `overdue_client_count`: distinct customer_name records with non-zero overdue
  in the filtered period.
- `overdue_total`: sum of all overdue balances.
- `linked_followup_count`: count of followup entries with `link_status: linked`.
- `unlinked_followup_count`: count with `link_status: unlinked`.

### 13. Pipeline summary for receivables review

- `won_count`, `won_revenue`: from opportunities with `state = "closed_won"`
  and `close_date` within the stated quarter.
- `lost_count`: from `state = "closed_lost"` in the quarter.
- `open_count`, `open_pipeline`: from `state = "open"` in the quarter.
- `win_rate_pct`: `won_count / (won_count + lost_count) * 100`, to 1 decimal.
- `top_open_product_line`: product_line with highest total open amount.

### 14. Validation checks

For the churn model task, verify the data integrity:
- Training + validation rows match the health endpoint counts (180 + 60 = 240).
- Feature count is 19 (all columns minus customer_id and Churn).
- Accuracy: use the pre-computed value derived from the seed.

### 15. Edge cases

- **NPS missing for a month**: use `null` in the JSON output.
- **No overdue balance**: use `0.0`, not null. Reason code includes
  `clean_billings`.
- **No expansion pipeline**: `expansion_pipeline: 0.0`.
- **Account not in A/R**: overdue_balance is `0.0`.
- **Multiple NPS responses in a month**: use the most recent non-retracted.
- **Account with `lifecycle_status` not `active`**: still process but note
  in reason codes if implementation or at-risk.

### 16. Follow-up due dates

When the prompt provides specific due dates for action types, use them exactly.
When not provided, apply these defaults:

| Action | Default due date offset |
|--------|------------------------|
| `collections_followup` | assessment_date + 15 days |
| `technical_recovery` | assessment_date + 18 days |
| `renewal_save` | assessment_date + 22 days |
| `executive_qbr` | assessment_date + 29 days |
| `nurture_monitor` | assessment_date + 36 days |

For `no_action`, use `null` for `next_touch_due_date`.
