# CRM Support Console — Reusable Skill

## Base URL

Use the URL from `environment_access.md`. Ignore `127.0.0.1` / `localhost` in task prompts.
Known public base: `http://34.46.77.124:8003` (verify against environment_access.md).

---

## Core API Reference

| Endpoint | Use |
|---|---|
| `GET /api/tickets/<id>` | Ticket detail: status, account_id, service_type, area |
| `GET /api/accounts/<id>` | Account status (active / suspended / hold), service_area |
| `GET /api/outages?service_area=<area>` | Active outages → list of `{outage_id, service_type, area}` |
| `GET /api/diagnostics/<id>` | Flags: latency, stability, bandwidth, packet_loss |
| `GET /api/troubleshooting/<id>` | Auto-fix attempt result |
| `GET /api/cases/<id>` | Case detail: customer_id, line_id, status |
| `GET /api/lines/<id>` | Line state: status, roaming, network_mode, data_saver, vpn, apn, mobile_data, permissions |
| `GET /api/devices/<id>` | Device model, capabilities |
| `GET /api/plans/<id>` | Plan features, roaming support |
| `GET /api/enterprise/incidents/<id>` | Incident detail: account, severity, engineering_owner, account_owner |
| `GET /api/enterprise/export-runs?incident_id=<id>` | Export history: success/failure per date |
| `GET /api/enterprise/messages?query=<text>` | Search messages for root-cause clues |
| `GET /api/enterprise/sla/<enterprise_account_id>` | SLA terms, credit percentages |

---

## Ticket Triage Rules (Internet / Video / Voice)

### Step 1 — Account Lookup
- Call `GET /api/accounts/<account_id>`.
- If the account does **not exist** or the account_id is malformed (e.g., `BAD-*`): **FAILED** / `INVALID_ACCOUNT`.
- If the account is **suspended / on hold / overdue**: **FAILED** / `INELIGIBLE_ACCOUNT` (or `OVERDUE_SUSPENSION` with route `ACCOUNTS_PAYABLE` in SLA-review contexts).

### Step 2 — Outage Check
- Extract the `service_area` from the account.
- Call `GET /api/outages?service_area=<area>`.
- If an active outage matches the ticket's **service_type** (internet / video / voice): **PENDING_ACTION** / `OUTAGE_WAIT` (route: `ACTIVE_OUTAGE`). No diagnostic needed. Include the `outage_id`.

### Step 3 — Diagnostics & Resolution
- If account is valid and no outage: call `GET /api/diagnostics/<ticket_id>`.
- Map diagnostic flags directly to the boolean issue fields (`latency_issue`, `stability_issue`, `bandwidth_issue`).

**Resolution routing by symptom/root-cause:**

| Symptom / Root Cause | Status | Route | Escalation |
|---|---|---|---|
| Performance issues (latency/packet-loss/jitter), valid account, no outage, auto-fix succeeds | RESOLVED | AUTO_TROUBLESHOOTING | NONE |
| Active matching outage | PENDING_ACTION | OUTAGE_WAIT | NONE |
| Physical infrastructure (line work, field damage, cable cut) | ESCALATED | ESCALATION | FIELD_OPS |
| Backbone / capacity errors | ESCALATED | ESCALATION | NETWORK_ENGINEERING |
| Provisioning mismatch / stale config | ESCALATED | ESCALATION | TIER2_SUPPORT |
| Account suspended / on hold | FAILED | INELIGIBLE_ACCOUNT | NONE |
| Overdue suspension (SLA review context) | FAILED | — | ACCOUNTS_PAYABLE |
| Auth failure / credentials broken | FAILED | AUTH_FAILED | NONE |
| Invalid / non-existent account | FAILED | INVALID_ACCOUNT | NONE |

### Diagnostic Flag Convention
- `diagnostic_needed: true` → RESOLVED and ESCALATED technical tickets.
- `diagnostic_needed: false` → FAILED tickets, outage-wait tickets.
- When diagnostics run, ALL flags reflect what the API returns (do not zero them out just because one is false).

---

## Mobile Case Queue Rules

### Step 1 — Case Lookup
- `GET /api/cases/<case_id>` → extract `customer_id`, `line_id`.
- `GET /api/lines/<line_id>` → line status, roaming, network_mode, data_saver, vpn, mobile_data, permissions.

### Step 2 — Issue → Action Mapping

| Reported Issue | Primary Action | Secondary | Final Route | Notes |
|---|---|---|---|---|
| No service after movement / commute | RESEAT_SIM | NO_ACTION | SELF_SERVICE | Physical SIM reseat |
| Line suspended, customer ready to pay | SEND_PAYMENT_REQUEST | RESUME_LINE_REBOOT | BILLING_RECOVERY | Fetch bill_id from line/account; charge = bill amount |
| Traveling abroad, no mobile data | TOGGLE_ROAMING | NO_ACTION | SELF_SERVICE | If line roaming already toggled on but still no data → ENABLE_LINE_ROAMING (carrier-side) |
| Can't send photos in messaging | GRANT_MESSAGING_PERMISSION | NO_ACTION | SELF_SERVICE | Permission = `storage` for MMS |
| Mobile data works but slow + VPN active | DISCONNECT_VPN | NO_ACTION | SELF_SERVICE | |
| Data stopped after usage limit | REFUEL_DATA | NO_ACTION | DATA_RECOVERY | Use customer's accepted GB; $2.00/GB |
| Traveler: roaming ON phone but line not provisioned | ENABLE_LINE_ROAMING | NO_ACTION | CARRIER_UPDATE | carrier_update_required=true |
| Slow data + data-saver icon visible | TOGGLE_DATA_SAVER | NO_ACTION | DEVICE_SETTING_FIX | |
| Slow data on older network mode | SET_NETWORK_MODE | NO_ACTION | DEVICE_SETTING_FIX | |
| No data after settings change | TOGGLE_MOBILE_DATA | NO_ACTION | DEVICE_SETTING_FIX | |

### Permission Field
- `NONE` unless the action is `GRANT_MESSAGING_PERMISSION` → then use `storage`.
- In some task variants, `sms` or `sms_and_storage` may appear; check line permissions API.

### Bill / Charge Rules
- `bill_id`: empty string `""` unless a bill payment is involved (SEND_PAYMENT_REQUEST).
- `charge_amount_usd`: always a number with two decimals. For billing cases, use the actual bill amount from the API. For data refuel: `refuel_gb × 2.00`.
- Data refuel pricing: **$2.00 per GB**.

---

## Enterprise Incident Response Rules

### Step 1 — Incident Lookup
- `GET /api/enterprise/incidents/<incident_id>` → `enterprise_account_id`, severity, engineering_owner, account_owner.

### Step 2 — Export Runs
- `GET /api/enterprise/export-runs?incident_id=<id>` → find the contiguous failed window.
- `start_date` = first failed day, `end_date` = last failed day.
- `failed_days` = count of consecutive failures in the window.
- `backfill_days` = same as `failed_days` (manual backfill covers every failed day).

### Step 3 — Root Cause
- `GET /api/enterprise/messages?query=<keywords>` with terms from the complaint (e.g., "export", "credential", "rotation", "pipeline").
- Derive a concise root-cause string (e.g., `"stale credential after rotation"`).
- Check for alert mentions. If alerts were archived before the failure: `contributing_alert_issue = "ARCHIVED_ALERT_ROUTE"`. Otherwise `NONE` or `UNKNOWN`.

### Step 4 — SLA
- `GET /api/enterprise/sla/<enterprise_account_id>` → credit percentage for the failure duration/severity.

### Naming Conventions
- **channel_name**: Client name lowercase, hyphenated. E.g., `"Asteri Retail Inc."` → `"asteri-retail-inc"`.
- **evidence_folder**: `"<Client Name> <Month> <Year> Investigation"`. E.g., `"Asteri Retail Inc. May 2026 Investigation"`.
- **report_title**: `"<Client Name> Export Failure - Resolution Report"`.

### Share Permissions
- Always a list of `{user, permission}` objects.
- Order: match the order in `permission_users_to_include` from requirements.
- Permission values: `view`, `edit`, or `upload_only`.

### Severity Triage
- Multi-day export failure blocking executive reporting → **Critical**.
- Use the severity from the incident API if available; otherwise infer from impact.

### Response Status
- If SLA credit > 0% → `NEEDS_FINANCE_REVIEW`.
- If root cause uncertain → `UNDER_INVESTIGATION` or `NEEDS_ENGINEERING_REVIEW`.
- Fully resolved with no credit → `READY_TO_SEND`.

---

## SLA Queue Review Rules (Train 004 variant)

Same triage as ticket rules above, with these additional `key_blocker` mappings:

| Condition | key_blocker | route_team |
|---|---|---|
| Active outage match | ACTIVE_OUTAGE | NONE |
| Account doesn't exist / malformed ID | INVALID_ACCOUNT | NONE |
| Auth credentials broken | AUTH_FAILED | NONE |
| Account suspended — overdue | OVERDUE_SUSPENSION | ACCOUNTS_PAYABLE |
| Account suspended — fraud | FRAUD_SUSPENSION | NONE |
| Backbone / capacity errors | NETWORK_CAPACITY | NETWORK_ENGINEERING |
| Provisioning mismatch / stale | PROVISIONING_STALE | TIER2_SUPPORT |
| Physical line fault | PHYSICAL_LINE_FAULT | FIELD_OPS |
| No blocker (auto-fixable) | NONE | NONE |

---

## Output Conventions (Checklist)

1. **Preserve input order** — tickets/cases in output must match the order in the input payload.
2. **All enum values** — copy exactly from the answer template. No invented values.
3. **Empty strings vs null** — use `""` for absent IDs (outage_id, bill_id). Never `null`.
4. **Numeric types**:
   - `charge_amount_usd`: always two decimals (`0.00`, `86.40`, `4.00`).
   - `data_refuel_gb`: one decimal (`2.0`, `0.0`).
   - Counts / percentages: plain integers.
5. **Booleans** — lowercase `true` / `false`.
6. **Summary counts must sum correctly** — verify each summary field against the decision list before returning.
7. **Date format** — `YYYY-MM-DD` strings.
8. **Never fabricate data** — always pull from API responses. If an API field is absent, default to the zero-value for its type.

---

## Common Pitfalls

- **Forgetting to override localhost** — always use the `environment_access.md` base URL, never `127.0.0.1`.
- **Calling diagnostics for outage tickets** — skip diagnostics when an active outage is found; the ticket is PENDING_ACTION.
- **Calling diagnostics for FAILED tickets** — skip for INVALID_ACCOUNT, INELIGIBLE_ACCOUNT, AUTH_FAILED.
- **Missing the outage check** — always check outages BEFORE diagnostics; an outage changes the entire resolution path.
- **Wrong escalation team** — FIELD_OPS for physical/field issues, NETWORK_ENGINEERING for capacity/backbone, TIER2_SUPPORT for provisioning/config.
- **Forgetting customer_preferences** — when the payload includes `customer_preferences`, check the case_id key for `accepted_refuel_gb` and `does_not_want_plan_change`.
- **Mixing up TOGGLE_ROAMING vs ENABLE_LINE_ROAMING** — TOGGLE_ROAMING is a device-side action (phone setting), ENABLE_LINE_ROAMING is a carrier-side provisioning change (`carrier_update_required: true`).
- **Missing secondary_action** — always include it even when `NO_ACTION`; never omit the field.
- **Summary miscounts** — double-check that `batch_summary` / `queue_summary` / `worklist_summary` counts exactly match the decisions array.

---

## Compact SOP

1. **Read** the answer template first — it defines the output shape and enums.
2. **Read** all input payloads (CSV, JSON, email).
3. **For each ticket/case in order:**
   a. Fetch the entity from the API (ticket, case, incident).
   b. Fetch related records (account, line, plan, device, outage, SLA).
   c. Apply the triage rules above to determine status, route, blockers, and flags.
   d. Populate one entry in the decisions array.
4. **Compute summaries** by counting across the decisions array.
5. **Validate** enum values, numeric formats, and summary counts.
6. **Return** only the JSON object matching the answer template — no markdown, no explanation.
