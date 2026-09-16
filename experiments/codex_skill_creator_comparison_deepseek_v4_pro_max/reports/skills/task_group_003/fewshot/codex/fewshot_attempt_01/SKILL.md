---
name: support-console
description: Resolve telecom support tasks using a shared support-console REST API. Use when the task involves service-ticket classification, mobile contact-center case resolution, enterprise incident investigation, queue-quality triage, mobile-data recovery, or any support-console record lookups. The skill covers accounts, tickets, diagnostics, troubleshooting, outages, customers, lines, devices, plans, bills, contact-center cases, enterprise accounts, incidents, export runs, messages, and SLA contracts.
---

# Support Console

## Overview

Resolve telecom support tasks against a shared REST API. Every task includes a `<TASK_ENV_BASE_URL>` placeholder that points to the running support-console instance (typically `http://task-env:9003/`). All data must come from API responses, never from assumptions.

## Essential Rules

1. Replace `<TASK_ENV_BASE_URL>` with the actual base URL provided in the task prompt.
2. Call the API for every record the task references; do not guess values.
3. Preserve payload ordering in output arrays unless the task explicitly says otherwise.
4. Output only JSON that conforms to the provided answer template.

## API Navigation

| Resource | List endpoint | Single-item endpoint |
|---|---|---|
| Tickets | `GET /api/tickets` | `GET /api/tickets/{ticket_id}` |
| Accounts | `GET /api/accounts` (via catalog) | `GET /api/accounts/{account_id}` |
| Outages | `GET /api/outages` | (list only) |
| Diagnostics | | `GET /api/diagnostics/{ticket_id}` |
| Troubleshooting | | `GET /api/troubleshooting/{ticket_id}` |
| Customers | `GET /api/customers` | `GET /api/customers/{customer_id}` |
| Lines | `GET /api/lines` | `GET /api/lines/{line_id}` |
| Devices | | `GET /api/devices/{device_id}` |
| Plans | | `GET /api/plans/{plan_id}` |
| Bills | `GET /api/bills` | `GET /api/bills/{bill_id}` |
| Cases | via catalog | `GET /api/contact-center/cases/{case_id}` |
| Enterprise accounts | `GET /api/enterprise/accounts` | `GET /api/enterprise/accounts/{account_id}` |
| Enterprise incidents | `GET /api/enterprise/incidents` | `GET /api/enterprise/incidents/{incident_id}` |
| Export runs | `GET /api/enterprise/export-runs` | (list only) |
| Messages | `GET /api/enterprise/messages` | (list only) |
| SLA | | `GET /api/enterprise/sla/{account_id}` |
| Catalog | `GET /api/catalog` | (system overview) |

For complete field-by-field schemas and record shapes, see [references/api_schemas.md](references/api_schemas.md).

## Task Workflows

### Service Ticket Resolution

Applies when the task provides a batch of ticket IDs and asks for resolution status, diagnostic needs, outage matching, escalations, and routing.

**For each ticket:**

1. `GET /api/tickets/{ticket_id}` to get `account_id`, `service_area`, `service_type`.
2. `GET /api/accounts/{account_id}` to check account status and authentication.
3. `GET /api/outages` and match against the ticket's `service_area` and `service_type`.
4. `GET /api/diagnostics/{ticket_id}` to see root causes and metrics.
5. `GET /api/troubleshooting/{ticket_id}` to see applied fixes and post-fix metrics.

**Decision rules:**

- **Account not found** (404 or unknown account_id): `FAILED` / `INVALID_ACCOUNT`
- **Account status `Suspended`**: `FAILED` / `INELIGIBLE_ACCOUNT`
- **Authentication failures** (`last_login_status: "FAILURE"`, `account_recovery_status: "FAILURE"`): `FAILED` / `AUTH_FAILED`
- **Active outage** matching the ticket's `service_area` and `service_type`: `PENDING_ACTION` / `OUTAGE_WAIT`. Set `outage_id` to the matching outage.
- **Diagnostics + troubleshooting fixable**: If diagnostics reveals a root cause that the troubleshooting steps successfully remediated (comparing pre/post metrics for improvement), mark `RESOLVED` / `AUTO_TROUBLESHOOTING`. Set boolean flags based on diagnostic metrics.
- **Structural/hardware root cause** where troubleshooting was inadequate: `ESCALATED`. Map root cause to escalation team:
  - `FIBER_DROP_DAMAGE`, `SIGNAL_LOSS`, `PHYSICAL_LINE_FAULT` → `FIELD_OPS`
  - `BACKBONE_CAPACITY`, `NETWORK_CAPACITY` → `NETWORK_ENGINEERING`
  - `PROVISIONING_STALE`, `CONFIGURATION_DRIFT` → `TIER2_SUPPORT`
- **Overdue suspension**: `FAILED` / `ACCOUNTS_PAYABLE` (if the schema supports it), key blocker `OVERDUE_SUSPENSION`.

When a task asks for a `batch_summary`, count results and also count tickets requiring customer wait (those marked `PENDING_ACTION`).

### Mobile Contact-Center Case Resolution

Applies when the task gives a case queue and asks for support actions.

**For each case:**

1. `GET /api/contact-center/cases/{case_id}` to get `line_id`, `customer_id`, `device_id`, `issue_type`.
2. `GET /api/lines/{line_id}` for status, roaming, suspension reason, plan.
3. `GET /api/devices/{device_id}` for signal, sim, VPN, data saver, messaging permissions, network mode, mobile data, roaming.
4. `GET /api/bills` (or per-customer bills) to check for overdue bills.
5. `GET /api/plans/{plan_id}` for plan limits and pricing.

**Action selection by issue pattern:**

| Symptom | Likely cause | Primary action | Notes |
|---|---|---|---|
| No service after commute/travel | SIM dislodged | `RESEAT_SIM` | Confirm with `sim_status: "missing"` |
| Line suspended, user willing to pay | Overdue bill | `SEND_PAYMENT_REQUEST` + `RESUME_LINE_REBOOT` | Find overdue bill, set `bill_id`, `charge_amount_usd` |
| Traveling abroad, no data | Roaming off on device or line | `TOGGLE_ROAMING` (device-side) or `ENABLE_LINE_ROAMING` (line-side) | Check both `line.roaming_enabled` and `device.phone_roaming_enabled` |
| Cannot send photos/MMS | Missing storage permission | `GRANT_MESSAGING_PERMISSION` | Check `device.messaging_permissions.storage`, set `permission` field |
| Slow data with VPN running | VPN throttling | `DISCONNECT_VPN` | Confirm `device.vpn_connected: true` |
| Slow data, data-saver icon | Data saver active | `TOGGLE_DATA_SAVER` | Confirm `device.data_saver_mode: true` |
| Slow data, old network mode | 3G-only mode | `SET_NETWORK_MODE` | Confirm `device.network_mode_preference` set to legacy |
| No data, mobile data off | Toggle needed | `TOGGLE_MOBILE_DATA` | Confirm `device.mobile_data_enabled: false` |
| Data limit reached | Need refuel | `REFUEL_DATA` | Compare `line.data_used_gb` vs `plan.data_limit_gb` |

Set `secondary_action` to `NO_ACTION` unless a clear follow-up is identified.

Set `final_route`:
- Device-side fixes (toggle, reseat, VPN, data saver, network mode) → `SELF_SERVICE`
- Billing/payment actions → `BILLING_RECOVERY`
- Line-side roaming/carrier changes → `CARRIER_UPDATE`
- Complex issues requiring a person → `HUMAN_TRANSFER`

### Enterprise Incident Investigation

Applies when a client has an export failure or similar enterprise incident and a formal response package must be assembled.

**Workflow:**

1. Identify the incident ID from the complaint (may be approximate, search `/api/enterprise/incidents`).
2. `GET /api/enterprise/incidents/{incident_id}` for severity, owners, account_id, product.
3. `GET /api/enterprise/accounts/{account_id}` for account_owner, name, tier.
4. `GET /api/enterprise/export-runs` and filter by `enterprise_account_id` and `incident_id` to find the failure window.
5. `GET /api/enterprise/messages` and filter by incident-related message IDs or channels/accounts to find root cause details and SLA information.
6. `GET /api/enterprise/sla/{account_id}` for the credit percentage.

**Naming conventions (when requirements specify a style):**

- `channel_name`: lowercase-hyphenated version of the client organization name (e.g., "Example Corp" → `example-corp`)
- `evidence_folder`: `{Client Name} {Month Year} Investigation` (e.g., "Example Corp May 2026 Investigation")
- `report_title`: `{Client Name} Export Failure - Resolution Report`

**Share permissions:** Assign `view` or `edit` to listed users based on role; read permission designations from the task requirements.

**Response status:**
- `NEEDS_FINANCE_REVIEW` when SLA credits are involved and the task involves billing/credit handling
- `NEEDS_ENGINEERING_REVIEW` when root cause has an engineering owner
- `READY_TO_SEND` when all information is confirmed
- `UNDER_INVESTIGATION` when evidence is still being collected

**Root cause:** Derive from `failure_code` on failed export runs combined with message bodies. Map `STALE_CREDENTIAL` → "stale credential after rotation", `STAGING_STORAGE_QUOTA` → "storage quota exceeded".

**Failure window:** Find consecutive failed runs by date. `start_date` is the first failed run date, `end_date` is the last, `failed_days` is the count.

**Backfill:** Equal to `failed_days` unless evidence shows partial recovery.

**Contributing alert issue:** `ARCHIVED_ALERT_ROUTE` when messages mention an alert/export channel that appears in the archive; otherwise `NONE` or `UNKNOWN`.

### Queue Quality Triage

Applies when classifying tickets before SLA handoff.

Follow the same data-gathering steps as Service Ticket Resolution, but classify with `key_blocker` instead of full resolution detail. The `key_blocker` enum values:

- `ACTIVE_OUTAGE` — matching active outage on service_area + service_type
- `INVALID_ACCOUNT` — account not found
- `AUTH_FAILED` — authentication permanently failed
- `OVERDUE_SUSPENSION` — account suspended due to overdue bill
- `FRAUD_SUSPENSION` — account suspended for fraud
- `NETWORK_CAPACITY` — backbone/capacity root cause
- `PROVISIONING_STALE` — provisioning mismatch
- `PHYSICAL_LINE_FAULT` — fiber drop or physical damage
- `NONE` — no blocking issue found (ticket resolvable)

Map `key_blocker` to `route_team`:
- `ACTIVE_OUTAGE` → `NONE` (awaiting resolution)
- `INVALID_ACCOUNT` → `NONE`
- `AUTH_FAILED` → `NONE`
- `OVERDUE_SUSPENSION` → `ACCOUNTS_PAYABLE`
- `NETWORK_CAPACITY` → `NETWORK_ENGINEERING`
- `PROVISIONING_STALE` → `TIER2_SUPPORT`
- `PHYSICAL_LINE_FAULT` → `FIELD_OPS`

Set `diagnostic_required: true` when diagnostics are needed for further investigation (voice profile issues, backbone capacity, provisioning mismatches). Set `false` for outages, invalid accounts, auth failures, and overdue suspensions where diagnostics add no value.

`final_resolution_status`:
- `PENDING_ACTION` for active outages (waiting for outage resolution)
- `RESOLVED` for tickets where diagnostics + troubleshooting show improvement and no structural blocker remains
- `ESCALATED` for tickets needing specialist teams
- `FAILED` for invalid accounts, auth failures, overdue suspensions

### Mobile Data Recovery

Applies when a worklist of mobile data cases needs resolution with data refuel calculations.

**For each case:**

1. `GET /api/contact-center/cases/{case_id}` for line_id, device_id, issue_type, customer_location.
2. `GET /api/lines/{line_id}` for data_used_gb, status, roaming_enabled.
3. `GET /api/devices/{device_id}` for the full device state.
4. `GET /api/plans/{plan_id}` for data_limit_gb and data_refueling_price_per_gb.

**Action selection mirrors Mobile Contact-Center cases with these additions:**

- **Data refuel**: When `line.data_used_gb > plan.data_limit_gb`, use `REFUEL_DATA`. Check task payload for accepted refuel GB. Calculate charge: `accepted_gb × plan.data_refueling_price_per_gb`. Set `data_refuel_gb` and `charge_amount_usd`.
- **Line roaming missing**: When customer is abroad and `line.roaming_enabled: false`, use `ENABLE_LINE_ROAMING`, `carrier_update_required: true`.
- **Device-setting fixes**: `TOGGLE_DATA_SAVER`, `SET_NETWORK_MODE`, `TOGGLE_MOBILE_DATA`, `DISCONNECT_VPN` — these are `DEVICE_SETTING_FIX` routes.

**final_route values:**
- `DATA_RECOVERY` for refuel operations
- `CARRIER_UPDATE` for line-side roaming changes
- `DEVICE_SETTING_FIX` for device toggles
- `HUMAN_TRANSFER` for cases requiring a person

## Reference

For detailed API schemas with every field and data type, see [references/api_schemas.md](references/api_schemas.md).
