# CRM Support Console — Solver Skill

## Base URL

Always use the remote base URL from `environment_access.md`. **Never** use `localhost`, `127.0.0.1`, or any URL embedded in a task prompt — the `environment_access.md` override is authoritative.

## API Reference

| Endpoint | Use |
|---|---|
| `GET /health` | Confirm API is reachable before starting |
| `GET /api/catalog` | Discover available endpoints / schemas |
| `GET /api/tickets/{ticket_id}` | Ticket status, account link, reported issue, service type |
| `GET /api/accounts/{account_id}` | Account standing: active, suspended, on-hold, credit class |
| `GET /api/diagnostics/{ticket_id}` | Latency, stability, bandwidth metrics; returns boolean flags |
| `GET /api/troubleshooting/{ticket_id}` | Auto-remediation results; indicates whether a fix was applied |
| `GET /api/outages?service_area={area}` | Active outages for a service area; returns outage_id or empty |
| `GET /api/lines/{line_id}` | Mobile line state: suspended, roaming, data-saver, network mode |
| `GET /api/devices/{device_id}` | Device capabilities, VPN status, APN config, SIM state |
| `GET /api/plans/{plan_id}` | Plan details, data limits, roaming provisions, throttling |
| `GET /api/cases/{case_id}` | Case record: customer, line, device linkage |
| `GET /api/enterprise/incidents/{incident_id}` | Incident metadata: severity, owners, channel, status |
| `GET /api/enterprise/export-runs?incident_id={incident_id}` | Export-run log; use to determine failure window (first/last failed date) |
| `GET /api/enterprise/messages?query={text}` | Search internal messages for root-cause clues, alert references |
| `GET /api/enterprise/sla/{enterprise_account_id}` | SLA terms: credit percentage per day, severity thresholds |

## Resolution SOP — Ticket Triage (train_001 / train_004)

Follow this priority order for every ticket. **Stop at the first match** — later checks should NOT override an earlier decision.

### Step 1 — Account Validity Check
Call `GET /api/accounts/{account_id}`.
- **404 / "not found" / non-matching account id** → `final_resolution_status: "FAILED"`, `key_blocker: "INVALID_ACCOUNT"`, `resolution_route: "INELIGIBLE_ACCOUNT"`. Done.
- **Account suspended / on-hold / overdue** → `FAILED` + `key_blocker: "OVERDUE_SUSPENSION"` + `route_team: "ACCOUNTS_PAYABLE"` + `resolution_route: "INELIGIBLE_ACCOUNT"`.
- **Authentication failure on account** → `FAILED` + `key_blocker: "AUTH_FAILED"` + `resolution_route: "AUTH_FAILED"`.

### Step 2 — Active Outage Check
Call `GET /api/outages?service_area={area}` using the service area from the ticket or account record.
- **Active outage found** → `final_resolution_status: "PENDING_ACTION"`, `key_blocker: "ACTIVE_OUTAGE"`, `resolution_route: "OUTAGE_WAIT"`, `outage_id` from response. Set `diagnostic_needed: false` — the outage is the root cause.

### Step 3 — Run Diagnostics (only if Steps 1-2 are clean)
Call `GET /api/diagnostics/{ticket_id}`.
- **Diagnostics return latency/stability/bandwidth flags** → set the corresponding boolean fields from the actual diagnostic response. Do not assume — only set `true` what the API returns as problematic.
- **Diagnostics fail or are unavailable** → `diagnostic_needed: false`.

### Step 4 — Auto-Troubleshooting
Call `GET /api/troubleshooting/{ticket_id}`.
- **Fix applied successfully** → `final_resolution_status: "RESOLVED"`, `resolution_route: "AUTO_TROUBLESHOOTING"`, `key_blocker: "NONE"`.
- **Troubleshooting indicates physical/line fault** → `ESCALATED` + `route_team: "FIELD_OPS"` + `key_blocker: "PHYSICAL_LINE_FAULT"` + `resolution_route: "ESCALATION"`.
- **Network capacity / backbone issue** → `ESCALATED` + `route_team: "NETWORK_ENGINEERING"` + `key_blocker: "NETWORK_CAPACITY"` + `resolution_route: "ESCALATION"`.
- **Provisioning stale / mismatch** → `ESCALATED` + `route_team: "TIER2_SUPPORT"` + `key_blocker: "PROVISIONING_STALE"` + `resolution_route: "ESCALATION"`.

### Diagnostic Flag Convention
Only set `latency_issue`, `stability_issue`, `bandwidth_issue` to `true` when the API's diagnostic response explicitly flags them. Default all three to `false` when diagnostics are skipped (outage, invalid account, auth failure, overdue).

## Resolution SOP — Mobile Case Routing (train_002)

For each case, look up the line, device, plan, and account via their respective endpoints. Map the reported issue to the primary action:

| Reported Symptom | Primary Action | Route | Notes |
|---|---|---|---|
| No service after travel/commute/move | `RESEAT_SIM` | `SELF_SERVICE` | SIM may have shifted |
| Line suspended, customer willing to pay | `SEND_PAYMENT_REQUEST` | `BILLING_RECOVERY` | Look up bill via account; set `bill_id` and `charge_amount_usd` from API |
| Suspended line → follow-up after payment | `RESUME_LINE_REBOOT` | _secondary_action_ | Pair with SEND_PAYMENT_REQUEST |
| Traveling abroad, no mobile data | `TOGGLE_ROAMING` | `SELF_SERVICE` | Check device roaming toggle first |
| Can't send MMS / photo messages | `GRANT_MESSAGING_PERMISSION` | `SELF_SERVICE` | Set `permission: "storage"` for photos |
| Mobile data slow (VPN active) | `DISCONNECT_VPN` | `SELF_SERVICE` | Check device VPN status |
| Mobile data slow (data saver on) | `TOGGLE_DATA_SAVER` | `SELF_SERVICE` | |
| Wrong network mode (3G on 4G-capable) | `SET_NETWORK_MODE` | `SELF_SERVICE` | |
| Mobile data toggle off | `TOGGLE_MOBILE_DATA` | `SELF_SERVICE` | |
| APN misconfigured | `RESET_APN_REBOOT` | `SELF_SERVICE` | |
| Wi-Fi calling issue | `TOGGLE_WIFI_CALLING` | `SELF_SERVICE` | |
| Airplane mode stuck | `TOGGLE_AIRPLANE_MODE` | `SELF_SERVICE` | |
| No self-service fix possible | `TRANSFER_HUMAN` | `HUMAN_TRANSFER` | Last resort |

### Mobile Routing Rules
- Always check `permission` from the device/line API response. Set to `"NONE"` unless the API indicates a permission grant is needed.
- `secondary_action` defaults to `"NO_ACTION"` unless a multi-step sequence is indicated (e.g., pay-then-resume).
- `bill_id` and `charge_amount_usd` are empty/0.0 unless a billing action is taken.
- Always verify the line state (`/api/lines/{line_id}`) to confirm the primary action will resolve the issue.

## Resolution SOP — Mobile Data Recovery (train_005)

Same lookup pattern as train_002 but focused on data-specific issues:

| Symptom | Primary Action | Route | Charge |
|---|---|---|---|
| Data stopped, usage limit reached | `REFUEL_DATA` | `DATA_RECOVERY` | $2.00/GB from plan API; use customer's accepted GB amount |
| Roaming on device but carrier-side disabled | `ENABLE_LINE_ROAMING` | `CARRIER_UPDATE` | $0.00; set `carrier_update_required: true` |
| Data saver icon visible, slow speeds | `TOGGLE_DATA_SAVER` | `DEVICE_SETTING_FIX` | $0.00 |
| Slow data on older network mode | `SET_NETWORK_MODE` | `DEVICE_SETTING_FIX` | $0.00 |
| No data after settings change | `TOGGLE_MOBILE_DATA` | `DEVICE_SETTING_FIX` | $0.00 |

### Data Recovery Rules
- `data_refuel_gb` comes from `customer_preferences` in the payload (the customer's accepted amount), NOT from the plan cap.
- `charge_amount_usd` = `data_refuel_gb × 2.00` (confirm the $/GB rate from the plan API; default $2.00/GB).
- `carrier_update_required: true` ONLY for `ENABLE_LINE_ROAMING` — this is a carrier-side provisioning change, not a device toggle.
- Device-side toggles (`TOGGLE_DATA_SAVER`, `SET_NETWORK_MODE`, `TOGGLE_MOBILE_DATA`) are `DEVICE_SETTING_FIX` with no charge and no carrier update.

## Enterprise Incident Response SOP (train_003)

### Evidence Gathering
1. `GET /api/enterprise/incidents/{incident_id}` → severity, owners, channel_name, status
2. `GET /api/enterprise/export-runs?incident_id={incident_id}` → identify first and last failed date → `failure_window`
3. `GET /api/enterprise/messages?query={descriptive_terms}` → search for root-cause clues, alert references, stale-credential mentions
4. `GET /api/enterprise/sla/{enterprise_account_id}` → credit percentage, backfill policy

### Field Derivation Rules
- **root_cause_category**: Concise summary from message evidence (e.g., `"stale credential after rotation"`). Derive from the most specific failure message found.
- **contributing_alert_issue**: `"ARCHIVED_ALERT_ROUTE"` if messages reference an alert that was archived/missed. `"NONE"` if no contributing alert. `"UNKNOWN"` if unclear.
- **failure_window**: `start_date` = first failed export date; `end_date` = last failed export date; `failed_days` = count of distinct failed dates.
- **backfill_days**: Equal to `failed_days` unless SLA terms specify otherwise.
- **sla_credit_percent**: From SLA endpoint. Common pattern: 5% per failed day, capped per terms.
- **severity**: Based on scope — 3+ failed days with executive impact → `"Critical"`; 1-2 days → `"High"`; partial failure → `"Medium"`.
- **engineering_owner / account_owner**: From incident API response (use the exact user ID string returned).
- **channel_name**: From incident API; format as lowercase-with-hyphens.
- **evidence_folder**: `"{Client Name} {Month} {Year} Investigation"` (e.g., `"Asteri Retail Inc. May 2026 Investigation"`).
- **report_title**: `"{Client Name} Export Failure - Resolution Report"`.
- **share_permissions**: Use the `permission_users_to_include` list from requirements. First user gets `"view"`, second gets `"edit"` (or as specified). Preserve the order from the requirements file.
- **response_status**: `"NEEDS_FINANCE_REVIEW"` when SLA credits are involved. `"READY_TO_SEND"` when no finance/engineering sign-off needed. `"NEEDS_ENGINEERING_REVIEW"` when root cause needs engineering confirmation.

## Output Conventions (ALL task types)

### General
- **Preserve payload order**: Iterate tickets/cases in the order they appear in the input file.
- **Empty/missing IDs**: Use `""` (empty string), never `null` or omission.
- **Zero amounts**: Use `0.0` (float), never `0` (int) for currency/GB fields.
- **No-op enums**: Use `"NONE"` for non-applicable escalation teams, permissions, key blockers.
- **No-op actions**: Use `"NO_ACTION"` for non-applicable secondary actions.

### Enum Case Sensitivity
All enum values are **UPPER_SNAKE_CASE** and must match exactly:
- Resolution status: `RESOLVED`, `PENDING_ACTION`, `ESCALATED`, `FAILED`
- Routes: `AUTO_TROUBLESHOOTING`, `OUTAGE_WAIT`, `ESCALATION`, `INELIGIBLE_ACCOUNT`, `AUTH_FAILED`, `INVALID_ACCOUNT`, `SELF_SERVICE`, `BILLING_RECOVERY`, `CARRIER_UPDATE`, `HUMAN_TRANSFER`, `DATA_RECOVERY`, `DEVICE_SETTING_FIX`
- Teams: `NONE`, `TIER2_SUPPORT`, `FIELD_OPS`, `NETWORK_ENGINEERING`, `ACCOUNTS_PAYABLE`
- Severity: `Critical`, `High`, `Medium`, `Low` (Title Case)
- Permissions: `NONE`, `sms`, `storage`, `sms_and_storage` (lowercase)
- Response status: `READY_TO_SEND`, `NEEDS_FINANCE_REVIEW`, `NEEDS_ENGINEERING_REVIEW`, `UNDER_INVESTIGATION`

### Summary Counts
- Every summary count must **exactly match** the decisions array. Sum across categories should equal total ticket/case count.
- For the batch summary in train_001, `tickets_requiring_customer_wait` = count of `PENDING_ACTION` tickets.
- For train_004 queue summary, include per-team counts (in addition to per-status counts).

### Boolean Fields
- `diagnostic_needed` / `diagnostic_required`: `true` ONLY when diagnostics were actually run and produced useful results. `false` for outage, invalid account, auth failure, overdue, or fraud cases.
- `carrier_update_required`: `true` ONLY for carrier-side provisioning changes (e.g., `ENABLE_LINE_ROAMING`).

## Common Pitfalls

1. **Using localhost URL**: Always use the base URL from `environment_access.md`. The task prompt may say `http://127.0.0.1:8057` — ignore it.
2. **Running diagnostics on outage tickets**: If an active outage covers the service area, skip diagnostics — the outage is the root cause.
3. **Wrong charge calculation**: Data refuel charge = customer's accepted GB × plan rate. Always confirm the rate from the plan API; never hardcode without verification.
4. **Confusing device roaming vs carrier roaming**: `TOGGLE_ROAMING` is a device-side toggle. `ENABLE_LINE_ROAMING` is a carrier-side provisioning change (requires `carrier_update_required: true`).
5. **Missing secondary_action**: When a line is suspended and needs payment, the secondary action after payment is `RESUME_LINE_REBOOT`.
6. **Account checks before everything**: Always validate the account FIRST. Invalid/suspended accounts short-circuit all other checks.
7. **Naming convention drift**: Follow the naming style from `response_requirements.json` exactly — lowercase-hyphen for channels, specific title/folder templates for enterprise responses.
8. **SLA backfill equals failed days**: Unless the SLA endpoint explicitly states a different policy, `backfill_days = failed_days`.

## Quick Pre-Flight Checklist

- [ ] Read `environment_access.md` for the real base URL
- [ ] `GET /health` to confirm connectivity
- [ ] Read ALL payload files (CSV, JSON, email text, requirements)
- [ ] Read the answer template to know exact output shape
- [ ] For each ticket/case, follow the priority: Account → Outage → Diagnostics → Troubleshooting → Route
- [ ] Verify summary counts match the decisions array
- [ ] Check all enum values against the template's allowed values
- [ ] Output valid JSON only — no markdown wrappers, no commentary
