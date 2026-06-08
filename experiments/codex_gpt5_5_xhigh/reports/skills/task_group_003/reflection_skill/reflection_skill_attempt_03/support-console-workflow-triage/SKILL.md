---
name: support-console-workflow-triage
description: Use this skill for support-console tasks that ask Codex to resolve telecom service tickets, mobile support cases, mobile data recovery worklists, or enterprise export incident response packages from structured inputs plus a shared local support API. It provides the SOP, API lookup order, field meanings, business rules, and pitfalls needed to produce the required answer.json accurately.
---

# Support Console Workflow Triage

## Operating Rules

- Read the task prompt, payload files, and answer template first. Preserve the requested ordering: payload order for ticket CSVs and ascending `case_id` order for case lists unless the template says otherwise.
- Use the base URL supplied by the harness or prompt. Verify with `/health`, then use `/api/catalog` only for orientation.
- Do not answer from the customer wording alone. Resolve every item from API evidence.
- Return only JSON conforming to the task's `answer_template.json`. Use numeric JSON values for charges and counts, not strings.

## API Lookup SOP

For service tickets:

1. Load each CSV row.
2. Query `/api/tickets/<ticket_id>` for account, service area, service type, subscription, and summary.
3. Query `/api/outages?service_area=<service_area>` and apply only active outages whose `service_types` include the ticket's service type.
4. If there is no active matching outage and no obvious account/auth blocker, query `/api/diagnostics/<ticket_id>` and `/api/troubleshooting/<ticket_id>`.

For mobile cases:

1. Query `/api/cases/<case_id>`.
2. Query `/api/lines/<line_id>`.
3. Query `/api/devices/<device_id>` from the case/line.
4. Query `/api/plans/<plan_id>` for data limit and refuel price.
5. If a billing recovery requires `bill_id` or `charge_amount_usd`, copy those from billing evidence exposed by the task/API. Do not compute overdue balances from the plan monthly price.

For enterprise incidents:

1. Parse the complaint for client, product, and incident reference.
2. Query `/api/enterprise/incidents/<incident_id>`.
3. Query `/api/enterprise/export-runs?incident_id=<incident_id>`.
4. Query `/api/enterprise/messages?query=<client or owner or root-cause term>` several ways; short client names often work better than full sentences.
5. Query `/api/enterprise/sla/<enterprise_account_id>`.

## Service Ticket Rules

- Active matching outage: `final_resolution_status` is `PENDING_ACTION`; route is `OUTAGE_WAIT` or blocker is `ACTIVE_OUTAGE`; set team to `NONE`, diagnostic fields false, and include `outage_id`.
- Invalid account, auth failure, or ineligible account hold: `final_resolution_status` is `FAILED`; diagnostics are not required; diagnostic issue flags are false.
- In same-day batch templates, `INELIGIBLE_ACCOUNT` uses `escalation_team: NONE`; do not mark `ACCOUNTS_PAYABLE` unless the template has a route-team/key-blocker style field for overdue suspension.
- Overdue suspension in queue-quality templates: `key_blocker: OVERDUE_SUSPENSION`, `route_team: ACCOUNTS_PAYABLE`, and `final_resolution_status: FAILED`.
- Auth failures use `key_blocker: AUTH_FAILED` with `route_team: NONE` unless explicit evidence says a human escalation is required.
- Technical diagnostics are required for non-outage resolved/escalated faults. Mark issue booleans from pre-troubleshooting diagnostics: high latency, high jitter/stability problems, and bandwidth materially below subscribed speed.
- Configuration/profile refreshes that materially recover service are `RESOLVED` with no route team.
- Physical line damage, fiber drop damage, signal loss after line work, or similar plant faults escalate to `FIELD_OPS`.
- Backbone/capacity faults escalate to `NETWORK_ENGINEERING`.
- Stale provisioning after a move or account/service mismatch escalates to `TIER2_SUPPORT`.
- Count summaries directly from per-item decisions after all rows are final.

## Mobile Case Rules

- Always decide from line status first, then device settings, then plan/data usage.
- Suspended for overdue billing: `primary_action: SEND_PAYMENT_REQUEST`, `secondary_action: RESUME_LINE_REBOOT`, `final_route: BILLING_RECOVERY`, and charge/bill fields from billing evidence.
- Missing SIM or no-service with `sim_status: missing`: `RESEAT_SIM`, usually `SELF_SERVICE`.
- Airplane mode on: `TOGGLE_AIRPLANE_MODE`.
- Carrier line roaming enabled but phone roaming disabled while abroad: `TOGGLE_ROAMING`, self-service.
- Phone roaming enabled but carrier line roaming disabled while abroad: `ENABLE_LINE_ROAMING`, `carrier_update_required: true`, route `CARRIER_UPDATE`.
- MMS/photo messaging failures: missing SMS/storage permission means `GRANT_MESSAGING_PERMISSION` with `permission` set to `sms`, `storage`, or `sms_and_storage`; APN/MMSC profile problems point to `RESET_APN_REBOOT`.
- Data over plan limit with accepted refuel: `REFUEL_DATA`; `data_refuel_gb` is the accepted amount; charge is `accepted_refuel_gb * data_refueling_price_per_gb`; route `DATA_RECOVERY`.
- `mobile_data_enabled: false`: `TOGGLE_MOBILE_DATA`.
- `data_saver_mode: true`: `TOGGLE_DATA_SAVER`.
- Old/limited network mode such as `3g_only`: `SET_NETWORK_MODE`.
- `vpn_connected: true` with slow data: `DISCONNECT_VPN`.
- Use `secondary_action: NO_ACTION` unless the workflow explicitly requires a follow-up, such as resume-line after payment.
- For mobile-data worklists, summarize by final route category: data refuel, carrier update, device setting fix, and human transfer.

## Enterprise Response Rules

- Failure window is the consecutive set of failed export run dates for the incident. Use first failed date, last failed date, and count of failed days.
- `backfill_days` equals the number of failed export days requiring manual backfill unless evidence states a different number.
- Normalize root cause into a concise phrase from failure codes plus messages. Example pattern: stale credential after rotation, quota exceeded, scheduler stale secret. Avoid verbose sentence-style causes.
- `contributing_alert_issue` is `ARCHIVED_ALERT_ROUTE` when message/channel evidence shows the alert path is archived or not actively routed; otherwise use `NONE` unless evidence is unclear.
- SLA credit comes from the SLA endpoint or account escalation evidence. Do not invent percentages.
- If an SLA credit is due and there is no explicit finance approval, set `response_status: NEEDS_FINANCE_REVIEW` even when engineering cause and owners are known.
- Use `NEEDS_ENGINEERING_REVIEW` when root cause or remediation evidence is missing; use `UNDER_INVESTIGATION` when the incident lacks enough evidence for a client package.
- Artifact names follow `response_requirements.json` literally:
  - Lowercase hyphen channel means normalize the legal client name, including suffixes such as `inc`, not the product name.
  - Investigation folder should be human-readable with client name, month/year, and `Investigation`.
  - Report title should be client name plus export failure/resolution wording when requested.
- Preserve `share_permissions` user order from requirements. If only two permission users are listed and no role evidence is supplied, use first `view`, second `edit`.

## Common Pitfalls

- Do not let generated/noise diagnostics override a matching active outage or an account blocker.
- Do not set issue booleans true for outage-wait or account-failed tickets just because diagnostics exist.
- Do not route same-day ineligible accounts to `ACCOUNTS_PAYABLE`; that team is for overdue-suspension queue classifications.
- Do not use plan monthly price as a bill amount. Billing recovery amount must be copied from bill evidence.
- Do not mark enterprise SLA-credit responses as ready to send before finance review.
- Do not over-specify root-cause text; concise normalized categories match better than long explanations.
