---
name: task-group-003-fewshot-attempt-02
description: Use this skill when solving task_group_003 support-console tasks involving residential service tickets, mobile support cases, mobile-data recovery worklists, or enterprise export-complaint response packages. It gives the learned fewshot rules, API lookup sequence, JSON field definitions, summary counting rules, and common pitfalls for this task group.
---

# Task Group 003 Support Console SOP

Return only JSON matching the task's `payloads/answer_template.json`. Preserve any order required by the template: ticket payload order for ticket lists, ascending `case_id` for case lists, and requirement-listed order for permission users.

Use the harness-provided base URL when present; otherwise use the support-console API base URL from the task prompt. The useful endpoints are:

- `/api/tickets` and `/api/tickets/<ticket_id>`
- `/api/outages?service_area=<area>`
- `/api/diagnostics/<ticket_id>`
- `/api/troubleshooting/<ticket_id>`
- `/api/cases` and `/api/cases/<case_id>`
- `/api/lines/<line_id>`, `/api/devices/<device_id>`, `/api/plans/<plan_id>`
- `/api/enterprise/incidents/<incident_id>`
- `/api/enterprise/export-runs?incident_id=<incident_id>`
- `/api/enterprise/messages?query=<text>`
- `/api/enterprise/sla/<enterprise_account_id>`

## Residential Ticket Triage

For each ticket from a CSV worklist, query the ticket record first. Use its `service_area` to look up active outages, then query diagnostics and troubleshooting only if the ticket is not already blocked by an outage/account/auth issue.

Decision precedence:

1. If the account id is clearly invalid, the intake says no matching account, or the task text says the account is ineligible/on hold, mark `FAILED`. Use `INVALID_ACCOUNT` where the template has `key_blocker`; use `INELIGIBLE_ACCOUNT` where the template has `resolution_route`.
2. If the ticket/service area has an active outage whose `service_types` include the ticket service type, mark `PENDING_ACTION`, set the outage id, use route `OUTAGE_WAIT` or blocker `ACTIVE_OUTAGE`, set no escalation team, and do not require diagnostics.
3. If the intake or record indicates authentication failed and never recovered, mark `FAILED`, blocker/route `AUTH_FAILED`, no escalation, no diagnostics.
4. If the line/account is suspended for an overdue bill, mark `FAILED`, blocker `OVERDUE_SUSPENSION`, route team `ACCOUNTS_PAYABLE` when that field exists.
5. Otherwise use diagnostics and troubleshooting evidence. Mark diagnostics required/needed for these operational tickets.

Metric flags for ticket-decision templates:

- `latency_issue`: true when diagnostics latency is materially high, especially above about 100 ms.
- `stability_issue`: true when jitter is materially high, especially above about 30 ms, or packet/signal-loss root causes are present.
- `bandwidth_issue`: true when diagnostic bandwidth is materially below the subscribed rate, especially below about 80% of `subscribed_mbps`.
- Leave all three false for outage-wait, account/auth failure, and other cases where diagnostics are not the decision basis.

Escalation and blocker mapping:

- Self-service/config/profile causes that troubleshooting fixes into acceptable post-metrics -> `RESOLVED`, team `NONE`, route `AUTO_TROUBLESHOOTING`, blocker `NONE`.
- Physical fiber/drop/signal-loss causes or unresolved line-test results -> `ESCALATED`, team `FIELD_OPS`, blocker `PHYSICAL_LINE_FAULT` when available.
- Backbone/capacity causes or failed reroute attempts -> `ESCALATED`, team `NETWORK_ENGINEERING`, blocker `NETWORK_CAPACITY`.
- Provisioning stale/mismatch after move -> `ESCALATED`, team `TIER2_SUPPORT`, blocker `PROVISIONING_STALE`.
- Voice profile stale that is fixed by profile refresh -> `RESOLVED`.

Ticket summaries are simple counts over your final decisions. `tickets_requiring_customer_wait` counts outage-wait tickets only. Team counts count final route/escalation teams, not all investigated tickets.

## Mobile Support Queue

For each case, query `/api/cases/<case_id>`, then the referenced line, device, and plan. The task payload's reported issue and customer preferences can override or refine the API evidence.

Primary action rules:

- Line suspended for overdue bill and customer is ready to pay -> `SEND_PAYMENT_REQUEST`; secondary `RESUME_LINE_REBOOT`; route `BILLING_RECOVERY`; fill `bill_id` and overdue charge from available bill/support-console evidence. If no bill applies, leave bill fields empty/0.
- Device `airplane_mode: true` -> `TOGGLE_AIRPLANE_MODE`.
- No service with SIM missing/not seated -> `RESEAT_SIM`.
- Mobile data disabled on the device -> `TOGGLE_MOBILE_DATA`.
- Abroad with phone roaming disabled -> `TOGGLE_ROAMING`, route `SELF_SERVICE` or `DEVICE_SETTING_FIX`.
- Abroad with phone roaming enabled but line `roaming_enabled: false` -> `ENABLE_LINE_ROAMING`; set `carrier_update_required: true`; route `CARRIER_UPDATE`.
- Data used exceeds the plan limit and the payload includes accepted refuel GB -> `REFUEL_DATA`; `data_refuel_gb` is the accepted GB; charge is `accepted_refuel_gb * plan.data_refueling_price_per_gb`; route `DATA_RECOVERY`.
- Slow data with `data_saver_mode: true` -> `TOGGLE_DATA_SAVER`.
- Slow data with old/limited network mode such as `3g_only` -> `SET_NETWORK_MODE`.
- Slow data with VPN connected -> `DISCONNECT_VPN`.
- MMS/photo messaging failure with missing storage permission -> `GRANT_MESSAGING_PERMISSION`, `permission: "storage"`. Missing SMS permission uses `sms`; both missing uses `sms_and_storage`.
- APN/MMSC profile missing or edited -> `RESET_APN_REBOOT`.
- Use `TRANSFER_HUMAN`/`HUMAN_TRANSFER` for fraud, expired contract, SIM lock/security issues, or any case without a safe self-service/carrier/billing operation.

Set `secondary_action` to `NO_ACTION` unless a payment recovery needs `RESUME_LINE_REBOOT`. For non-billing cases, `bill_id` is `""`, `charge_amount_usd` is `0.0`, and `permission` is `NONE`.

Mobile summaries count by final route/action class:

- `self_service_fixes`: final route `SELF_SERVICE`.
- `billing_recoveries`: final route `BILLING_RECOVERY`.
- `carrier_updates`: carrier update route or `carrier_update_required: true`.
- `device_setting_fixes`: final route `DEVICE_SETTING_FIX`.
- `data_refuel_cases`: primary action `REFUEL_DATA`.
- `human_transfers`: final route `HUMAN_TRANSFER`.
- `total_estimated_customer_charge_usd`: sum customer charges, usually only data refuels and billing recovery charges.

## Enterprise Export Complaint Package

Parse the complaint for client name, product, and incident reference. Query the incident, export runs, SLA contract, and messages using the client name and root-cause keywords. Message search may work better with the short client name or terms like credential, alert, archive, backfill, quota, or the product name than with the incident id alone.

Fill fields as follows:

- `incident_id`, `enterprise_account_id`, `severity`, `engineering_owner`, and `account_owner` come from the incident record.
- `failure_window.start_date` and `end_date` are the first and last failed export-run dates for the incident. `failed_days` is the number of failed runs in that consecutive window.
- `backfill_days` usually equals the number of failed export days when evidence confirms the later successful/manual backfill.
- `root_cause_category` is a concise lowercase business phrase from `failure_code` plus message evidence, not the raw enum. Example pattern: stale credential after a rotation when export runs show a stale-credential failure and messages mention an old secret.
- `contributing_alert_issue` is `ARCHIVED_ALERT_ROUTE` when alert evidence was routed to an archive/archived alert channel; use `NONE` when evidence shows no alert-routing issue; use `UNKNOWN` only if evidence is missing.
- `sla_credit_percent` comes from `/api/enterprise/sla/<enterprise_account_id>` when the failure count meets the trigger; otherwise 0.
- `channel_name`: lowercase hyphenated client/legal name, preserving meaningful suffixes like `inc`.
- `evidence_folder`: client name plus failure month/year plus `Investigation`.
- `report_title`: client name plus `Export Failure - Resolution Report`.
- `share_permissions`: include exactly the requested users in listed order. If the requirements give only users and no permissions, use the learned default pairing: first user `view`, second user `edit`; do not add owners unless requested.
- `response_status`: `NEEDS_FINANCE_REVIEW` when an SLA credit is due; `NEEDS_ENGINEERING_REVIEW` when root-cause/backfill evidence is incomplete; `UNDER_INVESTIGATION` when core incident evidence is missing; otherwise `READY_TO_SEND`.

## Formatting Pitfalls

- Match enum spelling exactly, including uppercase values and `Critical`/`High` capitalization for severity.
- Use numeric JSON values, not strings, for charges, GB, counts, percentages, and booleans.
- Use `""` for non-applicable ids, not `null`.
- Keep customer charges rounded to the template precision: one decimal for GB and two decimals for USD, but JSON may display `4.0` rather than `4.00`.
- Do not count diagnostics for outage/account/auth-blocked tickets.
- Do not let noisy diagnostics override an active outage or a clear eligibility/billing blocker.
