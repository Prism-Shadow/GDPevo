# Support Console Skill — SOP for Ticket/Case Resolution

## API Base
Use the harness-provided base URL (not localhost). All endpoints listed at `/api/catalog`.

## Core SOP: Always Fetch the Full Record Chain

For any ticket or case ID found in a payload, retrieve every linked record before deciding:
- **Wireline tickets**: `/api/tickets/<id>` → `/api/accounts/<account_id>` → `/api/diagnostics/<id>` → `/api/troubleshooting/<id>` → `/api/outages?service_area=<area>`
- **Mobile cases**: `/api/cases/<id>` → `/api/lines/<line_id>` → `/api/devices/<device_id>` → `/api/plans/<plan_id>` → `/api/bills` (filter by customer_id)
- **Enterprise incidents**: `/api/enterprise/incidents/<id>` → `/api/enterprise/accounts` (filter by name) → `/api/enterprise/export-runs?incident_id=<id>` → `/api/enterprise/messages?query=<keyword>` → `/api/enterprise/sla/<enterprise_account_id>`

## Wireline Ticket Resolution Rules

### Outage-First Rule
When `GET /api/outages?service_area=<area>` returns an active outage whose `service_types` includes the ticket's `service_type`, the outage explains the issue. Set ALL technical boolean flags (`latency_issue`, `stability_issue`, `bandwidth_issue`, `diagnostic_needed`) to **false** — do not double-count symptoms already explained by the outage.
- Status: `PENDING_ACTION`
- Route: `OUTAGE_WAIT`
- Escalation team: `NONE`
- Key blocker (train_004): `ACTIVE_OUTAGE`

### Account Status Rules
- **Suspended account** → `FAILED`, resolution route `INELIGIBLE_ACCOUNT`, escalation team `ACCOUNTS_PAYABLE`. Set all boolean flags false.
- **Account not found (404)** → `FAILED`, key blocker `INVALID_ACCOUNT`, route team `NONE`.
- **Authentication failure** (`last_login_status: "FAILURE"`, `account_recovery_status: "FAILURE"`) → `FAILED`, key blocker `AUTH_FAILED`, route team `NONE`.
- **Overdue suspension** → `FAILED`, key blocker `OVERDUE_SUSPENSION`.

### Diagnostic Root Cause → Resolution Mapping
Match the diagnostic `root_causes` array to the resolution:

| Root Cause | Resolution Status | Escalation / Route |
|---|---|---|
| `CONFIGURATION_DRIFT` | `RESOLVED` if troubleshooting improved metrics | `AUTO_TROUBLESHOOTING` |
| `FIBER_DROP_DAMAGE`, `SIGNAL_LOSS` | `ESCALATED` | `FIELD_OPS` / `ESCALATION` |
| `BACKBONE_CAPACITY` | `ESCALATED` | `NETWORK_ENGINEERING` / key blocker `NETWORK_CAPACITY` |
| `PROVISIONING_STALE` | `ESCALATED` | `TIER2_SUPPORT` / key blocker `PROVISIONING_STALE` |
| Physical line fault | `ESCALATED` | `FIELD_OPS` / key blocker `PHYSICAL_LINE_FAULT` |

### Boolean Flag Thresholds (Wireline)
- `latency_issue`: true when diagnostic latency > ~100 ms
- `stability_issue`: true when diagnostic jitter > ~30 ms
- `bandwidth_issue`: true when diagnostic bandwidth significantly below `subscribed_mbps`
- `diagnostic_needed` / `diagnostic_required`: false when root cause is external (outage, account status, auth); true when diagnostic found actionable technical root cause

## Mobile Case Resolution Rules

### Device State → Action Mapping

| Device State | Primary Action | Notes |
|---|---|---|
| `sim_status: "missing"` | `RESEAT_SIM` | Common after commute/travel |
| Line `status: "Suspended"` + `suspension_reason: "OVERDUE_BILL"` | `SEND_PAYMENT_REQUEST` | Secondary: `RESUME_LINE_REBOOT`; route: `BILLING_RECOVERY` |
| `phone_roaming_enabled: false` (line roaming on) | `TOGGLE_ROAMING` | Phone-side toggle; route: `SELF_SERVICE` |
| Line `roaming_enabled: false` (phone roaming on) | `ENABLE_LINE_ROAMING` | Carrier-side change; `carrier_update_required: true`; route: `CARRIER_UPDATE` |
| `can_send_mms: false` + `messaging_permissions.storage: false` | `GRANT_MESSAGING_PERMISSION` | Permission: `storage`; route: `SELF_SERVICE` |
| `vpn_connected: true` + slow data | `DISCONNECT_VPN` | Route: `SELF_SERVICE` / `DEVICE_SETTING_FIX` |
| `data_saver_mode: true` + slow data | `TOGGLE_DATA_SAVER` | Route: `DEVICE_SETTING_FIX` |
| `network_mode_preference: "3g_only"` + slow | `SET_NETWORK_MODE` | Route: `DEVICE_SETTING_FIX` |
| `mobile_data_enabled: false` | `TOGGLE_MOBILE_DATA` | Route: `DEVICE_SETTING_FIX` |
| `data_used_gb` > plan `data_limit_gb` | `REFUEL_DATA` | Use customer_preferences for GB amount; charge = GB × `data_refueling_price_per_gb` |

### Data Refuel Calculation
- `data_refuel_gb`: from `customer_preferences.<case_id>.accepted_refuel_gb` (one decimal)
- `charge_amount_usd`: refuel GB × plan's `data_refueling_price_per_gb` (two decimals)
- Route: `DATA_RECOVERY`
- `carrier_update_required`: false (refuel is not a carrier update)

### Roaming Distinction (Critical)
Always check **both** the line and the device:
- `line.roaming_enabled` — carrier-side provisioning
- `device.phone_roaming_enabled` — phone-side toggle
- If the line has roaming ON but phone has it OFF → `TOGGLE_ROAMING` (self-service, device setting)
- If the line has roaming OFF → `ENABLE_LINE_ROAMING` (carrier update required)

## Enterprise Incident Response Rules

### Data Gathering
1. Fetch incident → get `enterprise_account_id`, owners, severity, product
2. Fetch export runs filtered by `incident_id` → identify failed vs succeeded dates
3. Fetch SLA contract → get `credit_percent` for the product
4. Search messages by incident ID or keywords → find root cause narrative and channel name

### Field Conventions
- `root_cause_category`: use the `failure_code` from failed export runs or a concise label derived from message evidence
- `failure_window`: min and max `run_date` among failed runs; `failed_days` = count of distinct failed run dates
- `backfill_days`: equal to `failed_days` (each failed day needs backfill)
- `sla_credit_percent`: integer from the SLA contract's product-specific credit field
- `severity`: from the incident record
- `engineering_owner` / `account_owner`: from the incident record
- `channel_name`: the channel where the root-cause message was posted
- `contributing_alert_issue`: infer from message channel or alert routing evidence
- `evidence_folder` / `report_title`: follow the naming conventions in `response_requirements.json` (typically `client-date-investigation` and `client-export-failure-report` formats)
- `share_permissions`: users from `permission_users_to_include`, ordered as listed in requirements
- `response_status`: assess from completeness of evidence

## Output Format Conventions
- Always preserve payload order (ticket_id order from CSV, ascending case_id from JSON)
- Use empty string `""` for absent IDs (outage_id, bill_id), not null or omission
- Use `0.00` / `0.0` for numeric fields when not applicable
- Use `"NONE"` / `"NO_ACTION"` for absent enum values, never omit
- Summary counts must match the decision arrays exactly

## Common Pitfalls
1. **Double-counting outage symptoms**: When an active outage covers the service area and service type, do not set `latency_issue`, `bandwidth_issue`, etc. to true — the outage is the root cause.
2. **Confusing phone vs line roaming**: Read both `device.phone_roaming_enabled` and `line.roaming_enabled`; they are independent and have different fix actions.
3. **Missing account validation**: Always check `/api/accounts/<id>` returns a valid record; a 404 means `INVALID_ACCOUNT`.
4. **Ignoring customer preferences**: When `customer_preferences` is present in the payload, use it to determine refuel GB and whether plan changes are allowed.
5. **Wrong number format**: `charge_amount_usd` takes two decimals; `data_refuel_gb` takes one decimal.
6. **Overlooking the troubleshooting result**: Even when a diagnostic ran, check if the troubleshooting actually improved metrics to decide `RESOLVED` vs `PENDING_ACTION`.
