# SKILL: CRM Support-Console Decision Tasks

## When to use
Use this when a task asks you to act as a support analyst/lead over a **CRM support-console REST API** and emit a structured JSON decision package. Symptoms: a `prompt.txt` plus a `payloads/` folder containing an `answer_template.json` and one input file (CSV ticket/queue batch, JSON case/work queue, or a complaint email + requirements). The work is always: read input rows -> look up live records in the API -> apply deterministic business rules -> emit JSON that exactly matches the template.

There are four task families seen so far:
1. **Offline ticket batch resolution** (CSV of tickets -> `ticket_decisions` + `batch_summary`).
2. **Queue-quality classification before SLA handoff** (CSV of tickets -> `ticket_decisions` with `key_blocker` + `queue_summary`).
3. **Contact-center / mobile case triage** (JSON of cases -> `case_decisions` with device/line/bill actions + `queue_summary`).
4. **Mobile-data recovery worklist** (JSON of cases -> `case_decisions` with refuel/charge + `worklist_summary`).
5. **Enterprise export-complaint response package** (email + requirements -> one flat object).

## API usage habits
Base URL is given in `environment_access.md` and **overrides** any `http://127.0.0.1:8057` in the prompt. Call with `curl -s <base>/<endpoint>`. The API is read-only; it never exposes answers. Confirm reachability with `GET /health` and use `GET /api/catalog` for record counts.

Record types and how to chain them:
- `GET /api/tickets/<ticket_id>` -> `{account_id, service_area, service_type, subscribed_mbps, issue_summary, status}`.
- `GET /api/accounts/<account_id>` -> `{status (Active|Suspended), tier, authentication:{account_recovery_status, last_login_status}}`. A missing account returns `{"error":"not_found"}` -> INVALID_ACCOUNT. **Accounts do NOT carry a suspension reason**; infer overdue-vs-fraud from the ticket note text.
- `GET /api/outages?service_area=<area>` -> array (often `[]`). Take the area from the **ticket** (or account). An outage blocks only if `active == true` AND the ticket's `service_type` is in the outage's `service_types`.
- `GET /api/diagnostics/<ticket_id>` -> pre-fix metrics `{latency_ms, jitter_ms, bandwidth_mbps, root_causes[]}`. May be empty (no body) when none was run.
- `GET /api/troubleshooting/<ticket_id>` -> post-fix `{post_latency_ms, post_jitter_ms, post_bandwidth_mbps, steps[]}`.
- Mobile triage chain: case (`/api/cases/<case_id>`) -> `customer_id`, `line_id`, `device_id`, `issue_type`, `customer_location`. Then `/api/lines/<line_id>` (status, suspension_reason, roaming_enabled, plan_id, data_used_gb), `/api/devices/<device_id>` (the toggle state), `/api/plans/<plan_id>` (data_limit_gb, data_refueling_price_per_gb), `/api/bills` (filter by `customer_id`).
- Enterprise chain: `/api/enterprise/incidents/<id>`, `/api/enterprise/export-runs?incident_id=<id>`, `/api/enterprise/accounts` (filter by id), `/api/enterprise/sla/<enterprise_account_id>`, `/api/enterprise/messages?query=<text>` (search by client name, author, or keyword; querying the incident id often returns nothing - search by client name instead).

General habits: fetch every record an input row references; never assume. Preserve the exact input order of rows. Keep IDs verbatim (case-sensitive). Numbers must match the template's stated precision.

---

## FAMILY 1 - Offline ticket batch resolution
Template fields per ticket: `ticket_id, account_id, final_resolution_status, diagnostic_needed, latency_issue, stability_issue, bandwidth_issue, outage_id, escalation_team, resolution_route`. Plus `batch_summary` counts.

Decision procedure (evaluate gates **in order**; first match wins):
1. **Account missing** (`error:not_found`) -> `resolution_route=INVALID_ACCOUNT`, `final_resolution_status=FAILED`, `escalation_team=NONE`, `outage_id=""`, all issue flags false, `diagnostic_needed=false`.
2. **Auth failure** (`authentication.last_login_status=="FAILURE"` or `account_recovery_status=="FAILURE"`) -> `resolution_route=AUTH_FAILED`, status `FAILED`, team `NONE`, no diagnostics.
3. **Account not Active** (`status=="Suspended"`) -> `resolution_route=INELIGIBLE_ACCOUNT`, status `FAILED` (account-level block), team `NONE`, no diagnostics. (If the family routes billing, suspended-overdue may instead go to ACCOUNTS_PAYABLE - see Family 2 for the distinction; in Family 1 the route enum has INELIGIBLE_ACCOUNT, so use it.)
4. **Active outage matches** (active outage in the ticket's `service_area` whose `service_types` includes the ticket `service_type`) -> `resolution_route=OUTAGE_WAIT`, status `PENDING_ACTION`, `outage_id=<that id>`, team `NONE`, `diagnostic_needed=false`. This ticket counts toward `tickets_requiring_customer_wait`.
5. **Technical issue, auto-fixable** -> read diagnostics + troubleshooting. If `root_causes` are software/config class (CONFIGURATION_DRIFT, VOICE_PROFILE_STALE, PROVISIONING_STALE, GENERATED_NOISE) and post-troubleshooting metrics returned to healthy range -> `resolution_route=AUTO_TROUBLESHOOTING`, status `RESOLVED`, team `NONE`.
6. **Technical issue, NOT auto-fixable** (physical/network root cause that troubleshooting did not clear) -> `resolution_route=ESCALATION`, status `ESCALATED`, pick `escalation_team`:
   - physical line / signal faults (FIBER_DROP_DAMAGE, SIGNAL_LOSS, PHYSICAL_LINE_FAULT) -> `FIELD_OPS`.
   - backbone / capacity (BACKBONE_CAPACITY, NETWORK_CAPACITY) -> `NETWORK_ENGINEERING`.
   - residual config/provisioning needing manual work -> `TIER2_SUPPORT`.
   - billing/overdue when route allows -> `ACCOUNTS_PAYABLE`.

Issue-flag booleans (from the **diagnostics** record, i.e. pre-fix metrics; if no diagnostics ran, all false):
- `latency_issue` = latency_ms is elevated (use > ~100 ms as the threshold; the reported customer issue mentioning latency reinforces it).
- `stability_issue` = jitter_ms elevated (use > ~30 ms) and/or "intermittent/drops" report.
- `bandwidth_issue` = delivered `bandwidth_mbps` materially below `subscribed_mbps` (use < ~80% of subscribed).
- These thresholds are inferred from limited samples; cross-check against the customer's reported symptom wording and the diagnostics `root_causes`.
- `diagnostic_needed`: true when a diagnostic is the determining technical step for an eligible/active account with a technical complaint (i.e. routes AUTO_TROUBLESHOOTING or ESCALATION). false for INVALID_ACCOUNT, AUTH_FAILED, INELIGIBLE_ACCOUNT, and OUTAGE_WAIT (the blocker is non-technical / already known).

`outage_id` = the matching active outage id, else `""` (empty string, never null).

`batch_summary`: count statuses across the decisions (`RESOLVED, PENDING_ACTION, ESCALATED, FAILED` integers) and `tickets_requiring_customer_wait` = number of OUTAGE_WAIT (PENDING_ACTION on outage) tickets. The four status counts must sum to the number of tickets.

---

## FAMILY 2 - Queue-quality classification (pre-SLA handoff)
Template per ticket: `ticket_id, final_resolution_status, route_team, key_blocker, diagnostic_required`. Plus `queue_summary` with status counts AND per-team counts.

`key_blocker` enum and how to choose (first match wins, same gate order as Family 1):
- `INVALID_ACCOUNT` - account id not found.
- `AUTH_FAILED` - authentication failure on the account.
- `OVERDUE_SUSPENSION` - account Suspended and ticket note mentions overdue/billing/payment.
- `FRAUD_SUSPENSION` - account Suspended and ticket note mentions fraud/abuse/security hold.
- `ACTIVE_OUTAGE` - matching active outage for service_area + service_type.
- `NETWORK_CAPACITY` - diagnostics root cause BACKBONE_CAPACITY / capacity, troubleshooting did not clear.
- `PHYSICAL_LINE_FAULT` - FIBER_DROP_DAMAGE / SIGNAL_LOSS / physical line.
- `PROVISIONING_STALE` - PROVISIONING_STALE root cause still needing manual provisioning (Tier2) - but if a `PROVISIONING_ADJUSTMENT` troubleshooting step restored healthy metrics, it is RESOLVED with `NONE`.
- `NONE` - resolved cleanly, no blocker.

`route_team` mapping:
- INVALID_ACCOUNT / AUTH_FAILED / clean RESOLVED -> `NONE`.
- ACTIVE_OUTAGE -> `NONE` (wait, not a team handoff).
- OVERDUE_SUSPENSION / FRAUD_SUSPENSION -> `ACCOUNTS_PAYABLE`.
- PHYSICAL_LINE_FAULT -> `FIELD_OPS`.
- NETWORK_CAPACITY -> `NETWORK_ENGINEERING`.
- PROVISIONING_STALE / residual config needing manual work -> `TIER2_SUPPORT`.

`final_resolution_status`:
- `FAILED` for INVALID_ACCOUNT, AUTH_FAILED (cannot proceed).
- `PENDING_ACTION` for ACTIVE_OUTAGE (and for suspensions awaiting customer/billing action - judge by note; overdue suspensions that need a team handoff are typically `ESCALATED` to ACCOUNTS_PAYABLE).
- `ESCALATED` for PHYSICAL_LINE_FAULT, NETWORK_CAPACITY, PROVISIONING_STALE that was not auto-cleared, and team-routed suspensions.
- `RESOLVED` when troubleshooting cleared an auto-fixable root cause (VOICE_PROFILE_STALE+VOICE_PROFILE_REFRESH, CONFIGURATION_DRIFT, GENERATED_NOISE, cleared PROVISIONING_STALE).

`diagnostic_required`: true only when a technical diagnostic is the determining next step for an Active, authenticated account (escalation/auto-fix paths). false for INVALID_ACCOUNT, AUTH_FAILED, suspensions, and ACTIVE_OUTAGE.

`queue_summary`: emit integer counts for each status (`FAILED, PENDING_ACTION, RESOLVED, ESCALATED`) and for each team actually used (`TIER2_SUPPORT, FIELD_OPS, NETWORK_ENGINEERING, ACCOUNTS_PAYABLE`). Status counts sum to ticket count; team counts sum to the number of tickets whose `route_team != NONE`.

### Auto-fixable vs escalate cheat-sheet (Families 1 & 2)
| root_cause | typical troubleshooting step | outcome | team |
|---|---|---|---|
| CONFIGURATION_DRIFT | PROFILE_REFRESH / PROVISIONING_SYNC | RESOLVED | NONE |
| VOICE_PROFILE_STALE | VOICE_PROFILE_REFRESH | RESOLVED | NONE |
| PROVISIONING_STALE | PROVISIONING_ADJUSTMENT | RESOLVED if metrics recover | NONE / else TIER2 |
| GENERATED_NOISE | GENERATED_CHECK | RESOLVED (benign) | NONE |
| FIBER_DROP_DAMAGE / SIGNAL_LOSS | LINE_TEST / SIGNAL_REFRESH (does NOT clear) | ESCALATED | FIELD_OPS |
| BACKBONE_CAPACITY | BACKBONE_REROUTE_ATTEMPT (does NOT clear) | ESCALATED | NETWORK_ENGINEERING |

"Recovered" = post_latency_ms back near/under ~100 and post metrics close to subscribed. Physical/backbone cases stay high (post_latency ~170-200) -> escalate. **Root-cause class is the primary signal; post-metrics confirm it.**

---

## FAMILY 3 - Contact-center / mobile case triage
Template per case: `case_id, customer_id, line_id, primary_action, secondary_action, permission, bill_id, charge_amount_usd, final_route`. Plus `queue_summary`. **Order cases by ascending case_id.**

For each case: fetch case -> line -> device -> (bill if billing) -> plan (if data cap). Diagnose from the device/line state, not the prose:
- `issue_type=NO_SERVICE`:
  - device `sim_status=="missing"` -> `RESEAT_SIM` (SELF_SERVICE).
  - device `airplane_mode==true` -> `TOGGLE_AIRPLANE_MODE`.
  - line `status=="Suspended"` with `suspension_reason=="OVERDUE_BILL"` and customer willing to pay -> primary `SEND_PAYMENT_REQUEST`, secondary `RESUME_LINE_REBOOT`; set `bill_id` to the customer's Overdue bill and `charge_amount_usd` to its `amount_due_usd`; route `BILLING_RECOVERY`.
- `issue_type=MOBILE_DATA`:
  - device `mobile_data_enabled==false` -> `TOGGLE_MOBILE_DATA`.
  - location `abroad` and device `phone_roaming_enabled==false` -> `TOGGLE_ROAMING`; if the **line** `roaming_enabled==false` -> `ENABLE_LINE_ROAMING` (carrier-side); route `CARRIER_UPDATE`.
  - over data cap (`line.data_used_gb > plan.data_limit_gb`) -> `REFUEL_DATA` (see Family 4 for charge).
- `issue_type=SLOW_DATA`:
  - device `vpn_connected==true` -> `DISCONNECT_VPN`.
  - device `data_saver_mode==true` -> `TOGGLE_DATA_SAVER`.
  - device `network_mode_preference` is a legacy/old mode (e.g. `3g_only`) -> `SET_NETWORK_MODE`.
- `issue_type=MMS`:
  - `can_send_mms==false` and `messaging_permissions.storage==false` -> `GRANT_MESSAGING_PERMISSION` with `permission="storage"`.
  - if both sms and storage are missing -> `permission="sms_and_storage"`; only sms missing -> `permission="sms"`.
- Nothing actionable / contradictory / needs an agent -> `TRANSFER_HUMAN`, route `HUMAN_TRANSFER`.

`secondary_action`: the required follow-up (e.g. `RESUME_LINE_REBOOT` after a payment request, or a reboot after a SIM reseat). Use `NO_ACTION` when none is needed.

`permission`: `NONE` unless the action is GRANT_MESSAGING_PERMISSION; then `sms`, `storage`, or `sms_and_storage` matching the missing flags.

`bill_id` / `charge_amount_usd`: empty string / `0.00` unless billing applies. When billing applies, `charge_amount_usd` = the bill's `amount_due_usd` formatted to **two decimals**.

`final_route` mapping: device-setting fixes (RESEAT_SIM, TOGGLE_*, DISCONNECT_VPN, GRANT_MESSAGING_PERMISSION, SET_NETWORK_MODE) -> `SELF_SERVICE`; payment/suspension -> `BILLING_RECOVERY`; roaming/carrier -> `CARRIER_UPDATE`; agent needed -> `HUMAN_TRANSFER`.

`queue_summary`: `self_service_fixes, billing_recoveries, carrier_updates, human_transfers` = counts of each `final_route`. They sum to the case count.

---

## FAMILY 4 - Mobile-data recovery worklist
Template per case: `case_id, primary_action, secondary_action, data_refuel_gb, charge_amount_usd, carrier_update_required, final_route`. Plus `worklist_summary`. **Order by ascending case_id.** Read `customer_preferences` in the worklist for per-case refuel acceptance / plan-change constraints.

Action selection (device/line state, same logic as Family 3 data/slow rules):
- over data cap (`data_used_gb > plan.data_limit_gb`, device `speed_test=="no_connection"`) -> `REFUEL_DATA`. `data_refuel_gb` = the customer's `accepted_refuel_gb` from preferences (one decimal); `charge_amount_usd` = `data_refuel_gb * plan.data_refueling_price_per_gb`, two decimals. Honor `does_not_want_plan_change=true` (refuel, do not switch plan). Route `DATA_RECOVERY`.
- abroad, **line** `roaming_enabled==false` while phone roaming on -> `ENABLE_LINE_ROAMING`, `carrier_update_required=true`, route `CARRIER_UPDATE`.
- `data_saver_mode==true` -> `TOGGLE_DATA_SAVER`, route `DEVICE_SETTING_FIX`.
- legacy `network_mode_preference` (`3g_only`) with slow speed -> `SET_NETWORK_MODE`, route `DEVICE_SETTING_FIX`.
- `mobile_data_enabled==false` -> `TOGGLE_MOBILE_DATA`, route `DEVICE_SETTING_FIX`.
- `vpn_connected==true` slow -> `DISCONNECT_VPN`, route `DEVICE_SETTING_FIX`.
- nothing actionable -> `TRANSFER_HUMAN`, route `HUMAN_TRANSFER`.

Defaults: `data_refuel_gb=0.0`, `charge_amount_usd=0.00`, `carrier_update_required=false`, `secondary_action=NO_ACTION` unless applicable.

`worklist_summary`: `data_refuel_cases, carrier_updates, device_setting_fixes, human_transfers` (route counts) and `total_estimated_customer_charge_usd` = sum of all `charge_amount_usd`, two decimals.

---

## FAMILY 5 - Enterprise export-complaint response package
Output is ONE flat object (not a list). Steps:
1. Identify the incident: the email gives an `INC-...` reference and client name. `GET /api/enterprise/incidents/<id>` -> `enterprise_account_id, engineering_owner, account_owner, product, severity, status`.
2. `GET /api/enterprise/export-runs?incident_id=<id>` -> the consecutive `FAILED` runs define the **failure window**. `start_date` = first FAILED `run_date`, `end_date` = last FAILED `run_date`, `failed_days` = count of FAILED runs. The first `SUCCEEDED` run after them is the recovery (not part of the window).
3. `root_cause_category`: derive a concise category from the FAILED runs' `failure_code` plus corroborating message body (e.g. STALE_CREDENTIAL + "scheduler pod still references old secret" -> "stale credential / rotated secret not picked up"; STAGING_STORAGE_QUOTA + "bucket reached quota" -> "staging storage quota exceeded"). Keep it short and grounded in evidence.
4. `contributing_alert_issue`: `ARCHIVED_ALERT_ROUTE` if an alert/message about the failure landed in an **archived** channel (e.g. channel name contains `archive`, so nobody was paged); `NONE` if alerting was fine; `UNKNOWN` if evidence is insufficient.
5. `backfill_days`: number of failed days that need manual backfill = `failed_days` (messages often state it explicitly, e.g. "four days require manual backfill"). Trust the explicit message number if present.
6. `sla_credit_percent`: integer from `GET /api/enterprise/sla/<enterprise_account_id>` (`monthly_export_credit_percent`), corroborated by the escalation message. Confirm the `credit_trigger` was met (e.g. "3 consecutive failed runs" with 3 failed days; ">72 hours" with 4 failed days).
7. `severity`: from the incident record (and email subject). Critical | High | Medium | Low.
8. `engineering_owner` / `account_owner`: from the incident record (user ids like `delana.rao`, `stephany.lo`). `finance_owner` comes from the enterprise account record (used for share permissions/review).
9. Naming artifacts - follow the `naming_style` in `response_requirements.json` exactly:
   - `channel_name`: lowercase hyphenated, derived from client + topic (e.g. `asteri-retail-export-failure`).
   - `evidence_folder`: client-date investigation folder (e.g. `asteri-retail-2026-05-15-investigation`); use the relevant incident/recovery date.
   - `report_title`: human-readable "client export failure report" (e.g. `Asteri Retail Inc. Export Failure Report`).
   - Match casing/format to the requirement description; these strings are exact-match scored, so mirror the stated style precisely.
10. `share_permissions`: include exactly the users in `permission_users_to_include`, **in that listed order**. Choose `permission` by role: finance/account reviewers -> `view`; engineering/contributors who add evidence -> `edit` or `upload_only` (use `upload_only` for evidence-drop-only roles). Default a finance owner reviewing a credit to `view`.
11. `response_status`: `UNDER_INVESTIGATION` if the incident is still open and unverified; `NEEDS_FINANCE_REVIEW` when an SLA credit must be signed off by finance; `NEEDS_ENGINEERING_REVIEW` when root cause/backfill awaits engineering confirmation; `READY_TO_SEND` only when window, root cause, backfill, credit, and owners are all confirmed. When a credit is owed and finance is a listed reviewer, prefer `NEEDS_FINANCE_REVIEW`.

---

## Common misjudgments / exclusion rules
- **Do NOT escalate** an account-level block (invalid / auth-failed / suspended / active-outage). Those are FAILED or PENDING_ACTION with team `NONE` (suspensions route to ACCOUNTS_PAYABLE only where billing handoff is the intended action). Escalation teams are for *technical* faults on otherwise-eligible accounts.
- **Do NOT mark `diagnostic_needed`/`diagnostic_required` true** for invalid/auth/suspended/outage tickets - the blocker is non-technical, so a diagnostic is pointless.
- **Do NOT treat an inactive outage as a blocker.** Require `active==true` AND service_type membership in the outage's `service_types`.
- **Do NOT infer account suspension reason from the account record** (it has none) - read the ticket note text (overdue vs fraud).
- **Do NOT auto-resolve a physical/backbone fault** just because a troubleshooting step ran; check that post-metrics actually recovered. GENERATED_NOISE is benign/synthetic and resolves; FIBER/SIGNAL/BACKBONE do not.
- **Do NOT reorder rows.** Ticket families preserve payload order; case families sort ascending by case_id; enterprise share_permissions follow the requirements list order.
- **Do NOT include extra users** in share_permissions beyond `permission_users_to_include`.
- **Do NOT switch a customer's plan** when they accepted a refuel and set `does_not_want_plan_change=true`.
- **Empty vs null**: use `""` for empty strings (e.g. `outage_id`, `bill_id`) and `0.0`/`0.00` for unused numbers - never `null`.
- **Charge precision**: two decimals for USD (`charge_amount_usd`), one decimal for `data_refuel_gb`.
- The first SUCCEEDED export run is recovery evidence, NOT part of the failure window or failed-day count.

## Output-format discipline
- Return **only** JSON conforming to the task's `answer_template.json` - no prose, no markdown fences, no extra keys.
- Reproduce enum spellings EXACTLY as in the template (e.g. `PENDING_ACTION`, `ACCOUNTS_PAYABLE`, `NETWORK_ENGINEERING`, `SELF_SERVICE`, `READY_TO_SEND`).
- Copy IDs verbatim (case-sensitive). Booleans are JSON `true`/`false`.
- Summary integer counts must reconcile with the per-row decisions (statuses sum to row count; route/team counts sum to rows routed).
- Re-read the template field descriptions before emitting; several fields specify ordering, precision, or "empty when not applicable" - honor each literally.
