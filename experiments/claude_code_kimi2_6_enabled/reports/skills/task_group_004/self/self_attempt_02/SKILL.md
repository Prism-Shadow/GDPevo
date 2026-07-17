# CRM Retention Analytics Board — Solver Skill

## API Base URL
Use the current solver's `environment_access.md` / `GDPEVO_ENV_BASE_URL` as the API base URL. Do not hard-code `localhost` or `127.0.0.1` as the operative base URL.

## Available Endpoints
- `GET {base}/api/health` — service status and row counts
- `GET {base}/api/accounts` — all account profiles
- `GET {base}/api/accounts/{account_id}` — single account profile
- `GET {base}/api/accounts/{account_id}/metrics` — monthly metrics time series
- `GET {base}/api/opportunities` — all opportunities (open and closed)

## Endpoint Response Shapes

### Account Profile
```json
{
  "account_id": "string",
  "display_name": "string",
  "legal_name": "string",
  "account_aliases": ["string"],
  "segment": "Strategic|Enterprise|Mid-Market|SMB",
  "lifecycle_status": "active|implementation|renewal_risk|paused",
  "product_plan": "string",
  "region": "string",
  "billing_arr_current": 0.0,
  "crm_arr": 0.0,
  "contract_tenure_months": 0,
  "csm_owner": "string",
  "renewal_date": "YYYY-MM-DD"
}
```

### Monthly Metrics (per account, 12 months)
```json
{
  "account_id": "string",
  "month": "YYYY-MM",
  "quarter": "YYYY-QN",
  "active_seats": 0,
  "nps_score": null,
  "product_usage": 0.0,
  "recognized_revenue": 0.0,
  "sla_compliance": 0.0,
  "support_ticket_count": 0,
  "survey_status": "missing|completed"
}
```

### Opportunities
```json
{
  "account_id": "string",
  "account_legal_name": "string",
  "amount": 0.0,
  "close_date": "YYYY-MM-DD",
  "created_date": "YYYY-MM-DD",
  "opportunity_id": "string",
  "product_line": "string",
  "region": "string",
  "stage": "string",
  "state": "open|closed"
}
```

## Workflow

### Step 1: Parse Prompt Parameters
Extract from the task prompt:
- **Board as-of date** (e.g., `2026-03-31` or `2026-06-30`)
- **Activity period** (start date, end date)
- **Months to include** (e.g., `2026-01`, `2026-02`, `2026-03` for Q1; `2026-04`, `2026-05`, `2026-06` for Q2)
- **Account IDs** to include
- **A/R aging as-of date**
- **Follow-up due dates** for each action type

### Step 2: Fetch Account Profiles
Call `GET /api/accounts` once and filter to the requested account IDs client-side. The response is a single JSON object with an `accounts` array.

### Step 3: Fetch Monthly Metrics
For each account, call `GET /api/accounts/{account_id}/metrics`. Filter the returned `metrics` array to only the months specified in the prompt. Compute period averages for:
- `avg_nps_score` (ignore nulls)
- `avg_product_usage`
- `avg_sla_compliance`
- `avg_support_ticket_count`

### Step 4: Fetch and Filter Opportunities
Call `GET /api/opportunities` once. Filter client-side to:
- `account_id` in the requested list
- `state` = `"open"`
- `close_date` falls within the activity period
Sum `amount` per account to compute `expansion_pipeline`.

### Step 5: Compute current_arr
Use `billing_arr_current` from the account profile as the operative ARR figure. The prompt says "reconcile account profile data, billing snapshots"; `billing_arr_current` is the current billing snapshot.

### Step 6: Compute overdue_balance
The AR aging endpoint (`/api/ar_aging` or similar) is not exposed in the public API. If AR aging data is unavailable, set `overdue_balance = 0.0` for all accounts.

### Step 7: Calculate Risk Level
Use a deterministic tiered model. Start at `"low"` and elevate based on the following thresholds evaluated against the **period averages**:

| Factor | Threshold | Risk Elevation |
|--------|-----------|----------------|
| `lifecycle_status` = `"renewal_risk"` or `"paused"` | — | At least `"high"` |
| `renewal_date` within 90 days of board as-of date | — | Elevate one tier |
| `avg_nps_score` < 30 (and not null) | — | Elevate one tier |
| `avg_product_usage` < 60 | — | Elevate one tier |
| `avg_support_ticket_count` > 6 | — | Elevate one tier |
| `avg_sla_compliance` < 85 | — | Elevate one tier |

**Tier mapping:**
- No elevations → `"low"`
- 1 elevation → `"medium"`
- 2 elevations → `"high"`
- 3+ elevations, or `lifecycle_status` in ("renewal_risk", "paused") plus any other elevation → `"critical"`

### Step 8: Determine Primary Action
Apply the first matching rule in priority order:

1. `collections_followup` — if `overdue_balance > 0`
2. `renewal_save` — if `lifecycle_status` = `"renewal_risk"` or `renewal_date` is within 90 days of board date
3. `technical_recovery` — if `avg_product_usage` < 60 or `avg_support_ticket_count` > 6 or `avg_sla_compliance` < 85 or `avg_nps_score` < 30
4. `executive_qbr` — if `segment` in (`"Strategic"`, `"Enterprise"`) and risk level is `"low"` or `"medium"`
5. `nurture_monitor` — default for all remaining accounts

### Step 9: Determine Reason Codes
Return a list of all applicable reason codes. Use controlled strings exactly:

| Condition | Reason Code |
|-----------|-------------|
| `overdue_balance > 0` | `"overdue_receivable"` |
| `lifecycle_status` = `"renewal_risk"` | `"renewal_risk"` |
| `lifecycle_status` = `"paused"` | `"paused_account"` |
| `avg_product_usage` < 60 | `"low_usage"` |
| `avg_nps_score` < 30 (and not null) | `"low_nps"` |
| `avg_support_ticket_count` > 6 | `"high_support_volume"` |
| `avg_sla_compliance` < 85 | `"sla_breach"` |

### Step 10: Set next_touch_due_date
Map `primary_action` to the corresponding date from the prompt's follow-up due dates:
- `collections_followup` → `followup_calendar.collections_followup`
- `technical_recovery` → `followup_calendar.technical_recovery`
- `renewal_save` → `followup_calendar.renewal_save`
- `executive_qbr` → `followup_calendar.executive_qbr`
- `nurture_monitor` → `followup_calendar.nurture_monitor`

### Step 11: Sort Action Board (Standard Retention Board Order)
Sort accounts by:
1. `risk_level` descending (`critical` > `high` > `medium` > `low`)
2. `current_arr` descending
3. `account_id` ascending (for deterministic tie-breaking)

Assign `rank` starting at 1.

### Step 12: Compute Segment Summary
- `strategic_accounts`: count where `segment` = `"Strategic"`
- `enterprise_accounts`: count where `segment` = `"Enterprise"`
- `arr_at_risk`: sum of `current_arr` for accounts with `risk_level` in (`"high"`, `"critical"`)
- `open_expansion_pipeline`: sum of `expansion_pipeline` across all accounts
- `net_revenue_exposure`: `arr_at_risk - open_expansion_pipeline` (net exposure after expansion upside)

### Step 13: Build Followup Calendar
Use the exact dates provided in the prompt for each key:
- `collections_followup`
- `technical_recovery`
- `renewal_save`
- `executive_qbr`
- `nurture_monitor`

### Step 14: Set Policy Codes
Select one code from each pipe-separated group to document the methodology used. These must match the controlled values in the answer template.

| Field | Recommended Default | Meaning |
|-------|---------------------|---------|
| `risk_model_code` | `RS-6` | Composite threshold model (lifecycle + metrics) |
| `arr_source_code` | `REV-1` | Uses `billing_arr_current` |
| `support_hygiene_code` | `SUP-9` | Full hygiene (tickets + SLA + survey) |
| `action_priority_code` | `ACT-7` | Risk-first priority order |
| `board_sort_code` | `BORD-1` | Risk level descending, then ARR descending |
| `exposure_formula_code` | `EXP-2` | Net exposure = `arr_at_risk - pipeline` |
| `calendar_policy_code` | `CAL-3` | Prompt-driven due dates |

## Output Format Rules
- Return **JSON only** — no markdown, no commentary, no code fences.
- `currency` values: exactly 2 decimal places.
- `counts` (rank, strategic_accounts, enterprise_accounts): integers.
- `percentages`: 1 decimal place if any are included.
- Controlled enums:
  - `risk_level`: `"low"`, `"medium"`, `"high"`, `"critical"`
  - `primary_action`: `"collections_followup"`, `"technical_recovery"`, `"renewal_save"`, `"executive_qbr"`, `"nurture_monitor"`
  - `reason_codes`: `"overdue_receivable"`, `"renewal_risk"`, `"paused_account"`, `"low_usage"`, `"low_nps"`, `"high_support_volume"`, `"sla_breach"`

## Pitfalls
- **Do not hard-code localhost**; always read `environment_access.md` for the base URL.
- `/api/opportunities` does not support query parameters; filter client-side.
- `nps_score` can be `null` in metrics; always ignore nulls when computing averages.
- The AR aging endpoint is not exposed in the public API; set `overdue_balance = 0.0` if unavailable.
- Use `billing_arr_current` for `current_arr`, not `crm_arr`.
- The `followup_calendar` object keys are fixed and must all be present even if no account maps to a given action.
- The `policy_codes` must contain exactly one value per field, chosen from the pipe-separated options in the answer template.
- The `action_board` must include **all** requested accounts, even if their pipeline or at-risk amount is zero.
