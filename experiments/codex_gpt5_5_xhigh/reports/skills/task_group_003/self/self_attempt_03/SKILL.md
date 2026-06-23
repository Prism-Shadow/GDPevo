---
name: crm-support-ticket-sop
description: Use this skill whenever a task asks Codex to resolve CRM, service-ticket, mobile support, contact-center, queue-quality, or enterprise export-complaint cases from payload files plus a shared support-console API. It gives the lookup workflow, strict JSON output conventions, routing and action rules, summary-count habits, and pitfalls for support-console evidence tasks.
---

# CRM Support Ticket SOP

Use this skill for support-console tasks where the prompt provides a payload file and an `answer_template.json`. The goal is not to write a narrative; it is to return the exact JSON object requested by the template using console evidence.

## Evidence Workflow

1. Read the prompt, payload files, and answer template first. The template controls field names, enum spellings, ordering, empty-value conventions, and summaries.
2. Use the support-console base URL from the prompt or harness. If an `environment_access.md` file is provided, prefer its `GDPEVO_ENV_BASE_URL`. Check `/health` before bulk lookups.
3. Use the remote console API only. Do not start a local service or inspect local environment source.
4. The API paths are usually under `/api`:
   - Wired service tickets: `GET /api/tickets/{ticket_id}`, `GET /api/accounts/{account_id}`, `GET /api/diagnostics/{ticket_id}`, `GET /api/outages?service_area={service_area}`.
   - Mobile queues: `GET /api/cases/{case_id}`, `GET /api/customers/{customer_id}`, `GET /api/lines/{line_id}`, `GET /api/devices/{device_id}`, `GET /api/bills?customer_id={customer_id}`, `GET /api/plans/{plan_id}`.
   - Enterprise export incidents: `GET /api/enterprise/incidents/{incident_id}`, `GET /api/enterprise/accounts/{enterprise_account_id}`, `GET /api/enterprise/export-runs?incident_id={incident_id}`, `GET /api/enterprise/messages?incident_id={incident_id}`.
5. Treat `{"error":"not_found"}` as evidence that the record is absent. Do not silently substitute a similarly named record.
6. Keep a small evidence table while working: input id, fetched ids, decisive evidence, final enum choices. This prevents summary-count drift.

## Output Conventions

Return only JSON conforming to the answer template. Do not add prose, markdown, comments, or extra fields.

- Preserve the requested order: payload order for ticket batches; ascending `case_id` when the template says so; listed order for required permission users.
- Use exact enum spelling and casing. Use `NONE`, `NO_ACTION`, empty string, `false`, or `0.00` only as the template specifies.
- For numeric money fields, emit two decimal places when writing the JSON text; for GB fields that request one decimal, emit one decimal.
- Count summaries from the final decision objects after all routing is settled. Count route/team enums only when the decision uses that route/team, and do not count `NONE`.
- If the template includes both per-item decisions and a summary, finish per-item decisions first, then recompute every summary field directly from them.

## Wired Service-Ticket Rules

Fetch the ticket, account, active outages for the ticket service area, and diagnostics. Classify in this priority order so noisy diagnostics do not override a hard blocker:

1. Missing ticket or missing account: `FAILED`; route/blocker `INVALID_ACCOUNT`; no escalation team; diagnostic not required.
2. Account status is not active: usually `PENDING_ACTION`; route `INELIGIBLE_ACCOUNT` or blocker `OVERDUE_SUSPENSION`/`FRAUD_SUSPENSION`; team `ACCOUNTS_PAYABLE` for overdue/account-hold cases. Do not diagnose a suspended account as a network fault.
3. Authentication failure or unrecovered account recovery: `FAILED`; route/blocker `AUTH_FAILED`; usually route to `TIER2_SUPPORT` if a team field is required.
4. Active outage matching the ticket service type: `PENDING_ACTION`; route `OUTAGE_WAIT`; blocker `ACTIVE_OUTAGE`; include the `outage_id`; no escalation team. Count customer-wait tickets for outage waits, not for every pending action.
5. Diagnostics-driven resolution or escalation:
   - `CONFIGURATION_DRIFT` or similar customer/service configuration drift: `RESOLVED`, route `AUTO_TROUBLESHOOTING`, team `NONE`.
   - `FIBER_DROP_DAMAGE`, `SIGNAL_LOSS`, physical drop, or line-work damage: `ESCALATED`, team `FIELD_OPS`, blocker `PHYSICAL_LINE_FAULT`.
   - `BACKBONE_CAPACITY`, congestion, or capacity faults: `ESCALATED`, team `NETWORK_ENGINEERING`, blocker `NETWORK_CAPACITY`.
   - `PROVISIONING_STALE`, `VOICE_PROFILE_STALE`, stale profile, or move/provisioning mismatch: `ESCALATED`, team `TIER2_SUPPORT`, blocker `PROVISIONING_STALE`.
   - Unknown but materially bad diagnostics on an otherwise active, non-outage account: escalate to `TIER2_SUPPORT` rather than inventing an outage.

Diagnostic flags are evidence fields, not routing priorities. Set them from measurements when diagnostics exist:

- `latency_issue`: high latency, packet-loss/latency root cause, or latency roughly at or above 100 ms.
- `stability_issue`: high jitter, packet loss, signal loss, intermittent service, or jitter roughly at or above 30 ms.
- `bandwidth_issue`: measured bandwidth materially below subscription, commonly below about 80 percent of subscribed Mbps.
- `diagnostic_needed`/`diagnostic_required`: true when diagnostics are what decides the outcome; false for invalid account, suspension, auth failure, and active outage decisions.

## Mobile Support Rules

For each case, fetch the case, customer, line, device, bills, and plan. The line identifies the customer, device, plan, suspension state, roaming entitlement, and data usage; the device identifies the user-side setting.

Choose the first decisive action in this priority order:

1. Missing case, line, device, or ambiguous evidence: `TRANSFER_HUMAN` with route `HUMAN_TRANSFER`.
2. Suspended line for overdue bill: primary `SEND_PAYMENT_REQUEST`, secondary `RESUME_LINE_REBOOT`, include the overdue `bill_id`, set charge to the overdue amount, route `BILLING_RECOVERY`.
3. Airplane mode enabled: `TOGGLE_AIRPLANE_MODE`.
4. SIM missing/not active with no service: `RESEAT_SIM`.
5. Mobile data disabled: `TOGGLE_MOBILE_DATA`.
6. Abroad or roaming issue:
   - Carrier/line roaming disabled: `ENABLE_LINE_ROAMING`, route `CARRIER_UPDATE`, and set carrier-update flags true when present.
   - Phone roaming disabled while line roaming is enabled: `TOGGLE_ROAMING`, a device/self-service fix.
7. Data usage over the plan limit with accepted refuel: `REFUEL_DATA`; refuel GB comes from customer preference or the requested amount; charge is `GB * plan.data_refueling_price_per_gb`.
8. Slow data with data saver enabled: `TOGGLE_DATA_SAVER`.
9. Slow data with old network mode such as `3g_only`: `SET_NETWORK_MODE`.
10. Slow data with VPN connected: `DISCONNECT_VPN`.
11. MMS/photo messaging failure:
    - Missing `sms` and/or `storage` permission: `GRANT_MESSAGING_PERMISSION`; set `permission` to `sms`, `storage`, or `sms_and_storage`.
    - APN/MMSC configuration missing while permissions are fine: `RESET_APN_REBOOT`.
12. Wi-Fi-calling-specific voice issue with Wi-Fi calling disabled: `TOGGLE_WIFI_CALLING`.
13. If no listed operation fits, use `TRANSFER_HUMAN`; do not force a self-service action.

Use `NO_ACTION` as the secondary action unless the workflow truly requires a second operation, such as resuming a line after payment. Map final routes to the template vocabulary: device toggles and permissions are `SELF_SERVICE` or `DEVICE_SETTING_FIX`; refuels are `DATA_RECOVERY` when available; carrier-side line changes are `CARRIER_UPDATE`; overdue recovery is `BILLING_RECOVERY`; unresolved/ambiguous cases are `HUMAN_TRANSFER`.

## Enterprise Export Complaint Rules

Extract the incident reference, client, and product from the complaint, then fetch the incident, enterprise account, export runs, and messages. Enterprise message endpoints may include unrelated generated or other-client messages; filter by client, incident, product, dates, authors, and content.

- `failure_window`: use consecutive failed export `run_date` values for the relevant incident. `start_date` is the first failed day, `end_date` is the last failed day, and `failed_days` is the count of failed runs. Do not include the later successful recovery run in the failure window.
- `backfill_days`: usually equals failed days unless a specific backfill record or relevant message says otherwise.
- `root_cause_category`: synthesize a concise category from repeated failure codes and relevant engineering messages, such as stale credential, scheduler secret mismatch, quota exhaustion, or storage failure. Avoid generic labels when evidence is specific.
- `contributing_alert_issue`: set `ARCHIVED_ALERT_ROUTE` when relevant alert evidence was posted only to an archive/archived alert channel; `NONE` when alert routing was normal; `UNKNOWN` when there is no alert evidence.
- SLA credit comes from relevant contract/account-escalation evidence. If the credit is missing or uncertain, use a finance-review response status instead of guessing.
- Owners come from incident/account records: engineering owner from incident, account owner from incident or enterprise account, finance owner from account if needed for credit review.
- `severity` preserves incident casing exactly, such as `Critical`.
- Names and artifacts follow the requirements file. For lowercase-hyphen channel names, slug the client/product/incident words. For investigation folders, include the client slug plus the relevant date in `YYYY-MM-DD`. For report titles, use a clean client export failure title.
- `share_permissions` must include exactly the required users in the required order. Apply least privilege: finance/account reviewers usually get `view`, active editors get `edit`, and evidence upload-only contributors get `upload_only` when the requirement or role implies that.
- `response_status` is `READY_TO_SEND` only when root cause, window, backfill, SLA credit, owners, and artifacts are all supported. Use `NEEDS_FINANCE_REVIEW`, `NEEDS_ENGINEERING_REVIEW`, or `UNDER_INVESTIGATION` for missing or unresolved evidence.

## Common Pitfalls

- Do not copy a train answer or assume one exists. Resolve from payload plus console records.
- Do not let generated noise root causes or unrelated generated messages drive the answer.
- Do not let diagnostics override invalid accounts, suspensions, auth failures, or active outages.
- Do not count active outages unless the outage service types include the ticket service type.
- Do not forget bill/refuel charges: overdue bill amounts and data-refuel prices come from records, not from the customer wording alone.
- Do not reorder outputs for convenience when the template says to preserve payload order.
- Before finalizing, validate JSON syntax mentally or with a parser, then recheck every enum, empty string, decimal, and summary count.
