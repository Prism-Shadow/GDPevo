---
name: support-console-resolver
description: Resolve support operations tasks using a shared REST support-console API. Use when the user is a support analyst, contact-center lead, enterprise support lead, queue-quality analyst, or mobile-data recovery analyst working from a ticket batch, case queue, complaint, queue snapshot, or mobile worklist against the support-console API. Also use when the task mentions offline service tickets, support console, contact center cases, enterprise export complaints, SLA reviews, or mobile data recovery worklists, even if the user does not explicitly name the API. Always fetch support-console records before classifying or deciding.
---

# Support Console Resolver

Resolve support operations tasks by querying a shared support-console REST API
at the base URL provided as `<TASK_ENV_BASE_URL>`, then producing structured
JSON that matches the supplied answer template.

## Overview

The support console is a read-only REST API. Every task follows the same
two-phase pattern:

1. **Collect evidence**: Read the worklist (CSV or JSON from a `payloads/`
   directory), then for every item fetch the relevant console records through
   the API.
2. **Decide and output**: Apply the decision rules that match the task domain to
   classify each item, then return JSON conforming to the supplied answer
   template.

Never guess a resolution without fetching the console records. Every decision
must be traceable to evidence from at least one API response.

## API Usage

The base URL arrives as `<TASK_ENV_BASE_URL>`. Replace it literally in every
request. All endpoints are GET only and require no authentication.

Always fetch the catalog first to confirm which endpoints are live:

```
GET <TASK_ENV_BASE_URL>/api/catalog
```

The exact endpoint set may vary between task environments; rely on the live
catalog, not a static list.

Full endpoint schemas and response shapes are documented in
[references/api_reference.md](references/api_reference.md). Read that file when
you need to know which fields an endpoint returns and what values to expect. It
also explains how record identifiers correlate across endpoints.

### Fetching Strategy

- When the worklist provides explicit IDs, use the single-record endpoints:
  `GET .../api/tickets/<ticket_id>`, `GET .../api/accounts/<account_id>`, etc.
- For lookup across a collection that lacks a direct filter (outages, export
  runs, messages), fetch the full list and filter in-memory by the field that
  connects the record to your current item (service_area for outages,
  enterprise_account_id for export runs).
- Do not fetch the full collection for domains that provide a direct
  single-record endpoint (tickets, accounts, lines, devices, plans, bills, cases,
  customers, incidents, enterprise accounts, SLA contracts). Use the collection
  endpoint only when you need to scan or filter. When scanning a collection,
  filter by the relationship field (customer_id, account_id, etc.) rather than
  downloading and inspecting every record randomly.

### Reading the Catalog

The `/api/catalog` response includes an `endpoints` list and a `record_counts`
object. The catalog is the authoritative list of which endpoints exist in this
environment; use it to plan your fetch set.

## Decision Rules by Task Domain

The support console covers several task domains. The domain is signaled by the
task prompt and the payload shape. Use the rules for the matching domain. If a
payload does not clearly match a single domain, read the task prompt carefully
and match the closest domain; the answer template shape is often the clearest
signal.

### Offline Service Tickets (Ticket Batch)

Triggered when the task prompt mentions a "ticket batch" and the worklist is a
CSV whose columns include `ticket_id, account_id` and describe individual
service complaints.

For each ticket, fetch in this order:

1. The ticket record (`/api/tickets/<ticket_id>`)
2. The account record (`/api/accounts/<account_id>`)
3. The full outage list (`/api/outages`); filter by the ticket's `service_area`
   and check whether any active outage covers the ticket's `service_type`
4. The diagnostic record (`/api/diagnostics/<ticket_id>`) -- always attempt this,
   even for suspended accounts; diagnostics may still return data
5. If diagnostics returned actionable root causes, the troubleshooting
   record (`/api/troubleshooting/<ticket_id>`)

Decision table (evaluate top-down; first match wins):

| Condition | Status | Route | Team |
|-----------|--------|-------|------|
| Account endpoint returns an error or 404 | FAILED | INELIGIBLE_ACCOUNT | NONE |
| Account `status` is `Suspended` | FAILED | INELIGIBLE_ACCOUNT | NONE |
| Active outage covers the ticket's `service_area` AND the outage's `service_types` includes the ticket's `service_type` | PENDING_ACTION | OUTAGE_WAIT | NONE |
| Diagnostics root cause includes FIBER_DROP_DAMAGE or SIGNAL_LOSS, AND troubleshooting post values are still degraded below subscription thresholds | ESCALATED | ESCALATION | FIELD_OPS |
| Diagnostics root cause includes BACKBONE_CAPACITY | ESCALATED | ESCALATION | NETWORK_ENGINEERING |
| Diagnostics root cause is actionable (CONFIGURATION_DRIFT, PROVISIONING_STALE) AND troubleshooting ran successfully with post values improved | RESOLVED | AUTO_TROUBLESHOOTING | NONE |
| Diagnostics root cause is actionable AND troubleshooting did not run or post values are still degraded | ESCALATED | ESCALATION | TIER2_SUPPORT |
| Last login status on account is `FAILURE` (check `authentication.last_login_status`) | FAILED | AUTH_FAILED | NONE |
| Account `status` is `Suspended` with a nonpayment indicator and no outage | FAILED | INELIGIBLE_ACCOUNT | ACCOUNTS_PAYABLE |

Boolean flags for each ticket come from the diagnostic evidence:

| Flag | Rule |
|------|------|
| `diagnostic_needed` | true when diagnostic root causes are actionable, i.e., not `GENERATED_NOISE` |
| `latency_issue` | true when `latency_ms` exceeds 80 ms, or post-troubleshooting latency exceeds 100 ms |
| `stability_issue` | true when `jitter_ms` exceeds 25 ms |
| `bandwidth_issue` | true when `bandwidth_mbps` falls below 70% of `subscribed_mbps` |
| `outage_id` | the matching outage ID when an active outage applies; empty string otherwise |

Escalation applies when a ticket requires a specialized team. Set
`escalation_team` to the matching team enum value; use `NONE` when no
escalation is needed.

### Queue Snapshot Review

Triggered when the task prompt mentions "queue snapshot" or "SLA handoff" and
the worklist is a CSV with columns including `ticket_id, account_id,
reported_service_type, queue_note`.

Fetch order is the same as offline service tickets, but the classification
model is simpler (four outcomes: FAILED, PENDING_ACTION, RESOLVED, or
ESCALATED with a route team):

| Condition | Status | Key Blocker | Route Team |
|-----------|--------|-------------|------------|
| Account ID returns 404 | FAILED | INVALID_ACCOUNT | NONE |
| Account `authentication.last_login_status` is `FAILURE` | FAILED | AUTH_FAILED | NONE |
| Account `status` is `Suspended` | FAILED | OVERDUE_SUSPENSION | ACCOUNTS_PAYABLE |
| Active outage covers the ticket's service_area and service_type | PENDING_ACTION | ACTIVE_OUTAGE | NONE |
| Diagnostics root cause is BACKBONE_CAPACITY | ESCALATED | NETWORK_CAPACITY | NETWORK_ENGINEERING |
| Diagnostics root cause is PROVISIONING_STALE | ESCALATED | PROVISIONING_STALE | TIER2_SUPPORT |
| Diagnostics returned actionable root causes (not GENERATED_NOISE) | RESOLVED | NONE | NONE |
| Fallthrough (no clear diagnostic signal) | FAILED | AUTH_FAILED | NONE |

`diagnostic_required` is true when the diagnostic record returned actionable
root causes and the account is reachable.

### Contact Center Cases

Triggered when the task prompt mentions "contact-center", "case queue", or
"support queue" and the worklist is a JSON array of case objects with fields
like `case_id` and `reported_issue`.

For each case, fetch in order:

1. The case record (`/api/cases/<case_id>`) -- gives `customer_id`, `line_id`,
   `device_id`
2. The line record (`/api/lines/<line_id>`)
3. The device record (`/api/devices/<device_id>`)
4. If line `status` is `Suspended`, fetch the bill list (`/api/bills`) and
   filter by `customer_id` to find the overdue bill
5. The plan record (`/api/plans/<plan_id>`) when data usage or refueling is
   relevant

Decision rules by issue pattern:

**SIM missing**: `sim_status` on device is `"missing"` -> primary_action =
`RESEAT_SIM`. The SIM may have dislodged; reseating it is the first step.

**Line suspended for overdue bill**: line `status` is `"Suspended"` and
`suspension_reason` is `"OVERDUE_BILL"` -> primary_action =
`SEND_PAYMENT_REQUEST`, secondary_action = `RESUME_LINE_REBOOT`. Find the
overdue bill (matching `customer_id`, `status: "Overdue"`) for `bill_id` and
`charge_amount_usd`. `final_route` = `BILLING_RECOVERY`.

**Traveler abroad, no data**: case `customer_location` is `"abroad"`. Check the
device `phone_roaming_enabled` and line `roaming_enabled`. When line roaming is
enabled but device roaming is off, primary_action = `TOGGLE_ROAMING`. When line
roaming itself is disabled, primary_action = `ENABLE_LINE_ROAMING` and
`carrier_update_required` = true.

**Cannot send MMS photos**: `can_send_mms` on device is `false` or a required
permission (`sms`, `storage`) is missing from `messaging_permissions` ->
primary_action = `GRANT_MESSAGING_PERMISSION`. Set `permission` to the missing
key (e.g., `"storage"` when `messaging_permissions.storage` is false).

**Slow data, VPN connected**: `vpn_connected` on device is `true` ->
primary_action = `DISCONNECT_VPN`. A corporate or personal VPN can throttle
mobile data throughput.

**Slow data, data saver active**: `data_saver_mode` on device is `true` ->
primary_action = `TOGGLE_DATA_SAVER`.

**Slow data, legacy network mode**: `network_mode_preference` is set to a
legacy value such as `"3g_only"` -> primary_action = `SET_NETWORK_MODE`.

**No data, mobile data toggled off**: `mobile_data_enabled` on device is
`false` -> primary_action = `TOGGLE_MOBILE_DATA`.

**Data exceeded plan limit**: line `data_used_gb` exceeds plan `data_limit_gb`
-> primary_action = `REFUEL_DATA`.

`final_route` classification:
- `SELF_SERVICE` -- device or line fixes the customer can apply themselves
- `BILLING_RECOVERY` -- payment was requested
- `CARRIER_UPDATE` -- a carrier-side change is needed (`carrier_update_required`)
- `DATA_RECOVERY` -- data was refueled
- `DEVICE_SETTING_FIX` -- data-saver, network mode, mobile data toggle, or VPN fix
- `HUMAN_TRANSFER` -- no automatic fix is available

`secondary_action` is `NO_ACTION` unless the same case needs a paired follow-up
operation (such as resuming a line after payment). `permission` is `NONE`
unless a messaging permission grant is the action.

### Mobile Data Recovery

Triggered when the task prompt mentions "mobile-data", "data recovery", or
"mobile data" and the worklist is a JSON array of mobile cases, often with an
accompanying `customer_preferences` object.

For each case, fetch in order:

1. The case record
2. The line record (check `data_used_gb` against plan limit, `roaming_enabled`)
3. The device record
4. The plan record (for data limit and `data_refueling_price_per_gb`)

Decision rules:

- **Data exceeded**: When `data_used_gb` > plan `data_limit_gb`, primary_action
  = `REFUEL_DATA`. Check `customer_preferences` for the accepted GB amount and
  whether the customer wants a plan change. `data_refuel_gb` = the accepted
  amount from preferences (default to 2.0 when not specified).
  `charge_amount_usd` = `data_refuel_gb` * `data_refueling_price_per_gb` from
  the plan. `final_route` = `DATA_RECOVERY`.

- **Traveler abroad, line roaming disabled**: line `roaming_enabled` is
  `false` -> primary_action = `ENABLE_LINE_ROAMING`, `carrier_update_required` =
  true, `final_route` = `CARRIER_UPDATE`.

- **Traveler abroad, phone roaming disabled but line roaming enabled**:
  device `phone_roaming_enabled` is `false` -> primary_action =
  `TOGGLE_ROAMING`, `final_route` = `SELF_SERVICE`.

- **Data saver on**: device `data_saver_mode` is `true` -> primary_action =
  `TOGGLE_DATA_SAVER`, `final_route` = `DEVICE_SETTING_FIX`.

- **Legacy network mode**: device `network_mode_preference` is a legacy value
  -> primary_action = `SET_NETWORK_MODE`, `final_route` = `DEVICE_SETTING_FIX`.

- **Mobile data toggled off**: device `mobile_data_enabled` is `false` ->
  primary_action = `TOGGLE_MOBILE_DATA`, `final_route` = `DEVICE_SETTING_FIX`.

`secondary_action` is `NO_ACTION` unless the case demands a paired follow-up.
`data_refuel_gb` is 0.0 when no refuel is performed. `charge_amount_usd` is
0.0 when no charge applies. `carrier_update_required` is true only when a
carrier-side change is part of the resolution.

### Enterprise Export Complaints

Triggered when the task prompt mentions "enterprise", "export complaint", or
"structured response package". The payload directory typically contains a
complaint email/text and a `response_requirements.json`.

From the complaint, extract:
- The incident identifier (e.g., `INC-...`)
- The enterprise client name

Then fetch in order:

1. The enterprise incident (`/api/enterprise/incidents/<incident_id>`)
2. The enterprise account (`/api/enterprise/accounts/<enterprise_account_id>`)
3. The export runs list (`/api/enterprise/export-runs`); filter by
   `enterprise_account_id` to find runs linked to the incident
4. The messages list (`/api/enterprise/messages`); filter by the enterprise
   account, incident, or related channels
5. The enterprise SLA contract (`/api/enterprise/sla/<enterprise_account_id>`)

Assemble the response fields:

| Field | How to determine |
|-------|-----------------|
| `incident_id` | From the complaint email |
| `enterprise_account_id` | From the incident record |
| `root_cause_category` | Synthesize from export-run `failure_code` and message body text. Common patterns: `"stale credential after rotation"` for STALE_CREDENTIAL + credential-rotation messages; `"storage quota exceeded"` for quota-related messages. |
| `contributing_alert_issue` | `ARCHIVED_ALERT_ROUTE` when incident-related messages appear in an archive- or alert-named channel; `NONE` otherwise |
| `failure_window` | The date range of consecutive FAILED export runs. `start_date` = first failed run date, `end_date` = last failed run date, `failed_days` = count of consecutive failed days |
| `backfill_days` | Equal to `failed_days` unless message evidence indicates more days affected |
| `sla_credit_percent` | From the enterprise SLA contract (`monthly_export_credit_percent`) |
| `severity` | From the incident record |
| `engineering_owner` | From the incident record |
| `account_owner` | From the incident record, or the enterprise account record when the incident record omits it |
| `channel_name` | The primary channel from the most relevant incident-related message |
| `evidence_folder` | Format as `"{Enterprise Name} {Month Year} Investigation"`, e.g., "Asteri Retail Inc. May 2026 Investigation" |
| `report_title` | Format as `"{Enterprise Name} Export Failure - Resolution Report"` |
| `share_permissions` | One entry per user listed in `response_requirements`; default permission is `view` |
| `response_status` | `NEEDS_FINANCE_REVIEW` when SLA credit applies; otherwise `READY_TO_SEND` |

**Naming conventions**: Use the pattern from the response requirements.
Typically the evidence folder uses the enterprise name from the account record
with the month and year of the failure window followed by "Investigation". The
report title uses the enterprise name followed by "Export Failure - Resolution
Report". Channel names use lowercase with hyphens.

## Answer Template

Every task provides an answer template (usually at
`payloads/answer_template.json`). The output must conform exactly to that
template's structure, field names, types, and enumeration values. Do not add or
omit fields.

Preserve the order of items from the worklist in the output array. The summary
section (`batch_summary`, `queue_summary`, or `worklist_summary`) counts items
by their final classification; derive counts from your own decisions, not from
any precomputed value.

Enumerated fields accept only the values listed in the template's type
annotations. When a value is not applicable, use the template's sentinel (empty
string `""`, `0.0`, `false`, or `"NO_ACTION"` / `"NONE"` as indicated by the
template).

## Verifying Your Work

After filling in every item, recheck each decision against its supporting API
evidence. If any decision lacks a clear evidentiary chain from at least one API
response, reconsider it. A decision that cannot be traced to an API response is
effectively a guess and will produce wrong answers under test conditions.
