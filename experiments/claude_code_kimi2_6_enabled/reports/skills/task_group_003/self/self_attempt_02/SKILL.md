# Support Console Analyst – Reusable SOP

## 1. Environment & Base URL
- The remote support-console API is reachable **only** at the URL provided in `environment_access.md` (e.g. `http://34.46.77.124:8003`).
- Do **not** use localhost, `env/setup.sh`, or any local environment.

## 2. Core API Endpoints
The following REST endpoints were discovered and verified.  Query parameters do **not** appear to filter results; fetch the full collection and filter client-side.

| Resource | Collection | Single-item |
|----------|------------|-------------|
| Tickets | `GET /api/tickets` | `GET /api/tickets/{ticket_id}` |
| Cases | `GET /api/cases` | `GET /api/cases/{case_id}` |
| Accounts | `GET /api/accounts` | `GET /api/accounts/{account_id}` |
| Devices | `GET /api/devices` | `GET /api/devices/{device_id}` |
| Customers | `GET /api/customers` | `GET /api/customers/{customer_id}` |
| Lines | `GET /api/lines` | `GET /api/lines/{line_id}` |
| Plans | `GET /api/plans` | `GET /api/plans/{plan_id}` |

> **Caution:** A `HEAD` request to the root returns `501 Unsupported method`; use `GET`. Many intuitive paths (e.g. `/api/diagnostics`, `/api/incidents`, `/api/network-status`) return `{"error":"not_found"}`.

## 3. Data Relationships & Lookup Chain
1. **Tickets** → lookup **Account** by `account_id` to verify `status` (`Active`/`Suspended`) and `authentication.last_login_status`.
2. **Cases** → lookup:
   - **Device** by `device_id` for hardware/settings state.
   - **Line** by `line_id` for `status`, `suspension_reason`, `data_used_gb`, `roaming_enabled`, `plan_id`.
   - **Customer** by `customer_id` for basic identity.
   - **Plan** by `plan_id` for `data_limit_gb` and `data_refueling_price_per_gb`.
3. Cross-check `service_area` between ticket and account; mismatches may indicate provisioning issues.

## 4. Key Diagnostic Fields

### Accounts
- `status`: `Active` vs `Suspended` → billing/account-restore path.
- `authentication.last_login_status`: `SUCCESS` vs `FAILURE` → auth-reset path.
- A ticket whose `account_id` is **not found** in `/api/accounts` (e.g. `BAD-5403`) is an invalid/intake-missing account.

### Lines
- `status`: `Active` vs `Suspended`.
- `suspension_reason`: `OVERDUE_BILL` | `CONTRACT_ENDED` | `""`.
- `data_used_gb` vs plan `data_limit_gb` → data-limit / refuel decision.
- `roaming_enabled` (`true`/`false`) → roaming provisioning vs device setting.

### Devices
| Field | Relevant States | Diagnostic Meaning |
|-------|-----------------|--------------------|
| `sim_status` | `active`, `missing`, `locked_pin` | Physical SIM issue → hardware/SIM replacement |
| `signal_strength` | `good`, `none` | Network coverage or SIM/hardware failure |
| `speed_test` | `excellent`, `good`, `fair`, `poor`, `no_connection` | Throughput diagnostic |
| `mobile_data_enabled` | `true`/`false` | User settings toggle |
| `data_saver_mode` | `true`/`false` | Data-saver throttling |
| `network_mode_preference` | `4g_5g_preferred`, `3g_only` | Legacy-network throttling |
| `vpn_connected` | `true`/`false` | VPN-induced slowdown |
| `phone_roaming_enabled` | `true`/`false` | Device-side roaming toggle |
| `can_send_mms` | `true`/`false` | MMS capability (also check `messaging_permissions.storage` and `mmsc_url_present`) |

## 5. Task-Type Workflow Rules

### 5.1 Ticket Classification (offline batch)
- **Inputs:** `ticket_batch.csv` + API records.
- **Required outputs per ticket:** `ticket_class`, `recommended_resolution`.
- **Reasoning heuristics:**
  - `Suspended` account + hold/overdue language → billing / account-restore class.
  - `Active` account + area-wide / backbone / neighborhood language → infrastructure / network-ops class.
  - `Active` account + site-specific / line-work / fiber-drop language → field-tech / onsite-repair class.
  - `Active` account + authentication failure → auth-reset / profile-repair class.
  - `Active` account + voice-profile / call-drop language → voice-provisioning class.
  - Non-existent account in intake → invalid-account / data-cleanup class.

### 5.2 Case Triage (queue action)
- **Inputs:** `case_queue.json` + device/line records.
- **Required output per case:** `queue_action`.
- **Reasoning heuristics:**
  - `sim_status: missing` → hardware replacement queue.
  - `line.status: Suspended` + `suspension_reason: OVERDUE_BILL` → billing queue.
  - `line.status: Suspended` + `suspension_reason: CONTRACT_ENDED` → retention/renewal queue.
  - `can_send_mms: false` + (`messaging_permissions.storage: false` or `mmsc_url_present: false`) → device-support / permission-fix queue.
  - `customer_location: abroad` + `line.roaming_enabled: false` → roaming-provisioning queue.
  - `vpn_connected: true` + `speed_test: poor` → VPN-troubleshoot queue.
  - `data_saver_mode: true` + `speed_test: fair` → device-settings queue.
  - `mobile_data_enabled: false` → device-settings queue.

### 5.3 Queue Snapshot Analysis
- **Inputs:** `queue_snapshot.csv` + ticket/account records.
- **Required outputs per row:** `account_valid` (boolean), `queue_status`, `first_action`.
- `account_valid` is `false` when the ticket’s `account_id` does not exist in `/api/accounts`.
- `queue_status` and `first_action` follow the same classification heuristics as §5.1, but phrased as queue status (e.g. `waiting_for_infrastructure`, `ready_for_dispatch`, `blocked_billing`, `invalid_account`).

### 5.4 Mobile-Data Recovery
- **Inputs:** `mobile_data_worklist.json` + device/line/plan records.
- **Required outputs per case:** `primary_operation`, `follow_up_operation`, `expected_charge`.
- **Reasoning heuristics:**
  - `data_used_gb > plan.data_limit_gb` → primary: `Data_Refuel` (or plan upgrade if customer allows).  Charge = `accepted_refuel_gb × plan.data_refueling_price_per_gb`.
  - `customer_location: abroad` + `line.roaming_enabled: false` → primary: `Enable_Roaming`.
  - `data_saver_mode: true` → primary: `Disable_Data_Saver`.
  - `network_mode_preference: 3g_only` → primary: `Switch_Network_Mode`.
  - `mobile_data_enabled: false` → primary: `Enable_Mobile_Data`.
  - `vpn_connected: true` + slow data → primary: `Disconnect_VPN` or `VPN_Troubleshoot`.
  - `sim_status: missing` → primary: `Replace_SIM`.
- `follow_up_operation` is typically `"Monitor"` or `"Notify_Customer"` unless a second hardware/software issue is present.
- `expected_charge`: use `"None"` for settings toggles; use a calculated dollar amount (rounded to two decimals) for refuel or hardware replacement.

### 5.5 Enterprise Complaint Response
- **Inputs:** `client_complaint_email.txt` + `response_requirements.json`.
- **Important:** The support-console API **does not expose** enterprise/incident/export endpoints.  All required fields must be synthesized from the email text and the requirements JSON.
- **Required fields:**
  - `incident_id` – from email subject/body (e.g. `INC-7301`).
  - `enterprise_account_id` – infer from client name or email domain.
  - `root_cause_category` – concise category inferred from failure description.
  - `contributing_alert_issue` – enum: `ARCHIVED_ALERT_ROUTE | NONE | UNKNOWN`.
  - `failure_window` – parse dates from email; `failed_days` = integer count.
  - `backfill_days` – integer; typically equals `failed_days` unless stated otherwise.
  - `sla_credit_percent` – integer percent (read requirements for guidance).
  - `severity` – enum: `Critical | High | Medium | Low`.
  - `engineering_owner`, `account_owner` – string user IDs (infer from context or requirements).
  - `channel_name` – follow naming style from requirements (lowercase-hyphen).
  - `evidence_folder` – follow naming style (client-date investigation folder).
  - `report_title` – follow naming style (client export failure report title).
  - `share_permissions` – array ordered **exactly** as listed in `response_requirements.json` `permission_users_to_include`; each item has `user` and `permission` (`view | edit | upload_only`).
  - `response_status` – enum: `READY_TO_SEND | NEEDS_FINANCE_REVIEW | NEEDS_ENGINEERING_REVIEW | UNDER_INVESTIGATION`.

## 6. Output Conventions
- **Always** return **only** JSON that conforms to the task’s `answer_template.json`.
- Preserve the exact array/object nesting from the template.
- Use the ticket/case IDs exactly as they appear in the payload; do not re-order unless the template requires a specific sort.
- For monetary values: output as numeric strings or formatted strings based on template schema; if a template expects `"string"` for charge, use `"$4.00"` or `"None"` consistently.
- For enum fields, use the exact uppercase/lowercase spelling shown in the template comments.

## 7. Common Pitfalls
- **Do not assume account validity from the ticket alone.** Always query `/api/accounts/{account_id}`; a `BAD-*` or missing account is a real edge case.
- **Do not confuse device roaming with line roaming.** `phone_roaming_enabled` (device) and `roaming_enabled` (line) are separate toggles.
- **Check `data_used_gb` against the plan limit**, not a hard-coded value; plans vary (Basic 5, Premium 15, Unlimited Plus, Family Share, and generated plans).
- **Generated tickets/accounts/devices/lines** (`ticket_id` `TCK-8xxx`, `account_id` `ACC-7xxx`, `device_id` `DEV-Gxxx`, `line_id` `LINE-Gxxx`) may exist in the API as background noise; focus only on the IDs listed in the task payload.
- **Do not guess endpoints** outside the verified list (§2).  Broad brute-force scanning is unnecessary and wastes time.
- **HEAD requests are not supported** by this server; always use `GET`.
