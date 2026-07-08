# CRM Retention Analytics Skill

## Purpose
Generate structured retention analytics reports (QBR packets, risk queues, action boards, receivables reviews, churn validation) from the ApexCloud Retention Operations API.

## API Base URL
Read `environment_access.md` in the current solver directory. Use the `GDPEVO_ENV_BASE_URL` value as the API base URL. Do not hard-code `localhost` as the operative base URL.

## Core Endpoint Families

### Account & Profile
- `GET /api/accounts/<account_id>` — account profile (ARR, segment, tenure, renewal date, health flags)
- `GET /api/accounts/<account_id>/metrics?start=YYYY-MM&end=YYYY-MM` — monthly revenue, SLA, usage metrics
- `GET /api/accounts/<account_id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` — support ticket counts and SLA breaches
- `GET /api/accounts/<account_id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` — NPS scores by survey date

### Finance & Pipeline
- `GET /api/finance/ar-aging` — A/R aging snapshot; filter by `as_of` date when needed
- `GET /api/opportunities` — open/won/lost pipeline; filter by quarter/close-date range
- `GET /api/hr/summary` — headcount and claims for ops context
- `GET /api/events/performance` — event orders and revenue for ops context

### Product Health
- `GET /api/health/usage` — product usage trends (often account-scoped or portfolio-scoped)

### Exports
- `GET /exports/churn/train.csv` — churn model training data
- `GET /exports/churn/validation.csv` — churn model validation data
- `GET /exports/churn/candidates.csv` — candidate accounts with predicted churn probabilities

## Workflow Rules

1. **Parse the prompt first**: extract account IDs, date ranges, months, as-of dates, quarter, region, and any explicit due dates.
2. **Read the answer template**: `input/payloads/answer_template.json` defines the exact output schema, required keys, and ordering.
3. **Fetch data in dependency order**:
   - Account profiles first (to validate IDs and get ARR/segment/tenure).
   - Metrics/tickets/NPS in parallel per account.
   - Finance/pipeline/HR/event data as a second wave.
   - CSV exports last (only for churn-model tasks).
4. **Cross-reference carefully**:
   - A/R customers link to CRM accounts by legal name matching; `link_status` is `"linked"` when a CRM `account_id` is found, else `"unlinked"`.
   - Use the exact `account_id` values from the prompt; never invent or normalize them.
5. **Compute derived fields** before assembling JSON:
   - `average_revenue` = mean of monthly revenues.
   - `arr_at_risk` = sum of `current_arr` for accounts with `risk_level` in (`critical`, `high`, `medium`).
   - `net_revenue_exposure` = `arr_at_risk` − `open_expansion_pipeline`.
   - `win_rate_pct` = `won_count` / (`won_count` + `lost_count`) × 100.
   - `ticket_trend` = compare early-month ticket count to late-month count: `improving` if decreasing, `worsening` if increasing, `flat` if same.
6. **Rank deterministically**: when the prompt asks for a ranked list, sort by the primary metric (risk score, churn probability, etc.) descending; break ties by `account_id` ascending.
7. **Populate `policy_codes`** exactly as required by the answer template. Common codes observed:
   - Risk model: `RS-6`
   - ARR source: `REV-4`
   - Support hygiene: `SUP-8`
   - Action priority: `ACT-5`
   - Board sort: `BORD-4`
   - Exposure formula: `EXP-6`
   - Calendar policy: `CAL-5`
   - Receivable trigger: `RCP-7`
   - CRM match: `CM-5`
   - Pipeline window: `PW-6`
   - Follow-up scope: `FS-4`
   - Model protocol: `MOD-7`
   - Probability scale: `PRB-4`
   - Deployment rule: `DEP-5`
   - Outreach mapping: `OUT-2`

## Controlled Labels (Enum Vocabularies)

Use these exact strings; never paraphrase.

### Risk Levels
- `critical`, `high`, `medium`, `low`

### Primary / Outreach Actions
- `collections_followup` — overdue receivables exist
- `technical_recovery` — SLA degradation, usage decline, or NPS drop
- `renewal_save` — renewal window approaching, low tenure
- `executive_qbr` — strategic account needing executive engagement
- `nurture_monitor` — healthy account, no immediate risk
- `no_action` — low risk, no follow-up needed

### Reason Codes
- `renewal_window` — within renewal period
- `overdue_receivable` — `overdue_balance > 0`
- `nps_drop` — NPS below threshold or declining
- `sla_degradation` — SLA compliance below 100 % or trending down
- `usage_decline` — product usage decreasing
- `low_tenure_high_churn` — short tenure combined with high churn probability
- `expansion_offset` — large open expansion pipeline offsets risk
- `clean_billings` — no overdue balance, no critical issues

### Ticket Trend
- `improving`, `worsening`, `flat`

### Metric Sources
- `crm_closed_won`, `support_export`, `sla_report`, `nps_survey`, `billing_snapshot`, `ar_aging`, `pipeline_crm`, `event_dashboard`, `hr_report`

### Review Owner
- `solutions_engineering`, `customer_success`, `finance_ops`

### Agenda Topics (QBR)
- `partnership_overview`, `q2_metrics`, `performance_highlights`, `q3_initiatives`, `technical_recovery`, `commercial_expansion`

### Link Status (Receivables)
- `linked`, `unlinked`

### Accuracy Band
- `90_plus`

### Model Checks
- `tenure_risk_direction`: `negative`, `positive`, `not_assessed`
- `uses_billing_arr_source`: boolean

## Output Precision Rules

| Field Type | Precision |
|---|---|
| Currency (revenue, ARR, balance, pipeline) | 2 decimal places |
| Percentages (SLA, win rate, accuracy) | 1 decimal place |
| Counts (tickets, accounts, orders) | Integer |
| Risk scores | Integer |
| Churn probabilities | 3 decimal places |

## Business Rules & Pitfalls

- **Collections first**: if `overdue_balance > 0`, `primary_action` should normally be `collections_followup` unless other signals are overwhelmingly stronger.
- **Renewal window + low tenure**: combine into `renewal_save` action with `renewal_window` and `low_tenure_high_churn` reason codes.
- **Expansion offset**: when an account has a large `open_expansion_pipeline`, include `expansion_offset` in `reason_codes` and subtract from exposure calculations.
- **Clean billings**: only add `clean_billings` reason code when `overdue_balance == 0` and no critical/high risk factors are present.
- **Next touch due date**: map from the prompt’s action-specific due dates; use `null` for `no_action` accounts.
- **Segment summary**: `strategic_accounts` + `enterprise_accounts` must equal total accounts reviewed. Count segments from account profile data.
- **Do not include test answers**: the skill must describe how to derive values, not provide pre-computed numbers.
- **Do not access files outside the solver attempt directory**: all inputs (prompt, answer template, environment) are inside the staged directory.

## JSON Assembly Checklist

1. Top-level keys match `answer_template.json` exactly.
2. Arrays are ordered as specified (by rank, by date, or alphabetically when instructed).
3. All enum values are from the controlled vocabularies above.
4. Numeric precision matches the table.
5. `policy_codes` object is present when the template requires it.
6. No extra keys, no missing required keys, no trailing commas.
