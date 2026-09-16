# Support-Console Decision Rules

Use these rules after collecting API evidence. They are reusable heuristics for the support-console task family; the answer template for the current task remains authoritative.

## General Output Rules

- Return only JSON. Do not include explanations, markdown fences, comments, or uncertainty notes.
- Copy the top-level shape, field names, enum strings, and ordering instructions from `payloads/answer_template.json`.
- Preserve payload order when the template says so. Sort by ID only when the template explicitly asks for ascending order.
- Use JSON booleans and numbers, not strings. Use empty strings for not-applicable IDs if the template says so.
- Recompute every summary count from the decision objects after all decisions are filled.
- Prefer exact support-console records over text in the intake payload. Payload text identifies what to look up; the API supplies the evidence.
- Treat generated/noise records as distractors unless they are directly linked by the input IDs, incident ID, enterprise account, customer, line, or ticket.

## Fixed-Service Ticket Routing

For ticket batch, queue-quality, or SLA handoff tasks, fetch each ticket, its account, active outages, diagnostics, and troubleshooting records. Apply blockers before diagnostics:

1. **Missing ticket or account**: classify as `FAILED`. Use `INVALID_ACCOUNT` or `INVALID_ACCOUNT` route when the template has a blocker/route field. No diagnostic is required.
2. **Authentication failure**: if the account authentication fields show failed login or failed recovery, classify as `FAILED` with `AUTH_FAILED`. No diagnostic is required.
3. **Suspended account**: classify as `FAILED`. Use `OVERDUE_SUSPENSION` when the suspension is billing/overdue; use `FRAUD_SUSPENSION` when fraud is indicated. In queue templates, route overdue suspensions to `ACCOUNTS_PAYABLE`; in simpler resolution-route templates, use the ineligible-account route and no escalation team unless the template requires one.
4. **Active outage**: if an active outage matches the ticket service area and includes the ticket service type, classify as `PENDING_ACTION`. Use the matching outage ID, route `OUTAGE_WAIT` when available, `ACTIVE_OUTAGE` as the blocker when available, and do not mark diagnostics as required.
5. **Diagnostics and troubleshooting**: for active, non-outage tickets, use diagnostics to identify issue flags and root cause; use troubleshooting to decide whether automated recovery succeeded.

Map root causes conservatively:

- Configuration/profile causes such as `CONFIGURATION_DRIFT` or stale voice profile recover through automated troubleshooting when post-checks improve enough for the service. Mark `RESOLVED`, team `NONE`, route `AUTO_TROUBLESHOOTING`, blocker `NONE`.
- Physical plant causes such as fiber/drop damage or signal loss require field work. Mark `ESCALATED`, team `FIELD_OPS`, blocker `PHYSICAL_LINE_FAULT`.
- Capacity/backbone causes require network engineering. Mark `ESCALATED`, team `NETWORK_ENGINEERING`, blocker `NETWORK_CAPACITY`.
- Provisioning mismatch/stale provisioning requires tier-2 support. Mark `ESCALATED`, team `TIER2_SUPPORT`, blocker `PROVISIONING_STALE`.
- Unknown persistent causes should escalate to `TIER2_SUPPORT` unless the template or evidence points to a more specific team.

Diagnostic flags:

- `diagnostic_needed`/`diagnostic_required` is true only when the diagnostic was needed to classify an active non-outage ticket.
- `latency_issue` is true for materially high latency, commonly over 100 ms, or when root-cause evidence directly names latency or packet loss.
- `stability_issue` is true for high jitter, packet loss, signal loss, intermittent service, or physical-line causes.
- `bandwidth_issue` is true when measured bandwidth is materially below the subscribed speed, commonly below 80 percent of subscribed Mbps.

## Mobile and Contact-Center Case Routing

For mobile/contact-center worklists, fetch the case, customer, line, device, plan, and all bills for the customer. Billing and carrier state take priority over device toggles.

Primary routes and actions:

- Suspended line with overdue bill: `SEND_PAYMENT_REQUEST`; follow with `RESUME_LINE_REBOOT` when the template has a secondary action. Include the overdue bill ID and amount. Route as `BILLING_RECOVERY`.
- Suspended line for fraud or an unclear non-billing reason: `TRANSFER_HUMAN`.
- No service with airplane mode enabled: `TOGGLE_AIRPLANE_MODE`.
- No service with missing/unseated SIM: `RESEAT_SIM`.
- Mobile data disabled on the device: `TOGGLE_MOBILE_DATA`.
- Traveler/abroad with device roaming off but line roaming enabled: `TOGGLE_ROAMING`.
- Traveler/abroad with line roaming disabled but device roaming on: `ENABLE_LINE_ROAMING`, mark carrier update required, and use the carrier-update route.
- MMS/photo messaging failure with missing `storage` or `sms` permission: `GRANT_MESSAGING_PERMISSION`; set `permission` to `storage`, `sms`, or `sms_and_storage`.
- MMS with missing APN/MMSC evidence: use APN reset/reboot if that enum is available.
- Data usage at or above the plan limit with an accepted top-up/refuel preference: `REFUEL_DATA`; set `data_refuel_gb` from the accepted amount and charge as `accepted_gb * plan.data_refueling_price_per_gb`.
- Slow data with data saver enabled: `TOGGLE_DATA_SAVER`.
- Slow data with an obsolete network mode such as 3G-only: `SET_NETWORK_MODE`.
- Slow data with VPN connected: `DISCONNECT_VPN`.
- Voice/calling issues with Wi-Fi calling disabled and that enum available: `TOGGLE_WIFI_CALLING`.
- If the evidence does not identify a supported self-service, billing, data recovery, or carrier action, use `TRANSFER_HUMAN`.

Field conventions:

- Set `secondary_action` to `NO_ACTION` unless a required follow-up is evident.
- Set `permission` to `NONE` unless the primary action grants messaging permission.
- Set not-applicable `bill_id` to an empty string and charges/refuel amounts to `0.0`.
- In contact-center templates, ordinary device fixes route to `SELF_SERVICE`; in mobile-data worklists, data-limit refuels route to `DATA_RECOVERY`, carrier changes to `CARRIER_UPDATE`, device settings to `DEVICE_SETTING_FIX`, and transfers to `HUMAN_TRANSFER`.

## Enterprise Export Response Packages

For enterprise export complaints, extract the incident ID, client name, product, requested users, and naming instructions from the payloads. Use `/api/search` to find candidates, then exact enterprise endpoints for the incident, account, SLA contract, export runs, and messages.

Evidence selection:

- Prefer runs with the exact `incident_id`. If no incident ID is provided, use the enterprise account, product, complaint dates, and client messages to identify the relevant run group.
- Sort export runs by `run_date`. The failure window is the consecutive failed block that matches the complaint. `failed_days` is the count of failed run dates in that block.
- `backfill_days` is the count of failed days that evidence shows were manually backfilled or recovered by a later successful run. If evidence says every failed day was manually backfilled, this equals `failed_days`.
- Derive `root_cause_category` from the repeated failure code and the explanatory messages. Convert machine codes to a concise lowercase phrase, and prefer the message wording when it explains the actual cause.
- Set `contributing_alert_issue` to `ARCHIVED_ALERT_ROUTE` when relevant alert evidence lives in an archive/archived alert channel or says alerts routed to an archive. Use `NONE` when there is no alert-routing issue; use `UNKNOWN` only when the task asks for the field and the evidence is insufficient.
- Fetch the SLA contract by enterprise account. Apply the export credit only when the trigger condition is satisfied by the failure window.

Owners and artifacts:

- Use `engineering_owner` and `account_owner` from the incident/account records.
- Generate `channel_name` from the client/account name by lowercasing, removing punctuation, and joining words with hyphens.
- Follow the payload naming style for `evidence_folder` and `report_title`. For client-date folders, use the client name plus the month and year from the failure window plus `Investigation`. For export reports, use the client name plus `Export Failure - Resolution Report` unless the requirements say otherwise.
- Include `share_permissions` users exactly as listed in the requirements. Use evidence to assign permissions when possible: finance/audit recipients normally get `view`, engineering/report collaborators get `edit`, and `upload_only` only when the requirements call for evidence uploads. If a required user has no role record, infer from position or wording and preserve the listed order.

Response status priority:

1. `UNDER_INVESTIGATION` if the incident or export-run evidence is still incomplete.
2. `NEEDS_ENGINEERING_REVIEW` if root cause, recovery, or engineering owner evidence is missing or unresolved.
3. `NEEDS_FINANCE_REVIEW` if an SLA credit applies and finance handling is required.
4. `READY_TO_SEND` when evidence, recovery, owners, artifacts, and required reviews are complete.
