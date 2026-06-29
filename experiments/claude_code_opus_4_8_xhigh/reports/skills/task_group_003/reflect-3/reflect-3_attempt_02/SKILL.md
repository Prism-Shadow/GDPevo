# Support-Console Resolution Skill

## When to use
Use this skill for any task that hands you a small batch/queue of support records
(tickets, mobile cases, or an enterprise complaint) and asks you to classify or
resolve each item and emit a strict JSON answer. The work is always: (1) read the
payload list, (2) look up authoritative records from the shared support-console REST
API, (3) apply deterministic business rules, (4) emit ONLY JSON matching the task's
`answer_template.json`.

Never guess record contents from the customer's prose — the prose only hints at the
issue *type*. The decision is driven by the actual API record fields.

## API base URL and lookup habits
Base URL: `<remote-env-url>` (this overrides any `127.0.0.1:8057`
shown in a prompt). All endpoints are GET and read-only.

Start with `/api/catalog` if unsure what exists. Core endpoints and how to chain them:

- Tickets family (CSV of `ticket_id, account_id, service_type, ...`):
  - `GET /api/tickets/<ticket_id>` -> service_area, service_type, subscribed_mbps.
  - `GET /api/accounts/<account_id>` -> status (Active/Suspended), authentication block.
    A missing account returns `{"error":"not_found"}`.
  - `GET /api/diagnostics/<ticket_id>` -> pre-fix latency_ms, jitter_ms, bandwidth_mbps, root_causes[].
  - `GET /api/troubleshooting/<ticket_id>` -> steps[] and post_* metrics (after auto-fix).
  - `GET /api/outages?service_area=<area>` -> list (may be empty `[]`); each has
    active, service_types[], outage_id, eta_hours.
- Mobile cases family (case list of `case_id`):
  - `GET /api/cases` (or `/api/cases/<id>`) -> customer_id, line_id, device_id,
    issue_type, customer_location.
  - `GET /api/lines/<line_id>` -> status, suspension_reason, roaming_enabled,
    plan_id, data_used_gb.
  - `GET /api/devices/<device_id>` -> the device-state flags (see vocab below).
  - `GET /api/plans/<plan_id>` -> data_limit_gb, data_refueling_price_per_gb.
  - `GET /api/bills` -> filter by customer_id for status/amount_due_usd/bill_id.
  - `GET /api/customers` -> customer status/name (returns the full list; filter locally).
- Enterprise family (incident reference in the complaint):
  - `GET /api/enterprise/incidents/<incident_id>` -> enterprise_account_id, severity,
    product, engineering_owner, account_owner, status.
  - `GET /api/enterprise/accounts` -> finance_owner, account_owner, tier, name.
  - `GET /api/enterprise/export-runs?incident_id=<id>` -> per-day runs with status,
    failure_code, run_date.
  - `GET /api/enterprise/sla/<enterprise_account_id>` -> monthly_export_credit_percent,
    credit_trigger.
  - `GET /api/enterprise/messages?query=<text>` -> internal chatter; search by client
    name and by "alert"/"archive" to find contributing-alert evidence.

Always preserve the ID order required by the template (payload order for tickets;
ascending case_id for cases). Compute every summary count by tallying your own
per-item decisions — never eyeball it.

---

## SOP A — Offline ticket batch resolution
(template has per-ticket: final_resolution_status, diagnostic_needed/diagnostic_required,
issue flags, outage_id, escalation_team/route_team, resolution_route/key_blocker)

Evaluate each ticket with this precedence (first matching rule wins for status/route):

1. **Account invalid** — account lookup returns not_found ->
   status FAILED; route/team NONE; route INVALID_ACCOUNT; key_blocker INVALID_ACCOUNT;
   no diagnostic needed.
2. **Account Suspended** (`status: "Suspended"`) ->
   - If suspension is for an overdue bill / general hold: status FAILED; route/team
     NONE; route INELIGIBLE_ACCOUNT; key_blocker OVERDUE_SUSPENSION; no diagnostic.
3. **Authentication failed** (account.authentication.last_login_status == "FAILURE"
   or account_recovery_status == "FAILURE", report "authentication never recovered") ->
   status ESCALATED; route/team TIER2_SUPPORT; route ESCALATION; key_blocker AUTH_FAILED;
   no diagnostic.
4. **Active outage** covering this service_type in the ticket's service_area
   (`/api/outages?service_area=` returns an entry with `active:true` whose
   `service_types` includes the ticket's service_type) ->
   status PENDING_ACTION; route/team NONE; resolution_route OUTAGE_WAIT;
   key_blocker ACTIVE_OUTAGE; set outage_id to that outage; this ticket counts as a
   "customer wait"; no diagnostic.
5. **Otherwise run the diagnostic path** (account Active, no outage):
   - A real diagnostic drives the decision -> diagnostic_needed/required = true.
   - Inspect `root_causes[]`:
     - Physical-plant causes (FIBER_DROP_DAMAGE, SIGNAL_LOSS) ->
       status ESCALATED; team FIELD_OPS; route ESCALATION; key_blocker
       PHYSICAL_LINE_FAULT.
     - Backbone/network-capacity cause (BACKBONE_CAPACITY) ->
       status ESCALATED; team NETWORK_ENGINEERING; route ESCALATION; key_blocker
       NETWORK_CAPACITY.
     - Provisioning cause (PROVISIONING_STALE / CONFIGURATION_DRIFT) and a stale-profile
       fix step ran: judge by recovery (rule 6). CONFIGURATION_DRIFT that heals ->
       RESOLVED. PROVISIONING_STALE that does NOT fully heal -> ESCALATED to
       TIER2_SUPPORT, key_blocker PROVISIONING_STALE (do NOT downgrade to
       PENDING_ACTION/NONE — keep the team and the blocker).
     - Voice profile cause (VOICE_PROFILE_STALE) with VOICE_PROFILE_REFRESH that heals
       -> RESOLVED, team/route NONE, key_blocker NONE.
6. **Auto-resolution test** (when a real troubleshooting fix ran):
   Compare `post_*` metrics to health. The system is HEALED when post_latency_ms drops
   back to roughly < 100 ms (and jitter normalizes). If healed -> status RESOLVED,
   team/route NONE, key_blocker NONE. If post_latency_ms is still elevated (>~100 ms,
   e.g. only nudged 188->176 or 136->121) -> NOT resolved: escalate per the root-cause
   team above, and keep the matching key_blocker. Bandwidth that is merely below the
   subscribed rate does NOT by itself block RESOLVED (voice cases recover even with
   bandwidth under subscription); latency recovery is the primary signal.

### Decoy / noise diagnostics
A `root_causes` of `GENERATED_NOISE` paired with a `GENERATED_CHECK` troubleshooting
step is a filler/no-op diagnostic. It is NOT the real blocker. When such a ticket also
has a real upstream blocker (outage / invalid / auth / suspension), classify by the
upstream blocker and set diagnostic_needed/required = FALSE. Do not let GENERATED_NOISE
metrics fool you into AUTO_TROUBLESHOOTING.

### Issue flags (when the template asks for latency/stability/bandwidth booleans)
Derive these from the **pre-fix diagnostics** record, independent of the final status:
- `latency_issue` = diagnostics.latency_ms is high (roughly >= 100 ms).
- `stability_issue` = diagnostics.jitter_ms is high (roughly >= 30 ms).
- `bandwidth_issue` = diagnostics.bandwidth_mbps < ticket.subscribed_mbps.
  (Pitfall: set bandwidth_issue TRUE whenever measured bandwidth is below the
  subscribed rate even for an escalated/physical-fault ticket — do not zero the flags
  just because the ticket is escalated.)
For tickets short-circuited by outage/invalid/auth/suspension, the issue flags are all
false (no meaningful diagnostic was the basis of the decision) and outage_id is "" unless
rule 4 applied.

### Enum vocabularies (tickets)
- final_resolution_status: RESOLVED | PENDING_ACTION | ESCALATED | FAILED
- escalation_team / route_team: NONE | TIER2_SUPPORT | FIELD_OPS | NETWORK_ENGINEERING |
  ACCOUNTS_PAYABLE
- resolution_route: AUTO_TROUBLESHOOTING | OUTAGE_WAIT | ESCALATION | INELIGIBLE_ACCOUNT |
  AUTH_FAILED | INVALID_ACCOUNT
- key_blocker: NONE | ACTIVE_OUTAGE | INVALID_ACCOUNT | AUTH_FAILED | OVERDUE_SUSPENSION |
  FRAUD_SUSPENSION | NETWORK_CAPACITY | PROVISIONING_STALE | PHYSICAL_LINE_FAULT
- outage_id: the matching OUT-id, else "" (empty string, never null).

batch/queue summary: count each status, count each route_team used, and (tickets template)
`tickets_requiring_customer_wait` = number of OUTAGE_WAIT tickets.

---

## SOP B — Contact-center / mobile case triage
(template fields: primary_action, secondary_action, permission, bill_id,
charge_amount_usd, final_route — and the data-recovery variant: data_refuel_gb,
charge_amount_usd, carrier_update_required, final_route)

For each case, pull line + device (+ bill/plan when relevant), then map by the device
state, not the prose. Decision rules:

1. **Line Suspended for overdue bill** (line.status Suspended, suspension_reason
   OVERDUE_BILL; bill Overdue) -> primary SEND_PAYMENT_REQUEST, secondary
   RESUME_LINE_REBOOT, bill_id = that bill, charge_amount_usd = bill.amount_due_usd,
   final_route BILLING_RECOVERY.
2. **SIM missing / no service** (device.sim_status == "missing", signal "none") ->
   primary RESEAT_SIM, final_route SELF_SERVICE.
3. **MMS cannot send** (device.can_send_mms false): the blocker is a missing messaging
   permission. If storage permission is false -> GRANT_MESSAGING_PERMISSION with
   permission "storage" (use "sms", "storage", or "sms_and_storage" to match whichever
   permission(s) are false; "NONE" when none). final_route SELF_SERVICE.
4. **Slow data with VPN connected** (device.vpn_connected true) -> DISCONNECT_VPN,
   SELF_SERVICE.
5. **Roaming abroad, no data**:
   - line.roaming_enabled false (carrier side off) -> ENABLE_LINE_ROAMING,
     carrier_update_required true, final_route CARRIER_UPDATE.
   - line roaming on but device phone_roaming_enabled false -> TOGGLE_ROAMING
     (device toggle), final_route SELF_SERVICE / DEVICE_SETTING_FIX.
6. **Data stopped after usage limit** (line.data_used_gb >= plan.data_limit_gb) ->
   REFUEL_DATA. Refuel amount = customer's accepted_refuel_gb (from preferences) when
   given, else the gap needed. charge = refuel_gb * plan.data_refueling_price_per_gb,
   two decimals. final_route DATA_RECOVERY. Respect `does_not_want_plan_change`.
7. **Slow data, data-saver icon** (device.data_saver_mode true) -> TOGGLE_DATA_SAVER,
   DEVICE_SETTING_FIX.
8. **Slow data on old network mode** (device.network_mode_preference "3g_only") ->
   SET_NETWORK_MODE, DEVICE_SETTING_FIX.
9. **No data after settings change** (device.mobile_data_enabled false) ->
   TOGGLE_MOBILE_DATA, DEVICE_SETTING_FIX.
10. Nothing actionable / needs a person -> TRANSFER_HUMAN, HUMAN_TRANSFER.

Use NO_ACTION for secondary_action whenever no follow-up is needed.
Only REFUEL_DATA (and billing payment) produce a non-zero charge; everything else is
charge 0.00. Permissions field is NONE unless rule 3 applies. bill_id is "" unless a
bill is actually involved.

### Summary computation (mobile)
- self_service_fixes / device_setting_fixes = count of SELF_SERVICE / DEVICE_SETTING_FIX
  routes.
- billing_recoveries = BILLING_RECOVERY count; carrier_updates = CARRIER_UPDATE count;
  human_transfers = HUMAN_TRANSFER count; data_refuel_cases = DATA_RECOVERY count.
- total_estimated_customer_charge_usd = sum of every charge_amount_usd, two decimals.

### Enum vocabularies (mobile)
- actions (superset): TOGGLE_AIRPLANE_MODE, RESEAT_SIM, RESET_APN_REBOOT,
  SEND_PAYMENT_REQUEST, RESUME_LINE_REBOOT, TRANSFER_HUMAN, TOGGLE_MOBILE_DATA,
  TOGGLE_ROAMING, ENABLE_LINE_ROAMING, REFUEL_DATA, TOGGLE_DATA_SAVER, SET_NETWORK_MODE,
  DISCONNECT_VPN, GRANT_MESSAGING_PERMISSION, TOGGLE_WIFI_CALLING, NO_ACTION.
  (The data-recovery template exposes only the data-relevant subset — use only the enum
  values that template lists.)
- permission: NONE | sms | storage | sms_and_storage
- final_route (contact center): SELF_SERVICE | BILLING_RECOVERY | CARRIER_UPDATE |
  HUMAN_TRANSFER
- final_route (data recovery): DATA_RECOVERY | CARRIER_UPDATE | DEVICE_SETTING_FIX |
  HUMAN_TRANSFER

---

## SOP C — Enterprise export-complaint response package
(template: incident_id, enterprise_account_id, root_cause_category,
contributing_alert_issue, failure_window{start_date,end_date,failed_days}, backfill_days,
sla_credit_percent, severity, engineering_owner, account_owner, channel_name,
evidence_folder, report_title, share_permissions[], response_status)

Procedure:
1. Take the incident reference from the complaint email; confirm via
   `/api/enterprise/incidents/<id>` -> enterprise_account_id, severity, product,
   engineering_owner, account_owner.
2. `/api/enterprise/export-runs?incident_id=<id>` -> identify the consecutive FAILED
   runs. failure_window.start_date = first FAILED run_date, end_date = last FAILED
   run_date, failed_days = count of FAILED runs. The later SUCCEEDED run is the recovery,
   not a failure. backfill_days = number of failed days that must be manually
   re-run (= failed_days).
3. root_cause_category = the export-run `failure_code` corroborated by message evidence
   (e.g. a credential rotation that left a stale secret => stale credential).
4. contributing_alert_issue: search `/api/enterprise/messages` by client name and
   "alert"/"archive". If the alerting message landed in an archived alert channel
   (channel name containing "archive") so the team missed it ->
   ARCHIVED_ALERT_ROUTE. Else NONE (use UNKNOWN only if truly indeterminate).
5. sla_credit_percent = `/api/enterprise/sla/<enterprise_account_id>`
   monthly_export_credit_percent (an integer percent). Confirm the credit_trigger
   (e.g. "3 consecutive failed runs") is met.
6. severity = the incident's severity enum (Critical | High | Medium | Low).
7. engineering_owner / account_owner = incident's owner user ids. finance_owner comes
   from the enterprise account record (used for share permissions / finance review).
8. channel_name / evidence_folder / report_title: build from the response_requirements
   `naming_style` exactly (lowercase-hyphen channel; client+date investigation folder;
   "<Client> Export Failure Report" style title). Match the requested casing/format
   token-for-token; these are exact-string-scored and easy to lose points on.
9. share_permissions: include exactly the users in `permission_users_to_include`, in the
   listed order, each with a permission from {view, edit, upload_only}.
10. response_status: if a financial SLA credit must be approved before sending ->
    NEEDS_FINANCE_REVIEW; if engineering sign-off is still pending ->
    NEEDS_ENGINEERING_REVIEW; if the incident is still being investigated ->
    UNDER_INVESTIGATION; only READY_TO_SEND when nothing is outstanding.

Reliable fields here: incident_id, enterprise_account_id, owners, the failure window
dates+count, sla_credit_percent, severity, and contributing_alert_issue. The free-text
artifact strings (channel_name, evidence_folder, report_title) and share-permission
levels are exact-match and the biggest risk — derive them strictly from the provided
naming_style and user list rather than inventing your own convention.

---

## Output-format discipline (all task families)
- Return ONLY the JSON object conforming to the task's `answer_template.json`. No prose,
  no markdown fences, no extra keys.
- Preserve the exact ID ordering the template demands.
- Enums must match the template spelling EXACTLY (uppercase enum tokens, exact casing of
  severity/permission). A near-synonym scores as wrong.
- Numbers: money to two decimals, data_refuel_gb to one decimal, integers for counts and
  percents. Use 0.0 / 0.00 (not null) when "not applicable"; use "" (empty string, not
  null) for not-applicable string/ID fields.
- Recompute all summary counts from your own per-item decisions so they are internally
  consistent.
- Booleans are real JSON booleans, not strings.

## Pitfalls learned (reusable)
- bandwidth_issue depends only on measured-vs-subscribed; it stays TRUE on escalated
  physical-fault tickets too. Do not blank issue flags just because a ticket escalates.
- A PROVISIONING_STALE ticket whose auto-fix leaves latency still elevated escalates to
  TIER2_SUPPORT and KEEPS the PROVISIONING_STALE blocker — it is not PENDING_ACTION and
  not NONE. Auto-resolution requires genuine metric recovery (latency back under ~100ms).
- GENERATED_NOISE root cause + GENERATED_CHECK step = decoy; the real classification comes
  from the upstream blocker, and diagnostic_required is false for those tickets.
- For enterprise packages, the deterministic API-derived fields are dependable; sink your
  effort into matching the requested naming conventions and permission levels exactly,
  since those exact-string fields are where points silently leak.
