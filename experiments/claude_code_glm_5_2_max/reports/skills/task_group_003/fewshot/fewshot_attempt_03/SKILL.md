---
name: scn003-crm-support-ops
description: SCN_003 CRM support-operations solver. Resolve ticket batches (fixed-line diagnostics + gates), mobile contact-center triage, and enterprise export-complaint response packages against the shared support-console API. Apply exact metric thresholds, gate order, root-cause->team map, mobile action decision tree, and enterprise package derivation rules.
---

# SCN_003 CRM Support-Operations SOP

Executable procedure for three task families behind one support-console API. Always read `payloads/answer_template.json` first to detect which output schema is required, then follow the matching SOP. Return only JSON that conforms to the template. Preserve payload order (tickets) or ascending case_id order (mobile) exactly.

## 0. API map

Base URL: the harness-provided support console (training prompts show `http://127.0.0.1:8057`; the live base is `<remote-env-url>`). Use whatever base the harness supplies. All endpoints are GET, JSON.

Fixed-line / ticket domain:
- `GET /api/tickets/{ticket_id}` → `{ticket_id, account_id, service_area, service_type, subscribed_mbps, status, issue_summary, created_at}`
- `GET /api/accounts/{account_id}` → `{account_id, name, service_area, status, tier, authentication{last_login_status, last_login_at, account_recovery_status}}` (404 `{"error":"not_found"}` when account missing)
- `GET /api/diagnostics/{ticket_id}` → `{ticket_id, latency_ms, jitter_ms, bandwidth_mbps, root_causes[], started_at, completed_at}` (pre-troubleshooting metrics)
- `GET /api/troubleshooting/{ticket_id}` → `{ticket_id, post_latency_ms, post_jitter_ms, post_bandwidth_mbps, steps[], started_at, completed_at}` (post-troubleshooting metrics)
- `GET /api/outages` → list of `{outage_id, active, service_area, service_types[], eta_hours, impact_score, started_at}`

Mobile domain:
- `GET /api/cases/{case_id}` → `{case_id, customer_id, line_id, device_id, issue_type, customer_location, summary, opened_at}`
- `GET /api/lines/{line_id}` → `{line_id, customer_id, device_id, plan_id, status, suspension_reason, roaming_enabled, data_used_gb, phone_number, contract_end_date}`
- `GET /api/devices/{device_id}` → `{device_id, model, sim_status, signal_strength, airplane_mode, mobile_data_enabled, phone_roaming_enabled, data_saver_mode, network_mode_preference, vpn_connected, wifi_calling_enabled, mmsc_url_present, can_send_mms, messaging_permissions{sms, storage}, speed_test}`
- `GET /api/plans/{plan_id}` → `{plan_id, name, data_limit_gb, data_refueling_price_per_gb, monthly_price_usd}`
- `GET /api/bills` → list of `{bill_id, customer_id, amount_due_usd, status, due_date}` (filter by customer_id)

Enterprise domain (all under `/api/enterprise`):
- `GET /api/enterprise/accounts` → list; `GET /api/enterprise/accounts/{ENT-id}` → `{enterprise_account_id, name, tier, account_owner, finance_owner}`
- `GET /api/enterprise/incidents` → list; `GET /api/enterprise/incidents/{INC-id}` → `{incident_id, enterprise_account_id, product, severity, status, summary, received_at, account_owner, engineering_owner}`
- `GET /api/enterprise/export-runs` → list of `{run_id, incident_id, enterprise_account_id, run_date, status, failure_code, exported_record_count}` (filter by incident_id)
- `GET /api/enterprise/sla/{tier}` and `/api/enterprise/sla/{tier}/{days}` exist but return empty `{}` — SLA credit is a derived formula, not a lookup (see §3).
- No alert-route/permissions/postmortem endpoints exist; `contributing_alert_issue` and share-permission values are inference rules (see §3).

The `/health` endpoint returns 200. Unknown paths return 404 `{"error":"not_found"}`.

---

## 1. Family A — Ticket batch resolution (fixed-line)

Two output schemas exist; detect from the template.
- Schema A1 (decisions carry `latency_issue`/`stability_issue`/`bandwidth_issue`/`diagnostic_needed`/`resolution_route`/`escalation_team` + `batch_summary` with status counts and `tickets_requiring_customer_wait`).
- Schema A2 (decisions carry `key_blocker`/`route_team`/`diagnostic_required` + `queue_summary` with status counts AND per-team counts `TIER2_SUPPORT`/`FIELD_OPS`/`NETWORK_ENGINEERING`/`ACCOUNTS_PAYABLE`).

Both share the same gate logic, thresholds, and root-cause→team map; only the surface fields differ.

### 1.1 Gate order (evaluate top-down; first match wins, terminal)

For each ticket (in payload order):

1. **Account exists.** `GET /api/accounts/{account_id}`. If 404 → **INVALID_ACCOUNT**. Status=FAILED, diagnostic=false. (A1 route `INVALID_ACCOUNT`, outage_id `""`, team NONE. A2 key_blocker `INVALID_ACCOUNT`, route_team NONE.)
2. **Authentication.** If `authentication.last_login_status == "FAILURE"` OR `authentication.account_recovery_status == "FAILURE"` → **AUTH_FAILED**. Status=FAILED, diagnostic=false. (A1 route `AUTH_FAILED`. A2 key_blocker `AUTH_FAILED`, route_team NONE.)
3. **Account eligibility / status.** If `status != "Active"` (typically `"Suspended"`):
   - A2 schema: classify by report/queue-note context — billing/overdue suspension → **OVERDUE_SUSPENSION**, route_team `ACCOUNTS_PAYABLE`; fraud suspension → **FRAUD_SUSPENSION**, route_team `ACCOUNTS_PAYABLE` (or NONE if not billing-recoverable). Status=FAILED, diagnostic=false.
   - A1 schema: suspended/on-hold account → **INELIGIBLE_ACCOUNT**, team NONE. Status=FAILED, diagnostic=false. (A1 does not sub-classify overdue vs fraud.)
   - Note: the fixed-line account object has no `suspension_reason`; the distinction comes from the report text ("overdue notice" → overdue; "account hold" → ineligible in A1). A suspended account ALWAYS fails the gate (never runs diagnostics).
4. **Active outage.** `GET /api/outages`. A match = an outage with `active == true` AND `outage.service_area == ticket.service_area` AND `ticket.service_type IN outage.service_types`. If a match exists → **OUTAGE_WAIT**. Status=PENDING_ACTION, diagnostic=false, outage_id = matched `outage_id`. (A2 key_blocker `ACTIVE_OUTAGE`, route_team NONE.) If multiple active outages match the same area+type, use the first matching `outage_id`. Inactive outages (`active==false`) never match.
5. **Run diagnostics.** None of the above matched → `diagnostic_needed=true` (A2 `diagnostic_required=true`). Fetch `/api/diagnostics/{ticket_id}` (pre) and `/api/troubleshooting/{ticket_id}` (post). Compute pre issue flags, then post resolution (§1.3, §1.4).

Order is mandatory: a suspended account with a simultaneous active outage still resolves to the account gate (step 3) before the outage gate (step 4). Auth failure (step 2) beats account-status and outage.

### 1.2 Metric thresholds (EXACT)

Global floors (same for all service types):
- **latency_ms floor = 100.** Latency issue iff `latency_ms > 100`.
- **jitter_ms floor = 30.** Stability issue iff `jitter_ms > 30`. (`stability_issue` corresponds to jitter.)

Bandwidth floor is a fraction of the ticket's `subscribed_mbps` and VARIES by `reported_service_type` / `service_type`:

| service_type | bandwidth floor (issue if `bandwidth_mbps < floor`) |
|---|---|
| internet | `0.90 × subscribed_mbps` |
| voice    | `0.90 × subscribed_mbps` |
| video    | `0.80 × subscribed_mbps` |

Confirmed: internet 90% (resolved ticket post_bw lands just above `0.90×subscribed`), voice 90% (same), video 80% (inferred from a partially-cleared escalated ticket whose post_bw lands just above `0.80×subscribed`). Derivation method: `bandwidth_floor_mbps = ratio[service_type] × subscribed_mbps`. These are ratios of subscribed because an absolute floor is impossible — two internet tickets at different subscribed rates flag the same measured Mbps differently (verified against gold).

Pre-troubleshooting issue flags (A1 `latency_issue`/`stability_issue`/`bandwidth_issue`) = whether the PRE (`/api/diagnostics`) metric violates its floor. These are PRE-troubleshooting flags only; they do not change after troubleshooting.

### 1.3 Root-cause → escalation team map

Applies only to diagnostic tickets that ESCALATE (post-troubleshooting did not clear all issues). Read `root_causes[]` from `/api/diagnostics` and map by keyword:

| root_cause keyword | escalation team | A2 key_blocker label |
|---|---|---|
| `FIBER_*`, `SIGNAL_*`, fiber/signal/physical-line (e.g. `FIBER_DROP_DAMAGE`, `SIGNAL_LOSS`) | `FIELD_OPS` | `PHYSICAL_LINE_FAULT` |
| `BACKBONE_*`, `CAPACITY_*`, `NETWORK_CAPACITY` (e.g. `BACKBONE_CAPACITY`) | `NETWORK_ENGINEERING` | `NETWORK_CAPACITY` |
| `PROVISIONING_*`, provisioning (e.g. `PROVISIONING_STALE`) | `TIER2_SUPPORT` | `PROVISIONING_STALE` |
| `BILLING_*`, billing/overdue | `ACCOUNTS_PAYABLE` | `OVERDUE_SUSPENSION` (usually handled at the gate) |

Roots that auto-resolve via troubleshooting and do NOT escalate (e.g. `CONFIGURATION_DRIFT`, `VOICE_PROFILE_STALE`) get team NONE / key_blocker NONE in A2. The map only fires when post-troubleshooting fails to clear all issues.

### 1.4 Post-troubleshooting resolution

Re-check the POST metrics (`/api/troubleshooting`'s `post_latency_ms`/`post_jitter_ms`/`post_bandwidth_mbps`) against the SAME floors (latency 100, jitter 30, bandwidth floor by type). The post-bandwidth floor uses the SAME ratio × subscribed_mbps.

- If ALL post metrics clear their floors (post_latency ≤ 100, post_jitter ≤ 30, post_bandwidth ≥ floor) → **RESOLVED**, route **AUTO_TROUBLESHOOTING** (A1) / key_blocker NONE, route_team NONE (A2). The ticket used auto-troubleshooting.
- Else (any post metric still violates) → **ESCALATED**, route **ESCALATION** (A1) / route_team from the root-cause→team map (A2). A2 key_blocker = the root-cause-derived label above.

### 1.5 Audit formulas (state/emit when the schema or a grader requests an audit block; train gold omits it)

Computed over the whole ticket batch. `Diagnostic tickets` = tickets that reached step 5 (ran `/api/diagnostics`). `Gated tickets` = tickets terminal at steps 1–4.

- **pre_troubleshooting_bandwidth_gap_total_mbps** = Σ over diagnostic tickets of `max(0, bandwidth_floor_mbps − pre_bandwidth_mbps)`, where `bandwidth_floor_mbps = ratio[service_type] × subscribed_mbps`.
- **diagnostic_records_skipped_by_gate** = count of gated tickets (routes INVALID_ACCOUNT / AUTH_FAILED / INELIGIBLE_ACCOUNT / OVERDUE_SUSPENSION / FRAUD_SUSPENSION / OUTAGE_WAIT). These have `/api/diagnostics` records available but they are not used.
- **post_troubleshooting_remaining_issue_flags** = Σ over diagnostic tickets of (number of {latency, stability, bandwidth} still violating when post metrics are checked). 0 if all resolved.
- **post_threshold_excess_totals** = over ESCALATED diagnostic tickets (post not cleared), three sums:
  - latency excess = Σ `max(0, post_latency_ms − 100)`
  - jitter excess  = Σ `max(0, post_jitter_ms − 30)`
  - bandwidth shortfall = Σ `max(0, bandwidth_floor_mbps − post_bandwidth_mbps)`
- **tickets_using_post_troubleshooting_records** = count of diagnostic tickets with a `/api/troubleshooting` record used in the decision (= diagnostic tickets that are RESOLVED or ESCALATED via auto-troubleshooting).
- **tickets_with_active_outage_match** = count of tickets routed to OUTAGE_WAIT (step 4 match).
- **unique_escalation_teams** = sorted unique `escalation_team`/`route_team` values among ESCALATED tickets, excluding NONE.
- **root_cause_escalation_ticket_ids** = map team → sorted list of ticket_ids escalated to that team (from the root-cause map).
- **post success/failure id lists**: `post_success_ids` = sorted ticket_ids where post cleared all issues (RESOLVED/AUTO_TROUBLESHOOTING); `post_failure_ids` = sorted ticket_ids where post did NOT clear all (ESCALATED).
- **per-ticket floor + shortfall lists (sorted by ticket_id)**: for each diagnostic ticket, a record with `{ticket_id, service_type, subscribed_mbps, bandwidth_floor_mbps, pre_bandwidth_mbps, pre_bandwidth_shortfall_mbps=max(0,floor−pre), post_bandwidth_mbps, post_bandwidth_shortfall_mbps=max(0,floor−post), latency_floor_ms=100, pre_latency_ms, post_latency_ms, jitter_floor_ms=30, pre_jitter_ms, post_jitter_ms}`, sorted ascending by ticket_id.

### 1.6 Summary blocks

- A1 `batch_summary`: counts of RESOLVED / PENDING_ACTION / ESCALATED / FAILED, plus `tickets_requiring_customer_wait` = count of PENDING_ACTION (outage-wait) tickets.
- A2 `queue_summary`: counts of FAILED / PENDING_ACTION / RESOLVED / ESCALATED, plus per-team counts `TIER2_SUPPORT` / `FIELD_OPS` / `NETWORK_ENGINEERING` / `ACCOUNTS_PAYABLE` (tally route_team across all tickets; teams with zero still appear as 0).

---

## 2. Family B — Mobile contact-center triage

Two output schemas; detect from the template.
- Schema B1 "triage" (train_002): per-case `customer_id`, `line_id`, `primary_action`, `secondary_action`, `permission`, `bill_id`, `charge_amount_usd`, `final_route` (SELF_SERVICE | BILLING_RECOVERY | CARRIER_UPDATE | HUMAN_TRANSFER). Broader action enum incl. RESEAT_SIM, SEND_PAYMENT_REQUEST, RESUME_LINE_REBOOT, GRANT_MESSAGING_PERMISSION, TOGGLE_WIFI_CALLING, RESET_APN_REBOOT, TOGGLE_AIRPLANE_MODE.
- Schema B2 "data recovery" (train_005): per-case `primary_action`, `secondary_action`, `data_refuel_gb`, `charge_amount_usd`, `carrier_update_required`, `final_route` (DATA_RECOVERY | CARRIER_UPDATE | DEVICE_SETTING_FIX | HUMAN_TRANSFER). Narrower, data-focused action enum.

For each case: `GET /api/cases/{case_id}` → line_id, device_id, customer_id, issue_type, customer_location. Then `GET /api/lines/{line_id}`, `GET /api/devices/{device_id}`, `GET /api/plans/{plan_id}` (plan_id from line), and find the customer's bill via `GET /api/bills` filtered by customer_id. Process cases in ascending case_id order.

### 2.1 Phone-side vs carrier-line-side (decides final_route)

- **Phone-side (device setting / self service)**: RESEAT_SIM, TOGGLE_AIRPLANE_MODE, TOGGLE_MOBILE_DATA, TOGGLE_ROAMING (phone-side roaming toggle), TOGGLE_DATA_SAVER, SET_NETWORK_MODE, DISCONNECT_VPN, GRANT_MESSAGING_PERMISSION, TOGGLE_WIFI_CALLING, RESET_APN_REBOOT → B1 route `SELF_SERVICE`, B2 route `DEVICE_SETTING_FIX`. carrier_update_required=false.
- **Carrier-line-side**: ENABLE_LINE_ROAMING (carrier must turn on line roaming) → route `CARRIER_UPDATE`, carrier_update_required=true. REFUEL_DATA (plan data add-on, chargeable) → B2 route `DATA_RECOVERY`. SEND_PAYMENT_REQUEST + RESUME_LINE_REBOOT (billing recovery) → B1 route `BILLING_RECOVERY`. TRANSFER_HUMAN → `HUMAN_TRANSFER` in both.

### 2.2 Decision tree (evaluate top-down; first match wins)

1. **Suspended line (billing gate).** If `line.status == "Suspended"`:
   - `suspension_reason == "OVERDUE_BILL"` and the customer has a bill with `status == "Overdue"`: **primary = SEND_PAYMENT_REQUEST**, **secondary = RESUME_LINE_REBOOT**, `bill_id` = overdue bill_id, `charge_amount_usd` = bill.amount_due_usd, route `BILLING_RECOVERY`, permission NONE. (B1.)
   - Other suspension reasons not recoverable remotely: TRANSFER_HUMAN, route HUMAN_TRANSFER.
2. **NO_SERVICE (device hardware).** If `issue_type == "NO_SERVICE"` or `sim_status == "missing"` or `signal_strength == "none"`:
   - `sim_status == "missing"`: **RESEAT_SIM** (SELF_SERVICE). (Customer re-seats the SIM after a commute drop.)
   - `airplane_mode == true`: **TOGGLE_AIRPLANE_MODE** (SELF_SERVICE).
   - else (sim active, no airplane, still no service): **RESET_APN_REBOOT**, else TRANSFER_HUMAN.
3. **MMS.** If `issue_type == "MMS"` or (`can_send_mms == false`):
   - If `messaging_permissions.storage == false` and `sms == false`: **GRANT_MESSAGING_PERMISSION**, permission `sms_and_storage`.
   - elif `storage == false`: **GRANT_MESSAGING_PERMISSION`, permission `storage`.
   - elif `sms == false`: **GRANT_MESSAGING_PERMISSION**, permission `sms`.
   - elif `mmsc_url_present == false`: **RESET_APN_REBOOT**.
   - else TRANSFER_HUMAN.
   - (permission enum: NONE | sms | storage | sms_and_storage; only non-NONE for GRANT_MESSAGING_PERMISSION.)
4. **Roaming abroad with no data.** If `customer_location == "abroad"` and data unavailable:
   - `line.roaming_enabled == false`: **ENABLE_LINE_ROAMING** (CARRIER_UPDATE, carrier_update_required=true). The carrier line must be roaming-enabled.
   - elif `device.phone_roaming_enabled == false`: **TOGGLE_ROAMING** (SELF_SERVICE). Phone-side roaming switch is off but the line allows roaming.
5. **Data cap exceeded.** If `line.data_used_gb > plan.data_limit_gb`: **REFUEL_DATA**. `data_refuel_gb` = `customer_preferences.accepted_refuel_gb` for the case (fall back to a 1.0 GB default if absent). `charge_amount_usd` = `data_refuel_gb × plan.data_refueling_price_per_gb`, rounded to 2 decimals. route `DATA_RECOVERY`. carrier_update_required=false.
6. **Mobile data off.** If `device.mobile_data_enabled == false`: **TOGGLE_MOBILE_DATA** (DEVICE_SETTING_FIX).
7. **Slow data** (`issue_type == "SLOW_DATA"` or `speed_test` in {poor, fair}):
   - `vpn_connected == true`: **DISCONNECT_VPN** (SELF_SERVICE).
   - `data_saver_mode == true`: **TOGGLE_DATA_SAVER** (DEVICE_SETTING_FIX).
   - `network_mode_preference` is an older mode (e.g. `3g_only`, not `4g_5g_preferred`): **SET_NETWORK_MODE** (DEVICE_SETTING_FIX).
   - else TRANSFER_HUMAN.
8. **Fallback:** TRANSFER_HUMAN, route HUMAN_TRANSFER.

`secondary_action` is the required follow-up (only RESUME_LINE_REBOOT after SEND_PAYMENT_REQUEST in training); otherwise `NO_ACTION`. `data_refuel_gb` = 0.0 and `charge_amount_usd` = 0.0 when not REFUEL_DATA. `bill_id` = `""` when not billing. `carrier_update_required` is true ONLY for ENABLE_LINE_ROAMING (false otherwise, including REFUEL_DATA).

### 2.3 Summary blocks

- B1 `queue_summary`: tally `self_service_fixes` / `billing_recoveries` / `carrier_updates` / `human_transfers` from final_route.
- B2 `worklist_summary`: tally `data_refuel_cases` / `carrier_updates` / `device_setting_fixes` / `human_transfers` from final_route, plus `total_estimated_customer_charge_usd` = Σ charge_amount_usd (2 decimals).

---

## 3. Family C — Enterprise export-complaint response package

Single output schema (train_003). Inputs: `payloads/client_complaint_email.txt` (client name, product, approximate incident reference, severity hint in subject) and `payloads/response_requirements.json` (`required_fields`, `permission_users_to_include` [ordered], `naming_style`). Pull evidence from `/api/enterprise/*`.

### 3.1 Derivation chain (produce fields in this order)

1. **incident_id** — from the email's "Approximate incident reference" (`INC-7301`).
2. `GET /api/enterprise/incidents/{incident_id}`. Pull `enterprise_account_id`, `severity`, `account_owner`, `engineering_owner`, `received_at`, `status`, `product`.
   - `GET /api/enterprise/accounts/{enterprise_account_id}` for `name`, `tier`, `finance_owner`.
3. **Failed export-run window** — `GET /api/enterprise/export-runs`, filter `incident_id == incident_id` AND `status == "FAILED"`. `failure_window.start_date` = min `run_date`, `end_date` = max `run_date`, `failed_days` = count of FAILED runs. (Confirmed: INC-7301 → 2026-05-12..2026-05-14, 3 days.)
4. **backfill_days** = `failed_days` (one backfill per missed failed day).
5. **root_cause_category** — concise human phrase from the dominant `failure_code` shared by the FAILED runs. Map (only STALE_CREDENTIAL gold-confirmed; others inferred):
   - `STALE_CREDENTIAL` → `"stale credential after rotation"`
   - `STAGING_STORAGE_QUOTA` → `"staging storage quota exhaustion"`
   - `TIMEOUT` → `"export timeout"`
   - `RATE_LIMIT` → `"rate-limit throttling"`
   - `` (no code) → `"unknown"`
6. **contributing_alert_issue** — enum `ARCHIVED_ALERT_ROUTE | NONE | UNKNOWN`. The enterprise export-complaint scenario arises because failures persisted undetected; default to **ARCHIVED_ALERT_ROUTE** (the alert route was archived so monitoring did not surface the failures during the window). Set `NONE` only if evidence shows a live alert fired during the window; `UNKNOWN` if alert state is indeterminate. (train_003 → ARCHIVED_ALERT_ROUTE.)
7. **sla_credit_percent** = `failed_days × 5` (5% credit per failed day; validated: 3 days → 15%). The `/api/enterprise/sla/*` endpoints return empty, so use this formula. (Severity Critical in training; the 5%/day rate is the confirmed rule.)
8. **severity** — from the incident (`Critical | High | Medium | Low`). May match the email subject qualifier.
9. **engineering_owner** — from incident. **account_owner** — from incident (== account.account_owner).
10. **channel_name** — naming rule "lowercase hyphen channel": take the client `name`, lowercase, strip punctuation (periods/commas), replace spaces with hyphens. (Asteri Retail Inc. → `asteri-retail-inc`.)
11. **evidence_folder** — naming rule "client-date investigation folder": `<name> <Month Year> Investigation`, where Month Year comes from the failure_window start date. (→ `Asteri Retail Inc. May 2026 Investigation`.)
12. **report_title** — naming rule "client export failure report title": `<name> Export Failure - Resolution Report`. (→ `Asteri Retail Inc. Export Failure - Resolution Report`.)
13. **share_permissions** — one entry per user in `response_requirements.permission_users_to_include`, IN THAT ORDER. Permission value: if the user is the account's `finance_owner` → `view`; otherwise `edit`. (Enum: view | edit | upload_only. train_003: laura.brown=finance_owner→view, jun.chen→edit.) `upload_only` applies to contributors not exemplified in training.
14. **response_status** — enum `READY_TO_SEND | NEEDS_FINANCE_REVIEW | NEEDS_ENGINEERING_REVIEW | UNDER_INVESTIGATION`:
    - If `sla_credit_percent > 0` → **NEEDS_FINANCE_REVIEW** (credit requires finance sign-off). (train_003 → NEEDS_FINANCE_REVIEW.)
    - elif root_cause not determinable from failure_code → `NEEDS_ENGINEERING_REVIEW`.
    - elif incident.status still `UNDER_INVESTIGATION` with no credit and no root cause → `UNDER_INVESTIGATION`.
    - else → `READY_TO_SEND`.

### 3.2 Enterprise pitfalls
- The "Generated Enterprise N" accounts (owners literally `acct.owner`/`finance.owner`) are synthetic placeholders; the real accounts have real owner user-ids. Use the incident's `enterprise_account_id` to fetch the right account.
- `received_at` is when the complaint was received (after the failure window); it is NOT a failure date. Use export-run `run_date`s for the window.
- `failure_window.failed_days` and `backfill_days` are the count of FAILED runs, not calendar span (they coincide when failures are consecutive; if a gap exists, count FAILED runs).
- Do not echo the incident's `status` (`UNDER_INVESTIGATION`) as `response_status` — they are different fields; `response_status` is derived from credit/root-cause.

---

## 4. Cross-family pitfalls

- **Base URL.** Prompts show `http://127.0.0.1:8057`; always substitute the harness-provided/live base (`<remote-env-url>`). Every endpoint is under that one host.
- **Gate order is strict.** A suspended account with an active outage still resolves to the account gate, not the outage gate. Auth failure beats account-status and outage. Never run diagnostics on a gated ticket (`diagnostic_needed`/`diagnostic_required` = false).
- **Bandwidth floor is a RATIO of `subscribed_mbps`, per service_type** (internet 0.90, voice 0.90, video 0.80), not an absolute Mbps and not `subscribed_mbps` itself. Two tickets with the same measured Mbps but different `subscribed_mbps` can differ on the bandwidth flag.
- **latency floor 100 ms and jitter floor 30 ms are global.** Latency/jitter issue iff metric EXCEEDS the floor; bandwidth issue iff metric is BELOW the floor.
- **ticket_decisions issue flags are PRE-troubleshooting only.** Re-evaluate with POST metrics to decide RESOLVED vs ESCALATED; do not mutate the pre flags.
- **Active outage requires `active==true`** plus area + service_type match. Inactive outages in the same area do not match.
- **Mobile: distinguish roaming sides.** `line.roaming_enabled=false` → ENABLE_LINE_ROAMING (carrier, CARRIER_UPDATE); `line.roaming_enabled=true` but `device.phone_roaming_enabled=false` → TOGGLE_ROAMING (phone, SELF_SERVICE).
- **REFUEL_DATA** uses `customer_preferences.accepted_refuel_gb` for the GB and `plan.data_refueling_price_per_gb` for the rate. Charge = GB × rate, 2 decimals.
- **Field presence differs by schema.** B2 omits customer_id/line_id/permission/bill_id and adds data_refuel_gb/carrier_update_required. A2 omits the per-issue flags and adds key_blocker. Always follow the loaded template's exact field set and enum values.
- **Ordering.** Tickets: preserve payload order. Mobile cases: ascending case_id. share_permissions: order exactly as `permission_users_to_include`. Audit id-lists: sorted ascending by ticket_id. unique_escalation_teams: sorted.
- **Numeric formatting.** `charge_amount_usd` 2 decimals; `data_refuel_gb` 1 decimal (`0.0` when n/a). Integers for all counts.

## 5. Output field definitions (quick reference)

Family A1 (ticket_decisions): `ticket_id`, `account_id`, `final_resolution_status` (RESOLVED|PENDING_ACTION|ESCALATED|FAILED), `diagnostic_needed` (bool), `latency_issue` (bool, pre), `stability_issue` (bool, pre = jitter), `bandwidth_issue` (bool, pre), `outage_id` (string, `""` if none), `escalation_team` (NONE|TIER2_SUPPORT|FIELD_OPS|NETWORK_ENGINEERING|ACCOUNTS_PAYABLE), `resolution_route` (AUTO_TROUBLESHOOTING|OUTAGE_WAIT|ESCALATION|INELIGIBLE_ACCOUNT|AUTH_FAILED|INVALID_ACCOUNT). batch_summary: RESOLVED/PENDING_ACTION/ESCALATED/FAILED counts + tickets_requiring_customer_wait.

Family A2 (ticket_decisions): `ticket_id`, `final_resolution_status`, `route_team` (NONE|TIER2_SUPPORT|FIELD_OPS|NETWORK_ENGINEERING|ACCOUNTS_PAYABLE), `key_blocker` (NONE|ACTIVE_OUTAGE|INVALID_ACCOUNT|AUTH_FAILED|OVERDUE_SUSPENSION|FRAUD_SUSPENSION|NETWORK_CAPACITY|PROVISIONING_STALE|PHYSICAL_LINE_FAULT), `diagnostic_required` (bool). queue_summary: FAILED/PENDING_ACTION/RESOLVED/ESCALATED + TIER2_SUPPORT/FIELD_OPS/NETWORK_ENGINEERING/ACCOUNTS_PAYABLE.

Family B1 (case_decisions): `case_id`, `customer_id`, `line_id`, `primary_action`, `secondary_action`, `permission` (NONE|sms|storage|sms_and_storage), `bill_id` (`""` if none), `charge_amount_usd`, `final_route` (SELF_SERVICE|BILLING_RECOVERY|CARRIER_UPDATE|HUMAN_TRANSFER). queue_summary: self_service_fixes/billing_recoveries/carrier_updates/human_transfers.

Family B2 (case_decisions): `case_id`, `primary_action`, `secondary_action`, `data_refuel_gb` (1 decimal, 0.0 if none), `charge_amount_usd` (2 decimals), `carrier_update_required` (bool), `final_route` (DATA_RECOVERY|CARRIER_UPDATE|DEVICE_SETTING_FIX|HUMAN_TRANSFER). worklist_summary: data_refuel_cases/carrier_updates/device_setting_fixes/human_transfers + total_estimated_customer_charge_usd.

Family C: `incident_id`, `enterprise_account_id`, `root_cause_category`, `contributing_alert_issue` (ARCHIVED_ALERT_ROUTE|NONE|UNKNOWN), `failure_window{start_date,end_date,failed_days}`, `backfill_days`, `sla_credit_percent`, `severity` (Critical|High|Medium|Low), `engineering_owner`, `account_owner`, `channel_name`, `evidence_folder`, `report_title`, `share_permissions[{user,permission(view|edit|upload_only)}]`, `response_status` (READY_TO_SEND|NEEDS_FINANCE_REVIEW|NEEDS_ENGINEERING_REVIEW|UNDER_INVESTIGATION).
