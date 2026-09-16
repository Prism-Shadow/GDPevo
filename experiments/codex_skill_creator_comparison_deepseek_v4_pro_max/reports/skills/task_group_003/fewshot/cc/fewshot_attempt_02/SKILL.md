---
name: telecom-support-analyst
description: Resolve telecom support-console tasks that involve cross-referencing tickets, accounts, outages, diagnostics, customers, lines, devices, plans, bills, contact-center cases, enterprise incidents, export runs, messages, and SLA contracts through a shared REST API. Use this skill whenever the user asks you to process a batch of support tickets, triage a contact-center case queue, prepare an enterprise incident response, classify a ticket queue for SLA handoff, resolve mobile-data recovery cases, or any task that mentions a support-console API with telecom entities.
---

# Telecom Support Console Analyst

## Overview

This skill covers the shared support-console REST API used across telecom operations tasks. Every task follows the same core pattern: a payload worklist identifies items to resolve, the API provides evidence for each item, and the answer template defines the exact output schema. Your job is to connect evidence to decisions without guessing.

The API is documented in [references/api-reference.md](references/api-reference.md). Read it when you need specific endpoint shapes, response fields, or entity relationships.

## The universal workflow

Every task, regardless of domain, follows these phases in order.

### Phase 1: Ingest

Read every file under `payloads/`. There will always be at least two files:

1. **The worklist** — a CSV or JSON file listing the items you must resolve (tickets, cases, or incidents). This is your input queue. Preserve the order items appear in the worklist; the answer template expects it.
2. **The answer template** — a JSON file (`answer_template.json`) defining the exact output schema. Every field name, every enum value, every nested structure must appear in your output exactly as shown. The template is authoritative on field names, types, and enum sets.

Some tasks include additional payload files (complaint emails, response requirements). Read them all before starting.

### Phase 2: Fetch and cross-reference

For each item in the worklist, fetch the API records needed to make a decision. Parallelize fetches where possible — items are independent. The minimum set of endpoints for each domain is described in the Domain Patterns section below.

**Critical rule:** Every decision must be grounded in API evidence. Never invent values. If an API returns an unexpected shape or a field is missing, treat it as the default (empty string `""`, `0`, `false`, or `NONE` as appropriate for the field type) rather than guessing.

The API base URL is always provided in the task prompt as `<TASK_ENV_BASE_URL>`. Substitute it literally.

### Phase 3: Map evidence to decisions

For each item, map the API evidence to the answer-template fields. The decision tables in [references/api-reference.md](references/api-reference.md) describe the mapping logic. The general principle: inspect the most specific record first (the item itself — ticket, case, incident), then follow foreign keys to related entities (accounts, lines, devices, outages, export runs, messages), and finally apply the mapping rules.

### Phase 4: Assemble and output

1. Fill the per-item array in the answer template, preserving the worklist order.
2. Compute the summary aggregates by counting the per-item decisions. Never hard-code summary numbers; derive them from the decisions you just made.
3. Output **only** the completed JSON. No markdown fences, no commentary, no surrounding text.

## Domain patterns

The five task families share the same API but differ in which endpoints matter and how evidence maps to decisions.

### Ticket resolution (offline batch)

**Payload worklist:** CSV with `ticket_id`, `account_id`, `reported_service_type`, and a customer report or queue note.

**API evidence chain per ticket:**
1. `GET /api/tickets/{ticket_id}` — confirms the ticket exists and gives `service_area`
2. `GET /api/accounts/{account_id}` — account status, tier, authentication state, service_area
3. `GET /api/diagnostics/{ticket_id}` — latency, jitter, bandwidth, root causes (may 404 for non-diagnosable tickets)
4. `GET /api/outages` — check for active outages covering the ticket's `service_area`

**Decision logic:**
- If the account is not Active or not found, the ticket fails with an account-related route. Check whether the account_id is malformed (non-existent) vs. a real account with a blocking status.
- If an active outage covers the ticket's service_area and matches the reported service_type, the ticket waits on the outage (PENDING_ACTION with OUTAGE_WAIT).
- If diagnostics show latency/packet-loss/jitter root causes, the ticket may be auto-resolved by troubleshooting. Mark the boolean flags from the diagnostic evidence: compare the diagnostic values against the subscribed_mbps and against normal thresholds (latency > 80ms is a latency issue; jitter > 20ms is a stability issue; bandwidth < 80% of subscribed is a bandwidth issue).
- If the report involves physical line work or field-level issues, escalate to FIELD_OPS. If it involves backbone capacity, escalate to NETWORK_ENGINEERING. Provisioning mismatches go to TIER2_SUPPORT. Overdue suspensions go to ACCOUNTS_PAYABLE.
- If none of the above apply but diagnostics confirm a recoverable issue, mark RESOLVED with AUTO_TROUBLESHOOTING.

### Contact-center case triage

**Payload worklist:** JSON with `case_id` and `reported_issue` per case.

**API evidence chain per case:**
1. `GET /api/contact-center/cases/{case_id}` — gives `customer_id`, `line_id`, `device_id`, `issue_type`
2. `GET /api/customers/{customer_id}` — customer status
3. `GET /api/lines/{line_id}` — line status, roaming, data_used, plan_id, suspension_reason, device_id
4. `GET /api/devices/{device_id}` — full device state (sim, radios, VPN, data saver, network mode, permissions, signal, speed test)
5. `GET /api/bills/{bill_id}` — only when billing is relevant (line suspended, overdue)
6. `GET /api/plans/{plan_id}` — data limits and refuel pricing

**Decision logic:**
- Match the reported issue to the most likely root cause by reading device and line state. A "no service" report with `sim_status: "missing"` suggests reseating the SIM. With `airplane_mode: true`, suggest toggling airplane mode. With `mobile_data_enabled: false`, toggle mobile data.
- For suspended lines, fetch the bill to get the overdue amount and route to BILLING_RECOVERY.
- For roaming issues, check whether phone-side roaming is on but line-side roaming is disabled (then ENABLE_LINE_ROAMING and route to CARRIER_UPDATE) vs. simply needing TOGGLE_ROAMING.
- For messaging permission issues, check `messaging_permissions` and `can_send_mms` on the device. Grant the missing permission.
- For slow data, check `vpn_connected`, `data_saver_mode`, `network_mode_preference`. Disconnect VPN, toggle data saver, or set network mode accordingly.
- `secondary_action` is NO_ACTION unless the evidence clearly shows a second fix is needed.
- `permission` field: only set when the primary action itself requires a permission grant (e.g., GRANT_MESSAGING_PERMISSION requires `storage`).
- `charge_amount_usd` is 0.0 unless a bill payment is involved; then use the exact amount from the bill.
- `final_route` summarizes the outcome: SELF_SERVICE for device-setting fixes, BILLING_RECOVERY for payment-related cases, CARRIER_UPDATE for line-side provisioning changes, HUMAN_TRANSFER when automated resolution is impossible.

### Enterprise incident response

**Payload worklist:** Complaint email (txt) plus `response_requirements.json`.

**API evidence chain:**
1. `GET /api/enterprise/incidents/{incident_id}` — incident details, severity, owners, enterprise_account_id
2. `GET /api/enterprise/accounts/{enterprise_account_id}` — account name, tier, account_owner, finance_owner
3. `GET /api/enterprise/export-runs?enterprise_account_id={id}` — filter to the incident's runs by `incident_id`
4. `GET /api/enterprise/messages?enterprise_account_id={id}` — filter to messages referencing the incident or related channels
5. `GET /api/enterprise/sla/{enterprise_account_id}` — credit percentage and trigger conditions

**Decision logic:**
- `root_cause_category`: derived from the `failure_code` on failed export runs. Read the failure_code string and convert to a human-readable category (e.g., STALE_CREDENTIAL → "stale credential after rotation"). Look at messages for additional context about the cause.
- `contributing_alert_issue`: check whether any messages reference an archived alert route channel. If a message's channel name contains "archive" and it is relevant to the incident, mark ARCHIVED_ALERT_ROUTE; otherwise NONE.
- `failure_window`: the earliest and latest failed run dates define the window. Count the distinct dates that failed.
- `backfill_days`: the number of failed days needing backfill. Default matches `failed_days` unless messages indicate a different count.
- `sla_credit_percent`: from the SLA contract for the matching product and failure scenario.
- `severity`: from the incident record.
- `engineering_owner` and `account_owner`: from the incident and enterprise account records. The incident's `engineering_owner` is authoritative; the account's `account_owner` is authoritative.
- `channel_name`: lowercase-hyphen of the enterprise account name (e.g., "Acme Corp." → "acme-corp").
- `evidence_folder`: "[Account Name] [Month Year] Investigation" (derive month/year from the failure window start date).
- `report_title`: "[Account Name] Export Failure - Resolution Report".
- `share_permissions`: from `response_requirements.json` `permission_users_to_include`, ordered as listed. Default first user to `view`, second to `edit` unless requirements specify otherwise.
- `response_status`: NEEDS_FINANCE_REVIEW when an SLA credit is involved and credit percent is non-zero; otherwise READY_TO_SEND if all evidence is clear, or NEEDS_ENGINEERING_REVIEW if root cause points to engineering.

### Queue quality classification

**Payload worklist:** CSV with `ticket_id`, `account_id`, `reported_service_type`, `queue_note`.

**API evidence chain per ticket:**
1. `GET /api/tickets/{ticket_id}` — ticket record
2. `GET /api/accounts/{account_id}` — account status and authentication
3. `GET /api/diagnostics/{ticket_id}` — diagnostic results (may 404)
4. `GET /api/outages` — active outage check

**Decision logic:**
- `final_resolution_status`: FAILED when the account is invalid, auth has failed, or the account is suspended. PENDING_ACTION when an active outage is the sole blocker. RESOLVED when diagnostics indicate a recoverable issue. ESCALATED when the issue needs a specialized team.
- `route_team`: NONE when no escalation is needed. ACCOUNTS_PAYABLE for overdue/fraud suspensions. NETWORK_ENGINEERING for backbone capacity. FIELD_OPS for physical line faults. TIER2_SUPPORT for provisioning issues.
- `key_blocker`: the single most important reason the ticket cannot be auto-resolved. Choose the most specific match: ACTIVE_OUTAGE, INVALID_ACCOUNT, AUTH_FAILED, OVERDUE_SUSPENSION, FRAUD_SUSPENSION, NETWORK_CAPACITY, PROVISIONING_STALE, PHYSICAL_LINE_FAULT, or NONE.
- `diagnostic_required`: true when diagnostics ran successfully and produced evidence; false when diagnostics are unavailable (404 or empty), the account is invalid, or an outage is the obvious cause.
- Queue note text is advisory only; always verify against API records.

### Mobile data recovery

**Payload worklist:** JSON with `case_id`, `reported_issue`, and optional `customer_preferences`.

**API evidence chain per case:**
1. `GET /api/contact-center/cases/{case_id}` — `line_id`, `device_id`
2. `GET /api/lines/{line_id}` — line status, `data_used_gb`, `plan_id`, `roaming_enabled`
3. `GET /api/devices/{device_id}` — `mobile_data_enabled`, `data_saver_mode`, `network_mode_preference`, `phone_roaming_enabled`, `vpn_connected`
4. `GET /api/plans/{plan_id}` — `data_limit_gb`, `data_refueling_price_per_gb`

**Decision logic:**
- "Data stopped after usage limit": compare `data_used_gb` to `data_limit_gb`. If over limit, primary action is REFUEL_DATA. `data_refuel_gb` comes from `customer_preferences` (if provided) or a sensible default. `charge_amount_usd` = `data_refuel_gb` × `data_refueling_price_per_gb`.
- "Traveler has roaming on phone but no data": check `phone_roaming_enabled` (device) vs. `roaming_enabled` (line). If phone-side is on but line-side is off, primary is ENABLE_LINE_ROAMING with `carrier_update_required: true`. If both are on, check `mobile_data_enabled`.
- "Slow data and data-saver icon visible": primary is TOGGLE_DATA_SAVER.
- "Slow data on older network mode": primary is SET_NETWORK_MODE.
- "No data after settings change": check `mobile_data_enabled` on device. If off, primary is TOGGLE_MOBILE_DATA.
- `final_route`: DATA_RECOVERY for refuel cases, CARRIER_UPDATE when a line-side provisioning change is needed, DEVICE_SETTING_FIX for toggles/mode changes, HUMAN_TRANSFER when the issue cannot be resolved through automation.

## General rules

### Template fidelity

The answer template defines field names, enum value sets, nesting, and ordering. Do not add, remove, or rename fields. Enum values must be drawn exactly from the template's allowed set. Strings that say "preserve payload order" or "preserve ascending order" mean exactly that — your output array must match the input order.

### Summary computation

Every summary field is a count derived from the per-item decisions. After filling all per-item entries, count each category and fill the summary block. Never hard-code summary values; compute them from your decisions even if the arithmetic seems obvious. Mismatched summaries are a common failure mode.

### API errors

When an endpoint returns a 404 or an error response, treat the missing record as evidence of a problem (e.g., invalid account, ticket not found, no diagnostics available). Do not retry endlessly. Map the absence to the appropriate failure status in the template.

### Parallelism

Items in a worklist are independent. Fetch all item records, plus shared resources like `GET /api/outages`, `GET /api/enterprise/messages`, and `GET /api/enterprise/export-runs`, in parallel. This is the single biggest performance lever.

### Output format

Your final response must be raw JSON — no markdown fences, no explanatory text. The answer template's structure IS your output structure.
