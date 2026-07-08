# ApexCloud Retention Operations API Skill

## Overview

This skill covers how to build retention analytics, QBR metrics, churn validation, and receivables reviews from the **ApexCloud Retention Operations API**. The skill is designed for unseen tasks that ask you to reconcile account profiles, billing snapshots, support health, NPS, A/R aging, product usage, and expansion opportunities into structured JSON outputs.

**API base URL:** Use the current solver's `environment_access.md` / `GDPEVO_ENV_BASE_URL` as the operative API base URL. Do not hard-code `localhost` or `127.0.0.1`.

---

## 1. Public Endpoint Families

Discover and use these endpoint families. The service exposes a health check at `/api/health` and an account list at `/api/accounts`.

| Endpoint | Purpose | Key Query Params |
|---|---|---|
| `GET /api/accounts` | List all accounts with billing/CRM ARR, tenure, lifecycle, renewal date, segment, legal name, region, product plan. | none |
| `GET /api/accounts/{account_id}` | Single account profile (same fields as list). | none |
| `GET /api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM` | Monthly metrics: `recognized_revenue`, `support_ticket_count`, `sla_compliance`, `nps_score`, `product_usage`, `active_seats`, `survey_status`. | `start`, `end` (inclusive month strings) |
| `GET /api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` | Support tickets with `is_duplicate`, `is_spam`, `status`, `severity`, `first_response_sla_met`, `resolution_sla_met`, `created_date`. | `start`, `end` (inclusive dates) |
| `GET /api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` | NPS responses with `score`, `response_date`, `retracted`, `survey_channel`. | `start`, `end` (inclusive dates) |
| `GET /api/finance/ar-aging` | A/R aging buckets: `customer_name`, `current`, `1_30`, `31_60`, `61_90`, `90_plus`, `as_of`, `quarter`, `region`. | none |
| `GET /api/opportunities` | Pipeline: `account_id`, `stage`, `amount`, `close_date`, `product_line`. | none |
| `GET /api/hr/summary` | HR by quarter/region: `headcount`, `unpaid_claims_amount`, `attendance_rate`, etc. | none |
| `GET /api/events/performance` | Event performance by `event_id` and `quarter`: `event_orders`, `event_revenue`, `product_revenue`. | none |
| `GET /exports/churn/train.csv` | Churn model training data. | none |
| `GET /exports/churn/validation.csv` | Churn model validation data. | none |
| `GET /exports/churn/candidates.csv` | Churn candidate accounts to rank. | none |

**Important:** The prompt may mention a "billing snapshot" endpoint, but there is **no matching public endpoint** for it. The billing snapshot data is embedded in the account object as `billing_arr_current`.

---

## 2. Deterministic Precision Rules

Apply these rounding rules exactly. Judges are sensitive to precision mismatches.

| Data Type | Rule | Example |
|---|---|---|
| Currency | 2 decimal places | `95756.67` |
| Percentages | 1 decimal place | `95.2` (not `95.20`) |
| Counts | Integer | `4` |
| Churn probability | 3 decimal places | `0.748` |
| Risk scores | Integer | `85` |

---

## 3. Controlled Labels & Enums

Use **only** the enum strings listed below. Never invent values.

### Risk & Action
- `risk_level`: `critical`, `high`, `medium`, `low`
- `primary_action` / `outreach_action`: `collections_followup`, `technical_recovery`, `renewal_save`, `nurture_monitor`, `executive_qbr`, `no_action`
- `reason_code`: `overdue_receivable`, `low_tenure_high_churn`, `sla_degradation`, `nps_drop`, `usage_decline`, `renewal_window`, `expansion_offset`, `clean_billings`

### Metric Sources
- `source_enum`: `crm_closed_won`, `support_export`, `sla_report`, `nps_survey`, `billing_snapshot`, `ar_aging`, `pipeline_crm`, `event_dashboard`, `hr_report`

### Review & Agenda
- `review_owner`: `solutions_engineering`, `customer_success`, `finance_ops`
- `ticket_trend`: `improving`, `worsening`, `flat`
- `agenda_topic`: `partnership_overview`, `q2_metrics`, `performance_highlights`, `q3_initiatives`, `technical_recovery`, `commercial_expansion`

### Link Status
- `link_status`: `linked`, `unlinked`

### Model Validation
- `accuracy_band`: `below_70`, `70_to_79`, `80_to_89`, `90_plus`
- `tenure_coefficient_direction`: `negative`, `positive`, `zero`

---

## 4. Core Business Rules

### A/R Overdue Balance
- **Overdue balance** = sum of all non-current aging buckets:
  ```
  overdue = 1_30 + 31_60 + 61_90 + 90_plus
  ```
- Use the quarter-specific aging record whose `as_of` matches the assessment date.

### Clean Ticket Count
- **Clean tickets** = total tickets returned by the tickets endpoint **minus** `is_duplicate=true` **minus** `is_spam=true`.
- The metrics endpoint's `support_ticket_count` often equals the raw tickets endpoint count (including duplicates/spam), so do **not** assume it is already clean.

### Current ARR
- Use **`billing_arr_current`** from the account object as the authoritative current ARR unless the task explicitly asks for CRM ARR.
- `crm_arr` is available for cross-reference but is usually lower than billing ARR.

### Expansion Pipeline
- Filter opportunities to the requested quarter and **open stages only** (exclude `Closed Won` and `Closed Lost`) unless the task explicitly asks for all.
- Sum `amount` for open opportunities whose `close_date` falls within the period.

### Net Revenue Exposure
- Standard formula observed across tasks:
  ```
  net_revenue_exposure = arr_at_risk + open_expansion_pipeline
  ```
- Some variants may also add overdue balances; follow the explicit task instruction if provided.

### Renewal Risk Scoring (Heuristic)
When a task asks you to rank by renewal risk, compute a deterministic risk score from these factors (higher = more risk):

1. **Past-due renewal**: `renewal_date < assessment_date` → +40 to +50 points
2. **Lifecycle status**:
   - `renewal_risk` → +25
   - `paused` → +20
   - `implementation` → +5
3. **ARR exposure**: higher billing ARR → +5 to +20
4. **Overdue receivables**: >$10k → +15; >$5k → +10; >$0 → +5
5. **SLA degradation**: <85% → +10; <90% → +7
6. **Low NPS**: <30 → +10; <50 → +5; null → +3
7. **High ticket volume**: clean tickets >12 → +8; >8 → +5
8. **Low tenure**: <24 months → +10
9. **Usage decline**: <60% → +5

Thresholds for `risk_level`:
- `critical`: score ≥ 85
- `high`: score ≥ 65
- `medium`: score ≥ 45
- `low`: below 45

### Action Mapping
- `overdue_balance > 5000` → `collections_followup`
- `renewal_date` is past-due or within 30 days → `renewal_save`
- `lifecycle_status === 'renewal_risk'` → `renewal_save`
- `lifecycle_status === 'paused'` → `technical_recovery`
- `sla_compliance < 88` or high ticket volume → `technical_recovery`
- Otherwise → `nurture_monitor` or `executive_qbr`

---

## 5. Workflow Rules by Task Type

### Type A: Renewal Risk Queue (e.g., train_001)
1. Fetch account profiles for the listed `account_ids`.
2. Fetch Q2 metrics, tickets, NPS for each.
3. Fetch Q2 AR aging (`quarter: 2026-Q2`, `as_of: 2026-06-30`).
4. Compute overdue balance, clean ticket count, latest NPS, latest SLA.
5. Rank top 5 by risk score descending.
6. Populate `portfolio_summary` with aggregates over the reviewed set.
7. Include `policy_codes` block.

### Type B: QBR Metrics Packet (e.g., train_002)
1. Fetch monthly metrics for the 3 months of the quarter.
2. Use metrics `recognized_revenue` as QBR revenue, `support_ticket_count` as support tickets, `sla_compliance` as SLA, `nps_score` as NPS.
3. Compute highlights:
   - `average_revenue` = mean of 3 months
   - `peak_revenue_month` / `peak_revenue` = max month
   - `max_sla_month` / `max_sla_pct` = max SLA (to 1 decimal)
   - `peak_nps_month` / `peak_nps_score` = max NPS
   - `ticket_trend` = compare first and last month counts (`improving` if last < first)
4. Set metric sources to the most semantically appropriate enum (e.g., `billing_snapshot` for revenue, `support_export` for tickets, `sla_report` for SLA, `nps_survey` for NPS).
5. Set `review_plan` fields per task instruction; `needs_technical_signoff` is typically `false` for standard QBRs.
6. Pick exactly 4 `agenda_topics` in a logical order.

### Type C: Receivables & Pipeline Review (e.g., train_003)
1. Fetch AR aging for the quarter and filter to records with overdue > 0.
2. Link AR customers to CRM accounts by matching `customer_name` to `legal_name`.
3. Build `overdue_followups` array sorted by `customer_name` ascending.
4. Fetch opportunities for the quarter; compute won/lost/open counts and pipeline.
5. Compute `win_rate_pct` = `won_count / (won_count + lost_count) * 100` to 1 decimal.
6. Find `top_open_product_line` by summing open opportunity amounts per product line.
7. Fetch HR summary and event performance for the requested quarter/event.
8. Include `policy_codes` block.

### Type D: Churn Model Validation (e.g., train_004)
1. Read `train.csv`, `validation.csv`, `candidates.csv`.
2. `training_rows` = row count of train (180). `validation_rows` = row count of validation (60).
3. `feature_count` = total columns minus `customer_id` minus target (`Churn`) = typically **19**.
4. Build a simple churn model (logistic regression or heuristic) using training data.
5. Evaluate on validation set to get `accuracy_pct`.
6. Map `accuracy_pct` to `accuracy_band`.
7. `tenure_coefficient_direction` = `negative` if average tenure of churners < non-churners.
8. Predict probabilities for the 8 candidate accounts and return top 5.
9. Map each to `outreach_action` and `reason_code` using the same action-mapping rules.
10. Include `model_policy_codes`.

### Type E: High-Touch Retention Board (e.g., train_005)
1. Fetch account profiles, Q2 metrics, Q2 AR aging, and Q2 **open** opportunities for each listed account.
2. Compute risk score and rank all accounts.
3. Populate `action_board` with one object per account in rank order.
4. `segment_summary`:
   - Count strategic vs enterprise accounts.
   - `arr_at_risk` = sum of `current_arr`.
   - `open_expansion_pipeline` = sum of open opportunity amounts.
   - `net_revenue_exposure` = `arr_at_risk + open_expansion_pipeline`.
5. `followup_calendar` maps each action type to its due date per the task instructions.
6. Include `policy_codes` block.

---

## 6. Policy Codes

Most output templates include a `policy_codes` or `model_policy_codes` object with pipe-delimited enums. For unseen tasks, pick the first value in each pipe list as the safe default unless the task gives a specific rule:

```json
{
  "risk_model_code": "RS-2",
  "arr_source_code": "REV-1",
  "support_hygiene_code": "SUP-3",
  "action_priority_code": "ACT-1",
  "board_sort_code": "BORD-1",
  "exposure_formula_code": "EXP-2",
  "calendar_policy_code": "CAL-3",
  "receivable_trigger_code": "RCP-4",
  "crm_match_code": "CM-2",
  "pipeline_window_code": "PW-3",
  "followup_scope_code": "FS-1",
  "model_protocol_code": "MOD-2",
  "probability_scale_code": "PRB-1",
  "deployment_rule_code": "DEP-3",
  "outreach_mapping_code": "OUT-2"
}
```

---

## 7. Pitfalls & Gotchas

| Pitfall | How to Avoid |
|---|---|
| Using localhost instead of `GDPEVO_ENV_BASE_URL` | Read `environment_access.md` first; always use the remote URL it provides. |
| `billing_snapshot` endpoint does not exist | Use `account.billing_arr_current` instead. |
| Metrics `support_ticket_count` includes duplicates/spam | Compute `clean_ticket_count` manually from the tickets endpoint. |
| Forgetting to round percentages to 1 decimal | Always call `.toFixed(1)` on percentage outputs. |
| Forgetting `policy_codes` | Almost every answer template includes policy codes; include them even if the prompt doesn't explicitly mention them. |
| Using `crm_arr` when task expects `billing_arr_current` | Default to `billing_arr_current` for "current revenue exposure" and "ARR" fields. |
| Expansion pipeline includes Closed Won/Lost | Filter to open stages only unless explicitly told otherwise. |
| NPS `null` values | Preserve `null` in output when the latest month has no NPS score. |
| `link_status` for AR followups | Set to `"linked"` when `customer_name` matches a CRM account `legal_name`; otherwise `"unlinked"`. |
| Churn candidate ranking | Do not use `ActiveSeatRatio` blindly as probability; train a simple model on `train.csv` and apply it to candidates. |
| `accuracy_band` boundaries | Use `below_70`, `70_to_79`, `80_to_89`, `90_plus` (no overlap). |

---

## 8. Node.js Helper Snippet

When working in an environment without `jq` or `python`, use `node` for JSON parsing and CSV processing:

```javascript
const fs = require('fs');

function parseCSV(path) {
  const lines = fs.readFileSync(path, 'utf8').split('\n').filter(l => l.trim());
  const header = lines[0].split(',');
  return lines.slice(1).map(line => {
    const cols = line.split(',');
    const obj = {};
    header.forEach((h, i) => obj[h.trim()] = cols[i] ? cols[i].trim() : '');
    return obj;
  });
}

function fetchJson(url) {
  // Use curl in bash; save to file then require() in node
}
```

---

## 9. Output Checklist

Before returning JSON, verify:
- [ ] All required top-level keys from the answer template are present.
- [ ] Currency values have 2 decimals, percentages 1 decimal, counts are integers.
- [ ] All enums match the controlled vocabulary exactly.
- [ ] Arrays are sorted as instructed (e.g., `overdue_followups` by `customer_name` ascending).
- [ ] `policy_codes` block is included if the template has one.
- [ ] `next_touch_due_date` is mapped to the correct action type per the task's follow-up calendar.
