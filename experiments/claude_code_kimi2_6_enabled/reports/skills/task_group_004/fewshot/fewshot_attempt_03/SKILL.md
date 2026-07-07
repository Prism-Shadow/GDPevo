# CRM Retention Analytics — Action Board Generation

## Purpose
Generate a prioritized customer-retention action board, segment summary, follow-up calendar, and policy-code manifest by querying a CRM analytics API and applying the business rules documented below.

## Environment
- Read `environment_access.md` in the solver attempt directory to obtain `GDPEVO_ENV_BASE_URL`.  
- Use **that value** as the API base URL for every request.  
- Do **not** hard-code `localhost` or any other fixed host.

## Required API Endpoints
All endpoints are `GET` and return JSON.  Append them to the base URL obtained above.

| Endpoint | What it provides |
|----------|-----------------|
| `/v1/accounts` | Account master data: `account_id`, `name`, `current_arr`, `tier`, `status`, `created_at`, etc. |
| `/v1/health-score` | Per-account health scores: `account_id`, `health_score`, `sla_status`, `usage_trend`, etc. |
| `/v1/renewals` | Renewal opportunities: `account_id`, `renewal_date`, `renewal_amount`, `status`, etc. |
| `/v1/invoices` | Invoice / billing data: `account_id`, `amount`, `due_date`, `paid_date`, `status`, etc. |
| `/v1/nps` | NPS survey results: `account_id`, `score`, `survey_date`, etc. |
| `/v1/expansion` | Expansion pipeline: `account_id`, `pipeline_amount`, `stage`, `expected_close`, etc. |
| `/v1/interactions` | Touch history: `account_id`, `interaction_date`, `type`, `notes`, etc. |

Fetch **all** endpoints and join on `account_id`.  Cache the payloads in memory; do not write intermediate files outside the solver directory.

## Output Schema
Produce a single JSON object with exactly these top-level keys:

```json
{
  "action_board": [ … ],
  "segment_summary": { … },
  "followup_calendar": { … },
  "policy_codes": { … }
}
```

### 1. `action_board` — array of account objects, sorted **risk desc → current_arr desc**
Each element:

| Field | Type | Rule |
|-------|------|------|
| `rank` | integer | 1-based position in the sorted board |
| `account_id` | string | From `/v1/accounts` |
| `risk_level` | string | One of `critical`, `high`, `medium`, `low` (see Risk Model below) |
| `primary_action` | string | One of `collections_followup`, `technical_recovery`, `renewal_save`, `executive_escalation`, `nurture_monitor`, `no_action` (see Action Priority below) |
| `current_arr` | number | From `/v1/accounts`; round to **two decimals** |
| `expansion_pipeline` | number | Sum of open pipeline amounts for the account from `/v1/expansion`; default `0.0` |
| `overdue_balance` | number | Sum of invoice amounts where `status` is overdue / unpaid past `due_date` from `/v1/invoices`; default `0.0`; round to **two decimals** |
| `next_touch_due_date` | string\|null | Calculated touch date (see Calendar Policy below); `null` when `primary_action` is `no_action` |
| `reason_codes` | string[] | Ordered list of applicable reason codes (see Reason Codes below); deduplicate, preserve logical order |

### 2. `segment_summary`

| Field | Rule |
|-------|------|
| `strategic_accounts` | Count of board accounts whose `current_arr >= 1_000_000` |
| `enterprise_accounts` | Count of board accounts whose `current_arr < 1_000_000` |
| `arr_at_risk` | Sum of `current_arr` for **all** accounts on the action board; round to two decimals |
| `open_expansion_pipeline` | Sum of `expansion_pipeline` for **all** accounts on the action board; round to two decimals |
| `net_revenue_exposure` | `arr_at_risk - open_expansion_pipeline`; round to two decimals (can be negative) |

### 3. `followup_calendar`

| Key | Rule |
|-----|------|
| `collections_followup` | Earliest `next_touch_due_date` among accounts whose `primary_action` is `collections_followup`; if none, use the earliest interaction date + standard offset (see Calendar Policy) |
| `technical_recovery` | Earliest `next_touch_due_date` among accounts whose `primary_action` is `technical_recovery` |
| `renewal_save` | Earliest `next_touch_due_date` among accounts whose `primary_action` is `renewal_save` |
| `executive_qbr` | Fixed offset from the board generation date (see Calendar Policy) |
| `nurture_monitor` | Fixed offset from the board generation date (see Calendar Policy) |

All dates are ISO-8601 (`YYYY-MM-DD`).

### 4. `policy_codes`

Seven string fields that identify which variant of each business rule was active.  The exact code depends on data characteristics (e.g., board size, presence of overdue invoices, NPS distribution, etc.).  Valid values per field:

| Field | Valid codes |
|-------|-------------|
| `risk_model_code` | `RS-2`, `RS-6`, `RS-9` |
| `arr_source_code` | `REV-1`, `REV-4`, `REV-8` |
| `support_hygiene_code` | `SUP-3`, `SUP-8`, `SUP-9` |
| `action_priority_code` | `ACT-1`, `ACT-5`, `ACT-7` |
| `board_sort_code` | `BORD-1`, `BORD-4`, `BORD-8` |
| `exposure_formula_code` | `EXP-2`, `EXP-6`, `EXP-9` |
| `calendar_policy_code` | `CAL-3`, `CAL-5`, `CAL-7` |

Select the code by matching the data pattern to the conventions observed in training examples (e.g., `RS-6` when the risk model uses a 4-tier critical/high/medium/low scale with composite health + billing + renewal signals).

---

## Business Rules (Deterministic)

### A. Risk Model
Evaluate each account and assign **exactly one** risk level:

1. **Critical** — any of the following:
   - `overdue_balance > 0` AND `health_score` below threshold (e.g., < 60)
   - `health_score` extremely low (e.g., < 40) regardless of billing
   - Renewal within window AND severe health degradation
2. **High** — any of the following:
   - `overdue_balance > 0` with moderate health issues
   - `health_score` low (e.g., 40–59) without overdue
   - Multiple negative signals (NPS drop + SLA degradation + usage decline)
   - Large expansion pipeline at risk due to health issues
3. **Medium** — any of the following:
   - Renewal window approaching with mild health concerns
   - Single negative signal (SLA degradation or usage decline) on a healthy account
   - Moderate health score (e.g., 60–74) with no acute billing issues
4. **Low** — remaining accounts that still have at least one minor signal (e.g., slight NPS drop, small SLA miss, or expansion offset) but are otherwise stable.

Accounts with **no negative signals** are excluded from the action board entirely.

### B. Reason Codes
Populate `reason_codes` in this **priority order** (omit any that do not apply):

| Code | Trigger Condition |
|------|-------------------|
| `overdue_receivable` | `overdue_balance > 0` |
| `renewal_window` | Renewal date within the standard horizon (e.g., ≤ 90 days) AND not yet closed-won |
| `nps_drop` | Most recent NPS score is below a threshold (e.g., < 30) OR dropped significantly vs. prior survey |
| `sla_degradation` | `sla_status` is not "green" / "met" OR health-score SLA component is flagged |
| `usage_decline` | `usage_trend` is negative or "declining" |
| `expansion_offset` | `expansion_pipeline > 0` AND account has any other risk signal (used to show pipeline at risk) |

### C. Action Priority (Primary Action)
Map the account’s dominant signal to a single `primary_action`:

| Primary Action | Precedence Rule |
|----------------|-----------------|
| `collections_followup` | `overdue_balance > 0` — highest precedence |
| `technical_recovery` | `health_score` is low/critical OR `sla_degradation` + `usage_decline` present |
| `renewal_save` | `renewal_window` reason code present AND no higher-precedence action |
| `executive_escalation` | Very large ARR (e.g., strategic) + critical risk + no clear owner; use sparingly |
| `nurture_monitor` | Low risk with only minor signals; still on board because of some flag |
| `no_action` | Account has minimal signals and is effectively stable; `next_touch_due_date` becomes `null` |

### D. Calendar Policy (Next-Touch Dates)
For each account, compute `next_touch_due_date` as:

- Start from the **most recent interaction date** for that account in `/v1/interactions`.
- Add an offset based on `primary_action` and `risk_level`:
  - `collections_followup` → +3 business days (or shortest offset)
  - `technical_recovery` → +7 calendar days
  - `renewal_save` → +14 calendar days
  - `executive_escalation` → +5 calendar days
  - `nurture_monitor` → +21 calendar days
- If no interaction exists, use the **current date** (today) as the baseline.
- For `no_action` accounts, set `null`.

For the global `followup_calendar`:
- `executive_qbr` → today + 21 calendar days
- `nurture_monitor` → today + 28 calendar days

### E. Board Sort
1. Filter out accounts with **no negative signals** (they do not appear on the board).  
2. Sort remaining accounts by:
   1. `risk_level` descending (`critical` > `high` > `medium` > `low`)
   2. `current_arr` descending (largest first)
3. Assign `rank` sequentially starting at `1`.

### F. ARR & Pipeline Rounding
- All monetary fields (`current_arr`, `expansion_pipeline`, `overdue_balance`, `arr_at_risk`, `open_expansion_pipeline`, `net_revenue_exposure`) are rounded to **exactly two decimal places** in the JSON output.  Use standard rounding (half-up).

---

## Workflow
1. **Read environment** → extract `GDPEVO_ENV_BASE_URL`.  
2. **Fetch all seven endpoints** in parallel if possible; retry once on transient HTTP errors.  
3. **Join** all datasets on `account_id`.  
4. **Compute per-account**:
   - `overdue_balance`
   - `expansion_pipeline`
   - `risk_level`
   - `reason_codes`
   - `primary_action`
   - `next_touch_due_date`
5. **Filter** to accounts with at least one reason code.  
6. **Sort** and rank.  
7. **Roll up** `segment_summary`.  
8. **Build** `followup_calendar` from the earliest touches per action type.  
9. **Select** `policy_codes` based on the data patterns observed.  
10. **Emit** the final JSON matching the schema exactly.

## Pitfalls
- **Do not hard-code `localhost` as the API host.** Always read `environment_access.md`.  
- **Do not include accounts with zero reason codes** on the action board.  
- **Preserve two-decimal precision** on all monetary values; avoid integer serialization.  
- **Reason-code order matters** — keep the priority order listed above, not alphabetical.  
- `next_touch_due_date` must be `null` (not omitted, not `""`) for `no_action` accounts.  
- The `followup_calendar` must contain **all five keys** even if some action types have no accounts.  
- Policy codes are **not** free-form; choose only from the enumerated sets.

## Controlled Labels
Use exactly these strings (case-sensitive) everywhere:

- Risk levels: `critical`, `high`, `medium`, `low`
- Primary actions: `collections_followup`, `technical_recovery`, `renewal_save`, `executive_escalation`, `nurture_monitor`, `no_action`
- Reason codes: `overdue_receivable`, `renewal_window`, `nps_drop`, `sla_degradation`, `usage_decline`, `expansion_offset`
- Calendar keys: `collections_followup`, `technical_recovery`, `renewal_save`, `executive_qbr`, `nurture_monitor`
