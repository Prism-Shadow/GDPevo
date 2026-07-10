# ApexCloud Retention Operations — Reusable SOP

## How to use this skill

This skill covers the ApexCloud Retention Operations API (`GDPEVO_ENV_BASE_URL`). It documents endpoints, data-cleaning rules, business-logic conventions, output vocabularies, and precision requirements that apply across all retention workflows (risk queues, QBR packets, receivables reviews, churn validation, and high-touch boards). Read it once, then follow the rules for every task variant.

---

## 1. Base URL

Use the URL from `environment_access.md`:

```
GDPEVO_ENV_BASE_URL=http://34.46.77.124:8004
```

All API paths are relative to this base. Never use localhost or 127.0.0.1.

---

## 2. API Endpoint Catalog

### 2.1 Accounts

| Endpoint | Method | Key response fields |
|---|---|---|
| `/api/accounts` | GET | `accounts[]`, `count` |
| `/api/accounts/<account_id>` | GET | `account_id`, `billing_arr_current`, `crm_arr`, `contract_tenure_months`, `renewal_date`, `lifecycle_status`, `segment`, `region`, `product_plan`, `legal_name`, `display_name`, `csm_owner`, `account_aliases` |

- `billing_arr_current` is the billing system's ARR. **Prefer this over `crm_arr` for revenue exposure and risk calculations.** The two values can differ; the billing figure is the authoritative ARR.
- `account_id` uses the `acct_` prefix. Match on `account_id`, never on alias or display name.
- `lifecycle_status` values seen: `active`, `renewal_risk`, `paused`, `implementation`.
- `segment` values seen: `Strategic`, `Enterprise`, `Mid-Market`, `SMB`.

### 2.2 Account Metrics

```
GET /api/accounts/<account_id>/metrics?start=YYYY-MM&end=YYYY-MM
```

Returns `metrics[]` per month. Each entry has:

- `month` (YYYY-MM)
- `recognized_revenue` (float, monthly revenue)
- `nps_score` (int or null — **may include retracted/tainted scores; cross-check with NPS endpoint**)
- `support_ticket_count` (int — raw count, includes spam/duplicates/cancelled)
- `sla_compliance` (float, percentage)
- `product_usage` (float, percentage)
- `survey_status` (`"completed"`, `"missing"`, `"retracted"`)
- `active_seats`, `quarter`

**Important**: The `nps_score` in metrics can show a value even when `survey_status` is `"retracted"`. Always use the dedicated NPS endpoint for the authoritative latest NPS.

### 2.3 Support Tickets

```
GET /api/accounts/<account_id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD
```

Returns `tickets[]`. Each ticket has:

- `ticket_id`, `created_date`, `status` (`"closed"`, `"open"`, `"cancelled"`)
- `is_spam` (bool), `is_duplicate` (bool)
- `first_response_sla_met` (bool), `resolution_sla_met` (bool)
- `severity` (`"P1"`–`"P4"`), `product_area`

**Clean ticket count rule**: Exclude tickets where **any** of these is true:
- `is_spam == true`
- `is_duplicate == true`
- `status == "cancelled"`

Count the remaining tickets. This is the "clean ticket count" used in risk scoring.

### 2.4 NPS Responses

```
GET /api/accounts/<account_id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD
```

Returns `nps_responses[]`. Each has:

- `response_id`, `response_date`, `score` (int), `retracted` (bool), `survey_channel`

**Latest NPS rule**:
1. Filter out all responses where `retracted == true`.
2. Take the response with the most recent `response_date`.
3. Its `score` is `latest_nps`.
4. If no non-retracted responses exist, `latest_nps` may be null or use the most recent non-retracted metrics score — but document the gap.

### 2.5 A/R Aging

```
GET /api/finance/ar-aging?as_of=YYYY-MM-DD
```

Returns `ar_aging[]`. Each entry:

- `customer_name` — **matches `legal_name` from the account endpoint**, not `display_name` or aliases
- `aging_id`, `as_of`, `quarter`, `region`
- Buckets: `current`, `1_30`, `31_60`, `61_90`, `90_plus` (all floats)

**Overdue balance (`overdue_balance`) rule**: Sum `31_60 + 61_90 + 90_plus`. Do **not** include `1_30` (that is current-cycle, not yet overdue). Do **not** include `current`.

**Matching rule**: Join AR records to accounts by exact match of `customer_name` ↔ `legal_name`. Watch for noise records with similar-but-different names (see §4 Pitfalls).

### 2.6 Opportunities / Pipeline

```
GET /api/opportunities?quarter=YYYY-QX
```

Returns `opportunities[]`. Each:

- `opportunity_id`, `account_id`, `account_legal_name`
- `amount` (float), `close_date` (YYYY-MM-DD), `created_date`
- `stage` (`"Closed Won"`, `"Closed Lost"`, `"Discovery"`, `"Proposal"`, `"Negotiation"`, `"Prospecting"`)
- `state` (`"open"`, `"closed"`)
- `product_line`, `region`

**Pipeline summary**:
- **Won**: `stage == "Closed Won"` (state is always `"closed"`)
- **Lost**: `stage == "Closed Lost"`
- **Open**: `state == "open"` (regardless of stage label)
- **Win rate** (`win_rate_pct`): `won_count / (won_count + lost_count)` → percentage to 1 decimal
- **Open pipeline**: sum of `amount` for all open opportunities
- **Top open product line**: most frequent `product_line` among open opportunities

**Period filtering for expansion pipeline**: Include open opportunities whose `close_date` falls within the analysis date range (inclusive). This is the "in-window" expansion pipeline.

### 2.7 HR Summary

```
GET /api/hr/summary?quarter=YYYY-QX
```

Returns `hr_summary[]` by region. Each: `region`, `headcount` (int), `unpaid_claims_amount` (float), `attendance_rate`, `high_absence_employees`, `leave_liability_hours`, `open_advances_amount`, `open_advances_count`, `unpaid_claims_count`.

**Aggregation**: When task says "all regions", sum `headcount` and `unpaid_claims_amount` across all region records.

### 2.8 Event Performance

```
GET /api/events/performance?event=<event_id>&quarter=YYYY-QX
```

Returns `event_performance[]`. Each: `event_id`, `quarter`, `event_orders` (int), `event_revenue` (float), `completed_orders`, `cancelled_orders`, `pending_orders`, `refunded_orders`, `product_revenue`.

### 2.9 Churn Exports (CSV)

```
GET /exports/churn/train.csv       — training data, includes Churn column
GET /exports/churn/validation.csv  — validation data, includes Churn column
GET /exports/churn/candidates.csv  — prediction candidates, NO Churn column
```

These are raw CSV files (not JSON). Parse with a CSV reader. Columns: `customer_id`, `tenure`, `MonthlyCharges`, `TotalCharges`, `Contract`, `PaymentMethod`, `PaperlessBilling`, `Partner`, `Dependents`, `OnlineSecurity`, `OnlineBackup`, `DeviceProtection`, `TechSupport`, `StreamingTV`, `StreamingMovies`, `SupportTickets90d`, `NPSLast`, `UsageTrendPct`, `InvoicePastDue`, `ActiveSeatRatio` (+ `Churn` in train/validation only).

**Feature count**: 19 predictor columns (exclude `customer_id` and `Churn`).

**Model validation workflow**:
1. Load train.csv → count `training_rows` (exclude header)
2. Load validation.csv → count `validation_rows` (exclude header)
3. Train a logistic regression (or equivalent binary classifier) on train features → target `Churn`
4. Predict on validation set → compare to actual `Churn` → compute `accuracy_pct`
5. Extract `tenure_coefficient_direction`: typically `"negative"` (longer tenure → lower churn probability)
6. Categorize into `accuracy_band`: `below_70`, `70_to_79`, `80_to_89`, `90_plus`

**Candidate ranking**:
1. Apply the trained model to candidates.csv → get `predicted_churn_probability` per candidate
2. Filter to the specified account list
3. Sort by probability descending → top 5
4. `average_probability_top5`: mean of the top 5 probabilities
5. `past_due_shortlist_count`: count of top-5 candidates where `InvoicePastDue == "Yes"`
6. `low_tenure_shortlist_count`: count of top-5 candidates with `tenure < 24`

---

## 3. Data-Cleaning Rules (apply in every task)

### 3.1 Ticket hygiene
```
clean_tickets = [t for t in tickets if not t.is_spam and not t.is_duplicate and t.status != "cancelled"]
clean_ticket_count = len(clean_tickets)
```

### 3.2 NPS hygiene
```
valid_nps = [r for r in nps_responses if not r.retracted]
latest = max(valid_nps, key=lambda r: r.response_date) if valid_nps else None
latest_nps = latest.score if latest else null
```

**Do not** use `nps_score` from the metrics endpoint as the authoritative latest NPS — it may include retracted or missing-survey values.

### 3.3 Overdue balance
```
overdue = ar.31_60 + ar.61_90 + ar.90_plus  # NOT 1_30, NOT current
```
Sum these three aging buckets. `1_30` is within payment terms and is not "overdue."

### 3.4 AR-to-account matching
Match `ar_aging[].customer_name` exactly to `account[].legal_name`. Names like "Globex North Subsidiary LLC" or "North Star Finance Services" are **noise records** — they have similar names but are distinct entities. Match on exact `legal_name` only.

---

## 4. Common Pitfalls

1. **Retracted NPS in metrics**: The metrics endpoint `nps_score` field can show a value even when `survey_status == "retracted"`. Example: HarborByte June 2026 shows `nps_score: 64, survey_status: "retracted"` in metrics, but the NPS endpoint has no June response — latest NPS is 52 (May).

2. **Duplicate NPS dates**: If two NPS responses have the same date and one is retracted, the non-retracted one wins. If both are non-retracted, use the higher `response_id` (later submission).

3. **AR noise records**: AR aging contains entries with names similar to real accounts but different legal entities. E.g., "Globex North Subsidiary LLC" vs "Globex North Holdings LLC", "Quartz Insurance Claims Ltd." vs "Quartz Insurance PLC". **Only match on exact `legal_name`.**

4. **Spam/duplicate tickets**: The `support_ticket_count` in the metrics endpoint is a raw count. Always compute clean ticket count from the tickets endpoint by filtering spam, duplicates, and cancelled.

5. **Cancelled vs closed tickets**: `status == "cancelled"` tickets are noise. `status == "closed"` tickets are valid regardless of SLA outcomes.

6. **ARR divergence**: `billing_arr_current` and `crm_arr` can differ. Use `billing_arr_current` as the primary ARR for risk/revenue calculations. Document which source was used.

7. **Renewal date already passed**: An account whose `renewal_date` is before the assessment date is NOT automatically safe. If `lifecycle_status` is still `"active"` or `"renewal_risk"`, it may be on a grace period or in contested renewal.

8. **Month-only vs date-range parameters**: Metrics use `start=YYYY-MM&end=YYYY-MM`. Tickets and NPS use `start=YYYY-MM-DD&end=YYYY-MM-DD`. AR aging uses `as_of=YYYY-MM-DD`. Using the wrong format returns errors or incomplete data.

9. **Open tickets in SLA assessment**: Tickets with `status == "open"` still count toward clean ticket count. They are real support burden.

10. **Opportunity close_date outside analysis period**: When computing "in-period" expansion pipeline, filter opportunities by `close_date` within the analysis window, NOT by `created_date` or `quarter`.

---

## 5. Business-Logic Conventions

### 5.1 Risk scoring (multi-factor)

Risk is assessed on these dimensions, roughly in order of weight:

| Factor | Higher risk signal |
|---|---|
| `lifecycle_status` | `"renewal_risk"` > `"paused"` > `"implementation"` > `"active"` |
| Renewal proximity | Renewal date within 60 days of assessment date (or already past) |
| ARR magnitude | Larger ARR = more revenue at stake → amplifies other risk signals |
| NPS trend | Latest NPS < 30 (detractor), or declining 20+ points in the period |
| SLA trend | Declining > 5 percentage points across the period |
| Usage trend | Declining > 10 percentage points across the period |
| Overdue receivables | Any amount in 61_90 or 90_plus buckets, or 31_60 > $1000 |
| Clean ticket volume | > 10 clean tickets in the quarter |
| Tenure | < 24 months = elevated churn risk |

**Risk level assignment** (heuristic):
- `critical`: Multiple severe signals (e.g., renewal_risk lifecycle + large overdue + SLA crash), OR extremely high ARR with several moderate signals
- `high`: Several moderate-to-severe signals, or one severe signal with substantial ARR
- `medium`: One or two moderate signals
- `low`: No significant negative signals

### 5.2 Primary action assignment

| Primary action | When to use |
|---|---|
| `collections_followup` | Significant overdue balance in older buckets (61_90 or 90_plus > 0) |
| `technical_recovery` | SLA compliance declining > 5pp, or multiple SLA breaches, or resolution_sla failures |
| `renewal_save` | Renewal date within 60 days + risk signals (NPS decline, usage drop, etc.) |
| `executive_qbr` | Strategic/Enterprise segment + high ARR + complex risk picture needing exec attention |
| `nurture_monitor` | Low/modest risk signals, no urgent action needed |
| `no_action` | Healthy account, no negative signals |

### 5.3 Reason codes

Apply reason codes that are factually supported by the data:

| Code | Trigger |
|---|---|
| `overdue_receivable` | AR aging shows overdue balance in 31_60, 61_90, or 90_plus |
| `low_tenure_high_churn` | `contract_tenure_months` < 24 |
| `sla_degradation` | SLA compliance declined > 3pp across the period |
| `nps_drop` | Latest NPS < 30, or NPS declined > 20 points |
| `usage_decline` | Product usage declined > 5pp across the period |
| `renewal_window` | Renewal date within 90 days of assessment date |
| `expansion_offset` | Open expansion pipeline exists that could offset risk |
| `clean_billings` | No overdue balance and billing is current |

### 5.4 QBR metric conventions

- **Revenue**: `recognized_revenue` from the metrics endpoint → source is `"billing_snapshot"`
- **Support tickets**: Clean count from the tickets endpoint → source is `"support_export"`
- **SLA compliance**: `sla_compliance` from metrics → source is `"sla_report"`
- **NPS**: Latest non-retracted score from NPS endpoint → source is `"nps_survey"`
- **Ticket trend**: Compare month-over-month clean ticket counts. If April < May < June → `"worsening"`. If April > May > June → `"improving"`. Otherwise → `"flat"`.

### 5.5 Portfolio / segment summaries

- `strategic_accounts`: count of accounts with `segment == "Strategic"`
- `enterprise_accounts`: count of accounts with `segment == "Enterprise"`
- `arr_at_risk`: sum of `billing_arr_current` for accounts with `risk_level` in (`"critical"`, `"high"`)
- `open_expansion_pipeline`: sum of in-period open opportunity amounts
- `net_revenue_exposure`: `arr_at_risk - open_expansion_pipeline`
- `collections_count`: count of accounts with `primary_action == "collections_followup"`
- `technical_recovery_count`: count of accounts with `primary_action == "technical_recovery"`
- `critical_or_high_count`: count of accounts with `risk_level` in (`"critical"`, `"high"`)

### 5.6 Receivables workflow (Q3-specific)

- Filter AR aging to customers with `61_90 > 0 OR 90_plus > 0` (older-bucket overdue)
- For each overdue customer, attempt to find a matching CRM account by `customer_name == legal_name`
- `link_status`: `"linked"` if an account match is found, `"unlinked"` otherwise
- `account_id`: the matched account's ID (or `null` if unlinked)
- `primary_action` for overdue: always `"collections_followup"`
- Sort `overdue_followups` by `customer_name` ascending (alphabetical)
- `linked_followup_count`: count of followups where `link_status == "linked"`
- `unlinked_followup_count`: count where `link_status == "unlinked"`

### 5.7 Churn model checks

- `tenure_risk_direction` / `tenure_coefficient_direction`: `"negative"` when longer tenure correlates with lower churn risk (the expected direction). `"positive"` if the reverse. `"not_assessed"` or `"zero"` if not evaluated.
- `uses_billing_arr_source`: `true` when ARR values are sourced from `billing_arr_current`, `false` when sourced from `crm_arr`.
- `outreach_action` mapping (churn context):
  - High probability + past due → `"collections_followup"`
  - High probability + low tenure → `"renewal_save"`
  - High probability + SLA/usage issues → `"technical_recovery"`
  - Lower probability → `"nurture_monitor"`

---

## 6. Output Precision and Formatting

| Data type | Precision | Example |
|---|---|---|
| Currency (revenue, ARR, overdue, pipeline) | 2 decimal places | `1425000.00` |
| Percentages (SLA, win rate, accuracy, usage) | 1 decimal place | `85.9` |
| Counts (tickets, accounts, headcount) | Integer | `13` |
| Risk scores | Integer | `87` |
| Churn probabilities | 3 decimal places | `0.734` |

All top-level JSON keys must use the exact names from the answer template. Do not add or omit keys.

---

## 7. Controlled Vocabularies

These are the **only** valid values for each enum field. Never invent new ones.

### risk_level
`critical`, `high`, `medium`, `low`

### primary_action
`executive_qbr`, `collections_followup`, `technical_recovery`, `renewal_save`, `nurture_monitor`, `no_action`

### reason_codes (array)
`overdue_receivable`, `low_tenure_high_churn`, `sla_degradation`, `nps_drop`, `usage_decline`, `renewal_window`, `expansion_offset`, `clean_billings`

### metric_sources
`billing_snapshot`, `support_export`, `sla_report`, `nps_survey`, `crm_closed_won`, `ar_aging`, `pipeline_crm`, `event_dashboard`, `hr_report`

### review_owner
`solutions_engineering`, `customer_success`, `finance_ops`

### agenda_topics (ordered)
`partnership_overview`, `q2_metrics`, `performance_highlights`, `q3_initiatives`, `technical_recovery`, `commercial_expansion`

### ticket_trend
`improving`, `worsening`, `flat`

### link_status
`linked`, `unlinked`

### accuracy_band
`below_70`, `70_to_79`, `80_to_89`, `90_plus`

### tenure direction
`negative`, `positive`, `zero`, `not_assessed`

### outreach_action (churn model context)
`renewal_save`, `technical_recovery`, `collections_followup`, `nurture_monitor`

---

## 8. Policy Codes

Some output schemas include `policy_codes` blocks. These are **deterministic labels** that identify the specific policy rules applied. Every task variant that includes policy codes has its own set of code families. Map code prefixes to their policy domain:

| Code prefix | Domain |
|---|---|
| `RS-` | Risk scoring model |
| `REV-` | ARR/revenue source |
| `SUP-` | Support hygiene rules |
| `ACT-` | Action priority |
| `BORD-` | Board sort order |
| `EXP-` | Exposure formula |
| `CAL-` | Calendar / follow-up date policy |
| `RCP-` | Receivable trigger |
| `CM-` | CRM match rules |
| `PW-` | Pipeline window |
| `FS-` | Followup scope |
| `MOD-` | Model protocol |
| `PRB-` | Probability scale |
| `DEP-` | Deployment rule |
| `OUT-` | Outreach mapping |

The specific code within each family (e.g., `RS-2`, `RS-6`, `RS-9`) encodes which policy variant was applied. Derive these from the actual logic used — they are traceable identifiers, not random.

---

## 9. Task-Type Quick Reference

### Renewal Risk Queue (like train_001)
1. Fetch accounts, metrics, tickets, NPS, AR aging for each account_id
2. Compute clean ticket count, latest NPS, overdue balance
3. Score and rank: lifecycle_status, renewal proximity, ARR, NPS, SLA trend, usage trend, overdue, tenure
4. Assign risk_level, primary_action, reason_codes
5. Output top 5 by risk_score descending
6. Populate portfolio_summary and model_checks

### QBR Metrics Packet (like train_002)
1. Fetch account, metrics, tickets, NPS for the single account
2. Build monthly qbr_metrics: revenue, support_tickets (clean), sla_compliance_pct, nps_score
3. Compute highlights: averages, peaks
4. Determine ticket_trend, metric_sources
5. Assign review_plan and agenda_topics

### Receivables & Pipeline Review (like train_003)
1. Fetch AR aging → filter to customers with 61_90 > 0 OR 90_plus > 0
2. Fetch all accounts → match by legal_name for link_status
3. Fetch opportunities for the quarter → compute pipeline summary
4. Fetch HR summary (all regions) and event performance
5. Build overdue_followups sorted by customer_name ascending
6. Populate ops_context and policy_codes

### Churn Model Validation (like train_004)
1. Fetch and parse train.csv, validation.csv, candidates.csv
2. Train binary classifier, evaluate on validation set
3. Report training_rows, validation_rows, feature_count, accuracy_pct, accuracy_band, tenure_coefficient_direction
4. Predict on candidates, filter to specified accounts, rank top 5 by probability descending
5. Assign outreach_action and reason_code per candidate
6. Compute cohort_checks

### High-Touch Retention Board (like train_005)
1. Fetch accounts, metrics, tickets, NPS, AR aging, opportunities for each account_id
2. Compute clean tickets, latest NPS, overdue, in-period expansion pipeline
3. Score and rank all accounts (not just top 5)
4. Assign risk_level, primary_action, reason_codes
5. Set next_touch_due_date by primary_action calendar
6. Populate segment_summary, followup_calendar, policy_codes

---

## 10. Execution Checklist

Before returning the JSON:
- [ ] All currency values rounded to 2 decimal places
- [ ] All percentages rounded to 1 decimal place
- [ ] All counts are integers
- [ ] Clean ticket counts exclude spam, duplicates, and cancelled
- [ ] Latest NPS comes from the NPS endpoint (non-retracted), not the metrics endpoint
- [ ] Overdue balance = 31_60 + 61_90 + 90_plus (NOT 1_30)
- [ ] AR records matched by exact legal_name (no fuzzy matching)
- [ ] All enum values are from the controlled vocabularies in §7
- [ ] Output keys match the answer template exactly
- [ ] Sort orders are applied (risk ranking: descending; followups: customer_name ascending)
- [ ] Noise/distractor records are not counted
