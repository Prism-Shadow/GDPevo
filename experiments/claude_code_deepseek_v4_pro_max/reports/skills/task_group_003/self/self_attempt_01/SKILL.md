# Support Console Skill — Task Group 003

## Environment

- **Base URL**: `http://34.46.77.124:8003` (remote only; never use localhost)
- **Service**: `task_group_003_support_console`
- **Auth**: None required (public API)
- **Data shape**: All timestamps are ISO-8601 with `Z` suffix. All enums are `UPPER_SNAKE_CASE`. All IDs are prefixed (see ID glossary below).

## ID Prefix Glossary

| Prefix | Entity | Example |
|--------|--------|---------|
| `ACC-` | Consumer/Business Account | `ACC-5107` |
| `TCK-` | Support Ticket | `TCK-5107` |
| `CASE-` | Mobile Case | `CASE-2101` |
| `CUST-` | Mobile Customer | `CUST-2101` |
| `LINE-` | Mobile Line | `LINE-2101` |
| `DEV-` | Mobile Device | `DEV-2101` |
| `PLAN-` | Mobile Plan | `PLAN-PREMIUM` |
| `BILL-` | Bill | `BILL-2101` |
| `ENT-` | Enterprise Account | `ENT-3001` |
| `INC-` | Enterprise Incident | `INC-7301` |
| `RUN-` | Export Run | `RUN-AST-0` |
| `MSG-` | Enterprise Message | `MSG-7301-A` |
| `OUT-` | Service Outage | `OUT-9102` |
| `SA-` | Service Area | `SA-17` |

## Endpoint Catalog

### Consumer / Business (Residential Fiber)

| Endpoint | Method | Notes |
|----------|--------|-------|
| `/api/accounts` | GET | List all accounts |
| `/api/accounts/<account_id>` | GET | Single account |
| `/api/tickets` | GET | List all tickets |
| `/api/tickets/<ticket_id>` | GET | Single ticket |
| `/api/outages` | GET | List all outages |
| `/api/outages?service_area=<area>` | GET | Filter outages by service area |
| `/api/diagnostics/<ticket_id>` | GET | Diagnostic results for a ticket |
| `/api/troubleshooting/<ticket_id>` | GET | Remediation steps and post-fix metrics |

### Mobile / Wireless

| Endpoint | Method | Notes |
|----------|--------|-------|
| `/api/cases` | GET | List all mobile cases |
| `/api/cases/<case_id>` | GET | Single case |
| `/api/customers` | GET | List all mobile customers |
| `/api/lines` | GET | List all mobile lines |
| `/api/lines/<line_id>` | GET | Single line |
| `/api/devices/<device_id>` | GET | Single device |
| `/api/plans/<plan_id>` | GET | Single plan |
| `/api/bills` | GET | List all bills |

### Enterprise

| Endpoint | Method | Notes |
|----------|--------|-------|
| `/api/enterprise/accounts` | GET | List enterprise accounts |
| `/api/enterprise/incidents` | GET | List enterprise incidents |
| `/api/enterprise/incidents/<incident_id>` | GET | Single incident |
| `/api/enterprise/export-runs?incident_id=<id>` | GET | Export runs for an incident |
| `/api/enterprise/messages?query=<text>` | GET | Text search across messages |
| `/api/enterprise/sla/<enterprise_account_id>` | GET | SLA contract details |

### Meta

| Endpoint | Notes |
|----------|-------|
| `/health` | Liveness check; returns `{"ok": true, "service": "..."}` |
| `/api/catalog` | Endpoint listing + record counts; use to gauge data scale |

## Data Models

### Account (`ACC-*`)
```
account_id, name, service_area, status, tier
authentication: { last_login_status, account_recovery_status, last_login_at }
```
- **status**: `Active` | `Suspended`
- **tier**: always `standard` in this dataset
- **authentication.last_login_status**: `SUCCESS` | `FAILURE`
- **authentication.account_recovery_status**: `""` (normal) | `FAILURE`

### Ticket (`TCK-*`)
```
ticket_id, account_id, service_area, service_type, subscribed_mbps, status, issue_summary, created_at
```
- **service_type**: `internet` | `video` | `voice`
- **subscribed_mbps**: 100, 200, 300, 500, 750
- **status**: always `OPEN` in this dataset
- **account_id**: can be `BAD-*` (non-existent account → intake error)

### Diagnostics (`/api/diagnostics/<ticket_id>`)
```
ticket_id, bandwidth_mbps, latency_ms, jitter_ms, root_causes[], started_at, completed_at
```
- **root_causes** (array of enum strings):
  - `CONFIGURATION_DRIFT` — account/profile out of sync
  - `FIBER_DROP_DAMAGE` — physical line damage
  - `SIGNAL_LOSS` — signal degradation
  - `BACKBONE_CAPACITY` — regional backbone overload
  - `VOICE_PROFILE_STALE` — voice config needs refresh
  - `GENERATED_NOISE` — non-deterministic filler (ignore for business logic)

### Troubleshooting (`/api/troubleshooting/<ticket_id>`)
```
ticket_id, steps[], post_bandwidth_mbps, post_latency_ms, post_jitter_ms, started_at, completed_at
```
- **steps** (ordered array): `PROFILE_REFRESH`, `PROVISIONING_SYNC`, `LINE_TEST`, `SIGNAL_REFRESH`, `BACKBONE_REROUTE_ATTEMPT`, `VOICE_PROFILE_REFRESH`, `GENERATED_CHECK`

### Outage (`OUT-*`)
```
outage_id, service_area, active, service_types[], impact_score, eta_hours, started_at
```
- **active**: boolean — only `true` outages affect service
- **impact_score**: 0.0–1.0 float
- **service_types**: array of affected service types

### Case (`CASE-*`) — Mobile
```
case_id, customer_id, line_id, device_id, issue_type, customer_location, summary, opened_at
```
- **issue_type**: `NO_SERVICE` | `MOBILE_DATA` | `SLOW_DATA` | `MMS`
- **customer_location**: `home` | `abroad`

### Line (`LINE-*`) — Mobile
```
line_id, customer_id, device_id, phone_number, plan_id, status, suspension_reason,
roaming_enabled, data_used_gb, contract_end_date
```
- **status**: `Active` | `Suspended`
- **suspension_reason**: `""` | `OVERDUE_BILL` | `CONTRACT_ENDED`

### Device (`DEV-*`) — Mobile
```
device_id, model, sim_status, signal_strength, speed_test, mobile_data_enabled,
airplane_mode, phone_roaming_enabled, wifi_calling_enabled, data_saver_mode,
vpn_connected, network_mode_preference, can_send_mms, mmsc_url_present,
messaging_permissions: { sms, storage }
```
- **sim_status**: `active` | `missing` | `locked_pin`
- **signal_strength**: `none` | `good` | `excellent`
- **speed_test**: `no_connection` | `poor` | `fair` | `excellent`
- **network_mode_preference**: `4g_5g_preferred` | `3g_only`

### Plan (`PLAN-*`) — Mobile
```
plan_id, name, data_limit_gb, monthly_price_usd, data_refueling_price_per_gb
```

### Bill (`BILL-*`)
```
bill_id, customer_id, amount_due_usd, due_date, status
```
- **status**: `Paid` | `Overdue` | `Issued`

### Enterprise Account (`ENT-*`)
```
enterprise_account_id, name, tier, account_owner, finance_owner
```
- **tier**: `Enterprise` | `Strategic`

### Enterprise Incident (`INC-*`)
```
incident_id, enterprise_account_id, product, severity, status, summary,
account_owner, engineering_owner, received_at
```
- **severity**: `Critical` | `High` | `Medium`
- **product**: `monthly_export` | `dashboard_refresh` | `generated_product`

### Export Run (`RUN-*`)
```
run_id, enterprise_account_id, incident_id, run_date, status, exported_record_count, failure_code
```
- **status**: `FAILED` | `SUCCEEDED`
- **failure_code**: `""` (success) | `STALE_CREDENTIAL` | `STAGING_STORAGE_QUOTA`

### Enterprise Message (`MSG-*`)
```
message_id, author, body, channel, created_at
```
- **channel**: `export-alerts-archive` | `account-escalations` | `data-platform` | `support`

### Enterprise SLA
```
enterprise_account_id, credit_trigger, monthly_export_credit_percent, executive_contact
```

## Standard Operating Procedures

### SOP-1: Triage a Consumer/Business Ticket

```
1. GET /api/tickets/<ticket_id> → extract account_id, service_area, service_type
2. GET /api/accounts/<account_id> → check status, auth
3. GET /api/outages?service_area=<service_area> → check for active outages covering service_type
4. GET /api/diagnostics/<ticket_id> → get root causes
5. GET /api/troubleshooting/<ticket_id> → get remediation steps
```

**Decision tree:**
- Account not found (`BAD-*` account_id) → **Intake error** — ticket references non-existent account
- Account `status: "Suspended"` → **Account-level issue** — billing/account hold
- Auth `last_login_status: "FAILURE"` or `account_recovery_status: "FAILURE"` → **Authentication failure**
- Active outage for service_area AND service_type in outage's service_types → **Known outage** (eta_hours, impact_score provide context)
- Otherwise → **Technical issue** — root_causes from diagnostics tell the story

### SOP-2: Triage a Mobile Case

```
1. GET /api/cases/<case_id> → extract line_id, device_id, issue_type, customer_location
2. GET /api/lines/<line_id> → check status, roaming, data_used_gb, plan_id
3. GET /api/devices/<device_id> → check all device flags
4. GET /api/plans/<plan_id> → check data_limit_gb
5. If line Suspended: check suspension_reason, check /api/bills for bill status
```

**Decision matrix by issue_type:**

| issue_type | Check | Root Cause |
|------------|-------|------------|
| `NO_SERVICE` | `device.sim_status` = `missing` | SIM missing |
| `NO_SERVICE` | `device.sim_status` = `locked_pin` | SIM PIN locked |
| `NO_SERVICE` | `device.airplane_mode` = true | Airplane mode on |
| `NO_SERVICE` | `line.status` = `Suspended`, `suspension_reason` = `OVERDUE_BILL` | Overdue bill |
| `NO_SERVICE` | `line.status` = `Suspended`, `suspension_reason` = `CONTRACT_ENDED` | Contract expired |
| `MOBILE_DATA` | `device.mobile_data_enabled` = false | Data toggle off |
| `MOBILE_DATA` | `line.data_used_gb` > `plan.data_limit_gb` | Data cap reached |
| `MOBILE_DATA` | `customer_location` = `abroad`, `device.phone_roaming_enabled` = false | Device roaming off |
| `MOBILE_DATA` | `customer_location` = `abroad`, `line.roaming_enabled` = false | Line roaming off |
| `SLOW_DATA` | `device.vpn_connected` = true | VPN throttling |
| `SLOW_DATA` | `device.data_saver_mode` = true | Data saver active |
| `SLOW_DATA` | `device.network_mode_preference` = `3g_only` | Forced 3G |
| `MMS` | `device.can_send_mms` = false | MMS capability off |
| `MMS` | `device.messaging_permissions.storage` = false | Storage permission denied |
| `MMS` | `device.mmsc_url_present` = false | MMSC URL missing |

### SOP-3: Investigate an Enterprise Incident

```
1. GET /api/enterprise/incidents/<incident_id> → product, severity, enterprise_account_id
2. GET /api/enterprise/export-runs?incident_id=<incident_id> → failure pattern
3. GET /api/enterprise/messages?query=<keyword> → human context (query by product, failure_code, account name)
4. GET /api/enterprise/sla/<enterprise_account_id> → credit terms
5. GET /api/enterprise/accounts → find account owner/finance owner
```

**Failure code interpretation:**
- `STALE_CREDENTIAL` → Credential rotation happened but scheduler still uses old secret. Fix: update credentials in scheduler.
- `STAGING_STORAGE_QUOTA` → Staging bucket full. Fix: increase quota or clear old data.
- Consecutive failures → Check SLA for credit trigger thresholds.

**SLA credit patterns:**
- Count consecutive failed runs (same failure_code, sequential dates)
- Match against `credit_trigger` text and `monthly_export_credit_percent`
- SLA credits are percentage of monthly bill

## Common Pitfalls

1. **Don't stop at the first finding.** A ticket/case may have multiple contributing factors — check all related entities. For example, a "no service" case might have both a suspended line AND a missing SIM.

2. **Outages only explain tickets in the same service_area.** Always cross-reference `ticket.service_area` with `outage.service_area`, and verify `ticket.service_type` is in `outage.service_types`.

3. **Not all outages are active.** Only `active: true` outages affect current service. `active: false` outages are historical.

4. **`GENERATED_NOISE` root causes are non-deterministic filler.** Don't build business logic around them. Focus on the deterministic root causes: `CONFIGURATION_DRIFT`, `FIBER_DROP_DAMAGE`, `SIGNAL_LOSS`, `BACKBONE_CAPACITY`, `VOICE_PROFILE_STALE`.

5. **`GENERATED_CHECK` troubleshooting steps are non-deterministic filler.** Same rule — ignore for business logic.

6. **Account ID `BAD-*` is a real pattern.** Tickets can reference non-existent accounts. The `BAD-` prefix indicates an intake/registration error where the account was never created. Verify by checking `/api/accounts/BAD-5403` (returns `{"error": "not_found"}`).

7. **Roaming requires BOTH device AND line.** A traveler abroad needs `device.phone_roaming_enabled = true` AND `line.roaming_enabled = true`. Check both.

8. **Data cap is plan.data_limit_gb vs line.data_used_gb.** Compare the plan limit with actual usage. `data_used_gb > data_limit_gb` = cap reached.

9. **Contract expiration is a date comparison.** `contract_end_date` is `YYYY-MM-DD`. If it's before the case `opened_at` date, the contract has ended (and the line should be suspended with `CONTRACT_ENDED`).

10. **MMS failures have 3 distinct root causes.** Check `can_send_mms`, then `messaging_permissions.storage`, then `mmsc_url_present`. They are independent checks.

11. **Enterprise tiers matter for SLA.** `Strategic` tier accounts may have higher credit percentages and tighter triggers than `Enterprise` tier.

12. **Messages are best queried with keywords from the incident.** Query by product name (`export`, `dashboard`), failure code (`credential`, `quota`), or account name (`Asteri`, `Quanta`).

## Output Conventions

When producing a diagnosis, structure output as:

```
## Diagnosis for <ID>

**Root Cause:** <primary cause in plain English>
**Evidence:**
- <entity.field> = <value> → <what this means>
- ...

**Resolution:** <what was done or should be done>
**Metrics Impact:** <before → after for bandwidth/latency if applicable>
```

For multiple findings, list all with the most actionable/specific first. Distinguish between "this is the cause" vs "this is a contributing factor."

## Data Generation Notes

- Some records contain "Generated" in names/summaries (e.g., "Generated Customer 01", "Generated support ticket"). These are synthetic filler records with non-deterministic values.
- Root causes labeled `GENERATED_NOISE` and troubleshooting steps labeled `GENERATED_CHECK` are non-deterministic — do not treat them as meaningful business signals.
- Generated incidents/products/incidents exist but the deterministic ones (INC-7301, INC-8301, INC-8402) contain the real business logic patterns.
