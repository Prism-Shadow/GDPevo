# SCN_003 CRM Support-Console Operations Skill

Executable SOP for resolving three families of support-console tasks against the shared API:
1. **Ticket batch resolution / queue quality** (offline service tickets) — train_001, train_004
2. **Mobile contact-center triage** (case queue / mobile-data worklist) — train_002, train_005
3. **Enterprise export-complaint response package** — train_003

All facts below were derived by probing the live API and reasoning through the train tasks. Numeric thresholds marked **[inferred]** are committed estimates; string conventions marked **[inferred]** are committed naming rules. Use them as-is.

---

## 0. API MAP

Base URL: the prompt says `http://127.0.0.1:8057` "unless the harness provides a different base URL". The harness-provided base for this environment is **`<remote-env-url>`**. Always use the harness-provided base if present; fall back to the prompt's literal base otherwise.

### Ticket / diagnostics endpoints
| Endpoint | Returns | Notes |
|---|---|---|
| `GET /api/tickets` | list of all tickets | fields: ticket_id, account_id, service_type, service_area, status, subscribed_mbps, issue_summary, created_at |
| `GET /api/tickets/{ticket_id}` | single ticket | |
| `GET /api/accounts` | all accounts | fields: account_id, name, status(`Active`/`Suspended`), service_area, tier, authentication{last_login_status, account_recovery_status, last_login_at} |
| `GET /api/accounts/{account_id}` | single account | 404 `not_found` when account_id is invalid (e.g. `BAD-*`) |
| `GET /api/outages` | all outages | fields: outage_id, service_area, service_types[], active, eta_hours, impact_score, started_at |
| `GET /api/diagnostics/{ticket_id}` | diagnostic record | fields: latency_ms, jitter_ms, bandwidth_mbps, root_causes[], started_at, completed_at. **Path param, not query.** Returns 404 at `/api/diagnostics?ticket_id=` (query form does NOT work). |
| `GET /api/troubleshooting/{ticket_id}` | post-troubleshooting record | fields: post_latency_ms, post_jitter_ms, post_bandwidth_mbps, steps[], started_at, completed_at. Path param only. |

### Mobile endpoints
| Endpoint | Returns |
|---|---|
| `GET /api/cases` | cases: case_id, customer_id, line_id, device_id, issue_type, customer_location(`home`/`abroad`), summary, opened_at |
| `GET /api/customers` | customers: customer_id, name, phone_number, status |
| `GET /api/lines` | lines: line_id, customer_id, device_id, plan_id, phone_number, status(`Active`/`Suspended`), suspension_reason(`OVERDUE_BILL`/`CONTRACT_ENDED`/""), roaming_enabled, data_used_gb, contract_end_date |
| `GET /api/plans` | plans: plan_id, name, data_limit_gb, data_refueling_price_per_gb, monthly_price_usd |
| `GET /api/bills` | bills: bill_id, customer_id, amount_due_usd, due_date, status(`Paid`/`Overdue`/`Issued`) |
| `GET /api/devices` | devices: device_id, model, sim_status, signal_strength, speed_test, airplane_mode, mobile_data_enabled, phone_roaming_enabled, data_saver_mode, vpn_connected, wifi_calling_enabled, can_send_mms, mmsc_url_present, messaging_permissions{sms, storage}, network_mode_preference |

### Enterprise endpoints
| Endpoint | Returns |
|---|---|
| `GET /api/enterprise/accounts` | ENT accounts: enterprise_account_id, name, tier, account_owner, finance_owner |
| `GET /api/enterprise/incidents` | incidents: incident_id, enterprise_account_id, product, severity(`Critical`/`High`/`Medium`), status, summary, received_at, engineering_owner, account_owner |
| `GET /api/enterprise/incidents/{incident_id}` | single incident |
| `GET /api/enterprise/export-runs` | export runs: run_id, incident_id, enterprise_account_id, run_date, status(`FAILED`/`SUCCEEDED`), failure_code, exported_record_count |
| `GET /api/enterprise/sla/table`, `/api/enterprise/sla/credit(s)` | returns `{}` (empty stubs) — **SLA credit must be derived, not fetched** |

No endpoints exist for channels, folders, reports, share-permissions, alerts, or a user directory. Those response-package fields are **constructed via naming conventions** (see §5).

---

## 1. TICKET FAMILY — gating, diagnostics, thresholds, escalation

### 1.1 Gating order (apply IN THIS ORDER; first match wins; SKIPS diagnostics)

```
GATE 1 — Account existence
    GET /api/accounts/{account_id} -> 404 not_found?
        => route = INVALID_ACCOUNT, status = FAILED, team = NONE,
           key_blocker = INVALID_ACCOUNT, diagnostic_needed = false
GATE 2 — Account eligibility (account.status)
    account.status == "Suspended"
        => route = INELIGIBLE_ACCOUNT, status = PENDING_ACTION,
           team = ACCOUNTS_PAYABLE, key_blocker = OVERDUE_SUSPENSION
           (or FRAUD_SUSPENSION if evidence says fraud — default OVERDUE),
           diagnostic_needed = false
GATE 3 — Authentication
    authentication.last_login_status == "FAILURE"
    OR authentication.account_recovery_status == "FAILURE"
        => route = AUTH_FAILED, status = PENDING_ACTION, team = NONE,
           key_blocker = AUTH_FAILED, diagnostic_needed = false
GATE 4 — Active outage matching service_area AND service_type
    exists outage o: o.active==true AND o.service_area==ticket.service_area
                   AND ticket.service_type IN o.service_types
        => route = OUTAGE_WAIT, status = PENDING_ACTION, team = NONE,
           key_blocker = ACTIVE_OUTAGE, outage_id = o.outage_id,
           diagnostic_needed = false  (NO diagnostics run)
GATE 5 — Diagnose
    run /api/diagnostics/{ticket_id} and /api/troubleshooting/{ticket_id}
```

**Critical rule:** an active outage **short-circuits to OUTAGE_WAIT with NO diagnostics**, even though the API will still return diagnostic records for that ticket — you MUST ignore them. The outage must match BOTH service_area and the ticket's service_type (an outage covering only `video` does not gate an `internet` ticket).

### 1.2 Diagnostic metric floors (PRE-troubleshooting issue flags)

A ticket is flagged with an issue when the **pre-troubleshooting** diagnostic value violates the floor:

| Metric | Threshold | Issue flag | Scope |
|---|---|---|---|
| `latency_ms` | **> 100 ms** | `latency_issue` | uniform across all service types |
| `jitter_ms` | **> 30 ms** | `stability_issue` (jitter) | uniform across all service types |
| `bandwidth_mbps` | **< 0.90 × `subscribed_mbps`** | `bandwidth_issue` | fraction uniform; value differs because subscribed differs |

**Bandwidth floor table by reported_service_type [inferred]:** floor = 0.90 × subscribed_mbps.

| service_type | bandwidth floor |
|---|---|
| voice | 0.90 × subscribed_mbps |
| internet | 0.90 × subscribed_mbps |
| video | 0.90 × subscribed_mbps |

> Derivation: the three named tickets that RESOLVE via auto-troubleshooting land at 90.7% (TCK-5107, internet sub 300 → post bw 272), 93% (TCK-5402, voice sub 100 → post bw 93), and 91% (TCK-6103, voice sub 100 → post bw 91) of subscribed — all clustered just above 90%. Latency resolved-post values (82, 79, 78) sit below 100 and escalated-post (121, 176, 198, 206, 171) sit above 100 → 100 ms boundary. Jitter resolved-post (21, 18, 19) below 30 and escalated-post (32, 41, 43, 46, 40) above 30 → 30 ms boundary. The floor is treated as uniform 90% across types because voice+internet resolved cases both pin it at ~90%; video has no resolved named case so 90% is the committed estimate.

### 1.3 Resolution via auto-troubleshooting

After gating reaches diagnostics, auto-troubleshooting is attempted. Recompute the three issue flags against the **POST-troubleshooting** values using the SAME thresholds:

- `post_latency_ms ≤ 100` AND `post_jitter_ms ≤ 30` AND `post_bandwidth_mbps ≥ 0.90 × subscribed_mbps`
  - ALL three clear => **final_resolution_status = RESOLVED**, resolution_route = `AUTO_TROUBLESHOOTING`, escalation_team = `NONE`
  - ANY still violates => **final_resolution_status = ESCALATED**, resolution_route = `ESCALATION`, escalation_team = root-cause→team map (§1.4)

The three PRE issue flags reported in the answer (`latency_issue`, `stability_issue`, `bandwidth_issue`) are the **PRE-troubleshooting** violations (true even if the ticket later resolves). For gated tickets (no diagnostics) all three flags are `false`.

### 1.4 Root-cause → escalation_team map (from `/api/diagnostics` `root_causes`)

When a diagnosed ticket is ESCALATED, map the root cause(s) to a team:

| root_cause | escalation_team | key_blocker (train_004) |
|---|---|---|
| `FIBER_DROP_DAMAGE` | `FIELD_OPS` | `PHYSICAL_LINE_FAULT` |
| `SIGNAL_LOSS` | `FIELD_OPS` | `PHYSICAL_LINE_FAULT` |
| `BACKBONE_CAPACITY` | `NETWORK_ENGINEERING` | `NETWORK_CAPACITY` |
| `CONFIGURATION_DRIFT` | `TIER2_SUPPORT` | (resolves in train; team if escalated) |
| `VOICE_PROFILE_STALE` | `TIER2_SUPPORT` | (resolves in train; team if escalated) |
| `PROVISIONING_STALE` | `TIER2_SUPPORT` [inferred] | `PROVISIONING_STALE` |
| `GENERATED_NOISE` | `TIER2_SUPPORT` [inferred] (default for noise-escalated) | — |

Account-state → team (not from diagnostics):
- account `Suspended` (overdue) => `ACCOUNTS_PAYABLE` (route INELIGIBLE_ACCOUNT, status PENDING_ACTION)
- auth failure => `NONE` (customer-side recovery)
- active outage => `NONE`

If a ticket has multiple root causes, the most severe physical/network cause wins (FIBER/SIGNAL > BACKBONE > others).

### 1.5 Per-ticket decision fields

train_001 `ticket_decisions` entry:
- `ticket_id`, `account_id` (preserve payload order)
- `final_resolution_status`: RESOLVED | PENDING_ACTION | ESCALATED | FAILED
- `diagnostic_needed`: true only when diagnostics actually ran (gate 5); false for all gates
- `latency_issue`, `stability_issue`, `bandwidth_issue`: PRE-troubleshooting violations (false if not diagnosed)
- `outage_id`: the matching outage_id for OUTAGE_WAIT; **empty string** otherwise
- `escalation_team`: NONE | TIER2_SUPPORT | FIELD_OPS | NETWORK_ENGINEERING | ACCOUNTS_PAYABLE
- `resolution_route`: AUTO_TROUBLESHOOTING | OUTAGE_WAIT | ESCALATION | INELIGIBLE_ACCOUNT | AUTH_FAILED | INVALID_ACCOUNT

train_004 `ticket_decisions` entry:
- `final_resolution_status`, `route_team` (same enum as escalation_team), `key_blocker` (NONE | ACTIVE_OUTAGE | INVALID_ACCOUNT | AUTH_FAILED | OVERDUE_SUSPENSION | FRAUD_SUSPENSION | NETWORK_CAPACITY | PROVISIONING_STALE | PHYSICAL_LINE_FAULT), `diagnostic_required` (same as diagnostic_needed)

### 1.6 Status assignment summary

| Route | status | team |
|---|---|---|
| INVALID_ACCOUNT | FAILED | NONE |
| INELIGIBLE_ACCOUNT (overdue) | PENDING_ACTION | ACCOUNTS_PAYABLE |
| AUTH_FAILED | PENDING_ACTION | NONE |
| OUTAGE_WAIT | PENDING_ACTION | NONE |
| AUTO_TROUBLESHOOTING (all post clear) | RESOLVED | NONE |
| ESCALATION (any post fails) | ESCALATED | root-cause map |

### 1.7 Batch / queue summary fields

train_001 `batch_summary`:
- `RESOLVED`, `PENDING_ACTION`, `ESCALATED`, `FAILED` = counts of each status
- `tickets_requiring_customer_wait` = count of `OUTAGE_WAIT`-routed tickets (customers waiting on service restoration). [inferred: distinct from PENDING_ACTION count; counts only outage waits]

train_004 `queue_summary`:
- `FAILED`, `PENDING_ACTION`, `RESOLVED`, `ESCALATED` = status counts
- `TIER2_SUPPORT`, `FIELD_OPS`, `NETWORK_ENGINEERING`, `ACCOUNTS_PAYABLE` = counts of tickets assigned to each team (route_team). Tickets with route_team NONE are not counted in any team bucket.

### 1.8 Reference: train ticket outcomes (verified against API)

| ticket | account | type | gate | route | status | team | root cause |
|---|---|---|---|---|---|---|---|
| TCK-5107 | ACC-5107 Active/SUCC | internet | diag | AUTO_TROUBLESHOOTING | RESOLVED | NONE | CONFIGURATION_DRIFT |
| TCK-5131 | ACC-5131 Active/SUCC | video | OUTAGE (OUT-9102 SA-31 video) | OUTAGE_WAIT | PENDING_ACTION | NONE | (no diag) |
| TCK-5184 | ACC-5184 Active/SUCC | internet | diag | ESCALATION | ESCALATED | FIELD_OPS | FIBER_DROP_DAMAGE+SIGNAL_LOSS |
| TCK-5202 | ACC-5202 Suspended | internet | eligible-fail | INELIGIBLE_ACCOUNT | PENDING_ACTION | ACCOUNTS_PAYABLE | (no diag) |
| TCK-5401 | ACC-5401 Active/SUCC | internet | OUTAGE (OUT-9401 SA-61) | OUTAGE_WAIT | PENDING_ACTION | NONE | (no diag) |
| TCK-5402 | ACC-5402 Active/SUCC | voice | diag | AUTO_TROUBLESHOOTING | RESOLVED | NONE | VOICE_PROFILE_STALE |
| TCK-5403 | BAD-5403 missing | internet | invalid | INVALID_ACCOUNT | FAILED | NONE | (no diag) |
| TCK-5404 | ACC-5404 Active/FAILURE | video | auth-fail | AUTH_FAILED | PENDING_ACTION | NONE | (no diag) |
| TCK-5405 | ACC-5405 Suspended | internet | eligible-fail | INELIGIBLE_ACCOUNT | PENDING_ACTION | ACCOUNTS_PAYABLE | (no diag) |
| TCK-5406 | ACC-5406 Active/SUCC | internet | diag | ESCALATION | ESCALATED | NETWORK_ENGINEERING | BACKBONE_CAPACITY |
| TCK-5407 | ACC-5407 Active/SUCC | video | diag | ESCALATION | ESCALATED | TIER2_SUPPORT | PROVISIONING_STALE |

---

## 2. AUDIT MATH DEFINITIONS (ticket family)

These are the precise computation definitions for any audit/summary fields a task may request (used by queue-quality variants). "Diagnosed tickets" = tickets that reached gate 5 (gated tickets are excluded from diagnostic aggregations).

- `diagnostic_records_skipped_by_gate` = count of tickets NOT diagnosed = tickets stopped at gate 1–4 (invalid account + suspended + auth-failed + active-outage). Equals `total_tickets − diagnosed_count`.

- `pre_troubleshooting_bandwidth_gap_total` = Σ over **diagnosed** tickets of `max(0, bandwidth_floor − pre_bandwidth_mbps)`, where `bandwidth_floor = 0.90 × subscribed_mbps`. (Sum of pre-troubleshooting bandwidth shortfalls; only positive shortfalls counted.)

- `post_troubleshooting_remaining_issue_flags` = Σ over **diagnosed** tickets of the count of POST issue flags still true (`latency_issue_post + stability_issue_post + bandwidth_issue_post`). Each ticket contributes 0–3. (Gated tickets contribute 0; they were never diagnosed.)

- `post_threshold_excess_totals` = over **diagnosed** tickets, sum the post-violation excesses, reported as three components:
  - `latency_excess_ms` = Σ max(0, post_latency_ms − 100)
  - `jitter_excess_ms` = Σ max(0, post_jitter_ms − 30)
  - `bandwidth_shortfall_mbps` = Σ max(0, bandwidth_floor − post_bandwidth_mbps)
  (Only tickets still violating post-troubleshooting contribute; resolved tickets contribute 0 to each.)

- `per-ticket floor/shortfall list` = for each diagnosed ticket: `{ticket_id, service_type, subscribed_mbps, bandwidth_floor, pre_bandwidth_mbps, pre_shortfall = max(0, floor − pre_bw), post_bandwidth_mbps, post_shortfall = max(0, floor − post_bw)}`.

- `success_ids` = diagnosed tickets whose POST issues ALL cleared (RESOLVED via auto-troubleshooting).
- `failure_ids` = diagnosed tickets with any POST issue remaining (ESCALATED). (Gated tickets are in neither; they are "skipped".)

- `root-cause → escalation grouping` = bucket `failure_ids` by their diagnostic root_cause(s) and the mapped escalation_team. Output e.g. `{FIELD_OPS: [TCK-5184, TCK-6105], NETWORK_ENGINEERING: [TCK-5406, TCK-6104], TIER2_SUPPORT: [TCK-5407]}`. When a ticket has multiple root causes, assign it to the team of the most severe cause (FIBER/SIGNAL > BACKBONE > config/provisioning > noise).

---

## 3. MOBILE TRIAGE FAMILY — decision tree (train_002, train_005)

For each case, load: case (`/api/cases`), customer, line (`/api/lines`), plan (`/api/plans`), bill (`/api/bills`), device (`/api/devices`). Decide primary_action, secondary_action, and route. The `issue_type` and `customer_location` are hints; the **device/line signals are authoritative**.

### 3.1 Decision precedence (first match wins)

```
A. LINE SUSPENDED (line.status == "Suspended")
   - suspension_reason == "OVERDUE_BILL"  (or bill.status == "Overdue"):
       primary   = SEND_PAYMENT_REQUEST
       secondary = RESUME_LINE_REBOOT
       route     = BILLING_RECOVERY
       bill_id   = the Overdue bill_id, charge_amount_usd = bill.amount_due_usd
   - suspension_reason == "CONTRACT_ENDED" (contract_end_date in past):
       primary = TRANSFER_HUMAN, route = HUMAN_TRANSFER        [inferred]
   - other suspension:
       primary = TRANSFER_HUMAN, route = HUMAN_TRANSFER

B. SIM / device hardware (line Active)
   - device.sim_status == "missing":
       primary = RESEAT_SIM, secondary = NO_ACTION, route = SELF_SERVICE
   - device.sim_status == "locked_pin" (SIM locked):
       primary = TRANSFER_HUMAN, route = HUMAN_TRANSFER        [inferred]

C. ROAMING — only when customer_location == "abroad" (issue involves mobile data)
   - line.roaming_enabled == false:
       primary = ENABLE_LINE_ROAMING, route = CARRIER_UPDATE,
       carrier_update_required = true, secondary = NO_ACTION
   - else device.phone_roaming_enabled == false:
       primary = TOGGLE_ROAMING, route = SELF_SERVICE,         [inferred route]
       carrier_update_required = false, secondary = NO_ACTION

D. DATA CAP EXCEEDED (line.data_used_gb > plan.data_limit_gb)
       primary   = REFUEL_DATA
       route     = DATA_RECOVERY
       data_refuel_gb = customer preference accepted_refuel_gb
                        (else the overage amount, else a default)
       charge_amount_usd = round(data_refuel_gb × plan.data_refueling_price_per_gb, 2)
       carrier_update_required = false, secondary = NO_ACTION

E. SLOW / NO DATA — device settings (issue_type SLOW_DATA or MOBILE_DATA)
   - device.data_saver_mode == true:
       primary = TOGGLE_DATA_SAVER, route = DEVICE_SETTING_FIX
   - else device.network_mode_preference in {3g_only, 2g_only, lte_only} (legacy):
       primary = SET_NETWORK_MODE, route = DEVICE_SETTING_FIX
   - else device.mobile_data_enabled == false:
       primary = TOGGLE_MOBILE_DATA, route = DEVICE_SETTING_FIX
   - else device.vpn_connected == true:
       primary = DISCONNECT_VPN, route = SELF_SERVICE   (train_002) / DEVICE_SETTING_FIX (train_005)
   - else device.airplane_mode == true:
       primary = TOGGLE_AIRPLANE_MODE, route = SELF_SERVICE        [inferred]

F. MMS (issue_type MMS, device.can_send_mms == false)
   - messaging_permissions.storage == false AND sms == false:
       primary = GRANT_MESSAGING_PERMISSION, permission = sms_and_storage
   - messaging_permissions.storage == false:
       primary = GRANT_MESSAGING_PERMISSION, permission = storage
   - messaging_permissions.sms == false:
       primary = GRANT_MESSAGING_PERMISSION, permission = sms
   - mmsc_url_present == false:
       primary = RESET_APN_REBOOT, route = SELF_SERVICE
   - else: TRANSFER_HUMAN

G. DEFAULT: primary = TRANSFER_HUMAN, route = HUMAN_TRANSFER
```

### 3.2 Enum maps between the two task variants

| concept | train_002 enum | train_005 enum |
|---|---|---|
| reseat SIM | RESEAT_SIM | (not listed; use TRANSFER_HUMAN if absent) |
| toggle phone roaming | TOGGLE_ROAMING | TOGGLE_ROAMING |
| enable line/carrier roaming | ENABLE_LINE_ROAMING | ENABLE_LINE_ROAMING |
| data top-up | REFUEL_DATA | REFUEL_DATA |
| data saver off | TOGGLE_DATA_SAVER | TOGGLE_DATA_SAVER |
| network mode | SET_NETWORK_MODE | SET_NETWORK_MODE |
| mobile data on | TOGGLE_MOBILE_DATA | TOGGLE_MOBILE_DATA |
| vpn off | DISCONNECT_VPN | DISCONNECT_VPN |
| grant perm | GRANT_MESSAGING_PERMISSION | (not listed; TRANSFER_HUMAN) |
| payment | SEND_PAYMENT_REQUEST / RESUME_LINE_REBOOT | (not listed) |
| apn reset | RESET_APN_REBOOT | (not listed) |
| airplane | TOGGLE_AIRPLANE_MODE | (not listed) |
| wifi calling | TOGGLE_WIFI_CALLING | (not listed) |
| human | TRANSFER_HUMAN | TRANSFER_HUMAN |
| none | NO_ACTION | NO_ACTION |

### 3.3 Route maps

train_002 `final_route` (SELF_SERVICE | BILLING_RECOVERY | CARRIER_UPDATE | HUMAN_TRANSFER):
- RESEAT_SIM, TOGGLE_ROAMING, GRANT_MESSAGING_PERMISSION, DISCONNECT_VPN, TOGGLE_AIRPLANE_MODE, RESET_APN_REBOOT, TOGGLE_WIFI_CALLING → SELF_SERVICE
- SEND_PAYMENT_REQUEST (+RESUME_LINE_REBOOT) → BILLING_RECOVERY
- ENABLE_LINE_ROAMING → CARRIER_UPDATE
- TRANSFER_HUMAN → HUMAN_TRANSFER

train_005 `final_route` (DATA_RECOVERY | CARRIER_UPDATE | DEVICE_SETTING_FIX | HUMAN_TRANSFER):
- REFUEL_DATA → DATA_RECOVERY
- ENABLE_LINE_ROAMING → CARRIER_UPDATE
- TOGGLE_DATA_SAVER, SET_NETWORK_MODE, TOGGLE_MOBILE_DATA, DISCONNECT_VPN, TOGGLE_ROAMING(if device-side) → DEVICE_SETTING_FIX
- TRANSFER_HUMAN → HUMAN_TRANSFER

### 3.4 Output field specifics

train_002 `case_decisions`: case_id, customer_id, line_id, primary_action, secondary_action, permission (NONE|sms|storage|sms_and_storage), bill_id (empty when not applicable), charge_amount_usd (2 decimals), final_route. `queue_summary`: self_service_fixes, billing_recoveries, carrier_updates, human_transfers.

train_005 `case_decisions`: case_id, primary_action, secondary_action, data_refuel_gb (1 decimal, 0.0 when N/A), charge_amount_usd (2 decimals), carrier_update_required (bool), final_route. `worklist_summary`: data_refuel_cases, carrier_updates, device_setting_fixes, human_transfers, total_estimated_customer_charge_usd (2 decimals = Σ charges).

### 3.5 Reference: train mobile outcomes (verified)

train_002 (CASE-2101..2105):
| case | signal | primary | secondary | permission | bill_id | charge | route |
|---|---|---|---|---|---|---|---|
| CASE-2101 | sim missing | RESEAT_SIM | NO_ACTION | NONE | "" | 0.00 | SELF_SERVICE |
| CASE-2102 | line Suspended OVERDUE_BILL, bill 86.40 Overdue | SEND_PAYMENT_REQUEST | RESUME_LINE_REBOOT | NONE | BILL-2102 | 86.40 | BILLING_RECOVERY |
| CASE-2103 | abroad, phone_roaming false, line roaming true | TOGGLE_ROAMING | NO_ACTION | NONE | "" | 0.00 | SELF_SERVICE |
| CASE-2104 | can_send_mms false, storage false | GRANT_MESSAGING_PERMISSION | NO_ACTION | storage | "" | 0.00 | SELF_SERVICE |
| CASE-2105 | vpn connected, speed poor | DISCONNECT_VPN | NO_ACTION | NONE | "" | 0.00 | SELF_SERVICE |

queue_summary: self_service_fixes=4, billing_recoveries=1, carrier_updates=0, human_transfers=0.

train_005 (CASE-2501..2505):
| case | signal | primary | secondary | refuel_gb | charge | carrier_update | route |
|---|---|---|---|---|---|---|---|
| CASE-2501 | data_used 16.2 > 15 cap, pref 2.0gb, PREMIUM $2/gb | REFUEL_DATA | NO_ACTION | 2.0 | 4.00 | false | DATA_RECOVERY |
| CASE-2502 | abroad, line roaming false, phone roaming true | ENABLE_LINE_ROAMING | NO_ACTION | 0.0 | 0.00 | true | CARRIER_UPDATE |
| CASE-2503 | data_saver true, speed fair | TOGGLE_DATA_SAVER | NO_ACTION | 0.0 | 0.00 | false | DEVICE_SETTING_FIX |
| CASE-2504 | network_mode 3g_only, speed poor | SET_NETWORK_MODE | NO_ACTION | 0.0 | 0.00 | false | DEVICE_SETTING_FIX |
| CASE-2505 | mobile_data_enabled false | TOGGLE_MOBILE_DATA | NO_ACTION | 0.0 | 0.00 | false | DEVICE_SETTING_FIX |

worklist_summary: data_refuel_cases=1, carrier_updates=1, device_setting_fixes=3, human_transfers=0, total_estimated_customer_charge_usd=4.00.

---

## 4. KEY DISCRIMINATORS & PITFALLS (mobile)

- **TOGGLE_ROAMING vs ENABLE_LINE_ROAMING:** TOGGLE_ROAMING fixes the *device* setting (`device.phone_roaming_enabled == false`) while the *line* already has `line.roaming_enabled == true`. ENABLE_LINE_ROAMING fixes the *carrier/line* side (`line.roaming_enabled == false`). Both are abroad-data cases; check `line.roaming_enabled` FIRST, then `device.phone_roaming_enabled`.
- **REFUEL_DATA charge:** use `plan.data_refueling_price_per_gb` (PREMIUM=2.0, BASIC=5.0, PLUS=0.1, FAMILY=3.0, generated plans vary). Multiply by the refuel GB (from `customer_preferences.accepted_refuel_gb` when present). Round to 2 decimals.
- **MMS granularity:** storage-only missing → permission `storage`; sms-only → `sms`; both → `sms_and_storage`; APN/MMSC url missing (`mmsc_url_present==false`) → `RESET_APN_REBOOT`, not a permission grant.
- **Data cap check uses `line.data_used_gb > plan.data_limit_gb`** (strictly greater). PLAN-PLUS data_limit 999 effectively unlimited.
- **Suspended line ≠ eligible for device fixes.** Always check `line.status` first; a suspended line never reaches device-setting branches.
- **train_005 has no bill_id/permission fields**; train_002 has no data_refuel_gb/carrier_update_required fields. Emit only the fields each template defines.
- **secondary_action** is `NO_ACTION` for single-step fixes; the only multi-step train case is SEND_PAYMENT_REQUEST → RESUME_LINE_REBOOT.

---

## 5. ENTERPRISE EXPORT-COMPLAINT FAMILY (train_003)

Build a structured response package from the complaint email + `/api/enterprise/*` evidence.

### 5.1 Procedure

1. From complaint email: client name, product, approximate incident_id (e.g. INC-7301).
2. `GET /api/enterprise/accounts` → match client name → `enterprise_account_id`, `account_owner`, `finance_owner`, `tier`.
3. `GET /api/enterprise/incidents/{incident_id}` → `severity`, `engineering_owner`, `account_owner`, `product`, `status`, `received_at`, `summary`.
4. `GET /api/enterprise/export-runs` → filter by `incident_id`. Separate FAILED runs from SUCCEEDED.
5. **Failure window** = the consecutive FAILED run_dates. `start_date` = first failed date, `end_date` = last failed date, `failed_days` = count of FAILED runs in the window. (Verify they are consecutive.)
6. **backfill_days** = `failed_days` (each failed export day must be re-run/backfilled). [inferred: equals the number of failed days]
7. **root_cause_category** = the `failure_code` shared by the failed runs (e.g. `STALE_CREDENTIAL`, `STAGING_STORAGE_QUOTA`, `RATE_LIMIT`, `TIMEOUT`). Express as a concise category string (use the failure_code value, upper-snake to readable form).
8. **contributing_alert_issue** = `NONE` when no alert evidence exists in the email/runs; `ARCHIVED_ALERT_ROUTE` if evidence shows an alert was mis-routed to an archived channel; `UNKNOWN` if uncertain. [inferred: default NONE]
9. **sla_credit_percent** = derived table below.
10. **owners**: `engineering_owner` and `account_owner` from the incident record.
11. **channel_name / evidence_folder / report_title / share_permissions** = naming conventions below.
12. **response_status** = see below.

### 5.2 SLA credit table [inferred — endpoints return empty]

`sla_credit_percent = min(cap, per_day × failed_days)`:

| severity | per_day | cap |
|---|---|---|
| Critical | 10% | 50% |
| High | 10% | 40% |
| Medium | 5% | 25% |
| Low | 5% | 15% |

> For INC-7301 (Critical, 3 failed days) → min(50, 10×3) = **30%**. The `/api/enterprise/sla/*` endpoints return `{}`, so the credit is computed, not fetched.

### 5.3 Naming conventions [inferred]

- `channel_name` = client name lowercased, spaces→hyphens, drop trailing "Inc."/"Group"/etc. Asteri Retail Inc. → `asteri-retail`.
- `evidence_folder` = `{client-slug}-{failure_window_end_date}-investigation`. e.g. `asteri-retail-2026-05-14-investigation`.
- `report_title` = `{Client Display Name} Export Failure Report`. e.g. `Asteri Retail Export Failure Report`.
- `share_permissions` = one entry per user in `permission_users_to_include` (from response_requirements), **in the order listed**. Each entry `{user, permission}` where permission ∈ {view, edit, upload_only}. Assign `edit` to the finance_owner (reviews SLA credit) and `view` to the other listed user. [inferred role assignment]

### 5.4 response_status [inferred]

- `NEEDS_FINANCE_REVIEW` when the package includes a non-zero SLA credit (finance sign-off required). — default for Critical monthly_export export failures.
- `NEEDS_ENGINEERING_REVIEW` when root cause is unresolved / engineering action pending and no SLA credit.
- `READY_TO_SEND` when all evidence complete and no review block.
- `UNDER_INVESTIGATION` when incident.status is UNDER_INVESTIGATION and evidence is incomplete.

For INC-7301 → `NEEDS_FINANCE_REVIEW` (SLA credit 30% involved). [inferred]

### 5.5 Reference: INC-7301 verified package

- incident_id: INC-7301
- enterprise_account_id: ENT-3001 (Asteri Retail Inc., Enterprise tier)
- root_cause_category: STALE_CREDENTIAL (all 3 failed runs share failure_code STALE_CREDENTIAL)
- contributing_alert_issue: NONE [inferred]
- failure_window: start 2026-05-12, end 2026-05-14, failed_days 3 (RUN-AST-0/1/2 FAILED; RUN-AST-3 on 2026-05-15 SUCCEEDED with 124803 records)
- backfill_days: 3
- sla_credit_percent: 30 [inferred]
- severity: Critical
- engineering_owner: delana.rao
- account_owner: stephany.lo
- channel_name: asteri-retail [inferred]
- evidence_folder: asteri-retail-2026-05-14-investigation [inferred]
- report_title: Asteri Retail Export Failure Report [inferred]
- share_permissions: [{user: laura.brown, permission: edit}, {user: jun.chen, permission: view}] [inferred roles; laura.brown = finance_owner of ENT-3001; jun.chen not in API — treat as listed response contact]
- response_status: NEEDS_FINANCE_REVIEW [inferred]

### 5.6 Pitfalls (enterprise)

- `failure_code` on SUCCEEDED runs is `""` (empty) — ignore it; use FAILED runs to derive root cause.
- `exported_record_count` on FAILED runs is 0; the SUCCEEDED run's count is the recovered volume, not the failure.
- Use the **incident_id from the complaint** (INC-7301), not the enterprise_account_id, to filter export-runs. Multiple incidents can share an account.
- `failed_days` counts FAILED runs in the consecutive window, not all runs for the incident (some runs for the same incident on other dates may be SUCCEEDED).
- `permission_users_to_include` ordering must be preserved exactly as given in `response_requirements.json`.
- The dashboard_refresh product (INC-8402) has NO export runs — failure_window would be empty/zero; only monthly_export-style products produce export-run windows.

---

## 6. GENERAL EXECUTION RULES

1. **Always use the harness-provided base URL** for the API; the prompt's `127.0.0.1:8057` is a placeholder.
2. **Fetch supporting records per item** (account/line/device/etc.) — never assume values from the ticket/case text alone.
3. **Preserve payload order** for ticket_decisions/case_decisions; preserve `permission_users_to_include` order for share_permissions.
4. **Return only JSON** matching the answer_template exactly — no extra fields, no prose. Use empty string `""` for non-applicable string fields (e.g. outage_id) and 0.00 / 0.0 for non-applicable numeric fields.
5. **Booleans**: diagnostic_needed/diagnostic_required false for any gated ticket; carrier_update_required true only for ENABLE_LINE_ROAMING.
6. **Rounding**: charge_amount_usd → 2 decimals; data_refuel_gb → 1 decimal; sla_credit_percent → integer.
7. **Don't read diagnostic records for outage-wait tickets** — the API returns them, but the gate says skip.
8. **Threshold recap (commit to these):** latency > 100 ms → latency_issue; jitter > 30 ms → stability_issue; bandwidth < 0.90 × subscribed_mbps → bandwidth_issue; RESOLVED iff post-troubleshooting all three clear.
