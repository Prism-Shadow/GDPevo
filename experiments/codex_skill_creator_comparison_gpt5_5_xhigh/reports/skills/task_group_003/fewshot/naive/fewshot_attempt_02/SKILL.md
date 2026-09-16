---
name: support-console-resolution
description: Solve support-console ticket, mobile case, and enterprise export response tasks that require payload parsing plus read-only API evidence.
---

# Support Console Resolution Skill

Use this skill when the task asks for JSON decisions based on local payloads and the shared support console API. The payload is only the worklist; the authoritative facts usually come from the API.

## Operating Rules

- Return only JSON matching the provided `payloads/answer_template.json`.
- Preserve the ordering required by the template: usually payload order for tickets and ascending `case_id` order for mobile cases.
- Use `<TASK_ENV_BASE_URL>` from the prompt or environment note. Check `GET /api/catalog` if endpoint names differ; use read-only business endpoints only.
- Do not infer customer/account state from prose when an API record exists. Query by the IDs in the payload, then follow related IDs.
- Prefer `GET /api/search?q=<id-or-client-name>` when a direct account endpoint is unavailable or when you need related records.
- Fill empty strings, `false`, `0.0`, and `NO_ACTION` exactly as the template specifies when a field is not applicable.
- Compute summary counts from your final per-item decisions, not separately from the payload.

## Service Ticket Workflow

For each ticket row:

1. Fetch the ticket with `/api/tickets/{ticket_id}` and search the account ID with `/api/search?q=<account_id>` to validate account status and authentication.
2. Check `/api/outages` for an active outage matching the ticket `service_area` and `service_type`.
3. Fetch `/api/diagnostics/{ticket_id}` and `/api/troubleshooting/{ticket_id}` only after the account and outage checks do not already decide the ticket.
4. Compare diagnostics with ticket service facts:
   - `latency_issue`: true for clearly high latency, especially around or above 100 ms.
   - `stability_issue`: true for high jitter, packet/signal-loss evidence, or line-damage root causes.
   - `bandwidth_issue`: true when measured bandwidth is materially below the subscribed rate, about 80% or less.
   - `diagnostic_required` / `diagnostic_needed`: true for service-quality cases that proceed to troubleshooting or escalation; false for invalid accounts, authentication failures, suspensions, and active outages.

Decision precedence:

- No matching account record: `FAILED`, blocker/route `INVALID_ACCOUNT`, no team, no diagnostics.
- Account authentication recovery or last login failure tied to the complaint: `FAILED`, blocker/route `AUTH_FAILED`, no team.
- Suspended or otherwise ineligible account:
  - If the template has an overdue blocker/team, use `OVERDUE_SUSPENSION` and `ACCOUNTS_PAYABLE` for overdue billing suspensions.
  - Otherwise use the template's ineligible-account route and no escalation team unless the evidence explicitly names a payment handoff.
- Active outage for the service area and service type: `PENDING_ACTION`, blocker `ACTIVE_OUTAGE`, route `OUTAGE_WAIT`, include `outage_id`, no diagnostics, no escalation team.
- Fixable profile/configuration causes with post-troubleshooting metrics back in acceptable range: `RESOLVED`, route `AUTO_TROUBLESHOOTING`, team `NONE`, blocker `NONE`.
- Physical plant or signal-loss causes such as drop damage: `ESCALATED`, team `FIELD_OPS`, blocker `PHYSICAL_LINE_FAULT`.
- Backbone/capacity causes: `ESCALATED`, team `NETWORK_ENGINEERING`, blocker `NETWORK_CAPACITY`.
- Provisioning/profile stale causes that are not fully repaired by troubleshooting: `ESCALATED`, team `TIER2_SUPPORT`, blocker `PROVISIONING_STALE`.

For ticket summaries, count final statuses and route teams exactly from the decisions. Customer-wait counts are the tickets left pending because of outage/wait routes.

## Mobile Case Workflow

For each case:

1. Fetch or search the case to get `customer_id`, `line_id`, and `device_id`.
2. Fetch `/api/lines/{line_id}`, `/api/devices/{device_id}`, the line plan with `/api/plans/{plan_id}`, and the customer's bill from `/api/bills` when billing recovery may apply.
3. Apply action rules in this priority order.

Line and billing rules:

- `line.status == Suspended` with `suspension_reason == OVERDUE_BILL`: primary `SEND_PAYMENT_REQUEST`, secondary `RESUME_LINE_REBOOT`, bill ID and amount from the overdue bill, final route `BILLING_RECOVERY`.
- Suspension for contract end, fraud, locked account state, or no recoverable bill: `TRANSFER_HUMAN`, no charge, final route `HUMAN_TRANSFER`.

No-service and device setting rules:

- `device.airplane_mode == true`: `TOGGLE_AIRPLANE_MODE`.
- `device.sim_status == missing`: `RESEAT_SIM`.
- `device.sim_status` locked or requiring carrier/security intervention: `TRANSFER_HUMAN`.
- `device.mobile_data_enabled == false`: `TOGGLE_MOBILE_DATA`.
- Abroad with phone roaming off but line roaming on: `TOGGLE_ROAMING`, self-service/device-setting route.
- Abroad with phone roaming on but line roaming disabled: `ENABLE_LINE_ROAMING`, `carrier_update_required: true`, final route `CARRIER_UPDATE`.

Data recovery rules:

- If line `data_used_gb` is at or above the plan `data_limit_gb` and the payload provides accepted refuel GB, use `REFUEL_DATA`.
- `data_refuel_gb` is the accepted GB. Charge equals accepted GB multiplied by `data_refueling_price_per_gb`, rounded to two decimals.
- Data refuel cases use final route `DATA_RECOVERY`. If no accepted refuel or customer consent is available, transfer to a human rather than inventing a charge.

Slow-data and MMS rules:

- `device.data_saver_mode == true`: `TOGGLE_DATA_SAVER`.
- Legacy network mode such as `3g_only`: `SET_NETWORK_MODE`.
- `device.vpn_connected == true`: `DISCONNECT_VPN`.
- MMS/photo-send failure with missing messaging permissions: `GRANT_MESSAGING_PERMISSION`; set `permission` to `sms`, `storage`, or `sms_and_storage` based on the missing booleans.
- MMS failure with missing MMSC/APN URL: `RESET_APN_REBOOT`.
- Wi-Fi-calling-specific trouble with Wi-Fi calling disabled: `TOGGLE_WIFI_CALLING`.

For contact-center templates, use `SELF_SERVICE`, `BILLING_RECOVERY`, `CARRIER_UPDATE`, or `HUMAN_TRANSFER`. For mobile-data worklists, classify self-service setting changes as `DEVICE_SETTING_FIX`, refuels as `DATA_RECOVERY`, carrier line changes as `CARRIER_UPDATE`, and unresolved/manual cases as `HUMAN_TRANSFER`.

`secondary_action` is normally `NO_ACTION`; use a secondary action only when the evidence and template imply a required follow-up, such as resuming/rebooting a line after payment.

## Enterprise Export Response Workflow

Use this for structured response packages about export failures or enterprise incidents.

1. Parse the complaint and requirements for client name, product, approximate incident ID, named users, naming style, and required fields.
2. Fetch the incident by ID if available; otherwise search by client name and product. Then fetch the enterprise account and SLA contract for the incident's `enterprise_account_id`.
3. Filter `/api/enterprise/export-runs` to the chosen incident/account/product. Use only failed runs for the failure window.
4. Search or scan `/api/enterprise/messages` for messages matching the client, incident, product, failure code, owner names, or account.

Field derivation:

- `incident_id`, `enterprise_account_id`, `severity`, `engineering_owner`, and `account_owner` come from the incident/account records.
- `failure_window.start_date` and `end_date` are the first and last failed run dates for the relevant incident; `failed_days` is the count of failed runs in that window.
- `backfill_days` equals the failed-day count unless a message or requirement gives a different manual backfill count.
- `root_cause_category` is a concise lowercase phrase from the failure code plus message evidence. Convert codes from screaming snake case to readable words and enrich only with evidence found in messages.
- `contributing_alert_issue` is `ARCHIVED_ALERT_ROUTE` when the relevant alert/root-cause evidence is found only in an archive/archived alert channel; `NONE` when the active evidence route is normal; `UNKNOWN` when evidence is insufficient.
- `sla_credit_percent` comes from the SLA contract if the trigger is satisfied by the failed runs; otherwise use `0`.
- `channel_name` follows the requested naming style. For a lowercase-hyphen channel, slugify the enterprise account name.
- `evidence_folder` and `report_title` should follow the naming style literally, using the client name and the month/year of the failure window when requested.
- `share_permissions` must include exactly the requested users, in the listed order. Assign permissions from explicit requirements when present. If unspecified, finance/account reviewers are usually `view`; engineering or response collaborators are usually `edit`; use `upload_only` only when the requirement says the user should upload evidence without editing.

Response status priority:

- Missing root-cause, incident, or run evidence: `UNDER_INVESTIGATION`.
- Root cause or backfill is unresolved or still needs owner confirmation: `NEEDS_ENGINEERING_REVIEW`.
- SLA credit is nonzero or finance approval is required: `NEEDS_FINANCE_REVIEW`.
- Otherwise, when evidence, owners, artifacts, and permissions are complete: `READY_TO_SEND`.

## Final JSON Check

Before responding:

- Re-open the template and verify every key name, enum spelling, number precision, and empty default.
- Ensure IDs are copied from API/payload evidence, not normalized.
- Recompute summaries from the decision array and confirm they match the array length.
- Output one valid JSON object and no markdown or explanatory text.
