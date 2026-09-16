 # Support Console API Reference

 The support console exposes a REST API at `<TASK_ENV_BASE_URL>`. All endpoints accept
 GET requests and return JSON. No authentication is required.

 ## Table of Contents

 - [Endpoint Catalog](#endpoint-catalog)
 - [Account Records](#account-records)
 - [Ticket Records](#ticket-records)
 - [Diagnostics Records](#diagnostics-records)
 - [Troubleshooting Records](#troubleshooting-records)
 - [Outage Records](#outage-records)
 - [Customer Records](#customer-records)
 - [Line Records](#line-records)
 - [Device Records](#device-records)
 - [Plan Records](#plan-records)
 - [Bill Records](#bill-records)
 - [Case Records](#case-records)
 - [Enterprise Endpoints](#enterprise-endpoints)
   - [Enterprise Accounts](#enterprise-accounts)
   - [Enterprise Incidents](#enterprise-incidents)
   - [Export Runs](#export-runs)
   - [Messages](#messages)
   - [SLA Contracts](#sla-contracts)
 - [Decision-Relationship Quick Reference](#decision-relationship-quick-reference)

 ---

 ## Endpoint Catalog

 `GET /api/catalog` lists every available endpoint and aggregate record counts.
 Start every task by fetching this to confirm which endpoints exist.

 The set of business endpoints (excluding `/health` and `/api/catalog` itself) is:

 | Endpoint | Purpose |
 |---|---|
 | `/api/accounts` | List all service accounts |
 | `/api/accounts/<account_id>` | Single account detail |
 | `/api/tickets` | List all service tickets |
 | `/api/tickets/<ticket_id>` | Single ticket detail |
 | `/api/diagnostics/<ticket_id>` | Diagnostic run for a ticket |
 | `/api/troubleshooting/<ticket_id>` | Troubleshooting run for a ticket |
 | `/api/outages` | List all outages |
 | `/api/customers` | List all mobile customers |
 | `/api/customers/<customer_id>` | Single customer detail |
 | `/api/lines/<line_id>` | Single mobile line detail |
 | `/api/devices/<device_id>` | Single device detail |
 | `/api/plans/<plan_id>` | Single plan detail |
 | `/api/bills` | List all bills |
 | `/api/bills/<bill_id>` | Single bill detail |
 | `/api/cases` | List all contact-center cases |
 | `/api/cases/<case_id>` | Single case detail |
 | `/api/enterprise/accounts` | List enterprise accounts |
 | `/api/enterprise/accounts/<account_id>` | Single enterprise account |
 | `/api/enterprise/incidents` | List enterprise incidents |
 | `/api/enterprise/incidents/<incident_id>` | Single incident |
 | `/api/enterprise/export-runs` | List all export runs |
 | `/api/enterprise/messages` | List enterprise messages |
 | `/api/enterprise/sla/<account_id>` | SLA contract for an enterprise account |

 ---

 ## Account Records

 `GET /api/accounts/<account_id>`

 ```json
 {
   "account_id": "ACC-XXXX",
   "name": "Example Fiber",
   "service_area": "SA-XX",
   "status": "Active | Suspended",
   "tier": "standard",
   "authentication": {
     "last_login_at": "ISO8601",
     "last_login_status": "SUCCESS | FAILURE",
     "account_recovery_status": "" | "FAILURE"
   }
 }
 ```

 **Key decision fields:**
 - `status`: `"Suspended"` means the account cannot be auto-resolved; route to FAILED.
 - `authentication.last_login_status`: `"FAILURE"` with empty recovery means AUTH_FAILED.
 - `authentication.account_recovery_status`: `"FAILURE"` confirms auth dead-end.
 - `service_area`: used to match with outage records.

 ---

 ## Ticket Records

 `GET /api/tickets/<ticket_id>`

 ```json
 {
   "ticket_id": "TCK-XXXX",
   "account_id": "ACC-XXXX",
   "service_type": "internet | voice | video",
   "status": "OPEN",
   "service_area": "SA-XX",
   "subscribed_mbps": 300,
   "issue_summary": "...",
   "created_at": "ISO8601"
 }
 ```

 **Key decision fields:**
 - `service_area` + `service_type`: cross-reference with active outages.
 - `account_id`: look up the account for status and auth checks.
 - `subscribed_mbps`: compare against diagnostic `bandwidth_mbps` to assess bandwidth issues.

 ---

 ## Diagnostics Records

 `GET /api/diagnostics/<ticket_id>`

 ```json
 {
   "ticket_id": "TCK-XXXX",
   "bandwidth_mbps": 209.0,
   "latency_ms": 142.8,
   "jitter_ms": 33.5,
   "root_causes": ["CONFIGURATION_DRIFT"],
   "started_at": "ISO8601",
   "completed_at": "ISO8601"
 }
 ```

 Diagnostics are always available for every ticket (even accounts that are
 suspended or nonexistent — the API returns generated noise in those cases).
 Always check the account status first before interpreting diagnostic results.

 **Key decision thresholds (approximate, evaluate with context):**
 - `latency_ms > 100` → latency issue
 - `jitter_ms > 30` → stability issue
 - `bandwidth_mbps < subscribed_mbps * 0.85` → bandwidth issue
 - `root_causes` entries indicate the underlying problem class

 **Root cause → escalation mapping:**
 | Root Cause | Implication |
 |---|---|
 | `FIBER_DROP_DAMAGE`, `SIGNAL_LOSS` | Physical damage; needs FIELD_OPS |
 | `BACKBONE_CAPACITY` | Network-level capacity; needs NETWORK_ENGINEERING |
 | `PROVISIONING_STALE` | Provisioning mismatch; needs TIER2_SUPPORT |
 | `CONFIGURATION_DRIFT`, `VOICE_PROFILE_STALE` | Usually fixable via auto-troubleshooting |

 ---

 ## Troubleshooting Records

 `GET /api/troubleshooting/<ticket_id>`

 ```json
 {
   "ticket_id": "TCK-XXXX",
   "steps": ["PROFILE_REFRESH", "PROVISIONING_SYNC"],
   "post_latency_ms": 82.0,
   "post_jitter_ms": 21.0,
   "post_bandwidth_mbps": 272.0,
   "started_at": "ISO8601",
   "completed_at": "ISO8601"
 }
 ```

 **Key decision: did auto-troubleshooting fix the problem?**

 Compare post_ values against the same thresholds as diagnostics:
 - If post values are within healthy range → RESOLVED / AUTO_TROUBLESHOOTING
 - If post values remain poor → the issue is beyond auto-repair; escalate

 Troubleshooting `steps` values like `LINE_TEST`, `SIGNAL_REFRESH`,
 `BACKBONE_REROUTE_ATTEMPT`, `PROVISIONING_ADJUSTMENT` describe what was tried.

 ---

 ## Outage Records

 `GET /api/outages`

 ```json
 {
   "outage_id": "OUT-XXXX",
   "active": true,
   "service_area": "SA-XX",
   "service_types": ["video", "internet"],
   "impact_score": 0.94,
   "eta_hours": 6,
   "started_at": "ISO8601"
 }
 ```

 **Key decision logic:**
 1. Match ticket's `service_area` to outage `service_area` AND
    ticket's `service_type` is in outage `service_types` AND
    `active` is `true`.
 2. If all match → PENDING_ACTION with resolution_route OUTAGE_WAIT.
 3. If a ticket matches an active outage, it is not eligible for auto-resolve;
    skip diagnostics/troubleshooting interpretation for that ticket.

 ---

 ## Customer Records

 `GET /api/customers/<customer_id>`

 ```json
 {
   "customer_id": "CUST-XXXX",
   "name": "...",
   "phone_number": "555-XXXX",
   "status": "Active"
 }
 ```

 Mobile cases anchor on customer records. Customer IDs follow the pattern
 `CUST-<case_suffix>` (e.g., CASE-XXXX → CUST-XXXX).

 ---

 ## Line Records

 `GET /api/lines/<line_id>`

 ```json
 {
   "line_id": "LINE-XXXX",
   "customer_id": "CUST-XXXX",
   "device_id": "DEV-XXXX",
   "plan_id": "PLAN-XXXX",
   "phone_number": "555-XXXX",
   "status": "Active | Suspended",
   "suspension_reason": "" | "OVERDUE_BILL",
   "data_used_gb": 4.0,
   "roaming_enabled": true | false,
   "contract_end_date": "YYYY-MM-DD"
 }
 ```

 **Key decision fields:**
 - `status`: `"Suspended"` with `suspension_reason: "OVERDUE_BILL"` → billing recovery path.
 - `roaming_enabled`: whether the carrier-side roaming is provisioned.
   When `false` and the customer is abroad → ENABLE_LINE_ROAMING.
 - `data_used_gb`: compare against plan's `data_limit_gb` to detect over-limit.
 - `plan_id`: used to fetch plan details (limits, refueling price).

 ---

 ## Device Records

 `GET /api/devices/<device_id>`

 ```json
 {
   "device_id": "DEV-XXXX",
   "model": "Pixel Work",
   "sim_status": "missing | active",
   "signal_strength": "none | good",
   "speed_test": "no_connection | fair | poor | excellent",
   "mobile_data_enabled": true | false,
   "phone_roaming_enabled": true | false,
   "data_saver_mode": true | false,
   "vpn_connected": true | false,
   "network_mode_preference": "4g_5g_preferred | 3g_only",
   "can_send_mms": true | false,
   "mmsc_url_present": true | false,
   "messaging_permissions": {
     "sms": true | false,
     "storage": true | false
   },
   "airplane_mode": true | false,
   "wifi_calling_enabled": true | false
 }
 ```

 **Device-state → action mapping:**
 | Observed State | Recommended Action |
 |---|---|
 | `sim_status: "missing"` and/or `signal_strength: "none"` | RESEAT_SIM |
 | `phone_roaming_enabled: false` when abroad | TOGGLE_ROAMING |
 | `data_saver_mode: true` with SLOW_DATA | TOGGLE_DATA_SAVER |
 | `network_mode_preference: "3g_only"` with SLOW_DATA | SET_NETWORK_MODE |
 | `mobile_data_enabled: false` with no data | TOGGLE_MOBILE_DATA |
 | `vpn_connected: true` with poor speed | DISCONNECT_VPN |
 | `can_send_mms: false` or `messaging_permissions.storage: false` | GRANT_MESSAGING_PERMISSION |
 | `airplane_mode: true` | TOGGLE_AIRPLANE_MODE |

 ---

 ## Plan Records

 `GET /api/plans/<plan_id>`

 ```json
 {
   "plan_id": "PLAN-XXXX",
   "name": "Premium 15",
   "data_limit_gb": 15.0,
   "data_refueling_price_per_gb": 5.0,
   "monthly_price_usd": 65.0
 }
 ```

 **Key decision fields:**
 - `data_limit_gb`: when line `data_used_gb > data_limit_gb` → data over limit.
 - `data_refueling_price_per_gb`: × refuel GB = charge amount for REFUEL_DATA.

 ---

 ## Bill Records

 `GET /api/bills` (list all; filter by `customer_id`)

 ```json
 {
   "bill_id": "BILL-XXXX",
   "customer_id": "CUST-XXXX",
   "amount_due_usd": 99.99,
   "due_date": "YYYY-MM-DD",
   "status": "Overdue"
 }
 ```

 When a line is suspended due to `OVERDUE_BILL`, find the overdue bill by matching
 `customer_id` and `status: "Overdue"`. The bill's `amount_due_usd` becomes the
 charge amount for SEND_PAYMENT_REQUEST.

 ---

 ## Case Records

 `GET /api/cases/<case_id>`

 ```json
 {
   "case_id": "CASE-XXXX",
   "customer_id": "CUST-XXXX",
   "line_id": "LINE-XXXX",
   "device_id": "DEV-XXXX",
   "issue_type": "NO_SERVICE | MOBILE_DATA | SLOW_DATA",
   "customer_location": "home | abroad",
   "summary": "...",
   "opened_at": "ISO8601"
 }
 ```

 Cases connect customer, line, and device. Resolve by fetching all three records
 and following the decision frameworks.

 ---

 ## Enterprise Endpoints

 ### Enterprise Accounts

 `GET /api/enterprise/accounts/<account_id>`

 ```json
 {
   "enterprise_account_id": "ENT-XXXX",
   "name": "Acme Corp",
   "tier": "Enterprise | Strategic",
   "account_owner": "acct.owner",
   "finance_owner": "finance.owner"
 }
 ```

 ### Enterprise Incidents

 `GET /api/enterprise/incidents/<incident_id>`

 ```json
 {
   "incident_id": "INC-XXXX",
   "enterprise_account_id": "ENT-XXXX",
   "product": "monthly_export",
   "severity": "Critical | High | Medium | Low",
   "status": "UNDER_INVESTIGATION | RESOLVED",
   "summary": "...",
   "account_owner": "acct.owner",
   "engineering_owner": "eng.owner",
   "received_at": "ISO8601"
 }
 ```

 ### Export Runs

 `GET /api/enterprise/export-runs`

 Filter by `enterprise_account_id` and/or `incident_id`.

 ```json
 {
   "run_id": "RUN-AST-0",
   "enterprise_account_id": "ENT-XXXX",
   "incident_id": "INC-XXXX",
   "run_date": "2026-05-12",
   "status": "FAILED | SUCCEEDED",
   "failure_code": "STALE_CREDENTIAL" | "",
   "exported_record_count": 0
 }
 ```

 **Key decision:** consecutive FAILED runs define the failure window.
 The count of consecutive FAILED days = `backfill_days`.
 The `failure_code` from the failed runs is the primary root-cause signal.

 ### Messages

 `GET /api/enterprise/messages`

 Filter by `incident_id` or `enterprise_account_id`.

 ```json
 {
   "message_id": "MSG-XXXX",
   "author": "eng.owner",
   "body": "...",
   "channel": "export-alerts-archive",
   "created_at": "ISO8601"
 }
 ```

 Messages provide root-cause narrative. The channel name can signal whether an
 alert was archived (`*-archive` suffix). Message `author` fields identify owners.

 ### SLA Contracts

 `GET /api/enterprise/sla/<enterprise_account_id>`

 ```json
 {
   "enterprise_account_id": "ENT-XXXX",
   "monthly_export_credit_percent": 10,
   "credit_trigger": "3 consecutive failed export runs",
   "executive_contact": "exec@example.com"
 }
 ```

 ---

 ## Decision-Relationship Quick Reference

 | Task Type | Start With | Then Fetch | Key Decisions |
 |---|---|---|---|
 | Offline ticket batch | Ticket → Account | Diagnostics, Troubleshooting, Outages | Account status, outage match, diag cause → resolve/escalate/fail |
 | Contact-center case queue | Case → Customer, Line, Device | Bill (if suspended), Plan | Device state → self-service fix; line status → billing |
 | Enterprise export complaint | Incident → Enterprise Account | Export Runs, Messages, SLA | Failure window, root cause, credit, owners, naming conventions |
 | Queue quality review | Ticket → Account | Diagnostics, Troubleshooting, Outages | Same as offline batch but classify blocker, route_team |
 | Mobile data recovery | Case → Line, Device | Plan, Customer preferences | Data limit, roaming state, device settings |
