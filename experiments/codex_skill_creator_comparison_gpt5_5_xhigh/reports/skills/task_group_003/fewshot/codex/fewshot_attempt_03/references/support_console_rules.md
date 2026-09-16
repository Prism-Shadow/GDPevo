# Support Console Rules

Use these rules after fetching support-console evidence. Treat them as priority guidance; the prompt and answer template remain authoritative.

## Endpoint Joins

Ticket tasks:
- Fetch the ticket by `ticket_id`.
- Fetch the service account by `account_id`.
- Fetch active outages and match `service_area` plus `service_type`.
- Fetch diagnostics and troubleshooting by `ticket_id`.

Mobile/contact-center tasks:
- Fetch the case by `case_id`; prefer the catalog path if endpoint aliases differ.
- Join `customer_id`, `line_id`, `device_id`, and `plan_id` to customer, line, device, plan, and customer bills.
- Use payload preferences for accepted data refuel amounts or refusal of plan changes.

Enterprise export tasks:
- Identify the enterprise incident from the complaint, incident reference, client name, and product.
- Join incident to enterprise account, SLA contract, export runs, and relevant messages.
- Derive owner, channel, folder, title, share permissions, and response status from API records plus response requirements.

`/api/search?q=...` is useful when the payload gives a client name, approximate incident reference, or partial record clue.

## Ticket Priority

Apply terminal blockers before diagnostics:
- Missing or nonmatching account: `FAILED`, no diagnostic, invalid-account blocker or route.
- Suspended or ineligible account: `FAILED`, no diagnostic. Use accounts-payable routing only for overdue billing suspension when the template has that team/blocker.
- Authentication failure with no recovered login: `FAILED`, no diagnostic, auth-failed blocker or route.
- Active matching outage: `PENDING_ACTION`, no diagnostic, outage/wait route, and the matching `outage_id` when the template asks for it.

Use diagnostics and troubleshooting after blockers:
- Configuration drift or stale voice/profile evidence that troubleshooting corrected maps to `RESOLVED` with self-service or auto-troubleshooting routing.
- Physical fiber, drop damage, or signal-loss evidence maps to escalation, usually field operations or physical-line-fault.
- Backbone or capacity evidence maps to network-engineering escalation.
- Stale provisioning evidence maps to tier-2 support escalation unless the fetched troubleshooting evidence clearly resolves it.

Diagnostic flags:
- `diagnostic_needed` or `diagnostic_required` is true only when diagnostics/troubleshooting evidence is used to resolve or escalate the issue.
- `latency_issue` comes from high latency or complaint/evidence of latency.
- `stability_issue` comes from jitter, packet loss, signal loss, intermittent service, or call drops.
- `bandwidth_issue` comes from poor speed or bandwidth materially below the subscribed rate.
- Summary fields such as customer-wait tickets count only final decisions that are pending because of an outage or wait route.

## Mobile Actions

Resolve billing and line state before device settings:
- Overdue suspended line with an unpaid bill: `SEND_PAYMENT_REQUEST`, then `RESUME_LINE_REBOOT`; route to billing recovery and include the bill and amount.
- Non-billing suspension, fraud, ended contract, missing records, or no supported deterministic operation: `TRANSFER_HUMAN`.

No-service actions:
- Airplane mode enabled: `TOGGLE_AIRPLANE_MODE`.
- Missing or unseated SIM: `RESEAT_SIM`.
- Line active and device state otherwise normal: choose the specific setting or carrier operation indicated by the fetched records; transfer if none applies.

MMS actions:
- Missing SMS and/or storage permission: `GRANT_MESSAGING_PERMISSION`; set the permission field to `sms`, `storage`, or `sms_and_storage`.
- Missing MMSC/APN profile evidence: `RESET_APN_REBOOT`.

Mobile-data actions:
- Device mobile data disabled: `TOGGLE_MOBILE_DATA`.
- Traveler with phone roaming enabled but line roaming disabled: `ENABLE_LINE_ROAMING`, `carrier_update_required: true`, carrier-update route.
- Traveler with line roaming enabled but phone roaming disabled: `TOGGLE_ROAMING`.
- Data usage above plan limit and an accepted refuel amount: `REFUEL_DATA`; charge equals accepted GB times the plan refuel price per GB.
- Slow data with data saver enabled: `TOGGLE_DATA_SAVER`.
- Slow data with old or restrictive network mode: `SET_NETWORK_MODE`.
- Slow data with VPN connected: `DISCONNECT_VPN`.

Set `secondary_action` to `NO_ACTION` unless the rule explicitly requires a follow-up.

## Enterprise Export Packages

Use export-run evidence for dates and counts:
- Failure window starts at the first failed run date and ends at the last failed run date for the incident/product.
- `failed_days` is the count of failed run dates in that window.
- `backfill_days` is the count of failed days later backfilled or manually recovered according to export-run or message evidence.

Root cause and alert route:
- Convert failure codes and messages into a concise lowercase category, such as credential, scheduler, dependency, or storage failure phrasing.
- If the relevant alert or discussion appears only in an archived alert channel, use `ARCHIVED_ALERT_ROUTE`; otherwise use `NONE` when evidence shows a normal route, and `UNKNOWN` when evidence is insufficient.

Response status:
- If an SLA credit is owed and finance approval is not already confirmed, use `NEEDS_FINANCE_REVIEW`.
- If root cause or remediation is unresolved, use engineering review or investigation status as the template permits.
- Use ready-to-send only when incident, owners, backfill, SLA handling, artifacts, and required permissions are all supported by evidence.

Naming artifacts:
- Lowercase channel names, hyphenate words, and remove punctuation unless requirements say otherwise.
- Folder and report titles should follow the requirement's client/date/title style using the enterprise account name and incident month.
- Preserve required share-permission user order and use the permission values from requirements or support-console evidence.
