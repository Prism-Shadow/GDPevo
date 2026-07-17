# CRM Retention Analytics Skill

## API Base URL

Use the API base URL from the solver's environment: read `environment_access.md` for the operative `GDPEVO_ENV_BASE_URL`. Do not hard-code `localhost` or `127.0.0.1` as the base URL.

## Endpoint Inventory

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Service health, seed, and row counts for all underlying data sources. Use to verify connectivity and discover dataset sizes. |
| `/api/accounts` | GET | All accounts. Returns `{ "accounts": [...], "count": N }`. No query-parameter filtering is supported; filter client-side. |
| `/api/accounts/{account_id}` | GET | Single account record with full profile. |
| `/api/accounts/{account_id}/metrics` | GET | Monthly account metrics (12 records). Returns `{ "account_id", "count", "metrics": [...] }`. |
| `/api/accounts/{account_id}/nps` | GET | NPS response history. Returns `{ "account_id", "count", "nps_responses": [...] }`. |
| `/api/accounts/{account_id}/tickets` | GET | Support ticket history. Returns `{ "account_id", "count", "tickets": [...] }`. |
| `/api/opportunities` | GET | All CRM opportunities. Returns `{ "opportunities": [...], "count": N }`. No query-parameter filtering is supported; filter client-side. |

**Note on undiscovered endpoints:** The health endpoint references additional datasets (`ar_aging.json`, `billing_snapshots.json`, `churn_candidates.csv`, `event_performance.json`, `hr_summary.json`) that may not be exposed as public REST endpoints in all environments. If a task requires receivables, HR headcount, event orders, or churn-risk scores and no dedicated endpoint responds, derive the values from the available endpoints or request guidance. Always attempt the standard `/api/*` path first, then account-scoped `/api/accounts/{id}/<resource>` variants.

## Data Models

### Account
- `account_id` (string, e.g. `acct_globex_north`)
- `account_aliases` (string[])
- `display_name` (string)
- `legal_name` (string)
- `segment` (string enum: `Strategic`, `Enterprise`, `Mid-Market`)
- `product_plan` (string enum: `Launch`, `Growth`, `Scale`, `Enterprise`, `Strategic`)
- `lifecycle_status` (string enum: `active`, `implementation`, `renewal_risk`, `paused`)
- `region` (string)
- `csm_owner` (string)
- `contract_tenure_months` (integer)
- `renewal_date` (string, `YYYY-MM-DD`)
- `crm_arr` (float) — ARR as recorded in CRM
- `billing_arr_current` (float) — ARR as recorded in billing

### Opportunity
- `opportunity_id` (string)
- `account_id` (string)
- `account_legal_name` (string)
- `product_line` (string enum: `AI Assist`, `Workflow Plus`, `Core Retention`, `Data Cloud`)
- `stage` (string enum: `Discovery`, `Prospecting`, `Proposal`, `Negotiation`, `Closed Won`, `Closed Lost`)
- `state` (string enum: `open`, `closed`) — `open` = not yet won or lost; `closed` = won or lost
- `amount` (float)
- `close_date` (string, `YYYY-MM-DD`)
- `created_date` (string, `YYYY-MM-DD`)
- `region` (string)

### Monthly Metric
- `month` (string, `YYYY-MM`)
- `quarter` (string, `YYYY-QN`)
- `active_seats` (integer)
- `product_usage` (float, 0–100)
- `nps_score` (integer)
- `recognized_revenue` (float)
- `sla_compliance` (float, 0–100)
- `support_ticket_count` (integer)
- `survey_status` (string enum: `completed`, `pending`, `skipped`)

### NPS Response
- `response_id` (string)
- `response_date` (string, `YYYY-MM-DD`)
- `score` (integer, 0–100)
- `survey_channel` (string enum: `email`, `in_app`, `csm_call`)
- `retracted` (boolean)

### Support Ticket
- `ticket_id` (string)
- `created_date` (string, `YYYY-MM-DD`)
- `status` (string enum: `open`, `closed`)
- `severity` (string enum: `P1`, `P2`, `P3`, `P4`)
- `product_area` (string)
- `first_response_sla_met` (boolean)
- `resolution_sla_met` (boolean)
- `is_spam` (boolean)
- `is_duplicate` (boolean)

## Business Rules & Filtering Logic

### Quarter Scoping
- "Current quarter" or "this quarter" in task text refers to the quarter of the most recent metric month returned by `/api/accounts/{id}/metrics`. Derive it from the `quarter` field (e.g., `2026-Q2`).
- When a task asks for pipeline or metrics "for this quarter", filter opportunities or metrics whose `quarter` matches the current quarter, or whose `close_date` / `month` falls within that quarter's date range.

### Retention Pipeline (High-Risk Accounts)
- Criteria typically include:
  - `crm_arr` or `billing_arr_current` > threshold (e.g., 5000)
  - Churn risk > threshold (e.g., 0.7) — when churn-risk scores are unavailable, proxy with:
    - `lifecycle_status == "renewal_risk"`
    - Low recent NPS (`nps_score` below ~40)
    - Declining `product_usage` over the last 3 months
    - High open-ticket volume with poor SLA compliance
- Segment filters: `Strategic` and `Enterprise` are the top two tiers; include both when the task asks for "strategic and enterprise accounts".

### Pipeline Summary
- `won_count`: Opportunities with `state == "closed"` and `stage == "Closed Won"`
- `won_revenue`: Sum of `amount` for won opportunities
- `lost_count`: Opportunities with `state == "closed"` and `stage == "Closed Lost"`
- `open_count`: Opportunities with `state == "open"`
- `open_pipeline`: Sum of `amount` for open opportunities
- `win_rate_pct`: `won_count / (won_count + lost_count) * 100.0` — compute as a float with one decimal place
- `top_open_product_line`: The `product_line` with the highest total open `amount` among open opportunities; break ties alphabetically

### Support Health (Proxy)
- When "low support health" is requested but no composite health score endpoint exists, derive from:
  - `sla_compliance` in the latest month (lower = worse)
  - Ratio of `resolution_sla_met == false` tickets to total tickets
  - High `support_ticket_count` in recent metrics
  - Very low NPS scores

### ARR Source Selection
- Prefer `crm_arr` for CRM-facing reports (retention pipeline, expansion potential).
- Use `billing_arr_current` when the task explicitly asks for billing/receivables context.
- If only one is needed, document which was used in reasoning; default to `crm_arr` for retention analytics.

### Link Status (Overdue Follow-ups)
- `linked`: An overdue receivable record has a matching `account_id` in the CRM accounts list.
- `unlinked`: An overdue receivable record has no matching `account_id` in the CRM accounts list.
- When receivables data is unavailable from a dedicated endpoint, use `billing_arr_current` discrepancies or negative indicators from billing snapshots as proxies, and clearly note the derivation.

### Risk Level & Ranking
- `critical`: Account meets multiple risk criteria (e.g., overdue receivables + renewal risk status + low support health)
- `high`: Meets two major criteria
- `medium`: Meets one criterion
- `low`: Meets none
- Rank the action board by severity (critical first), then by `current_arr` descending, then by `overdue_balance` descending.

### Primary Actions
- `collections_followup`: Account has overdue receivables
- `technical_recovery`: Low support health / high unresolved ticket volume
- `renewal_save`: `lifecycle_status == "renewal_risk"` or churn risk high
- `executive_qbr`: Strategic account with expansion pipeline but no immediate risk
- `nurture_monitor`: Active account with no immediate risk

### Reason Codes
- `overdue_receivable`
- `high_churn_risk`
- `low_support_health`
- `renewal_at_risk`
- `declining_usage`

### Follow-up Calendar
- Compute due dates relative to the current date (or the latest metric month if the current date is not available):
  - `collections_followup`: Current date + 1 business day
  - `technical_recovery`: Current date + 2 business days
  - `renewal_save`: Current date + 3 business days
  - `executive_qbr`: Current date + 5 business days
  - `nurture_monitor`: Current date + 7 business days
- Format as `YYYY-MM-DD`.

## Output Schemas

There are two primary output shapes used across tasks. Inspect the task's answer template to determine which is required.

### Shape A — Pipeline & Financial Summary
```json
{
  "financial_summary": {
    "overdue_client_count": 0,
    "overdue_total": 0.00,
    "linked_followup_count": 0,
    "unlinked_followup_count": 0
  },
  "pipeline_summary": {
    "won_count": 0,
    "won_revenue": 0.00,
    "lost_count": 0,
    "open_count": 0,
    "open_pipeline": 0.00,
    "win_rate_pct": 0.0,
    "top_open_product_line": ""
  },
  "overdue_followups": [
    {
      "customer_name": "",
      "link_status": "linked",
      "account_id": null,
      "overdue_balance": 0.00,
      "due_date": "YYYY-MM-DD",
      "primary_action": "collections_followup"
    }
  ],
  "ops_context": {
    "hr_headcount": 0,
    "unpaid_claims_total": 0.00,
    "event_orders": 0,
    "event_revenue": 0.00
  },
  "policy_codes": {
    "receivable_trigger_code": "RCP-4|RCP-7|RCP-9",
    "crm_match_code": "CM-2|CM-5|CM-8",
    "pipeline_window_code": "PW-3|PW-6|PW-9",
    "followup_scope_code": "FS-1|FS-4|FS-8"
  }
}
```

### Shape B — Executive Action Board
```json
{
  "action_board": [
    {
      "rank": 1,
      "account_id": "acct_example",
      "risk_level": "critical",
      "primary_action": "collections_followup",
      "current_arr": 0.0,
      "expansion_pipeline": 0.0,
      "overdue_balance": 0.0,
      "next_touch_due_date": "YYYY-MM-DD",
      "reason_codes": ["overdue_receivable"]
    }
  ],
  "segment_summary": {
    "strategic_accounts": 0,
    "enterprise_accounts": 0,
    "arr_at_risk": 0.0,
    "open_expansion_pipeline": 0.0,
    "net_revenue_exposure": 0.0
  },
  "followup_calendar": {
    "collections_followup": "YYYY-MM-DD",
    "technical_recovery": "YYYY-MM-DD",
    "renewal_save": "YYYY-MM-DD",
    "executive_qbr": "YYYY-MM-DD",
    "nurture_monitor": "YYYY-MM-DD"
  },
  "policy_codes": {
    "risk_model_code": "RS-2|RS-6|RS-9",
    "arr_source_code": "REV-1|REV-4|REV-8",
    "support_hygiene_code": "SUP-3|SUP-8|SUP-9",
    "action_priority_code": "ACT-1|ACT-5|ACT-7",
    "board_sort_code": "BORD-1|BORD-4|BORD-8",
    "exposure_formula_code": "EXP-2|EXP-6|EXP-9",
    "calendar_policy_code": "CAL-3|CAL-5|CAL-7"
  }
}
```

### Policy Codes
- `policy_codes` is a required top-level object in both shapes.
- Populate it with the pipe-delimited code strings shown in the answer template (e.g., `"RCP-4|RCP-7|RCP-9"`). Do not modify the codes unless the task explicitly asks for a different policy configuration.
- These codes are metadata that indicate which business-rule variants were applied.

## Workflow Rules

1. **Start with health check.** Call `/api/health` to confirm the API is up and note dataset sizes.
2. **Fetch all accounts and opportunities.** These are the two global list endpoints. Fetch them first because most downstream logic joins against them.
3. **Fetch account-scoped data on demand.** For accounts that pass initial filters, call `/api/accounts/{id}/metrics`, `/api/accounts/{id}/nps`, and `/api/accounts/{id}/tickets` as needed. Do not fetch every account's detail data if the task only asks for a small subset.
4. **Filter client-side.** The API does not support query-parameter filtering. Apply all filters (segment, ARR threshold, lifecycle status, quarter, etc.) in your code after fetching the data.
5. **Derive missing fields explicitly.** If a required field (e.g., `overdue_balance`, `churn_risk`) has no direct endpoint, derive it from available data and document the derivation in the output reasoning.
6. **Match accounts carefully.** Join on `account_id` (not `display_name` or `legal_name`) because aliases vary. Use `account_legal_name` from opportunities or `display_name` from accounts only for human-readable labels.
7. **Use `crm_arr` as the canonical ARR** unless the task specifies billing ARR.
8. **Format monetary values** to two decimal places (`0.00`) and percentages to one decimal place (`0.0`).
9. **Sort consistently.** For action boards, sort by risk level severity, then `current_arr` desc, then `overdue_balance` desc. For follow-up lists, sort by `due_date` asc, then `overdue_balance` desc.
10. **Respect nulls.** If an account has no opportunities, its `expansion_pipeline` is `0.0`. If no receivables data exists, `overdue_balance` is `0.0` and `overdue_client_count` is `0`.

## Pitfalls

- **Do not assume query parameters work.** `/api/accounts?segment=Enterprise` still returns all accounts; filter in code.
- **Do not hard-code localhost.** Always read the base URL from `environment_access.md` / `GDPEVO_ENV_BASE_URL`.
- **Do not confuse `crm_arr` with `billing_arr_current`.** They can differ significantly (e.g., Globex North: 1,057,320 vs 1,188,000).
- **Do not ignore `lifecycle_status`.** It is the strongest available proxy for churn risk when no dedicated churn-risk endpoint exists.
- **Do not include retracted NPS scores** in health calculations unless the task explicitly asks for them. Filter `retracted == false`.
- **Do not include spam or duplicate tickets** in support-health calculations unless instructed otherwise.
- **Watch for missing endpoints.** If a task requires data from `ar_aging`, `hr_summary`, or `event_performance` and no `/api/*` endpoint returns it, derive from the closest available proxy or return `0` values with clear documentation.
- **Policy codes must match the template exactly.** Do not invent new codes or omit the object.
- **Date formats must be `YYYY-MM-DD`.** No timezone offsets, no timestamps.
