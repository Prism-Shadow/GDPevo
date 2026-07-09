# ApexCloud Retention Operations API — Reusable Skill

## Environment

- **Base URL**: `http://34.46.77.124:8004`
- All task prompts may reference `localhost:8074` or `127.0.0.1:8074`; ignore those — always use the base URL above.
- Never run `env/setup.sh`, never use localhost/127.0.0.1.

---

## API Endpoint Reference

These endpoint families are available. Use the one that matches the task's data requirements.

### Account & Metrics
| Endpoint | Purpose |
|---|---|
| `GET /api/accounts/<account_id>` | Account profile (ARR, tenure, segment, lifecycle stage, renewal date) |
| `GET /api/accounts/<account_id>/metrics?start=YYYY-MM&end=YYYY-MM` | Monthly metrics: revenue, usage trend, SLA, etc. |
| `GET /api/accounts/<account_id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` | Support tickets with SLA status per ticket |
| `GET /api/accounts/<account_id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` | NPS survey responses by month |

### Financial & Pipeline
| Endpoint | Purpose |
|---|---|
| `GET /api/finance/ar-aging?as_of=YYYY-MM-DD` | A/R aging with customer names, balances, aging buckets |
| `GET /api/finance/billing-snapshot?as_of=YYYY-MM-DD` | Billing snapshot with current ARR per account |
| `GET /api/opportunities?start=YYYY-MM-DD&end=YYYY-MM-DD` | CRM pipeline: won, lost, open opportunities with product lines |

### Operations Context
| Endpoint | Purpose |
|---|---|
| `GET /api/hr/summary?quarter=YYYY-QN` | HR headcount, unpaid claims |
| `GET /api/events/performance?event=<name>&quarter=YYYY-QN` | Event orders and revenue |

### Exports
| Endpoint | Purpose |
|---|---|
| `GET /exports/churn/train.csv` | Churn model training dataset (CSV) |
| `GET /exports/churn/validation.csv` | Churn model validation dataset (CSV) |
| `GET /exports/churn/candidates.csv` | Candidate accounts for churn prediction (CSV) |

### Additional Endpoints (infer from task needs)
- `GET /api/accounts/<account_id>/usage?start=YYYY-MM&end=YYYY-MM` — product usage data
- `GET /api/accounts/<account_id>/expansion?quarter=YYYY-QN` — expansion pipeline per account

---

## Numeric Precision Rules

| Data type | Precision | Example |
|---|---|---|
| Currency (ARR, revenue, overdue_balance, pipeline, claims) | **2 decimals** | `1416439.47`, `0.00` |
| Percentages (SLA, win_rate, accuracy) | **1 decimal** | `93.3`, `75.0`, `100.0` |
| Churn probability | **3 decimals** | `0.102`, `0.039`, `0.001` |
| Counts (tickets, headcount, orders, rows) | **integer** | `13`, `377`, `445` |
| Risk scores | **integer** | `100`, `60`, `15` |

---

## Controlled Vocabularies (Enums)

### Risk Levels (descending severity)
`critical` > `high` > `medium` > `low`

### Primary Actions
| Action | When to use |
|---|---|
| `collections_followup` | Overdue receivables present; A/R-driven risk |
| `technical_recovery` | SLA degradation, usage decline, NPS drop; product/tech-driven risk |
| `renewal_save` | Account is in or near a renewal window with elevated risk |
| `executive_qbr` | Strategic/escalation — highest-touch intervention |
| `nurture_monitor` | Low risk; monitor and engage lightly |
| `no_action` | Lowest risk tier; no active intervention needed |

### Reason Codes
| Code | Trigger |
|---|---|
| `overdue_receivable` | Account has an overdue balance in A/R aging |
| `low_tenure_high_churn` | Low-tenure account in a high-churn segment/cohort |
| `sla_degradation` | SLA compliance below threshold or declining |
| `nps_drop` | NPS declined vs prior period or below benchmark |
| `usage_decline` | Product usage trending down |
| `renewal_window` | Renewal date falls within analysis window or near term |
| `expansion_offset` | Open expansion pipeline partially offsets risk (mitigating factor) |
| `clean_billings` | No overdue balance — billing is current (positive signal) |

### Metric Sources (use these exact labels)
- `crm_closed_won` — revenue from CRM won deals
- `support_export` — support ticket counts
- `sla_report` — SLA compliance data
- `nps_survey` — NPS survey responses
- `billing_snapshot` — billing/ARR data
- `ar_aging` — accounts receivable aging
- `pipeline_crm` — CRM pipeline/opportunity data
- `event_dashboard` — event performance data
- `hr_report` — HR/headcount data

### Ticket Trend
`improving` | `worsening` | `flat`
— Compare ticket counts month-over-month across the period. Fewer tickets each month = improving.

### Accuracy Band (churn model)
`below_70` | `70_to_79` | `80_to_89` | `90_plus`

### Tenure / Coefficient Direction
`negative` | `positive` | `not_assessed` | `zero`

### Link Status (A/R to CRM matching)
`linked` | `unlinked`
— When an A/R customer cannot be matched to any CRM account_id, it is `unlinked` and `account_id` is `null`.

### Review Owner
`solutions_engineering` | `customer_success` | `finance_ops`

### Agenda Topics (QBR)
`partnership_overview` | `q2_metrics` | `performance_highlights` | `q3_initiatives` | `technical_recovery` | `commercial_expansion`

---

## Business Logic Rules

### Risk Score Computation
Risk score is a composite integer (0-100) derived from these weighted signals:
- Overdue receivables (high weight)
- NPS decline (medium-high weight)
- SLA degradation (medium weight)
- Usage decline (medium weight)
- Renewal window proximity (medium weight)
- Low tenure / high churn segment (medium weight)
- Expansion pipeline partially offsets (subtractive)

**Score-to-level mapping:**
- 70–100 → `critical`
- 50–69 → `high`
- 20–49 → `medium`
- 0–19 → `low`

### Reaching for Expansion Pipeline
The `expansion_pipeline` field (in retention boards) is the total open opportunity value for the account within the quarter. Include it even when zero (use `0.0`).

### Net Revenue Exposure
`net_revenue_exposure = arr_at_risk - open_expansion_pipeline`
Compute to 2 decimal places.

### ARR at Risk
Sum of `current_arr` for all accounts ranked `critical` or `high`. Compute to 2 decimal places.

### Overdue Balance
When zero, output `0.0` (not `null`). Add `clean_billings` as a reason code when there is no overdue balance — this is a positive signal.

### Sorting Rules
- **Risk accounts / action board**: Sort by risk score descending (highest risk first). Within ties, higher ARR first.
- **Overdue follow-ups**: Sort by `customer_name` ascending (alphabetical).
- **QBR metrics**: Order months chronologically.

### NPS Handling
- Use the **latest** NPS score in the period as `latest_nps`.
- For trends, compare across months. Peak NPS is the highest monthly score.

### SLA Compliance
Compute from ticket data: `(tickets_within_sla / total_tickets) * 100`, rounded to 1 decimal. If there are 0 tickets, SLA is `100.0`.

### Support Ticket Counting
Count only "clean" (non-spam, non-duplicate) tickets. The API may return a `clean_ticket_count` or you may need to filter by ticket status.

### Churn Model Validation
- Read the CSV exports directly; they contain labeled rows.
- `training_rows`: row count of train.csv (excluding header)
- `validation_rows`: row count of validation.csv (excluding header)
- `feature_count`: number of feature columns (excluding ID and label columns)
- `accuracy_pct`: from the model metadata or computed from validation results
- `tenure_coefficient_direction`: extracted from model coefficients; `negative` means higher tenure → lower churn risk
- Accuracy band is binned from accuracy_pct

### Churn Candidate Ranking
- Read candidates.csv for the candidate accounts listed in the prompt.
- Rank by `predicted_churn_probability` descending, take top 5.
- Map churn probability to outreach action:
  - ≥ 0.05 → `collections_followup` or `renewal_save` (depending on root cause)
  - 0.01–0.05 → `renewal_save` or `technical_recovery`
  - < 0.01 → `nurture_monitor`

### A/R-to-CRM Linking
- Take customer names from the A/R aging endpoint.
- Match against CRM accounts by name (fuzzy — watch for "Inc.", "LLC", "Ltd.", "Group" suffix variations).
- If a match is found: `link_status = "linked"`, populate `account_id`.
- If no match: `link_status = "unlinked"`, `account_id = null`.

### Policy Codes
Policy codes appear in responses from the API itself. Read them from the API response payloads — do not invent them. Common code families:
- `RS-*` — risk scoring protocol
- `REV-*` — revenue/ARR source
- `SUP-*` — support hygiene
- `ACT-*` — action priority
- `RCP-*` — receivable trigger
- `CM-*` — CRM match rules
- `PW-*` — pipeline window
- `FS-*` — follow-up scope
- `MOD-*` — model protocol (churn)
- `PRB-*` — probability scale (churn)
- `DEP-*` — deployment rules (churn)
- `OUT-*` — outreach mapping (churn)
- `BORD-*` — board sort order
- `EXP-*` — exposure formula
- `CAL-*` — calendar policy

**Always include the policy_codes block** when the answer template has one. Copy the codes from the relevant API response(s).

### Follow-up Due Dates
When the task gives due dates by action type, use them exactly:
- `collections_followup` → typically 15 days after as-of date
- `technical_recovery` → typically 18 days after as-of date
- `renewal_save` → typically 22 days after as-of date
- `executive_qbr` → typically 29 days after as-of date
- `nurture_monitor` → typically 36 days after as-of date

The exact dates will be provided in the task prompt. For `no_action`, `next_touch_due_date` is `null`.

### Portfolio / Segment Summaries
- `accounts_reviewed`: total accounts evaluated
- `critical_or_high_count`: count of accounts with risk_level critical or high
- `collections_count`: count of accounts with primary_action `collections_followup`
- `technical_recovery_count`: count of accounts with primary_action `technical_recovery`
- `strategic_accounts` / `enterprise_accounts`: from account segment field in API

---

## Workflow Procedure

### Step 1: Orient
1. Read `environment_access.md` for the base URL.
2. Read the task prompt. Extract: task type, account IDs, date ranges, as-of dates, quarter, months, and any special parameters.
3. Read `input/payloads/answer_template.json` to understand the required output shape, enum options, and which sections are expected.

### Step 2: Fetch Data
1. Determine which endpoint families are needed based on the output shape and task description.
2. Call each endpoint with the correct parameters. Use the date formats exactly: `YYYY-MM-DD` for dates, `YYYY-MM` for months, `YYYY-QN` for quarters.
3. For per-account endpoints, iterate over all specified account_ids.
4. For churn tasks, fetch the CSV exports and parse them.

### Step 3: Compute & Transform
1. Apply the numeric precision rules consistently.
2. Compute derived values (risk scores, averages, sums, win rates) from raw API data.
3. Map raw signals to controlled enum values using the vocabularies above.
4. Sort lists according to the sorting rules.
5. Compute segment summaries by aggregating over the ranked accounts.

### Step 4: Assemble Output
1. Start from the answer template structure.
2. Populate every field. Never omit a key from the template.
3. Use `null` for genuinely absent values (e.g., `account_id` for unlinked customers, `next_touch_due_date` for no_action).
4. Use `0.0` (not null) for zero-value currency/percentage fields.
5. Include policy_codes read from API responses.
6. Output **pure JSON only** — no markdown fences, no explanatory text, no trailing commas.

---

## Pitfalls & Edge Cases

1. **Port mismatch**: Task prompts say port 8074; always use port 8004 from environment_access.md.
2. **A/R customer name variants**: "North Star Finance Services" vs "Northstar Finance Group Inc." — these are different entities. Match carefully; when in doubt, leave unlinked.
3. **Zero tickets in a month**: SLA compliance is 100.0, not undefined.
4. **Multiple NPS scores per month**: Use the most recent survey response within that month.
5. **Null vs 0.0**: Currency fields use `0.0` for zero, `null` only when the data is genuinely absent (e.g., account_id for unlinked).
6. **Sort stability**: When risk scores tie, use ARR descending as secondary sort. When names tie (unlikely), preserve API order.
7. **Policy codes are read, not computed**: Don't guess policy codes. They come from the API response payloads. If an endpoint doesn't return them, the code may be embedded in a different endpoint's response.
8. **Month format consistency**: API path params use `YYYY-MM`, date range params use `YYYY-MM-DD`. Don't mix them.
9. **CSV parsing**: The churn exports have a header row. `training_rows` = total rows minus 1 (the header). Feature count = total columns minus label and ID columns.
10. **Expansion pipeline is additive**: An account can have both risk signals AND expansion pipeline — `expansion_offset` is a reason code, not a risk eliminator. It offsets but doesn't cancel risk.
11. **Output is always pure JSON**: Never wrap in ```json fences or add commentary. The evaluator expects raw parseable JSON.
