---
name: support-console-analyst
description: Resolve offline support tickets, contact-center cases, enterprise incidents, queue-quality reviews, and mobile-data recovery from a telecom support console API. Covers ticket triage, mobile-device troubleshooting, billing recovery, enterprise export incident response, and queue classification.
---

# Support Console Analyst

Resolve support operations tasks using a shared telecom support-console REST API at
the base URL provided in `<TASK_ENV_BASE_URL>`. Every task follows the same
pattern: read the payload files, fetch live evidence from the API, apply the
decision rules below, and return JSON conforming to the answer template.

**Core rule**: decisions must be grounded in API evidence, never in assumption.
When an API result provides a value, prefer it over payload hints.

## API Quick Reference

All endpoints are GET and return JSON arrays or single objects. Key endpoints by
task family:

| Task family | Primary endpoints | Supporting endpoints |
|---|---|---|
| Ticket triage | `/api/tickets/{id}`, `/api/accounts/{id}`, `/api/diagnostics/{id}`, `/api/troubleshooting/{id}` | `/api/outages` |
| Contact-center cases | `/api/cases/{id}`, `/api/customers`, `/api/lines/{id}`, `/api/devices/{id}` | `/api/plans/{id}`, `/api/bills` |
| Enterprise incidents | `/api/enterprise/incidents/{id}`, `/api/enterprise/accounts`, `/api/enterprise/export-runs`, `/api/enterprise/messages` | `/api/enterprise/sla/{account_id}` |
| Queue quality | `/api/tickets/{id}`, `/api/accounts/{id}`, `/api/diagnostics/{id}` | `/api/outages` |
| Mobile data recovery | `/api/cases/{id}`, `/api/lines/{id}`, `/api/devices/{id}`, `/api/plans/{id}` | `/api/bills`, `/api/customers` |

**Tip**: the catalog at `/api/catalog` lists all endpoints and record counts;
use it to confirm the API shape when in doubt.

The expected response shapes for each endpoint are documented in
[api_schemas.md](api_schemas.md).

## General Workflow

1. **Read the payload files** to identify which entities need resolution.
2. **Read the answer template** to know the exact output schema.
3. **Fetch API evidence** for each entity. Parallelize fetches for entities
   that do not depend on one another.
4. **Apply the decision rules** for the task family (see sections below).
5. **Fill the answer template** in the order given (ticket IDs, case IDs, etc.).
6. **Compute the summary** counts from the per-entity decisions.

Never skip fetching an API endpoint that the decision rules require. When an
entity references an ID that produces no API result, treat it as a not-found
condition (see rule tables for the consequence).

## Task Family: Ticket Triage

Payoff answers the question: for each open ticket, what is the resolution status,
route, and which service-quality flags are set?

### Entity Resolution Steps

For each ticket in the batch:

1. `GET /api/tickets/{ticket_id}` — confirms the ticket exists and gives
   `account_id`, `service_area`, `service_type`, `subscribed_mbps`.
2. `GET /api/accounts/{account_id}` — reveals `status` (Active / Suspended),
   `authentication.last_login_status`, `authentication.account_recovery_status`.
3. `GET /api/outages` — list all active outages. Cross-reference:
   an outage covers the ticket when the ticket's `service_area` matches the
   outage's `service_area` **and** the ticket's `service_type` appears in the
   outage's `service_types`.
4. `GET /api/diagnostics/{ticket_id}` — yields `root_causes`, pre-fix
   `latency_ms`, `jitter_ms`, `bandwidth_mbps`.
5. `GET /api/troubleshooting/{ticket_id}` — yields `steps` taken and
   post-fix metrics.

### Decision Table

Evaluate in order; the first matching row wins.

| Condition | Resolution | Route | Flags | Escalation |
|---|---|---|---|---|
| Account not found (404 on `/api/accounts/{id}`) | FAILED | INVALID_ACCOUNT | all false | NONE |
| Account `status` = `Suspended` | FAILED | INELIGIBLE_ACCOUNT | all false | NONE |
| Ticket covered by an active outage | PENDING_ACTION | OUTAGE_WAIT | all false | NONE |
| Diagnostic `root_causes` includes `FIBER_DROP_DAMAGE` or `SIGNAL_LOSS` | ESCALATED | ESCALATION | `diagnostic_needed`=true, other flags from diagnostics | FIELD_OPS |
| Diagnostic `root_causes` includes `BACKBONE_CAPACITY` | ESCALATED | ESCALATION | `diagnostic_needed`=true, other flags from diagnostics | NETWORK_ENGINEERING |
| Diagnostic `root_causes` includes `PROVISIONING_STALE` | ESCALATED | ESCALATION | `diagnostic_needed`=true, other flags from diagnostics | TIER2_SUPPORT |
| Diagnostic completed and troubleshooting completed with improved post metrics | RESOLVED | AUTO_TROUBLESHOOTING | `diagnostic_needed`=true, set flags from diagnostics | NONE |
| Troubleshooting attempted but post metrics still degraded | ESCALATED | ESCALATION | `diagnostic_needed`=true, set flags from diagnostics | Map root cause to team per above |

### Flag Derivation

When `diagnostic_needed` is true, derive boolean flags from diagnostics:

- **latency_issue**: `latency_ms` > 100.
- **stability_issue**: `jitter_ms` > 30.
- **bandwidth_issue**: `bandwidth_mbps` < 85% of `subscribed_mbps` from the
  ticket record.

These flags reflect the *pre-troubleshooting* state. Compute them from the
diagnostics endpoint, not from troubleshooting.

### Outage Id

When a ticket is covered by an outage, set `outage_id` to the matching outage's
id. Otherwise use the empty string `""`.

## Task Family: Contact-Center Cases

Payoff answers the question: for each case, what support action should be taken
next, what billing charge applies, and what is the final route?

### Entity Resolution Steps

For each case in the queue:

1. `GET /api/cases/{case_id}` — yields `customer_id`, `line_id`, `device_id`,
   `issue_type`, `customer_location`, `summary`.
2. For efficiency: read `/api/customers`, `/api/lines`, `/api/bills`,
   `/api/devices`, `/api/plans` once and index by id. Or fetch singletons.
3. `GET /api/lines/{line_id}` — yields `status`, `suspension_reason`,
   `roaming_enabled`, `data_used_gb`, `plan_id`.
4. `GET /api/devices/{device_id}` — yields `sim_status`, `messaging_permissions`,
   `can_send_mms`, `vpn_connected`, `signal_strength`, `speed_test`,
   `phone_roaming_enabled`, `airplane_mode`, `data_saver_mode`,
   `network_mode_preference`, `mobile_data_enabled`.
5. `GET /api/bills` and filter by `customer_id` — yields `amount_due_usd`,
   `status` (Paid / Overdue), `bill_id`.

### Decision Table

Evaluate in order. For each case, pick the *single* best primary action based
on evidence.

| Condition | Primary Action | Secondary Action | Bill Id | Charge | Route |
|---|---|---|---|---|---|
| Device `sim_status` = `missing` | RESEAT_SIM | NO_ACTION | "" | 0.0 | SELF_SERVICE |
| Line `status` = `Suspended` and `suspension_reason` = `OVERDUE_BILL` | SEND_PAYMENT_REQUEST | RESUME_LINE_REBOOT | overdue bill id | overdue bill `amount_due_usd` | BILLING_RECOVERY |
| Customer abroad (`customer_location` = `abroad`) and line `roaming_enabled` = false | ENABLE_LINE_ROAMING | NO_ACTION | "" | 0.0 | SELF_SERVICE |
| Customer abroad and `phone_roaming_enabled` = true and line `roaming_enabled` = true but no data | TOGGLE_ROAMING | NO_ACTION | "" | 0.0 | SELF_SERVICE |
| Device `can_send_mms` = false or `messaging_permissions.storage` = false | GRANT_MESSAGING_PERMISSION | NO_ACTION | "" | 0.0 | SELF_SERVICE |
| Device `data_saver_mode` = true | TOGGLE_DATA_SAVER | NO_ACTION | "" | 0.0 | SELF_SERVICE |
| Device `vpn_connected` = true | DISCONNECT_VPN | NO_ACTION | "" | 0.0 | SELF_SERVICE |
| Device `network_mode_preference` set to legacy (e.g. `3g_only`) | SET_NETWORK_MODE | NO_ACTION | "" | 0.0 | SELF_SERVICE |
| Device `mobile_data_enabled` = false | TOGGLE_MOBILE_DATA | NO_ACTION | "" | 0.0 | SELF_SERVICE |
| None of the above (genuinely unclear) | TRANSFER_HUMAN | NO_ACTION | "" | 0.0 | HUMAN_TRANSFER |

### Permissions

Set the `permission` field based on the device's `messaging_permissions`:
- If `storage` is false and the action is GRANT_MESSAGING_PERMISSION → `storage`
- If `sms` is false and the action is GRANT_MESSAGING_PERMISSION → `sms`
- If both are false → `sms_and_storage`
- Otherwise → `NONE`

### Final Route Mapping

| Route | Condition |
|---|---|
| SELF_SERVICE | Primary action is a device-side fix (RESEAT_SIM, TOGGLE_ROAMING, GRANT_MESSAGING_PERMISSION, DISCONNECT_VPN, TOGGLE_DATA_SAVER, SET_NETWORK_MODE, TOGGLE_MOBILE_DATA, ENABLE_LINE_ROAMING) |
| BILLING_RECOVERY | Primary action is SEND_PAYMENT_REQUEST |
| CARRIER_UPDATE | Primary action requires a carrier-side provisioning change |
| HUMAN_TRANSFER | Primary action is TRANSFER_HUMAN |

## Task Family: Enterprise Incident Response

Payoff produces a structured response package for an export-failure complaint.

### Entity Resolution Steps

1. Extract the incident reference ID and client name from the complaint email.
2. `GET /api/enterprise/incidents/{incident_id}` — yields `enterprise_account_id`,
   `engineering_owner`, `account_owner`, `severity`, `product`, `status`, `summary`.
3. `GET /api/enterprise/accounts` — find the matching account to confirm
   `name`, `account_owner`, `finance_owner`.
4. `GET /api/enterprise/export-runs` — filter by `incident_id` and
   `enterprise_account_id`. The failed runs define the `failure_window` and
   the failure codes give the `root_cause_category`.
5. `GET /api/enterprise/messages` — filter by incident (look for matching
   body/author references). Messages identify the alert channel and SLA
   credit terms.
6. `GET /api/enterprise/sla/{enterprise_account_id}` — confirms
   `monthly_export_credit_percent` and credit trigger.

### Field Derivation

| Output field | Derivation |
|---|---|
| `incident_id` | From complaint email reference or payload requirements. |
| `enterprise_account_id` | From `/api/enterprise/incidents/{id}` → `enterprise_account_id`. |
| `root_cause_category` | Read the `failure_code` from the failed export runs. Translate: `STALE_CREDENTIAL` → "stale credential after rotation"; `STAGING_STORAGE_QUOTA` → "staging storage quota exceeded". Use the actual failure code text when no mapping is known. |
| `contributing_alert_issue` | If a message referencing the incident appears in a channel whose name contains `archive` → `ARCHIVED_ALERT_ROUTE`; otherwise `NONE` or `UNKNOWN` based on evidence availability. |
| `failure_window.start_date` | Earliest failed run `run_date`. |
| `failure_window.end_date` | Latest failed run `run_date`. |
| `failure_window.failed_days` | Count of distinct failed run dates. |
| `backfill_days` | Same as `failed_days` (each failed day needs backfill). |
| `sla_credit_percent` | From `/api/enterprise/sla/{id}` → `monthly_export_credit_percent`, as a number. |
| `severity` | From the incident endpoint; preserve exact value (Critical, High, Medium, Low). |
| `engineering_owner` | From the incident endpoint. |
| `account_owner` | From the incident endpoint. |
| `channel_name` | From the naming convention in the response requirements payload: lowercase, hyphen-separated version of the enterprise account name. E.g. "Asteri Retail Inc." → "asteri-retail-inc". |
| `evidence_folder` | From naming convention: `{Enterprise Account Name} {month year} Investigation` using the month of the failure. |
| `report_title` | From naming convention: `{Enterprise Account Name} Export Failure - Resolution Report`. |
| `share_permissions` | List users from the response requirements payload, ordered as specified. Assign `view` to finance stakeholders, `edit` to engineering stakeholders. |
| `response_status` | If an SLA credit > 0% is involved and finance review is standard process → `NEEDS_FINANCE_REVIEW`. If root cause is unclear → `UNDER_INVESTIGATION`. If engineering review is pending → `NEEDS_ENGINEERING_REVIEW`. If fully documented → `READY_TO_SEND`. |

## Task Family: Queue Quality Review

Payoff classifies each ticket into a resolution status, routes it to the right
team, and identifies the key blocker.

### Entity Resolution Steps

For each ticket in the snapshot:

1. `GET /api/tickets/{ticket_id}` — confirms existence, yields `account_id`.
2. `GET /api/accounts/{account_id}` — yields `status`, `authentication`.
3. `GET /api/outages` — cross-reference as in Ticket Triage.
4. `GET /api/diagnostics/{ticket_id}` — yields `root_causes`, pre-fix metrics.
5. `GET /api/troubleshooting/{ticket_id}` — yields `steps`, post-fix metrics.

### Decision Table

Evaluate in order; first match wins.

| Condition | Status | Route Team | Key Blocker | Diagnostic |
|---|---|---|---|---|
| Account not found (404 on `/api/accounts/{id}`) | FAILED | NONE | INVALID_ACCOUNT | false |
| Account `authentication.last_login_status` = `FAILURE` | FAILED | NONE | AUTH_FAILED | false |
| Account `status` = `Suspended` | FAILED | ACCOUNTS_PAYABLE | OVERDUE_SUSPENSION | false |
| Ticket covered by an active outage | PENDING_ACTION | NONE | ACTIVE_OUTAGE | false |
| Diagnostic `root_causes` includes `FIBER_DROP_DAMAGE` or `SIGNAL_LOSS` | ESCALATED | FIELD_OPS | PHYSICAL_LINE_FAULT | true |
| Diagnostic `root_causes` includes `BACKBONE_CAPACITY` | ESCALATED | NETWORK_ENGINEERING | NETWORK_CAPACITY | true |
| Diagnostic `root_causes` includes `PROVISIONING_STALE` | ESCALATED | TIER2_SUPPORT | PROVISIONING_STALE | true |
| Diagnostic completed with root cause found, and troubleshooting resolved (post metrics within acceptable range: latency < 100, jitter < 30, bandwidth >= 85% of subscribed) | RESOLVED | NONE | NONE | true |
| Troubleshooting attempted but post metrics still degraded | ESCALATED | Map root cause to team per above | Map root cause to blocker per above | true |

### Key Blocker Mapping

| Diagnostic Root Cause | Key Blocker |
|---|---|
| `FIBER_DROP_DAMAGE`, `SIGNAL_LOSS` | PHYSICAL_LINE_FAULT |
| `BACKBONE_CAPACITY` | NETWORK_CAPACITY |
| `PROVISIONING_STALE` | PROVISIONING_STALE |
| `CONFIGURATION_DRIFT`, `VOICE_PROFILE_STALE`, `GENERATED_NOISE` (fully resolved) | NONE |
| Active outage match | ACTIVE_OUTAGE |
| Account auth failure | AUTH_FAILED |
| Invalid account ID | INVALID_ACCOUNT |
| Account Suspended | OVERDUE_SUSPENSION |

## Task Family: Mobile Data Recovery

Payoff resolves mobile-data issues using device diagnostics, line state, and
plan limits.

### Entity Resolution Steps

For each case in the worklist:

1. `GET /api/cases/{case_id}` — yields `line_id`, `device_id`, `customer_id`,
   `issue_type`, `customer_location`.
2. `GET /api/lines/{line_id}` — yields `data_used_gb`, `plan_id`,
   `roaming_enabled`, `status`.
3. `GET /api/devices/{device_id}` — yields `mobile_data_enabled`,
   `data_saver_mode`, `network_mode_preference`, `phone_roaming_enabled`,
   `vpn_connected`, `sim_status`.
4. `GET /api/plans/{plan_id}` — yields `data_limit_gb`,
   `data_refueling_price_per_gb`.
5. `GET /api/bills` by `customer_id` when billing status is needed.

### Decision Table

Evaluate in order for each case:

| Condition | Primary | Secondary | Refuel GB | Charge | Carrier Update | Route |
|---|---|---|---|---|---|---|
| Line `data_used_gb` > plan `data_limit_gb` (data exhausted) | REFUEL_DATA | NO_ACTION | From customer_preferences in payload, or 0.0 | refuel_gb × `data_refueling_price_per_gb` | false | DATA_RECOVERY |
| Customer abroad (`customer_location` = `abroad`) and line `roaming_enabled` = false | ENABLE_LINE_ROAMING | NO_ACTION | 0.0 | 0.0 | true | CARRIER_UPDATE |
| Device `data_saver_mode` = true | TOGGLE_DATA_SAVER | NO_ACTION | 0.0 | 0.0 | false | DEVICE_SETTING_FIX |
| Device `network_mode_preference` set to legacy (`3g_only`, `2g_only`) | SET_NETWORK_MODE | NO_ACTION | 0.0 | 0.0 | false | DEVICE_SETTING_FIX |
| Device `mobile_data_enabled` = false | TOGGLE_MOBILE_DATA | NO_ACTION | 0.0 | 0.0 | false | DEVICE_SETTING_FIX |
| Device `vpn_connected` = true | DISCONNECT_VPN | NO_ACTION | 0.0 | 0.0 | false | DEVICE_SETTING_FIX |
| None of the above | TRANSFER_HUMAN | NO_ACTION | 0.0 | 0.0 | false | HUMAN_TRANSFER |

### Charge Calculation

Only for `REFUEL_DATA`: multiply `data_refuel_gb` × `data_refueling_price_per_gb`.
Round to two decimal places. For all other actions charge is 0.0.

The `data_refuel_gb` is normally taken from the `customer_preferences` map in
the payload. If the customer accepted a specific refuel amount, use it.
Otherwise default to 0.0.

### Carrier Update

Set `carrier_update_required` = true only when the fix changes carrier-side
provisioning (e.g. `ENABLE_LINE_ROAMING`). Device-side fixes do not need it.

## Summary Computations

Every task requires a summary object. Compute counts by iterating the
per-entity decisions:

- Count each distinct status / route / category.
- For ticket triage: `tickets_requiring_customer_wait` = count of
  `PENDING_ACTION` tickets (those waiting on an outage).
- For mobile data recovery: `total_estimated_customer_charge_usd` = sum of all
  `charge_amount_usd` values, rounded to two decimal places.
- For all summaries: ensure every status/route/category key from the template
  appears with an integer count (0 when none match).

## Consistency Checks

Before finalising, verify:

1. **Every entity from the payload appears** in the decisions array, in the
   order the payload lists them.
2. **Enum values match the template exactly** — case, spelling, underscore
   placement.
3. **All summary keys are present** with integer counts that sum to the total
   number of entities.
4. **Empty strings are `""` not omitted** for fields like `outage_id`,
   `bill_id`, etc.
5. **Numeric rounding**: charge amounts and refuel GB to the precision stated
   in the template (two decimals for USD, one decimal for GB).
6. **Boolean fields** are `true` / `false` (lowercase), never `"true"` or `1`.
7. **Accurate IDs**: every derived ID (customer_id, line_id, account_id,
   bill_id) comes from an API response, not from the payload.

## Troubleshooting

| Symptom | Likely fix |
|---|---|
| API returns 404 | Check whether the ID is valid or if the endpoint path is correct (the catalog at `/api/catalog` lists available paths). |
| Duplicate entity IDs | Fetch list endpoints once and index by ID; the API surfaces shared records. |
| Missing bill for a customer | Bills are indexed by `customer_id`. If multiple exist, prefer the one with status `Overdue` for billing-recovery cases; otherwise use the most recent by `due_date`. |
| Export runs return many accounts | Always filter by both `incident_id` and `enterprise_account_id`. |
| SLA endpoint returns 404 | Check the enterprise account ID; only enterprise-tier accounts have SLA contracts. |

## Post-Fill Checklist

Run through this before writing the final JSON:

- [ ] All payload entities represented in order.
- [ ] Every required field from the answer template present.
- [ ] Enum values match the template's spelling exactly.
- [ ] Summary counts add up to the entity count.
- [ ] All monetary values rounded to two decimal places.
- [ ] All boolean values lowercase `true`/`false`.
- [ ] Empty strings used where template expects them (`""` not omitted).
- [ ] No hardcoded values from training examples.
