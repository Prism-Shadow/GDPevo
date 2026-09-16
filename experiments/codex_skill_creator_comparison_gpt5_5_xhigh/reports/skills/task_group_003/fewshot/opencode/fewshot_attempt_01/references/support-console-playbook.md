# Support Console Playbook

Use the support-console base URL from the task environment note or prompt. No credentials are required.

## Quick template detector

- `ticket_decisions` + `batch_summary`: ticket batch triage.
- `case_decisions` + `queue_summary` with action enums like `RESEAT_SIM` or `TOGGLE_MOBILE_DATA`: mobile/contact queue.
- `case_decisions` + `worklist_summary` with `data_refuel_gb` and `carrier_update_required`: mobile-data recovery.
- `ticket_decisions` + `queue_summary` with blocker/team enums: queue-quality review.
- `incident_id` + `failure_window` + `share_permissions`: enterprise incident response.

## Common endpoints

- `GET /api/tickets`
- `GET /api/customers`
- `GET /api/lines`
- `GET /api/bills`
- `GET /api/plans`
- `GET /api/devices`
- `GET /api/outages`
- `GET /api/diagnostics/{ticket_id}`
- `GET /api/troubleshooting/{ticket_id}`
- `GET /api/enterprise/incidents`
- `GET /api/enterprise/export-runs`
- `GET /api/enterprise/messages`
- `GET /api/enterprise/accounts`
- `GET /api/enterprise/sla/{account_id}`

## Evidence rules

- Use IDs from the payload to locate records first.
- Prefer record state over complaint wording when they disagree.
- Use the smallest action that fits the evidence.
- Treat an active outage as a wait condition, not a self-service fix.
- Treat an invalid or ineligible account as `FAILED`, not `ESCALATED`.
- Treat billing suspension as a recovery flow when the template allows it.
- Treat carrier-side changes and local device toggles as distinct outcomes.

## Ticket batch triage

- If service area and service type match an active outage, use `PENDING_ACTION`, `OUTAGE_WAIT`, an empty outage id, and no escalation.
- If self-troubleshooting can fix the issue, use `RESOLVED`, `AUTO_TROUBLESHOOTING`, and mark the relevant issue booleans.
- If physical, network, or provisioning work is needed, use `ESCALATED` and the matching team.
- If the account is invalid, blocked, or not eligible, use `FAILED` with the matching failure route.
- Count summary fields from final statuses. Track customer-wait items only for cases that truly cannot close yet.

## Mobile/contact queue

- Match customer, line, bill, plan, and device records together.
- Use `RESEAT_SIM` for no-service or missing-SIM states.
- Use `SEND_PAYMENT_REQUEST` plus `RESUME_LINE_REBOOT` for overdue suspension recovery. Fill `bill_id` and `charge_amount_usd` from the bill record.
- Use `TOGGLE_ROAMING` or `ENABLE_LINE_ROAMING` when roaming is the blocker. Use `ENABLE_LINE_ROAMING` when a carrier-side update is required.
- Use `GRANT_MESSAGING_PERMISSION` for MMS or photo-send failures when permissions are missing. Choose `storage`, `sms`, or `sms_and_storage` from device state.
- Use `TOGGLE_DATA_SAVER`, `SET_NETWORK_MODE`, `DISCONNECT_VPN`, or `TOGGLE_MOBILE_DATA` for device-setting fixes.
- Use `REFUEL_DATA` only when the plan, usage, or customer preferences justify it. Compute charge from the accepted GB amount times the plan's refueling price.
- Use `NO_ACTION` only when the template expects no follow-up.

## Queue-quality review

- Map blockers to teams: active outage -> pending action / none; overdue suspension -> `ACCOUNTS_PAYABLE`; network capacity -> `NETWORK_ENGINEERING`; provisioning stale -> `TIER2_SUPPORT`; physical line fault -> `FIELD_OPS`.
- Set `diagnostic_required` to true when the blocker or route depends on troubleshooting evidence.
- Preserve ticket order exactly as given.

## Enterprise incident response

- Use `/api/enterprise/incidents/{id}` for the incident record, `/api/enterprise/export-runs` for the day-by-day failure pattern, `/api/enterprise/messages` for alert clues, `/api/enterprise/accounts` for account metadata, and `/api/enterprise/sla/{account_id}` for credit policy.
- Derive `failure_window` from consecutive failed runs.
- Set `backfill_days` to the number of days manually backfilled or required to restore coverage.
- Derive `root_cause_category` from the failure code and evidence pattern, and keep it concise.
- Set `contributing_alert_issue` only when the evidence explicitly supports it; otherwise use `NONE` or `UNKNOWN`.
- Copy owners from the incident and account records.
- Keep `share_permissions` in the order requested by the requirements.
- Follow naming requirements exactly; treat channel names, folder names, and report titles as formatting fields, not creative writing.
- Set `response_status` to the least-final state that still matches unresolved approval or investigation needs.
