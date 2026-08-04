---
name: support-console-agent
description: Resolve support-operations tasks by querying a shared support-console REST API and producing structured JSON decisions from payloads and answer templates. Use when the task involves tickets, cases, incidents, or worklists that reference a support console API at a resolvable base URL.
---

# Support Console Agent Skill

## Overview

This skill handles support-operations tasks that follow a consistent pattern:
1. A prompt assigns a support role (analyst, lead, recovery specialist, etc.).
2. A base URL (`<TASK_ENV_BASE_URL>` or `GDPEVO_ENV_BASE_URL`) points to a shared support-console REST API.
3. One or more payload files (CSV, JSON) contain the work items.
4. An answer-template JSON defines the exact output schema.
5. The agent must query the API for each work item, cross-reference related records, make a decision, fill the template, compute summaries, and return only the filled JSON.

## Step 1 — Resolve the API Base URL

The prompt always provides the API base through one of these mechanisms, tried in order:
1. Read `environment_access.md` (or similar env-access file in the workspace) and extract `GDPEVO_ENV_BASE_URL` or an equivalent URL.
2. If the prompt contains a literal `<TASK_ENV_BASE_URL>`, substitute it with the value from step 1.
3. If neither is available, check the environment variable `GDPEVO_ENV_BASE_URL`.

Store the resolved URL as `$API_BASE`. Every API call uses this base. No authentication is required (no credentials, no tokens, no headers beyond `Accept: application/json`).

## Step 2 — Explore the API Catalog

Before processing any work items, query the catalog endpoint:

```
GET $API_BASE/api/catalog
```

The catalog response describes every available endpoint, the fields each endpoint returns, and the relationships between entities. Use it to:
- Confirm which endpoints are relevant for the current task domain.
- Understand the field names and types you will encounter.
- Identify entity relationships (e.g., a ticket links to an account, a case links to a customer/line, an incident links to an enterprise account).

Keep the catalog response handy throughout the task; it is the single source of truth for field names and semantics.

## Step 3 — Load the Work Items

Identify the payload file(s) referenced in the prompt. Common patterns:
- **CSV payloads**: Read with a CSV-aware approach. The first row is a header. Each subsequent row is one work item with typed columns (ticket_id, account_id, reported_service_type, etc.).
- **JSON payloads**: Parse the JSON object. Work items are typically inside a top-level key (`cases`, `tickets`, etc.). Each item has an identifier field.
- **Multi-file payloads**: Some tasks include a primary payload plus supplementary files (complaint email text, response requirements JSON, customer preferences). Read every file in the payload directory.

Preserve the original order of work items as they appear in the payload. The answer template almost always requires "preserve payload order" or "preserve ascending case_id order."

## Step 4 — Load the Answer Template

Read the file referenced as `payloads/answer_template.json` (or similar path from the prompt). Parse it as the output schema you must fill. Study:
- **Field names and types**: Strings, enums (with allowed values), booleans, integers, numbers.
- **Nested objects**: Some templates have nested structures (e.g., `failure_window` with `start_date`, `end_date`, `failed_days`).
- **Array elements**: The per-item array key (e.g., `ticket_decisions`, `case_decisions`).
- **Summary object**: The aggregate counts key (e.g., `batch_summary`, `queue_summary`, `worklist_summary`).
- **Enum constraints**: Every enum field has an allowed set of values; never invent a value outside the set.
- **Ordering comments**: Strings like "preserve payload order" or "preserve ascending case_id order" tell you how to sequence the per-item array.

**Critical rule**: Produce output that exactly conforms to this template. Do not add extra keys, omit required keys, or change key names.

## Step 5 — Query the API for Each Work Item

For every work item in the payload, perform the following lookup pattern:

### 5a. Look up the primary entity

Use the identifier from the payload to fetch the entity directly:
- Ticket tasks → `GET $API_BASE/api/tickets/{ticket_id}`
- Case tasks → `GET $API_BASE/api/contact-center/cases/{case_id}` or `GET $API_BASE/api/cases/{case_id}`
- Incident tasks → `GET $API_BASE/api/enterprise/incidents/{incident_id}`
- Account lookups → `GET $API_BASE/api/accounts/{account_id}` or `GET $API_BASE/api/enterprise/accounts/{account_id}`

If the primary entity is not found (HTTP 404), treat the item as failed with an appropriate blocker (e.g., `INVALID_ACCOUNT`, `INELIGIBLE_ACCOUNT`).

### 5b. Query related entities

Based on the entity type and the fields returned, fetch related records:
- **For tickets**: diagnostics (`/api/diagnostics/{ticket_id}`), troubleshooting (`/api/troubleshooting/{ticket_id}`), outages (`/api/outages` — filter for active outages matching location or account), and the linked account.
- **For mobile cases**: customer (`/api/customers/{customer_id}`), line (`/api/lines/{line_id}`), device (`/api/devices/{device_id}`), plan (`/api/plans/{plan_id}`), bills (`/api/bills` — filter for the customer).
- **For enterprise incidents**: enterprise account (`/api/enterprise/accounts/{account_id}`), export runs (`/api/enterprise/export-runs` — filter by account and date range), messages (`/api/enterprise/messages` — filter by incident), SLA (`/api/enterprise/sla/{account_id}`).

### 5c. Gather evidence fields

From all queried records, extract the evidence fields that drive decisions. Common evidence fields include:
- **Account status**: active, suspended, overdue, fraudulent, ineligible, invalid.
- **Diagnostic results**: latency issues, stability issues, bandwidth issues, whether diagnostics passed.
- **Outage status**: active outage ID, outage scope (neighborhood, backbone, etc.).
- **Line state**: suspended, active, roaming-enabled, airplane-mode.
- **Device state**: network mode, data-saver on/off, mobile-data on/off, VPN connected, APN settings.
- **Bill state**: overdue amount, payment status.
- **Plan state**: data cap, roaming allowance, refuel eligibility.
- **Export-run state**: failure dates, error messages, credential status.
- **SLA records**: credit percentage, severity.

## Step 6 — Apply Decision Logic

### 6a. Ticket Resolution Domain

For each ticket, determine:

| Evidence | Decision |
|----------|----------|
| Account not found in `/api/accounts/{account_id}` | `final_resolution_status`: FAILED, `resolution_route`: INVALID_ACCOUNT, `key_blocker`: INVALID_ACCOUNT |
| Account found but ineligible (suspended, on hold, fraudulent) | `final_resolution_status`: FAILED, `resolution_route`: INELIGIBLE_ACCOUNT (or AUTH_FAILED / OVERDUE_SUSPENSION / FRAUD_SUSPENSION per the specific status) |
| Active outage matching the account's service area | `final_resolution_status`: PENDING_ACTION, `resolution_route`: OUTAGE_WAIT, `outage_id`: the active outage ID |
| Diagnostics show issues AND no active outage | `final_resolution_status`: RESOLVED, `resolution_route`: AUTO_TROUBLESHOOTING, `diagnostic_needed`: true, set boolean issue flags from diagnostic results |
| Diagnostics show issues that can't be auto-resolved | `final_resolution_status`: ESCALATED, `resolution_route`: ESCALATION, `escalation_team`: map from the blocker type (FIELD_OPS for physical, NETWORK_ENGINEERING for capacity, TIER2_SUPPORT for provisioning, ACCOUNTS_PAYABLE for billing) |

**Issue flag mapping** (from diagnostic/troubleshooting data):
- `latency_issue`: true when diagnostics or troubleshooting indicate latency problems.
- `stability_issue`: true when diagnostics or troubleshooting indicate stability/packet-loss problems.
- `bandwidth_issue`: true when diagnostics or troubleshooting indicate bandwidth/speed problems.
- `diagnostic_needed` / `diagnostic_required`: true when diagnostics were actually run and returned results.

### 6b. Mobile Support Domain (Contact Center / Data Recovery)

For each case, determine the primary action by matching the reported issue to device/line/plan state:

| Evidence from API | Primary Action |
|-------------------|---------------|
| Line shows no service / no signal | `RESEAT_SIM` or `TOGGLE_AIRPLANE_MODE` (check device airplane-mode state) |
| Line is suspended with an overdue bill | `SEND_PAYMENT_REQUEST` |
| Customer traveling, roaming off on line | `ENABLE_LINE_ROAMING` or `TOGGLE_ROAMING` |
| Messaging app can't send photos | `GRANT_MESSAGING_PERMISSION` with required permission from device state |
| Mobile data is on but slow, data-saver visible | `TOGGLE_DATA_SAVER` |
| Data slow on older network mode | `SET_NETWORK_MODE` |
| Mobile data toggled off | `TOGGLE_MOBILE_DATA` |
| Data stopped after hitting usage limit | `REFUEL_DATA` (use customer's accepted refuel amount or a default) |
| VPN connected and interfering | `DISCONNECT_VPN` |
| WiFi calling causing issues | `TOGGLE_WIFI_CALLING` |
| APN misconfigured after settings change | `RESET_APN_REBOOT` |
| No clear self-service fix applies | `TRANSFER_HUMAN` |

**Secondary action**: Usually `NO_ACTION` unless the primary action needs a follow-up. Common follow-up: after `SEND_PAYMENT_REQUEST`, add `RESUME_LINE_REBOOT` as the secondary action.

**Permissions**: Check the device or app state. If the primary action involves messaging and storage permission is needed, set `permission` to `storage`. If SMS permission is needed, set to `sms`. Both → `sms_and_storage`. Otherwise `NONE`.

**Billing context**: When the action involves a payment request or data refuel with a charge:
- Set `bill_id` to the relevant bill identifier.
- Set `charge_amount_usd` to the amount from the bill or the refuel cost.
- For data refuel, calculate `data_refuel_gb` and `charge_amount_usd` from plan/customer preferences.

**Final route classification**:
- `SELF_SERVICE` / `DEVICE_SETTING_FIX`: Actions the customer performs on their device (toggle, reseat, mode change).
- `BILLING_RECOVERY` / `DATA_RECOVERY`: Actions involving payments or data refuels.
- `CARRIER_UPDATE`: Actions requiring a carrier-side change (roaming enable, plan change).
- `HUMAN_TRANSFER`: Actions requiring human intervention.

### 6c. Enterprise Incident Domain

For an incident response:

1. **Fetch the incident** from `/api/enterprise/incidents/{incident_id}` to confirm it exists and get the enterprise account ID.

2. **Fetch export runs** from `/api/enterprise/export-runs` for the account. Identify the failed runs within the complaint window. The `failure_window` is the date range of consecutive failures; `failed_days` is the count of days in that range. `backfill_days` equals `failed_days` (the number of days that need manual backfill).

3. **Fetch messages** from `/api/enterprise/messages` related to the incident. Analyze the message content to determine `root_cause_category`. Look for phrases about credentials, rotation, permissions, configuration, timeout, quota, etc. Summarize in a concise phrase (e.g., "stale credential after rotation", "storage quota exceeded", "upstream API timeout").

4. **Check alert routing**: If messages reference an alert that was archived or routed incorrectly, set `contributing_alert_issue` accordingly (`ARCHIVED_ALERT_ROUTE`, `NONE`, or `UNKNOWN`).

5. **Fetch SLA** from `/api/enterprise/sla/{account_id}`. Extract `sla_credit_percent` and `severity`.

6. **Assign owners**: `engineering_owner` and `account_owner` are user identifiers (typically lowercase dot-separated names like `firstname.lastname`) found in the incident, export-run, or message records.

7. **Apply naming conventions**: Follow the naming style described in the response-requirements or inferred from examples:
   - `channel_name`: lowercase-hyphenated client name (e.g., "asteri-retail-inc").
   - `evidence_folder`: "{Client Name} {Month Year} Investigation".
   - `report_title`: "{Client Name} Export Failure - Resolution Report".

8. **Share permissions**: Map the users listed in the response requirements to their permission levels (`view` or `edit`). Preserve the listing order from the requirements.

9. **Response status**: Select based on the financial/review context:
   - SLA credit > 0% → `NEEDS_FINANCE_REVIEW`
   - Engineering uncertainty → `NEEDS_ENGINEERING_REVIEW`
   - Unclear root cause → `UNDER_INVESTIGATION`
   - Everything confirmed → `READY_TO_SEND`

### 6d. Queue Quality Domain

For queue-quality classification, cross-reference each ticket against the API and classify:

| Evidence | Classification |
|----------|---------------|
| Active outage matching ticket | `final_resolution_status`: PENDING_ACTION, `key_blocker`: ACTIVE_OUTAGE |
| Account not found | `final_resolution_status`: FAILED, `key_blocker`: INVALID_ACCOUNT |
| Account found but auth failed | `final_resolution_status`: FAILED, `key_blocker`: AUTH_FAILED |
| Account suspended — overdue | `final_resolution_status`: FAILED, `key_blocker`: OVERDUE_SUSPENSION, `route_team`: ACCOUNTS_PAYABLE |
| Account suspended — fraud | `final_resolution_status`: FAILED, `key_blocker`: FRAUD_SUSPENSION |
| Diagnostics pass and auto-fixable | `final_resolution_status`: RESOLVED, `route_team`: NONE |
| Network capacity / backbone issue | `final_resolution_status`: ESCALATED, `key_blocker`: NETWORK_CAPACITY, `route_team`: NETWORK_ENGINEERING |
| Provisioning issue | `final_resolution_status`: ESCALATED, `key_blocker`: PROVISIONING_STALE, `route_team`: TIER2_SUPPORT |
| Physical line fault | `final_resolution_status`: ESCALATED, `key_blocker`: PHYSICAL_LINE_FAULT, `route_team`: FIELD_OPS |

`diagnostic_required`: true when diagnostics were run for the ticket and returned data.

## Step 7 — Fill the Answer Template

For each work item, create one entry in the per-item array of the template. Preserve the payload order exactly. For every field:

- **String fields**: Copy the literal value from the API response.
- **Enum fields**: Choose exactly one value from the allowed set in the template.
- **Boolean fields**: Derive from API evidence (e.g., `diagnostic_needed` is true when diagnostics data exists).
- **Numeric fields**: Count or sum from the data (e.g., `failed_days`, `backfill_days`, `charge_amount_usd`, `data_refuel_gb`).
- **Empty/missing values**: Use `""` for empty strings, `0` or `0.0` for empty numbers, `false` for empty booleans, `NONE` for empty enums. Follow the exact type and format shown in the template.

## Step 8 — Compute Summaries

After filling all per-item entries, compute the aggregate summary object:

- Count entries by `final_resolution_status` (RESOLVED, PENDING_ACTION, ESCALATED, FAILED).
- Count entries by `route_team` or `final_route`.
- For customer-wait tickets: count items where `resolution_route` is `OUTAGE_WAIT`.
- For billing/data summaries: sum `charge_amount_usd` across all items.
- For data recovery: count `data_refuel_cases`, `carrier_updates`, `device_setting_fixes`, `human_transfers`.

Double-check that every count in the summary matches the per-item array.

## Step 9 — Output the JSON

Output only the filled JSON object. No markdown fences, no explanatory text, no preamble. The JSON must:
- Be valid JSON (double-quoted keys, no trailing commas).
- Conform exactly to the answer template schema.
- Preserve payload ordering.
- Have accurate summary counts that match the individual decisions.

## Common Pitfalls

- **Wrong endpoint for entity type**: Use `/api/tickets/{id}` for ticket tasks, `/api/contact-center/cases/{id}` for mobile case tasks, `/api/enterprise/incidents/{id}` for incident tasks. The catalog distinguishes these.
- **Preserving order**: Always iterate payload items in the order they appear; do not sort or reorder.
- **Enum typos**: Copy enum values exactly from the answer template's allowed set. Case and spelling must match.
- **Missing related lookups**: Always fetch diagnostics, troubleshooting, outages, bills, devices, etc. when the decision logic depends on them. A missing lookup leads to an incorrect decision.
- **Charge precision**: `charge_amount_usd` always has two decimal places (e.g., `86.40` not `86.4`).
- **GB precision**: `data_refuel_gb` always has one decimal place (e.g., `2.0` not `2`).
- **Forgetting the catalog**: Always query `/api/catalog` first. Field names and semantics are not always obvious from the endpoint path alone.
- **Summary mismatch**: Every summary count must be reconcilable against the per-item decisions. Re-count before finalizing.
