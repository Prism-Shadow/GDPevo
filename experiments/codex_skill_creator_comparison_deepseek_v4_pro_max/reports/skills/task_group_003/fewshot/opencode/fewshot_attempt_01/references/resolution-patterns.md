# Resolution Patterns

How to map API evidence to template output fields for each task type.

## Ticket Resolution

Ticket templates typically require: `final_resolution_status`, `diagnostic_needed`,
`latency_issue`, `stability_issue`, `bandwidth_issue`, `outage_id`,
`escalation_team`, `resolution_route`, plus an `account_id`.

### Step 1: Fetch Primary Records

For each ticket in the payload, fetch `GET /api/tickets/{ticket_id}` in parallel.
Also fetch `GET /api/outages` to get the full active outage list.

### Step 2: Check for Active Outage

Before fetching diagnostics, check whether the ticket's `account_id` appears in
any active outage's `affected_accounts` array. If it does:

- `final_resolution_status`: `PENDING_ACTION`
- `outage_id`: the matching outage's ID
- `resolution_route`: `OUTAGE_WAIT`
- `diagnostic_needed`: `false`
- `latency_issue`, `stability_issue`, `bandwidth_issue`: `false`
- `escalation_team`: `NONE`

An active outage takes priority; do not fetch diagnostics for this ticket.

### Step 3: When No Outage Matches, Fetch Diagnostics

Fetch `GET /api/diagnostics/{ticket_id}` and
`GET /api/troubleshooting/{ticket_id}` in parallel.

### Step 4: Classify the Ticket From API Evidence

**Diagnostic flags** (`latency_issue`, `stability_issue`, `bandwidth_issue`):
Set each to `true` when the diagnostic response shows a clear problem in that
dimension. For example, high latency_ms or jitter_ms for `latency_issue`, low
stability_score or pattern of drops for `stability_issue`, low bandwidth_mbps
for `bandwidth_issue`. Use `true` when the value crosses an obviously abnormal
threshold and `false` when it is within normal range.

**`diagnostic_needed`**: Set `true` when you actually fetched and needed the
diagnostic. Set `false` when the ticket was resolved by outage match or account
validation without needing diagnostics.

**Troubleshooting-driven classification:**

- If the troubleshooting report says `fixable` is true:
  - `final_resolution_status`: `RESOLVED`
  - `resolution_route`: `AUTO_TROUBLESHOOTING`
  - `escalation_team`: `NONE`

- If the troubleshooting report says `fixable` is false and provides
  `required_team`:
  - `final_resolution_status`: `ESCALATED`
  - `resolution_route`: `ESCALATION`
  - `escalation_team`: map `required_team` to the template enum. Common
    mappings: a team like "field_ops" becomes `FIELD_OPS`, "network_engineering"
    becomes `NETWORK_ENGINEERING`, "tier2_support" becomes `TIER2_SUPPORT`,
    "accounts_payable" becomes `ACCOUNTS_PAYABLE`.

### Step 5: Account Validation

When the ticket's `account_id` does not resolve to a valid account, or the
account has a status that blocks resolution (suspended, invalid, ineligible):

- `final_resolution_status`: `FAILED`
- `resolution_route`: map to the appropriate failure route from the template
  (e.g. `INELIGIBLE_ACCOUNT`, `INVALID_ACCOUNT`, `AUTH_FAILED`,
  `OVERDUE_SUSPENSION`)
- `escalation_team`: `NONE` (unless the template specifically calls for a
  routing team like `ACCOUNTS_PAYABLE` for overdue suspensions)
- All issue flags: `false`
- `diagnostic_needed`: `false`

Account validation failure takes priority over diagnostics. If the account
record is missing, returns an error, or shows a blocked status, classify as
FAILED without fetching diagnostics.

### Queue-Quality Audit Variant

When the template uses `key_blocker` and `route_team` instead of
`escalation_team` and `resolution_route`, the same logic applies with different
field names:

- Active outage → `key_blocker`: `ACTIVE_OUTAGE`, `route_team`: `NONE`
- Auto-troubleshooting fixable → `key_blocker`: `NONE`, `route_team`: `NONE`
- Troubleshooting not fixable → `key_blocker`: map from the underlying cause,
  `route_team`: map from `required_team`
- Invalid/missing account → `key_blocker`: `INVALID_ACCOUNT`
- Auth failure → `key_blocker`: `AUTH_FAILED`
- Overdue suspension → `key_blocker`: `OVERDUE_SUSPENSION`,
  `route_team`: `ACCOUNTS_PAYABLE`
- Capacity issue → `key_blocker`: `NETWORK_CAPACITY`,
  `route_team`: `NETWORK_ENGINEERING`
- Provisioning issue → `key_blocker`: `PROVISIONING_STALE`,
  `route_team`: `TIER2_SUPPORT`

### Summary Computation

After all tickets are classified, tally each `final_resolution_status` value
for the summary counts. For `tickets_requiring_customer_wait`, count tickets
where `final_resolution_status` is `PENDING_ACTION` (the customer must wait for
the outage to clear).

## Case Triage

Case templates typically require: `primary_action`, `secondary_action`,
`permission`, `bill_id`, `charge_amount_usd`, `final_route`, plus
`customer_id` and `line_id` from the API.

### Step 1: Fetch Records

For each case, fetch `GET /api/cases/{case_id}` to get `customer_id` and
`line_id`. Then fetch `GET /api/customers/{customer_id}` and
`GET /api/lines/{line_id}` in parallel. From the line record, note any
`bill_id`, `plan_id`, or `device_id` references and fetch those in a second
parallel wave.

### Step 2: Classify by Line State

The line record is the primary decision driver. Map the line's state to
`primary_action` and `final_route`:

**Line is active but shows no service or connectivity problems:**
- SIM/APN issues: use `RESEAT_SIM` or `RESET_APN_REBOOT`
- The reported issue helps distinguish: "no service after commute" suggests
  SIM reseating; "APN" or data configuration issues suggest APN reset
- `final_route`: `SELF_SERVICE`
- `secondary_action`: `NO_ACTION`

**Line is suspended AND has a `bill_id`:**
- Fetch the bill. If the bill status is `overdue`:
  - `primary_action`: `SEND_PAYMENT_REQUEST`
  - `secondary_action`: `RESUME_LINE_REBOOT`
  - `bill_id`: from the line record
  - `charge_amount_usd`: the bill's `amount_due`, formatted to two decimals
  - `final_route`: `BILLING_RECOVERY`

**Roaming not enabled but customer is traveling:**
- `primary_action`: `TOGGLE_ROAMING` (if device has roaming capability but
  line toggle is off) or `ENABLE_LINE_ROAMING` (if line needs carrier-side
  enablement)
- `final_route`: `SELF_SERVICE` (when it's a toggle) or `CARRIER_UPDATE` (when
  it requires carrier-side change)
- `secondary_action`: `NO_ACTION`

**Permission issue (e.g. messaging app cannot send photos):**
- `primary_action`: `GRANT_MESSAGING_PERMISSION`
- `permission`: the specific permission needed (from the line record's
  permission flags or from the plan/device capabilities). Use the template's
  enum: `sms`, `storage`, or `sms_and_storage`
- `final_route`: `SELF_SERVICE`
- `secondary_action`: `NO_ACTION`

**Slow data with VPN connected:**
- `primary_action`: `DISCONNECT_VPN`
- `final_route`: `SELF_SERVICE`
- `secondary_action`: `NO_ACTION`

**Other active-line issues:**
- `TOGGLE_AIRPLANE_MODE` for radio-level issues
- `TOGGLE_MOBILE_DATA` when mobile data is off
- `TOGGLE_WIFI_CALLING` for WiFi calling problems
- `TRANSFER_HUMAN` when no self-service fix applies

### Step 3: Default Values

When no secondary action, no bill, no charge, and no special permission apply:
- `secondary_action`: `NO_ACTION`
- `permission`: `NONE`
- `bill_id`: `""`
- `charge_amount_usd`: `0.0`

### Summary Computation

Tally each `final_route` value: count `SELF_SERVICE` for `self_service_fixes`,
`BILLING_RECOVERY` for `billing_recoveries`, `CARRIER_UPDATE` for
`carrier_updates`, `HUMAN_TRANSFER` for `human_transfers`.

## Enterprise Incidents

Enterprise templates require: `incident_id`, `enterprise_account_id`,
`root_cause_category`, `contributing_alert_issue`, `failure_window` (with
`start_date`, `end_date`, `failed_days`), `backfill_days`, `sla_credit_percent`,
`severity`, `engineering_owner`, `account_owner`, `channel_name`,
`evidence_folder`, `report_title`, `share_permissions`, `response_status`.

### Step 1: Fetch Records

Fetch `GET /api/enterprise/incidents/{incident_id}` to get the incident record.
From it, extract `enterprise_account_id`. Then fetch in parallel:
- `GET /api/enterprise/accounts/{account_id}`
- `GET /api/enterprise/export-runs`
- `GET /api/enterprise/messages`
- `GET /api/enterprise/sla/{account_id}`

### Step 2: Determine Failure Window

From the export-runs list, find all records with a failed status within the
relevant date range (guided by the complaint email and incident timestamps).
- `start_date`: the earliest failed export date
- `end_date`: the latest failed export date
- `failed_days`: the count of distinct dates with failed exports

### Step 3: Determine Root Cause

Read the messages list and export-run error messages. Identify the root cause
category from message content. Write a concise category label (e.g. "stale
credential after rotation", "configuration drift", "pipeline timeout").

### Step 4: Check Contributing Alert Issue

If any message record shows an alert route issue (e.g. `ARCHIVED_ALERT_ROUTE`),
set `contributing_alert_issue` to that value. Otherwise use `NONE` or `UNKNOWN`
per the template enum.

### Step 5: Compute SLA Credit

From the SLA record: use `credit_percent` directly. If the SLA record provides
`breach_days`, that may inform `backfill_days`. The `backfill_days` should
match `failed_days` when the data needs to be backfilled for each failed day.

### Step 6: Assign Owners and Metadata

- `severity`: from the incident record (Critical, High, Medium, Low)
- `engineering_owner`: from the incident record
- `account_owner`: from the enterprise account record
- `channel_name`: from the incident record

### Step 7: Build Naming from Conventions

The response requirements file specifies naming conventions. Use them to
construct:
- `evidence_folder`: e.g. "{Company Name} {Month Year} Investigation"
- `report_title`: e.g. "{Company Name} Export Failure - Resolution Report"

### Step 8: Share Permissions

From the response requirements `permission_users_to_include` array, build
`share_permissions` with each user and the appropriate permission level (`view`
for stakeholders, `edit` for owners/engineers). Preserve the order from the
requirements file.

### Step 9: Response Status

- If `sla_credit_percent` is greater than 0: `NEEDS_FINANCE_REVIEW`
- If root cause is not fully determined: `NEEDS_ENGINEERING_REVIEW`
- Otherwise: `READY_TO_SEND`

## Mobile Data Recovery

Mobile data templates require: `primary_action`, `secondary_action`,
`data_refuel_gb`, `charge_amount_usd`, `carrier_update_required`, `final_route`.

### Step 1: Fetch Records

For each case, fetch `GET /api/cases/{case_id}` to get `customer_id` and
`line_id`. Fetch `GET /api/customers/{customer_id}` and
`GET /api/lines/{line_id}` in parallel. Then fetch `GET /api/plans/{plan_id}`
and `GET /api/devices/{device_id}` from the line record.

### Step 2: Check Customer Preferences

The payload includes `customer_preferences` mapping `case_id` to accepted refuel
amounts and plan-change preferences. Always check this before deciding actions.
If `does_not_want_plan_change` is true, do not recommend plan changes.

### Step 3: Classify by Line and Plan State

**Data cap hit (usage limit reached):**
- Plan has a `data_cap_gb` and the customer's usage exceeded it
- Customer preferences include `accepted_refuel_gb`:
  - `primary_action`: `REFUEL_DATA`
  - `data_refuel_gb`: the accepted amount from preferences
  - `charge_amount_usd`: compute from refuel GB at the standard per-GB rate
    (use the rate found in the plan or SLA record; common rate is $2/GB)
  - `final_route`: `DATA_RECOVERY`
  - `secondary_action`: `NO_ACTION`
  - `carrier_update_required`: `false`

**Roaming needed but not enabled:**
- Line shows roaming not enabled, but plan supports roaming or customer needs
  carrier-side change:
  - `primary_action`: `ENABLE_LINE_ROAMING`
  - `carrier_update_required`: `true`
  - `final_route`: `CARRIER_UPDATE`
  - `data_refuel_gb`: `0.0`
  - `charge_amount_usd`: `0.0`
  - `secondary_action`: `NO_ACTION`

**Device setting issues:**
- `data_saver_on` is true → `TOGGLE_DATA_SAVER` → `DEVICE_SETTING_FIX`
- `network_mode` is an older generation → `SET_NETWORK_MODE` → `DEVICE_SETTING_FIX`
- `mobile_data_on` is false → `TOGGLE_MOBILE_DATA` → `DEVICE_SETTING_FIX`
- `vpn_connected` is true → `DISCONNECT_VPN` → `DEVICE_SETTING_FIX`

For all device setting fixes:
- `data_refuel_gb`: `0.0`
- `charge_amount_usd`: `0.0`
- `carrier_update_required`: `false`
- `secondary_action`: `NO_ACTION`

### Step 4: Default Values

- `secondary_action`: `NO_ACTION`
- `data_refuel_gb`: `0.0`
- `charge_amount_usd`: `0.0`
- `carrier_update_required`: `false`

### Summary Computation

Tally by `final_route`: `DATA_RECOVERY` for `data_refuel_cases`,
`CARRIER_UPDATE` for `carrier_updates`, `DEVICE_SETTING_FIX` for
`device_setting_fixes`, `HUMAN_TRANSFER` for `human_transfers`.
Sum all `charge_amount_usd` values for `total_estimated_customer_charge_usd`.
