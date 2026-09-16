---
name: support-console-operations
description: Solve support-console operations tasks that require API-backed JSON decisions for service tickets, mobile cases, and enterprise export incidents.
---

# Support Console Operations Skill

Use this skill when a task asks for support-console evidence from `<TASK_ENV_BASE_URL>` and requires JSON conforming to a provided `payloads/answer_template.json`.

## Ground Rules

- Read the prompt, every payload file, and the answer template first.
- Return only valid JSON matching the template shape, field names, enum spelling, ordering requirements, and numeric precision.
- Use the support-console API as the source of truth. Do not infer from customer wording alone when API records exist.
- Use only read-only business endpoints. Do not call any judge/evaluator endpoint.
- Preserve payload order for ticket lists. Sort case decisions by ascending `case_id` when the template says so.
- Leave string IDs empty only when the template says an empty string means "not applicable".
- Compute all summary counts from the emitted decisions, not separately.

## API Workflow

Start with `GET /api/catalog` when available to confirm endpoint names. Use `GET /api/search?q=<id or client>` as a cross-reference when direct endpoints are absent or when you need linked records.

For service tickets, gather:

- Ticket: `/api/tickets/{ticket_id}`
- Diagnostics: `/api/diagnostics/{ticket_id}`
- Troubleshooting: `/api/troubleshooting/{ticket_id}`
- Outages: `/api/outages`, filtered to active outages matching both `service_area` and `service_type`
- Account state: search by `account_id` if a direct account endpoint is unavailable

For mobile/contact-center cases, gather:

- Case record via the case endpoint advertised by the catalog, or `search` by `case_id`
- Customer: `/api/customers/{customer_id}`
- Line: `/api/lines/{line_id}`
- Device: `/api/devices/{device_id}`
- Plan: `/api/plans/{plan_id}`
- Bills: search by `customer_id` or use `/api/bills`, then filter to that customer

For enterprise export incidents, gather:

- Incident: `/api/enterprise/incidents/{incident_id}` or search by client/product/reference
- Enterprise account: `/api/enterprise/accounts/{enterprise_account_id}`
- Export runs: `/api/enterprise/export-runs` or search by incident/account
- Messages: `/api/enterprise/messages` or search by client, incident, product, or failure terms
- SLA: `/api/enterprise/sla/{enterprise_account_id}`

## Service Ticket Decisions

Apply blockers before diagnostics:

1. If no matching account record exists for the ticket account, classify as failed with the invalid-account route/blocker and no diagnostic.
2. If account authentication shows failed login/recovery and the ticket is an authentication problem, classify as failed with the auth-failed route/blocker and no diagnostic.
3. If account or line state is suspended/held:
   - Use overdue-suspension and accounts-payable routing when the template has those fields and evidence mentions overdue billing.
   - Otherwise use the template's ineligible-account route/blocker with no escalation team.
4. If an active outage matches both service area and service type, classify as pending action/outage wait, include the outage ID when requested, set diagnostic-required/needed false, and count it as a customer-wait case.

If no blocker applies, use diagnostics and troubleshooting:

- Set `diagnostic_needed`/`diagnostic_required` true when diagnostics drive the decision.
- `latency_issue`: true for clearly high latency, typically around 100 ms or higher, or when root causes/text indicate latency or packet loss.
- `stability_issue`: true for high jitter, packet loss, signal loss, intermittent service, or similar stability evidence.
- `bandwidth_issue`: true when measured bandwidth is materially below subscribed speed, usually below about 80 percent, or when speed/throughput evidence says poor.
- If troubleshooting resolves metrics to acceptable levels and the root cause is a refreshable profile/configuration issue, mark resolved with the auto-troubleshooting/no-team route.
- Physical signal, fiber drop, damaged line, or line-work evidence escalates to field operations and physical-line-fault when that blocker enum exists.
- Backbone, capacity, congestion, or network-wide engineering evidence escalates to network engineering and network-capacity.
- Stale provisioning, profile mismatch after a move, or failed provisioning adjustment escalates to tier 2 support and provisioning-stale.
- If serious diagnostics remain bad after troubleshooting and no more specific route exists, escalate to tier 2 support.

For queue-quality templates:

- `key_blocker` is `NONE` for resolved/self-service outcomes.
- `route_team` is `NONE` unless an escalation or accounts-payable recovery is needed.
- Count each route-team enum from emitted decisions, including zeroes for teams present in the template.

## Mobile Case Decisions

Use the case issue type and customer wording to choose the relevant record fields, but let line/device/bill/plan state decide the action. Prefer the first matching item in this priority order.

1. Suspended line with overdue bill:
   - `primary_action`: `SEND_PAYMENT_REQUEST`
   - `secondary_action`: `RESUME_LINE_REBOOT`
   - `bill_id`: overdue bill for the customer
   - `charge_amount_usd`: overdue amount
   - route: billing recovery
2. Fraud, unsupported suspension, missing customer/line/device evidence, or ambiguous states that cannot be fixed from the allowed actions:
   - transfer human when available; otherwise no action only if the template has no transfer route.
3. No service:
   - `airplane_mode: true` -> `TOGGLE_AIRPLANE_MODE`
   - SIM missing/inactive/not ready -> `RESEAT_SIM`
   - mobile data disabled for a data complaint -> `TOGGLE_MOBILE_DATA`
   - APN/MMSC carrier settings missing -> `RESET_APN_REBOOT`
4. Roaming while abroad:
   - Phone roaming disabled while line roaming is enabled -> `TOGGLE_ROAMING`, no carrier update.
   - Line/carrier roaming disabled -> `ENABLE_LINE_ROAMING`, carrier update required.
   - If both are disabled and the template allows a secondary action, enable line roaming first and toggle device roaming second.
5. Data limit exhausted:
   - Compare line `data_used_gb` with plan `data_limit_gb`.
   - If payload preferences include accepted refuel GB, use `REFUEL_DATA`.
   - `data_refuel_gb` is the accepted amount; charge is accepted GB times `data_refueling_price_per_gb`.
   - Use a data-recovery route when the template provides one; otherwise use self-service unless human approval is required.
6. Slow data:
   - `data_saver_mode: true` -> `TOGGLE_DATA_SAVER`
   - old or restrictive network mode such as 3G-only -> `SET_NETWORK_MODE`
   - `vpn_connected: true` -> `DISCONNECT_VPN`
7. MMS/photo messaging:
   - Missing `sms` and/or `storage` permissions -> `GRANT_MESSAGING_PERMISSION`; set `permission` to `sms`, `storage`, or `sms_and_storage`.
   - Permissions present but MMS/APN config missing -> `RESET_APN_REBOOT`.
8. Voice/Wi-Fi calling issues:
   - If Wi-Fi calling is off and the complaint is about voice coverage or Wi-Fi calling, use `TOGGLE_WIFI_CALLING`.

Set `secondary_action` to `NO_ACTION` unless a required follow-up is shown by the rule. Set permission to `NONE` except for messaging-permission fixes. Set bill and charge fields to empty/zero unless billing recovery or refuel applies.

Route mapping:

- Billing recovery: `BILLING_RECOVERY`
- Carrier-side line change: `CARRIER_UPDATE` and `carrier_update_required: true`
- Refuel/data-limit recovery: `DATA_RECOVERY` when present
- Local device settings: `DEVICE_SETTING_FIX` when present, otherwise `SELF_SERVICE`
- Human transfer: `HUMAN_TRANSFER`

## Enterprise Export Response Packages

Extract the client, product, requested incident reference, required users, and naming requirements from the payloads. Then build the response from API evidence:

- Identify the incident from the reference first. If the reference is approximate, search by client and product and choose the incident whose account and product match the complaint.
- Use the incident for `incident_id`, `enterprise_account_id`, `severity`, `engineering_owner`, and `account_owner` unless stronger account evidence overrides owner fields.
- Filter export runs to the chosen incident/account/product. Failed runs determine:
  - `failure_window.start_date`: earliest failed run date
  - `failure_window.end_date`: latest failed run date
  - `failure_window.failed_days`: count of failed run dates
  - `backfill_days`: failed-day count unless message/export evidence gives a different manual backfill count
- Derive `root_cause_category` as a concise lower-case phrase from failure codes plus message evidence. Prefer the business-readable cause, not the raw code.
- Set `contributing_alert_issue` to `ARCHIVED_ALERT_ROUTE` when alert evidence is in an archive/retired channel or states that alerts routed to an archived location; `NONE` when active alert routing is clean; `UNKNOWN` when evidence is missing.
- Use the SLA contract for `sla_credit_percent` when the failure window meets the trigger. Otherwise use zero if the template requires a number.
- Build names from requirements:
  - `channel_name`: lowercase client name, punctuation removed, words hyphenated.
  - `evidence_folder`: client name plus month/year of the failure window plus `Investigation`.
  - `report_title`: client name plus an export-failure resolution-report title, following the requested naming style.
- Build `share_permissions` in exactly the user order requested by the requirements. Give finance/SLA-credit reviewers view permission; give operational response collaborators edit permission; use upload-only only when requirements explicitly describe upload-only evidence intake.

Choose `response_status` by remaining blocker:

- Nonzero SLA credit or explicit credit handling still needing approval -> `NEEDS_FINANCE_REVIEW`
- Missing root cause, missing successful recovery/backfill evidence, or unresolved engineering facts -> `NEEDS_ENGINEERING_REVIEW` or `UNDER_INVESTIGATION` according to the template wording and incident state
- Complete evidence and no pending approval -> `READY_TO_SEND`

## Final JSON Check

Before final output:

- Verify every object has every field from the template and no extra fields.
- Verify enum spelling exactly matches the template.
- Recompute summaries from the decisions.
- Use JSON numbers for amounts; keep required one- or two-decimal values conceptually rounded to the template precision.
- Output JSON only, with no Markdown fence or explanation.
