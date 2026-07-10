# Support Console API Skill

## Environment
- Base URL provided by `environment_access.md` (GDPEVO_ENV_BASE_URL). Never use localhost unless the remote URL explicitly points there.
- Always consult `/api/catalog` first when entering an unfamiliar task category to confirm available endpoints.

## API Endpoint Reference

### Core Endpoints
| Endpoint | Purpose |
|---|---|
| `/api/accounts/<id>` | Account status, auth (last_login_status, account_recovery_status), tier, service_area |
| `/api/tickets/<id>` | Ticket detail: account_id, service_area, service_type, subscribed_mbps, status |
| `/api/outages?service_area=<area>` | Active outages with outage_id, eta_hours, impact_score, service_types affected |
| `/api/diagnostics/<ticket_id>` | Post-hoc root causes, bandwidth/latency/jitter measurements |
| `/api/troubleshooting/<ticket_id>` | Remediation steps taken and post-fix metrics |

### Mobile Support Endpoints
| Endpoint | Purpose |
|---|---|
| `/api/cases` / `/api/cases/<id>` | Case records with customer_id, line_id, device_id, issue_type |
| `/api/customers/<id>` | Customer name, status, phone_number |
| `/api/lines/<id>` | Line status, suspension_reason, roaming_enabled, plan_id, data_used_gb |
| `/api/devices/<id>` | Full device state: sim_status, airplane_mode, mobile_data_enabled, phone_roaming_enabled, data_saver_mode, network_mode_preference, vpn_connected, signal_strength, speed_test, messaging_permissions, can_send_mms, wifi_calling_enabled |
| `/api/plans/<id>` | data_limit_gb, data_refueling_price_per_gb, monthly_price_usd |
| `/api/bills` | bill_id, customer_id, amount_due_usd, status (Paid/Overdue), due_date |

### Enterprise Endpoints
| Endpoint | Purpose |
|---|---|
| `/api/enterprise/incidents/<id>` | Incident: severity, engineering_owner, account_owner, enterprise_account_id, product, status |
| `/api/enterprise/export-runs?incident_id=<id>` | Export run history: run_date, status, failure_code, exported_record_count |
| `/api/enterprise/messages?query=<text>` | Channel messages with author, channel, body, created_at |
| `/api/enterprise/sla/<account_id>` | SLA contract: credit triggers, credit percentages |
| `/api/enterprise/accounts` | Enterprise accounts: name, tier, account_owner, finance_owner |

## Business Rules by Domain

### Offline Service Ticket Resolution (train_001 / train_004 pattern)

**Resolution routing:**
- Active outage covering the ticket's service_type → `PENDING_ACTION`, route `OUTAGE_WAIT`, set `outage_id`
- Successful auto-troubleshooting (post-fix metrics improved) → `RESOLVED`, route `AUTO_TROUBLESHOOTING`
- Root cause requires physical/network engineering (FIBER_DROP_DAMAGE, SIGNAL_LOSS, BACKBONE_CAPACITY, PROVISIONING_STALE) → `ESCALATED`, route `ESCALATION`
- Account suspended → `FAILED`, route `INELIGIBLE_ACCOUNT`
- Account not found → `FAILED`, route `INVALID_ACCOUNT`
- Authentication failure → `FAILED`, route team `TIER2_SUPPORT`

**Escalation team mapping:**
- Backbone/network capacity issues → `NETWORK_ENGINEERING`
- Physical line/fiber damage → `NETWORK_ENGINEERING`
- Provisioning stale → `NETWORK_ENGINEERING`
- Auth failures → `TIER2_SUPPORT`
- Invalid account / overdue suspension → `ACCOUNTS_PAYABLE`
- Active outage / auto-fix / no issue → `NONE`

**Issue flag thresholds (internet tickets):**
- `latency_issue`: diagnostic latency > ~100ms
- `stability_issue`: diagnostic jitter > ~30ms
- `bandwidth_issue`: diagnostic bandwidth < subscribed_mbps
- `diagnostic_needed`: `true` when diagnostics are required to identify the root cause; `false` when the blocker is obvious from account/outage state alone (active outage, invalid account, auth failure, account suspension). Diagnostics that DID run does not mean they were *needed* — if the cause was already obvious, set `false`.

**Key blockers (train_004 queue-quality pattern):**
- `ACTIVE_OUTAGE` — ticket area has an active outage
- `INVALID_ACCOUNT` — account ID not found in the system
- `AUTH_FAILED` — account exists but last login failed
- `OVERDUE_SUSPENSION` — account status is Suspended
- `NETWORK_CAPACITY` — backbone capacity root cause
- `PROVISIONING_STALE` — provisioning stale root cause
- `NONE` — no systemic blocker; can be auto-resolved

### Mobile Support Queue (train_002 pattern)

**Always check both line-level AND device-level state** — they frequently differ. The line's roaming_enabled and the device's phone_roaming_enabled are independent.

**Primary action selection:**
- `sim_status: "missing"` → `RESEAT_SIM`
- Line `Suspended` + `OVERDUE_BILL` → `SEND_PAYMENT_REQUEST` + `RESUME_LINE_REBOOT` (secondary)
- Line `roaming_enabled: true` but device `phone_roaming_enabled: false` → `TOGGLE_ROAMING`
- Line `roaming_enabled: false` while abroad → `ENABLE_LINE_ROAMING`
- `can_send_mms: false` + missing `storage` permission → `GRANT_MESSAGING_PERMISSION` with `permission: "storage"`
- `vpn_connected: true` + slow data → `DISCONNECT_VPN`
- `data_saver_mode: true` + slow data → `TOGGLE_DATA_SAVER`
- `network_mode_preference: "3g_only"` + slow data → `SET_NETWORK_MODE`
- `mobile_data_enabled: false` + no data → `TOGGLE_MOBILE_DATA`

**Permission field:** Use the specific missing permission string (`sms`, `storage`, or `sms_and_storage`). Set `"NONE"` when no permission change is needed.

**Final route mapping:**
- Self-service device/line fixes → `SELF_SERVICE`
- Payment requests → `BILLING_RECOVERY`
- Carrier-side changes (roaming enable on line) → `CARRIER_UPDATE`
- Complex/escalated issues → `HUMAN_TRANSFER`

**Bill lookup:** When a line is suspended for `OVERDUE_BILL`, query `/api/bills` filtered by customer_id to find the overdue bill. Use `amount_due_usd` from the bill record.

### Mobile Data Recovery (train_005 pattern)

Same device/line diagnostic approach as train_002, with additional data-refuel logic:

- `data_used_gb > plan.data_limit_gb` → `REFUEL_DATA` with customer's accepted refuel GB
- Charge = refuel_gb × `plan.data_refueling_price_per_gb`
- `carrier_update_required: true` ONLY for carrier-side changes (`ENABLE_LINE_ROAMING`). Device-side toggles are NOT carrier updates.
- Final routes: `DATA_RECOVERY` (refuel), `CARRIER_UPDATE` (line roaming), `DEVICE_SETTING_FIX` (toggles/mode changes), `HUMAN_TRANSFER`

### Enterprise Incident Response (train_003 pattern)

**Data gathering pipeline:**
1. Query incident → get enterprise_account_id, owners, severity
2. Query export-runs by incident_id → identify failure window (first to last FAILED run dates), count failed_days
3. Query messages by incident/client name → find root cause details and SLA discussions
4. Query SLA contract → get credit_percent
5. Query enterprise accounts → get finance_owner for share_permissions

**Naming conventions** (from response_requirements `naming_style`):
- Channel name: lowercase-hyphen, from the message's `channel` field (e.g., `export-alerts-archive`)
- Evidence folder: `{client-slug}-{incident-date}-investigation` (e.g., `asteri-retail-2026-05-15-investigation`)
- Report title: `{client-slug}-{product}-failure-report` (e.g., `asteri-retail-export-failure-report`)

**Field conventions:**
- `contributing_alert_issue`: `ARCHIVED_ALERT_ROUTE` when the relevant message channel contains "archive"
- `sla_credit_percent`: integer, not a string with `%`
- `response_status`: `READY_TO_SEND` when all evidence is collected and owners are identified. `NEEDS_FINANCE_REVIEW` only if explicitly indicated.
- `backfill_days`: matches the number of `failed_days` in the failure window
- `share_permissions`: ordered by user as listed in requirements; finance_owner typically gets `view`

## Common Pitfalls

1. **Confusing line-level and device-level state.** Roaming, mobile data, and other settings exist on BOTH the carrier/line side and the device side. Check both independently.
2. **Setting `diagnostic_needed: true` just because diagnostics ran.** If the root cause is obvious without diagnostics (active outage, invalid account, suspended account, auth failure), set `false`.
3. **Using the wrong endpoint for customer data.** `CUST-*` IDs use `/api/customers`, not `/api/accounts` (which uses `ACC-*` ids).
4. **Missing the catalog step.** Always check `/api/catalog` to confirm which endpoints exist before designing the data-gathering plan.
5. **Using string formatting for numeric fields.** `sla_credit_percent`, `charge_amount_usd`, `data_refuel_gb` are numeric types, not strings.
6. **Overlooking the `carrier_update_required` flag.** Only carrier-side provisioning changes need this set to `true`. Device-side settings changes do not.
7. **Not querying bills for suspended lines.** The bill amount comes from the `/api/bills` list, filtered by customer_id, not from the plan price.
8. **Ignoring `naming_style` in response_requirements.** Naming conventions for channels, folders, and report titles are specified in the task payload and must be followed exactly.

## Compact SOP

### For offline ticket batches:
1. Read ticket CSV → extract ticket_ids and account_ids
2. Query each ticket, account, diagnostics, troubleshooting, and outages for each service_area
3. Classify each ticket: active outage? → OUTAGE_WAIT. Account issue? → FAILED + appropriate route. Diagnostics found fixable root cause? → RESOLVED. Diagnostics found infrastructure issue? → ESCALATED + appropriate team.
4. Fill batch_summary by counting final_resolution_status values

### For mobile case queues:
1. Read case queue → for each case, query line, device, plan, and customer
2. Check bill list for any suspended/overdue lines
3. Cross-reference line state vs device state for each setting
4. Map device anomalies to primary/secondary actions
5. Check plan data limits vs actual usage for data refuel decisions

### For enterprise incidents:
1. Query incident by ID → get enterprise_account_id
2. Query export-runs by incident_id → determine failure window
3. Query messages by client/product name → extract root cause and SLA discussions
4. Query SLA contract → get credit percent
5. Query enterprise accounts → get finance_owner and account_owner
6. Assemble response following naming conventions from response_requirements
