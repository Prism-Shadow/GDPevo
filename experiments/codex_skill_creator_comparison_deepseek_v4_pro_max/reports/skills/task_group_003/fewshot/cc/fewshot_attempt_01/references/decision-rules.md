# Decision Rules Reference

This document formalizes the evidence-to-decision mappings for every domain.
Use these rules to translate API responses into template-compliant decisions.

## Service ticket decision tree

For each ticket, follow this sequence in order. Stop at the first rule that
triggers; later rules only apply when earlier ones do not match.

### 1. Account validity gate

Check `GET /api/accounts/{account_id}`.

- If the endpoint returns 404 or the account record does not exist:
  final_resolution_status = `FAILED`
  key_blocker = `INVALID_ACCOUNT`
  resolution_route = `INELIGIBLE_ACCOUNT` (or `INVALID_ACCOUNT`)
  escalation_team = `NONE`
  Stop here.

- If `account.status` is `Suspended`:
  Check for overdue or fraud pattern.
  final_resolution_status = `FAILED`
  key_blocker = `OVERDUE_SUSPENSION` or `FRAUD_SUSPENSION`
  resolution_route = `INELIGIBLE_ACCOUNT`
  escalation_team = `ACCOUNTS_PAYABLE`
  Stop here.

- If `account.authentication.last_login_status` is `FAILURE`:
  final_resolution_status = `FAILED`
  key_blocker = `AUTH_FAILED`
  resolution_route = `AUTH_FAILED`
  escalation_team = `NONE`
  Stop here.

### 2. Active outage check

Fetch `GET /api/outages` and filter for `active: true` records where
`service_area` matches the ticket's service area AND `service_types` array
includes the ticket's `service_type`.

If a matching active outage exists:
  final_resolution_status = `PENDING_ACTION`
  key_blocker = `ACTIVE_OUTAGE`
  resolution_route = `OUTAGE_WAIT`
  escalation_team = `NONE`
  outage_id = the matched outage ID
  diagnostic_needed = false
  Stop here.

### 3. Diagnostics check

Fetch `GET /api/diagnostics/{ticket_id}`.

If diagnostics exist (non-404), examine:
- `latency_ms > 100` or `jitter_ms > 30` -> `latency_issue: true`
- `jitter_ms > 30` or `root_causes` include signal-related -> `stability_issue: true`
- `bandwidth_mbps` significantly below `subscribed_mbps` (e.g. < 80%) -> `bandwidth_issue: true`
- `root_causes` contains escalation-signaling values -> determine escalation team

If no diagnostics exist (404), set all flags to `false` and `diagnostic_needed: false`.

### 4. Troubleshooting check

Fetch `GET /api/troubleshooting/{ticket_id}`.

If troubleshooting exists (non-404):
- `steps[]` is non-empty AND `post_bandwidth_mbps` within range of `subscribed_mbps`
  AND post metrics improved:
  final_resolution_status = `RESOLVED`
  resolution_route = `AUTO_TROUBLESHOOTING`
  escalation_team = `NONE`
  diagnostic_needed = true (diagnostics were pulled)
  Stop here.

If troubleshooting steps exist but post metrics did not improve, or if no
troubleshooting record exists, the ticket needs escalation.

### 5. Escalation routing by root cause

Map the `root_causes[]` from diagnostics to escalation:

| Root cause | Escalation team | Key blocker |
|---|---|---|
| `PHYSICAL_LINE_FAULT` | `FIELD_OPS` | `PHYSICAL_LINE_FAULT` |
| `BACKBONE_CONGESTION` | `NETWORK_ENGINEERING` | `NETWORK_CAPACITY` |
| `PROVISIONING_MISMATCH` | `TIER2_SUPPORT` | `PROVISIONING_STALE` |
| `CONFIGURATION_DRIFT` | `TIER2_SUPPORT` or auto-resolved | `NONE` |

final_resolution_status = `ESCALATED`
resolution_route = `ESCALATION`
diagnostic_needed = true

If the root cause list is empty and no outage matches, but diagnostics show
issues, default to `TIER2_SUPPORT` escalation.

## Mobile case decision rules

### Symptom-to-action mapping

For each device field, map anomalies to primary actions:

| Device field / condition | Primary action | Route |
|---|---|---|
| `sim_status: missing` | `RESEAT_SIM` | SELF_SERVICE |
| `signal_strength: none` AND `airplane_mode: false` | `RESEAT_SIM` | SELF_SERVICE |
| `airplane_mode: true` with no-service complaint | `TOGGLE_AIRPLANE_MODE` | SELF_SERVICE |
| `mobile_data_enabled: false` with no/stopped data | `TOGGLE_MOBILE_DATA` | DEVICE_SETTING_FIX |
| `phone_roaming_enabled: false` AND case is travel | `TOGGLE_ROAMING` | SELF_SERVICE |
| `line.roaming_enabled: false` AND case is travel | `ENABLE_LINE_ROAMING` | CARRIER_UPDATE |
| `data_saver_mode: true` with slow data | `TOGGLE_DATA_SAVER` | DEVICE_SETTING_FIX |
| `network_mode_preference` contains `3g_only` | `SET_NETWORK_MODE` | DEVICE_SETTING_FIX |
| `vpn_connected: true` with slow data | `DISCONNECT_VPN` | DEVICE_SETTING_FIX |
| `can_send_mms: false` OR `messaging_permissions.storage: false` | `GRANT_MESSAGING_PERMISSION` | SELF_SERVICE |

### Line status rules

| Line condition | Primary action | Secondary action | Route |
|---|---|---|---|
| `status: Suspended` with `suspension_reason` about overdue | `SEND_PAYMENT_REQUEST` | `RESUME_LINE_REBOOT` | BILLING_RECOVERY |
| `status: Suspended` for other reasons | `TRANSFER_HUMAN` | `NO_ACTION` | HUMAN_TRANSFER |
| `data_used_gb` >= `plan.data_limit_gb` | `REFUEL_DATA` | `NO_ACTION` | DATA_RECOVERY |

### Charging rules

- Payment/billing actions: `charge_amount_usd` = `bill.amount_due_usd`
- Data refuel: `charge_amount_usd` = `refuel_gb * plan.data_refueling_price_per_gb`
- All other actions: `charge_amount_usd` = 0.0
- `bill_id` is set only for billing-related actions

### Permission rules

Set `permission` based on the action:
- `GRANT_MESSAGING_PERMISSION` for SMS issues -> `sms`
- `GRANT_MESSAGING_PERMISSION` for MMS/storage -> `storage`
- `GRANT_MESSAGING_PERMISSION` for both -> `sms_and_storage`
- All other actions -> `NONE`

### Route determination

| Action category | final_route |
|---|---|
| Device-toggle actions (TOGGLE_*, SET_*, RESEAT_SIM, DISCONNECT_VPN) | `SELF_SERVICE` or `DEVICE_SETTING_FIX` |
| Payment (SEND_PAYMENT_REQUEST) | `BILLING_RECOVERY` |
| Carrier-side roaming (ENABLE_LINE_ROAMING) | `CARRIER_UPDATE` |
| Data refuel (REFUEL_DATA) | `DATA_RECOVERY` |
| Human handoff (TRANSFER_HUMAN) | `HUMAN_TRANSFER` |

## Enterprise incident decision rules

### Root cause category derivation

From `GET /api/enterprise/export-runs`, extract the `failure_code` from the
failed runs. Map codes to human-readable categories:

| failure_code | root_cause_category |
|---|---|
| `STALE_CREDENTIAL` | stale credential after rotation |
| `STAGING_STORAGE_QUOTA` | staging storage quota exceeded |
| `PERMISSION_DENIED` | access permission revoked |
| `SCHEMA_MISMATCH` | schema mismatch after update |

### Contributing alert issue

Check `GET /api/enterprise/messages` for messages in channels that indicate
the alerting path:

- If the root cause message appeared in `export-alerts-archive`, the alert
  was routed to an archived channel -> `ARCHIVED_ALERT_ROUTE`
- If no relevant alert routing issue found -> `NONE`
- If unclear -> `UNKNOWN`

### Failure window

From the filtered export runs:
- `start_date` = earliest `run_date` with `status: FAILED`
- `end_date` = latest `run_date` with `status: FAILED`
- `failed_days` = count of distinct FAILED run dates

### SLA credit

From `GET /api/enterprise/sla/{enterprise_account_id}`:
- `sla_credit_percent` = `monthly_export_credit_percent`

### Backfill

`backfill_days` = number of days that failed (same as `failed_days`).

### Response status

- If `sla_credit_percent > 0` -> `NEEDS_FINANCE_REVIEW`
- Otherwise -> `READY_TO_SEND`

### Naming conventions

When the task provides naming requirements:
- Channel name: client company name, lowercase, hyphens for spaces
  (e.g. "Asteri Retail Inc." -> `asteri-retail-inc`)
- Evidence folder: "<Client Name> <Month Year> Investigation"
- Report title: "<Client Name> Export Failure - Resolution Report"

## Queue-quality classification rules

### Account check

Same gate as service ticket resolution Step 1.

### Outage check

Same as service ticket resolution Step 2. If active outage matches:
- key_blocker = `ACTIVE_OUTAGE`
- final_resolution_status = `PENDING_ACTION`
- route_team = `NONE`
- diagnostic_required = false

### Queue-note to blocker mapping

| Queue note pattern | key_blocker | diagnostic_required |
|---|---|---|
| "Neighborhood service interruption" -> match outage | `ACTIVE_OUTAGE` | false |
| "No matching account" | `INVALID_ACCOUNT` | false |
| "Authentication never recovered" | `AUTH_FAILED` | false |
| "Suspended after overdue" | `OVERDUE_SUSPENSION` | false |
| "Backbone capacity" | `NETWORK_CAPACITY` | true |
| "Provisioning mismatch" | `PROVISIONING_STALE` | true |
| "Drops calls" or video issue, no outage | Pull diagnostics, check root causes | true |
| "Nearby line work" with physical symptoms | `PHYSICAL_LINE_FAULT` | true |

### Blocker to route mapping

| key_blocker | route_team |
|---|---|
| `NONE` | `NONE` |
| `ACTIVE_OUTAGE` | `NONE` |
| `INVALID_ACCOUNT` | `NONE` |
| `AUTH_FAILED` | `NONE` |
| `NETWORK_CAPACITY` | `NETWORK_ENGINEERING` |
| `PROVISIONING_STALE` | `TIER2_SUPPORT` |
| `PHYSICAL_LINE_FAULT` | `FIELD_OPS` |
| `OVERDUE_SUSPENSION` | `ACCOUNTS_PAYABLE` |

### Status derivation

| Condition | final_resolution_status |
|---|---|
| key_blocker is ACTIVE_OUTAGE | PENDING_ACTION |
| Ticket resolved by troubleshooting | RESOLVED |
| key_blocker is INVALID_ACCOUNT, AUTH_FAILED, OVERDUE_SUSPENSION | FAILED |
| Escalation needed | ESCALATED |
