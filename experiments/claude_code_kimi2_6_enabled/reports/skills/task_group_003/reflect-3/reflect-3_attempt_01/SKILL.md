# Task Group 003 – Support Console Skill

## Environment
- Base URL: `http://34.46.77.124:8003` (override any local references)
- Only remote API calls; do not run local env/setup scripts or read env/ sources.

## Shared API Endpoints
Inspect these endpoints in this order. Do not brute-force scan.

| Resource | Endpoint | Notes |
|----------|----------|-------|
| Cases | `GET /api/cases` | List all cases; includes `case_id`, `customer_id`, `line_id`, `device_id`, `issue_type`, `summary` |
| Case detail | `GET /api/cases/{case_id}` | Same shape as list item |
| Tickets | `GET /api/tickets` | List all tickets; includes `ticket_id`, `account_id`, `service_area`, `service_type`, `status`, `issue_summary` |
| Ticket detail | `GET /api/tickets/{ticket_id}` | Same shape as list item |
| Accounts | `GET /api/accounts` | List all accounts |
| Account detail | `GET /api/accounts/{account_id}` | Includes `status`, `tier`, `service_area`, `authentication.last_login_status`, `authentication.account_recovery_status` |
| Lines | `GET /api/lines` | List all lines |
| Line detail | `GET /api/lines/{line_id}` | Includes `status`, `suspension_reason`, `roaming_enabled`, `plan_id`, `data_used_gb` |
| Devices | `GET /api/devices/{device_id}` | Critical for mobile tasks. Fields: `sim_status`, `signal_strength`, `mobile_data_enabled`, `phone_roaming_enabled`, `data_saver_mode`, `network_mode_preference`, `vpn_connected`, `airplane_mode`, `can_send_mms`, `messaging_permissions.sms`, `messaging_permissions.storage`, `mmsc_url_present`, `speed_test` |
| Plans | `GET /api/plans` | List all plans with `data_limit_gb`, `data_refueling_price_per_gb`, `monthly_price_usd` |
| Bills | `GET /api/bills` | List all bills with `customer_id`, `amount_due_usd`, `status` |
| Outages | `GET /api/outages` | List active/past outages with `service_area`, `service_types`, `active`, `outage_id` |

## General Data-Fetching SOP
1. Read the payload file(s) to get IDs.
2. For every ID, call the relevant detail endpoint(s) above. Do not assume values from the payload alone when the prompt says “resolved from the support-console records.”
3. Cross-reference service areas against `/api/outages` to detect active outages.
4. Cross-reference account status (Active vs Suspended) and authentication state.

## Task-Type 1 – Mobile Support Queue (case_queue.json / mobile_data_worklist.json)
### Output format
- `case_decisions[]` preserving ascending `case_id` order.
- Fields: `case_id`, `customer_id`, `line_id`, `primary_action`, `secondary_action`, `permission`, `bill_id`, `charge_amount_usd` (two decimals), `final_route`.
- `queue_summary` / `worklist_summary`: count categories exactly.

### Decision Rules (derived from training)
- **SIM missing / no signal / no service** → `RESEAT_SIM` → `SELF_SERVICE`
- **Line suspended + overdue bill** → `SEND_PAYMENT_REQUEST` (primary), `RESUME_LINE_REBOOT` (secondary). `bill_id` = the overdue bill. `charge_amount_usd` = `amount_due_usd`. Route = `BILLING_RECOVERY`.
- **Traveler cannot use mobile data abroad + `phone_roaming_enabled` = false** → `TOGGLE_ROAMING` → `SELF_SERVICE`
- **Traveler has roaming on phone but no data + `phone_roaming_enabled` = true** → `ENABLE_LINE_ROAMING` → `CARRIER_UPDATE`
- **Messaging app cannot send photos + `messaging_permissions.storage` = false** → `GRANT_MESSAGING_PERMISSION`, permission = `storage` → `SELF_SERVICE`
- **Slow data + `vpn_connected` = true** → `DISCONNECT_VPN` → `SELF_SERVICE`
- **Data stopped after usage limit + `data_used_gb` > `plan.data_limit_gb`** → `REFUEL_DATA`. `data_refuel_gb` = customer preference `accepted_refuel_gb`. `charge_amount_usd` = `accepted_refuel_gb × plan.data_refueling_price_per_gb`. Route = `DATA_RECOVERY`.
- **Slow data + `data_saver_mode` = true** → `TOGGLE_DATA_SAVER` → `DEVICE_SETTING_FIX`
- **Slow data + `network_mode_preference` = `3g_only`** → `SET_NETWORK_MODE` → `DEVICE_SETTING_FIX`
- **No data + `mobile_data_enabled` = false** → `TOGGLE_MOBILE_DATA` → `DEVICE_SETTING_FIX`
- When no secondary action is needed, use `NO_ACTION`.
- `permission` enum: `NONE | sms | storage | sms_and_storage`. Use exact enum strings.

## Task-Type 2 – Ticket / Queue Classification (ticket_batch.csv / queue_snapshot.csv)
### Output format
- `ticket_decisions[]` preserving payload order.
- Fields: `ticket_id`, `account_id`, `final_resolution_status`, `diagnostic_needed`, `latency_issue`, `stability_issue`, `bandwidth_issue`, `outage_id`, `escalation_team`, `resolution_route`.
- `batch_summary` / `queue_summary`: integer counts for each status and team.

### Classification Rules
- Check `/api/outages` for active outages matching the ticket’s `service_area` and `service_type`. If matched → `outage_id` populated, `resolution_route` = `OUTAGE_WAIT`, `final_resolution_status` = `PENDING_ACTION`, increment `tickets_requiring_customer_wait`.
- **Account status = Suspended** → `resolution_route` = `INELIGIBLE_ACCOUNT`, `final_resolution_status` = `FAILED` (or `PENDING_ACTION` if a payment hold), `escalation_team` = `NONE`.
- **Authentication failure / recovery failure** → `resolution_route` = `AUTH_FAILED`, `escalation_team` = `TIER2_SUPPORT`.
- **No matching account in intake (bad account_id)** → `INVALID_ACCOUNT`, `FAILED`.
- **Network capacity / backbone errors** → `NETWORK_CAPACITY`, `ESCALATED`, `NETWORK_ENGINEERING`.
- **Provisioning mismatch** → `PROVISIONING_STALE`, `ESCALATED`, `TIER2_SUPPORT`.
- **Intermittent / poor speed with no active outage** → `AUTO_TROUBLESHOOTING`, `PENDING_ACTION`, set `latency_issue`, `stability_issue`, `bandwidth_issue` as appropriate, `diagnostic_needed` = true.

## Task-Type 3 – Enterprise Export Complaint (client_complaint_email.txt + response_requirements.json)
### Output format
- Flat JSON with incident metadata fields (no nested arrays except `share_permissions` and `failure_window`).
- `share_permissions` ordered exactly as listed in `response_requirements.json`.

### Extraction Rules
- Read the complaint email for: account ID, export window, failed days, root cause, owners, SLA credit percent, requested folder name.
- Read `response_requirements.json` for permission users and naming_style.
- **naming_style** overrides literal folder names in the email when there is a conflict:
  - channel: lowercase-hyphen (e.g., `acme-weekly`)
  - evidence folder: `{client}-{date}-investigation` (e.g., `acmecorp-2025-06-02-investigation`)
  - report title: `{Client} Export Failure Report` (e.g., `AcmeCorp Export Failure Report`)
- `contributing_alert_issue` enum: `ARCHIVED_ALERT_ROUTE | NONE | UNKNOWN`
- `response_status` is typically `NEEDS_FINANCE_REVIEW` when an SLA credit is explicitly requested; otherwise may be `READY_TO_SEND` or `UNDER_INVESTIGATION`.
- Include all `required_fields` from the requirements file; missing fields will score 0.

## Sorting & Rounding
- Preserve ascending `case_id` or payload order in all arrays.
- Monetary values: exactly two decimal places (`0.00` when not applicable).
- Data refuel: one decimal place (`0.0` when not applicable).
- Percent / counts: integers.
- Averages: round to two decimals unless template specifies otherwise.

## Common Pitfalls
1. **Using wrong answer template** – verify the actual `answer_template.json` in the task directory; do not assume it matches a previous task.
2. **Not calling the API** – prompts explicitly say “resolved from the support-console records.” Device/line/account states can only be determined from the API.
3. **Wrong permission enum** – use `storage` (not `messaging_storage`) and `sms_and_storage` exactly.
4. **Roaming confusion** – distinguish `phone_roaming_enabled` (device setting) from `roaming_enabled` (line setting). The required action depends on which one is off and how the symptom is phrased.
5. **Forgetting secondary action** – when no follow-up is needed, explicitly set `"NO_ACTION"`.
6. **Outage lookup** – always cross-reference `service_area` + `service_type` against `/api/outages`; do not infer outages from ticket text alone.
7. **Inactive vs active outage** – an outage must be `active: true` to assign `OUTAGE_WAIT`.
