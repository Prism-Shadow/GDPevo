# Controlled Vocabulary

Every report uses controlled string values. Use exactly these values. Capitalization, underscores, and spelling matter.

---

## Risk levels

Used for `risk_level` in risk rankings and action boards.

| Value | Meaning |
|-------|---------|
| `critical` | Immediate action required; top-priority risk |
| `high` | Significant risk needing prompt intervention |
| `medium` | Moderate risk; scheduled follow-up |
| `low` | Monitor only; no urgent action needed |

Risk levels are assigned by risk score bands:
- `critical`: 80-100
- `high`: 50-79
- `medium`: 20-49
- `low`: 0-19

---

## Primary actions

Used for `primary_action` in risk rankings, follow-up items, and action boards. Each action maps to a specific intervention.

| Value | When to use |
|-------|------------|
| `executive_qbr` | Strategic account with complex multi-signal risk; needs executive-level business review |
| `collections_followup` | Account has overdue receivables (61-90 or 90+ days) |
| `technical_recovery` | SLA degradation or usage decline is the dominant risk signal |
| `renewal_save` | Account is near renewal with elevated churn risk (low tenure, NPS drop, or usage decline) |
| `nurture_monitor` | Low-risk account; maintain relationship cadence |
| `no_action` | No intervention needed; account is healthy |

**Action priority for risk ranking:**
1. If overdue balance > 0 and it is the dominant signal → `collections_followup`
2. If SLA degradation or usage decline is the dominant signal (with or without other issues) → `technical_recovery`
3. If near renewal with elevated risk (low tenure, NPS drop) → `renewal_save`
4. If strategic account with multiple risk signals → `executive_qbr`
5. If low risk → `nurture_monitor`
6. If no meaningful risk → `no_action`

---

## Reason codes

Used for `reason_codes` arrays. These describe why an account is at risk or stable.

| Code | Trigger condition |
|------|------------------|
| `overdue_receivable` | Overdue balance (61_90 + 90_plus) > 0 |
| `low_tenure_high_churn` | Contract tenure ≤ 24 months (accounts with short history are higher churn risk) |
| `sla_degradation` | Average SLA compliance < 90% across the period, or any individual ticket with a missed SLA (first_response or resolution) |
| `nps_drop` | Latest valid NPS score is lower than the prior valid score within the period, or lower than the previous quarter's NPS |
| `usage_decline` | Product usage dropped more than 2 percentage points from the first month to the last month of the analysis period |
| `renewal_window` | Renewal date falls within 90 days after the assessment date |
| `expansion_offset` | Account has at least one open expansion opportunity whose close date falls within the analysis period |
| `clean_billings` | No overdue balance, no SLA issues, no NPS drop, and no usage decline. Always appears last in the array. |

**Ordering rule for arrays:**
Order reason codes from most impactful to least impactful. `clean_billings` always appears last if present. An account can have both risk codes and `clean_billings` when some dimensions are healthy but others are not.

When `expansion_offset` appears alongside risk codes, it is placed after the risk codes but before `clean_billings` (it is a mitigating factor, not a risk signal).

---

## Metric sources

Used in QBR `metric_sources`. Each maps a metric to where the data came from.

| Value | Maps to |
|-------|---------|
| `crm_closed_won` | Revenue data from CRM closed-won opportunities |
| `support_export` | Support ticket counts |
| `sla_report` | SLA compliance percentages |
| `nps_survey` | NPS scores |
| `billing_snapshot` | Billing/ARR data |
| `ar_aging` | Accounts receivable aging |
| `pipeline_crm` | CRM pipeline data |
| `event_dashboard` | Event performance metrics |
| `hr_report` | HR headcount and claims data |

For QBR reports:
- Revenue → `crm_closed_won`
- Support tickets → `support_export`
- SLA compliance → `sla_report`
- NPS → `nps_survey`

---

## Ticket trends

Used in QBR `ticket_trend`.

| Value | Condition |
|-------|-----------|
| `improving` | Ticket count decreased from first month to last month of the period |
| `worsening` | Ticket count increased from first month to last month |
| `flat` | Ticket count stayed the same |

---

## Review owners

Used in QBR `review_owner`.

| Value | When to use |
|-------|------------|
| `customer_success` | Standard QBR for an active account (default) |
| `solutions_engineering` | When technical recovery or SLA issues dominate |
| `finance_ops` | When billing/receivables issues dominate |

---

## Agenda topics

Used in QBR `agenda_topics` (ordered array of exactly 4).

Available values:
- `partnership_overview` — Relationship summary and strategic context
- `q2_metrics` — Quarterly metric review
- `performance_highlights` — Notable achievements or improvements
- `q3_initiatives` — Forward-looking plans for next quarter
- `technical_recovery` — Addressing SLA or usage issues
- `commercial_expansion` — Expansion and growth opportunities

---

## Link status

Used in receivables `link_status`.

| Value | Condition |
|-------|-----------|
| `linked` | A/R customer name matches an account's `legal_name` or an entry in `account_aliases` |
| `unlinked` | No match found in the accounts list |

---

## Tenure risk direction

Used in `tenure_risk_direction`.

| Value | Meaning |
|-------|---------|
| `negative` | Lower tenure correlates with higher churn risk (standard pattern) |
| `positive` | Higher tenure correlates with higher churn risk (unusual) |
| `not_assessed` | Tenure relationship not evaluated |

In the standard churn model, tenure has a negative coefficient: lower-tenure accounts have higher predicted churn probability.

---

## Accuracy bands

Used in churn model validation `accuracy_band`.

| Value | Accuracy range |
|-------|---------------|
| `below_70` | < 70% |
| `70_to_79` | 70.0% to 79.9% |
| `80_to_89` | 80.0% to 89.9% |
| `90_plus` | ≥ 90.0% |

---

## Policy codes

Policy codes appear in `policy_codes` blocks. Each code encodes a specific data-handling or methodology choice. The mapping is:

### Risk model codes (RS)
- `RS-2`: Weighted-factor model with equal weights across signals
- `RS-6`: Signal-count model where risk score is based on the number and severity of risk signals present
- `RS-9`: Composite model with tenure-weighted adjustments

Use `RS-6` as the default. This model assigns risk scores based on counting risk signals and weighting by severity: each active risk signal contributes to the score, with more severe signals (overdue, NPS drop) contributing more than milder ones (sla_degradation, renewal_window). The risk score is computed as the sum of per-signal contributions capped at 100.

### ARR source codes (REV)
- `REV-1`: CRM ARR from `/api/accounts`
- `REV-4`: Billing snapshot ARR from `/api/billing/snapshots`
- `REV-8`: Recognized revenue sum from metrics endpoint

Use `REV-4` (billing snapshot) as the default for point-in-time ARR in reports.

### Support hygiene codes (SUP)
- `SUP-3`: Raw ticket count from metrics
- `SUP-8`: Clean ticket count (excluding spam, duplicates, cancelled) from `/tickets` endpoint
- `SUP-9`: SLA-miss-only count

Use `SUP-8` (clean ticket count) as the default.

### Action priority codes (ACT)
- `ACT-1`: Collections-first priority
- `ACT-5`: Balanced priority (overdue, then technical, then renewal)
- `ACT-7`: Technical-first priority

Use `ACT-5` (balanced priority) as the default.

### Board sort codes (BORD)
- `BORD-1`: Sort by risk level then ARR descending
- `BORD-4`: Sort by risk score descending
- `BORD-8`: Sort by ARR descending then risk level

Use `BORD-4` (risk score descending) as the default.

### Exposure formula codes (EXP)
- `EXP-2`: `arr_at_risk` = sum of ARR for critical+high accounts; `net_revenue_exposure` = `arr_at_risk` - `open_expansion_pipeline`
- `EXP-6`: `arr_at_risk` = sum of all accounts' ARR; `net_revenue_exposure` = `arr_at_risk` - `open_expansion_pipeline`
- `EXP-9`: `arr_at_risk` = sum of ARR for accounts with overdue balance; `net_revenue_exposure` = sum of overdue balances

Use `EXP-6` as the default: `arr_at_risk` is the total ARR of all accounts on the board, and `net_revenue_exposure` = `arr_at_risk` - `open_expansion_pipeline`.

### Calendar policy codes (CAL)
- `CAL-3`: All due dates are the 15th of the following month after assessment
- `CAL-5`: Due dates are tied to action type (collections=+15d, technical=+18d, renewal=+22d, executive=+29d, nurture=+36d from assessment date)
- `CAL-7`: All due dates are +7 days from assessment

Use `CAL-5` (action-type staggered) as the default.

### Receivable trigger codes (RCP)
- `RCP-4`: Include only 90+ day aging
- `RCP-7`: Include 61-90 and 90+ day aging
- `RCP-9`: Include all aging buckets with overdue (31+ days)

Use `RCP-7` as the default: overdue = 61_90 + 90_plus.

### CRM match codes (CM)
- `CM-2`: Match by exact legal_name only
- `CM-5`: Match by legal_name or account_aliases (fuzzy: strip suffixes like "LLC", "Inc.", "Ltd.")
- `CM-8`: Match by account_aliases only

Use `CM-5` as the default: match customer_name against legal_name and all entries in account_aliases. For suffix variants (e.g. "Globex North Subsidiary LLC" vs alias "Globex North Subsidiary"), strip common suffixes before comparing.

### Pipeline window codes (PW)
- `PW-3`: Pipeline filtered to close dates within the target quarter
- `PW-6`: All open pipeline regardless of close date
- `PW-9`: Pipeline filtered to close dates within +90 days from as-of date

Use `PW-6` (all open pipeline) as the default for pipeline summaries. For expansion pipeline per account, filter to close dates within the target quarter (`PW-3`).

### Followup scope codes (FS)
- `FS-1`: Include only linked customers
- `FS-4`: Include all customers with overdue balances (linked and unlinked)
- `FS-8`: Include only customers with overdue > $10,000

Use `FS-4` (all overdue) as the default.

### Churn model protocol codes (MOD)
- `MOD-2`: Train on full dataset, no validation split
- `MOD-7`: Train on train.csv, validate on validation.csv
- `MOD-9`: Train on combined train+validation, validate on candidates

Use `MOD-7` as the default: train on train.csv, measure accuracy on validation.csv.

### Probability scale codes (PRB)
- `PRB-1`: Raw logistic regression probabilities (0-1 scale)
- `PRB-4`: Normalized probabilities scaled to 0-1 range from model output
- `PRB-8`: Log-odds transformed probabilities

Use `PRB-4` as the default.

### Deployment rule codes (DEP)
- `DEP-3`: Predict on all candidates
- `DEP-5`: Predict on specified candidate list only
- `DEP-9`: Predict on candidates with tenure > 6 months

Use `DEP-5` (specified list only) as the default.

### Outreach mapping codes (OUT)
- `OUT-2`: Map predicted probability bands to outreach actions directly
- `OUT-6`: Map probability bands with reason code co-factors
- `OUT-8`: Map using only PastDue flag

Use `OUT-2` as the default: highest probability → `renewal_save`, mid-range → `technical_recovery`, low → `nurture_monitor`, with `collections_followup` overriding when `InvoicePastDue` is "Yes".
