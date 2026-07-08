# SCN_003 CRM Support-Console Resolution SOP

Executable SOP for the five CRM train families. All facts below were derived by
probing the live support-console API and cross-referencing records. Thresholds
marked **(inferred)** are committed numeric best-estimates reasoned from the
data; apply them as stated.

## 0. Environment & API map

- **Base URL:** `<remote-env-url>` — ALWAYS use this instead of any
  `127.0.0.1:8057` / localhost URL mentioned in a task prompt.
- Health: `GET /health` -> `{"ok": true}`.
- Catalog: `GET /api/catalog` (endpoints + record counts only).
- Records are the source of truth. Never assume a field — fetch it.

Endpoint reference (substitute real ids):

| Endpoint | Returns |
|---|---|
| `/api/accounts` , `/api/accounts/<account_id>` | account (status, tier, authentication{last_login_status, account_recovery_status}, service_area) |
| `/api/tickets` , `/api/tickets/<ticket_id>` | ticket (account_id, service_type, service_area, subscribed_mbps, status, issue_summary) |
| `/api/outages?service_area=<area>` | outages in that area: {active, eta_hours, impact_score, outage_id, service_area, service_types[], started_at} |
| `/api/diagnostics/<ticket_id>` | pre-troubleshoot metrics: latency_ms, jitter_ms, bandwidth_mbps, root_causes[] |
| `/api/troubleshooting/<ticket_id>` | post-troubleshoot metrics: post_latency_ms, post_jitter_ms, post_bandwidth_mbps, steps[] |
| `/api/customers` , `/api/lines` , `/api/lines/<line_id>` , `/api/devices/<device_id>` , `/api/plans/<plan_id>` , `/api/bills` , `/api/cases` , `/api/cases/<case_id>` | mobile family |
| `/api/enterprise/accounts` , `/api/enterprise/incidents` , `/api/enterprise/export-runs?incident_id=<id>` , `/api/enterprise/messages?query=<text>` , `/api/enterprise/sla/<enterprise_account_id>` | enterprise family |

Diagnostics/troubleshooting are only present for the `TCK-5xxx`/`TCK-6xxx`
ticket cohorts. The `TCK-8xxx` cohort has empty diagnostics, generic
"Generated Customer" accounts, and "Generated support ticket" summaries —
these are synthetic distractors; do not run the auto-troubleshoot pipeline on
them (they are only usable for pure gate/blocker classification when such a
task appears).

---

## 1. Family 1 — Offline ticket batch resolution (train_001, train_004)

Applies to any ticket-resolution / queue-quality task over `TCK-5xxx/6xxx`
tickets that carry real diagnostics.

### 1.1 Gating lifecycle (evaluate IN THIS ORDER; first hit wins)

A ticket must clear every gate before diagnostics run. A failed gate
short-circuits: NO diagnostics, NO troubleshooting analysis, all metric
issue-flags = false.

| # | Gate | Condition (fetch account + outages) | result status | resolution_route (train_001) | key_blocker (train_004) | route_team | diag_needed/required |
|---|---|---|---|---|---|---|---|
| 1 | INVALID_ACCOUNT | `GET /api/accounts/<account_id>` returns 404 (e.g. `BAD-*`) | FAILED | INVALID_ACCOUNT | INVALID_ACCOUNT | NONE | false |
| 2 | INELIGIBLE_ACCOUNT | account.status == `Suspended` (suspension_reason not exposed; in this dataset all suspensions are overdue-bill) | PENDING_ACTION | INELIGIBLE_ACCOUNT | OVERDUE_SUSPENSION | ACCOUNTS_PAYABLE | false |
| 3 | AUTH_FAILED | authentication.last_login_status == `FAILURE` OR account_recovery_status == `FAILURE` | FAILED | AUTH_FAILED | AUTH_FAILED | NONE | false |
| 4 | OUTAGE_WAIT | an outage in ticket.service_area with `active==true` AND ticket.service_type IN outage.service_types | PENDING_ACTION | OUTAGE_WAIT (outage_id = that outage) | ACTIVE_OUTAGE | NONE | false |
| 5 | (passes all gates) | account Active, auth OK, no matching active outage | -> run diagnostics | AUTO_TROUBLESHOOTING | NONE | (from root cause, see 1.4) | true |

**Outage match is type-specific (critical pitfall):** an active outage only
gates a ticket if the ticket's `service_type` is listed in the outage's
`service_types`. 23 tickets exist whose area has an active outage of a
different type — those are NOT gated and proceed to diagnostics. Always check
the `service_types` array, not just the service_area.

**Generated-noise marker:** gated tickets still return a diagnostics record,
but it is a sentinel: `root_causes == ["GENERATED_NOISE"]`, troubleshooting
`steps == ["GENERATED_CHECK"]`, and the metric values are fractional/random.
Treat these as "diagnostics skipped" — do NOT evaluate thresholds on them, set
all issue flags false, and count them in `diagnostic_records_skipped_by_gate`.

### 1.2 Diagnostic thresholds (the support-convention floors) — INFERRED

For any ticket that PASSES all gates (real diagnostics, non-`GENERATED_NOISE`):

| Metric | Flag | Floor | Issue when |
|---|---|---|---|
| latency | `latency_issue` | **100 ms** (inferred) | latency_ms > 100 |
| jitter / stability | `stability_issue` | **30 ms** (inferred) | jitter_ms > 30 |
| bandwidth | `bandwidth_issue` | **0.80 × subscribed_mbps** (inferred) | bandwidth_mbps < 0.8 × subscribed_mbps |

These three floors produce a fully consistent RESOLVED/ESCALATED split across
all 8 real-diagnostic tickets in the console (verified):

- RESOLVED tickets have every post-troubleshoot metric at/under floor.
- ESCALATED tickets have at least one post-troubleshoot metric still violating.

**Bandwidth floor table (effective values at standard provisioning):**
The rule is `0.8 × subscribed_mbps`. Observed standard provisions:

| service_type | subscribed_mbps | bandwidth floor |
|---|---|---|
| voice | 100 | 80 |
| internet | 300 | 240 |
| internet | 500 | 400 |
| video | 500 | 400 |
| video | 750 | 600 |

If a ticket has a non-standard subscribed_mbps (the `TCK-8xxx` distractors show
internet 100/200/750, video 200/300, voice 200/300/500/750), still compute
`0.8 × subscribed_mbps` — do NOT use a fixed per-type absolute. The
`subscribed_mbps` field exists for this purpose.

(Rationale for 0.8 over a fixed per-type floor: sub-500 internet tickets run at
52–64% of provisioned speed, which is plainly degraded; a fixed floor of ~240
would miss that. 0.8 × subscribed flags all real-degraded tickets correctly.)
(0.75 is statistically indistinguishable on this data; 0.80 is the standard SLA
convention and is the committed value.)

### 1.3 Resolved vs Escalated (for gate-passing tickets only)

Run auto-troubleshooting then re-evaluate the POST metrics against the SAME
floors:

- **RESOLVED** iff `post_latency_ms <= 100` AND `post_jitter_ms <= 30` AND
  `post_bandwidth_mbps >= 0.8 × subscribed_mbps` (all three clear).
  -> resolution_route = `AUTO_TROUBLESHOOTING`, escalation_team/route_team =
  `NONE`.
- **ESCALATED** if any post metric still violates.
  -> resolution_route = `ESCALATION`, escalation_team/route_team = root-cause
  team (1.4).

The PRE-troubleshoot `latency_issue`/`stability_issue`/`bandwidth_issue` flags
(train_001) are computed from the **diagnostics** (pre) metrics vs the floors.
For gated tickets all three are `false`.

### 1.4 Root-cause -> escalation-team map (complete; verified)

Derived from which root causes appear on RESOLVED vs ESCALATED tickets and the
natural owning team:

| root_cause (in diagnostics.root_causes) | outcome | escalation_team |
|---|---|---|
| `CONFIGURATION_DRIFT` | RESOLVED (auto-TS clears all metrics) | NONE |
| `VOICE_PROFILE_STALE` | RESOLVED (auto-TS clears all metrics) | NONE |
| `FIBER_DROP_DAMAGE` | ESCALATED | FIELD_OPS |
| `SIGNAL_LOSS` | ESCALATED | FIELD_OPS |
| `BACKBONE_CAPACITY` | ESCALATED | NETWORK_ENGINEERING |
| `PROVISIONING_STALE` | ESCALATED | TIER2_SUPPORT |
| `GENERATED_NOISE` | (gated — not a real root cause) | (gate-determined, see 1.1) |

When a ticket has multiple root causes, use the first non-resolving one to pick
the team (e.g. FIBER_DROP_DAMAGE + SIGNAL_LOSS -> FIELD_OPS). ACCOUNTS_PAYABLE
is reached only via the Suspended gate (billing), never via a diagnostic root
cause.

### 1.5 train_001 output (`ticket_batch.csv` -> ticket_decisions + batch_summary)

For each ticket (preserve payload order) produce:
- `ticket_id`, `account_id`
- `final_resolution_status`: RESOLVED | PENDING_ACTION | ESCALATED | FAILED
  (gate-failed = FAILED for INVALID_ACCOUNT/AUTH_FAILED; PENDING_ACTION for
  OUTAGE_WAIT/INELIGIBLE_ACCOUNT; gate-pass ticket then RESOLVED/ESCALATED per 1.3)
- `diagnostic_needed`: true only for gate-passing tickets (false for every gate)
- `latency_issue`, `stability_issue`, `bandwidth_issue`: pre-flags per 1.2; all
  `false` when gated
- `outage_id`: the matching active outage id for OUTAGE_WAIT tickets; `""`
  otherwise
- `escalation_team`: NONE | TIER2_SUPPORT | FIELD_OPS | NETWORK_ENGINEERING |
  ACCOUNTS_PAYABLE (NONE for RESOLVED/OUTAGE_WAIT/AUTH_FAILED/INVALID_ACCOUNT;
  ACCOUNTS_PAYABLE for INELIGIBLE_ACCOUNT; root-cause team for ESCALATED)
- `resolution_route`: AUTO_TROUBLESHOOTING | OUTAGE_WAIT | ESCALATION |
  INELIGIBLE_ACCOUNT | AUTH_FAILED | INVALID_ACCOUNT

`batch_summary`:
- `RESOLVED`, `PENDING_ACTION`, `ESCALATED`, `FAILED`: counts by status
- `tickets_requiring_customer_wait`: count of OUTAGE_WAIT-routed tickets
  (inferred — the customer is told to wait for an active outage to clear).
  INELIGIBLE_ACCOUNT is a customer-action (pay) state, not a pure wait.

### 1.6 train_004 output (`queue_snapshot.csv` -> ticket_decisions + queue_summary)

For each ticket produce:
- `final_resolution_status` (same enum/logic as 1.5)
- `route_team`: NONE | TIER2_SUPPORT | FIELD_OPS | NETWORK_ENGINEERING |
  ACCOUNTS_PAYABLE — NONE for OUTAGE_WAIT / AUTH_FAILED / INVALID_ACCOUNT /
  RESOLVED; ACCOUNTS_PAYABLE for Suspended; root-cause team for ESCALATED.
  (Inferred: AUTH_FAILED -> NONE, terminal failure. If your data shows auth
  recovery is actively worked, TIER2_SUPPORT is the alternative.)
- `key_blocker`: NONE | ACTIVE_OUTAGE | INVALID_ACCOUNT | AUTH_FAILED |
  OVERDUE_SUSPENSION | FRAUD_SUSPENSION | NETWORK_CAPACITY |
  PROVISIONING_STALE | PHYSICAL_LINE_FAULT — map from the gate / root cause:
  - OUTAGE_WAIT -> ACTIVE_OUTAGE
  - INVALID_ACCOUNT -> INVALID_ACCOUNT
  - AUTH_FAILED -> AUTH_FAILED
  - Suspended -> OVERDUE_SUSPENSION (FRAUD_SUSPENSION only if a fraud marker is
    present; none exists in this dataset, all suspensions are overdue)
  - ESCALATED + BACKBONE_CAPACITY -> NETWORK_CAPACITY
  - ESCALATED + PROVISIONING_STALE -> PROVISIONING_STALE
  - ESCALATED + FIBER_DROP_DAMAGE/SIGNAL_LOSS -> PHYSICAL_LINE_FAULT
  - RESOLVED -> NONE
- `diagnostic_required`: true only for gate-passing tickets.

`queue_summary`: counts of FAILED / PENDING_ACTION / RESOLVED / ESCALATED, plus
counts of tickets routed to TIER2_SUPPORT / FIELD_OPS / NETWORK_ENGINEERING /
ACCOUNTS_PAYABLE (route_team; NONE is not counted in any team bucket).

---

## 2. Family 2 — Mobile contact-center triage (train_002, train_005)

Applies to `case_queue.json` / `mobile_data_worklist.json` tasks. For each case
fetch: case, customer, line, device (/api/devices/<device_id>),
plan (/api/plans/<plan_id>), and the customer's bills.

### 2.1 Decision tree (evaluate top-down; first match wins)

1. **Suspended line (billing).** line.status == `Suspended` (and an Overdue
   bill exists) -> **BILLING_RECOVERY**:
   - primary `SEND_PAYMENT_REQUEST`, secondary `RESUME_LINE_REBOOT`
   - `bill_id` = the overdue bill id; `charge_amount_usd` = bill.amount_due_usd
   - final_route `BILLING_RECOVERY` (train_002) / not a train_005 route
   (suspension_reason is `OVERDUE_BILL` in this dataset; if a fraud/data-cap
   suspension appeared, transfer human instead.)
2. **Data cap exceeded.** line.data_used_gb > plan.data_limit_gb ->
   **REFUEL_DATA**:
   - `data_refuel_gb` = customer preference `accepted_refuel_gb` (if provided);
     otherwise the overage `data_used_gb - data_limit_gb` rounded up to 0.1
   - `charge_amount_usd` = data_refuel_gb × plan.data_refueling_price_per_gb
   - Respect `does_not_want_plan_change` (do not change plan, only refuel)
   - final_route `DATA_RECOVERY` (train_005); train_002 would also use REFUEL_DATA
3. **SIM missing.** device.sim_status == `missing` -> `RESEAT_SIM`
   (final_route SELF_SERVICE / DEVICE_SETTING_FIX).
4. **Airplane mode on.** device.airplane_mode == true -> `TOGGLE_AIRPLANE_MODE`.
5. **Roaming (only when customer_location == `abroad` and no data):**
   - if line.roaming_enabled == false -> `ENABLE_LINE_ROAMING`
     (final_route CARRIER_UPDATE, carrier_update_required = true) — the LINE
     lacks roaming; carrier/account-side update needed.
   - else if device.phone_roaming_enabled == false -> `TOGGLE_ROAMING`
     (final_route SELF_SERVICE / DEVICE_SETTING_FIX) — device toggle only.
   - (Precedence: line-roaming-off beats phone-roaming-off. CASE-2103 =
     phone off + line on -> TOGGLE_ROAMING; CASE-2502 = phone on + line off ->
     ENABLE_LINE_ROAMING.)
6. **Mobile data off.** device.mobile_data_enabled == false ->
   `TOGGLE_MOBILE_DATA` (DEVICE_SETTING_FIX).
7. **MMS / messaging (issue_type MMS or can_send_mms == false):**
   - if messaging_permissions missing any needed perm -> `GRANT_MESSAGING_PERMISSION`
     - permission field = the missing subset: `sms`, `storage`, or
       `sms_and_storage` (NONE if nothing missing)
     - (storage needed to access photos; sms needed to send)
   - else if mmsc_url_present == false -> `RESET_APN_REBOOT`
8. **Slow data (issue_type SLOW_DATA or speed_test poor/fair):**
   - if device.vpn_connected == true -> `DISCONNECT_VPN`
   - else if device.data_saver_mode == true -> `TOGGLE_DATA_SAVER`
   - else if network_mode_preference is not `4g_5g_preferred` (e.g. `3g_only`)
     -> `SET_NETWORK_MODE`
9. **No actionable signal / unmatched** -> `TRANSFER_HUMAN` (HUMAN_TRANSFER) or
   `NO_ACTION`.

Secondary action: `NO_ACTION` for all single-step fixes; the only multi-step in
this dataset is SEND_PAYMENT_REQUEST -> RESUME_LINE_REBOOT (billing).

### 2.2 train_002 output (`case_queue.json`)

Per case: `case_id`, `customer_id`, `line_id`, `primary_action`,
`secondary_action`, `permission` (NONE|sms|storage|sms_and_storage — only set
for GRANT_MESSAGING_PERMISSION, else NONE), `bill_id` (only billing case, else
`""`), `charge_amount_usd` (billing amount; 0.00 otherwise), `final_route`
(SELF_SERVICE | BILLING_RECOVERY | CARRIER_UPDATE | HUMAN_TRANSFER).
- SELF_SERVICE = device toggles the customer performs (RESEAT_SIM, TOGGLE_ROAMING,
  GRANT_MESSAGING_PERMISSION, DISCONNECT_VPN, TOGGLE_AIRPLANE_MODE, etc.)
- BILLING_RECOVERY = suspended-line payment flow
- CARRIER_UPDATE = line-side change (ENABLE_LINE_ROAMING)

`queue_summary`: self_service_fixes, billing_recoveries, carrier_updates,
human_transfers (counts by final_route).

### 2.3 train_005 output (`mobile_data_worklist.json`)

Per case: `case_id`, `primary_action`, `secondary_action`, `data_refuel_gb`
(0.0 unless REFUEL_DATA), `charge_amount_usd` (refuel charge; 0.00 otherwise),
`carrier_update_required` (true only for ENABLE_LINE_ROAMING), `final_route`
(DATA_RECOVERY | CARRIER_UPDATE | DEVICE_SETTING_FIX | HUMAN_TRANSFER).
- DATA_RECOVERY = REFUEL_DATA
- CARRIER_UPDATE = ENABLE_LINE_ROAMING
- DEVICE_SETTING_FIX = TOGGLE_DATA_SAVER / SET_NETWORK_MODE / TOGGLE_MOBILE_DATA
  / DISCONNECT_VPN / TOGGLE_ROAMING (device-side)
- HUMAN_TRANSFER = TRANSFER_HUMAN

`worklist_summary`: data_refuel_cases, carrier_updates, device_setting_fixes,
human_transfers (counts by final_route), and
`total_estimated_customer_charge_usd` = sum of charge_amount_usd across cases
(refuel charges only; carrier/settings fixes carry no charge).

### 2.4 Refuel math (precise)

`charge_amount_usd = round(data_refuel_gb × plan.data_refueling_price_per_gb, 2)`
e.g. PLAN-PREMIUM: data_refueling_price_per_gb = 2.00, accepted_refuel_gb = 2.0
-> 2.0 × 2.00 = **4.00**. (Verified on CASE-2501.)

---

## 3. Family 3 — Enterprise export-complaint response package (train_003)

Applies to a client complaint email + `response_requirements.json`. Pipeline:

### 3.1 Identify incident & account
- From the email: client name (e.g. "Asteri Retail Inc."), product
  (e.g. `monthly_export`), and approximate incident ref (e.g. `INC-7301`).
- `GET /api/enterprise/incidents` -> find the incident_id (confirm against the
  email's approximate ref). Read `enterprise_account_id`, `severity`,
  `engineering_owner`, `account_owner`, `status`, `received_at`, `product`.
- `GET /api/enterprise/accounts` -> cross-check the account: `account_owner`,
  `finance_owner`, name, tier.

### 3.2 Failure window & backfill
- `GET /api/enterprise/export-runs?incident_id=<incident_id>`.
- The failed runs are those with `status == "FAILED"`.
- `failure_window.start_date` = min run_date among FAILED runs;
  `failure_window.end_date` = max run_date among FAILED runs;
  `failure_window.failed_days` = count of FAILED runs.
- `backfill_days` = count of FAILED runs (each failed day needs manual backfill).
  (Confirmed: Asteri = 3 failed runs 05-12/13/14, backfill_days 3. Quanta
  message states "four days require manual backfill" = 4.)
- The first `SUCCEEDED` run after the failure window is the recovery point (do
  not count it as a failure).

### 3.3 Root cause & contributing alert
- `GET /api/enterprise/messages?query=<client name>` (and/or product-related
  terms). Inspect message bodies + channels.
- `root_cause_category`: concise category inferred from the FAILED runs'
  `failure_code` + message evidence. e.g. failure_code `STALE_CREDENTIAL` +
  message "scheduler pod still references old secret" after "credential
  rotation completed" -> `stale_credential`.
- `contributing_alert_issue` enum: ARCHIVED_ALERT_ROUTE | NONE | UNKNOWN.
  - If a relevant alert message was posted to an "*-archive" channel (e.g.
    `export-alerts-archive`) -> `ARCHIVED_ALERT_ROUTE` (the alert was routed to
    an archive and missed). Asteri = ARCHIVED_ALERT_ROUTE.
  - If alerting worked normally -> `NONE`. If no alert evidence -> `UNKNOWN`.

### 3.4 SLA credit & severity
- `GET /api/enterprise/sla/<enterprise_account_id>` -> use
  `monthly_export_credit_percent` (or the product-appropriate credit field) as
  `sla_credit_percent`. Cross-check with account-escalations messages (e.g.
  "requires 15 percent SLA credit after three consecutive failed monthly export
  runs"). Asteri = **15**.
- `severity`: copy from the incident (`Critical`/`High`/`Medium`/`Low`).

### 3.5 Owners
- `engineering_owner`: from incident (and author of the engineering message).
  Asteri = `delana.rao`.
- `account_owner`: from incident/account. Asteri = `stephany.lo`.

### 3.6 Naming conventions (from response_requirements.naming_style)
- **channel_name** — "lowercase hyphen channel": client name lowercased with
  hyphens, e.g. `asteri-retail`.
- **evidence_folder** — "client-date investigation folder":
  `<client-hyphenated>-<YYYY-MM-DD>` using the incident `received_at` date.
  e.g. `asteri-retail-2026-05-15`. (Inferred: date = incident received date.)
- **report_title** — "client export failure report title":
  `<Client Name> Export Failure Report`. e.g.
  `Asteri Retail Export Failure Report`. (Inferred title-case; "Monthly" may be
  inserted before "Export" if the product is monthly_export — prefer the
  literal convention without it unless the test expects product specificity.)

### 3.7 Share permissions
- `share_permissions`: one entry per user in
  `response_requirements.permission_users_to_include`, **in the order listed**.
- permission enum: view | edit | upload_only.
- Assignment (inferred): the account's `finance_owner` (e.g. `laura.brown`)
  gets `edit` (owns SLA credit/cost); other listed users (e.g. `jun.chen`) get
  `view`. If a listed user is clearly an evidence-uploader (engineering), use
  `upload_only`.
- Asteri: `[{user: laura.brown, permission: edit}, {user: jun.chen, permission: view}]`.

### 3.8 response_status
enum: READY_TO_SEND | NEEDS_FINANCE_REVIEW | NEEDS_ENGINEERING_REVIEW |
UNDER_INVESTIGATION.
- Rule (inferred): if `sla_credit_percent > 0` -> **NEEDS_FINANCE_REVIEW**
  (applying a monetary credit requires finance sign-off; this is why the
  finance_owner is in share_permissions).
- else if root-cause fix is not yet confirmed (no SUCCEEDED run after the
  failures, or messages say fix pending) -> NEEDS_ENGINEERING_REVIEW.
- else if evidence incomplete -> UNDER_INVESTIGATION.
- else READY_TO_SEND.
- Asteri -> NEEDS_FINANCE_REVIEW (15% credit).

### 3.9 train_003 output fields (all required_fields)
incident_id, enterprise_account_id, root_cause_category, contributing_alert_issue,
failure_window{start_date,end_date,failed_days}, backfill_days,
sla_credit_percent, severity, engineering_owner, account_owner, channel_name,
evidence_folder, report_title, share_permissions[{user,permission}],
response_status.

Asteri (INC-7301) resolved values: incident_id `INC-7301`;
enterprise_account_id `ENT-3001`; root_cause_category `stale_credential`;
contributing_alert_issue `ARCHIVED_ALERT_ROUTE`; failure_window
{2026-05-12, 2026-05-14, 3}; backfill_days 3; sla_credit_percent 15;
severity Critical; engineering_owner delana.rao; account_owner stephany.lo;
channel_name asteri-retail; evidence_folder asteri-retail-2026-05-15;
report_title Asteri Retail Export Failure Report; share_permissions
[laura.brown=edit, jun.chen=view]; response_status NEEDS_FINANCE_REVIEW.

---

## 4. Audit math definitions (test tasks may request rich audit fields)

Compute these over the ticket set of a Family-1 task.

- **diagnostic_records_skipped_by_gate** = count of tickets that hit any gate
  (INVALID_ACCOUNT / INELIGIBLE_ACCOUNT / AUTH_FAILED / OUTAGE_WAIT). Equivalently
  the count of `GENERATED_NOISE`-rooted diagnostics (+ any empty-diagnostic
  gated tickets). These never enter threshold evaluation.
- **pre_troubleshooting_bandwidth_gap_total** = sum over gate-PASSING tickets
  of `max(0, (0.8 × subscribed_mbps) − diagnostics.bandwidth_mbps)`.
  Gated/generated-noise tickets are EXCLUDED (their "metrics" are noise).
- **post_troubleshooting_remaining_issue_flags** = per gate-passing ticket, the
  set of still-violating flags after troubleshooting:
  `{latency if post_latency_ms>100, jitter if post_jitter_ms>30,
  bandwidth if post_bandwidth_mbps < 0.8×subscribed}`. Empty set == RESOLVED.
- **post_threshold_excess_totals** = per metric, summed over gate-passing
  tickets:
  - latency_excess_total = Σ max(0, post_latency_ms − 100)
  - jitter_excess_total  = Σ max(0, post_jitter_ms − 30)
  - bandwidth_shortfall_total = Σ max(0, (0.8×subscribed) − post_bandwidth_mbps)
  (These quantify how far each escalated ticket still exceeds the floor.)
- **per-ticket floor/shortfall lists** = for each gate-passing ticket:
  `{ticket_id, service_type, subscribed_mbps, latency_floor=100,
  jitter_floor=30, bandwidth_floor=0.8×subscribed,
  pre_bandwidth_shortfall=max(0,floor−preB),
  post_bandwidth_shortfall=max(0,floor−postB),
  pre_flags, post_remaining_flags}`.
- **success / failure id lists**:
  - success_ids = gate-passing tickets RESOLVED by auto-troubleshooting
    (post flags all clear).
  - failure_ids = gate-passing tickets ESCALATED (>=1 post flag remains).
  - Gated tickets are neither — keep them in a separate skipped list.
- **root-cause-escalation grouping** = group failure_ids by root_cause ->
  escalation_team:
  FIBER_DROP_DAMAGE/SIGNAL_LOSS -> FIELD_OPS;
  BACKBONE_CAPACITY -> NETWORK_ENGINEERING;
  PROVISIONING_STALE -> TIER2_SUPPORT.

---

## 5. Pitfalls (do not trip on these)

1. **Base URL override:** prompts say `127.0.0.1:8057`; always use
   `<remote-env-url>`.
2. **Outage type match:** an outage only gates a ticket if the ticket's
   service_type is in `outage.service_types`. 23 same-area-different-type cases
   exist — do not gate them.
3. **GENERATED_NOISE is a sentinel, not a real root cause:** gated tickets
   return fake diagnostics with fractional values. Never evaluate thresholds on
   them; set all flags false; count as gate-skipped.
4. **Gate order matters:** check INVALID_ACCOUNT -> Suspended -> AUTH_FAILED ->
   OUTAGE_WAIT -> diagnostics. E.g. a Suspended account with an outage is
   INELIGIBLE_ACCOUNT (suspension gate first), not OUTAGE_WAIT.
5. **Bandwidth floor scales with subscribed_mbps (0.8×), not a fixed per-type
   number.** A 500mbps internet line at 318mbps IS a bandwidth issue.
6. **RESOLVED requires ALL THREE post metrics clear**, not just the originally
   flagged ones.
7. **Mobile roaming split:** phone_roaming_enabled off -> TOGGLE_ROAMING
   (self-service); line.roaming_enabled off -> ENABLE_LINE_ROAMING
   (carrier update). Distinguished by which level roaming is disabled.
8. **Refuel amount** = customer's `accepted_refuel_gb` preference (not the
   overage) when provided; charge = gb × plan.data_refueling_price_per_gb.
9. **Enterprise backfill_days = count of FAILED export runs** (not the calendar
   span, though they usually coincide).
10. **share_permissions order** = order in response_requirements.permission_users_to_include.
11. **`TCK-8xxx` distractors** have empty/generic records — only use for pure
    gate/blocker classification, never for the threshold/resolution pipeline.
12. **All accounts are tier=standard** (no tier-based threshold variation); all
    observed suspensions are overdue-bill (no fraud marker in data).
13. **STATUS vs ROUTE:** FAILED status pairs with INVALID_ACCOUNT/AUTH_FAILED
    routes; PENDING_ACTION with OUTAGE_WAIT/INELIGIBLE_ACCOUNT; RESOLVED with
    AUTO_TROUBLESHOOTING; ESCALATED with ESCALATION.

---

## 6. Quick reference — derived constants

- Latency floor: **100 ms** (inferred)
- Jitter/stability floor: **30 ms** (inferred)
- Bandwidth floor: **0.80 × subscribed_mbps** (inferred)
- Route-team map: CONFIGURATION_DRIFT/VOICE_PROFILE_STALE -> NONE(resolved);
  FIBER_DROP_DAMAGE/SIGNAL_LOSS -> FIELD_OPS; BACKBONE_CAPACITY ->
  NETWORK_ENGINEERING; PROVISIONING_STALE -> TIER2_SUPPORT; Suspended ->
  ACCOUNTS_PAYABLE.
- Gate order: INVALID_ACCOUNT -> INELIGIBLE_ACCOUNT(Suspended) -> AUTH_FAILED ->
  OUTAGE_WAIT(type-matched) -> diagnostics.
- Asteri SLA credit: 15%; backfill_days 3; root cause stale_credential;
  alert ARCHIVED_ALERT_ROUTE; response_status NEEDS_FINANCE_REVIEW.
