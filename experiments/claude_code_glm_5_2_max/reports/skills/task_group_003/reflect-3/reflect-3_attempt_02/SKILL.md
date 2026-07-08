# SC003 CRM Support Operations Analyst

Resolve support-console operations across three task families using the shared support console API.
This is a train-only reflect skill: it contains reusable RULES only (no task answers, no judge hooks).

## 0. Environment & API map

Base URL (always use this; ignore any `127.0.0.1` URL in prompts):
`<remote-env-url>`

- `GET /health` -> `{"ok": true}`
- `GET /api/catalog` -> endpoint list + record counts (public).
- Accounts/tickets:
  - `GET /api/accounts`, `GET /api/accounts/<account_id>`
  - `GET /api/tickets`, `GET /api/tickets/<ticket_id>`
  - `GET /api/outages?service_area=<area>` (list; filter client-side by `active==true` and `service_type` membership)
  - `GET /api/diagnostics/<ticket_id>`
  - `GET /api/troubleshooting/<ticket_id>`
- Mobile:
  - `GET /api/customers`, `GET /api/lines`, `GET /api/lines/<line_id>`
  - `GET /api/devices/<device_id>`, `GET /api/plans/<plan_id>`
  - `GET /api/bills`, `GET /api/cases`, `GET /api/cases/<case_id>`
- Enterprise:
  - `GET /api/enterprise/accounts`, `GET /api/enterprise/incidents`
  - `GET /api/enterprise/export-runs?incident_id=<incident_id>`
  - `GET /api/enterprise/messages?query=<text>` (substring search over body/author/channel)
  - `GET /api/enterprise/sla/<enterprise_account_id>`

Records are the source of truth. Never assume fields; always probe per id. Floating-point/heuristic
"GENERATED_*" values in diagnostics/troubleshooting are decoy filler for tickets that are gated before
diagnostics run — they are not used in decisions.

---

## 1. Ticket family SOP (offline-service ticket batch & queue review)

Applies to per-ticket classification tasks (template has `ticket_decisions` + a summary).
Two variants exist with different per-ticket field sets; the gating logic is identical.

### 1.1 Converged floors (EXACT)

| metric | floor | violation rule |
|---|---|---|
| bandwidth | `0.90 * subscribed_mbps` | `bandwidth_issue` / bandwidth violated iff `bandwidth_mbps < 0.90*subscribed_mbps` |
| latency | `100 ms` (absolute) | `latency_issue` iff `latency_ms > 100` |
| jitter | `25 ms` (absolute) | `stability_issue` iff `jitter_ms > 25` |

- Bandwidth floor is a RATIO of the ticket's `subscribed_mbps` (probe `/api/tickets/<id>`).
- Latency and jitter floors are ABSOLUTE (same for all service types).
- Rationale for 0.90: train "barely resolves" cases clear the floor by ~2-3 Mbps at exactly 90%
  (e.g. post bw 272 vs 0.90*300=270; post bw 93 vs 0.90*100=90). 0.85 also passes train but 0.90
  is the design value.
- Pre-troubleshooting values = `/api/diagnostics/<id>` fields `bandwidth_mbps`, `latency_ms`, `jitter_ms`.
- Post-troubleshooting values = `/api/troubleshooting/<id>` fields `post_bandwidth_mbps`, `post_latency_ms`, `post_jitter_ms`.

### 1.2 Gating order (evaluate top-down; first match wins)

1. **Account/auth gate -> FAILED, no diagnostics.**
   - `GET /api/accounts/<account_id>`. If `account_id` not found -> `INVALID_ACCOUNT`.
   - If `authentication.last_login_status != "SUCCESS"` (or `account_recovery_status=="FAILURE"`) -> `AUTH_FAILED`.
   - If `status != "Active"` (e.g. `Suspended`): this is an account gate -> FAILED. The `key_blocker`
     is `OVERDUE_SUSPENSION` when the report/note says overdue/billing; `FRAUD_SUSPENSION` for fraud.
     The owning team is `ACCOUNTS_PAYABLE` for overdue/billing suspension; `NONE` for invalid/fraud/auth.
2. **Active outage gate -> PENDING_ACTION (outage-wait), no diagnostics.**
   - `GET /api/outages?service_area=<ticket.service_area>`. If any `active==true` outage exists AND
     the ticket's `service_type` is in `outage.service_types` -> outage-wait. Record `outage_id`.
3. **Diagnostics + troubleshooting (passes both gates).**
   - Compute pre flags from diagnostics vs floors (bandwidth_issue / latency_issue / stability_issue).
   - Compute post clearance from troubleshooting vs floors.
   - If ALL post metrics clear floors -> `RESOLVED` via `AUTO_TROUBLESHOOTING`, escalation team `NONE`.
   - Else -> `ESCALATED` via `ESCALATION`, escalation team from diagnostics `root_causes` (see 1.4).

`diagnostic_needed` / `diagnostic_required` = `true` for RESOLVED and ESCALATED (diagnostics were
needed to decide); `false` for any gated ticket (outage/invalid/auth/suspended).

### 1.3 Per-variant output fields

**Batch variant** (`answer_template.ticket_decisions[]`): `ticket_id`, `account_id`,
`final_resolution_status` (RESOLVED|PENDING_ACTION|ESCALATED|FAILED), `diagnostic_needed` (bool),
`latency_issue` / `stability_issue` / `bandwidth_issue` (pre-troubleshooting floor violations; all
`false` for gated tickets), `outage_id` (empty string unless outage-wait),
`escalation_team` (NONE|TIER2_SUPPORT|FIELD_OPS|NETWORK_ENGINEERING|ACCOUNTS_PAYABLE),
`resolution_route` (AUTO_TROUBLESHOOTING|OUTAGE_WAIT|ESCALATION|INELIGIBLE_ACCOUNT|AUTH_FAILED).
- `resolution_route` mapping: RESOLVED->AUTO_TROUBLESHOOTING; outage-wait->OUTAGE_WAIT; ESCALATED->ESCALATION;
  INVALID_ACCOUNT->INELIGIBLE_ACCOUNT; AUTH_FAILED->AUTH_FAILED; suspended account->INELIGIBLE_ACCOUNT.
- `escalation_team` = NONE for RESOLVED and all gated tickets EXCEPT overdue-suspension which uses
  ACCOUNTS_PAYABLE (see 1.4/1.5).
- `batch_summary`: `{RESOLVED, PENDING_ACTION, ESCALATED, FAILED, tickets_requiring_customer_wait}`.
  `tickets_requiring_customer_wait` = count of OUTAGE_WAIT tickets.

**Queue variant** (`answer_template.ticket_decisions[]`): `ticket_id`, `final_resolution_status`,
`route_team` (NONE|TIER2_SUPPORT|FIELD_OPS|NETWORK_ENGINEERING|ACCOUNTS_PAYABLE),
`key_blocker` (NONE|ACTIVE_OUTAGE|INVALID_ACCOUNT|AUTH_FAILED|OVERDUE_SUSPENSION|FRAUD_SUSPENSION|
NETWORK_CAPACITY|PROVISIONING_STALE|PHYSICAL_LINE_FAULT), `diagnostic_required` (bool).
- `route_team` = escalation team for ESCALATED tickets; for gated tickets: OVERDUE_SUSPENSION->
  ACCOUNTS_PAYABLE; ACTIVE_OUTAGE/INVALID_ACCOUNT/AUTH_FAILED/FRAUD_SUSPENSION->NONE; RESOLVED->NONE.
- `key_blocker`: ACTIVE_OUTAGE (outage-wait); INVALID_ACCOUNT; AUTH_FAILED; OVERDUE_SUSPENSION;
  FRAUD_SUSPENSION; NETWORK_CAPACITY (BACKBONE_CAPACITY root cause); PROVISIONING_STALE
  (PROVISIONING_STALE root cause); PHYSICAL_LINE_FAULT (fiber/signal drop); NONE (RESOLVED).
- `queue_summary`: `{FAILED, PENDING_ACTION, RESOLVED, ESCALATED, TIER2_SUPPORT, FIELD_OPS,
  NETWORK_ENGINEERING, ACCOUNTS_PAYABLE}`. Status counts count every ticket. Team counts count only
  tickets with that non-NONE `route_team` (do NOT count NONE).

### 1.4 Root-cause -> team map (from `/api/diagnostics/<id>.root_causes`)

Scan each root_cause string (case-insensitive substring):
- contains `fiber` or `signal` -> `FIELD_OPS` (key_blocker `PHYSICAL_LINE_FAULT`)
- contains `backbone` or `capacity` -> `NETWORK_ENGINEERING` (key_blocker `NETWORK_CAPACITY`)
- contains `provisioning` -> `TIER2_SUPPORT` (key_blocker `PROVISIONING_STALE`)
- contains `billing` -> `ACCOUNTS_PAYABLE`
- otherwise (e.g. CONFIGURATION_DRIFT, VOICE_PROFILE_STALE, GENERATED_NOISE) -> no team. Such tickets
  are designed to RESOLVE via auto-troubleshooting (their post metrics clear). If a no-team root cause
  ticket does NOT clear floors (should not happen by design), it still ESCALATED with team NONE.

### 1.5 Account-gate -> team nuance (IMPORTANT, learned via feedback)

- `INVALID_ACCOUNT` (account not_found) -> status FAILED, route_team/escalation_team NONE.
- `AUTH_FAILED` (auth failure) -> status FAILED, team NONE.
- `OVERDUE_SUSPENSION` (account Suspended + overdue/billing context) -> status **FAILED** (it is an
  account gate, *not* PENDING_ACTION) but route_team/escalation_team **ACCOUNTS_PAYABLE** (billing owns
  recovery). This is the one gated status that carries a non-NONE team.
- `FRAUD_SUSPENSION` -> status FAILED, team NONE (or ACCOUNTS_PAYABLE if billing-dispute; default NONE).
- Generic non-overdue account hold/suspension -> FAILED, team NONE, route INELIGIBLE_ACCOUNT.
- ACTIVE_OUTAGE -> status PENDING_ACTION, team NONE, route OUTAGE_WAIT.

### 1.6 Ticket pitfalls

- An account can be `Active` with `authentication.last_login_status == "FAILURE"` -> that is AUTH_FAILED
  (check BOTH account.status AND authentication).
- Outage must be `active==true` AND include the ticket's `service_type` in `service_types`.
- For gated tickets, all three issue flags are `false` (no diagnostics run).
- `outage_id` is empty string `""` for every non-outage ticket.
- Do not run the floor check on GENERATED_* decoy values from gated tickets.

---

## 2. Mobile triage SOP (contact-center queue, full mobile)

Template: `case_decisions[]` with `case_id`, `customer_id`, `line_id`, `primary_action`,
`secondary_action` (same enum as primary), `permission` (NONE|sms|storage|sms_and_storage),
`bill_id` (empty unless billing), `charge_amount_usd` (2 decimals), `final_route`
(SELF_SERVICE|BILLING_RECOVERY|CARRIER_UPDATE|HUMAN_TRANSFER). Plus `queue_summary`
{self_service_fixes, billing_recoveries, carrier_updates, human_transfers}.

Inputs: `payloads/case_queue.json` (cases). Resolve via `/api/cases/<case_id>` ->
`customer_id`, `line_id`, `device_id`, `issue_type`, `customer_location`. Then `/api/lines/<line_id>`,
`/api/devices/<device_id>`, `/api/plans/<plan_id>`, `/api/bills` (filter by customer_id).

### 2.1 Mobile decision tree (primary_action)

- `sim_status == "missing"` -> **RESEAT_SIM** (SELF_SERVICE)
- `line.status == "Suspended"` and customer ready to pay overdue -> **SEND_PAYMENT_REQUEST** (BILLING_RECOVERY);
  `bill_id` = the customer's `Overdue` bill id, `charge_amount_usd` = that bill's `amount_due_usd`.
- customer_location `abroad` (or traveling) + no data:
  - `device.phone_roaming_enabled == false` -> **TOGGLE_ROAMING** (turn device roaming on; SELF_SERVICE)
  - `device.phone_roaming_enabled == true` AND `line.roaming_enabled == false` -> **ENABLE_LINE_ROAMING**
    (carrier must provision line roaming; CARRIER_UPDATE). [If line already enabled but device off, use TOGGLE_ROAMING.]
- `issue_type == "MMS"` / messaging cannot send photos: `device.can_send_mms == false`:
  - if `messaging_permissions.storage == false` -> **GRANT_MESSAGING_PERMISSION** with `permission="storage"`
    (or `sms_and_storage`/`sms` matching whichever perm is missing; set `permission` to the perm(s) being granted)
- slow data:
  - `device.vpn_connected == true` -> **DISCONNECT_VPN** (SELF_SERVICE)
  - otherwise if signal good but still slow, consider data-saver / network mode (see mobile-data SOP)
- unable to self-serve / hardware fault / unknown -> **TRANSFER_HUMAN** (HUMAN_TRANSFER)

### 2.2 secondary_action

- `NO_ACTION` for all self-service device fixes (RESEAT_SIM, TOGGLE_ROAMING, GRANT_MESSAGING_PERMISSION,
  DISCONNECT_VPN, etc.).
- `RESUME_LINE_REBOOT` is the REQUIRED follow-up ONLY for `SEND_PAYMENT_REQUEST` (after payment, resume
  line and reboot). This is the only non-NO_ACTION secondary in this family.
- Never invent airplane-mode/APN follow-ups; the device auto-registers.

### 2.3 permission / bill / charge / route

- `permission`: `NONE` except when `primary_action == GRANT_MESSAGING_PERMISSION` -> set to the missing
  permission(s): `storage` if only storage missing, `sms` if only sms missing, `sms_and_storage` if both.
- `bill_id` / `charge_amount_usd`: only for BILLING_RECOVERY (overdue bill). Empty string / 0.00 otherwise.
- `final_route`: SELF_SERVICE for device toggles/reseat/permission/vpn; BILLING_RECOVERY for payment;
  CARRIER_UPDATE for line-roaming carrier provisioning; HUMAN_TRANSFER for TRANSFER_HUMAN.
- `queue_summary`: count by `final_route`.

---

## 3. Mobile-data recovery SOP (mobile-data worklist)

Template: `case_decisions[]` with `case_id`, `primary_action`, `secondary_action`,
`data_refuel_gb` (1 decimal; 0.0 when N/A), `charge_amount_usd` (2 decimals), `carrier_update_required`
(bool), `final_route` (DATA_RECOVERY|CARRIER_UPDATE|DEVICE_SETTING_FIX|HUMAN_TRANSFER). Plus
`worklist_summary` {data_refuel_cases, carrier_updates, device_setting_fixes, human_transfers,
total_estimated_customer_charge_usd}.

Inputs: `payloads/mobile_data_worklist.json` (cases + `customer_preferences` map with
`accepted_refuel_gb`, `does_not_want_plan_change`). Resolve via `/api/cases`, `/api/lines`,
`/api/devices`, `/api/plans`.

### 3.1 Mobile-data decision tree (primary_action)

- Data cap exceeded (`line.data_used_gb > plan.data_limit_gb`) and customer `accepted_refuel_gb` present
  and `does_not_want_plan_change == true` -> **REFUEL_DATA**, `data_refuel_gb = accepted_refuel_gb`,
  `charge_amount_usd = accepted_refuel_gb * plan.data_refueling_price_per_gb`, route DATA_RECOVERY.
  (Use the customer-accepted refuel amount, NOT the data overage.)
- abroad + phone_roaming ON + `line.roaming_enabled == false` -> **ENABLE_LINE_ROAMING**,
  `carrier_update_required = true`, route CARRIER_UPDATE.
- `device.data_saver_mode == true` + slow data -> **TOGGLE_DATA_SAVER**, route DEVICE_SETTING_FIX.
- `device.network_mode_preference` is old/limited (e.g. `3g_only`) + slow data -> **SET_NETWORK_MODE`,
  route DEVICE_SETTING_FIX.
- `device.mobile_data_enabled == false` -> **TOGGLE_MOBILE_DATA** (turn on), route DEVICE_SETTING_FIX.
- `device.vpn_connected == true` + slow data -> **DISCONNECT_VPN**, route DEVICE_SETTING_FIX.
- Cannot self-serve -> **TRANSFER_HUMAN**, route HUMAN_TRANSFER.

### 3.2 Fields

- `secondary_action`: `NO_ACTION` for all (this family has no billing-recovery follow-up).
- `data_refuel_gb`: 0.0 for every non-refuel case; the accepted refuel GB for REFUEL_DATA.
- `charge_amount_usd`: 0.00 except REFUEL_DATA (= refuel_gb * price_per_gb). Two decimals.
- `carrier_update_required`: `true` ONLY for ENABLE_LINE_ROAMING; false otherwise.
- `worklist_summary.total_estimated_customer_charge_usd` = sum of all `charge_amount_usd` (2 decimals).
- Counts: data_refuel_cases (REFUEL_DATA), carrier_updates (CARRIER_UPDATE route),
  device_setting_fixes (DEVICE_SETTING_FIX route), human_transfers (HUMAN_TRANSFER route).

---

## 4. Enterprise package SOP (export-failure response)

Template (single object, not a list): `incident_id`, `enterprise_account_id`, `root_cause_category`,
`contributing_alert_issue` (ARCHIVED_ALERT_ROUTE|NONE|UNKNOWN), `failure_window` {start_date, end_date,
failed_days}, `backfill_days`, `sla_credit_percent`, `severity` (Critical|High|Medium|Low),
`engineering_owner`, `account_owner`, `channel_name`, `evidence_folder`, `report_title`,
`share_permissions` [{user, permission:view|edit|upload_only}], `response_status`
(READY_TO_SEND|NEEDS_FINANCE_REVIEW|NEEDS_ENGINEERING_REVIEW|UNDER_INVESTIGATION).

Inputs: `payloads/client_complaint_email.txt` (client name, product, ~incident ref) and
`payloads/response_requirements.json` (`required_fields`, `permission_users_to_include` list,
`naming_style`).

### 4.1 Resolve incident (API)

- `GET /api/enterprise/incidents` -> match by `incident_id` (from email "approximate incident reference")
  or by client name in `summary` and `product`. Gives `incident_id`, `enterprise_account_id`, `severity`,
  `engineering_owner`, `account_owner`, `status`, `product`.
- `GET /api/enterprise/accounts` -> confirm `enterprise_account_id`, `account_owner`, `finance_owner`.
- `GET /api/enterprise/export-runs?incident_id=<incident_id>` -> list of runs with `run_date`, `status`
  (FAILED/SUCCEEDED), `failure_code`, `exported_record_count`.
- `GET /api/enterprise/sla/<enterprise_account_id>` -> `monthly_export_credit_percent` (= sla_credit_percent),
  `credit_trigger` text.
- `GET /api/enterprise/messages?query=<client-name>` and `query=<failure_code>` and `query=alert` ->
  evidence messages (author, channel, body).

### 4.2 Audit formulas (solid, evidence-backed)

- `failure_window.start_date` = run_date of the FIRST `status==FAILED` run.
- `failure_window.end_date` = run_date of the LAST `status==FAILED` run.
- `failure_window.failed_days` = count of `status==FAILED` runs.
- `backfill_days` = `failed_days` (each failed run day needs manual backfill). Equals the number of
  consecutive failed days.
- `sla_credit_percent` = `sla.monthly_export_credit_percent` (confirmed by an account-escalations message).
- `severity` = `incident.severity`.
- `engineering_owner` = `incident.engineering_owner`. `account_owner` = `incident.account_owner`
  (== `enterprise/account.account_owner`).
- `root_cause_category` = concise category inferred from the FAILED run `failure_code` AND the root-cause
  message body (e.g. failure_code `STALE_CREDENTIAL` + message "scheduler pod still references old secret"
  -> a stale-credential / stale-secret category).
- `contributing_alert_issue` = `ARCHIVED_ALERT_ROUTE` when the root-cause/alert message's `channel`
  contains "archive" (alert was routed to an archived, unmonitored channel); else `NONE`; `UNKNOWN` if
  no alert evidence.

### 4.3 Naming artifacts (apply `response_requirements.naming_style` precisely)

`naming_style` = "lowercase hyphen channel; client-date investigation folder; client export failure
report title". Construct per the client slug used in the data (run-ids and message bodies, e.g. "Asteri"):
- `channel_name`: a lowercase-hyphen channel name (the response/coordination channel for this client).
- `evidence_folder`: `<client-slug>-<date>` investigation folder (date = failure_window.start_date).
- `report_title`: `<Client> Export Failure Report` style title.
These exact strings must match the judge; build them mechanically from the client slug + dates using the
convention above. (Exact capitalization/slug form was not fully pinned in train — derive consistently
from the client's short name as it appears in messages/run-ids.)

### 4.4 share_permissions

- One entry per user in `response_requirements.permission_users_to_include`, IN THAT ORDER.
- `permission` by role: `finance_owner` (from `/api/enterprise/accounts`) -> reviewer permission
  (edit/view); engineering/evidence provider -> upload_only; account_owner -> view/edit.
  Assign each listed user a permission consistent with their role. (Exact role->permission mapping was
  not fully pinned in train; finance/owner roles get edit or view, evidence providers get upload_only.)

### 4.5 response_status

Determined by what is still open in the response package:
- Root cause unknown / still diagnosing -> `UNDER_INVESTIGATION`.
- Backfill NOT yet confirmed (no successful backfill run / client asks for confirmation) -> engineering
  open -> `NEEDS_ENGINEERING_REVIEW`.
- SLA credit needs finance sign-off -> `NEEDS_FINANCE_REVIEW`.
- All items confirmed (root cause + backfill done + SLA + owners) -> `READY_TO_SEND`.
Note: `incident.status` (often `UNDER_INVESTIGATION`) is the incident status, NOT necessarily the
response_status — derive response_status from the response package's open items, not the incident field.

### 4.6 Enterprise pitfalls

- `backfill_days` = number of FAILED runs, NOT (data overage) and NOT zero even if a later run succeeded.
- `sla_credit_percent` comes from the SLA contract (`monthly_export_credit_percent`), confirmed by a
  messages entry; do not infer from severity alone.
- `failure_window` uses ONLY FAILED run dates; the recovery/success run date is NOT the end of the
  failure window.
- Match the incident by the email's stated reference AND client name to avoid picking a generated/other
  enterprise incident.
- Ignore `generated.*` filler messages and `Generated Enterprise *` accounts.

---

## 5. Cross-family execution rules

- Preserve payload order for list outputs (`ticket_decisions` in payload CSV order; `case_decisions`
  in ascending `case_id` order).
- Return ONLY JSON conforming to the task's `answer_template.json` (no extra keys, no prose).
- Numbers: `charge_amount_usd` / `total_estimated_customer_charge_usd` -> 2 decimals;
  `data_refuel_gb` -> 1 decimal; `sla_credit_percent` / `failed_days` / `backfill_days` -> integers;
  `failure_window` dates -> `YYYY-MM-DD`.
- Always substitute ids from the API; never hardcode from the prompt text alone.
- Booleans: `diagnostic_needed/required` true only for RESOLVED/ESCALATED; `carrier_update_required`
  true only for ENABLE_LINE_ROAMING.
- Decoy detection: `root_causes: ["GENERATED_NOISE"]` and troubleshooting `steps: ["GENERATED_CHECK"]`
  with irrational float metrics indicate a gated ticket (account/outage) whose diagnostics are filler —
  rely on the gate, not those numbers.
