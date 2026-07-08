# SCN_003 CRM Support-Operations Resolution Skill

Executable SOP for resolving offline-ticket batches, mobile contact-center queues,
and enterprise export-complaint response packages against the shared support console
API. Follow the procedures literally — record fields are the source of truth, never
assume values from the queue note or issue summary alone.

## 0. Environment & API map

Base URL (use this, not any 127.0.0.1 URL printed in a prompt):
`<remote-env-url>`

Health: `GET /health` → `{"ok": true}`
Catalog: `GET /api/catalog` (endpoint list + aggregate counts)

| Endpoint | Returns | Notes |
|---|---|---|
| `GET /api/accounts` | array | all service accounts |
| `GET /api/accounts/<account_id>` | object or `{"error":"not_found"}` | auth + status used for eligibility gate |
| `GET /api/tickets` | array | all tickets |
| `GET /api/tickets/<ticket_id>` | object | carries `subscribed_mbps`, `service_type`, `service_area` |
| `GET /api/outages?service_area=<area>` | array | each has `active`, `service_types[]`, `outage_id`, `eta_hours` |
| `GET /api/diagnostics/<ticket_id>` | object or `{}` | pre-troubleshooting metrics + `root_causes[]` |
| `GET /api/troubleshooting/<ticket_id>` | object or `{}` | post-troubleshooting metrics (`post_*`) + `steps[]` |
| `GET /api/customers` `GET /api/lines` `GET /api/lines/<line_id>` | object/array | mobile line record |
| `GET /api/devices/<device_id>` | object | mobile device settings |
| `GET /api/plans/<plan_id>` | object | has `data_limit_gb`, `data_refueling_price_per_gb` |
| `GET /api/bills` | array | each: `amount_due_usd`, `bill_id`, `customer_id`, `due_date`, `status` |
| `GET /api/cases` `GET /api/cases/<case_id>` | array/object | mobile case root |
| `GET /api/enterprise/accounts` | array | each: `account_owner`, `finance_owner`, `name`, `tier` |
| `GET /api/enterprise/incidents` | array | each: `engineering_owner`, `account_owner`, `severity`, `product`, `summary`, `received_at`, `status` |
| `GET /api/enterprise/export-runs?incident_id=<id>` | array | each run: `run_date`, `status` (FAILED/SUCCEEDED), `failure_code`, `exported_record_count` |
| `GET /api/enterprise/messages?query=<text>` | array | each: `author`, `body`, `channel`, `created_at`, `message_id` |
| `GET /api/enterprise/sla/<enterprise_account_id>` | object | `credit_trigger`, `monthly_export_credit_percent`, `executive_contact` |

Empty body `{}` from diagnostics/troubleshooting = no record for that ticket.

A `/api/diagnostics/<id>` or `/api/troubleshooting/<id>` record may exist in the API
even for a ticket that was gate-decided out (FAILED/PENDING_ACTION). Those records
must NOT be used for issue-flag computation; they exist for the
`diagnostic_records_skipped_by_gate` audit metric only.

## 1. Diagnostic floors (inferrable thresholds)

These absolute/ratio floors are NOT printed by the API; derive issue flags by
comparing diagnostics metrics to these floors:

| Metric | Floor (INFERRRED) | Issue flag set when |
|---|---|---|
| `latency_ms` | 100 ms | `latency_ms > 100` → `latency_issue = true` |
| `jitter_ms` | 30 ms | `jitter_ms > 30` → `stability_issue = true` |
| `bandwidth_mbps` | `0.80 × subscribed_mbps` | `bandwidth_mbps < 0.80 × subscribed_mbps` → `bandwidth_issue = true` |

Inferred from gold-flag matching across the 5 diagnostic tickets whose post-troubleshooting
status was known (TCK-5107 RESOLVED, TCK-5184 ESCALATED, TCK-5402 RESOLVED,
TCK-5406 ESCOLATED, TCK-5407 ESCALATED):
- RESOLVED post metrics sit at/below floors: post lat 82 & 79 (≤100), post jit 21 & 18 (≤30),
  post bw 272/300=0.91 & 93/100=0.93 (≥0.80).
- ESCALATED post metrics still violate at least one floor; pre-troubleshooting metrics
  on every diagnostics-used ticket all violate the corresponding floor set.
- The bandwidth ratio 0.80 sits in the only weakly-constrained window
  (TCK-5107 pre 209/300=0.697 fails; TCK-5107 post 272/300=0.907 passes), so 80% is the
  best single round-number estimate.

Boundary rule: treat `>=` for floors below which there is no issue and `>` for floors
above which there is an issue (strict inequalities; values do not hit the boundary in
observed data).

## 2. Family A — Offline ticket batch resolution

Two output flavors exist; both follow the same gating + diagnosing + troubleshooting SOP.
Distinguish by the answer template:
- **Flavor-1 (full)**: `ticket_decisions[]` with `final_resolution_status`,
  `diagnostic_needed`, `latency_issue`, `stability_issue`, `bandwidth_issue`,
  `outage_id`, `escalation_team`, `resolution_route`; batch_summary has
  RESOLVED / PENDING_ACTION / ESCALATED / FAILED + `tickets_requiring_customer_wait`.
- **Flavor-2 (queue-quality)**: `ticket_decisions[]` with `final_resolution_status`,
  `route_team`, `key_blocker`, `diagnostic_required`; queue_summary has per-team counts
  (TIER2_SUPPORT, FIELD_OPS, NETWORK_ENGINEERING, ACCOUNTS_PAYABLE) + per-status counts.

### 2.1 Gating order (apply strictly in this order; first hit wins)

For each `ticket_id` in the payload CSV (preserve payload order):

1. `GET /api/accounts/<account_id>`.
   - If the API returns `{"error":"not_found"}` or HTTP error →
     **INVALID_ACCOUNT** (key_blocker). final_resolution_status=FAILED,
     diagnostic_needed=false, all issue flags=false, escalation_team=NONE,
     route_team=NONE, outage_id="".
   - If `account.authentication.last_login_status == "FAILURE"` OR
     `account.authentication.account_recovery_status == "FAILURE"` →
     **AUTH_FAILED**. final_resolution_status=FAILED, diagnostic_needed=false,
     escalation_team=NONE, route_team=NONE, outage_id="".
   - If `account.status == "Suspended"`:
     - Look at the line/ticket context (issue_summary or queue_note). If it mentions
       "overdue" (or the linked `/api/lines/<line_id>` shows
       `suspension_reason=="OVERDUE_BILL"`, or there's a linked bill with
       `status=="Overdue"`) → **OVERDUE_SUSPENSION** (FAILED, route_team=
       ACCOUNTS_PAYABLE, escalation_team=ACCOUNTS_PAYABLE, diagnostic_needed=false).
     - Otherwise (generic hold / non-billing suspension) → **INELIGIBLE_ACCOUNT**
       (FAILED, diagnostic_needed=false, escalation_team=NONE, route_team=NONE).
     - Fraud-suspension variant: if issue context says "fraud" → **FRAUD_SUSPENSION**
       (FAILED, route_team=NONE, diagnostic_needed=false). Field exists in enum;
       treat same as INELIGIBLE_ACCOUNT for team routing unless evidence says otherwise.
2. Account gate passed (Active + auth SUCCESS) → check outage.
   `GET /api/outages?service_area=<ticket.service_area>`.
   Consider an outage a match iff `outage.active == true` AND
   `ticket.service_type in outage.service_types`.
   - Match → **ACTIVE_OUTAGE** (key_blocker). final_resolution_status=PENDING_ACTION,
     diagnostic_needed=false, all issue flags=false, resolution_route=OUTAGE_WAIT,
     outage_id=<matched outage_id> (Flavor-1 only), route_team=NONE.
   - No match → proceed to diagnostics (diagnostic_needed=true).
3. Diagnostics route: `GET /api/diagnostics/<ticket_id>` and
   `GET /api/troubleshooting/<ticket_id>`.

### 2.2 Pre-troubleshooting issue flag evaluation

Flavor-1 tickets that ran diagnostics populate `latency_issue`,
`stability_issue`, `bandwidth_issue` from diagnostics × floors:

- `latency_issue = diagnostic.latency_ms > 100`
- `stability_issue = diagnostic.jitter_ms > 30`
- `bandwidth_issue = diagnostic.bandwidth_mbps < 0.80 × ticket.subscribed_mbps`

(Flavor-2 does not emit per-issue flags but the underlying floors still drive the
post-troubleshooting RESOLVED-vs-ESCALATED determination.)

### 2.3 Post-troubleshooting resolution determination

For each ticket that got diagnostics:
- Compute post-issue flags the same way against the troubleshooting record's `post_`
  metrics:
  - post_latency_issue  = `troubleshooting.post_latency_ms > 100`
  - post_stability_issue = `troubleshooting.post_jitter_ms > 30`
  - post_bandwidth_issue = `troubleshooting.post_bandwidth_mbps < 0.80 × subscribed_mbps`
- If ALL THREE post flags are false → **RESOLVED via AUTO_TROUBLESHOOTING**
  (final_resolution_status=RESOLVED, escalation_team=NONE, route_team=NONE,
  resolution_route=AUTO_TROUBLESHOOTING).
- If ANY post flag is true → **ESCALATED** (final_resolution_status=ESCALATED,
  resolution_route=ESCALATION). Escalation team comes from the root_causes of the
  diagnostics record (see §2.4).

Note RESOLVED/ESCALATED still preserve the original pre-troubleshooting issue flags
in the Flavor-1 output (issue flags are PRE-TROUBLESHOOTING violations, not post).

### 2.4 Root-cause → escalation team map

For each ESCALATED ticket, take `diagnostics.root_causes[]` and map by keyword:

| Keyword in any root_cause | Escalation team (route_team) |
|---|---|
| `fiber` OR `signal` | FIELD_OPS |
| `backbone` OR `capacity` | NETWORK_ENGINEERING |
| `provisioning` | TIER2_SUPPORT |
| `billing` OR `overdue` OR `payment` | ACCOUNTS_PAYABLE |
| (no match / unrecognized) | TIER2_SUPPORT (fallback, inferred) |

A ticket's `key_blocker` (Flavor-2) for ESCALATED tickets uses the root_cause text:
- BACKBONE_CAPACITY → key_blocker=NETWORK_CAPACITY
- PROVISIONING_STALE → key_blocker=PROVISIONING_STALE
- FIBER_DROP_DAMAGE or SIGNAL_LOSS → key_blocker=PHYSICAL_LINE_FAULT
Other variants follow the same root_cause → team keyword pattern.

Evidence from gold:
- TCK-5184 root_causes=[FIBER_DROP_DAMAGE, SIGNAL_LOSS] both → FIELD_OPS ✓
- TCK-5406 root_causes=[BACKBONE_CAPACITY] → NETWORK_ENGINEERING ✓
- TCK-5407 root_causes=[PROVISIONING_STALE] → TIER2_SUPPORT ✓

### 2.5 Summary fields

Flavor-1 `batch_summary`:
- `RESOLVED`/`PENDING_ACTION`/`ESCALATED`/`FAILED` = counts of each final_resolution_status.
- `tickets_requiring_customer_wait` = count of PENDING_ACTION (waiting on outage).

Flavor-2 `queue_summary`:
- Per-status counts (FAILED, PENDING_ACTION, RESOLVED, ESCALATED).
- Per-team counts (TIER2_SUPPORT, FIELD_OPS, NETWORK_ENGINEERING, ACCOUNTS_PAYABLE) =
  counts of tickets routed to that team anywhere — including FAILED tickets routed to
  ACCOUNTS_PAYABLE via OVERDUE_SUSPENSION.

### 2.6 Field-emission cheat sheet

| Flavor-1 field | Where it comes from |
|---|---|
| `ticket_id` | payload CSV |
| `account_id` | payload CSV |
| `final_resolution_status` | §2.1 gate / §2.3 post determination |
| `diagnostic_needed` | true iff account+outage gates both pass |
| `latency_issue`/`stability_issue`/`bandwidth_issue` | PRE-troubleshooting flags (§2.2) — set to `false` if gate-decided |
| `outage_id` | matched outage id or `""` |
| `escalation_team` | NONE for RESOLVED/PENDING/FAILED; team per §2.4 for ESCALATED |
| `resolution_route` | AUTO_TROUBLESHOOTING / OUTAGE_WAIT / ESCALATION / INELIGIBLE_ACCOUNT / AUTH_FAILED / INVALID_ACCOUNT |

| Flavor-2 field | Where it comes from |
|---|---|
| `ticket_id` | payload CSV |
| `final_resolution_status` | same as Flavor-1 |
| `route_team` | NONE for non-escalated; team per §2.4 for ESCALATED; ACCOUNTS_PAYABLE for OVERDUE_SUSPENSION |
| `key_blocker` | NONE / ACTIVE_OUTAGE / INVALID_ACCOUNT / AUTH_FAILED / OVERDUE_SUSPENSION / FRAUD_SUSPENSION / NETWORK_CAPACITY / PROVISIONING_STALE / PHYSICAL_LINE_FAULT |
| `diagnostic_required` | alias of `diagnostic_needed` |

## 3. Family B — Mobile contact-center triage

Two output flavors:
- **Flavor-1 (full)**: `case_decisions[]` with
  `case_id`, `customer_id`, `line_id`, `primary_action`, `secondary_action`,
  `permission`, `bill_id`, `charge_amount_usd`, `final_route`;
  queue_summary with `self_service_fixes`, `billing_recoveries`,
  `carrier_updates`, `human_transfers`.
- **Flavor-2 (data-recovery analyst)**: `case_decisions[]` with
  `case_id`, `primary_action`, `secondary_action`, `data_refuel_gb`,
  `charge_amount_usd`, `carrier_update_required`, `final_route`;
  worklist_summary with `data_refuel_cases`, `carrier_updates`,
  `device_setting_fixes`, `human_transfers`, `total_estimated_customer_charge_usd`.

For every `case_id` in the payload (preserve ascending case_id order):
1. `GET /api/cases/<case_id>` → `{customer_id, customer_location, device_id, line_id, issue_type, summary}`.
2. `GET /api/lines/<line_id>` → `{status, suspension_reason, roaming_enabled, data_used_gb, plan_id, device_id}`.
3. `GET /api/devices/<device_id>` → settings (see decision tree).
4. `GET /api/plans/<line.plan_id>` → `{data_limit_gb, data_refueling_price_per_gb}` (only needed for REFUEL cases).
5. (Billing only) `GET /api/bills`, find bill where `customer_id == case.customer_id` and `status == "Overdue"` → use as the payment bill.

### 3.1 Mobile decision tree (first match wins, evaluate top-down)

| Condition (read in order) | primary_action | secondary_action | final_route | Extra fields |
|---|---|---|---|---|
| `line.status == "Suspended"` (any suspension_reason) AND customer is ready to pay (per queue note) | `SEND_PAYMENT_REQUEST` | `RESUME_LINE_REBOOT` | BILLING_RECOVERY | `bill_id` = overdue bill; `charge_amount_usd` = bill.amount_due_usd |
| `line.suspension_reason == "FRAUD"` or fraud-indicated (no pay resolution) | `TRANSFER_HUMAN` | `NO_ACTION` | HUMAN_TRANSFER | — |
| `device.sim_status == "missing"` and (issue_type=NO_SERVICE or speed_test=no_connection) | `RESEAT_SIM` | `NO_ACTION` | SELF_SERVICE (or DEVICE_SETTING_FIX in Flavor-2 if NO_SERVICE excluded) | — |
| `device.sim_status` indicates locked ("locked" / repeated PIN) and no other setting fix | `RESET_APN_REBOOT` | `NO_ACTION` | SELF_SERVICE | — |
| `case.customer_location == "abroad"` AND `line.roaming_enabled == false` (phone has roaming on but line side missing) | `ENABLE_LINE_ROAMING` (Flavor-1) / `ENABLE_LINE_ROAMING` (Flavor-2) | `NO_ACTION` | CARRIER_UPDATE | `carrier_update_required = true` |
| `case.customer_location == "abroad"` AND `line.roaming_enabled == true` AND `device.phone_roaming_enabled == false` | `TOGGLE_ROAMING` | `NO_ACTION` | SELF_SERVICE (Flavor-1) / DEVICE_SETTING_FIX (Flavor-2 if applicable) | — |
| `device.airplane_mode == true` | `TOGGLE_AIRPLANE_MODE` | `NO_ACTION` | SELF_SERVICE | — |
| `device.mobile_data_enabled == false` | `TOGGLE_MOBILE_DATA` | `NO_ACTION` | SELF_SERVICE (Flavor-1) / DEVICE_SETTING_FIX (Flavor-2) | — |
| `device.vpn_connected == true` (slow_data or poor speed_test) | `DISCONNECT_VPN` | `NO_ACTION` | SELF_SERVICE (Flavor-1) / DEVICE_SETTING_FIX (Flavor-2) | — |
| `device.data_saver_mode == true` (slow_data) | `TOGGLE_DATA_SAVER` | `NO_ACTION` | SELF_SERVICE (Flavor-1) / DEVICE_SETTING_FIX (Flavor-2) | — |
| `device.network_mode_preference == "3g_only"` or similar old mode (slow_data, not already matched) | `SET_NETWORK_MODE` | `NO_ACTION` | SELF_SERVICE (Flavor-1) / DEVICE_SETTING_FIX (Flavor-2) | — |
| `case.issue_type == "MMS"` AND `device.can_send_mms == false` AND `device.mmsc_url_present == true` AND any `messaging_permissions.{sms,storage} == false` | `GRANT_MESSAGING_PERMISSION` | `NO_ACTION` | SELF_SERVICE | `permission`: sms / storage / sms_and_storage corresponding to the missing flag(s) |
| `line.data_used_gb >= plan.data_limit_gb` (data cap hit) and customer accepts refuel (`customer_preferences.accepted_refuel_gb` in payload) | `REFUEL_DATA` (Flavor-1) / `REFUEL_DATA` (Flavor-2: takes priority over REFUEL_DATA variant) | `NO_ACTION` | BILLING_RECOVERY (Flavor-1) / DATA_RECOVERY (Flavor-2) | `data_refuel_gb` = accepted_refuel_gb; `charge_amount_usd` = `accepted_refuel_gb × plan.data_refueling_price_per_gb` |
| None of the above resolves the case | `TRANSFER_HUMAN` | `NO_ACTION` | HUMAN_TRANSFER | — |

Permission field semantics (Flavor-1 MMS):
- `messaging_permissions.sms == false && storage == false` → `permission = "sms_and_storage"`
- `messaging_permissions.sms == false` only → `permission = "sms"`
- `messaging_permissions.storage == false` only → `permission = "storage"`
- nothing missing → `permission = "NONE"` (shouldn't happen for a GRANT action)

Evidence mapping:
- CASE-2101: NO_SERVICE, home, line Active roaming true, sim_status=missing → RESEAT_SIM → SELF_SERVICE
- CASE-2102: NO_SERVICE, line.status=Suspended, suspension_reason=OVERDUE_BILL, customer ready →
  SEND_PAYMENT_REQUEST + RESUME_LINE_REBOOT, BILL-2102 amount=$86.40 → BILLING_RECOVERY
- CASE-2103: MOBILE_DATA abroad, line.roaming_enabled=true, device.phone_roaming_enabled=false →
  TOGGLE_ROAMING → SELF_SERVICE
- CASE-2104: MMS, device.can_send_mms=false, mmsc_url_present=true, storage=false →
  GRANT_MESSAGING_PERMISSION, permission="storage" → SELF_SERVICE
- CASE-2105: SLOW_DATA, vpn_connected=true → DISCONNECT_VPN → SELF_SERVICE
- CASE-2501: data_used_gb=16.2 ≥ plan.data_limit_gb=15.0, customer_preferences.accepted_refuel_gb=2.0,
  plan=PLAN-PREMIUM data_refueling_price_per_gb=2.0 → REFUEL_DATA, refuel_gb=2.0, charge=$4.00 → DATA_RECOVERY
- CASE-2502: abroad, line.roaming_enabled=false, device.phone_roaming_enabled=true →
  ENABLE_LINE_ROAMING, carrier_update_required=true → CARRIER_UPDATE
- CASE-2503: data_saver_mode=true → TOGGLE_DATA_SAVER → DEVICE_SETTING_FIX
- CASE-2504: network_mode_preference="3g_only" → SET_NETWORK_MODE → DEVICE_SETTING_FIX
- CASE-2505: mobile_data_enabled=false → TOGGLE_MOBILE_DATA → DEVICE_SETTING_FIX

### 3.2 Final-route conventions by flavor

| Action | Self-service route |
|---|---|
| TOGGLE_ROAMING | Flavor-1: SELF_SERVICE. Flavor-2: DEVICE_SETTING_FIX. |
| RESEAT_SIM, GRANT_MESSAGING_PERMISSION, DISCONNECT_VPN, SET_NETWORK_MODE, TOGGLE_DATA_SAVER, TOGGLE_MOBILE_DATA | Flavor-1: SELF_SERVICE. Flavor-2: DEVICE_SETTING_FIX. |
| SEND_PAYMENT_REQUEST + RESUME_LINE_REBOOT | Flavor-1: BILLING_RECOVERY. (Same action set not used in Flavor-2.) |
| REFUEL_DATA | Flavor-1: BILLING_RECOVERY (per full enum). Flavor-2: DATA_RECOVERY. |
| ENABLE_LINE_ROAMING | Both flavors: CARRIER_UPDATE. |
| TRANSFER_HUMAN | Both flavors: HUMAN_TRANSFER. |

`carrier_update_required=true` whenever primary_action=ENABLE_LINE_ROAMING (and only then) in Flavor-2.

### 3.3 Charge calculation

`charge_amount_usd` for billing / refuel cases:
- Billing-recovery (payment request): `charge_amount_usd = overdue_bill.amount_due_usd` (two decimals).
- Data refuel: `charge_amount_usd = accepted_refuel_gb × plan.data_refueling_price_per_gb` (two decimals).
- All non-billing actions: `charge_amount_usd = 0.00`.

### 3.4 Summary rollups

| Flavor-1 queue_summary | Count |
|---|---|
| self_service_fixes | tickets with final_route=SELF_SERVICE |
| billing_recoveries | tickets with final_route=BILLING_RECOVERY |
| carrier_updates | tickets with final_route=CARRIER_UPDATE |
| human_transfers | tickets with final_route=HUMAN_TRANSFER |

| Flavor-2 worklist_summary | Value |
|---|---|
| data_refuel_cases | count primary_action=REFUEL_DATA |
| carrier_updates | count primary_action=ENABLE_LINE_ROAMING |
| device_setting_fixes | count final_route=DEVICE_SETTING_FIX |
| human_transfers | count primary_action=TRANSFER_HUMAN |
| total_estimated_customer_charge_usd | sum of all `charge_amount_usd` (two decimals) |

Flavor-1 `charge_amount_usd` is "number with two decimals"; Flavor-2 too.
Flavor-2 `data_refuel_gb` is "number with one decimal", `0.0` when N/A.

## 4. Family C — Enterprise export-complaint response package

For each enterprise complaint payload (client_complaint_email.txt + response_requirements.json):

### 4.1 Identify the incident

1. `GET /api/enterprise/incidents` → find by `incident_id` (often present in the complaint email,
   e.g., "INC-7301") OR by matching `summary` keyword against the complaint subject/body.
2. Pull `enterprise_account_id`, `engineering_owner`, `account_owner`, `severity` from the
   incident record (these become `engineering_owner`/`account_owner`/`severity` in the response
   package — they are authoritative, do not derive from the email).

### 4.2 Identify failed export window and backfill

`GET /api/enterprise/export-runs?incident_id=<incident_id>`.
Filter to runs where `status == "FAILED"`. Sort by `run_date` ascending.
- `failure_window.start_date` = first failed run_date.
- `failure_window.end_date` = last failed run_date.
- `failure_window.failed_days` = count of failed runs.
- `backfill_days` = `failed_days` (manual backfill equals the number of failed runs).
- `root_cause_category` = human-readable summary derived from the failed runs' common
  `failure_code` plus message-board evidence (see below). E.g.,
  `STALE_CREDENTIAL` ("scheduler still references old secret" message) →
  `"stale credential after rotation"`.
  `STAGING_STORAGE_QUOTA` ("staging bucket reached quota") → `"staging bucket quota"`.

### 4.3 SLA credit

`GET /api/enterprise/sla/<enterprise_account_id>`:
- `sla_credit_percent` = `sla_contract.monthly_export_credit_percent` (integer percent).
- The `credit_trigger` text is supporting evidence (e.g., "3 consecutive failed export runs"
  vs "critical export outage longer than 72 hours") — verify the failure condition is satisfied
  before asserting the credit in the package; the credit_percent value itself is taken verbatim.

### 4.4 Contributing alert issue

`GET /api/enterprise/messages?query=<client keyword or incident id>` and inspect the channels.
- If the early-alert message has `channel` containing "archive" (e.g., `export-alerts-archive`)
  → `contributing_alert_issue = "ARCHIVED_ALERT_ROUTE"`.
- If no such archive-route evidence → `"NONE"` or `"UNKNOWN"` per template enum.

### 4.5 Owners and channel/evidence/report naming

`GET /api/enterprise/accounts` → find by `enterprise_account_id`:
- `account_owner` = the enterprise account's `account_owner` (authoritative, matches incident).
- `engineering_owner` = the incident's `engineering_owner` (authoritative).
- `finance_owner` = the enterprise account's `finance_owner` (used for share permission view tier).

Naming conventions (per `response_requirements.naming_style`):
- `channel_name`: client name → lowercase, hyphenated, punctation stripped. E.g.,
  "Asteri Retail Inc." → `asteri-retail-inc`.
- `evidence_folder`: `"<Client Name> <Month Year> Investigation"`. Use month/year of the failure
  window start. E.g., failure start 2026-05-12 → `"Asteri Retail Inc. May 2026 Investigation"`.
- `report_title`: `"<Client Name> Export Failure - Resolution Report"`.

`response_status`:
- `sla_credit_percent > 0` → `"NEEDS_FINANCE_REVIEW"`.
- (Coverage for other statuses in the enum READY_TO_SEND / NEEDS_ENGINEERING_REVIEW /
  UNDER_INVESTIGATION should drive off the SLA-credit result and incident.status.)
  Observed: closed SLA-credit case → NEEDS_FINANCE_REVIEW.

### 4.6 Share permissions

Take `response_requirements.permission_users_to_include` in order. For each user:
- If user matches `enterprise_account.finance_owner` → `"view"`.
- The next listed user (typically engineering/owner role) → `"edit"`.
- Any further users not on the finance tier → `"upload_only"` (enum value; inferred for the
  third-tier case).

Order the output array exactly as listed in permission_users_to_include.

Evidence (train_003): permission_users_to_include=["laura.brown","jun.chen"] →
[{user:laura.brown,permission:view}, {user:jun.chen,permission:edit}].
laura.brown is ENT-3001.finance_owner → view tier.

### 4.7 Response-package field reference

| Field | Source |
|---|---|
| `incident_id` | enterprise incident (or complaint email) |
| `enterprise_account_id` | enterprise incident |
| `root_cause_category` | failure_code + message body (human-readable short summary) |
| `contributing_alert_issue` | ARCHIVED_ALERT_ROUTE / NONE / UNKNOWN (per message channel) |
| `failure_window.start_date / end_date / failed_days` | min/max/count of FAILED export runs |
| `backfill_days` | = failed_days |
| `sla_credit_percent` | sla contract monthly_export_credit_percent |
| `severity` | enterprise incident.severity (Critical/High/Medium/Low) |
| `engineering_owner` | enterprise incident.engineering_owner |
| `account_owner` | enterprise incident.account_owner (matches enterprise account) |
| `channel_name` | client name lowercased-hyphenated |
| `evidence_folder` | "<Client Name> <FailureMonth Year> Investigation" |
| `report_title` | "<Client Name> Export Failure - Resolution Report" |
| `share_permissions[]` | ordered list with view (finance_owner)/edit/upload_only per §4.6 |
| `response_status` | NEEDS_FINANCE_REVIEW when sla_credit_percent > 0 |

## 5. Audit-math definitions (when test prompts request these)

These are computed over the batch of tickets the test prompt includes. Always compute
over the tickets whose `diagnostic_needed` flag became `true` for diagnostic audits,
and over ESCALATED/RESOLVED-with-troubleshooting tickets for post audits.

`bandwidth_floor(tkt) = 0.80 × tkt.subscribed_mbps`
   `latency_floor = 100 (ms)`
   `jitter_floor = 30 (ms)`

1. `pre_troubleshooting_bandwidth_gap_total_mbps`:
   Sum over every diagnostics-used ticket (those with `diagnostic_needed == true`) whose
   `diagnostics.bandwidth_mbps < bandwidth_floor` of `(bandwidth_floor - bandwidth_mbps)`.
   Units: Mbps. Gated-out tickets are excluded (even if their API diagnostic record exists).

2. `diagnostic_records_skipped_by_gate`:
   Count of tickets where `diagnostic_needed == false` BUT the API actually returns a
   non-empty diagnostics record at `/api/diagnostics/<ticket_id>`. (These records were
   available but skipped because the gate decided the ticket.)

3. `post_troubleshooting_remaining_issue_flags`:
   For each "unresolved diagnostic ticket" (diagnostic_needed=true AND
   final_resolution_status==ESCALATED) count how many of
   {post_latency_issue, post_stability_issue, post_bandwidth_issue} are still true
   against the floors. Sum across all unresolved diagnostic tickets.

4. `post_threshold_excess_totals`:
   For each unresolved diagnostic ticket, compute:
   - `latency_excess   = max(0, troubleshooting.post_latency_ms  - 100)`
   - `jitter_excess    = max(0, troubleshooting.post_jitter_ms   - 30)`
   - `bandwidth_short  = max(0, bandwidth_floor(tkt) - troubleshooting.post_bandwidth_mbps)`
   Sum (latency_excess + jitter_excess + bandwidth_short) across all unresolved
   diagnostic tickets. Report as a single total (ms + ms + Mbps aggregated).

5. `tickets_using_post_troubleshooting_records`:
   Count of tickets with `diagnostic_needed == true` AND a non-empty
   `/api/troubleshooting/<ticket_id>` record (i.e., post_ metrics were used to decide
   RESOLVED vs ESCALATED).

6. `tickets_with_active_outage_match`:
   Count of tickets for which an active outage (active=true, service_type in
   outage.service_types) sits in the ticket's service_area.

7. `unique_escalation_teams`:
   Sorted ascending set of distinct `escalation_team` values across the batch
   (excluding NONE).

8. `root_cause_escalation_ticket_ids` (by team):
   Map: team_name → sorted list of ticket_ids whose final escalation_team == team_name
   (i.e., the ESCOLATED tickets, grouped by their resolved escalation team per §2.4).
   Only populate teams that have at least one ticket.

9. `post_success` and `post_failure` id lists:
   - `post_success_ids` = sorted ascending list of ticket_ids whose
     final_resolution_status == RESOLVED (after troubleshooting, all post flags cleared).
   - `post_failure_ids` = sorted ascending list of ticket_ids whose
     final_resolution_status == ESCALATED (post still has at least one issue).
   Both limited to tickets that went through diagnostics (had a troubleshooting recheck).

10. Per-ticket floor + shortfall list (sorted by ticket_id ascending):
    For each diagnostics-used ticket, report:
    - `ticket_id`
    - `bandwidth_floor_mbps = 0.80 × subscribed_mbps`
    - `bandwidth_shortfall_mbps = max(0, bandwidth_floor_mbps - diagnostics.bandwidth_mbps)`
    - `latency_floor_ms = 100`
    - `latency_excess_ms = max(0, diagnostics.latency_ms - 100)`
    - `jitter_floor_ms = 30`
    - `jitter_excess_ms = max(0, diagnostics.jitter_ms - 30)`
    Sorted ascending by ticket_id.

## 6. Pitfalls and edge cases

- **API URLs in prompts lie**: any prompt printing `http://127.0.0.1:8057` (or similar)
  must be ignored; the base URL is `<remote-env-url>`. Apply to every endpoint
  substitution.
- **Gated-out tickets may still have diagnostics / troubleshooting records**: those are
  "skipped by gate" for the audit. Do NOT compute pre issue-flags for them in the per-ticket
  answer; their flags go to `false` in Flavor-1.
- **Bandwidth ratio only weakly constrained**: train data narrows it to
  0.697 < ratio ≤ 0.907 from TCK-5107 alone. Commit to 0.80 unless a test item
  contradicts (then revise proportionally). The jitter floor (≤21 to <33.5) and latency
  floor (≤82 to <97 from TCK-5402 pre being just below) commit to 30 ms and 100 ms.
- **Outage service_type overlap**: an outage applies only if the ticket's `service_type`
  is in outage.service_types. A plain `active == true` in the right service_area does
  not suffice — service_type must match.
- **Order preservation**: preserve the CSV payload order in `ticket_decisions`;
  preserve ascending case_id order in `case_decisions`.
- **Permission users order**: in Flavor-C, output share_permissions in the exact order of
  `response_requirements.permission_users_to_include` (do NOT sort alphabetically).
- **`route_team` for OVERDUE_SUSPENSION is ACCOUNTS_PAYABLE even though the ticket is
  FAILED**: the per-team summary counts include this ticket. Same for FRAUD_SUSPENSION
  if the test sets its team accordingly.
- **Two mobile output flavors**: same underlying decision tree, but Flavor-2 collapses
  billing/billing-recovery routes to DATA_RECOVERY and merges self-service fixes into
  DEVICE_SETTING_FIX. Watch the answer template before deciding which fields to emit.
- **REFUEL_DATA needs both**: line.data_used_gb ≥ plan.data_limit_gb AND explicit
  customer_preferences.accepted_refuel_gb in the worklist payload. If the customer
  refuses, fall through to other matches (often TRANSFER_HUMAN).
- **root_cause → team matching**: case-insensitive substring match. A single root_cause
  may contain multiple keywords (BACKBONE_CAPACITY matches both `backbone` and
  `capacity` → NETWORK_ENGINEERING).
- **failure_window count vs duration**: `failed_days` is the count of FAILED export runs,
  NOT the calendar span (e.g., 2026-05-12 to 2026-05-14 = 3 dates = 3 FAILED runs).
- **SLA credit value comes verbatim from the SLA contract**: never recompute from the
  number of failed days. Validate the trigger text is satisfied, but use the contract's
  `monthly_export_credit_percent` literally.
- **response_status**: when SLA credit > 0, status is NEEDS_FINANCE_REVIEW (finance_owner
  gets view permission in the share list); engineering gets edit. Verify against
  incident.status and sla.credit_trigger if the prompt insists on a different status enum.

## 7. Quick threshold summary (commit these numbers)

- **Latency floor: 100 ms** (inferred — TCK-5107 post=82 cleared, TCK-5407 post=121 still failing).
- **Jitter floor: 30 ms** (inferred — TCK-5107 post=21 cleared, all ESCALATED posts ≥32).
- **Bandwidth ratio: 0.80** of `subscribed_mbps` (inferred — TCK-5107 pre=209/300 fails,
  post=272/300 passes; ratio window is 0.697–0.907).
