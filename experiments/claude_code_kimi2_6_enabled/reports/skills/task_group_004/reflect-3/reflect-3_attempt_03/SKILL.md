# CRM Retention Analytics Skill

## Overview

Generate a retention action-board JSON for a filtered set of CRM accounts by querying a remote API, computing risk levels, expansion pipeline, and follow-up actions from account, opportunity, ticket, NPS, and metric data.

## API Base URL

Read `environment_access.md` in the solver attempt directory to get `GDPEVO_ENV_BASE_URL`. Use that value as the API base URL. Do **not** hard-code `localhost` as the operative base URL.

## Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/accounts` | GET | List all accounts (returns `accounts` array and `count`) |
| `/api/accounts/{account_id}` | GET | Single account details |
| `/api/accounts/{account_id}/tickets` | GET | Support tickets for the account |
| `/api/accounts/{account_id}/nps` | GET | NPS survey responses for the account |
| `/api/accounts/{account_id}/metrics` | GET | Monthly metrics for the account |
| `/api/opportunities` | GET | All opportunities (returns `opportunities` array and `count`). **Note:** Query parameters such as `account_id` or `state` do **not** filter the response; filter client-side. |

> **Note:** The task prompt may reference `/api/v1/accounts/retention`. That endpoint does **not** exist in this environment. Use the endpoints listed above.

## Account Object Fields

- `account_id` – stable identifier (e.g. `acct_globex_north`)
- `display_name` – human-readable name
- `legal_name` – full legal entity name
- `account_aliases` – array of known aliases
- `segment` – `SMB` | `Mid-Market` | `Enterprise` | `Strategic`
- `region` – e.g. `North America`, `EMEA`, `APAC`, `LATAM`
- `lifecycle_status` – `active` | `implementation` | `renewal_risk` | `paused`
- `renewal_date` – ISO date string (`YYYY-MM-DD`)
- `contract_tenure_months` – integer
- `product_plan` – e.g. `Launch`, `Growth`, `Scale`, `Enterprise`, `Strategic`
- `csm_owner` – assigned CSM name
- `billing_arr_current` – float
- `crm_arr` – float (usually the authoritative `current_arr` value for the board)

## Opportunity Object Fields

- `opportunity_id`
- `account_id`
- `amount` – float
- `state` – `open` | `closed` | `cancelled`
- `stage` – e.g. `Discovery`, `Proposal`
- `close_date`
- `product_line`
- `region`

## Ticket Object Fields

- `ticket_id`
- `account_id`
- `status` – `open` | `closed` | `cancelled`
- `severity` – `P1` … `P4`
- `product_area`
- `first_response_sla_met` – boolean
- `resolution_sla_met` – boolean
- `is_duplicate` – boolean
- `is_spam` – boolean
- `created_date`

## NPS Response Fields

- `response_id`
- `account_id`
- `response_date`
- `score` – integer (0-100)

## Monthly Metric Fields

- `month` – e.g. `2026-01`
- `quarter` – e.g. `2026-Q1`
- `account_id`
- `active_seats` – integer
- `nps_score` – integer or `null`
- `product_usage` – float (percentage)
- `recognized_revenue` – float
- `sla_compliance` – float (percentage)
- `support_ticket_count` – integer
- `survey_status` – `completed` | `missing`

## Workflow

1. **Read the task prompt** to extract the filter criteria (region, segment, lifecycle status, renewal-date window, tenure threshold, etc.).
2. **Fetch** `/api/accounts` and apply the filter.
3. **Fetch** `/api/opportunities` and build an in-memory map of `account_id → open opportunities`.
4. For **each** target account:
   - Compute `expansion_pipeline` = sum of `amount` for opportunities where `state === 'open'`.
   - (Optional but recommended) Fetch `/api/accounts/{id}/tickets`, `/api/accounts/{id}/nps`, and `/api/accounts/{id}/metrics` to enrich risk analysis.
5. **Determine risk level** using this priority:
   - `critical` – `lifecycle_status === 'renewal_risk'`
   - `high` – `lifecycle_status === 'paused'`
   - `medium` – `lifecycle_status === 'active'` with at least one risk indicator (low NPS < 40, high open-ticket count ≥ 8, low usage < 60, SLA compliance < 90, or renewal within 60 days)
   - `low` – otherwise
6. **Determine primary action**:
   - `collections_followup` – `lifecycle_status === 'paused'`
   - `renewal_save` – `lifecycle_status === 'renewal_risk'`
   - `technical_recovery` – active account with significant support backlog (≥ 8 open tickets or SLA compliance < 90)
   - `executive_qbr` – active account with large expansion pipeline (> 0) and no critical support issues
   - `nurture_monitor` – low-risk active accounts with no expansion pipeline
7. **Build `reason_codes`** based on the actual drivers:
   - `renewal_risk` – for `lifecycle_status === 'renewal_risk'`
   - `account_paused` – for `lifecycle_status === 'paused'`
   - `support_backlog` – for accounts with ≥ 8 open tickets
   - `low_nps` – for latest NPS < 45
   - `low_usage` – for latest `product_usage` < 60
   - `expansion_opportunity` – for active accounts with open expansion pipeline
   - `renewal_approaching` – default for active accounts
8. **Sort the action board**:
   - Primary: risk level ascending (`critical` → `high` → `medium` → `low`)
   - Secondary: `current_arr` descending
   - Assign sequential `rank` starting at 1.
9. **Compute segment summary**:
   - `strategic_accounts` – count of target accounts where `segment === 'Strategic'`
   - `enterprise_accounts` – count where `segment === 'Enterprise'`
   - `arr_at_risk` – sum of `current_arr` for all board rows
   - `open_expansion_pipeline` – sum of `expansion_pipeline`
   - `net_revenue_exposure` – `arr_at_risk + open_expansion_pipeline`
10. **Compute follow-up calendar**:
    - For each action type present on the board, set the calendar date to the *earliest* `next_touch_due_date` of any board row with that `primary_action`.
    - For action types not present, set a default date (e.g., today + 14 days).
11. **Select policy codes**. The answer template shows option ranges separated by `|`:
    - `risk_model_code` – `RS-2` | `RS-6` | `RS-9`
    - `arr_source_code` – `REV-1` | `REV-4` | `REV-8`
    - `support_hygiene_code` – `SUP-3` | `SUP-8` | `SUP-9`
    - `action_priority_code` – `ACT-1` | `ACT-5` | `ACT-7`
    - `board_sort_code` – `BORD-1` | `BORD-4` | `BORD-8`
    - `exposure_formula_code` – `EXP-2` | `EXP-6` | `EXP-9`
    - `calendar_policy_code` – `CAL-3` | `CAL-5` | `CAL-7`
    - Choose **one** code from each pipe-separated list. Heuristic: if the board uses a simple 3-level risk model and CRM ARR, prefer the lowest-suffix option (`RS-2`, `REV-1`, `SUP-3`, `ACT-1`, `BORD-1`, `EXP-2`, `CAL-3`).

## Output Field Definitions

| Field | Type | Rule |
|-------|------|------|
| `rank` | integer | 1-based after sorting |
| `account_id` | string | Exact API `account_id` |
| `risk_level` | string | `critical` \| `high` \| `medium` \| `low` |
| `primary_action` | string | `collections_followup` \| `technical_recovery` \| `renewal_save` \| `executive_qbr` \| `nurture_monitor` |
| `current_arr` | float | Use `crm_arr` from account object (round to 2 decimals) |
| `expansion_pipeline` | float | Sum of open-opportunity amounts (round to 2 decimals) |
| `overdue_balance` | float | No invoices endpoint is available; default to `0.0` |
| `next_touch_due_date` | string `YYYY-MM-DD` | Based on risk: critical = +1 day, high = +3 days, medium = +7 days, low = +14 days from today |
| `reason_codes` | string[] | Non-empty array of driver codes |

## Pitfalls

- **Do not assume `/api/v1/accounts/retention` exists.** The prompt may reference it, but the actual usable endpoints are `/api/accounts`, `/api/opportunities`, and the account sub-endpoints (`/tickets`, `/nps`, `/metrics`).
- **Opportunity filtering is client-side.** The `/api/opportunities` endpoint returns all 114 opportunities regardless of query params. Always filter by `state === 'open'` and `account_id` in memory.
- **No billing/invoice endpoint.** `overdue_balance` cannot be computed from available data; default it to `0.0`.
- **Floating-point precision.** Round monetary sums to 2 decimal places before serializing to JSON to avoid `4987847.749999999` artifacts.
- **Date context.** Use the current date from the task context (e.g., `2026-07-02`) when computing `next_touch_due_date` and follow-up calendar dates.
- **Policy codes.** Each policy code field accepts exactly one value from its pipe-separated option list; do not concatenate multiple options with `|`.
