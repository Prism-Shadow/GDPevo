# CRM Support Console — Agent Skill

## Environment
- **Base URL**: Read `environment_access.md` first. If it specifies `GDPEVO_ENV_BASE_URL`, use that. Otherwise default to the URL in the task prompt.
- **Health check**: `GET /health` → `{ok, service}`
- **Catalog**: `GET /api/catalog` lists all endpoints and record counts (generated seed data).

---

## API Reference

### Service Tickets (internet / voice / video)
| Endpoint | Key Fields |
|---|---|
| `GET /api/tickets/<id>` | `ticket_id`, `account_id`, `service_area`, `service_type`, `subscribed_mbps`, `status`, `issue_summary` |
| `GET /api/accounts/<id>` | `account_id`, `name`, `status` ("Active"|"Suspended"), `tier`, `service_area`, `authentication.last_login_status` ("SUCCESS"|"FAILURE"), `authentication.account_recovery_status` ("" or "FAILURE") |
| `GET /api/outages?service_area=<area>` | Array of `{outage_id, active, service_area, service_types[], eta_hours, impact_score}` |
| `GET /api/diagnostics/<ticket_id>` | `bandwidth_mbps`, `jitter_ms`, `latency_ms`, `root_causes[]` |
| `GET /api/troubleshooting/<ticket_id>` | `steps[]`, `post_bandwidth_mbps`, `post_jitter_ms`, `post_latency_ms` |

### Mobile Cases
| Endpoint | Key Fields |
|---|---|
| `GET /api/cases/<case_id>` | `case_id`, `customer_id`, `line_id`, `device_id`, `issue_type`, `customer_location` |
| `GET /api/lines/<line_id>` | `line_id`, `customer_id`, `device_id`, `plan_id`, `status` ("Active"|"Suspended"), `suspension_reason`, `roaming_enabled`, `data_used_gb` |
| `GET /api/devices/<device_id>` | `sim_status`, `mobile_data_enabled`, `phone_roaming_enabled`, `data_saver_mode`, `vpn_connected`, `network_mode_preference`, `signal_strength`, `speed_test`, `messaging_permissions{sms,storage}`, `airplane_mode`, `can_send_mms`, `mmsc_url_present`, `wifi_calling_enabled`, `model` |
| `GET /api/plans/<plan_id>` | `data_limit_gb`, `data_refueling_price_per_gb`, `monthly_price_usd` |
| `GET /api/bills` (list) | `bill_id`, `customer_id`, `amount_due_usd`, `status` ("Paid"|"Overdue"), `due_date` |
| `GET /api/customers` (list) | `customer_id`, `name`, `phone_number`, `status` |

### Enterprise
| Endpoint | Key Fields |
|---|---|
| `GET /api/enterprise/incidents/<id>` | `incident_id`, `enterprise_account_id`, `severity`, `engineering_owner`, `account_owner`, `product`, `status`, `summary` |
| `GET /api/enterprise/export-runs?incident_id=<id>` | Array of `{run_date, status, failure_code, exported_record_count}` |
| `GET /api/enterprise/messages?query=<text>` | Array of `{message_id, author, body, channel, created_at}` |
| `GET /api/enterprise/sla/<ent_account_id>` | `credit_trigger`, `monthly_export_credit_percent`, `executive_contact` |
| `GET /api/enterprise/accounts` (list) | `enterprise_account_id`, `name`, `account_owner`, `finance_owner`, `tier` |

---

## Decision SOPs

### SOP A: Offline Ticket Batch Resolution (train_001 style)

Per ticket, follow this decision tree in order:

**Step 1 — Account Validation**
- `GET /api/accounts/<account_id>`
- **404** → `final_resolution_status: "FAILED"`, `resolution_route: "INVALID_ACCOUNT"`, all issue flags false, no diagnostic
- **status = "Suspended"** → `"FAILED"`, `"INELIGIBLE_ACCOUNT"`, all issue flags false, no diagnostic
- **auth failure** (`last_login_status = "FAILURE"` or `account_recovery_status = "FAILURE"`) → `"FAILED"`, `"AUTH_FAILED"`, all false, no diagnostic

**Step 2 — Outage Check**
- `GET /api/outages?service_area=<ticket.service_area>` (or scan `GET /api/outages` for matching `service_area`)
- If an **active** outage covers the account's `service_area` AND `service_type` → `"PENDING_ACTION"`, `"OUTAGE_WAIT"`, populate `outage_id`, all issue flags false, no diagnostic needed

**Step 3 — Diagnostic**
- `GET /api/diagnostics/<ticket_id>`
- Set `diagnostic_needed: true`
- Set issue flags using thresholds:
  - `latency_issue`: `latency_ms > 80`
  - `stability_issue`: `jitter_ms > 20`
  - `bandwidth_issue`: `bandwidth_mbps < subscribed_mbps`
- `GET /api/troubleshooting/<ticket_id>`

**Step 4 — Resolution Decision**
- **Auto-troubleshooting succeeds**: post-troubleshooting metrics show significant improvement AND root causes are software/config fixable (CONFIGURATION_DRIFT, VOICE_PROFILE_STALE, etc.) → `"RESOLVED"`, `"AUTO_TROUBLESHOOTING"`, `escalation_team: "NONE"`
- **Auto-troubleshooting insufficient**: post metrics still below thresholds AND root causes indicate physical/network damage (FIBER_DROP_DAMAGE, SIGNAL_LOSS, BACKBONE_CAPACITY, PROVISIONING_STALE) → `"ESCALATED"`, `"ESCALATION"`
  - FIBER_DROP_DAMAGE / SIGNAL_LOSS → `escalation_team: "FIELD_OPS"`
  - BACKBONE_CAPACITY → `escalation_team: "NETWORK_ENGINEERING"`
  - PROVISIONING_STALE → `escalation_team: "TIER2_SUPPORT"`

### SOP B: Queue Quality Review (train_004 style)

Uses `key_blocker` instead of per-issue booleans.

| Condition | status | route_team | key_blocker | diagnostic_required |
|---|---|---|---|---|
| Account 404 | FAILED | NONE | INVALID_ACCOUNT | false |
| Auth FAILURE | FAILED | NONE | AUTH_FAILED | false |
| Account Suspended | FAILED | ACCOUNTS_PAYABLE | OVERDUE_SUSPENSION | false |
| Active outage matches area+type | PENDING_ACTION | NONE | ACTIVE_OUTAGE | false |
| Root cause BACKBONE_CAPACITY, ts can't fix | ESCALATED | NETWORK_ENGINEERING | NETWORK_CAPACITY | true |
| Root cause PROVISIONING_STALE, ts can't fix | ESCALATED | TIER2_SUPPORT | PROVISIONING_STALE | true |
| Root cause fixable by auto-ts, post metrics improved | RESOLVED | NONE | NONE | true |

**How to determine "ts can fix" vs "ts can't fix"**: Compare post-troubleshooting metrics to thresholds. If post metrics are still poor (e.g., post bandwidth far below subscribed, or post latency still >100), troubleshooting was insufficient → escalate. Root causes like BACKBONE_CAPACITY and PROVISIONING_STALE are typically beyond auto-ts capability.

### SOP C: Mobile Case Queue (train_002 style)

Per case, query the case, then its line, device, plan, and bills to find the customer's bill.

| Situation | primary_action | secondary_action | final_route | Notes |
|---|---|---|---|---|
| `sim_status: "missing"` + no service | RESEAT_SIM | NO_ACTION | SELF_SERVICE | |
| Line suspended (`suspension_reason: "OVERDUE_BILL"`) | SEND_PAYMENT_REQUEST | RESUME_LINE_REBOOT | BILLING_RECOVERY | Find overdue bill for customer_id → `bill_id`, `charge_amount_usd` |
| Abroad + `phone_roaming_enabled: false` (line roaming ON) | TOGGLE_ROAMING | NO_ACTION | SELF_SERVICE | Device-side toggle |
| `can_send_mms: false` with `messaging_permissions.storage: false` | GRANT_MESSAGING_PERMISSION | NO_ACTION | SELF_SERVICE | `permission: "storage"` |
| Slow data + `vpn_connected: true` | DISCONNECT_VPN | NO_ACTION | SELF_SERVICE | |
| All self-service cases → `permission: "NONE"`, `bill_id: ""`, `charge_amount_usd: 0.0` | | | | |

**Bill lookup for suspended lines**: `GET /api/bills` → filter by `customer_id`, pick the one with `status: "Overdue"`. Use its `bill_id` and `amount_due_usd`.

### SOP D: Mobile Data Recovery (train_005 style)

| Situation | primary_action | final_route | carrier_update | Charge |
|---|---|---|---|---|
| Data over plan limit (`data_used_gb > data_limit_gb`) + customer accepted refuel | REFUEL_DATA | DATA_RECOVERY | false | `refuel_gb × price_per_gb` (from plan) |
| Abroad + `line.roaming_enabled: false` + `device.phone_roaming_enabled: true` | ENABLE_LINE_ROAMING | CARRIER_UPDATE | **true** | 0.00 |
| `data_saver_mode: true` + slow data | TOGGLE_DATA_SAVER | DEVICE_SETTING_FIX | false | 0.00 |
| `network_mode_preference: "3g_only"` + slow data | SET_NETWORK_MODE | DEVICE_SETTING_FIX | false | 0.00 |
| `mobile_data_enabled: false` + no data | TOGGLE_MOBILE_DATA | DEVICE_SETTING_FIX | false | 0.00 |

**Carrier update required**: Only true for ENABLE_LINE_ROAMING (line-side roaming change). Device-side roaming toggle (TOGGLE_ROAMING) does NOT need carrier update.

**Distinction TOGGLE_ROAMING vs ENABLE_LINE_ROAMING**:
- Device has roaming off, line has roaming on → TOGGLE_ROAMING (device-side, no carrier update)
- Device has roaming on, line has roaming off → ENABLE_LINE_ROAMING (line-side, carrier update required)

### SOP E: Enterprise Export Complaint Response (train_003 style)

1. `GET /api/enterprise/incidents/<incident_id>` → severity, owners, enterprise_account_id
2. `GET /api/enterprise/export-runs?incident_id=<id>` → identify failure window, backfill days, root cause from `failure_code`
3. `GET /api/enterprise/messages?query=<company or incident keywords>` → find root cause context; check for alert-archive channel messages
4. `GET /api/enterprise/sla/<enterprise_account_id>` → SLA credit percent
5. `GET /api/enterprise/accounts` → find account owner, finance owner, company name

**Root cause category**: Map `failure_code` to human-readable category. `STALE_CREDENTIAL` → "stale credential after rotation".

**Contributing alert issue**: If any message's `channel` is `"export-alerts-archive"` → `"ARCHIVED_ALERT_ROUTE"`. Otherwise → `"NONE"`.

**Failure window**: From export runs: `min(run_date)` where status=FAILED to `max(run_date)` where status=FAILED. `failed_days` = count of FAILED runs.

**Backfill days**: Same as `failed_days` (each failed day needs one backfill day).

**SLA credit**: Use `monthly_export_credit_percent` from SLA endpoint.

**Naming conventions** (use actual company name from enterprise account):
- `channel_name`: lowercase-hyphen company name (e.g., "Asteri Retail Inc." → "asteri-retail-inc")
- `evidence_folder`: `"<Company> <Month Year> Investigation"` (infer month/year from incident received_at or run dates)
- `report_title`: `"<Company> Export Failure - Resolution Report"`

**Share permissions**: From `response_requirements.permission_users_to_include` (preserve order). Assign `"view"` to finance-related users, `"edit"` to engineering/ops users.

**Response status**: If SLA credit > 0 → `"NEEDS_FINANCE_REVIEW"`. Otherwise → `"READY_TO_SEND"` (default).

---

## Output Conventions

### Always
- Preserve input order in arrays (ticket list order, case_id ascending order).
- Return **only JSON** conforming exactly to the provided answer template.
- Empty string `""` for absent IDs (outage_id, bill_id), not `null`.
- `"NONE"` string for absent enum team/permission values, not empty string or null.
- Numeric fields: charge amounts with exactly 2 decimals; data_gb with 1 decimal; integers without decimals.
- Booleans: `true`/`false` (JSON literals), never strings.

### Batch summaries
- Counts must be integers matching the decision arrays exactly.
- `tickets_requiring_customer_wait`: count of items where resolution requires customer to wait (OUTAGE_WAIT, billing recovery, human transfer). Not simply `PENDING_ACTION` count — only those where the customer must wait for an external resolution.

---

## Common Pitfalls

1. **Outage priority**: Always check outages BEFORE running diagnostics. If an active outage covers the service area and type, skip diagnostics entirely — the ticket is PENDING_ACTION/OUTAGE_WAIT.
2. **Account-not-found (404)**: The account_id in the ticket may be bogus (e.g., "BAD-5403"). Treat 404 as INVALID_ACCOUNT → FAILED, no diagnostic.
3. **Auth failure vs Suspension**: Both are pre-check failures but map differently. Auth failure → AUTH_FAILED. Suspension → OVERDUE_SUSPENSION or INELIGIBLE_ACCOUNT.
4. **Post-troubleshooting evaluation**: Don't assume troubleshooting always works. Compare post metrics to thresholds. If still failing, escalate.
5. **TOGGLE_ROAMING vs ENABLE_LINE_ROAMING**: Check BOTH `line.roaming_enabled` AND `device.phone_roaming_enabled`. The disabled side determines the action and whether a carrier update is needed.
6. **Bill matching**: Match bills by `customer_id`, not `case_id` or `line_id`. Pick the one with `status: "Overdue"`.
7. **Missing diagnostics/troubleshooting**: If a ticket is blocked pre-check (outage, invalid account, auth failure), diagnostics and troubleshooting may still exist but should NOT be fetched — the pre-check result governs.
8. **Enterprise message search**: Try multiple search terms (company name, incident ID, "credential", product name). Messages may be sparse.
9. **Timestamp/month inference**: Use the incident `received_at` or export run dates to determine the month/year for folder/report naming.
10. **Precision**: charge_amount_usd requires exactly 2 decimal places; data_refuel_gb requires exactly 1 decimal place. Use `0.0` / `0.00` not `0`.
