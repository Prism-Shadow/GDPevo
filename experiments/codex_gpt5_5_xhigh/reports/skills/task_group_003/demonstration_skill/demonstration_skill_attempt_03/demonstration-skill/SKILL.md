---
name: demonstration-skill
description: Use this for task_group_003 support-console tasks involving wireline service tickets, mobile support cases, or enterprise export incidents. It gives API lookup steps, routing rules, output-field meanings, and pitfalls learned from training inputs and answers.
---

# Task Group 003 Support Console

## Operating Rules

Use the base URL supplied by the task or harness. Check `/health` and `/api/catalog` if unsure. Do not answer from the prompt text alone: for every ticket, case, line, device, plan, outage, incident, export run, SLA, or message, query the support-console API and let the records decide.

Always start from `payloads/answer_template.json` and return only JSON in that shape. Preserve the ordering requested by the template: ticket payload order, case ascending order, and share-permission user order from the requirements file. Summaries are simple counts/totals over the decisions you output.

## Wireline Ticket Workflow

For each ticket from a CSV:

1. Fetch `/api/tickets/<ticket_id>`.
2. If the account looks invalid or unmatched, mark `FAILED`, no diagnostic, no team, blocker/route `INVALID_ACCOUNT`.
3. If the record indicates authentication failure, mark `FAILED`, no diagnostic, route/blocker `AUTH_FAILED`.
4. If the customer is suspended/on account hold for overdue payment, mark `FAILED`, no diagnostic. Use `INELIGIBLE_ACCOUNT` for batch routes; use `OVERDUE_SUSPENSION` and `ACCOUNTS_PAYABLE` when the template has queue blockers/teams.
5. Query `/api/outages?service_area=<service_area>`. If an active outage covers the ticket service type, mark `PENDING_ACTION`, `OUTAGE_WAIT` or blocker `ACTIVE_OUTAGE`, include the `outage_id` if the template asks, and do not require diagnostics.
6. Otherwise fetch `/api/diagnostics/<ticket_id>` and `/api/troubleshooting/<ticket_id>`. Set diagnostic flags from the evidence:
   - `latency_issue`: high latency, usually above about 100 ms.
   - `stability_issue`: high jitter, packet/signal instability, or signal-loss root cause.
   - `bandwidth_issue`: measured bandwidth materially below subscription, roughly below 80 percent.
7. Route by durable root cause and post-troubleshooting result:
   - Self-service/config/profile issues that improve after troubleshooting: `RESOLVED`, `AUTO_TROUBLESHOOTING`, team `NONE`.
   - Physical line/fiber/signal damage: `ESCALATED`, team `FIELD_OPS`, blocker `PHYSICAL_LINE_FAULT`.
   - Backbone/capacity/congestion: `ESCALATED`, team `NETWORK_ENGINEERING`, blocker `NETWORK_CAPACITY`.
   - Stale provisioning/profile mismatch needing manual correction: `ESCALATED`, team `TIER2_SUPPORT`, blocker `PROVISIONING_STALE`.

Common pitfall: diagnostics may contain generated noise for tickets whose true blocker is outage, invalid account, auth failure, or billing suspension. Apply hard blockers and outage checks before interpreting diagnostic metrics.

## Mobile Case Workflow

For each case:

1. Fetch `/api/cases/<case_id>`, then `/api/lines/<line_id>`, `/api/devices/<device_id>`, and `/api/plans/<plan_id>`.
2. Apply blockers before device toggles:
   - Overdue suspended line: `SEND_PAYMENT_REQUEST`, secondary `RESUME_LINE_REBOOT`, route `BILLING_RECOVERY`. Fill bill id and amount only from an allowed billing record or payload evidence; otherwise do not invent bill data.
   - Fraud, ended contract, locked SIM/PUK, or unsafe account state: `TRANSFER_HUMAN`, route `HUMAN_TRANSFER`.
3. For no-service cases:
   - `airplane_mode=true`: `TOGGLE_AIRPLANE_MODE`.
   - `sim_status=missing`: `RESEAT_SIM`.
   - active line but device roaming off while abroad: `TOGGLE_ROAMING`.
4. For MMS/photo messaging:
   - Missing `sms` or `storage` permission: `GRANT_MESSAGING_PERMISSION`; set `permission` to `sms`, `storage`, or `sms_and_storage`.
   - Missing MMSC/APN evidence: `RESET_APN_REBOOT`.
5. For no-data/mobile-data cases:
   - `mobile_data_enabled=false`: `TOGGLE_MOBILE_DATA`.
   - Abroad with phone roaming on but line roaming disabled: `ENABLE_LINE_ROAMING`, `carrier_update_required=true`, route `CARRIER_UPDATE`.
   - Data used at or over plan limit and customer accepted a refuel: `REFUEL_DATA`; `data_refuel_gb` is the accepted amount and `charge_amount_usd = gb * plan.data_refueling_price_per_gb`.
6. For slow-data cases:
   - `data_saver_mode=true`: `TOGGLE_DATA_SAVER`.
   - network mode limited to an older mode such as 3G: `SET_NETWORK_MODE`.
   - `vpn_connected=true`: `DISCONNECT_VPN`.

Use `NO_ACTION` only when records show no actionable mismatch. For contact-center templates, summarize by `final_route` values (`SELF_SERVICE`, `BILLING_RECOVERY`, `CARRIER_UPDATE`, `HUMAN_TRANSFER`). For mobile-data worklists, summarize refuel cases, carrier updates, device-setting fixes, human transfers, and total estimated customer charge.

## Enterprise Export Complaint Workflow

From the complaint and requirements:

1. Identify the incident id/client/product from the email, then fetch `/api/enterprise/incidents/<incident_id>`.
2. Fetch `/api/enterprise/export-runs?incident_id=<incident_id>`. The failed window is the contiguous failed run dates relevant to the complaint: start date, end date, and failed-day count. `backfill_days` normally equals failed days unless message evidence gives a different manual backfill count.
3. Fetch `/api/enterprise/sla/<enterprise_account_id>`. Apply the SLA credit only when its trigger condition is met by the export-run evidence.
4. Search `/api/enterprise/messages?query=<text>` with the incident id, concise client/product words, failure code words, owner names, and root-cause terms. Message search is keyword-sensitive; short terms work better than full sentences.
5. Infer fields:
   - `root_cause_category`: concise lower-case phrase from failure code plus message evidence, not just the raw enum.
   - `contributing_alert_issue`: `ARCHIVED_ALERT_ROUTE` when alert/root-cause evidence lives in an archived alert channel or archived route; `NONE` when evidence shows normal routing; `UNKNOWN` when message evidence is missing.
   - owners and severity come from the incident record.
   - `channel_name`: client name lowercased, punctuation removed, spaces to hyphens.
   - `evidence_folder`: `<Client Name> <Month YYYY> Investigation`, using the failed-window month.
   - `report_title`: `<Client Name> Export Failure - Resolution Report`.
   - `share_permissions`: preserve required user order. If only users are supplied and no explicit permissions, use the collaboration convention from training: first user `view`, second user `edit`.
6. Set `response_status` as package readiness, not a direct copy of incident status:
   - Missing root cause or failure window: `UNDER_INVESTIGATION`.
   - SLA credit applies: `NEEDS_FINANCE_REVIEW`.
   - Engineering evidence/backfill is incomplete but finance is not the blocker: `NEEDS_ENGINEERING_REVIEW`.
   - All evidence and required artifacts are complete with no review blocker: `READY_TO_SEND`.

## Field Reminders

- Ticket `account_id`, case `customer_id`, and case `line_id` are copied from API records, not inferred from the input text when a record exists.
- `diagnostic_needed`/`diagnostic_required` is true only when diagnostics are part of deciding a technical resolution or escalation. It is false for outage waits, invalid accounts, auth failures, and billing/account blockers.
- `secondary_action` is usually `NO_ACTION`; use it only for a required paired operation such as payment followed by line resume/reboot.
- `permission` is `NONE` except for messaging-permission fixes.
- `bill_id`, `outage_id`, and artifact names are empty only when not applicable or not supported by evidence.
- Summary fields are derived from the emitted decisions; recalculate them after finalizing every row.

## Output Hygiene

Use exact enum spellings from the answer template. Empty strings mean "not applicable"; numeric zeroes should be `0.0` or `0.00`-equivalent JSON numbers as requested by the template. Do not add explanatory fields, comments, markdown, or prose.
