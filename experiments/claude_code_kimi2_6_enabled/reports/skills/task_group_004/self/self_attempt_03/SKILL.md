# ApexCloud Retention Operations Board Skill

## Overview

Build a high-touch retention action board by reconciling account profiles, billing snapshots, support health, NPS, receivables, product usage, and expansion opportunities from the ApexCloud Retention Operations API.

## API Base URL

Read `environment_access.md` in the solver directory and use `GDPEVO_ENV_BASE_URL` as the operative API base URL. Do not hard-code `localhost` or `127.0.0.1`. The task text may mention a local URL; always override with the environment variable.

## Known Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Service health and row counts of backing data files |
| `/api/accounts` | GET | List all account profiles (44 accounts) |
| `/api/accounts/{account_id}` | GET | Single account profile |
| `/api/opportunities` | GET | List all opportunities (114 records) |
| `/api/accounts/{account_id}/metrics` | GET | Monthly account metrics (12 months per account) |
| `/api/accounts/{account_id}/nps` | GET | NPS responses for an account (may also appear as `/api/accounts/{account_id}/nps_responses`) |
| `/api/accounts/{account_id}/billing_snapshots` | GET | Monthly billing data per account |
| `/api/accounts/{account_id}/ar_aging` | GET | A/R aging entries per account |
| `/api/accounts/{account_id}/support_tickets` | GET | Support tickets per account |

> **Endpoint Discovery Note:** If a sub-endpoint returns `not_found`, also try the top-level form (e.g., `/api/billing_snapshots`, `/api/ar_aging`, `/api/nps_responses`, `/api/support_tickets`). The API may expose data both ways.

## Account Profile Fields

Key fields from `/api/accounts` and `/api/accounts/{id}`:

- `account_id` — stable identifier
- `display_name` / `legal_name` / `account_aliases`
- `segment` — `Strategic`, `Enterprise`, `Mid-Market`, `SMB`
- `region` — `North America`, `EMEA`, `APAC`, `LATAM`
- `product_plan` — e.g., `Enterprise`, `Scale`, `Strategic`, `Growth`
- `lifecycle_status` — `active`, `renewal_risk`, `implementation`, etc.
- `renewal_date` — ISO date string
- `contract_tenure_months` — integer
- `csm_owner` — assigned CSM name
- `billing_arr_current` — current ARR from billing system
- `crm_arr` — ARR recorded in CRM

## Monthly Metrics Fields

From `/api/accounts/{id}/metrics`:

- `month` — `YYYY-MM`
- `quarter` — `YYYY-QN`
- `active_seats` — integer
- `product_usage` — percentage (0–100)
- `recognized_revenue` — currency
- `sla_compliance` — percentage
- `support_ticket_count` — integer
- `nps_score` — integer 0–10, or `null`
- `survey_status` — `completed` or `missing`

## Opportunity Fields

From `/api/opportunities`:

- `opportunity_id`
- `account_id`
- `amount` — currency
- `close_date` — ISO date
- `created_date` — ISO date
- `stage` — e.g., `Discovery`, `Proposal`, `Prospecting`, `Closed Won`, `Closed Lost`
- `state` — `open` or `closed`
- `product_line`

## NPS Response Fields

From `/api/accounts/{id}/nps`:

- `response_id`
- `score` — integer 0–10
- `response_date` — ISO date
- `survey_channel` — e.g., `email`, `csm_call`, `in_app`
- `retracted` — boolean; **exclude retracted responses from NPS calculations**

## Workflow Steps

1. **Read task parameters**
   - Board as-of date (e.g., `2026-06-30`)
   - Activity period start and end dates
   - Month identifiers (e.g., `2026-04`, `2026-05`, `2026-06`)
   - List of `account_id`s to include
   - Follow-up due dates per action type

2. **Fetch account profiles**
   - `GET /api/accounts` and filter to the requested `account_id`s
   - Or call `GET /api/accounts/{id}` for each

3. **Fetch opportunities**
   - `GET /api/opportunities`
   - Filter to `state == "open"` and `close_date` within the activity period
   - Sum `amount` per account as `expansion_pipeline`

4. **Fetch monthly metrics**
   - `GET /api/accounts/{id}/metrics`
   - Filter to months within the activity period
   - Aggregate: average `product_usage`, average `sla_compliance`, total `support_ticket_count`, latest `active_seats`, latest NPS (non-retracted)

5. **Fetch NPS responses**
   - `GET /api/accounts/{id}/nps`
   - Filter out `retracted: true`
   - Compute latest NPS within or before the period if needed

6. **Fetch billing & A/R data**
   - `GET /api/accounts/{id}/billing_snapshots` or `/api/billing_snapshots`
   - `GET /api/accounts/{id}/ar_aging` or `/api/ar_aging`
   - For A/R aging, sum amounts with `days_overdue > 0` as `overdue_balance` as of the board date
   - If the billing_snapshots endpoint is unavailable, fall back to `billing_arr_current` from the account profile for `current_arr`.

7. **Fetch support tickets (if available)**
   - `GET /api/accounts/{id}/support_tickets` or `/api/support_tickets`
   - Count tickets created within the activity period, or with status `open` as of board date

8. **Compute per-account board entries**
   - Determine `current_arr`: use `billing_arr_current` from the account profile as the primary source. If the task explicitly asks to reconcile with billing snapshots, fetch the latest billing snapshot for the period and use its `arr` field. If the two sources differ materially, prefer the billing snapshot ARR when the task uses the word "reconcile".
   - Determine `risk_level` based on heuristics (see Risk Model section)
   - Determine `primary_action` based on risk level and dominant reason (see Action Assignment section)
   - Compute `reason_codes` array
   - Set `next_touch_due_date` from the task-provided follow-up calendar
   - Compute `overdue_balance`: sum `amount` from all A/R aging entries for the account where `days_overdue > 0` as of the board date. If A/R aging is unavailable, set to `0.00`.
   - Compute `expansion_pipeline`: sum `amount` of all opportunities where `account_id` matches, `state == "open"`, and `close_date` falls within the activity period (inclusive).

9. **Sort the action board**
   - Use the **standard retention board order**: sort primarily by `risk_level` severity (`critical` > `high` > `medium` > `low`), secondarily by `current_arr` descending, then by `account_id` ascending for stability
   - Assign `rank` sequentially starting at 1

10. **Compute segment summary**
    - `strategic_accounts`: count of accounts with `segment == "Strategic"`
    - `enterprise_accounts`: count of accounts with `segment == "Enterprise"`
    - `arr_at_risk`: sum of `current_arr` across all board accounts
    - `open_expansion_pipeline`: sum of `expansion_pipeline`
    - `net_revenue_exposure`: typically `arr_at_risk + open_expansion_pipeline` (confirm against task-specific formula if implied)

11. **Populate follow-up calendar**
    - Use the exact dates provided in the task prompt for each action key

12. **Select policy codes**
    - The answer template shows pipe-separated options like `RS-2|RS-6|RS-9`
    - Select **one** code from each option set based on the risk model, ARR source, support hygiene, action priority, board sort, exposure formula, and calendar policy used
    - Document the rationale for the selected code in reasoning

13. **Emit JSON only**
    - Output must match `answer_template.json` structure exactly
    - No markdown, no extra text

## Risk Model Rules

Risk levels are controlled enums. Typical levels: `critical`, `high`, `medium`, `low`.

**Critical indicators (any one triggers critical):**
- `overdue_balance > 0` and significant relative to ARR
- `lifecycle_status == "renewal_risk"` and renewal date within 90 days of board date
- NPS ≤ 3 (detractor) and declining usage or high support volume
- Multiple severe factors simultaneously

**High indicators:**
- `overdue_balance > 0` but smaller relative to ARR
- NPS 4–6 (passive) combined with elevated support tickets or usage decline
- Renewal within 180 days with risk signals

**Medium indicators:**
- Moderate support volume without other severe signals
- Slight usage decline or missing NPS surveys
- Renewal within 365 days with minor concerns

**Low indicators:**
- Healthy NPS (≥ 7), stable usage, no overdue balance, low support volume
- Recent positive survey completions

> **Exact thresholds are task-specific.** Use deterministic heuristics: start with the most severe condition that applies and do not downgrade unless the task explicitly overrides.

## Action Assignment Rules

Controlled enum for `primary_action`:

| Action | Trigger Condition |
|--------|-------------------|
| `collections_followup` | `overdue_balance > 0` is the dominant reason |
| `technical_recovery` | Low usage, high support volume, or SLA compliance issues dominate |
| `renewal_save` | Renewal date near or `lifecycle_status == "renewal_risk"` dominates |
| `executive_qbr` | Strategic/Enterprise account with moderate risk; use when no more specific action applies to high-value accounts |
| `nurture_monitor` | Low risk, healthy metrics; monitor and maintain |

Priority: `collections_followup` > `technical_recovery` > `renewal_save` > `executive_qbr` > `nurture_monitor`. Assign the highest-priority action whose trigger condition is met.

## Reason Codes

Common controlled reason codes to include in the `reason_codes` array:

- `overdue_receivable` — when `overdue_balance > 0`
- `low_nps` — when latest valid NPS is in detractor or passive range
- `high_support_volume` — when support ticket count is elevated for the segment
- `declining_usage` — when `product_usage` trend is negative over the period
- `renewal_at_risk` — when renewal date is near or status is `renewal_risk`
- `missing_survey` — when `survey_status` is `missing` for the latest month
- `sla_breach` — when `sla_compliance` is below threshold
- `low_adoption` — when `active_seats` or `product_usage` is low relative to plan

Include all reason codes that apply to the account; do not cap the array length.

## Board Sort Code (Standard Retention Board Order)

1. Primary: `risk_level` in severity order (`critical`, `high`, `medium`, `low`)
2. Secondary: `current_arr` descending (highest ARR first within same risk level)
3. Tertiary: `account_id` ascending (for deterministic tie-breaking)

## Data Precision Rules

- Currency values (`current_arr`, `expansion_pipeline`, `overdue_balance`, `arr_at_risk`, etc.): exactly 2 decimal places
- Percentages: 1 decimal place if any are included in output
- Counts (`strategic_accounts`, `enterprise_accounts`, `rank`, ticket counts, seat counts): integers
- Dates: `YYYY-MM-DD` format
- Enum values: exact controlled strings (lowercase with underscores)

## Pitfalls & Edge Cases

- **Null NPS scores:** Treat `null` / missing NPS as a risk signal (include `missing_survey` reason). Do not assume 0.
- **Retracted NPS:** Always filter out responses where `retracted: true` before computing latest/average NPS.
- **ARR source mismatch:** `billing_arr_current` and `crm_arr` can differ. Use `billing_arr_current` unless the task explicitly asks to reconcile with billing snapshots.
- **Opportunity state vs stage:** Only `state == "open"` opportunities count toward `expansion_pipeline`, regardless of `stage`.
- **Close date filtering:** Opportunities must have `close_date` within the activity period (inclusive) to be included.
- **A/R aging as-of date:** Use the exact board date provided in the prompt, not the period end date.
- **Metrics month alignment:** Monthly metrics use `YYYY-MM` identifiers. Ensure the correct months are selected for the period.
- **Overdue balance precision:** Sum all `amount` values from A/R aging where `days_overdue > 0` as of the board date.
- **Empty boards:** If no accounts meet inclusion criteria, emit an empty `action_board` array with zeros in `segment_summary` and the provided follow-up dates.
- **Endpoint availability:** Some endpoints (`billing_snapshots`, `ar_aging`, `support_tickets`) may intermittently return `not_found`. Retry the account-scoped form (`/api/accounts/{id}/...`) if the top-level form fails, and vice versa.

## Policy Code Selection Guide

The answer template requires selecting one code from each pipe-separated option set. Typical mapping:

- `risk_model_code`: Map to the primary risk heuristic used (e.g., multi-factor with ARR-weighting, NPS-first, etc.)
- `arr_source_code`: Map to whether `billing_arr_current`, `crm_arr`, or reconciled billing snapshot ARR was used
- `support_hygiene_code`: Map to whether support health was evaluated by ticket count, SLA compliance, or open ticket status
- `action_priority_code`: Map to the action priority ordering applied
- `board_sort_code`: Map to the sort keys used (risk + ARR + account_id)
- `exposure_formula_code`: Map to how `net_revenue_exposure` was computed
- `calendar_policy_code`: Map to whether follow-up dates were taken directly from the prompt or adjusted

> **Selection rule:** Choose the code that corresponds to the actual method used. If uncertain, prefer the most conservative/default option in the set.

## Example Output Structure

```json
{
  "action_board": [
    {
      "rank": 1,
      "account_id": "acct_example",
      "risk_level": "critical",
      "primary_action": "collections_followup",
      "current_arr": 1150000.00,
      "expansion_pipeline": 0.00,
      "overdue_balance": 125000.00,
      "next_touch_due_date": "2026-07-15",
      "reason_codes": ["overdue_receivable", "renewal_at_risk"]
    }
  ],
  "segment_summary": {
    "strategic_accounts": 2,
    "enterprise_accounts": 3,
    "arr_at_risk": 2500000.00,
    "open_expansion_pipeline": 500000.00,
    "net_revenue_exposure": 3000000.00
  },
  "followup_calendar": {
    "collections_followup": "2026-07-15",
    "technical_recovery": "2026-07-18",
    "renewal_save": "2026-07-22",
    "executive_qbr": "2026-07-29",
    "nurture_monitor": "2026-08-05"
  },
  "policy_codes": {
    "risk_model_code": "RS-6",
    "arr_source_code": "REV-1",
    "support_hygiene_code": "SUP-3",
    "action_priority_code": "ACT-1",
    "board_sort_code": "BORD-1",
    "exposure_formula_code": "EXP-2",
    "calendar_policy_code": "CAL-3"
  }
}
```
