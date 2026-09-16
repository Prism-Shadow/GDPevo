# Decision Frameworks for Support Console Operations

This reference catalogs reusable decision logic from five operational domains.
Use it alongside the [API Reference](api_reference.md) to resolve support
console tasks.

## Table of Contents

- [1. Offline Service Ticket Resolution](#1-offline-service-ticket-resolution)
- [2. Contact-Center Case Queue](#2-contact-center-case-queue)
- [3. Enterprise Export Incident Response](#3-enterprise-export-incident-response)
- [4. Queue Quality Review](#4-queue-quality-review)
- [5. Mobile Data Recovery](#5-mobile-data-recovery)

---

## 1. Offline Service Ticket Resolution

**Input:** CSV with `ticket_id, account_id, reported_service_type, customer_report`
**Output:** JSON following the answer template's `ticket_decisions` and `batch_summary`

### Resolution flow (per ticket)

1. **Fetch the ticket** (`/api/tickets/<ticket_id>`) and the **account** (`/api/accounts/<account_id>`).

2. **Check account status first.**
   - Account `status: "Suspended"` → `FAILED` / `INELIGIBLE_ACCOUNT` / route `NONE`. Stop.
   - Account `authentication.last_login_status: "FAILURE"` with empty `account_recovery_status` → `FAILED` / `AUTH_FAILED` / route `NONE`. Stop.
   - Account not found (404) → `FAILED` / `INVALID_ACCOUNT` / route `NONE`. Stop.

3. **Fetch active outages** (`/api/outages`). Match by both `service_area` AND `service_type`.
   - Match found → `PENDING_ACTION` / `OUTAGE_WAIT` / route `NONE`.
     - Set `outage_id` from the matching outage.
     - Increment `tickets_requiring_customer_wait`.
     - Skip diagnostics/troubleshooting for outage-wait tickets.

4. **Fetch diagnostics** (`/api/diagnostics/<ticket_id>`) and **troubleshooting** (`/api/troubleshooting/<ticket_id>`).

5. **Classify issues from diagnostics:**
   - `latency_ms > 100` → `latency_issue: true`
   - `jitter_ms > 30` → `stability_issue: true`
   - `bandwidth_mbps < subscribed_mbps * 0.85` → `bandwidth_issue: true`

6. **Evaluate troubleshooting post_ values:**
   - If post_ values are within healthy ranges → `RESOLVED` / `AUTO_TROUBLESHOOTING` / route `NONE`. Diagnostic was indeed needed.
   - If post_ values remain poor → escalate.

7. **Determine escalation team from diagnostic root_causes:**
   - `FIBER_DROP_DAMAGE` or `SIGNAL_LOSS` → `FIELD_OPS`
   - `BACKBONE_CAPACITY` → `NETWORK_ENGINEERING`
   - `PROVISIONING_STALE` → `TIER2_SUPPORT`
   - `CONFIGURATION_DRIFT`, `VOICE_PROFILE_STALE`, or generated noise → auto-troubleshooting fixable

8. **Build decision:**
   - `RESOLVED` / `AUTO_TROUBLESHOOTING` when post-troubleshooting is healthy
   - `ESCALATED` with `resolution_route: "ESCALATION"` and appropriate `escalation_team`
   - `PENDING_ACTION` / `OUTAGE_WAIT` when an active outage covers the service
   - `FAILED` for suspended, auth-failed, or invalid accounts

### Batch summary

Count tickets in each `final_resolution_status` category.
`tickets_requiring_customer_wait` = count of tickets with `PENDING_ACTION` status.

---

## 2. Contact-Center Case Queue

**Input:** JSON array of cases with `case_id` and `reported_issue`
**Output:** JSON following the answer template's `case_decisions` and `queue_summary`

### ID mapping

Case suffix maps to all related IDs: CASE-XXXX → CUST-XXXX, LINE-XXXX, DEV-XXXX.
The case record itself carries `customer_id`, `line_id`, and `device_id`.

Per case, fetch: case → customer → line → device. Fetch bill if line is suspended.
Fetch plan only when you need pricing or data-limit information.

### Decision flow (per case)

1. **Fetch the case** (`/api/cases/<case_id>`).

2. **Fetch the line** (`/api/lines/<line_id>`).
   - `status: "Suspended"` with `suspension_reason: "OVERDUE_BILL"` → billing recovery:
     - `primary_action: "SEND_PAYMENT_REQUEST"`
     - `secondary_action: "RESUME_LINE_REBOOT"`
     - `final_route: "BILLING_RECOVERY"`
     - Find the overdue bill (`GET /api/bills`, filter by `customer_id` where `status: "Overdue"`) for `bill_id` and `charge_amount_usd`.
   - Otherwise, continue to device routing.

3. **Fetch the device** (`/api/devices/<device_id>`). Map observed device state to action:

   | Device State | primary_action | secondary_action | final_route | permission |
   |---|---|---|---|---|
   | `sim_status: "missing"` | RESEAT_SIM | NO_ACTION | SELF_SERVICE | NONE |
   | `phone_roaming_enabled: false` + `customer_location: "abroad"` | TOGGLE_ROAMING | NO_ACTION | SELF_SERVICE | NONE |
   | `messaging_permissions.storage: false` | GRANT_MESSAGING_PERMISSION | NO_ACTION | SELF_SERVICE | storage |
   | `can_send_mms: false` | GRANT_MESSAGING_PERMISSION | NO_ACTION | SELF_SERVICE | NONE |
   | `vpn_connected: true` + `speed_test: "poor"` | DISCONNECT_VPN | NO_ACTION | SELF_SERVICE | NONE |
   | `airplane_mode: true` | TOGGLE_AIRPLANE_MODE | NO_ACTION | SELF_SERVICE | NONE |
   | `data_saver_mode: true` | TOGGLE_DATA_SAVER | NO_ACTION | SELF_SERVICE | NONE |
   | `network_mode_preference: "3g_only"` | SET_NETWORK_MODE | NO_ACTION | SELF_SERVICE | NONE |
   | `mobile_data_enabled: false` | TOGGLE_MOBILE_DATA | NO_ACTION | SELF_SERVICE | NONE |

4. **Permission determination:**
   - `GRANT_MESSAGING_PERMISSION`: check which permission is missing (`sms`, `storage`, or both). Use the corresponding single value or `sms_and_storage`.
   - Other actions: `"NONE"`.

5. **Charge amount:** `0.0` unless billing recovery (use the bill's `amount_due_usd`).

6. **Queue summary:** count by `final_route`.

---

## 3. Enterprise Export Incident Response

**Input:** Client complaint email + response requirements JSON
**Output:** JSON following the answer template

### Step-by-step resolution

1. **Parse the complaint email** for:
   - Client name (→ enterprise account lookup)
   - Incident reference (→ incident_id)
   - Product affected
   - Number of failed days

2. **Fetch the incident** (`/api/enterprise/incidents/<incident_id>`):
   - Confirms `enterprise_account_id`, `severity`, `account_owner`, `engineering_owner`.

3. **Fetch the enterprise account** (`/api/enterprise/accounts/<enterprise_account_id>`):
   - Reveals `finance_owner`, confirms account name.

4. **Fetch export runs** (`/api/enterprise/export-runs`), filter by `incident_id`:
   - Sort by `run_date`. Identify the contiguous block of FAILED runs.
   - `failure_window.start_date` = earliest FAILED run_date.
   - `failure_window.end_date` = latest FAILED run_date.
   - `failed_days` = count of consecutive FAILED runs.
   - `backfill_days` = same as `failed_days` (each failed day requires manual backfill).
   - Root cause → from `failure_code` common to all failed runs.

5. **Fetch messages** (`/api/enterprise/messages`), filter by `incident_id`:
   - Identify the root-cause narrative message (earliest, often from engineering_owner).
   - Check channel name: if it contains `-archive` suffix → `contributing_alert_issue: "ARCHIVED_ALERT_ROUTE"`.
   - If no archive pattern → `contributing_alert_issue: "NONE"`.

6. **Fetch SLA** (`/api/enterprise/sla/<enterprise_account_id>`):
   - `sla_credit_percent` = `monthly_export_credit_percent`.

7. **Apply naming conventions** (from response requirements):
   - `channel_name`: lowercase-hyphen version of enterprise account name (e.g. "Acme Corp" → "acme-corp").
   - `evidence_folder`: "<Account Name> <Month Year> Investigation".
   - `report_title`: "<Account Name> Export Failure - Resolution Report".

8. **Share permissions:** list each user from `permission_users_to_include` in order.
   - Default pattern: finance owner (if listed) gets `view`, engineering owner (if listed) gets `edit`.
   - When the response requirements specify particular permission assignments, follow those.

9. **Response status:** Check whether SLA credit has been applied (scan messages for finance/owner confirmation).
   - If no finance confirmation message exists → `NEEDS_FINANCE_REVIEW`.
   - If engineering root cause not yet identified → `NEEDS_ENGINEERING_REVIEW`.
   - Otherwise → `READY_TO_SEND`.

---

## 4. Queue Quality Review

**Input:** CSV with `ticket_id, account_id, reported_service_type, queue_note`
**Output:** JSON following the answer template's `ticket_decisions` and `queue_summary`

Same resolution flow as offline ticket resolution (Section 1) but with different output fields:

- `final_resolution_status`: same four values (RESOLVED, PENDING_ACTION, ESCALATED, FAILED)
- `route_team`: escalation team or NONE for non-escalated
- `key_blocker`: the primary reason the ticket cannot be auto-resolved
- `diagnostic_required`: whether diagnostic results substantiate the issue

### Blocker mapping

| Condition | key_blocker |
|---|---|
| Active outage match | ACTIVE_OUTAGE |
| Account not found (404) | INVALID_ACCOUNT |
| Auth failure | AUTH_FAILED |
| Account suspended | OVERDUE_SUSPENSION |
| Backbone capacity root cause | NETWORK_CAPACITY |
| Provisioning stale root cause | PROVISIONING_STALE |
| Physical/fiber root cause | PHYSICAL_LINE_FAULT |
| Auto-troubleshooting successful | NONE |

### Route team mapping

| Diagnostic root_cause | route_team |
|---|---|
| FIBER_DROP_DAMAGE, SIGNAL_LOSS | FIELD_OPS |
| BACKBONE_CAPACITY | NETWORK_ENGINEERING |
| PROVISIONING_STALE | TIER2_SUPPORT |
| Suspended account | ACCOUNTS_PAYABLE |
| Resolved, outage-wait, failed (non-escalation) | NONE |

### Diagnostic required

`true` when a diagnostic report was material to the decision — i.e., when the
ticket is RESOLVED or ESCALATED through diagnostic evidence (not blocked by
outage, invalid account, auth failure, or suspension).
`false` when blocked by outage, invalid account, auth failure, or suspension.

---

## 5. Mobile Data Recovery

**Input:** JSON worklist of cases + optional `customer_preferences`
**Output:** JSON following the answer template's `case_decisions` and `worklist_summary`

### Decision flow (per case)

1. **Fetch the case** (`/api/cases/<case_id>`), **line** (`/api/lines/<line_id>`),
   **device** (`/api/devices/<device_id>`).

2. **Check for data over-limit** (line `data_used_gb > plan data_limit_gb`):
   - Fetch the plan (`/api/plans/<plan_id>`).
   - If over limit → `primary_action: "REFUEL_DATA"`, `final_route: "DATA_RECOVERY"`.
   - `data_refuel_gb`: from `customer_preferences` if provided, otherwise a standard increment.
   - `charge_amount_usd`: `data_refuel_gb * data_refueling_price_per_gb`.
   - `carrier_update_required`: `false`.

3. **Check roaming state:**
   - Line `roaming_enabled: false` + device `phone_roaming_enabled: true` + abroad
     → `primary_action: "ENABLE_LINE_ROAMING"`, `carrier_update_required: true`,
     `final_route: "CARRIER_UPDATE"`.
   - Note: `TOGGLE_ROAMING` toggles the device-side setting; `ENABLE_LINE_ROAMING`
     provisions carrier-side roaming. When the device already has phone_roaming
     enabled but data still doesn't work abroad, the carrier-side needs enabling.

4. **Check device settings for slow/no data:**
   - `data_saver_mode: true` → `TOGGLE_DATA_SAVER`, `final_route: "DEVICE_SETTING_FIX"`
   - `network_mode_preference: "3g_only"` → `SET_NETWORK_MODE`, `final_route: "DEVICE_SETTING_FIX"`
   - `mobile_data_enabled: false` → `TOGGLE_MOBILE_DATA`, `final_route: "DEVICE_SETTING_FIX"`
   - `vpn_connected: true` → `DISCONNECT_VPN`, `final_route: "DEVICE_SETTING_FIX"`

5. **Defaults when nothing matches:** `TRANSFER_HUMAN`, `final_route: "HUMAN_TRANSFER"`.

6. **Field defaults:** `secondary_action: "NO_ACTION"` unless specified.
   `charge_amount_usd: 0.0` unless data refuel.
   `data_refuel_gb: 0.0` when not refueling.

### Worklist summary

Count cases by `final_route`.
`total_estimated_customer_charge_usd` = sum of all `charge_amount_usd` across decisions.

---

## Cross-Cutting Patterns

### Account Status is Always First

Before interpreting diagnostics, troubleshooting, or any service-specific evidence,
always check the account status. Suspended, not-found, and auth-failed accounts
short-circuit all other analysis.

### Outage Match Overrides Diagnostics

When a ticket's service_area + service_type matches an active outage, the ticket is
an outage-wait case regardless of diagnostics/troubleshooting outcomes.

### ID Suffix Conventions

Contact-center cases and mobile data worklists use consistent suffixes:
CASE-XXXX → CUST-XXXX, LINE-XXXX, DEV-XXXX.
The case record itself carries all three related IDs. Use the case record to find
them rather than guessing.

### Root Cause → Escalation Consistency

The same diagnostic root_cause always maps to the same escalation team across all
task types. This is a stable domain rule, not task-specific.

### SLA Credit Comes from the SLA Contract

Enterprise SLA credit percent is always fetched from
`/api/enterprise/sla/<enterprise_account_id>`, not inferred from tier or policy.

### Naming Conventions Are Specified in Requirements

Enterprise response channel names, folder names, and report titles follow patterns
in the response requirements. Derive them mechanically:
- Channel: account name, lowercase, spaces → hyphens
- Folder: "<Account Name> <Month Year> Investigation"
- Report title: "<Account Name> Export Failure - Resolution Report"
