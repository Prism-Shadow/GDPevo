---
name: support-console-resolver
description: Use this skill whenever a task asks you to resolve support-console work from a shared API and local payloads, including offline service tickets, queue-quality SLA handoff classifications, mobile/contact-center case decisions, mobile-data recovery worklists, or enterprise export/SLA complaint response packages. It guides API evidence gathering, support decision precedence, charge/SLA calculations, summary counts, and strict answer-template JSON output.
---

# Support Console Resolver

Use this skill for support-console tasks where the prompt provides local payload files plus a `<TASK_ENV_BASE_URL>` API. The task is usually graded by exact JSON structure, so treat the answer template and API records as the source of truth.

## Output Discipline

1. Read the prompt, `payloads/answer_template.json`, and every payload file.
2. Return only JSON, with no Markdown, comments, or explanatory text.
3. Match the template exactly: keep required keys, enum spelling, empty strings for missing IDs, `0.0`/`0.00`-style numeric values as JSON numbers, and no extra fields.
4. Preserve the order the template/prompt requests. Ticket CSV tasks usually preserve payload order; mobile case tasks often request ascending `case_id`.
5. Count summaries from the decisions you actually output. Do not count API records that are not in the payload.
6. Prefer direct API evidence over issue wording. Use the issue text only to disambiguate between evidence-supported actions.

## API Collection Pattern

Use the base URL from the prompt/environment note. Typical GETs:

- `GET /api/search?q=<id-or-name>` to locate cases, accounts, clients, messages, and related records when direct endpoints are unavailable.
- Tickets: `/api/tickets/{ticket_id}`, `/api/diagnostics/{ticket_id}`, `/api/troubleshooting/{ticket_id}`, `/api/outages`, plus `/api/search?q=<account_id>` for account status/auth.
- Mobile cases: search each `case_id`, then fetch `/api/customers/{customer_id}`, `/api/lines/{line_id}`, `/api/devices/{device_id}`, `/api/plans/{plan_id}`, and filter `/api/bills` by `customer_id`.
- Enterprise complaints: `/api/enterprise/accounts`, `/api/enterprise/incidents`, `/api/enterprise/export-runs`, `/api/enterprise/messages`, and `/api/enterprise/sla/{enterprise_account_id}`.

If a direct cases endpoint name differs from the environment note, use `/api/search?q=<case_id>`; the search result includes the case record without relying on endpoint aliases.

## Fixed-Service Ticket Decisions

For each ticket row, gather ticket, account search result, active outage match, diagnostic, and troubleshooting records. Apply this precedence:

1. **Invalid account**: if no account record exists for the payload/ticket `account_id`, mark the ticket failed. Use `INVALID_ACCOUNT` when the template has `key_blocker`; use `INVALID_ACCOUNT` or `INELIGIBLE_ACCOUNT` when the template has `resolution_route`, based on the enum available. No diagnostic is required.
2. **Account ineligible/suspended**: if account status is not active, do not run service recovery. For key-blocker templates, map overdue or hold language to `OVERDUE_SUSPENSION` and route to `ACCOUNTS_PAYABLE` when that route field exists; map fraud language to `FRAUD_SUSPENSION`. For route-only templates, use `FAILED` with `INELIGIBLE_ACCOUNT`. No diagnostic is required.
3. **Authentication failure**: if account authentication shows failed login/recovery, use `FAILED` with `AUTH_FAILED`. No diagnostic is required.
4. **Active outage**: if an outage is `active: true`, its `service_area` matches the ticket, and the ticket `service_type` is included in outage `service_types`, use `PENDING_ACTION`, `ACTIVE_OUTAGE`/`OUTAGE_WAIT`, no escalation team, no diagnostic, and the outage ID. This is a customer-wait case.
5. **Diagnostics/troubleshooting**: otherwise set diagnostic required/needed true and classify from diagnostic root causes plus post-troubleshooting metrics.

Diagnostic flags, when present in the template:

- `latency_issue`: true for high latency, packet-loss wording, or latency root causes. A practical threshold is about 100 ms or higher.
- `stability_issue`: true for high jitter, signal loss, packet-loss wording, or intermittent/stability root causes. A practical threshold is about 30 ms jitter or higher.
- `bandwidth_issue`: true when diagnostic bandwidth is materially below the subscribed rate, especially below roughly 80 percent, or the issue/root cause says poor speed/capacity.

Root-cause routing:

- `CONFIGURATION_DRIFT` or `VOICE_PROFILE_STALE`: usually `RESOLVED`, no team, blocker `NONE`, route `AUTO_TROUBLESHOOTING`, if troubleshooting shows recovery/improvement.
- `FIBER_DROP_DAMAGE` or `SIGNAL_LOSS`: `ESCALATED` to `FIELD_OPS`; key blocker `PHYSICAL_LINE_FAULT`; route `ESCALATION`.
- `BACKBONE_CAPACITY`: `ESCALATED` to `NETWORK_ENGINEERING`; key blocker `NETWORK_CAPACITY`; route `ESCALATION`.
- `PROVISIONING_STALE`: `ESCALATED` to `TIER2_SUPPORT`; key blocker `PROVISIONING_STALE`; route `ESCALATION`.
- Unknown persistent failures: escalate to `TIER2_SUPPORT` when the template provides that team; otherwise choose the closest escalation route.

Summary fields:

- Status counts are counts of `final_resolution_status`.
- Team counts are counts of routed/escalated teams in the output.
- Customer-wait counts are active-outage `PENDING_ACTION` decisions.

## Mobile And Contact-Center Case Decisions

For each payload case, resolve the case record by `case_id`, then join to line, device, plan, customer, and current bill. Apply this precedence so one clear primary action is chosen:

1. **Suspended line**:
   - `OVERDUE_BILL` with an overdue bill: `SEND_PAYMENT_REQUEST`, secondary `RESUME_LINE_REBOOT`, bill ID and amount due, route `BILLING_RECOVERY`.
   - Contract-ended, fraud, or other non-payment suspensions: `TRANSFER_HUMAN`, route `HUMAN_TRANSFER`, zero charge.
2. **No service**:
   - `airplane_mode: true`: `TOGGLE_AIRPLANE_MODE`.
   - SIM missing/unseated: `RESEAT_SIM`.
   - SIM locked, blocked, or requires carrier/account intervention: `TRANSFER_HUMAN`.
   - Mobile data disabled with otherwise healthy line/device: `TOGGLE_MOBILE_DATA`.
3. **Roaming/mobile data abroad**:
   - Phone roaming disabled on the device: `TOGGLE_ROAMING` as a self-service/device setting fix.
   - Device roaming enabled but line roaming disabled: `ENABLE_LINE_ROAMING`, `carrier_update_required: true`, route `CARRIER_UPDATE`.
4. **Data limit or allowance exceeded**:
   - If line `data_used_gb` meets/exceeds plan `data_limit_gb` and the payload includes an accepted refuel amount, use `REFUEL_DATA`.
   - `data_refuel_gb` is the accepted amount; charge is `accepted_refuel_gb * plan.data_refueling_price_per_gb`, rounded to two decimals.
   - If no accepted paid refuel is documented and a human route exists, transfer rather than inventing a charge.
5. **Slow data/device settings**:
   - `data_saver_mode: true`: `TOGGLE_DATA_SAVER`.
   - Old or limited `network_mode_preference` such as 3G-only: `SET_NETWORK_MODE`.
   - `vpn_connected: true`: `DISCONNECT_VPN`.
   - Otherwise, use the available human-transfer/no-action enum if evidence does not support a device setting fix.
6. **MMS/messaging**:
   - Missing SMS/storage permissions: `GRANT_MESSAGING_PERMISSION`; set `permission` to `sms`, `storage`, or `sms_and_storage`.
   - Missing MMSC/APN profile or APN-edit wording: `RESET_APN_REBOOT`.
7. **Wi-Fi calling**: if the issue is Wi-Fi-calling-specific and the template supports it, choose `TOGGLE_WIFI_CALLING`.

Default fields:

- Secondary action is `NO_ACTION` unless the chosen workflow explicitly requires a follow-up.
- `permission` is `NONE` except messaging permission fixes.
- `bill_id` is empty unless a billing recovery is being initiated.
- Charges are zero unless billing recovery or data refuel applies.
- For contact-center summaries, count `final_route` values into self-service, billing, carrier, and human buckets.
- For mobile-data worklist summaries, count `DATA_RECOVERY`, `CARRIER_UPDATE`, `DEVICE_SETTING_FIX`, and `HUMAN_TRANSFER`, and sum customer charges from output decisions.

## Enterprise Export Complaint Packages

Use the complaint email and requirements file to identify the client, product, incident reference, required permission users, and naming style. Then collect enterprise account, incident, export runs, messages, and SLA contract.

Decision steps:

1. Match the incident by explicit incident ID when present; otherwise match by client/account name, product, date window, and complaint summary.
2. Use the incident for `incident_id`, `enterprise_account_id`, `severity`, `engineering_owner`, and `account_owner`.
3. For the failure window, filter export runs to the incident and relevant product/account. Sort failed runs by `run_date`; use the first and last failed dates and count failed days. `backfill_days` is the message-stated manual backfill count when present, otherwise the failed-run count.
4. Derive `root_cause_category` from the strongest evidence. Prefer concrete message text over bare codes. Useful code mappings include:
   - `STALE_CREDENTIAL`: credential rotation / stale secret issue.
   - `STAGING_STORAGE_QUOTA`: staging storage quota.
   - `TIMEOUT`: timeout.
   - `RATE_LIMIT`: rate limit.
   - Otherwise lowercase the failure code and replace underscores with spaces.
5. Set `contributing_alert_issue` to `ARCHIVED_ALERT_ROUTE` when message/channel evidence shows alerts or export evidence living in an archive/stale alert route. Use `NONE` when the evidence points to an ordinary active operational channel. Use `UNKNOWN` only when the field is required but the evidence is missing.
6. Use the SLA endpoint or contract message for `sla_credit_percent`, but only apply the credit if the trigger is satisfied by the failed-run evidence.
7. Build response artifact names from the requirement style:
   - `channel_name`: lowercase client name with punctuation removed and spaces converted to hyphens.
   - `evidence_folder`: client name, failure month/year, and `Investigation`.
   - `report_title`: client name plus an export-failure/resolution-report title when the product is an export pipeline.
8. Preserve `permission_users_to_include` order. Assign `view` to finance/SLA reviewers, `edit` to engineering/account owners or response collaborators, and `upload_only` only when the requirements explicitly call for evidence upload-only access.
9. Choose `response_status` by the remaining blocker:
   - `NEEDS_FINANCE_REVIEW` when an SLA credit is being applied or finance approval is still required.
   - `NEEDS_ENGINEERING_REVIEW` when root cause, backfill, or engineering owner evidence is incomplete.
   - `UNDER_INVESTIGATION` when the incident remains unresolved and required facts are missing.
   - `READY_TO_SEND` only when all required evidence is complete and no finance/engineering review gate remains.

## Final Validation Before Answering

- Re-read the template and compare every key and enum value.
- Confirm every ID came from payload or API evidence.
- Confirm every summary count equals the decisions array.
- Confirm no diagnostic, outage, bill, or SLA fields are populated from guesses.
- Output the JSON object only.
