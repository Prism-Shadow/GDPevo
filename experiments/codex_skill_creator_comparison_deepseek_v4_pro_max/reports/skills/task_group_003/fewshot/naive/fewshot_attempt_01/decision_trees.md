
# Decision Trees

## Ticket resolution (train_001, train_004 pattern)

For each ticket in the batch, follow this sequence:

1. **Fetch ticket** (`/api/tickets/{id}`). Extract `account_id` and `service_type`.
2. **Fetch customer** (`/api/customers/{account_id}`).
   - If 404: classify as `FAILED` / `INELIGIBLE_ACCOUNT` (or `INVALID_ACCOUNT`) / `key_blocker: INVALID_ACCOUNT`. Skip remaining steps.
   - If `account_status` is `closed`, `suspended`, `fraud_hold`, or `overdue`: classify as `FAILED` / route to the appropriate team.
     - `overdue` → `ACCOUNTS_PAYABLE` / `key_blocker: OVERDUE_SUSPENSION`
     - `fraud_hold` → `FAILED` / `key_blocker: FRAUD_SUSPENSION`
     - `closed` → `FAILED` / `INELIGIBLE_ACCOUNT`
   - If `auth_status` is `failed`: classify as `FAILED` / `key_blocker: AUTH_FAILED`. Skip remaining steps.
3. **Check outages** (`/api/outages`).
   - If an active outage covers the ticket's `service_type`: classify as `PENDING_ACTION` / `OUTAGE_WAIT` / `key_blocker: ACTIVE_OUTAGE` / `diagnostic_required: false`. Include the `outage_id`. Skip remaining steps.
4. **Run diagnostics** (`/api/diagnostics/{id}`).
   - Set `diagnostic_needed` / `diagnostic_required` to `true`.
   - Set `latency_issue` from `latency_ms` exceeding normal threshold or error flags.
   - Set `stability_issue` from `packet_loss_percent` above zero or `stability_score` below threshold.
   - Set `bandwidth_issue` from `bandwidth_mbps` below plan expectation.
   - If diagnostics are clean and troubleshooting is available: classify as `RESOLVED` / `AUTO_TROUBLESHOOTING`.
5. **Check for physical/network escalation triggers** from diagnostics and ticket data:
   - Physical line fault evidence → `ESCALATED` / `FIELD_OPS` / `key_blocker: PHYSICAL_LINE_FAULT`
   - Network capacity or backbone errors → `ESCALATED` / `NETWORK_ENGINEERING` / `key_blocker: NETWORK_CAPACITY`
   - Provisioning mismatch or stale config → `ESCALATED` / `TIER2_SUPPORT` / `key_blocker: PROVISIONING_STALE`
6. **Compute summary** from decisions.

### Status-to-route mapping (train_004 quality review)

| Key Blocker | Route Team | Final Status |
|---|---|---|
| `ACTIVE_OUTAGE` | `NONE` | `PENDING_ACTION` |
| `INVALID_ACCOUNT` | `NONE` | `FAILED` |
| `AUTH_FAILED` | `NONE` | `FAILED` |
| `OVERDUE_SUSPENSION` | `ACCOUNTS_PAYABLE` | `FAILED` |
| `FRAUD_SUSPENSION` | `NONE` | `FAILED` |
| `NETWORK_CAPACITY` | `NETWORK_ENGINEERING` | `ESCALATED` |
| `PROVISIONING_STALE` | `TIER2_SUPPORT` | `ESCALATED` |
| `PHYSICAL_LINE_FAULT` | `FIELD_OPS` | `ESCALATED` |
| `NONE` (clean diagnostic) | `NONE` | `RESOLVED` |

## Mobile case triage (train_002, train_005 pattern)

For each case, query the case record, then follow the chain: customer → line → bill → plan → device. Match the reported issue to the root cause found in the API records.

### Symptom-to-action table

| Reported Issue | Likely Root Cause | Primary Action | Secondary Action | Check These Endpoints |
|---|---|---|---|---|
| No service | SIM not seated or line inactive | `RESEAT_SIM` | `NO_ACTION` | `/api/lines/{id}` for line status |
| Suspended line / overdue bill | Bill unpaid, line suspended | `SEND_PAYMENT_REQUEST` | `RESUME_LINE_REBOOT` | `/api/bills/{id}` for `total_due` and status |
| Cannot use data while traveling | Roaming not enabled on line | `TOGGLE_ROAMING` (device-side) or `ENABLE_LINE_ROAMING` (carrier-side) | `NO_ACTION` | `/api/lines/{id}` for `roaming_enabled`, `/api/plans/{id}` for `roaming_included` |
| Messaging app cannot send photos | Missing storage permission | `GRANT_MESSAGING_PERMISSION` | `NO_ACTION` | `/api/devices/{id}` for `messaging_permissions` |
| Slow data | VPN connected, data saver on, or old network mode | See slow-data sub-table below | `NO_ACTION` | `/api/lines/{id}` for VPN, data saver, network mode |
| Data stopped after limit | Plan data exhausted | `REFUEL_DATA` | `NO_ACTION` | `/api/plans/{id}` for data limit, `/api/lines/{id}` for usage |
| No data after settings change | Mobile data toggled off | `TOGGLE_MOBILE_DATA` | `NO_ACTION` | `/api/lines/{id}` for `mobile_data_enabled` |

### Slow-data sub-table

Check the line record in this priority order and pick the first match:

1. `vpn_connected: true` → `DISCONNECT_VPN`
2. `data_saver_enabled: true` → `TOGGLE_DATA_SAVER`
3. `network_mode` is older than the device's best supported mode → `SET_NETWORK_MODE`

### Roaming decision

- If `roaming_enabled` on the line is `false` and the plan includes roaming: use `ENABLE_LINE_ROAMING`, set `carrier_update_required: true`
- If `roaming_enabled` on the line is `true` but the device has roaming toggled off: use `TOGGLE_ROAMING`, no carrier update needed

### Data refuel calculation

When refueling data:
- The GB amount comes from `customer_preferences` in the payload if present, otherwise compute a reasonable top-up from plan `data_limit_gb`
- `charge_amount_usd` = `data_addon_rate_per_gb` × refuel GB (from plan record)
- `final_route` = `DATA_RECOVERY`

### Permissions

Check device `messaging_permissions`:
- If `storage` is `false` and the issue is photo sending: set `permission: "storage"`
- If `sms` is `false` and the issue is SMS: set `permission: "sms"`
- If both: set `permission: "sms_and_storage"`
- Otherwise: `permission: "NONE"`

### Route mapping

| Final Route | Condition |
|---|---|
| `SELF_SERVICE` | Device-side fix (SIM reseat, toggle, VPN, data saver, network mode) |
| `BILLING_RECOVERY` | Bill payment + line resume |
| `CARRIER_UPDATE` | Line-side roaming enable |
| `DATA_RECOVERY` | Data refuel |
| `DEVICE_SETTING_FIX` | Mobile data toggle, data saver, network mode, VPN disconnect |
| `HUMAN_TRANSFER` | Issue cannot be resolved with available operations |

## Enterprise incident response (train_003 pattern)

1. **Parse the complaint email** for client name, product, and incident reference.
2. **Find the incident** via `/api/enterprise/incidents/{incident_id}`. Extract `account_id`, `severity`, `root_cause_category`, `contributing_alert_issue`.
3. **Fetch account** via `/api/enterprise/accounts/{account_id}`. Extract `account_name`, `engineering_owner`, `account_owner`, `sla_tier`.
4. **Find the failure window** via `/api/enterprise/export-runs`. Filter by `account_id` and look for consecutive `status: "failed"` runs. The `start_date` and `end_date` are the first and last failed run dates. `failed_days` is the count of failed runs.
5. **Get SLA credit** via `/api/enterprise/sla/{account_id}`. Use `credit_percent` and `backfill_days`.
6. **Check contributing alerts** via `/api/enterprise/messages`. Filter by account and time window.
7. **Build response**:
   - `channel_name`: lowercase-hyphen version of `account_name` (e.g. "client-name-inc")
   - `evidence_folder`: "{Account Name} {Month Year} Investigation" (e.g. "Client Name March 2026 Investigation")
   - `report_title`: "{Account Name} Export Failure - Resolution Report"
   - `share_permissions`: use the `permission_users_to_include` from requirements, in listed order. First user gets `view`, second gets `edit` (unless requirements specify otherwise).
   - `response_status`: use the value derived from incident/SLA evidence (e.g. if SLA credit is non-zero and needs finance sign-off, `NEEDS_FINANCE_REVIEW`).

### Response status decision

- SLA credit > 0% and incident is Critical severity → `NEEDS_FINANCE_REVIEW`
- Root cause is engineering-related and not fully resolved → `NEEDS_ENGINEERING_REVIEW`
- Incident still open → `UNDER_INVESTIGATION`
- All clear → `READY_TO_SEND`
