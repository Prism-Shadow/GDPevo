# ApexCloud Retention Operations — Agent Skill

Use this skill to execute revenue-retention analysis tasks against the ApexCloud Retention Operations API. It covers the API surface, output conventions, controlled vocabularies, business-policy rules, and common pitfalls distilled from solved Q2/Q3 2026 tasks.

---

## 1. Environment

- **Base URL:** Consult `environment_access.md` in the task directory. Use the `GDPEVO_ENV_BASE_URL` value (a remote IP) for all API calls.
- **Never** start the task-group environment, run `env/setup.sh`, or use `localhost`/`127.0.0.1` directly — the environment_access.md URL is authoritative and overrides any localhost reference in a task prompt.

---

## 2. API Endpoint Catalogue

All endpoints sit under the base URL. Use the exact parameter names and formats shown.

### 2.1 Account Profile
```
GET /api/accounts/<account_id>
```
Returns account metadata: legal name, segment (strategic/enterprise), tenure, lifecycle stage, renewal date, and current ARR.

### 2.2 Account Metrics (Usage)
```
GET /api/accounts/<account_id>/metrics?start=YYYY-MM&end=YYYY-MM
```
Returns monthly usage data. `start` and `end` are **month-level** strings (e.g. `2026-04`, `2026-06`). Response includes usage trend indicators.

### 2.3 Support Tickets
```
GET /api/accounts/<account_id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD
```
Returns support tickets in the date range. `start` and `end` are **date-level** strings. Key fields: ticket count, SLA compliance percentage per month.

### 2.4 NPS Scores
```
GET /api/accounts/<account_id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD
```
Returns NPS survey results in the date range. Key fields: NPS score per survey or per month.

### 2.5 Billing Snapshot
```
GET /api/accounts/<account_id>/billing-snapshot
```
Returns the billing-system ARR for the account. This is the authoritative ARR source when available.

### 2.6 A/R Aging
```
GET /api/finance/ar-aging?as_of=YYYY-MM-DD
```
Returns all customers with outstanding receivables and their aging buckets. Key fields: `customer_name`, `overdue_balance`, aging-bucket breakdowns.

### 2.7 CRM Pipeline / Opportunities
```
GET /api/opportunities?quarter=YYYY-QN
```
Returns pipeline opportunities. Key fields: product line, amount, stage (won/lost/open), close date.

### 2.8 HR Summary
```
GET /api/hr/summary?quarter=YYYY-QN
```
Returns headcount and unpaid-claims totals for the period.

### 2.9 Events
```
GET /api/events/performance?event=<event_slug>&quarter=YYYY-QN
```
Returns event metrics: orders, revenue.

### 2.10 Churn Exports
```
GET /exports/churn/train.csv
GET /exports/churn/validation.csv
GET /exports/churn/candidates.csv
```
CSV exports for churn model work. Training rows = row count minus 1 (header). Feature count = column count minus 1 (exclude target/label column). Validation rows = row count minus 1.

---

## 3. Output Precision Conventions

Apply these to **every** numeric field in the output JSON — the evaluator expects deterministic precision:

| Data type | Precision | Example |
|---|---|---|
| Currency (ARR, revenue, overdue, pipeline) | **2 decimal places** | `1416439.47`, `0.00` |
| Percentages (SLA, win rate, accuracy) | **1 decimal place** | `93.3`, `100.0`, `66.7` |
| Counts (tickets, accounts, headcount) | **integers** | `13`, `377` |
| Risk scores | **integers** | `100`, `60`, `15` |
| Churn probabilities | **3 decimal places** | `0.102`, `0.039`, `0.001` |

Always include trailing zeros to match the precision target (e.g. `0.0` not `0`, `100.0` not `100`). Empty/null numeric fields use `0`, `0.0`, or `0.00` depending on type — never omit a required numeric field.

---

## 4. Controlled Vocabulary

Use these exact enum strings. Do not invent variants, add spaces, or change casing.

### 4.1 Risk Levels
`critical` | `high` | `medium` | `low`

### 4.2 Primary Actions
`collections_followup` — overdue receivables exist  
`technical_recovery` — SLA degradation or usage decline  
`renewal_save` — renewal window concern, low tenure + high churn  
`executive_qbr` — executive-level engagement needed  
`nurture_monitor` — low risk, monitor passively  
`no_action` — no active intervention required  

### 4.3 Reason Codes
`overdue_receivable` — non-zero overdue balance  
`low_tenure_high_churn` — short tenure + elevated churn probability  
`sla_degradation` — SLA compliance dropping or below threshold  
`nps_drop` — NPS score decline  
`usage_decline` — product usage trending down  
`renewal_window` — renewal date falls within the analysis window  
`expansion_offset` — open expansion pipeline partially offsets risk  
`clean_billings` — no overdue balance, billing is current  

### 4.4 Ticket Trend
`improving` | `worsening` | `flat`

### 4.5 Metric Sources
`crm_closed_won` | `support_export` | `sla_report` | `nps_survey` | `billing_snapshot` | `ar_aging` | `pipeline_crm` | `event_dashboard` | `hr_report`

### 4.6 Review Owner
`solutions_engineering` | `customer_success` | `finance_ops`

### 4.7 Agenda Topics (QBR)
`partnership_overview` | `q2_metrics` | `performance_highlights` | `q3_initiatives` | `technical_recovery` | `commercial_expansion`

### 4.8 Link Status
`linked` | `unlinked`

### 4.9 Accuracy Band
`below_70` | `70_to_79` | `80_to_89` | `90_plus`

### 4.10 Tenure / Coefficient Direction
`negative` | `positive` | `zero` | `not_assessed`

---

## 5. Business-Policy Rules

### 5.1 ARR Source
- When billing-snapshot data exists for an account, **it is the authoritative ARR source**.
- Set `uses_billing_arr_source: true` when billing snapshots were queried and used.
- If billing snapshots are unavailable (e.g. account not found in billing system), fall back to the account-profile ARR and set `uses_billing_arr_source: false`.

### 5.2 Risk Scoring Heuristics
Risk is additive — each factor pushes the score up. Assign integer scores and let the relative ordering determine rank. Typical score ranges observed:
- **critical (100):** renewal window + multiple severe factors (overdue, NPS drop, SLA degradation, usage decline)
- **high (50–60):** overdue receivable + SLA degradation, or NPS drop + SLA + usage decline
- **medium (30–50):** renewal window + single concern, or overdue + SLA without other factors
- **low (15–20):** only SLA degradation or only NPS drop with no other factors
- When an account has `clean_billings` as its only code, score should be low.

### 5.3 Risk-Level Thresholds
Map scores to levels consistently:
- `critical`: score ≥ 80
- `high`: score 50–79
- `medium`: score 30–49
- `low`: score < 30

### 5.4 Action Mapping Rules
- **overdue_balance > 0** → action is `collections_followup`, reason code includes `overdue_receivable`
- **low tenure + high churn probability** → action is `renewal_save`, reason code includes `low_tenure_high_churn`
- **SLA degradation or usage decline** (without overdue) → action is `technical_recovery`
- **No risk factors** → action is `nurture_monitor` or `no_action`, reason code includes `clean_billings`

### 5.5 A/R ↔ CRM Linking
When correlating A/R aging customers to CRM accounts:
- Match `customer_name` from A/R to `legal_name` from the account profile.
- **Match found** → `link_status: "linked"`, `account_id` set to the matched account ID.
- **No match** → `link_status: "unlinked"`, `account_id: null`.
- Sort `overdue_followups` by `customer_name` **ascending** (lexicographic).

### 5.6 Follow-Up Due Dates
When the task specifies follow-up dates by action type, replicate the full `followup_calendar` object with all five action types. Typical offsets from a June 30 assessment date:
- `collections_followup`: 2026-07-15
- `technical_recovery`: 2026-07-18
- `renewal_save`: 2026-07-22
- `executive_qbr`: 2026-07-29
- `nurture_monitor`: 2026-08-05

In the `next_touch_due_date` per account, use the due date for that account's `primary_action`. For `no_action`, set `next_touch_due_date: null`.

### 5.7 Net Revenue Exposure
```
net_revenue_exposure = arr_at_risk - open_expansion_pipeline
```
Where `arr_at_risk` is the sum of `current_arr` for all accounts with risk_level `critical` or `high`. Round to 2 decimal places.

### 5.8 Win Rate
```
win_rate_pct = round((won_count / (won_count + lost_count)) * 100, 1)
```
If denominator is 0, return `0.0`.

### 5.9 Tenure Risk Direction
- `negative` — longer tenure correlates with lower churn risk (standard expectation)
- `positive` — longer tenure correlates with higher churn risk (unusual)
- `zero` — no correlation
- `not_assessed` — tenure data unavailable or model didn't include it

### 5.10 Ranking and Ordering
- **Risk queues:** Rank by `risk_score` descending. Break ties by `current_arr` descending.
- **Churn rankings:** Rank by `predicted_churn_probability` descending.
- **Action boards:** Rank by `risk_score` descending. Include **all** accounts in scope, not just a top-N.
- **"Top N" tasks:** Return exactly N entries in the ranked list, even if some have minimal risk.

### 5.11 QBR Metric Assignments
- `revenue` source: `crm_closed_won`
- `support_tickets` source: `support_export`
- `sla_compliance` source: `sla_report`
- `nps` source: `nps_survey`
- `ticket_trend`: compare first-month to last-month ticket counts — if decreasing `improving`, increasing `worsening`, same `flat`.

### 5.12 Policy Codes
Always include the `policy_codes` block when the answer template has one. The set of codes varies by task type. Use the code patterns observed:
- Risk model: `RS-6`
- ARR source: `REV-4`
- Support hygiene: `SUP-8`
- Action priority: `ACT-5`
- Receivable trigger: `RCP-7`
- CRM match: `CM-5`
- Pipeline window: `PW-6`
- Follow-up scope: `FS-4`
- Model protocol: `MOD-7`
- Probability scale: `PRB-4`
- Deployment rule: `DEP-5`
- Outreach mapping: `OUT-2`
- Board sort: `BORD-4`
- Exposure formula: `EXP-6`
- Calendar policy: `CAL-5`

Select the code variant (the suffix digit) based on the context: mid-range digits (4–7) are the standard/conservative policy selections. When in doubt, use the middle option from the template's allowed values.

---

## 6. Execution Workflow

### Step 1 — Read the answer template
Always locate and read `input/payloads/answer_template.json` first. It defines the exact output structure including field names, enum choices, and required nesting.

### Step 2 — Parse the task parameters
Extract from the prompt:
- Account IDs (list them explicitly)
- Date ranges, months, quarters
- Assessment / as-of dates
- Any special sort orders or follow-up dates

### Step 3 — Fetch all relevant data
Query every endpoint the task references. For multi-account tasks, loop over each account_id. Key data to collect per account:
- Account profile (legal name, segment, tenure, lifecycle, renewal date, ARR)
- Billing snapshot (authoritative ARR)
- Monthly metrics (usage trends)
- Support tickets (count, SLA by month)
- NPS scores (latest + trend)
- A/R aging (overdue balance)

For cross-cutting queries (A/R aging, opportunities, HR, events), fetch once and filter/correlate.

### Step 4 — Compute derived values
- Risk scores: additive factor model (see §5.2)
- Risk levels: threshold mapping (see §5.3)
- Primary actions: rule-based (see §5.4)
- Reason codes: collect all applicable codes for each account
- Portfolio/summary aggregations

### Step 5 — Assemble the JSON
Start from the answer template. Fill every field. Apply precision rules strictly. Use the controlled vocabulary exactly. Verify:
- All arrays have the correct count
- All numeric fields have correct precision
- All enum fields use exact allowed values
- `null` is used only where the template explicitly allows it (e.g. `account_id` for unlinked, `next_touch_due_date` for no_action)
- Sort order matches the task requirements

---

## 7. Common Pitfalls

1. **Wrong base URL** — Never use localhost. Always read `environment_access.md` and use `GDPEVO_ENV_BASE_URL`.

2. **Precision drift** — `0` is not `0.0` is not `0.00`. Match the field's precision convention exactly. A risk score of `100` must be an integer, not `100.0`.

3. **Extra or missing reason codes** — Every account in a risk ranking gets at least one reason code. Don't omit `clean_billings` when there are no billing issues. Don't omit `overdue_receivable` when overdue_balance > 0.

4. **Wrong list size** — When the task says "top 5", return exactly 5 entries. When it says "all accounts", return every account in scope. Don't truncate or pad.

5. **Sort order violations** — Risk rankings are score-descending then ARR-descending. Overdue followups are customer_name ascending. Churn rankings are probability-descending.

6. **A/R ↔ CRM matching failures** — Match by `customer_name` ↔ `legal_name`. Check for exact matches as well as common variations (e.g. "North Star Finance Services" vs "Northstar Finance Group Inc." may not match; "Globex North Holdings LLC" matches `acct_globex_north`).

7. **Missing policy_codes block** — Always include it when the template has one. Use standard mid-range codes unless the data clearly warrants a different variant.

8. **Wrong metric sources** — Don't guess source enums. Revenue comes from CRM (`crm_closed_won`), not billing. Support tickets come from the support system (`support_export`), not CRM. Match each metric to its canonical source.

9. **net_revenue_exposure sign** — This is `arr_at_risk - open_expansion_pipeline`. Expansion pipeline **reduces** exposure (offsets risk). A negative value is possible if expansion pipeline exceeds ARR at risk.

10. **next_touch_due_date for no_action** — Must be `null`, not an empty string or a date.

11. **SLA compliance** — When a month has no tickets, SLA compliance is `100.0` (not `0.0` and not `null`). An empty support queue is compliant.

12. **NPS when no surveys** — When an account has no NPS surveys in the period, use the most recent available score. Only use `null` if the template explicitly allows it for NPS fields.
