## When to Use

Use this skill when a task requires building structured retention-operations reports by calling the **ApexCloud Retention Operations API**. Typical deliverables are renewal-risk queues, QBR metric packets, receivables/pipeline reviews, churn-model validation readouts, and high‑touch retention action boards. Every response must be **JSON‑only**, follow the task‑supplied template exactly, and use the controlled vocabularies and precision rules described below.

---

## API Access

The base URL is provided through the environment variable or placeholder `<TASK_ENV_BASE_URL>`. All endpoints are read‑only `GET`. No authentication headers are required.

### Endpoint Reference

| Endpoint | Returns |
|---|---|
| `/api/accounts` | List of all CRM accounts (id, name, domain, segment, lifecycle stage, active status, region, owner). |
| `/api/accounts/{account_id}` | Single account profile including current ARR, tenure months, segment, lifecycle stage, and region. |
| `/api/accounts/{account_id}/metrics` | Monthly usage/product‑adoption metrics. Accepts `?start=YYYY-MM&end=YYYY-MM`. |
| `/api/accounts/{account_id}/tickets` | Support tickets. Accepts `?start=YYYY-MM-DD&end=YYYY-MM-DD`. |
| `/api/accounts/{account_id}/nps` | NPS survey responses. Accepts `?start=YYYY-MM-DD&end=YYYY-MM-DD`. |
| `/api/accounts/{account_id}/billing` | Billing records / current ARR snapshot. |
| `/api/accounts/{account_id}/ar-aging` | Per‑account receivables aging buckets. |
| `/api/billing/snapshots` | Global or filtered billing-snapshot data. |
| `/api/finance/ar-aging` | Finance‑side A/R aging (customer‑name oriented, may include non‑CRM entities). |
| `/api/opportunities` | CRM pipeline (open/won/lost opportunities with amounts, product lines, close dates). |
| `/api/hr/summary` | Headcount and unpaid‑claims aggregates. Supports region and quarter filters. |
| `/api/events/performance` | Event‑performance data (orders, revenue) for named events such as `apex_connect`. |
| `/exports/churn/train.csv` | Churn‑model training dataset. |
| `/exports/churn/validation.csv` | Churn‑model validation dataset. |
| `/exports/churn/candidates.csv` | Candidate accounts with predicted churn probabilities. |
| `/exports/account_metric_extract.csv` | Bulk account‑metric extract. |

### Calling Pattern

```
GET <TASK_ENV_BASE_URL>/api/accounts/{account_id}/metrics?start=2026-04&end=2026-06
```

Fetch data for every account and every relevant endpoint listed in the task prompt. Cross‑reference results so that customers appearing in the A/R aging export are matched to CRM accounts when a matching account exists (link status `linked` or `unlinked`).

---

## Controlled Vocabularies

Always use these enum values exactly. Never invent new labels.

### Account Risk

| Field | Values |
|---|---|
| `risk_level` | `critical`, `high`, `medium`, `low` |
| `primary_action` | `executive_qbr`, `collections_followup`, `technical_recovery`, `renewal_save`, `nurture_monitor`, `no_action` |
| `reason_codes` (array) | `overdue_receivable`, `low_tenure_high_churn`, `sla_degradation`, `nps_drop`, `usage_decline`, `renewal_window`, `expansion_offset`, `clean_billings` |

### Ticket / SLA

| Field | Values |
|---|---|
| `ticket_trend` | `improving`, `worsening`, `flat` |

### Metric Sources

| Field | Values |
|---|---|
| `metric_sources.*` | `crm_closed_won`, `support_export`, `sla_report`, `nps_survey`, `billing_snapshot`, `ar_aging`, `pipeline_crm`, `event_dashboard`, `hr_report` |

### QBR / Review

| Field | Values |
|---|---|
| `review_owner` | `solutions_engineering`, `customer_success`, `finance_ops` |
| `agenda_topics` (ordered) | `partnership_overview`, `q2_metrics`, `performance_highlights`, `q3_initiatives`, `technical_recovery`, `commercial_expansion` |

### Churn Model

| Field | Values |
|---|---|
| `accuracy_band` | `below_70`, `70_to_79`, `80_to_89`, `90_plus` |
| `tenure_coefficient_direction` | `negative`, `positive`, `zero` |
| `outreach_action` | `renewal_save`, `technical_recovery`, `collections_followup`, `nurture_monitor` |
| `tenure_risk_direction` | `negative`, `positive`, `not_assessed` |

### Link Status

| Value | Meaning |
|---|---|
| `linked` | The customer entity from finance/A/R data maps to a CRM account. |
| `unlinked` | No matching CRM account was found; `account_id` must be `null`. |

---

## Precision & Formatting Rules

- **Currency** (`current_arr`, `overdue_balance`, `revenue`, pipeline amounts, etc.): always **2 decimal places**.
- **Percentages** (`sla_compliance_pct`, `win_rate_pct`, `accuracy_pct`, etc.): always **1 decimal place**.
- **Churn probabilities** (`predicted_churn_probability`): always **3 decimal places**.
- **Counts** (`clean_ticket_count`, `support_tickets`, `accounts_reviewed`, headcount, etc.): always **integers**.
- **Risk scores**: always **integers**.
- **Dates**: use `YYYY-MM-DD` format (e.g., `2026-06-30`).
- **Months**: use `YYYY-MM` format (e.g., `2026-04`).
- **Booleans**: use JSON `true`/`false`.
- **Nulls**: use JSON `null` when a value is genuinely absent (e.g., no NPS score for a month, no `next_touch_due_date` for no‑action accounts).

---

## Policy Codes

Many templates include a `policy_codes` block. Policy codes follow the pattern `{PREFIX}-{DIGIT}` (e.g., `RS-6`, `REV-4`, `MOD-7`). Derive policy codes from the data following these conventions:

- **Risk model codes** (`RS-*`): based on accounts' risk‑score distribution.
- **ARR source codes** (`REV-*`): `REV-4` when billing snapshots are the primary ARR source; `REV-1` when account profiles are used; `REV-8` for mixed sources.
- **Support hygiene codes** (`SUP-*`): based on ticket‑count and SLA‑compliance patterns across the portfolio.
- **Action priority codes** (`ACT-*`): based on the action‑type distribution in the ranked output.
- **Receivable trigger codes** (`RCP-*`): based on overdue‑bucket aging patterns.
- **CRM match codes** (`CM-*`): based on how many A/R customers link to CRM accounts.
- **Pipeline window codes** (`PW-*`): based on the quarter's pipeline composition (open/won/lost mix).
- **Follow‑up scope codes** (`FS-*`): based on how many distinct follow‑up actions were generated.
- **Model protocol codes** (`MOD-*`): based on churn‑model row count and feature‑count tiers.
- **Probability scale codes** (`PRB-*`): based on the magnitude of predicted probabilities in the top‑5.
- **Deployment rule codes** (`DEP-*`): based on accuracy band.
- **Outreach mapping codes** (`OUT-*`): based on outreach‑action composition.
- **Board sort codes** (`BORD-*`): based on the sorting order of the action board.
- **Exposure formula codes** (`EXP-*`): based on how net revenue exposure was computed.
- **Calendar policy codes** (`CAL-*`): based on the follow‑up date assignments.

---

## Task Archetypes & Workflow

### 1. Renewal Risk Queue

- Fetch accounts, metrics, tickets, NPS, billing, and A/R aging for the listed `account_ids`.
- Rank by risk using a composite that considers: renewal timing, current ARR, NPS trajectory, SLA degradation, usage decline, overdue receivables, tenure, and lifecycle stage.
- Return top N accounts with ordered ranking, risk scores, and reason codes.
- Include a `portfolio_summary` aggregating counts and ARR‑at‑risk across all reviewed accounts.
- Include `model_checks` with `uses_billing_arr_source` (boolean) and `tenure_risk_direction`.

### 2. QBR Metrics Packet

- Fetch monthly metrics, tickets, SLA, and NPS for the specified single account over the three‑month window.
- Compute `highlights`: average revenue, peak month/values, ticket trend.
- Determine `metric_sources` for each metric field using the source‑enum vocabulary.
- Set `review_plan` with the correct owner and signoff flag.
- Build exactly four ordered `agenda_topics`.

### 3. Receivables & Pipeline Operations Review

- Start from `/api/finance/ar-aging`; isolate customers with overdue balances.
- For each overdue customer, attempt to link to a CRM account via `/api/accounts` lookup.
- Fetch `/api/opportunities` for the quarter; compute win/loss/open pipeline summary with win rate and top product line.
- Fetch `/api/hr/summary` and `/api/events/performance` for ops context.
- Sort `overdue_followups` by `customer_name` ascending; every follow‑up uses `collections_followup` as the primary action.

### 4. Churn Model Validation & Outreach Ranking

- Fetch and parse `/exports/churn/train.csv`, `/exports/churn/validation.csv`, and `/exports/churn/candidates.csv`.
- Validate the model: count rows, features, compute accuracy, determine accuracy band, check tenure coefficient direction.
- From candidates.csv, filter to the specified `customer_id` list and rank top N by descending predicted churn probability.
- Map each ranked account to the most appropriate `outreach_action` and `reason_code` based on their characteristics.
- Compute `cohort_checks`: past‑due shortlist count, low‑tenure shortlist count, average probability of top 5.

### 5. High‑Touch Retention Action Board

- Fetch full account profiles, billing snapshots, metrics, tickets, NPS, A/R aging, and expansion opportunities for all listed `account_ids`.
- Build the `action_board` ranked by risk, including expansion‑pipeline context and A/R exposure.
- Assign each account a `next_touch_due_date` from the follow‑up calendar based on its `primary_action`. Accounts with `no_action` get `null`.
- Compute `segment_summary` with strategic/enterprise breakdown, ARR‑at‑risk, open expansion pipeline, and net revenue exposure.
- Populate `followup_calendar` with the due dates provided in the prompt.

---

## General Rules

1. **Read the task prompt carefully** — it specifies the exact accounts, date ranges, ranking count, sort order, follow‑up dates, and output template.
2. **Fetch all relevant data before ranking or computing** — cross‑reference endpoints.
3. **Always use the controlled vocabularies** — never invent free‑form labels.
4. **Always apply the precision rules** — mismatched formatting makes output invalid.
5. **Policy codes must use the code‑digit format** — derive from the actual data distribution, not from placeholder hints.
6. **Return only valid JSON** — no markdown fences, no surrounding text, no trailing commas.
7. **Match the answer template structure exactly** — every key, every nesting level, every type.
8. **Sort according to the prompt** — risk rank (descending risk), candidate probability (descending), customer name (ascending) for follow‑ups.
9. **When linking A/R customers to CRM accounts**, match by name similarity. If no plausible match exists, mark `unlinked` with `account_id: null`.
10. **For no‑action accounts**, set `next_touch_due_date` to `null` and omit them from the active follow‑up calendar unless the template requires a placeholder.
