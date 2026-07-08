---
name: reflect-3_attempt_01
description: SCN_003 CRM support-console analyst. Resolve same-day ticket batches, mobile triage queues, mobile-data recovery worklists, and enterprise export-complaint response packages by querying the shared support-console API and applying fixed diagnostic thresholds, gating order, root-cause routing, and per-family decision trees.
---

# SCN_003 CRM Support Operations Analyst

Reusable rules for working a support-console workload across four task families. All evidence comes from the remote support-console API; never assume field values — fetch the records. Prompts may reference `127.0.0.1:8057`; always substitute the real base URL provided by the harness.

## 1. API Map

Base URL: use the harness-provided base URL (e.g. `<remote-env-url>`). Health: `GET /health`.

Public catalog: `GET /api/catalog` (endpoints + record counts only).

- `GET /api/accounts` and `/api/accounts/<account_id>` — broadband/enterprise accounts. Fields: `account_id`, `name`, `service_area`, `status` (`Active`/`Suspended`), `tier`, `authentication{last_login_status, account_recovery_status, last_login_at}`. A missing account returns `{"error":"not_found"}`.
- `GET /api/tickets` and `/api/tickets/<ticket_id>` — tickets. Fields: `ticket_id`, `account_id`, `service_type` (`internet`/`video`/`voice`), `service_area`, `subscribed_mbps`, `status`, `issue_summary`.
- `GET /api/outages?service_area=<area>` — outages for an area. Each: `outage_id`, `service_area`, `active` (bool), `service_types` (array), `eta_hours`, `impact_score`, `started_at`.
- `GET /api/diagnostics/<ticket_id>` — pre-troubleshoot snapshot. Fields: `bandwidth_mbps`, `latency_ms`, `jitter_ms`, `root_causes` (array), `started_at`/`completed_at`.
- `GET /api/troubleshooting/<ticket_id>` — post-troubleshoot snapshot. Fields: `post_bandwidth_mbps`, `post_latency_ms`, `post_jitter_ms`, `steps` (array). (Not every ticket has diagnostics/troubleshooting records.)
- `GET /api/customers`, `/api/lines`, `/api/lines/<line_id>` — mobile. Line fields: `line_id`, `customer_id`, `device_id`, `plan_id`, `status`, `roaming_enabled`, `data_used_gb`, `suspension_reason` (e.g. `OVERDUE_BILL`).
- `GET /api/devices/<device_id>` — device state: `airplane_mode`, `mobile_data_enabled`, `phone_roaming_enabled`, `sim_status` (`active`/`missing`), `signal_strength`, `speed_test` (`excellent`/`good`/`fair`/`poor`/`no_connection`), `data_saver_mode`, `vpn_connected`, `network_mode_preference` (`4g_5g_preferred`/`3g_only`/…), `can_send_mms`, `mmsc_url_present`, `messaging_permissions{sms, storage}`, `wifi_calling_enabled`.
- `GET /api/plans` and `/api/plans/<plan_id>` — `data_limit_gb`, `data_refueling_price_per_gb`, `monthly_price_usd`.
- `GET /api/bills` — `bill_id`, `customer_id`, `amount_due_usd`, `due_date`, `status` (`Paid`/`Overdue`/`Issued`).
- `GET /api/cases` and `/api/cases/<case_id>` — mobile cases. Fields: `case_id`, `customer_id`, `line_id`, `device_id`, `issue_type`, `customer_location` (`home`/`abroad`), `summary`.
- `GET /api/enterprise/accounts` — `enterprise_account_id`, `name`, `tier`, `account_owner`, `finance_owner`.
- `GET /api/enterprise/incidents` — `incident_id`, `enterprise_account_id`, `product`, `severity`, `status`, `engineering_owner`, `account_owner`, `received_at`, `summary`.
- `GET /api/enterprise/export-runs?incident_id=<id>` — runs: `run_id`, `run_date`, `status` (`FAILED`/`SUCCEEDED`), `failure_code`, `exported_record_count`.
- `GET /api/enterprise/messages?query=<text>` — messages: `message_id`, `author`, `body`, `channel`, `created_at`.
- `GET /api/enterprise/sla/<enterprise_account_id>` — `monthly_export_credit_percent`, `credit_trigger`, `executive_contact`.

## 2. Diagnostic Thresholds (EXACT, converged values)

These floors decide per-ticket issue flags and the RESOLVED-vs-ESCALATED outcome. They are absolute for latency/jitter and a RATIO for bandwidth.

| Metric | Floor | Violation test | Issue flag |
|---|---|---|---|
| Latency | **100 ms** (absolute) | `latency_ms > 100` | `latency_issue` |
| Jitter / stability | **30 ms** (absolute) | `jitter_ms > 30` | `stability_issue` |
| Bandwidth | **0.75 × subscribed_mbps** (ratio) | `bandwidth_mbps / subscribed_mbps < 0.75` | `bandwidth_issue` |

- Flags are computed from the **PRE-troubleshoot** diagnostics snapshot.
- A ticket is **RESOLVED** by auto-troubleshooting **iff ALL three post-troubleshoot values clear the floors** (`post_latency_ms <= 100` AND `post_jitter_ms <= 30` AND `post_bandwidth_mbps / subscribed_mbps >= 0.75`).
- If any post value still violates → **ESCALATED** to the team mapped from the diagnostics `root_causes`.
- Boundary: a value exactly equal to the floor is treated as PASSING (strict `>` / `<` for violation).

## 3. Root-Cause → Escalation Team Map

Derived from `/api/diagnostics/<ticket_id>.root_causes`:

| root_cause keyword | escalation_team / route_team | Notes |
|---|---|---|
| `FIBER_*`, `SIGNAL_LOSS`, `*DROP_DAMAGE`, physical line/fault | `FIELD_OPS` | key_blocker `PHYSICAL_LINE_FAULT` |
| `BACKBONE_*`, `*_CAPACITY` | `NETWORK_ENGINEERING` | key_blocker `NETWORK_CAPACITY` |
| `PROVISIONING_*` (stale/mismatch) | `TIER2_SUPPORT` | key_blocker `PROVISIONING_STALE` |
| Billing / overdue suspension | `ACCOUNTS_PAYABLE` | key_blocker `OVERDUE_SUSPENSION` |
| `CONFIGURATION_DRIFT`, `VOICE_PROFILE_STALE` | (cleared by auto-troubleshooting → `NONE`) | typically RESOLVED |

## 4. Family SOPs

### Family A — Ticket batch resolution (per-ticket decision)

Gating order is strict; the FIRST gate that trips wins and **no diagnostics are run** for gated tickets.

1. **Account gate.** Fetch `/api/accounts/<account_id>`.
   - `not_found` (bad account id) → status `FAILED`, route `INELIGIBLE_ACCOUNT` / key_blocker `INVALID_ACCOUNT`, team `NONE`, `diagnostic_needed=false`.
   - `authentication.account_recovery_status == "FAILURE"` OR `authentication.last_login_status == "FAILURE"` → status `FAILED`, route `AUTH_FAILED` / key_blocker `AUTH_FAILED`, team `NONE`, `diagnostic_needed=false`. (Auth gate beats status gate.)
   - `status == "Suspended"` → status `FAILED`, route `INELIGIBLE_ACCOUNT`, key_blocker `OVERDUE_SUSPENSION` (if overdue/hold — route team `ACCOUNTS_PAYABLE`) or `FRAUD_SUSPENSION` (if fraud). Infer the subtype from the customer report / queue note ("account hold", "overdue notice" → overdue; "fraud" → fraud). `diagnostic_needed=false`.
2. **Outage gate.** Fetch `/api/outages?service_area=<ticket.service_area>`. If any outage has `active==true` AND `ticket.service_type` ∈ `outage.service_types` → status `PENDING_ACTION`, route `OUTAGE_WAIT`, `outage_id=<that outage_id>`, team `NONE`, all issue flags `false`, `diagnostic_needed=false`. (`tickets_requiring_customer_wait` counts these.)
3. **Diagnostics.** Otherwise fetch `/api/diagnostics/<ticket_id>` and `/api/troubleshooting/<ticket_id>`. `diagnostic_needed=true`. Compute the three PRE flags (Section 2). Then:
   - All three POST values clear floors → status `RESOLVED`, route `AUTO_TROUBLESHOOTING`, team `NONE`.
   - Any POST value still violates → status `ESCALATED`, route `ESCALATION`, team = map from `root_causes` (Section 3). Set the matching `key_blocker`.

Output fields (batch template): `ticket_id, account_id, final_resolution_status, diagnostic_needed, latency_issue, stability_issue, bandwidth_issue, outage_id, escalation_team, resolution_route` + `batch_summary{RESOLVED, PENDING_ACTION, ESCALATED, FAILED, tickets_requiring_customer_wait}`. Preserve payload order. Empty `outage_id` = `""`. `diagnostic_needed` = whether the diagnostic step was part of the flow (true only for tickets that reached step 3).

**Queue-QA variant** (different field names): per-ticket `final_resolution_status, route_team, key_blocker, diagnostic_required` + `queue_summary{FAILED, PENDING_ACTION, RESOLVED, ESCALATED, TIER2_SUPPORT, FIELD_OPS, NETWORK_ENGINEERING, ACCOUNTS_PAYABLE}`. `route_team` = the escalation team (NONE for RESOLVED/outage/auth/invalid; ACCOUNTS_PAYABLE for overdue suspension; mapped team for ESCALATED). `diagnostic_required` == `diagnostic_needed`.

### Family B — Mobile triage queue (case decision)

For each case fetch `/api/cases/<case_id>` → `customer_id, line_id, device_id, issue_type, customer_location`; then the line, device, plan, and (if billing) the customer's bill. Decision tree (primary → secondary → route):

- **NO_SERVICE, `sim_status == "missing"`** (e.g. after a commute) → primary `RESEAT_SIM`, secondary `TOGGLE_AIRPLANE_MODE` (force network re-registration), route `SELF_SERVICE`.
- **NO_SERVICE, `line.status == "Suspended"` with `suspension_reason == "OVERDUE_BILL"`** and customer ready to pay → primary `SEND_PAYMENT_REQUEST`, secondary `RESUME_LINE_REBOOT`; `bill_id` = the customer's `Overdue` bill, `charge_amount_usd` = that bill's `amount_due_usd`; route `BILLING_RECOVERY`.
- **MOBILE_DATA, `customer_location == "abroad"`, `phone_roaming_enabled == false`, `line.roaming_enabled == true`** → primary `TOGGLE_ROAMING` (enable phone-side roaming), route `SELF_SERVICE`. (Line already provisioned for roaming; only the device toggle is off.)
- **MMS, `can_send_mms == false`** → primary `GRANT_MESSAGING_PERMISSION`; `permission` = whichever of `sms`/`storage` is `false` (`sms_and_storage` if both false); route `SELF_SERVICE`.
- **SLOW_DATA, `vpn_connected == true`** → primary `DISCONNECT_VPN`; route `SELF_SERVICE`.

Output fields: `case_id, customer_id, line_id, primary_action, secondary_action, permission, bill_id, charge_amount_usd, final_route` + `queue_summary{self_service_fixes, billing_recoveries, carrier_updates, human_transfers}`. Preserve ascending `case_id`. `permission` ∈ `NONE|sms|storage|sms_and_storage`. `bill_id` empty string when not applicable; `charge_amount_usd` 0.00 otherwise.

### Family C — Mobile-data recovery worklist

Per case fetch case → line → device → plan. Decision tree:

- **Data stopped after usage limit**: `line.data_used_gb > plan.data_limit_gb` → primary `REFUEL_DATA`; `data_refuel_gb` = the customer's accepted refuel amount (from `customer_preferences`); `charge_amount_usd` = `data_refuel_gb × plan.data_refueling_price_per_gb` (2 decimals); route `DATA_RECOVERY`; `carrier_update_required=false`.
- **Traveler roaming on phone but no data**: `customer_location=="abroad"`, `phone_roaming_enabled==true`, `line.roaming_enabled==false` → primary `ENABLE_LINE_ROAMING` (carrier must provision line-side roaming); `carrier_update_required=true`; route `CARRIER_UPDATE`; `data_refuel_gb=0.0`, charge `0.00`. (Mirror of Family-B abroad case: there phone toggle was off → `TOGGLE_ROAMING`/SELF_SERVICE; here the line side is off → carrier update.)
- **Slow data, data-saver icon**: `data_saver_mode==true` → primary `TOGGLE_DATA_SAVER`; route `DEVICE_SETTING_FIX`.
- **Slow data, older network mode**: `network_mode_preference` is `3g_only`/non-4g5g → primary `SET_NETWORK_MODE`; route `DEVICE_SETTING_FIX`.
- **No data after settings change**: `mobile_data_enabled==false` → primary `TOGGLE_MOBILE_DATA`; route `DEVICE_SETTING_FIX`.

`secondary_action` = `NO_ACTION` unless a follow-up re-connect step is clearly required. Output fields: `case_id, primary_action, secondary_action, data_refuel_gb, charge_amount_usd, carrier_update_required, final_route` + `worklist_summary{data_refuel_cases, carrier_updates, device_setting_fixes, human_transfers, total_estimated_customer_charge_usd}`. `data_refuel_gb` = `0.0` when not applicable (one decimal). `total_estimated_customer_charge_usd` = sum of all `charge_amount_usd` (typically only the refuel case; carrier/device fixes are free).

`final_route` enum: `DATA_RECOVERY | CARRIER_UPDATE | DEVICE_SETTING_FIX | HUMAN_TRANSFER`.
- `DATA_RECOVERY` = data refuel.
- `CARRIER_UPDATE` = action needs carrier-side provisioning (`ENABLE_LINE_ROAMING` when line roaming off; `carrier_update_required=true`).
- `DEVICE_SETTING_FIX` = a device toggle/setting (mobile data, data saver, network mode, VPN, phone roaming when self-service).
- `HUMAN_TRANSFER` = no automated fix applies (`TRANSFER_HUMAN`).

### Family D — Enterprise export-complaint response package

1. From the complaint email: `incident_id` (e.g. INC-7301), client name, product. Match the client name to `/api/enterprise/accounts` → `enterprise_account_id`, `account_owner`, `finance_owner`. Confirm via `/api/enterprise/incidents` (the incident carries `engineering_owner`, `account_owner`, `severity`, `status`, `product`).
2. `GET /api/enterprise/export-runs?incident_id=<id>`. Build the `failure_window`:
   - `start_date` = first FAILED run `run_date`; `end_date` = last FAILED run `run_date`; `failed_days` = count of FAILED runs.
   - `backfill_days` = `failed_days` (the consecutive failed days requiring/undergoing manual backfill). The first SUCCEEDED run after the streak is the recovery point.
3. `root_cause_category`: infer from the export-run `failure_code` + the matching `/api/enterprise/messages?query=...` evidence (e.g. `STALE_CREDENTIAL` + "scheduler pod still references old secret" message; `STAGING_STORAGE_QUOTA` + "bucket reached quota" message). Concise category string.
4. `contributing_alert_issue` ∈ `ARCHIVED_ALERT_ROUTE | NONE | UNKNOWN`: set `ARCHIVED_ALERT_ROUTE` when a root-cause message was posted to a channel whose name contains `archive` (e.g. `export-alerts-archive`) — the alert was misrouted to a dead channel and slowed detection. Else `NONE` (or `UNKNOWN` if alert routing is unresolved).
5. `sla_credit_percent`: from `/api/ enterprise/sla/<enterprise_account_id>.monthly_export_credit_percent` (cross-check against the account-escalations message that states the contracted credit). Trigger text (e.g. "3 consecutive failed export runs" or "outage longer than 72 hours") is descriptive; the percent is the numeric field.
6. `severity`: copy from the incident record (`Critical`/`High`/`Medium`/`Low`).
7. `engineering_owner`, `account_owner`: copy from the incident record (also on the enterprise account).
8. Constructed artifacts — follow the complaint's `naming_style` requirement EXACTLY (these strings are scored on exact match):
   - `channel_name`: lowercase-hyphen channel name (per `naming_style`).
   - `evidence_folder`: "client-date" investigation folder, e.g. `<client-lowercase-hyphen>-<YYYY-MM-DD>-investigation` (date = incident/failure date).
   - `report_title`: "<Client> Export Failure Report" (per `naming_style`; include "Monthly" when the product is `monthly_export`).
9. `share_permissions`: one entry per user in the complaint's `permission_users_to_include`, ordered as listed. `permission` ∈ `view|edit|upload_only`, assigned by role (finance owner → edit on the financial/SLA section; designated collaborator → upload_only or edit; pure reviewers → view). The exact role→permission mapping is task-specific — read the requirements.
10. `response_status` ∈ `READY_TO_SEND | NEEDS_FINANCE_REVIEW | NEEDS_ENGINEERING_REVIEW | UNDER_INVESTIGATION`: set from what remains open. If an `ARCHIVED_ALERT_ROUTE` contributing issue exists (alerting still broken) or the engineering fix needs verification → `NEEDS_ENGINEERING_REVIEW`. If the SLA credit needs finance sign-off → `NEEDS_FINANCE_REVIEW`. If root cause is still unresolved → `UNDER_INVESTIGATION`. Only `READY_TO_SEND` when all of root cause, backfill, SLA, and owners are confirmed with no open review.

**Pitfall (enterprise):** the constructed strings (`root_cause_category`, `channel_name`, `evidence_folder`, `report_title`), the per-user `permission` values, and `response_status` are the hard part — they require exact matches. Always derive every deterministic field from records (incident, SLA, export-runs) and treat only the constructed strings as needing careful `naming_style` compliance.

## 5. Audit / Summary Formulas

- **batch_summary.RESOLVED/PENDING_ACTION/ESCALATED/FAILED** = counts of per-ticket `final_resolution_status`.
- **batch_summary.tickets_requiring_customer_wait** = count of OUTAGE_WAIT tickets (active-outage gated).
- **queue_summary** status counts as above; team counts = counts of per-ticket `route_team` (NONE entries are not emitted as a summary key).
- **queue_summary (mobile triage)**: `self_service_fixes` + `billing_recoveries` + `carrier_updates` + `human_transfers` = total cases; each case maps 1:1 to its `final_route` (SELF_SERVICE/BILLING_RECOVERY/CARRIER_UPDATE/HUMAN_TRANSFER).
- **worklist_summary.total_estimated_customer_charge_usd** = Σ `charge_amount_usd` over all cases (round to 2 decimals). Only REFUEL_DATA cases normally carry a charge.

## 6. Pitfalls

- **Always substitute the real base URL** for any `127.0.0.1` address in a prompt.
- **Gating before diagnostics.** Account/auth/outage gates make a ticket FAILED or PENDING_ACTION with `diagnostic_needed=false` and all issue flags false — do not compute floors for gated tickets.
- **Outage must match service_type.** An active outage in the service_area only gates the ticket if the ticket's `service_type` is in `outage.service_types`.
- **Auth gate beats status gate.** A `status=Active` account with `account_recovery_status=FAILURE` is AUTH_FAILED, not Active. Conversely, suspended accounts all have `last_login_status=SUCCESS` — the suspension is a status gate, not an auth gate.
- **Flags are PRE, outcome is POST.** `latency_issue/stability_issue/bandwidth_issue` reflect the pre-troubleshoot snapshot; RESOLVED-vs-ESCALATED reflects the post-troubleshoot snapshot. A ticket can have all three pre-flags true yet still be RESOLVED (troubleshooting cleared them).
- **Bandwidth is a ratio, not absolute.** Compare `bandwidth_mbps / subscribed_mbps` to 0.75 — `subscribed_mbps` varies per ticket (100/200/300/500/750).
- **Mirror roaming cases.** Abroad + phone roaming off (line on) → `TOGGLE_ROAMING` (self-service). Abroad + line roaming off (phone on) → `ENABLE_LINE_ROAMING` (carrier update).
- **REFUEL charge uses the LINE's plan price**, not a flat rate: `plan.data_refueling_price_per_gb` × refuel GB (e.g. PLAN-PREMIUM = $2.0/gb).
- **Permission value**: emit `NONE` for non-MMS cases; for MMS emit the specific missing permission (`sms`/`storage`/`sms_and_storage`), not `NONE`.
- **Preserve order**: tickets/cases in payload order; cases ascending by `case_id` when the template says so; `share_permissions` ordered as listed in requirements.
- **Empty strings, not null**: `outage_id=""`, `bill_id=""` when not applicable.
