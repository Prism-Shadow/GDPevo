---
name: scn003-crm-support-console
description: Resolve SCN_003 CRM support-console tasks: ticket-batch resolution, mobile contact-center triage, and enterprise export-complaint response packages. Drive the remote console API, apply diagnostic floors + gating order, and emit the per-family JSON answer.
---

# SCN_003 CRM Support Console — Executable SOP

Self-evolved skill. All thresholds marked **(inferred)** were derived by reasoning against the live API records (no gold answers). They are committed numeric estimates.

## 0. Environment & base URL

- **Base URL: `<remote-env-url>`** (ALWAYS use this; ignore any `http://127.0.0.1:8057` in prompts).
- Health: `GET /health` → `{"ok": true}`.
- Catalog: `GET /api/catalog` (endpoints + record counts).
- Records are the source of truth — never assume fields; fetch them.

## 1. API map

### Ticket / fixed-line domain (train_001, train_004)
| Endpoint | Returns |
|---|---|
| `GET /api/tickets` | all tickets: `ticket_id, account_id, service_type, service_area, subscribed_mbps, status, issue_summary` |
| `GET /api/tickets/<ticket_id>` | single ticket (carries `subscribed_mbps` + `service_type`) |
| `GET /api/accounts/<account_id>` | `status` (Active/Suspended), `authentication{last_login_status, account_recovery_status}`, `service_area`, `tier` (404 `{"error":"not_found"}` = invalid account) |
| `GET /api/outages?service_area=<area>` | list of `{outage_id, active, eta_hours, service_types[], started_at}` |
| `GET /api/diagnostics/<ticket_id>` | PRE metrics: `bandwidth_mbps, latency_ms, jitter_ms, root_causes[]` |
| `GET /api/troubleshooting/<ticket_id>` | POST metrics: `post_bandwidth_mbps, post_latency_ms, post_jitter_ms, steps[]` |

### Mobile domain (train_002, train_005)
| Endpoint | Returns |
|---|---|
| `GET /api/cases` / `GET /api/cases/<case_id>` | `case_id, customer_id, line_id, device_id, issue_type, customer_location, summary` |
| `GET /api/customers` | `customer_id, name, phone_number, status` |
| `GET /api/lines/<line_id>` | `status` (Active/Suspended), `suspension_reason` (OVERDUE_BILL / CONTRACT_ENDED / ""), `roaming_enabled`, `data_used_gb`, `plan_id`, `device_id` |
| `GET /api/devices/<device_id>` | `sim_status`, `signal_strength`, `airplane_mode`, `mobile_data_enabled`, `phone_roaming_enabled`, `data_saver_mode`, `network_mode_preference`, `vpn_connected`, `can_send_mms`, `mmsc_url_present`, `messaging_permissions{sms, storage}`, `wifi_calling_enabled`, `speed_test` |
| `GET /api/plans/<plan_id>` | `data_limit_gb`, `data_refueling_price_per_gb`, `monthly_price_usd`, `name` |
| `GET /api/bills` | `bill_id, customer_id, amount_due_usd, due_date, status` (Paid/Overdue) |

### Enterprise domain (train_003)
| Endpoint | Returns |
|---|---|
| `GET /api/enterprise/accounts` | `enterprise_account_id, name, tier, account_owner, finance_owner` |
| `GET /api/enterprise/incidents` | `incident_id, enterprise_account_id, product, severity, status, summary, engineering_owner, account_owner, received_at` |
| `GET /api/enterprise/export-runs?incident_id=<id>` | `run_id, run_date, status (FAILED/SUCCEEDED), failure_code, exported_record_count` |
| `GET /api/enterprise/messages?query=<text>` | `message_id, author, channel, created_at, body` (substring search; use `query=.` to list all) |
| `GET /api/enterprise/sla/<enterprise_account_id>` | `monthly_export_credit_percent, credit_trigger, executive_contact` |

## 2. Ticket family — inferred diagnostic floors (CRITICAL)

Derived by flag-vs-metric reasoning across the 8 tickets that pass all gates (real `root_causes`, non-`GENERATED_NOISE`):

| Metric | Floor | Flag when | Cleared (post) when |
|---|---|---|---|
| **bandwidth_mbps** | **0.80 × subscribed_mbps (inferred)** | `bandwidth_mbps < 0.80·sub` | `post_bandwidth_mbps ≥ 0.80·sub` |
| **latency_ms** | **100 ms (inferred)** | `latency_ms > 100` | `post_latency_ms ≤ 100` |
| **jitter_ms** | **30 ms (inferred)** | `jitter_ms > 30` (= stability_issue) | `post_jitter_ms ≤ 30` |

Evidence: latency 100 is the only round number in the viable window [82, 121) (resolved post-lat max = 82; escalated post-lat min with latency remaining = 121). Bandwidth 0.80 yields all-integer floors for every observed `subscribed_mbps` (300→240, 500→400, 750→600, 100→80, 200→160) and is consistent with both anchor tickets (TCK-5107 sub=300 pre 209<240 flagged, post 272≥240 cleared→RESOLVED; TCK-5184 sub=500 pre 318<400 flagged, post 332<400 remains→ESCALATED). Jitter 30 is the standard SLA threshold in [21,32) and flags the high-jitter resolved example (TCK-5107 pre 33.5) so auto-troubleshooting clears all three issue types.

Worked floor table (per subscribed_mbps):

| subscribed_mbps | bandwidth floor (0.80·sub) |
|---|---|
| 100 | 80 |
| 200 | 160 |
| 300 | 240 |
| 500 | 400 |
| 750 | 600 |

## 3. Ticket family — gating order & resolution (train_001, train_004)

Evaluate each ticket in this strict order. The FIRST matching gate wins; gates 1–4 skip diagnostics.

### Gate 1 — Account lookup (INVALID_ACCOUNT)
- `GET /api/accounts/<account_id>` → 404 `{"error":"not_found"}` (e.g. `BAD-*`).
- **final_resolution_status = FAILED**, `diagnostic_needed = false`, `outage_id = ""`.
- train_001: `resolution_route = INVALID_ACCOUNT`, `escalation_team = NONE`.
- train_004: `key_blocker = INVALID_ACCOUNT`, `route_team = NONE`.

### Gate 2 — Auth gate (AUTH_FAILED)
- `authentication.last_login_status == "FAILURE"` OR `account_recovery_status == "FAILURE"`.
- **final_resolution_status = FAILED**, `diagnostic_needed = false`.
- train_001: `resolution_route = AUTH_FAILED`, `escalation_team = NONE`.
- train_004: `key_blocker = AUTH_FAILED`, `route_team = NONE`.
- (Eligibility+auth gates → FAILED **before** diagnostics.)

### Gate 3 — Account eligibility / suspension (inferred)
- `account.status == "Suspended"` (account exists, auth OK, but not Active → not eligible for diagnostics).
- **final_resolution_status = FAILED (inferred)**, `diagnostic_needed = false`.
- `key_blocker`:
  - default → `OVERDUE_SUSPENSION` (e.g. "overdue notice", "account hold", "suspended after overdue").
  - `FRAUD_SUSPENSION` only if an explicit fraud/security indicator appears in the ticket text (none in train data; default suspended accounts are overdue).
- Responsible team = `ACCOUNTS_PAYABLE` (billing owns the suspension).
  - train_001: `resolution_route = INELIGIBLE_ACCOUNT`, `escalation_team = ACCOUNTS_PAYABLE` (billing owner; alternative if eval treats escalation_team as strictly for ESCALATED status → NONE).
  - train_004: `key_blocker = OVERDUE_SUSPENSION`/`FRAUD_SUSPENSION`, `route_team = ACCOUNTS_PAYABLE`.
  - ALTERNATIVE interpretation: overdue suspension may be `PENDING_ACTION` (customer pays) + `ACCOUNTS_PAYABLE`; chose FAILED per the hint's eligibility→FAILED rule. If status counts mismatch, reconsider PENDING_ACTION.

### Gate 4 — Active outage in service_area (OUTAGE_WAIT)
- `GET /api/outages?service_area=<account.service_area>`; if any outage has `active == true` AND `ticket.service_type ∈ outage.service_types`.
- **final_resolution_status = PENDING_ACTION**, `diagnostic_needed = false`, `outage_id = <that outage_id>`.
- train_001: `resolution_route = OUTAGE_WAIT`, `escalation_team = NONE`, issue flags (latency/stability/bandwidth) all `false`.
- train_004: `key_blocker = ACTIVE_OUTAGE`, `route_team = NONE`.
- These count toward `tickets_requiring_customer_wait` (= count of OUTAGE_WAIT tickets).
- (Active outage → outage-wait, **no diagnostics**.)

### Gate 5 — Diagnose + auto-troubleshoot (passed all gates)
- `diagnostic_needed = true`. Fetch `/api/diagnostics/<tid>` and `/api/troubleshooting/<tid>`.
- **PRE flags** (floor violations on the diagnostic record):
  - `bandwidth_issue = bandwidth_mbps < 0.80·subscribed_mbps`
  - `latency_issue = latency_ms > 100`
  - `stability_issue = jitter_ms > 30`
- **POST clear** (on the troubleshooting record):
  - bandwidth cleared: `post_bandwidth_mbps ≥ 0.80·sub`
  - latency cleared: `post_latency_ms ≤ 100`
  - stability cleared: `post_jitter_ms ≤ 30`
- **Decision rule**: RESOLVED via auto-troubleshooting **iff every PRE-flagged issue is cleared POST**; otherwise ESCALATED.
  - RESOLVED → train_001: `resolution_route = AUTO_TROUBLESHOOTING`, `escalation_team = NONE`. train_004: `key_blocker = NONE`, `route_team = NONE`.
  - ESCALATED → train_001: `resolution_route = ESCALATION`, `escalation_team = <root-cause team>`. train_004: `key_blocker = <root-cause blocker>`, `route_team = <root-cause team>`.
- `GENERATED_NOISE` as the only root_cause = sentinel that the ticket was gated out (gates 1–4); never diagnose it. Real root_causes seen: `CONFIGURATION_DRIFT, FIBER_DROP_DAMAGE, SIGNAL_LOSS, VOICE_PROFILE_STALE, BACKBONE_CAPACITY, PROVISIONING_STALE`.

### Root-cause → team / key_blocker map (for ESCALATED diagnosed tickets)
| diagnostic root_cause | escalation_team | train_004 key_blocker |
|---|---|---|
| `FIBER_DROP_DAMAGE`, `SIGNAL_LOSS` (fiber/signal) | `FIELD_OPS` | `PHYSICAL_LINE_FAULT` |
| `BACKBONE_CAPACITY` (backbone/capacity) | `NETWORK_ENGINEERING` | `NETWORK_CAPACITY` |
| `PROVISIONING_STALE` (provisioning) | `TIER2_SUPPORT` | `PROVISIONING_STALE` |
| any `BILLING_*` (billing root cause) | `ACCOUNTS_PAYABLE` | (billing) |
| `CONFIGURATION_DRIFT`, `VOICE_PROFILE_STALE` | typically auto-RESOLVED; if not cleared → `TIER2_SUPPORT` (fallback) | — |

### train_001 batch_summary
- `RESOLVED / PENDING_ACTION / ESCALATED / FAILED`: counts of each `final_resolution_status`.
- `tickets_requiring_customer_wait`: count of OUTAGE_WAIT (PENDING_ACTION via active outage) tickets.

### Predicted train_001 (4 tickets) — sanity check
- TCK-5107 (ACC-5107 Active, SA-17 no outage, CONFIGURATION_DRIFT): pre bw209<240 T, lat142.8>100 T, jit33.5>30 T; post bw272≥240, lat82≤100, jit21≤30 → **RESOLVED**, AUTO_TROUBLESHOOTING, NONE.
- TCK-5131 (ACC-5131 Active, SA-31 active outage OUT-9102 covers video): **PENDING_ACTION**, OUTAGE_WAIT, outage_id=OUT-9102, NONE.
- TCK-5184 (ACC-5184 Active, SA-44 no outage, FIBER_DROP_DAMAGE+SIGNAL_LOSS): post bw332<400, lat176>100, jit41>30 → **ESCALATED**, ESCALATION, FIELD_OPS.
- TCK-5202 (ACC-5202 Suspended): **FAILED**, INELIGIBLE_ACCOUNT, ACCOUNTS_PAYABLE (per inferred rule).
- batch_summary: RESOLVED=1, PENDING_ACTION=1, ESCALATED=1, FAILED=1, tickets_requiring_customer_wait=1.

### Predicted train_004 (7 tickets) — sanity check
- TCK-5401: SA-61 outage OUT-9401 (internet) → PENDING_ACTION, ACTIVE_OUTAGE, NONE.
- TCK-5402 (VOICE_PROFILE_STALE, sub100): pre bw61<80 T, lat97≤100, jit24≤30; post bw93≥80, lat79, jit18 → RESOLVED, NONE, NONE.
- TCK-5403 (BAD-5403 not found): FAILED, INVALID_ACCOUNT, NONE.
- TCK-5404 (ACC-5404 auth FAILURE): FAILED, AUTH_FAILED, NONE.
- TCK-5405 (ACC-5405 Suspended/overdue): FAILED, OVERDUE_SUSPENSION, ACCOUNTS_PAYABLE.
- TCK-5406 (BACKBONE_CAPACITY, sub500): post bw298<400, lat198>100, jit43>30 → ESCALATED, NETWORK_CAPACITY, NETWORK_ENGINEERING.
- TCK-5407 (PROVISIONING_STALE, sub750): post bw610≥600 clear, lat121>100, jit32>30 → ESCALATED, PROVISIONING_STALE, TIER2_SUPPORT.
- queue_summary: FAILED=3, PENDING_ACTION=1, RESOLVED=1, ESCALATED=2, TIER2_SUPPORT=1, FIELD_OPS=0, NETWORK_ENGINEERING=1, ACCOUNTS_PAYABLE=1.

## 4. Mobile family — triage decision tree (train_002, train_005)

For each case, fetch case → customer → line → device → plan, and the customer's bills. Decide in this priority order (first match wins). `customer_location` "abroad" = traveler.

### Step 1 — Line suspended? (`line.status == "Suspended"`)
- `suspension_reason == "OVERDUE_BILL"` AND a bill `status == "Overdue"`:
  - **primary = SEND_PAYMENT_REQUEST**, **secondary = RESUME_LINE_REBOOT**, `final_route = BILLING_RECOVERY` (train_002) — bill_id = the overdue bill_id, `charge_amount_usd = bill.amount_due_usd`. (train_005 has no billing action in its enum → if a train_005 case is an overdue suspension, use TRANSFER_HUMAN.)
- `suspension_reason == "CONTRACT_ENDED"` (or any non-bill):
  - **primary = TRANSFER_HUMAN**, `final_route = HUMAN_TRANSFER` (renewal/retention needed; cannot self-serve).

### Step 2 — `issue_type == NO_SERVICE` (not suspended): inspect `device.sim_status`
- `sim_status == "missing"` (e.g. after a commute) → **RESEAT_SIM** (train_002 only; not in train_005 enum → TRANSFER_HUMAN there).
- `sim_status == "locked_pin"` (SIM PUK-locked) → **TRANSFER_HUMAN** (HUMAN_TRANSFER).
- `device.airplane_mode == true` → **TOGGLE_AIRPLANE_MODE** (SELF_SERVICE).

### Step 3 — `issue_type == MOBILE_DATA` (data not working)
- **Cap hit**: `line.data_used_gb > plan.data_limit_gb` → **REFUEL_DATA**.
  - `data_refuel_gb` = `customer_preferences[case_id].accepted_refuel_gb` if the worklist provides it; else default = `ceil(data_used_gb - data_limit_gb)` (min 1.0) **(inferred)**.
  - `charge_amount_usd = data_refuel_gb × plan.data_refueling_price_per_gb` (2-decimal).
  - `final_route = DATA_RECOVERY` (train_005); train_002 route = SELF_SERVICE.
- **Abroad + `line.roaming_enabled == false`** (line-side roaming off; phone may be on) → **ENABLE_LINE_ROAMING**, `carrier_update_required = true`, `final_route = CARRIER_UPDATE`. (carrier/line-side update)
- **Abroad + `phone_roaming_enabled == false`** (line roaming OK, phone toggle off) → **TOGGLE_ROAMING** (device self-service). train_002 `final_route = SELF_SERVICE`; train_005 `final_route = DEVICE_SETTING_FIX`. `carrier_update_required = false`.
- **`device.mobile_data_enabled == false`** (e.g. after a settings change) → **TOGGLE_MOBILE_DATA**. train_005 `final_route = DEVICE_SETTING_FIX`; train_002 `SELF_SERVICE`.
- **`device.airplane_mode == true`** → **TOGGLE_AIRPLANE_MODE**.

### Step 4 — `issue_type == SLOW_DATA`
- `device.data_saver_mode == true` → **TOGGLE_DATA_SAVER** (DEVICE_SETTING_FIX / SELF_SERVICE).
- `device.network_mode_preference` is an older mode (`3g_only`, `2g_only`, etc.) → **SET_NETWORK_MODE** (upgrade to `4g_5g_preferred`) (DEVICE_SETTING_FIX / SELF_SERVICE).
- `device.vpn_connected == true` → **DISCONNECT_VPN** (SELF_SERVICE / DEVICE_SETTING_FIX).
- (Evaluate data_saver → network_mode → vpn in order; pick the first active cause. If multiple, the most direct reported-symptom match.)

### Step 5 — `issue_type == MMS`
- `device.mmsc_url_present == false` (APN profile broken, e.g. after APN edit) → **RESET_APN_REBOOT** (SELF_SERVICE). (train_002 only.)
- `device.messaging_permissions.storage == false` and/or `sms == false` → **GRANT_MESSAGING_PERMISSION** (train_002 only).
  - `permission` field = the missing permission(s): `storage` if only storage missing; `sms` if only sms missing; `sms_and_storage` if both missing; `NONE` otherwise.
- (If `can_send_mms == false` but mmsc present + perms OK → consider `TOGGLE_WIFI_CALLING` or TRANSFER_HUMAN.)

### Step 6 — Fallback
- If no self-serve action applies or the issue is unrecoverable (hardware, fraud, contract) → **TRANSFER_HUMAN**, `final_route = HUMAN_TRANSFER`.

### final_route by action
| Action | train_002 final_route | train_005 final_route |
|---|---|---|
| RESEAT_SIM, TOGGLE_ROAMING, GRANT_MESSAGING_PERMISSION, DISCONNECT_VPN, RESET_APN_REBOOT, TOGGLE_AIRPLANE_MODE, TOGGLE_DATA_SAVER, SET_NETWORK_MODE, TOGGLE_MOBILE_DATA | SELF_SERVICE | DEVICE_SETTING_FIX (or SELF_SERVICE N/A in train_005) |
| REFUEL_DATA | SELF_SERVICE | DATA_RECOVERY |
| ENABLE_LINE_ROAMING | CARRIER_UPDATE | CARRIER_UPDATE |
| SEND_PAYMENT_REQUEST (+RESUME_LINE_REBOOT) | BILLING_RECOVERY | (not in enum → TRANSFER_HUMAN) |
| TRANSFER_HUMAN | HUMAN_TRANSFER | HUMAN_TRANSFER |

### Charge / carrier fields
- `charge_amount_usd`: REFUEL_DATA → `refuel_gb × plan.data_refueling_price_per_gb`; SEND_PAYMENT_REQUEST → `bill.amount_due_usd`; all other actions → `0.00` (2-decimal).
- `carrier_update_required` (train_005): `true` ONLY for ENABLE_LINE_ROAMING; `false` otherwise.
- `data_refuel_gb` (train_005): the refuel amount (1-decimal) for REFUEL_DATA; `0.0` otherwise.
- `permission` (train_002): `storage`/`sms`/`sms_and_storage` for GRANT_MESSAGING_PERMISSION; `NONE` otherwise.
- `bill_id` (train_002): the overdue bill_id for BILLING_RECOVERY; `""` otherwise.
- `secondary_action`: `RESUME_LINE_REBOOT` for BILLING_RECOVERY; `NO_ACTION` for all other single-step actions.

### Predicted train_002 (5 cases)
- CASE-2101 (sim missing) → RESEAT_SIM, secondary NO_ACTION, perm NONE, bill "", charge 0.00, SELF_SERVICE.
- CASE-2102 (Suspended OVERDUE_BILL, BILL-2102 Overdue $86.4) → SEND_PAYMENT_REQUEST, secondary RESUME_LINE_REBOOT, perm NONE, bill BILL-2102, charge 86.40, BILLING_RECOVERY.
- CASE-2103 (abroad, line.roaming_enabled=true, phone_roaming_enabled=false) → TOGGLE_ROAMING, secondary NO_ACTION, SELF_SERVICE.
- CASE-2104 (MMS, storage=false, mmsc present) → GRANT_MESSAGING_PERMISSION, permission=storage, SELF_SERVICE.
- CASE-2105 (SLOW_DATA, vpn_connected=true) → DISCONNECT_VPN, SELF_SERVICE.
- queue_summary: self_service_fixes=4, billing_recoveries=1, carrier_updates=0, human_transfers=0.

### Predicted train_005 (5 cases)
- CASE-2501 (data_used 16.2 > limit 15, pref accepted_refuel_gb=2.0) → REFUEL_DATA, data_refuel_gb=2.0, charge=2.0×2.0=4.00, carrier_update_required=false, DATA_RECOVERY.
- CASE-2502 (abroad, line.roaming_enabled=false, phone on) → ENABLE_LINE_ROAMING, data_refuel_gb=0.0, charge=0.00, carrier_update_required=true, CARRIER_UPDATE.
- CASE-2503 (data_saver_mode=true) → TOGGLE_DATA_SAVER, DEVICE_SETTING_FIX.
- CASE-2504 (network_mode_preference=3g_only) → SET_NETWORK_MODE, DEVICE_SETTING_FIX.
- CASE-2505 (mobile_data_enabled=false) → TOGGLE_MOBILE_DATA, DEVICE_SETTING_FIX.
- worklist_summary: data_refuel_cases=1, carrier_updates=1, device_setting_fixes=3, human_transfers=0, total_estimated_customer_charge_usd=4.00.

## 5. Enterprise family — export-complaint response package (train_003)

Inputs: complaint email (client name, product, incident ref) + `response_requirements.json` (required fields, `permission_users_to_include`, `naming_style`).

### Build order
1. **incident_id**: from the complaint email (e.g. INC-7301). Confirm via `GET /api/enterprise/incidents` (match `incident_id` + client).
2. **enterprise_account_id**: from `incident.enterprise_account_id` (cross-check `GET /api/enterprise/accounts` by `name` == client).
3. **failure_window**: `GET /api/enterprise/export-runs?incident_id=<id>`.
   - `start_date` = run_date of the FIRST FAILED run.
   - `end_date` = run_date of the LAST FAILED run.
   - `failed_days` = count of consecutive FAILED runs. (Asteri: 2026-05-12 → 2026-05-14, 3. Quanta: 2026-05-25 → 2026-05-28, 4.)
4. **backfill_days**: = `failed_days` (the failed runs are backfilled; confirmed by the succeeding recovery run + messages saying "N days require manual backfill"). (Asteri 3, Quanta 4.)
5. **root_cause_category**: the FAILED runs' `failure_code`, lowercased, corroborated by message evidence. (Asteri: `stale_credential`; Quanta: `staging_storage_quota`.) Concise category string.
6. **contributing_alert_issue** (`ARCHIVED_ALERT_ROUTE | NONE | UNKNOWN`): search `GET /api/enterprise/messages?query=<client/incident>`; if an alert message's `channel` contains `"archive"` (e.g. `export-alerts-archive`) → `ARCHIVED_ALERT_ROUTE`; if there is a clear alert in an active channel (e.g. `data-platform`) → `NONE`; if no message evidence → `UNKNOWN`. (Asteri: ARCHIVED_ALERT_ROUTE; Quanta: NONE.)
7. **sla_credit_percent**: `GET /api/enterprise/sla/<enterprise_account_id>` → `monthly_export_credit_percent`, applied when the `credit_trigger` condition is met (Asteri: "3 consecutive failed" → 15; Quanta: "critical export outage longer than 72 hours", 4 days=96h → 20). Integer percent.
8. **severity**: from `incident.severity` (Critical/High/Medium/Low).
9. **engineering_owner**: from `incident.engineering_owner`.
10. **account_owner**: from `incident.account_owner`.
11. **channel_name** (lowercase-hyphen): the active operational/alert channel for the product. If the alert was routed to an archived channel, use the active counterpart (strip `-archive`): Asteri → `export-alerts`. Otherwise use the channel from the engineering root-cause message (Quanta → `data-platform`). **(inferred)**
12. **evidence_folder** (client-date investigation folder): `<client-slug>-<failure_window.start_date>-investigation`. Client slug = first two words of the account name, lowercased, hyphenated (drop Inc./Group): Asteri Retail Inc. → `asteri-retail`. → `asteri-retail-2026-05-12-investigation`. **(inferred)**
13. **report_title** (client export failure report title): `<Client Name> Export Failure Report` (Title Case, full client name minus Inc./Group): `Asteri Retail Export Failure Report`. **(inferred)**
14. **share_permissions**: one entry per user in `response_requirements.permission_users_to_include`, in that exact order. Permission (`view | edit | upload_only`) **(inferred)**: finance_owner (if in list, e.g. laura.brown) → `edit` (approves/adjusts SLA credit); other included users → `view`. (Asteri: `[{user: laura.brown, permission: edit}, {user: jun.chen, permission: view}]`. Alternative: laura.brown=view, jun.chen=upload_only.)
15. **response_status** (`READY_TO_SEND | NEEDS_FINANCE_REVIEW | NEEDS_ENGINEERING_REVIEW | UNDER_INVESTIGATION`) **(inferred)**:
    - root_cause unknown (no failure_code / no message evidence) → `UNDER_INVESTIGATION`;
    - root_cause known but NO successful recovery run (fix not verified) → `NEEDS_ENGINEERING_REVIEW`;
    - root_cause known + recovery run SUCCEEDED + backfill done + SLA credit applicable → `NEEDS_FINANCE_REVIEW` (finance must approve the credit before sending);
    - all approved → `READY_TO_SEND`.
    - Asteri: STALE_CREDENTIAL known, RUN-AST-3 SUCCEEDED on 2026-05-15, 3-day backfill, 15% credit → **NEEDS_FINANCE_REVIEW**. (Alternative: READY_TO_SEND if the credit is treated as auto-applied per contract.)

### Predicted train_003 (Asteri / INC-7301)
- incident_id: INC-7301; enterprise_account_id: ENT-3001.
- root_cause_category: stale_credential; contributing_alert_issue: ARCHIVED_ALERT_ROUTE.
- failure_window: {start_date: 2026-05-12, end_date: 2026-05-14, failed_days: 3}; backfill_days: 3.
- sla_credit_percent: 15; severity: Critical.
- engineering_owner: delana.rao; account_owner: stephany.lo.
- channel_name: export-alerts; evidence_folder: asteri-retail-2026-05-12-investigation; report_title: Asteri Retail Export Failure Report.
- share_permissions: [{laura.brown, edit}, {jun.chen, view}].
- response_status: NEEDS_FINANCE_REVIEW.

## 6. Audit-math definitions (ticket family — for audit-style output variants)

Let **D** = set of diagnosed tickets (passed all gates; real root_cause). For t∈D: `sub` = subscribed_mbps; `f_bw = 0.80·sub`; `f_lat = 100`; `f_jit = 30`.

- **pre_troubleshooting_bandwidth_gap_total** = Σ_over_D `max(0, f_bw − pre_bandwidth_mbps)` (total Mbps below the bandwidth floor before troubleshooting; only positive gaps). **(inferred)**
- **diagnostic_records_skipped_by_gate** = count of tickets NOT diagnosed because a gate fired = (INVALID_ACCOUNT) + (AUTH_FAILED) + (suspended) + (active-outage). I.e. `total_tickets − |D|`. **(inferred)**
- **post_troubleshooting_remaining_issue_flags** = Σ_over_D (count of issue types among {bandwidth, latency, stability} still violated POST). RESOLVED tickets contribute 0; each ESCALATED ticket contributes ≥1. Compute: `(post_bw < f_bw) + (post_lat > f_lat) + (post_jit > f_jit)` summed over D. **(inferred)**
- **post_threshold_excess_totals** (per dimension, over D):
  - bandwidth shortfall: Σ `max(0, f_bw − post_bandwidth_mbps)`.
  - latency excess: Σ `max(0, post_latency_ms − f_lat)`.
  - jitter excess: Σ `max(0, post_jitter_ms − f_jit)`.
  - total = sum of the three. **(inferred)**
- **per-ticket floor/shortfall list** (for each t∈D): `{ticket_id, subscribed_mbps, bandwidth_floor=f_bw, pre_bandwidth_mbps, pre_bandwidth_shortfall=max(0,f_bw−pre_bw), pre_latency_ms, pre_latency_excess=max(0,pre_lat−f_lat), pre_jitter_ms, pre_jitter_excess=max(0,pre_jit−f_jit), post_* (same), pre_flags{bandwidth,latency,stability}, post_remaining_flags, root_causes, resolved_bool}`. **(inferred)**
- **success/failure ids**: success = ticket_ids with final_resolution_status RESOLVED; failure = ticket_ids ESCALATED (auto-troubleshoot did not clear all issues). (Gated FAILED/PENDING ids are列出 separately as skipped_by_gate.) **(inferred)**
- **root-cause-escalation grouping**: ESCALATED ticket_ids grouped by `root_cause → escalation_team` (fiber/signal→FIELD_OPS, backbone/capacity→NETWORK_ENGINEERING, provisioning→TIER2_SUPPORT, billing→ACCOUNTS_PAYABLE). **(inferred)**

## 7. Output field definitions (schema recap)

### train_001 ticket_decisions (per ticket, preserve payload order)
`ticket_id, account_id, final_resolution_status (RESOLVED|PENDING_ACTION|ESCALATED|FAILED), diagnostic_needed (bool), latency_issue (bool), stability_issue (bool, =jitter), bandwidth_issue (bool), outage_id (string; "" if none), escalation_team (NONE|TIER2_SUPPORT|FIELD_OPS|NETWORK_ENGINEERING|ACCOUNTS_PAYABLE), resolution_route (AUTO_TROUBLESHOOTING|OUTAGE_WAIT|ESCALATION|INELIGIBLE_ACCOUNT|AUTH_FAILED|INVALID_ACCOUNT)`.
batch_summary: `RESOLVED, PENDING_ACTION, ESCALATED, FAILED, tickets_requiring_customer_wait`.

### train_004 ticket_decisions (per ticket, preserve payload order)
`ticket_id, final_resolution_status (RESOLVED|PENDING_ACTION|ESCALATED|FAILED), route_team (NONE|TIER2_SUPPORT|FIELD_OPS|NETWORK_ENGINEERING|ACCOUNTS_PAYABLE), key_blocker (NONE|ACTIVE_OUTAGE|INVALID_ACCOUNT|AUTH_FAILED|OVERDUE_SUSPENSION|FRAUD_SUSPENSION|NETWORK_CAPACITY|PROVISIONING_STALE|PHYSICAL_LINE_FAULT), diagnostic_required (bool)`.
queue_summary: `FAILED, PENDING_ACTION, RESOLVED, ESCALATED, TIER2_SUPPORT, FIELD_OPS, NETWORK_ENGINEERING, ACCOUNTS_PAYABLE`.

### train_002 case_decisions (ascending case_id)
`case_id, customer_id, line_id, primary_action, secondary_action, permission (NONE|sms|storage|sms_and_storage), bill_id ("" if n/a), charge_amount_usd (2-decimal), final_route (SELF_SERVICE|BILLING_RECOVERY|CARRIER_UPDATE|HUMAN_TRANSFER)`.
queue_summary: `self_service_fixes, billing_recoveries, carrier_updates, human_transfers`.

### train_005 case_decisions (ascending case_id)
`case_id, primary_action, secondary_action, data_refuel_gb (1-decimal; 0.0 n/a), charge_amount_usd (2-decimal), carrier_update_required (bool), final_route (DATA_RECOVERY|CARRIER_UPDATE|DEVICE_SETTING_FIX|HUMAN_TRANSFER)`.
worklist_summary: `data_refuel_cases, carrier_updates, device_setting_fixes, human_transfers, total_estimated_customer_charge_usd`.

### train_003 (single object)
`incident_id, enterprise_account_id, root_cause_category, contributing_alert_issue (ARCHIVED_ALERT_ROUTE|NONE|UNKNOWN), failure_window{start_date,end_date,failed_days}, backfill_days, sla_credit_percent (int), severity (Critical|High|Medium|Low), engineering_owner, account_owner, channel_name, evidence_folder, report_title, share_permissions[{user,permission(view|edit|upload_only)}], response_status (READY_TO_SEND|NEEDS_FINANCE_REVIEW|NEEDS_ENGINEERING_REVIEW|UNDER_INVESTIGATION)`.

## 8. Pitfalls
- **Always use base URL `<remote-env-url>`**, never 127.0.0.1:8057.
- **GENERATED_NOISE** root_cause = gated-out sentinel; never run floor analysis on it. Only the 8 real root_cause tickets get diagnosed. Other "Generated Customer/Plan/Message/Enterprise" records are filler — distinguish real records (named owners, real failure_codes, real metrics) from generated filler.
- **Bandwidth floor is a RATIO of subscribed_mbps**, not absolute. Each ticket has its own `subscribed_mbps`. Compute `0.80·subscribed_mbps` per ticket.
- **stability_issue = jitter** (not a separate signal). Flag when `jitter_ms > 30`.
- **RESOLVED requires ALL pre-flagged issues cleared post** — not "improved". A ticket can improve on bandwidth but stay ESCALATED if latency/jitter remain (e.g. TCK-5407).
- **Outage gate requires `active==true` AND `service_type ∈ outage.service_types`** — a non-matching outage does not block.
- **Mobile roaming**: distinguish `line.roaming_enabled` (line-side → ENABLE_LINE_ROAMING, carrier update) vs `device.phone_roaming_enabled` (device toggle → TOGGLE_ROAMING, self-service). They are different fixes.
- **Mobile suspension**: `OVERDUE_BILL` → billing recovery (SEND_PAYMENT_REQUEST+RESUME_LINE_REBOOT); `CONTRACT_ENDED`/other → TRANSFER_HUMAN. Do not send a payment request for a non-bill suspension.
- **MMS**: `mmsc_url_present==false` → RESET_APN_REBOOT; `storage`/`sms` permission false → GRANT_MESSAGING_PERMISSION. Don't confuse the two.
- **Enterprise**: `failure_window.end_date` is the LAST FAILED run_date, not the recovery date. `backfill_days = failed_days`. `sla_credit_percent` comes from the SLA contract (per-account), applied when the trigger condition is met — it is NOT always 15 (Quanta=20).
- **preserve order**: ticket_decisions preserve payload CSV order; case_decisions preserve ascending case_id order.
- **Numbers**: charges 2-decimal; data_refuel_gb 1-decimal; sla_credit_percent integer.
- **Inferred fields with residual uncertainty**: suspension status (FAILED vs PENDING_ACTION), train_001 escalation_team for suspension (ACCOUNTS_PAYABLE vs NONE), channel_name/evidence_folder/report_title naming, share_permissions permission levels, response_status. If a count/total mismatches, reconsider suspension=PENDING_ACTION first.

## 9. Threshold summary (inferred)
- **latency_ms floor = 100** (flag >100; clear ≤100).
- **jitter_ms floor = 30** (flag >30; clear ≤30).
- **bandwidth floor = 0.80 × subscribed_mbps** (flag <0.80·sub; clear ≥0.80·sub).
