# Support Console Reference

## Endpoints

- `/api/catalog`
- `/api/tickets`
- `/api/tickets/<ticket_id>`
- `/api/outages`
- `/api/diagnostics/<ticket_id>`
- `/api/troubleshooting/<ticket_id>`
- `/api/cases`
- `/api/cases/<case_id>`
- `/api/customers`
- `/api/lines/<line_id>`
- `/api/bills`
- `/api/plans`
- `/api/devices/<device_id>`
- `/api/enterprise/accounts`
- `/api/enterprise/incidents`
- `/api/enterprise/export-runs`
- `/api/enterprise/messages`
- `/api/enterprise/sla/<enterprise_account_id>`

## Lookup Order

1. Use IDs from the payload to fetch the primary record.
2. Join to the supporting record types named by the template.
3. Decide the output only after the linked records agree.

## Decision Cues

### Offline Tickets

- Active outage in the same service area and service type -> `PENDING_ACTION`, `OUTAGE_WAIT`, outage id populated, no escalation.
- Account hold, invalid account, or other eligibility blocker -> `FAILED`, `INELIGIBLE_ACCOUNT` or `AUTH_FAILED`, no diagnostics.
- Customer-side recoverable performance issue -> `RESOLVED`, `AUTO_TROUBLESHOOTING`, diagnostic needed true.
- Line work, capacity, or provisioning defects -> `ESCALATED` to `FIELD_OPS`, `NETWORK_ENGINEERING`, or `TIER2_SUPPORT`.
- Set `latency_issue`, `stability_issue`, and `bandwidth_issue` from the symptom cluster; use true when the issue text is a performance problem rather than a pure access failure.

### Queue-Quality Reviews

- `ACTIVE_OUTAGE` -> `PENDING_ACTION`, `NONE`, false.
- `INVALID_ACCOUNT` -> `FAILED`, `NONE`, false.
- `AUTH_FAILED` -> `FAILED`, `NONE`, false.
- `OVERDUE_SUSPENSION` -> `FAILED`, `ACCOUNTS_PAYABLE`, false.
- `NETWORK_CAPACITY` -> `ESCALATED`, `NETWORK_ENGINEERING`, true.
- `PROVISIONING_STALE` -> `ESCALATED`, `TIER2_SUPPORT`, true.
- `PHYSICAL_LINE_FAULT` -> `ESCALATED`, `FIELD_OPS`, true.
- `RESOLVED` with a live line-level issue usually still gets `diagnostic_required=true`.

### Contact-Center Queues

- `NO_SERVICE` after a commute -> `RESEAT_SIM`.
- Suspended line with willingness to pay -> `SEND_PAYMENT_REQUEST` then `RESUME_LINE_REBOOT`.
- Abroad or roaming-related data loss -> `TOGGLE_ROAMING` or `ENABLE_LINE_ROAMING`.
- MMS or photo failure -> `GRANT_MESSAGING_PERMISSION` with `storage` or `sms_and_storage`.
- Slow data with VPN -> `DISCONNECT_VPN`.
- Slow data with data saver -> `TOGGLE_DATA_SAVER`.
- Slow data on older network mode -> `SET_NETWORK_MODE`.
- Data stopped after settings change -> `TOGGLE_MOBILE_DATA`.
- Usage-limit depletion -> `REFUEL_DATA`.
- Use `carrier_update_required=true` only for line-level roaming or carrier changes.
- Compute refuel charge as `data_refuel_gb * plan.data_refueling_price_per_gb`, rounded to two decimals.

### Enterprise Export Complaints

- Group export runs by `incident_id` and `enterprise_account_id`.
- Consecutive failed runs define the failure window; the first succeeding run marks recovery.
- `backfill_days` equals the count of failed days.
- Derive `root_cause_category` from the failure code and the message evidence.
- Use the account record for `engineering_owner`, `account_owner`, `name`, and `tier`.
- Use the SLA record for the credit trigger and percent.
- Build `channel_name`, `evidence_folder`, and `report_title` from the naming style in the requirements.
- Order `share_permissions` exactly as the requirements list the users.
- Set `response_status` to `NEEDS_FINANCE_REVIEW` when credit approval is still needed.
