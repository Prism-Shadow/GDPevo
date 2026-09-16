---
name: support-console
description: >
  Resolve telecom support-console decision tasks where the user provides a batch or queue payload (CSV/JSON),
  a strict JSON answer template, and a shared REST API at the TASK_ENV_BASE_URL for gathering evidence. Use this skill
  whenever the task involves service tickets, mobile support cases, enterprise incident investigations, or queue-quality
  classification that references a support-console API, even if the user does not explicitly name the console.
---

# Support Console Decision Solver

This skill covers the shared support-console REST API and the structured decision
workflows for resolving service tickets, mobile contact-center cases, enterprise
incident investigations, and queue-quality classification tasks.

## High-level workflow

Each task follows the same four-phase pattern:

1. **Read the payload** -- the input file (CSV, JSON, or plain text) listing the
   items that need decisions.
2. **Read the answer template** -- the JSON schema you must conform to. Every
   field, enum, and structure constraint in it is binding.
3. **Gather evidence from the API** -- query console endpoints for each item to
   collect diagnostics, account state, line/device data, outages, enterprise
   records, or messages as the task demands.
4. **Produce the answer** -- fill the template with evidence-backed decisions,
   preserving the exact field names, enum values, and item ordering specified in
   the template. Return only the JSON; no commentary.

## API surface

All endpoints live under the base URL provided as `<TASK_ENV_BASE_URL>` in the
prompt. Every endpoint is a read-only GET. The full catalog is available at
`/api/catalog`, but the key endpoints are organized by domain below.

Before making decisions, query every endpoint relevant to the payload items.
Never assume a value; always look it up.

For a complete reference of every endpoint, response field, and record shape,
read [references/api-surface.md](references/api-surface.md).

### Service-ticket endpoints

| Endpoint | Key fields returned |
|---|---|
| `GET /api/tickets/{ticket_id}` | `account_id`, `service_type`, `service_area`, `subscribed_mbps`, `status` |
| `GET /api/accounts/{account_id}` | `name`, `status`, `service_area`, `authentication.last_login_status`, `tier` |
| `GET /api/diagnostics/{ticket_id}` | `bandwidth_mbps`, `latency_ms`, `jitter_ms`, `root_causes[]` |
| `GET /api/troubleshooting/{ticket_id}` | `steps[]`, `post_bandwidth_mbps`, `post_latency_ms`, `post_jitter_ms` |
| `GET /api/outages` | `outage_id`, `service_area`, `service_types[]`, `active`, `eta_hours`, `impact_score` |

### Mobile / contact-center endpoints

| Endpoint | Key fields returned |
|---|---|
| `GET /api/cases/{case_id}` | `customer_id`, `line_id`, `device_id`, `issue_type`, `summary` |
| `GET /api/customers/{customer_id}` | `name`, `phone_number`, `status` |
| `GET /api/lines/{line_id}` | `customer_id`, `device_id`, `plan_id`, `status`, `roaming_enabled`, `suspension_reason`, `data_used_gb` |
| `GET /api/devices/{device_id}` | `model`, `sim_status`, `signal_strength`, `mobile_data_enabled`, `data_saver_mode`, `network_mode_preference`, `phone_roaming_enabled`, `vpn_connected`, `messaging_permissions`, `can_send_mms`, `mmsc_url_present` |
| `GET /api/plans/{plan_id}` | `name`, `data_limit_gb`, `data_refueling_price_per_gb`, `monthly_price_usd` |
| `GET /api/bills` | `bill_id`, `customer_id`, `amount_due_usd`, `status`, `due_date` |

### Enterprise endpoints

| Endpoint | Key fields returned |
|---|---|
| `GET /api/enterprise/accounts/{account_id}` | `name`, `account_owner`, `finance_owner`, `tier` |
| `GET /api/enterprise/incidents/{incident_id}` | `enterprise_account_id`, `product`, `severity`, `status`, `engineering_owner`, `account_owner`, `summary` |
| `GET /api/enterprise/export-runs` | `enterprise_account_id`, `incident_id`, `run_date`, `status`, `failure_code`, `exported_record_count` |
| `GET /api/enterprise/messages` | `author`, `body`, `channel`, `created_at` |
| `GET /api/enterprise/sla/{enterprise_account_id}` | `credit_trigger`, `monthly_export_credit_percent`, `executive_contact` |

### Supplementary endpoints

| Endpoint | Use |
|---|---|
| `GET /api/accounts` | List all accounts (for existence check) |
| `GET /api/customers` | List all customers |
| `GET /api/bills` | List all bills (filter by `customer_id` in response) |
| `GET /api/lines` | List all lines (not in catalog but available) |
| `GET /api/outages` | List all outages (filter by `service_area` and `active`) |

## Entity relationship map

Understanding which IDs connect to which records is critical. Here is the
relationship graph:

```
Service Tickets:
  ticket_id -> /api/tickets/{ticket_id}  ->  account_id
                                            service_area, service_type
  ticket_id -> /api/diagnostics/{ticket_id}
  ticket_id -> /api/troubleshooting/{ticket_id}
  account_id -> /api/accounts/{account_id}
  service_area -> /api/outages (filter by service_area, service_types)

Mobile Cases:
  case_id -> /api/cases/{case_id} -> customer_id, line_id, device_id
  customer_id -> /api/customers/{customer_id}
  line_id -> /api/lines/{line_id} -> plan_id
  device_id -> /api/devices/{device_id}
  plan_id -> /api/plans/{plan_id}
  customer_id -> /api/bills (filter by customer_id)

Enterprise Incidents:
  incident_id -> /api/enterprise/incidents/{incident_id} -> enterprise_account_id
  enterprise_account_id -> /api/enterprise/accounts/{enterprise_account_id}
  enterprise_account_id -> /api/enterprise/sla/{enterprise_account_id}
  enterprise_account_id -> /api/enterprise/export-runs (filter by account and incident)
  incident_id -> /api/enterprise/messages (filter by incident-related channel/body)
```

For search endpoints (`/api/outages`, `/api/bills`, `/api/enterprise/export-runs`,
`/api/enterprise/messages`), get the full list and filter in memory using the
relevant foreign key (`service_area`, `customer_id`, `enterprise_account_id`,
`incident_id`). Do not assume pagination; the lists are small enough to read
in one request.

## Decision workflows

Detailed decision rules for each domain live in
[references/decision-rules.md](references/decision-rules.md). Below are the
core patterns.

### Service ticket resolution

For each ticket, follow this evidence chain:

1. Check the account first. If the account ID is invalid (no matching record),
   the ticket is `FAILED` with route `INELIGIBLE_ACCOUNT` or `INVALID_ACCOUNT`.
   If the account status is suspended or authentication shows `FAILURE`, route
   accordingly.

2. If the account is valid, check for active outages that match the ticket's
   `service_area` and `service_type`. An active outage means the ticket should
   be `PENDING_ACTION` (wait for outage resolution).

3. If no outage applies, pull diagnostics for the ticket. Examine latency,
   jitter, and bandwidth against the subscribed rate. Root causes in
   `root_causes[]` tell you what went wrong. If diagnostics show issues,
   set relevant flags (`latency_issue`, `bandwidth_issue`, `stability_issue`).

4. Pull troubleshooting results. If troubleshooting completed with improved
   metrics, the ticket is `RESOLVED` via `AUTO_TROUBLESHOOTING`. If
   troubleshooting failed or the issue requires physical work, escalate to
   the team suggested by the root cause (`FIELD_OPS` for physical line faults,
   `NETWORK_ENGINEERING` for backbone capacity, `TIER2_SUPPORT` for provisioning).

5. Never guess the outcome. Every decision must be traceable to a specific
   API response field.

### Mobile case resolution

For each mobile case, trace the entity chain (`case -> line -> device -> plan`)
and check for bills:

1. Read the case summary and `issue_type` as a starting hypothesis.

2. Check the line status first. If suspended with an overdue reason, find the
   bill by matching `customer_id` against the bills list. The appropriate action
   is `SEND_PAYMENT_REQUEST` with `RESUME_LINE_REBOOT` as follow-up. The bill
   amount drives `charge_amount_usd`.

3. If active, inspect the device state for the specific symptom:
   - `sim_status: "missing"` -> SIM reseat
   - `signal_strength: "none"` with `airplane_mode: false` -> SIM reseat or airplane mode toggle
   - `mobile_data_enabled: false` -> toggle mobile data
   - `phone_roaming_enabled` false when traveler abroad -> toggle or enable roaming
   - `line.roaming_enabled` false for traveler -> enable line roaming (carrier-side)
   - `data_saver_mode: true` -> toggle data saver
   - `network_mode_preference` older than available -> set network mode
   - `vpn_connected: true` -> disconnect VPN
   - `messaging_permissions.storage` false when can't send photos -> grant permission

4. For data-cap issues, compare `line.data_used_gb` against `plan.data_limit_gb`.
   If at or near the limit, `REFUEL_DATA`. Use customer preferences if provided
   in the payload. Charge is `refuel_gb * plan.data_refueling_price_per_gb`.

5. `final_route` is determined by the action type:
   - Device-side settings -> `SELF_SERVICE` or `DEVICE_SETTING_FIX`
   - Payment-related -> `BILLING_RECOVERY`
   - Roaming enable on the line -> `CARRIER_UPDATE`
   - Data refuel -> `DATA_RECOVERY`
   - Anything requiring human judgment -> `HUMAN_TRANSFER`

### Enterprise incident investigation

For enterprise complaints, reconstruct the full incident timeline:

1. Match the complaint's incident reference to the incident record. This gives
   the `enterprise_account_id`, severity, and assigned owners.

2. Pull the enterprise account for the account owner and finance owner names.

3. Pull the SLA contract to get the credit trigger and credit percentage.

4. Pull export runs filtered by `enterprise_account_id` and `incident_id`.
   The failed runs define the failure window (earliest to latest failed date).
   The `failure_code` on each run tells you the root cause category. The number
   of failed days is `backfill_days`.

5. Pull messages. Look for messages authored by incident owners or referencing
   the incident's product/account. These provide the root-cause narrative and
   the credit justification. Messages in `export-alerts-archive` often contain
   the technical root cause.

6. Determine the contributing alert issue: if a message about the root cause
   appeared in `export-alerts-archive`, check whether that channel name suggests
   archived routing (`ARCHIVED_ALERT_ROUTE`).

7. Build the response package using naming conventions from the requirements:
   - Channel name: client name in lowercase hyphen form
   - Evidence folder: client name + date + "Investigation"
   - Report title: client name + "Export Failure - Resolution Report"
   - Share permissions: exactly the users listed in requirements in order
   - `response_status`: use `NEEDS_FINANCE_REVIEW` when an SLA credit is
     involved; `READY_TO_SEND` otherwise.

### Queue-quality classification

For queue-quality tasks, classify each ticket by its primary blocker:

1. For each ticket, check the account and outage status the same way as service
   ticket resolution.

2. Map queue-note patterns to blocker types:
   - "Neighborhood service interruption" -> check outages -> `ACTIVE_OUTAGE`
   - "No matching account" -> `INVALID_ACCOUNT`
   - "Authentication never recovered" -> check auth status -> `AUTH_FAILED`
   - "Suspended after overdue" -> `OVERDUE_SUSPENSION`
   - "Backbone capacity" -> check diagnostics -> `NETWORK_CAPACITY`
   - "Provisioning mismatch" -> check diagnostics -> `PROVISIONING_STALE`
   - Voice/video issues with no outage -> pull diagnostics and troubleshooting

3. If a specific blocker is found, set `diagnostic_required: false` (the
   blocker is already known). If the note is ambiguous and the ticket needs
   diagnosis to determine the path, set `diagnostic_required: true`.

4. Escalation routes follow the blocker:
   - `NETWORK_CAPACITY` -> `NETWORK_ENGINEERING`
   - `PROVISIONING_STALE` -> `TIER2_SUPPORT`
   - `PHYSICAL_LINE_FAULT` -> `FIELD_OPS`
   - `OVERDUE_SUSPENSION` -> `ACCOUNTS_PAYABLE`

## Answer construction rules

These rules apply to every task type:

- **Preserve payload item order** in the output array. The template says
  "preserve payload order" or "preserve ascending case_id order" -- follow
  that exactly.

- **Include every field from the template**, even if the value is an empty
  string, `0.0`, `false`, or `"NONE"`. Do not omit optional-seeming fields.

- **Enum values are case-sensitive**. Copy them exactly as written in the
  template.

- **Counts in summaries** must match the decisions. After filling the item
  array, tally the summary counts from the decisions you made.

- **`charge_amount_usd` and `data_refuel_gb`**: always include as numbers with
  the specified decimal precision. Use `0.0` or `0.00` when not applicable,
  never omit.

- **Only return the JSON**. Do not wrap it in markdown fences, do not add
  explanatory text. The output is machine-read.

## General guidelines

- Query the API for every piece of evidence. Even if the payload note seems
  clear, cross-check it against the console records.
- When an API returns an empty response or a 404, treat the record as
  nonexistent.
- For list endpoints like `/api/outages` and `/api/bills`, fetch the full list
  and filter client-side. There is no server-side filtering.
- If a template field has no matching console evidence, use the zero-value for
  its type (`""`, `false`, `0`, `"NONE"`).
- The `/api/catalog` endpoint is informational. It shows available endpoints
  and record counts but not task-specific data. It is a discovery aid, not
  evidence for decisions.
