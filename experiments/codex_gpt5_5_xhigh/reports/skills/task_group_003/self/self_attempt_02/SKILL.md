---
name: crm-service-ticket-sop
description: Resolve CRM support-console service tickets, mobile cases, fixed-service queue quality reviews, and enterprise export complaints into strict JSON answer templates using staged payloads plus support-console evidence.
---

# CRM Service-Ticket SOP

Use this skill for tasks that provide a support-console base URL, payload files, and an `answer_template.json` requiring ticket/case decisions, queue summaries, or enterprise response fields.

## Source Discipline

- Use only the prompt payloads, the answer template, `environment_access.md` when present, and the remote support-console records. Do not inspect answer files, judge endpoints, evaluator notes, local environment source, or other attempt folders.
- Prefer the harness/prompt base URL. If it gives a localhost default but `environment_access.md` gives a remote URL, use the remote URL.
- Return only JSON conforming to the template. No Markdown, comments, extra fields, or omitted required fields.

## Console Lookup Pattern

Start with `GET /health`. Useful console routes:

- `GET /api/search?q=<id-or-keyword>`: best general lookup. It returns matching records from collections such as `diagnostics`, `troubleshooting`, `enterprise_incidents`, `export_runs`, `messages`, and `sla_contracts`.
- `GET /api/accounts`, `/api/tickets`, `/api/outages`: fixed-service accounts, tickets, and active outage records.
- `GET /api/cases`, `/api/customers`, `/api/lines`, `/api/devices`, `/api/bills`, `/api/plans`: mobile case evidence.
- Detail lookups may work for direct resources such as `/api/accounts/<account_id>` and `/api/tickets/<ticket_id>`, but search is more reliable for joined evidence.

For every payload item, gather the intake row plus all linked records by the primary ID and relevant account/customer/line/device IDs. Do not decide from the intake text alone when console records disagree.

## Output Conventions

- Preserve the order required by the template: payload order unless it says ascending `case_id`.
- Use exact enum spellings from `answer_template.json`.
- Use `""` for non-applicable string IDs, `NONE` for non-applicable enum fields, `0.0`/`0.00` for non-applicable numeric fields, and real booleans for boolean fields.
- Format money and required two-decimal numbers as numeric values with two decimals when serializing. Do not include currency symbols.
- After building decisions, recompute summary counts from the decisions, not from memory. Count only the requested fields and exact enum names.

## Fixed-Service Tickets

Evidence to collect: ticket, account, active outage for matching `service_area` and `service_type`, diagnostics, and troubleshooting/post-checks.

Decision priority:

1. Invalid or missing account: `FAILED`, blocker `INVALID_ACCOUNT`, team `NONE`, route `INVALID_ACCOUNT`, no outage.
2. Account authentication failure (`last_login_status` or recovery status failure): `FAILED`, blocker/route `AUTH_FAILED`, team `NONE`.
3. Suspended/account hold: route to billing/accounts payable. For quality templates use `PENDING_ACTION`, `ACCOUNTS_PAYABLE`, blocker `OVERDUE_SUSPENSION` or the specific suspension reason. For route templates use `INELIGIBLE_ACCOUNT` when the template does not expose a billing recovery route.
4. Active outage matching service area and service type: `PENDING_ACTION`, route `OUTAGE_WAIT`, outage ID populated, team `NONE`, customer wait count increments.
5. Physical line signal issues (`FIBER_DROP_DAMAGE`, `SIGNAL_LOSS`, similar): `ESCALATED`, `FIELD_OPS`, blocker `PHYSICAL_LINE_FAULT`.
6. Backbone/capacity issues (`BACKBONE_CAPACITY`, regional backbone loss): `ESCALATED`, `NETWORK_ENGINEERING`, blocker `NETWORK_CAPACITY`.
7. Stale provisioning or profile issues:
   - `VOICE_PROFILE_STALE`, profile refresh, provisioning sync, configuration drift, or successful troubleshooting/post metrics: usually `RESOLVED`, route `AUTO_TROUBLESHOOTING`, team `NONE`.
   - If the template treats stale provisioning as a handoff blocker and post-checks do not prove recovery, use `ESCALATED`, `TIER2_SUPPORT`, blocker `PROVISIONING_STALE`.
8. Otherwise use the diagnostic/post-check evidence: materially improved latency/jitter/bandwidth after troubleshooting means `RESOLVED`; persistent poor metrics with no known field/capacity cause usually goes to `TIER2_SUPPORT`.

Diagnostic flags:

- `diagnostic_needed`/`diagnostic_required` is true when diagnostics were required to classify or validate the ticket, especially active technical tickets and escalations. It is false for invalid account/auth/billing-only blocks when the account state alone decides the route.
- `latency_issue` from high latency, `stability_issue` from high jitter/packet loss/intermittency/signal loss, and `bandwidth_issue` from bandwidth well below subscribed Mbps or explicit slow-speed evidence.

## Mobile Queue Cases

Join each case to customer, line, bill, device, and plan. The action is driven by the first concrete blocker:

- `airplane_mode: true`: `TOGGLE_AIRPLANE_MODE`, self service.
- `sim_status` missing/unseated: `RESEAT_SIM`, self service. Locked SIM/PIN or hardware/security problems go `TRANSFER_HUMAN`.
- Line suspended for `OVERDUE_BILL` with overdue bill: `SEND_PAYMENT_REQUEST` then `RESUME_LINE_REBOOT`, set `bill_id`, `charge_amount_usd` to amount due, route `BILLING_RECOVERY`.
- Line suspended for contract ended, fraud, or non-billing reason: `TRANSFER_HUMAN`, route `HUMAN_TRANSFER`.
- Abroad with phone roaming on but line roaming disabled: `ENABLE_LINE_ROAMING`, carrier update required where present, route `CARRIER_UPDATE`.
- Abroad with phone roaming off: `TOGGLE_ROAMING` first; if carrier/line roaming also disabled, secondary `ENABLE_LINE_ROAMING`.
- `mobile_data_enabled: false`: `TOGGLE_MOBILE_DATA`, route `DEVICE_SETTING_FIX` or `SELF_SERVICE`.
- Data used exceeds plan limit and customer accepts refuel: `REFUEL_DATA`, `data_refuel_gb` from preference, charge = GB * plan refuel price, route `DATA_RECOVERY`.
- `data_saver_mode: true`: `TOGGLE_DATA_SAVER`, route `DEVICE_SETTING_FIX`.
- `network_mode_preference` stuck on old mode such as `3g_only`: `SET_NETWORK_MODE`, route `DEVICE_SETTING_FIX`.
- `vpn_connected: true` with slow data: `DISCONNECT_VPN`, self service/device setting fix.
- MMS/photo send failures:
  - Missing storage and/or SMS permission: `GRANT_MESSAGING_PERMISSION`, set `permission` to `storage`, `sms`, or `sms_and_storage`.
  - Missing APN/MMSC configuration: `RESET_APN_REBOOT`.
  - Wi-Fi calling issue: `TOGGLE_WIFI_CALLING`.
- If no actionable evidence exists, use `TRANSFER_HUMAN` rather than inventing a fix.

Mobile summaries count final routes exactly (`SELF_SERVICE`/`DEVICE_SETTING_FIX`, billing recoveries, carrier updates, human transfers) and sum only customer charges that the output actually applies.

## Enterprise Export Complaints

Use the complaint text to identify the client, product, and incident hint, then search by incident ID, enterprise account ID, client name, failure code, and owner/message keywords.

Fields:

- `incident_id`, `enterprise_account_id`, `severity`, `engineering_owner`, and `account_owner` come from the incident/account records.
- `failure_window.start_date` and `end_date` are the first and last consecutive failed export `run_date`s for the incident; `failed_days` is the count of failed runs in that window.
- `backfill_days` usually equals the failed-day count unless a message gives a different manual backfill count.
- `root_cause_category` should be a concise category from failure codes plus messages, such as stale credential/old secret, quota exhaustion, or scheduler configuration.
- `contributing_alert_issue` is `ARCHIVED_ALERT_ROUTE` when the relevant alert/message lives in an archive channel or shows the alert was routed away from the active response path; otherwise `NONE`, or `UNKNOWN` if evidence is insufficient.
- `sla_credit_percent` comes from the SLA contract or account-escalation message, not from severity alone.
- Build required artifacts from the response requirements: lowercase hyphen channel name, client-date investigation folder, and a client export failure report title.
- `share_permissions` must include exactly the required users in the required order. Give finance/account reviewers `view` unless the requirement states edit/upload; give engineering collaborators `edit` when they must complete evidence.
- `response_status` is `READY_TO_SEND` only when root cause, recovery/backfill, SLA credit, owners, and artifacts are all supported. Use the specific review/under-investigation status when evidence is missing.

## Pitfalls

- Active outage beats diagnostic noise. Match both service area and service type before assigning `OUTAGE_WAIT`.
- Generated/noise root causes are not real blockers; rely on account state, outage match, known root-cause codes, and post-troubleshooting metrics.
- Do not count a suspended or invalid account as a technical outage or diagnostic escalation.
- Do not confuse device roaming with carrier/line roaming: phone roaming is a device toggle; line roaming disabled requires a carrier update.
- Do not include stale IDs from non-payload records just because search returns shared records. Use records linked to the staged IDs or the identified enterprise account/incident.
- Always audit that every payload item has one decision and every decision contributes to exactly the summary buckets requested by the template.
