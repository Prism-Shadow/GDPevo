---
name: support-console-ops
description: Resolve telecom support tasks using a shared support console REST API. Use when a prompt provides TASK_ENV_BASE_URL and asks to resolve support tickets (batch or queue), handle contact-center cases, classify ticket queues, prepare enterprise export incident responses, or recover mobile data. Covers ticket resolution, case routing, queue classification, enterprise incident response, and mobile data recovery workflows.
---

# Support Console Ops

Resolve telecom operations tasks by querying the support console REST API and
mapping evidence to structured JSON decisions. The API is a read-only
exploration surface; the skill covers five task types.

## Quick Start

1. Read the prompt to identify the task type and the payload file(s).
2. Parse the payload(s) to build the work list (tickets, cases, or incidents).
3. Query the API iteratively, gathering evidence for each item.
4. Map evidence to decisions following the rules in this skill.
5. Return JSON that conforms to the provided `answer_template.json`.

All API endpoints return JSON arrays of objects or single objects. Use `curl`
with `-s` and pipe through `python3 -m json.tool` for readability when exploring,
but prefer direct JSON parsing for decision logic.

## API Reference

See [references/api_reference.md](references/api_reference.md) for full
endpoint descriptions, field shapes, and interpretation rules. Load it when
the task involves unfamiliar endpoints.

Key base endpoints by task type:

| Task Type | Primary Endpoints |
|---|---|
| Ticket batch | `/api/tickets`, `/api/accounts`, `/api/outages`, `/api/diagnostics/<ticket_id>`, `/api/troubleshooting/<ticket_id>` |
| Contact center cases | `/api/cases`, `/api/customers`, `/api/lines`, `/api/devices/<device_id>`, `/api/plans/<plan_id>`, `/api/bills` |
| Enterprise incident response | `/api/enterprise/incidents`, `/api/enterprise/accounts`, `/api/enterprise/export-runs`, `/api/enterprise/messages`, `/api/enterprise/sla/<account_id>` |
| Mobile data recovery | `/api/cases`, `/api/lines`, `/api/devices/<device_id>`, `/api/plans/<plan_id>`, `/api/bills` |

## Task Type Decision Tree

Read the prompt to determine the task:

- **"support operations analyst" + "batch" + CSV payload** → Ticket Batch Resolution
- **"contact-center lead" + case queue JSON** → Contact Center Case Routing
- **"enterprise support lead" + complaint email** → Enterprise Incident Response
- **"queue-quality analyst" + queue snapshot CSV** → Ticket Queue Classification
- **"mobile-data recovery analyst" + worklist JSON** → Mobile Data Recovery

## Ticket Batch Resolution

Read each ticket from the CSV payload. For each ticket:

1. **Fetch the ticket** via `GET /api/tickets/<ticket_id>` — get `account_id`, `service_area`, `service_type`.
2. **Fetch the account** via `GET /api/accounts/<account_id>`:
   - If HTTP 404 or `account_id` starts with a non-standard prefix → `FAILED` / `INVALID_ACCOUNT`.
   - If `status: "Suspended"` → `FAILED` / `INELIGIBLE_ACCOUNT`.
   - If `authentication.last_login_status` is not `"SUCCESS"` → `FAILED` / `AUTH_FAILED`.
3. **Fetch outages** via `GET /api/outages` and match: `active: true`, same `service_area`, `service_types` includes ticket’s `service_type`. If match exists:
   - Status → `PENDING_ACTION`, route → `OUTAGE_WAIT`, `outage_id` → matched outage’s ID.
   - `diagnostic_needed` → `false`, all issue flags → `false`.
4. **No active outage** → fetch diagnostics via `GET /api/diagnostics/<ticket_id>`.
   - Examine `root_causes`. Ignore `GENERATED_NOISE` entries.
   - `CONFIGURATION_DRIFT` → fetch troubleshooting via `GET /api/troubleshooting/<ticket_id>`.
     - If troubleshooting has `steps` and `post_bandwidth_mbps` near `subscribed_mbps` → `RESOLVED` / `AUTO_TROUBLESHOOTING`.
   - `FIBER_DROP_DAMAGE` or `SIGNAL_LOSS` → `ESCALATED` / `ESCALATION` to `FIELD_OPS`.
   - `NETWORK_CAPACITY` → `ESCALATED` to `NETWORK_ENGINEERING`.
   - `PROVISIONING_STALE` → `ESCALATED` to `TIER2_SUPPORT`.
5. **Issue flags:** set `latency_issue`, `stability_issue`, `bandwidth_issue` based on diagnostics:
   - Compare `bandwidth_mbps` to `subscribed_mbps` (substantially lower → `bandwidth_issue: true`).
   - Compare `latency_ms` (>80 ms → `latency_issue: true`).
   - Compare `jitter_ms` (>25 ms → `stability_issue: true`).
6. **`diagnostic_needed`** is `true` when diagnostics were fetched and used.

Batch summary: count each `final_resolution_status` category plus tickets with
`PENDING_ACTION` as `tickets_requiring_customer_wait`.

## Ticket Queue Classification

Read tickets from a CSV with `ticket_id`, `account_id`, `reported_service_type`,
`queue_note`. Classify each:

1. **Active outage?** → `PENDING_ACTION`, `key_blocker: ACTIVE_OUTAGE`, no escalation needed.
2. **Invalid account?** → `FAILED`, `key_blocker: INVALID_ACCOUNT`.
3. **Auth failure?** → `FAILED`, `key_blocker: AUTH_FAILED`.
4. **Overdue suspension?** → `FAILED`, `key_blocker: OVERDUE_SUSPENSION`, route to `ACCOUNTS_PAYABLE`.
5. **Fraud suspension?** → `FAILED`, `key_blocker: FRAUD_SUSPENSION`.
6. **Config/provisioning drift?** → `RESOLVED` when troubleshooting succeeds; `diagnostic_required: true`.
7. **Network capacity / backbone?** → `ESCALATED` to `NETWORK_ENGINEERING`, `key_blocker: NETWORK_CAPACITY`.
8. **Physical line fault?** → `ESCALATED` to `FIELD_OPS`, `key_blocker: PHYSICAL_LINE_FAULT`.
9. **Provisioning stale?** → `ESCALATED` to `TIER2_SUPPORT`, `key_blocker: PROVISIONING_STALE`.

Where diagnostics or troubleshooting confirms a resolution, set
`diagnostic_required: true`. Where the blocker is self-evident (outage, invalid
account, etc.), set `diagnostic_required: false`.

## Contact Center Case Routing

Read each case from `case_queue.json`. For each case:

1. **Fetch the case** to get `line_id`, `device_id`, `customer_id`, `issue_type`, `customer_location`.
2. **Fetch the line** via `GET /api/lines/<line_id>`:
   - If `status: "Suspended"` with `suspension_reason: "OVERDUE_BILL"`:
     - Primary action → `SEND_PAYMENT_REQUEST`.
     - Secondary action → `RESUME_LINE_REBOOT`.
     - Fetch `/api/bills`, filter by `customer_id`, find overdue bill.
     - Set `bill_id` and `charge_amount_usd` from the bill.
     - `final_route` → `BILLING_RECOVERY`.
   - If `roaming_enabled: true` but case is abroad → fetch device; if `phone_roaming_enabled: false` → `TOGGLE_ROAMING`, `SELF_SERVICE`. If `phone_roaming_enabled: true` but still no data → `ENABLE_LINE_ROAMING`, `CARRIER_UPDATE`.
3. **Fetch the device** via `GET /api/devices/<device_id>`:
   - Map device state to action:
     - `sim_status: "missing"` + `signal_strength: "none"` → `RESEAT_SIM`.
     - `phone_roaming_enabled: false` while abroad → `TOGGLE_ROAMING`.
     - `data_saver_mode: true` with slow data → `TOGGLE_DATA_SAVER`.
     - `vpn_connected: true` with slow data → `DISCONNECT_VPN`.
     - `mobile_data_enabled: false` with no data → `TOGGLE_MOBILE_DATA`.
     - `can_send_mms: false` with MMS issue → `GRANT_MESSAGING_PERMISSION`.
     - Outdated `network_mode_preference` → `SET_NETWORK_MODE`.
4. **Permission field:** For `GRANT_MESSAGING_PERMISSION`, check `messaging_permissions`. If `storage` is `true` but `can_send_mms` is `false`, set `permission: "storage"`. Otherwise `permission: "NONE"`.
5. **Default:** `NO_ACTION` for both primary and secondary when no rule matches.

## Mobile Data Recovery

Read each case from the worklist JSON. For each case:

1. **Fetch the case, line, and device** as in Contact Center routing.
2. **Check if data refuel is needed:**
   - Fetch the plan via `GET /api/plans/<plan_id>`.
   - If `data_used_gb > plan.data_limit_gb` or the case reports "Data stopped after usage limit":
     - Primary action → `REFUEL_DATA`.
     - Use customer preferences for `data_refuel_gb` if provided.
     - `charge_amount_usd = data_refuel_gb * plan.data_refueling_price_per_gb`.
     - `final_route` → `DATA_RECOVERY`.
     - `carrier_update_required` → `false`.
3. **Device-based actions:**
   - `phone_roaming_enabled: false` while abroad → `TOGGLE_ROAMING` or `ENABLE_LINE_ROAMING`. If line-side roaming also needs enabling: `carrier_update_required: true`, `final_route: CARRIER_UPDATE`.
   - `data_saver_mode: true` → `TOGGLE_DATA_SAVER`, `DEVICE_SETTING_FIX`.
   - `mobile_data_enabled: false` → `TOGGLE_MOBILE_DATA`, `DEVICE_SETTING_FIX`.
   - Outdated `network_mode_preference` → `SET_NETWORK_MODE`, `DEVICE_SETTING_FIX`.
4. **Worklist summary:** count `data_refuel_cases`, `carrier_updates`, `device_setting_fixes`, `human_transfers`, and sum `total_estimated_customer_charge_usd`.

## Enterprise Incident Response

Given a complaint email and response requirements:

1. **Identify the incident** using the approximate reference from the complaint.
   `GET /api/enterprise/incidents/<incident_id>` to extract `enterprise_account_id`,
   `severity`, `engineering_owner`, `account_owner`.
2. **Fetch the enterprise account** via `GET /api/enterprise/accounts/<account_id>`.
3. **Fetch export runs** via `GET /api/enterprise/export-runs`. Filter by
   `enterprise_account_id`. Identify consecutive `FAILED` runs to determine
   `failure_window` (start_date, end_date, failed_days). The `failure_code` on
   those runs becomes `root_cause_category`. Count `SUCCEEDED` runs after the
   failure window → `backfill_days`.
4. **Fetch messages** via `GET /api/enterprise/messages`. Look for messages by
   the engineering owner and account owner. Extract root cause explanation from
   message bodies. If a message about the root cause is in a channel whose
   name contains "archive" → `contributing_alert_issue: ARCHIVED_ALERT_ROUTE`.
   Otherwise `NONE`.
5. **Fetch SLA** via `GET /api/enterprise/sla/<enterprise_account_id>`.
   `monthly_export_credit_percent` → `sla_credit_percent`.
6. **Name derivation** from naming_style requirements:
   - `channel_name`: lowercase, hyphenated client name.
   - `evidence_folder`: "Client Name Month Year Investigation".
   - `report_title`: "Client Name Export Failure - Resolution Report".
7. **Share permissions:** assign `view` or `edit` to users per requirements.
8. **Response status:** If `sla_credit_percent > 0` → `NEEDS_FINANCE_REVIEW`.
   Otherwise `READY_TO_SEND`.

## General Rules

- Always preserve payload order when returning JSON arrays.
- Use `"NONE"` for enum fields when no applicable value exists.
- Use `""` for string fields when no value applies.
- Use `0.0` for numeric fields when no value applies.
- Map `NO_ACTION` as secondary action when only one action is needed.
- When an API call returns an HTTP error, the item is failed with an appropriate
  `key_blocker` or `final_resolution_status` of `FAILED`.
- All monetary values use exactly two decimal places. Data refuel GB uses one decimal.
- Read `answer_template.json` before starting to understand the exact output schema.
