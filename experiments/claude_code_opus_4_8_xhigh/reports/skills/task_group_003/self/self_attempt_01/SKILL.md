# SKILL: CRM Support-Console Decision Tasks

## When to use
Use this when a task asks you to act as a support analyst/lead over a shared
"support-console" REST API and emit a **structured JSON decision** for a batch of
records: offline ticket batches, ticket queue-quality review, contact-center mobile
case triage, mobile-data recovery worklists, or enterprise export-complaint response
packages. The task always supplies a `payloads/answer_template.json` and one or more
input files (CSV / JSON / email). **Your output must be ONLY JSON conforming exactly
to that template** — exact enum strings, exact field names, correct numeric formats.

## API base URL & lookup habits
- Base URL: `<remote-env-url>` . **Always use this**, even when the
  prompt text says `http://127.0.0.1:8057` (the prompt's URL is a placeholder).
- It is read-only. Confirm with `curl -s <base>/health`. `GET /api/catalog` lists
  endpoints + record counts.
- Endpoints and what to chain them for:
  - Tickets: `/api/tickets/<ticket_id>` -> gives `account_id`, `service_type`,
    `service_area`, `subscribed_mbps`, `issue_summary`, `status`.
  - Accounts: `/api/accounts/<account_id>` -> `status` (Active/Suspended),
    `authentication.last_login_status`, `authentication.account_recovery_status`.
    A missing account returns `{"error":"not_found"}`.
  - Outages: `/api/outages?service_area=<area>` -> list; check `active` and whether
    `service_types` includes the ticket's `service_type`.
  - Diagnostics: `/api/diagnostics/<ticket_id>` -> `latency_ms`, `jitter_ms`,
    `bandwidth_mbps`, `root_causes` (list).
  - Troubleshooting: `/api/troubleshooting/<ticket_id>` -> `post_latency_ms`,
    `post_jitter_ms`, `post_bandwidth_mbps`, `steps` (list). This is the result of
    the auto-fix attempt; compare post-metrics to decide if the issue was resolved.
  - Mobile chain: `case_id` number == `customer_id` number == `bill_id` number
    (CASE-2101 -> CUST-2101 -> BILL-2101). Get the line from `/api/lines` filtered by
    `customer_id` (line has `device_id`, `plan_id`, `status`, `suspension_reason`,
    `roaming_enabled`, `data_used_gb`). Then `/api/devices/<device_id>`,
    `/api/plans/<plan_id>`, `/api/bills` (filter by `customer_id`).
  - Enterprise: `/api/enterprise/incidents/<incident_id>`,
    `/api/enterprise/export-runs?incident_id=<id>`,
    `/api/enterprise/sla/<enterprise_account_id>`,
    `/api/enterprise/accounts` (owners), and
    `/api/enterprise/messages?query=<text>` (substring search of bodies/metadata;
    query by the **client name** to find both root-cause and SLA messages).
- **Ignore "generated" noise records**: tickets `TCK-80xx` with summary "Generated
  support ticket", accounts named "Generated Customer", `root_causes:["GENERATED_NOISE"]`,
  troubleshooting `steps:["GENERATED_CHECK"]`, enterprise "finance.owner"/"acct.owner"
  placeholders. Only the IDs your payload actually lists matter; derive each from its
  own records.

---

## TASK FAMILY A — Offline ticket batch resolution
(template keys: `ticket_decisions[]` with `final_resolution_status`, `diagnostic_needed`,
`latency_issue`, `stability_issue`, `bandwidth_issue`, `outage_id`, `escalation_team`,
`resolution_route`; plus `batch_summary`.)

### Per-ticket decision procedure (evaluate gates IN ORDER; first match wins)
1. **Account lookup fails** (`/api/accounts/<id>` -> `not_found`, e.g. id prefix not
   `ACC-`): `resolution_route=INVALID_ACCOUNT`, `final_resolution_status=FAILED`,
   `escalation_team=NONE`, `diagnostic_needed=false`, all issue flags false,
   `outage_id=""`.
2. **Auth failed** (`authentication.last_login_status=="FAILURE"` or
   `account_recovery_status=="FAILURE"`): `resolution_route=AUTH_FAILED`,
   `final_resolution_status=FAILED`, `escalation_team=NONE`, `diagnostic_needed=false`.
3. **Account Suspended** (`status=="Suspended"`): `resolution_route=INELIGIBLE_ACCOUNT`,
   `escalation_team=ACCOUNTS_PAYABLE`, `final_resolution_status=PENDING_ACTION`
   (billing action needed; treat as needs-customer/billing action, not a tech FAILED),
   `diagnostic_needed=false`. (See Family B for the OVERDUE vs FRAUD distinction.)
4. **Active outage** for this service: an outage in the ticket's `service_area` with
   `active==true` AND `service_type` in the outage's `service_types`:
   `resolution_route=OUTAGE_WAIT`, `final_resolution_status=PENDING_ACTION`,
   `outage_id=<that outage_id>`, `escalation_team=NONE`, `diagnostic_needed=false`.
   This ticket counts toward `tickets_requiring_customer_wait`.
5. **Otherwise run the technical path** (diagnostics + troubleshooting):
   - `diagnostic_needed=true` (a diagnostic is warranted for an eligible, online,
     non-outage account).
   - Set issue flags from the **diagnostic** values vs the subscribed/expected level:
     - `latency_issue=true` if `latency_ms` is elevated (internet/video high-latency
       reports; in the data, healthy post-fix latency lands ~<=90ms while problem
       cases sit ~130-225ms). Treat clearly elevated latency (roughly >120ms) as an
       issue.
     - `stability_issue=true` if `jitter_ms` is elevated (problem cases ~40-52ms;
       healthy ~<=25ms). Treat roughly >35ms as an issue.
     - `bandwidth_issue=true` if delivered `bandwidth_mbps` is materially below
       `subscribed_mbps` (e.g. 209 delivered vs 300 subscribed). Compare to the
       ticket's `subscribed_mbps`, not an absolute number.
   - Decide resolution from `root_causes` + whether troubleshooting fixed it:
     - **Soft/config causes** (`CONFIGURATION_DRIFT`, `VOICE_PROFILE_STALE`,
       `PROVISIONING_STALE`) where post-troubleshooting metrics return to healthy
       (latency/jitter back to normal range, bandwidth restored): `RESOLVED`,
       `resolution_route=AUTO_TROUBLESHOOTING`, `escalation_team=NONE`.
     - **Hardware/physical causes** (`FIBER_DROP_DAMAGE`, `SIGNAL_LOSS`) that
       troubleshooting (LINE_TEST/SIGNAL_REFRESH) does NOT fix (post-latency still
       high, e.g. ~170+): `ESCALATED`, `resolution_route=ESCALATION`,
       `escalation_team=FIELD_OPS`.
     - **Network capacity cause** (`BACKBONE_CAPACITY`) that the reroute attempt does
       NOT fix: `ESCALATED`, `resolution_route=ESCALATION`,
       `escalation_team=NETWORK_ENGINEERING`.
     - **Provisioning/profile cause still degraded after the fix attempt** (improved
       but metrics still out of healthy range): escalate to `TIER2_SUPPORT`
       (`ESCALATED`/`ESCALATION`). If it returned to healthy, mark `RESOLVED`.

### batch_summary
- `RESOLVED`/`PENDING_ACTION`/`ESCALATED`/`FAILED` = exact counts of those statuses
  across `ticket_decisions` (they must sum to the number of tickets).
- `tickets_requiring_customer_wait` = count of `OUTAGE_WAIT` tickets (customer must
  wait for the outage ETA). Suspension/billing cases are NOT "customer wait".

---

## TASK FAMILY B — Ticket queue-quality review
(template keys: `ticket_decisions[]` with `final_resolution_status`, `route_team`,
`key_blocker`, `diagnostic_required`; plus `queue_summary`.)

Same gating logic as Family A, but the output names a `key_blocker` enum and a
`route_team`. Mapping:

| Situation | key_blocker | route_team | status | diagnostic_required |
|---|---|---|---|---|
| Account not found | `INVALID_ACCOUNT` | NONE | FAILED | false |
| Auth never recovered (auth FAILURE) | `AUTH_FAILED` | NONE | FAILED | false |
| Active outage covering the service | `ACTIVE_OUTAGE` | NONE | PENDING_ACTION | false |
| Suspended, overdue/billing note | `OVERDUE_SUSPENSION` | ACCOUNTS_PAYABLE | PENDING_ACTION | false |
| Suspended, fraud note | `FRAUD_SUSPENSION` | ACCOUNTS_PAYABLE | PENDING_ACTION | false |
| Backbone/capacity cause not fixed | `NETWORK_CAPACITY` | NETWORK_ENGINEERING | ESCALATED | true |
| Fiber/signal physical cause not fixed | `PHYSICAL_LINE_FAULT` | FIELD_OPS | ESCALATED | true |
| Provisioning mismatch not fully fixed | `PROVISIONING_STALE` | TIER2_SUPPORT | ESCALATED | true |
| Soft cause fixed by auto troubleshooting | `NONE` | NONE | RESOLVED | true |

Notes:
- **OVERDUE vs FRAUD suspension**: account records expose no reason field, so read the
  ticket `queue_note`/`issue_summary` text ("overdue notice"/"overdue bill" ->
  `OVERDUE_SUSPENSION`; "fraud"/"fraud hold" -> `FRAUD_SUSPENSION`). For mobile lines
  use `line.suspension_reason` (`OVERDUE_BILL`).
- `diagnostic_required` is `true` whenever the ticket reaches the technical path
  (eligible + online + no active outage), i.e. RESOLVED and ESCALATED tech tickets;
  it is `false` for INVALID_ACCOUNT, AUTH_FAILED, ACTIVE_OUTAGE, and SUSPENSION gates.

### queue_summary
- Status counts (`FAILED`,`PENDING_ACTION`,`RESOLVED`,`ESCALATED`) = counts across
  decisions; must sum to ticket count.
- `TIER2_SUPPORT`,`FIELD_OPS`,`NETWORK_ENGINEERING`,`ACCOUNTS_PAYABLE` = counts of each
  `route_team` value. `NONE` routes are not summed into any team bucket.

---

## TASK FAMILY C — Contact-center mobile case triage
(template keys: `case_decisions[]` with `customer_id`, `line_id`, `primary_action`,
`secondary_action`, `permission`, `bill_id`, `charge_amount_usd`, `final_route`;
plus `queue_summary`.)

For each case: resolve `customer_id` (case number == customer number), then its line,
device, plan, bill. Choose the action by matching the reported issue to the device/line
state. **First matching condition decides the primary action**; secondary_action is a
required follow-up (use `NO_ACTION` if none).

Action selection (read device/line fields, not just the words):
- `sim_status=="missing"` (no service / no signal) -> `RESEAT_SIM`. (signal "none",
  speed "no_connection" corroborate.)
- Line `status=="Suspended"` with `suspension_reason` billing/overdue, and there is an
  Overdue bill -> primary `SEND_PAYMENT_REQUEST`, secondary `RESUME_LINE_REBOOT`;
  set `bill_id` to the overdue bill and `charge_amount_usd` = its `amount_due_usd`
  (two decimals); `final_route=BILLING_RECOVERY`.
- Traveling abroad / roaming problem: if device `phone_roaming_enabled==false` ->
  `TOGGLE_ROAMING`; if device roaming on but line `roaming_enabled==false` ->
  `ENABLE_LINE_ROAMING` (carrier-side) -> `final_route=CARRIER_UPDATE`.
- Messaging/MMS can't send photos: device `can_send_mms==false` -> inspect
  `messaging_permissions`; grant the missing permission via
  `GRANT_MESSAGING_PERMISSION` and set `permission` to the missing one(s):
  `storage` if storage false, `sms` if sms false, `sms_and_storage` if both false;
  else `NONE`.
- Data works but slow: `vpn_connected==true` -> `DISCONNECT_VPN`;
  `data_saver_mode==true` -> `TOGGLE_DATA_SAVER`; `network_mode_preference` is a legacy
  mode like `3g_only` -> `SET_NETWORK_MODE`.
- `mobile_data_enabled==false` -> `TOGGLE_MOBILE_DATA`.
- No device fix applies / hard issue -> `TRANSFER_HUMAN`, `final_route=HUMAN_TRANSFER`.
- `permission` is `NONE` unless the case is a messaging-permission grant.
- `bill_id`/`charge_amount_usd`: empty string / 0.00 unless a payment is involved.

`final_route` mapping: device/setting/SIM fixes -> `SELF_SERVICE`; payment ->
`BILLING_RECOVERY`; carrier/roaming provisioning -> `CARRIER_UPDATE`; transfer ->
`HUMAN_TRANSFER`. `queue_summary` counts each route bucket; buckets sum to case count.

---

## TASK FAMILY D — Mobile-data recovery worklist
(template keys: `case_decisions[]` with `primary_action`, `secondary_action`,
`data_refuel_gb`, `charge_amount_usd`, `carrier_update_required`, `final_route`;
plus `worklist_summary`.)

Same lookups as Family C but focused on data. Action selection:
- Data stopped "after usage limit": compare `line.data_used_gb` to
  `plan.data_limit_gb`. If at/over the cap -> `REFUEL_DATA`. The refuel amount =
  customer's `accepted_refuel_gb` from `customer_preferences` (set `data_refuel_gb`);
  `charge_amount_usd = accepted_gb * plan.data_refueling_price_per_gb` (two decimals,
  e.g. 2.0 GB * $2.0 = `4.00`). Respect `does_not_want_plan_change` (do NOT propose a
  plan upgrade). `final_route=DATA_RECOVERY`, `carrier_update_required=false`.
- Roaming on phone but no data: device `phone_roaming_enabled==true` but line
  `roaming_enabled==false` -> `ENABLE_LINE_ROAMING`, `carrier_update_required=true`,
  `final_route=CARRIER_UPDATE`.
- Data-saver icon / slow: `data_saver_mode==true` -> `TOGGLE_DATA_SAVER`,
  `final_route=DEVICE_SETTING_FIX`.
- Slow on older network mode: `network_mode_preference=="3g_only"` (or other legacy)
  -> `SET_NETWORK_MODE`, `final_route=DEVICE_SETTING_FIX`.
- No data after settings change: `mobile_data_enabled==false` -> `TOGGLE_MOBILE_DATA`
  (`final_route=DATA_RECOVERY`); VPN on -> `DISCONNECT_VPN` (`DEVICE_SETTING_FIX`).
- Nothing matches -> `TRANSFER_HUMAN` / `HUMAN_TRANSFER`.
- `data_refuel_gb=0.0` and `charge_amount_usd=0.00` unless a refuel applies.
- `worklist_summary`: `data_refuel_cases`, `carrier_updates`, `device_setting_fixes`,
  `human_transfers` = counts by `final_route`; `total_estimated_customer_charge_usd` =
  sum of all `charge_amount_usd` (two decimals).

---

## TASK FAMILY E — Enterprise export-complaint response package
(single-object template: `incident_id`, `enterprise_account_id`, `root_cause_category`,
`contributing_alert_issue`, `failure_window{start_date,end_date,failed_days}`,
`backfill_days`, `sla_credit_percent`, `severity`, `engineering_owner`,
`account_owner`, `channel_name`, `evidence_folder`, `report_title`,
`share_permissions[]`, `response_status`.)

Procedure:
1. Read the complaint email/`response_requirements.json` for the client name, product,
   and the approximate `incident_id`. Confirm via
   `/api/enterprise/incidents/<incident_id>` — it gives `enterprise_account_id`,
   `product`, `severity`, `status`, `account_owner`, `engineering_owner`.
2. `GET /api/enterprise/export-runs?incident_id=<id>`. The `FAILED` runs (with a
   non-empty `failure_code`, `exported_record_count==0`) form the failure window:
   `start_date` = first failed `run_date`, `end_date` = last failed `run_date`,
   `failed_days` = number of FAILED runs. The subsequent `SUCCEEDED` run is the
   backfill/recovery; `backfill_days` = number of failed days that had to be
   backfilled (== `failed_days`).
3. `root_cause_category`: derive a concise category from the shared `failure_code`
   and the technical message. E.g. `failure_code=STALE_CREDENTIAL` + message about a
   "credential rotation … scheduler pod still references old secret" -> a concise
   category like `STALE_CREDENTIAL` / "stale export credential". For
   `STAGING_STORAGE_QUOTA` -> "staging storage quota exceeded". Match the dominant
   failure_code; keep it short.
4. `contributing_alert_issue`: search messages by the **client name**
   (`/api/enterprise/messages?query=<ClientName>`). If the technical alert message was
   posted to an **archived alert channel** (channel name contains "archive", e.g.
   `export-alerts-archive`) -> `ARCHIVED_ALERT_ROUTE` (alerts went to a dead channel,
   delaying detection). If alerts were in a live channel (e.g. `data-platform`) ->
   `NONE`. Use `UNKNOWN` only if no relevant message exists.
5. `sla_credit_percent`: from `/api/enterprise/sla/<enterprise_account_id>` ->
   `monthly_export_credit_percent`, but only when the `credit_trigger` is satisfied by
   the failure window (e.g. "3 consecutive failed export runs" met by 3 failed days;
   "outage longer than 72 hours" met by 4 failed days). Output the integer percent.
6. `severity`: copy from the incident (Critical/High/Medium/Low).
7. `engineering_owner`, `account_owner`: copy the incident's `engineering_owner` and
   `account_owner` user ids. Do NOT use `finance_owner` here (finance owner is only a
   share recipient / review approver).
8. Naming (follow `naming_style` literally):
   - `channel_name`: lowercase, hyphenated, derived from client + topic, e.g.
     `asteri-retail-export-incident`.
   - `evidence_folder`: client + date investigation folder, e.g.
     `asteri-retail-2026-05-15` (use the recovery/success date or incident date).
   - `report_title`: human-readable client export-failure title, e.g.
     `Asteri Retail Inc. Monthly Export Failure Report`.
9. `share_permissions`: build one entry per user listed in
   `requirements.permission_users_to_include`, **in that exact order**. Assign
   `permission`: finance owner (reviews the SLA credit) -> `view`; engineering/data
   contributor who must attach evidence -> `upload_only`; general editor -> `edit`.
   When unsure, default the finance/account reviewer to `view`. Preserve listed order.
10. `response_status`: if an SLA credit is being applied (finance must approve) ->
    `NEEDS_FINANCE_REVIEW`; if the incident is still `UNDER_INVESTIGATION` and no
    package is finalized -> `UNDER_INVESTIGATION`; if engineering RCA is unverified ->
    `NEEDS_ENGINEERING_REVIEW`; only `READY_TO_SEND` when root cause, backfill, credit,
    and owners are all confirmed. Prefer `NEEDS_FINANCE_REVIEW` whenever a monetary SLA
    credit is part of the response.

---

## Output-format discipline (applies to ALL families)
- Return **ONLY** the JSON object/array the template defines — no prose, no markdown
  fences, no comments. The template's value strings are field SPECS, not literal output.
- **Preserve order**: ticket/case arrays follow the payload's input order unless the
  template says "ascending case_id order" (then sort ascending). Re-read the template's
  order note per field.
- **Exact enums**: copy enum tokens verbatim (uppercase, underscores). A near-miss like
  `ESCALATE` vs `ESCALATED` or `SELF_SERVICE` vs `SELFSERVICE` is wrong.
- **Numbers**: `charge_amount_usd` two decimals (`4.00`), `data_refuel_gb` one decimal
  (`2.0`), percentages as integers (`15`), counts as integers. Don't quote numbers.
- **Empty/none sentinels**: use `""` for "empty string when none applies" string fields
  (e.g. `outage_id`, `bill_id`), `NONE` (enum) where the enum offers it, and `0.0`/`0.00`
  for inapplicable numbers — match what the template states.
- **IDs come from the payload, evidence from the API**: never invent IDs; copy
  `ticket_id`/`account_id`/`case_id` exactly as listed, and look up everything else.

## Common misjudgments / exclusion rules
- Do NOT run/flag diagnostics for invalid-account, auth-failed, suspended, or
  active-outage tickets — those gates short-circuit before the technical path.
- Do NOT escalate a ticket whose troubleshooting restored healthy metrics — that is
  `RESOLVED`/`AUTO_TROUBLESHOOTING`, escalation_team `NONE`.
- Do NOT treat "improved but still degraded" as resolved; provisioning/profile causes
  that remain out of range still escalate (TIER2_SUPPORT).
- An outage only blocks a ticket if it is `active` AND its `service_types` includes the
  ticket's `service_type`; an inactive or wrong-service-type outage does not gate.
- `tickets_requiring_customer_wait` counts ONLY outage-wait tickets, not billing holds.
- For enterprise: `engineering_owner`/`account_owner` are the incident's owners;
  `finance_owner` is a share recipient/approver, never the engineering or account owner.
- Apply the SLA credit only if the contract's `credit_trigger` is actually met by the
  failure window; otherwise `sla_credit_percent` may not apply.
- Ignore GENERATED_* noise records and placeholder owners — they are decoys.
- Summary counts must be internally consistent (status counts sum to record count;
  route/team buckets only count their own enum value).
```
