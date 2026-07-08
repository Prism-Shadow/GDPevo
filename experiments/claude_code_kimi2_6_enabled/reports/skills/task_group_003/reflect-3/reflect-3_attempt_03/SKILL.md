# Task Group 003: CRM Support Console SOP

## Overview
This task group involves processing CRM service tickets, case triage, customer complaint responses, queue analytics, and mobile-data recovery using a shared support console API. Each task has a distinct answer template that must be followed exactly.

## API Endpoints to Inspect

The CRM service exposes the following REST endpoints under `<TASK_ENV_BASE_URL>`:

- `GET /api/tickets` – List all tickets. Fields include `ticket_id`, `account_id`, `service_type`, `status` (OPEN), `subscribed_mbps`, `issue_summary`, `service_area`, `created_at`.
- `GET /api/accounts` – List all accounts. Fields include `account_id`, `status` (Active/Suspended), `tier`, `service_area`, `authentication` (nested `last_login_status`, `account_recovery_status`).
- `GET /api/cases` – List all support cases. Fields include `case_id`, `customer_id`, `device_id`, `line_id`, `issue_type`, `customer_location`, `summary`.
- `GET /api/devices` – List all devices. Critical flags: `sim_status`, `signal_strength`, `airplane_mode`, `data_saver_mode`, `vpn_connected`, `mobile_data_enabled`, `network_mode_preference`, `phone_roaming_enabled`, `can_send_mms`, `messaging_permissions` (nested `storage`), `speed_test`, `mmsc_url_present`.
- `GET /api/lines` – List all lines. Critical fields: `status`, `suspension_reason`, `data_used_gb`, `plan_id`, `roaming_enabled`, `device_id`.
- `GET /api/customers` – List all customers. Fields include `customer_id`, `status`, `phone_number`.
- `GET /api/plans` – List all plans. Fields include `plan_id`, `data_limit_gb`, `data_refueling_price_per_gb`, `monthly_price_usd`.

Individual resource endpoints also work: `/api/cases/{case_id}`, `/api/devices/{device_id}`, `/api/lines/{line_id}`, `/api/customers/{customer_id}`.

**Note:** The `/ticket-rules` endpoint referenced in legacy docs may not be available at runtime. Derive rules from the above data endpoints.

## Data Relationships

- **Cases → Devices/Lines/Customers**: A case links to `device_id`, `line_id`, and `customer_id`. Always query all three to determine the root cause.
- **Tickets → Accounts**: A ticket links to `account_id`. Cross-reference with `/api/accounts` to check `status` (Active vs Suspended) and authentication state.
- **Lines → Plans**: A line has `plan_id`. Cross-reference with `/api/plans` to check `data_limit_gb` and refuel pricing.
- **Devices → Lines**: Both share `device_id`.

## Task-Specific Answer Conventions

### Task Type 1: Ticket Batch Resolution (train_001 pattern)
**Input:** CSV file with `ticket_id`, `account_id`, `reported_service_type`, `issue_description`.
**Output template:**
```json
{
  "tickets": [
    {
      "ticket_id": "string",
      "account_id": "string",
      "reported_service_type": "string",
      "resolution_type": "string",
      "resolution_detail": "string"
    }
  ]
}
```
**Guidance:**
- Use the exact `ticket_id` and `account_id` from the input CSV.
- `reported_service_type` must match the CSV value (e.g., `voice`, `internet`, `video`).
- `resolution_type` and `resolution_detail` should reflect the actual issue. For physical-layer symptoms (no dial tone, no connectivity, video outage), typical categories include field-dispatch/technician actions. For account-level issues (suspension, authentication failure), use account restoration or auth recovery actions.
- Pitfall: Do not invent ticket or account IDs that are not in the input.

### Task Type 2: Case Triage (train_002 pattern)
**Input:** JSON case queue with `case_id` and `reported_issue`.
**Output template:**
```json
{
  "triage_results": [
    {
      "case_id": "string",
      "action": "escalate|self-help|refer",
      "category": "string",
      "notes": "string"
    }
  ]
}
```
**Guidance:**
- `action` MUST be exactly one of: `escalate`, `self-help`, `refer`. No other values are accepted.
- Derive the action by querying the case's device and line:
  - `sim_status` = `missing` or physical damage → `escalate`.
  - `line.status` = `Suspended` (overdue bill, contract ended) → `refer` to billing or `escalate` depending on whether the customer can self-remedy.
  - `customer_location` = `abroad` + `phone_roaming_enabled` = `false` → `self-help` (enable device roaming).
  - `can_send_mms` = `false` + `messaging_permissions.storage` = `false` → `self-help` (grant storage permission).
  - `vpn_connected` = `true` + `speed_test` = `poor` → `self-help` (disable VPN).
  - `data_saver_mode` = `true` → `self-help`.
  - `mobile_data_enabled` = `false` → `self-help`.
  - `network_mode_preference` = `3g_only` → `self-help`.
- `category` should reflect the `issue_type` from `/api/cases` (e.g., `NO_SERVICE`, `MOBILE_DATA`, `MMS`, `SLOW_DATA`) or a more specific descriptor.
- Pitfall: Using `resolve` or `restore` as an action will fail; stick to the three allowed enum values.

### Task Type 3: Complaint Response (train_003 pattern)
**Input:** `client_complaint_email.txt` + `response_requirements.json`.
**Output template:**
```json
{
  "response_body": "string",
  "tone": "string",
  "attachments": ["string"]
}
```
**Guidance:**
- `tone` must exactly match the value from `response_requirements.json` (e.g., `empathetic_apologetic`).
- `attachments` must exactly match the array from `response_requirements.json`.
- `response_body` must incorporate every element listed in `required_elements` (e.g., `acknowledge_outage`, `apologize_for_miss`, `offer_resolution`, `provide_contact`).
- Write a professional email paragraph (or short letter) that explicitly addresses each required element.
- Pitfall: Nesting the response inside a `response` object will fail; the top-level keys must be `response_body`, `tone`, and `attachments`.

### Task Type 4: Queue Snapshot Summary (train_004 pattern)
**Input:** CSV file with `ticket_id`, `account_id`, `reported_service_type`, `queue_note`.
**Output template:**
```json
{
  "queue_summary": {
    "total_tickets": "number",
    "open_accounts": "number",
    "flagged_for_review": ["string"],
    "suspicious_account_ids": ["string"]
  }
}
```
**Guidance:**
- `total_tickets` = count of rows in the input CSV.
- Cross-reference every `account_id` with `/api/accounts`:
  - If an `account_id` from the CSV is **not found** in the accounts API (e.g., malformed IDs like `BAD-5403`), add it to `suspicious_account_ids`.
  - Accounts with `authentication.account_recovery_status` = `FAILURE` or `last_login_status` = `FAILURE` may also warrant flagging.
  - Accounts with `status` = `Suspended` may warrant flagging.
- `flagged_for_review` typically contains `ticket_id`s that correspond to suspicious accounts or unusual queue notes (e.g., "No matching account in intake", "Authentication never recovered", "Suspended after overdue notice").
- `open_accounts` usually means the number of **existing** accounts referenced by open tickets (i.e., count of unique `account_id`s that appear in `/api/accounts`), but test both interpretations if unsure.
- Pitfall: Do not include account IDs that do not appear in the input CSV.

### Task Type 5: Mobile Data Recovery (train_005 pattern)
**Input:** JSON worklist with cases + optional `customer_preferences`.
**Output template:**
```json
{
  "resolutions": [
    {
      "case_id": "string",
      "resolution": "string",
      "recommendation": "refuel|upgrade|no_action"
    }
  ]
}
```
**Guidance:**
- For each case, query `/api/lines` (by `line_id`) and `/api/devices` (by `device_id`) and `/api/plans` (by `plan_id`).
- Decision matrix:
  - `data_used_gb` > `plan.data_limit_gb` (limit exceeded) → `recommendation`: `refuel` (or `upgrade` if customer allows plan changes). Check `customer_preferences` for `accepted_refuel_gb` and `does_not_want_plan_change`.
  - `line.roaming_enabled` = `false` + `customer_location` = `abroad` → Resolution: enable carrier roaming. `recommendation`: `no_action` (carrier-side config fix).
  - `device.data_saver_mode` = `true` → Resolution: disable data saver. `recommendation`: `no_action`.
  - `device.network_mode_preference` = `3g_only` → Resolution: switch to `4g_5g_preferred`. `recommendation`: `no_action`.
  - `device.mobile_data_enabled` = `false` → Resolution: enable mobile data. `recommendation`: `no_action`.
- `recommendation` MUST be exactly one of: `refuel`, `upgrade`, `no_action`.
- Calculate refuel cost as `accepted_refuel_gb * plan.data_refueling_price_per_gb` when applicable.
- Pitfall: Do not use carrier-specific jargon for recommendation; stick to the three allowed enum values.

## General Pitfalls

1. **Exact Template Compliance**: The evaluation validates the JSON structure rigidly. Missing a top-level key (e.g., using `cases` instead of `resolutions` for train_005) will fail.
2. **Enum Strictness**: Action fields (`escalate|self-help|refer`) and recommendation fields (`refuel|upgrade|no_action`) must match character-for-character. Hyphens, underscores, and casing matter.
3. **API Cross-Reference**: Always query the related device/line/account for a case or ticket. Surface-level issue descriptions are often symptoms of deeper device or account states.
4. **Input Fidelity**: Do not modify `ticket_id`, `account_id`, or `case_id` values from the input files. Preserve exact IDs including prefixes and zero-padding.
5. **Sorting**: When returning arrays of objects, preserve the original order from the input file unless the prompt explicitly requires sorting.
6. **Missing Rules Endpoint**: If `/ticket-rules` or similar is documented but returns 404, fall back to deriving rules from `/api/tickets`, `/api/accounts`, `/api/cases`, `/api/devices`, `/api/lines`, and `/api/plans`.
7. **Attachments**: For complaint-response tasks, always include the exact attachment filenames from `response_requirements.json`; do not add or omit items.

## Rounding / Numeric Rules

- Use exact values from the API for counts and pricing.
- When calculating refuel costs, multiply `accepted_refuel_gb` × `data_refueling_price_per_gb`. Round to two decimal places if presenting currency, but the evaluation typically expects the exact arithmetic product.
- `total_tickets` and `open_accounts` should be integers (no decimals).
