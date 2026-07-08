# SCN_003 CRM Support-Operations Skill

Reusable SOP for resolving CRM support-console batches across three task
families: (1) ticket-batch resolution, (2) mobile triage, (3) enterprise
export-complaint response packages. All facts below are distilled from gold
answers + live API probes and are intended for a downstream solver.

## 0. Environment & API base

- Prompts reference `http://127.0.0.1:8057` — ALWAYS replace with the real
  base URL: **`<remote-env-url>`**.
- Health: `GET /health` -> `{"ok": true}`.
- Catalog: `GET /api/catalog` (endpoints + record counts only).
- Records are the source of truth; never assume a field exists. Probe to confirm.

### API endpoint map (substitute real ids)

| Resource | Endpoint |
|---|---|
| Accounts | `GET /api/accounts` , `GET /api/accounts/<account_id>` |
| Tickets | `GET /api/tickets` , `GET /api/tickets/<ticket_id>` |
| Outages | `GET /api/outages` , `GET /api/outages?service_area=<area>` |
| Diagnostics (pre) | `GET /api/diagnostics/<ticket_id>` |
| Troubleshooting (post) | `GET /api/troubleshooting/<ticket_id>` |
| Mobile customers | `GET /api/customers` , `GET /api/customers/<customer_id>` |
| Mobile lines | `GET /api/lines` , `GET /api/lines/<line_id>` |
| Mobile devices | `GET /api/devices/<device_id>` |
| Mobile plans | `GET /api/plans` , `GET /api/plans/<plan_id>` |
| Mobile cases / bills | `GET /api/bills` , `GET /api/cases` , `GET /api/cases/<case_id>` , `GET /api/bills/<bill_id>` |
| Enterprise accounts | `GET /api/enterprise/accounts` |
| Enterprise incidents | `GET /api/enterprise/incidents` |
| Enterprise export-runs | `GET /api/enterprise/export-runs?incident_id=<incident_id>` |
| Enterprise messages | `GET /api/enterprise/messages?query=<text>` |
| Enterprise SLA | `GET /api/enterprise/sla/<enterprise_account_id>` |

Key record shapes (probe to confirm; do not hard-code):
- `GET /api/tickets/<id>` -> `{ticket_id, account_id, service_area, service_type, subscribed_mbps, status, issue_summary, created_at}`. **`subscribed_mbps` and `service_type` live here** and drive the bandwidth floor.
- `GET /api/accounts/<id>` -> `{account_id, name, service_area, status, tier, authentication:{last_login_status, account_recovery_status, last_login_at}}`. 404 body `{"error":"not_found"}` means invalid account.
- `GET /api/diagnostics/<id>` -> `{ticket_id, bandwidth_mbps, latency_ms, jitter_ms, root_causes:[...], started_at, completed_at}`.
- `GET /api/troubleshooting/<id>` -> `{ticket_id, post_bandwidth_mbps, post_latency_ms, post_jitter_ms, steps:[...], started_at, completed_at}`.
- `GET /api/outages?service_area=<area>` -> list of `{outage_id, service_area, service_types:[...], active, eta_hours, impact_score, started_at}`.

---

## 1. Family A — Ticket-batch resolution (train_001 / train_004)

Input: a CSV (`ticket_batch.csv` / `queue_snapshot.csv`) listing `ticket_id,
account_id, reported_service_type, customer_report/queue_note`. Resolve every
ticket from console records, not from the note text alone. Output JSON per the
provided `answer_template.json` (two schema variants exist — see §1.6).

### 1.1 Gating order (apply in this exact sequence per ticket)

1. **Account gate** (FAILED route — skip diagnostics):
   a. `GET /api/accounts/<account_id>` returns 404 -> **INVALID_ACCOUNT**.
      `final_resolution_status=FAILED`, `diagnostic_needed=false`.
   b. `authentication.last_login_status == "FAILURE"` (or
      `account_recovery_status == "FAILURE"`) -> **AUTH_FAILED**.
      `FAILED`, `diagnostic_needed=false`.
   c. `status == "Suspended"`:
      - If the ticket note/report text contains "overdue" (overdue notice) ->
        **OVERDUE_SUSPENSION**, route team **ACCOUNTS_PAYABLE** (FAILED,
        `diagnostic_needed=false`). The line-level analogue is
        `suspension_reason == "OVERDUE_BILL"`.
      - Else (e.g. "account hold") -> **INELIGIBLE_ACCOUNT** (FAILED,
        `diagnostic_needed=false`, no team).
2. **Outage gate** (only after account gate passes):
   - `GET /api/outages?service_area=<ticket.service_area>`. If any outage has
     `active == true` AND `ticket.service_type ∈ outage.service_types` ->
     **OUTAGE_WAIT**: `final_resolution_status=PENDING_ACTION`,
     `diagnostic_needed=false`, `outage_id=<matching outage_id>`. This is the
     only branch that sets a non-empty `outage_id`.
3. **Diagnostics** (account OK, no active outage):
   - `diagnostic_needed=true`. `GET /api/diagnostics/<id>` (pre) and
     `GET /api/troubleshooting/<id>` (post). Compute pre-flags (§1.3),
     then post-flags, then decide RESOLVED vs ESCALATED (§1.4).

Order matters: account/auth gates are evaluated before the outage gate, and the
outage gate before diagnostics. A gated ticket never runs diagnostics, so its
`latency_issue/stability_issue/bandwidth_issue` are all `false` and
`outage_id` is empty (except the OUTAGE_WAIT branch).

### 1.2 Flag semantics — flags are PRE-troubleshooting floor violations

`latency_issue`, `stability_issue`, `bandwidth_issue` are computed from the
**pre-troubleshooting** diagnostic record against absolute/ratio floors. They
are `false` for every gated ticket (no diagnostic was run).

### 1.3 Diagnostic floors (INFERRED — see §1.5 evidence)

| Metric | Floor | Issue rule (true when) | Source field |
|---|---|---|---|
| latency | **100 ms** | `latency_ms > 100` | `diagnostics.latency_ms` |
| jitter (stability) | **30 ms** | `jitter_ms > 30` | `diagnostics.jitter_ms` |
| bandwidth | **0.70 × subscribed_mbps** | `bandwidth_mbps < 0.70 × subscribed_mbps` | `diagnostics.bandwidth_mbps` vs `tickets.subscribed_mbps` |

Uniform across `service_type` (internet / video / voice all use the same
ratio + absolute floors). `subscribed_mbps` comes from the ticket record.

### 1.4 Post-troubleshooting re-check (RESOLVED vs ESCALATED)

For every diagnostic-eligible ticket, also `GET /api/troubleshooting/<id>` and
recompute the three flags against the SAME floors using the **post_** fields
(`post_bandwidth_mbps`, `post_latency_ms`, `post_jitter_ms`).

- If **all three post-flags are false** -> **RESOLVED**,
  `resolution_route=AUTO_TROUBLESHOOTING`, `escalation_team=NONE`.
- If **any post-flag is still true** -> **ESCALATED**, `resolution_route=ESCALATION`,
  `escalation_team` derived from `diagnostics.root_causes` (§1.5).

`outage_id` is empty string for both RESOLVED and ESCALATED.

### 1.5 Root-cause -> escalation-team map

Determine the team by scanning `root_causes[]` in priority order; first match
wins:

| Root-cause keyword (substring, case-insensitive) | escalation_team | (train_004 key_blocker label) |
|---|---|---|
| `FIBER` or `SIGNAL` | `FIELD_OPS` | (fiber/signal label) |
| `BACKBONE` or `CAPACITY` | `NETWORK_ENGINEERING` | `NETWORK_CAPACITY` |
| `PROVISIONING` | `TIER2_SUPPORT` | `PROVISIONING_STALE` |
| `BILLING` | `ACCOUNTS_PAYABLE` | (billing label) |
| (none of the above, e.g. `CONFIGURATION_DRIFT`, `GENERATED_NOISE`, `VOICE_PROFILE_STALE`) | resolves via auto-troubleshoot -> usually RESOLVED; if still failing, see note | — |

Observed: `CONFIGURATION_DRIFT` and `VOICE_PROFILE_STALE` tickets cleared all
post-flags so they were RESOLVED (no escalation). Only fiber/signal,
backbone/capacity, and provisioning root causes survived troubleshooting and
escalated. If a non-mapped root cause still has post-flags true, default the
team by the closest category; with no match, leave `FIELD_OPS` as a fallback
only when a physical-layer cause is evident (weakly inferred).

### 1.6 Output schema variants — follow the provided answer_template.json

**Variant 1 (train_001 style)** — richer per-ticket decision:
```
ticket_decisions[]: {ticket_id, account_id, final_resolution_status,
  diagnostic_needed, latency_issue, stability_issue, bandwidth_issue,
  outage_id ("" when none), escalation_team, resolution_route}
batch_summary: {RESOLVED, PENDING_ACTION, ESCALATED, FAILED,
  tickets_requiring_customer_wait}
```
- `resolution_route` enum: `AUTO_TROUBLESHOOTING | OUTAGE_WAIT | ESCALATION |
  INELIGIBLE_ACCOUNT | AUTH_FAILED | INVALID_ACCOUNT`.
- `escalation_team` enum: `NONE | TIER2_SUPPORT | FIELD_OPS |
  NETWORK_ENGINEERING | ACCOUNTS_PAYABLE`.
- `tickets_requiring_customer_wait` = count of PENDING_ACTION (outage-wait)
  tickets (the customer must wait for the outage to clear).

**Variant 2 (train_004 style)** — key_blocker + route_team:
```
ticket_decisions[]: {ticket_id, final_resolution_status, route_team,
  key_blocker, diagnostic_required}
queue_summary: {FAILED, PENDING_ACTION, RESOLVED, ESCALATED,
  TIER2_SUPPORT, FIELD_OPS, NETWORK_ENGINEERING, ACCOUNTS_PAYABLE}
```
- `key_blocker` labels: `ACTIVE_OUTAGE | INVALID_ACCOUNT | AUTH_FAILED |
  OVERDUE_SUSPENSION | NETWORK_CAPACITY | PROVISIONING_STALE | NONE`
  (and fiber/signal label for that branch).
- `route_team`: `NONE` for resolved / outage / invalid / auth; the mapped team
  for overdue + escalations.
- `diagnostic_required` == `diagnostic_needed` (same boolean).
- `queue_summary` counts: first four are status counts; the four team keys
  count tickets routed to each team (FIELD_OPS=0 in train_004).

Preserve payload (CSV) order in the `ticket_decisions` array.

### 1.7 Audit math formulas (state exactly)

Let `D` = set of diagnostic-eligible tickets (`diagnostic_needed=true`), `G` =
gated/skipped tickets (`diagnostic_needed=false`), `E` = ESCALATED tickets
(post-flags not all clear), `R` = RESOLVED-via-AUTO_TROUBLESHOOTING tickets.
Floors: `BW_RATIO=0.70`, `LAT=100`, `JIT=30`. For ticket `t`: `sub(t)` =
`subscribed_mbps`, `bw(t)`/`lat(t)`/`jit(t)` = pre diagnostic values,
`pbw(t)`/`plat(t)`/`pjit(t)` = post values.

1. **pre_troubleshooting_bandwidth_gap_total_mbps** =
   `Σ_{t∈D, bw(t) < 0.70·sub(t)} (0.70·sub(t) − bw(t))`.
2. **diagnostic_records_skipped_by_gate** = `|G|` (tickets with
   `diagnostic_needed=false`).
3. **post_troubleshooting_remaining_issue_flags** =
   `Σ_{t∈E} [ (plat(t)>100) + (pjit(t)>30) + (pbw(t)<0.70·sub(t)) ]`
   (count of post-flags still true, summed over escalated tickets).
4. **post_threshold_excess_totals** (over `E` only):
   - latency_excess_total = `Σ_{t∈E} max(0, plat(t) − 100)`
   - jitter_excess_total  = `Σ_{t∈E} max(0, pjit(t) − 30)`
   - bandwidth_shortfall_total = `Σ_{t∈E} max(0, 0.70·sub(t) − pbw(t))`
5. **tickets_using_post_troubleshooting_records** = `|D|` (every
   diagnostic-eligible ticket has a troubleshooting record consumed).
6. **tickets_with_active_outage_match** = count of tickets where an outage with
   `active=true`, matching `service_area`, and `service_type ∈
   outage.service_types` exists (i.e. the OUTAGE_WAIT branch).
7. **unique_escalation_teams** = sorted unique `escalation_team` values among
   `E`, excluding `NONE`.
8. **root_cause_escalation_ticket_ids by team** = `{team: sorted[ticket_id]}`
   for each team in `E`'s escalation teams.
9. **post success/failure id lists**:
   - success (RESOLVED via AUTO_TROUBLESHOOTING) = `sorted[ticket_id for t∈R]`
   - failure (ESCALATED) = `sorted[ticket_id for t∈E]`
10. **per-ticket floor + shortfall list** (sorted by `ticket_id`), one entry
    per `t∈D`:
    `{ticket_id, subscribed_mbps, bandwidth_floor_mbps=0.70·sub,
      latency_floor_ms=100, jitter_floor_ms=30,
      pre_bandwidth_shortfall_mbps=max(0, 0.70·sub−bw),
      pre_latency_excess_ms=max(0, lat−100),
      pre_jitter_excess_ms=max(0, jit−30)}`.

### 1.8 Worked evidence for the thresholds (INFERRED)

- **Bandwidth ratio 0.70 (strong):** TCK-5107 `sub=300`, pre `bw=209` flagged
  issue; `0.70·300 = 210`, and `209 < 210` (off by exactly 1 — boundary test).
  Post `bw=272 ≥ 210` -> cleared -> RESOLVED. TCK-5184 `sub=500`, pre `bw=318`
  flagged; `0.70·500=350`, `318<350`. Both consistent. (`0.75` also fits the
  two bandwidth points but cannot explain the deliberate `209`-vs-`210`
  boundary; commit to **0.70**.)
- **Latency floor 100 ms:** RESOLVED posts 82, 79 (≤100, no issue); ESCALATED
  posts 176, 198, 121 (>100, issue); pre-flagged gold 142.8, 188.4 (>100).
  All consistent with `>100 = issue`. Boundary untested; 100 is the canonical
  degraded-latency threshold.
- **Jitter floor 30 ms:** RESOLVED posts 21, 18 (≤30); ESCALATED posts 41, 43,
  32 (>30); pre-flagged gold 33.5, 44.2 (>30). All consistent with `>30`.
  (25 ms also fits all points; 30 is the canonical jitter threshold and matches
  the ESCALATED post value 32 being just over — commit to **30**.)

---

## 2. Family B — Mobile triage (train_002 / train_005)

Input: a JSON queue (`case_queue.json` / `mobile_data_worklist.json`) of cases
with `case_id` + `reported_issue`/`summary`. For each case, fetch
`GET /api/cases/<case_id>` to get `customer_id`, `line_id`, `device_id`,
`issue_type`, `customer_location`; then `GET /api/lines/<line_id>`,
`GET /api/devices/<device_id>`, `GET /api/plans/<plan_id>` (via line.plan_id),
and `GET /api/bills/<bill_id>` when a bill is referenced.

### 2.1 Decision tree (apply in priority order; first match wins)

1. **Line suspended for overdue bill** — `line.status=="Suspended"` and
   (`line.suspension_reason=="OVERDUE_BILL"` or note contains "overdue"):
   - primary `SEND_PAYMENT_REQUEST`, secondary `RESUME_LINE_REBOOT`,
     `final_route=BILLING_RECOVERY`.
   - `bill_id` = the line/customer's overdue bill; `charge_amount_usd` =
     `bill.amount_due_usd`. (Found via `GET /api/bills/<bill_id>`; the bill id
     pattern is `BILL-<case_num>`.)
2. **Data cap exceeded** — `line.data_used_gb > plan.data_limit_gb`:
   - primary `REFUEL_DATA`, `final_route=DATA_RECOVERY`.
   - `data_refuel_gb = ceil(data_used_gb − data_limit_gb)` (min 1.0; INFERRED
     from one point: overage 1.2 -> 2.0 GB).
   - `charge_amount_usd = data_refuel_gb × plan.data_refueling_price_per_gb`.
3. **SIM missing** — `device.sim_status=="missing"`:
   - primary `RESEAT_SIM`, `final_route=SELF_SERVICE`. (NO_SERVICE case after
     commute.)
4. **Abroad + roaming gap** — `case.customer_location=="abroad"` and data issue:
   a. `line.roaming_enabled==false` -> primary `ENABLE_LINE_ROAMING`,
      `carrier_update_required=true`, `final_route=CARRIER_UPDATE`
      (carrier-side; needs a carrier update).
   b. else `device.phone_roaming_enabled==false` -> primary `TOGGLE_ROAMING`,
      `final_route=SELF_SERVICE` (phone-side toggle).
5. **MMS / messaging permission** — `device.can_send_mms==false` and a
   `messaging_permissions` key is `false`:
   - primary `GRANT_MESSAGING_PERMISSION`, `permission=<the false key>` (e.g.
     `storage`), `final_route=SELF_SERVICE`. (`mmsc_url_present` should be true;
     the missing permission is the blocker.)
6. **VPN connected** — `device.vpn_connected==true` (slow data):
   - primary `DISCONNECT_VPN`, `final_route=SELF_SERVICE`.
7. **Data-saver on** — `device.data_saver_mode==true` (slow data):
   - primary `TOGGLE_DATA_SAVER`, `final_route=DEVICE_SETTING_FIX`.
8. **Stale network mode** — `device.network_mode_preference != "4g_5g_preferred"`
   (e.g. `"3g_only"`, slow data):
   - primary `SET_NETWORK_MODE`, `final_route=DEVICE_SETTING_FIX`.
9. **Mobile data disabled** — `device.mobile_data_enabled==false`:
   - primary `TOGGLE_MOBILE_DATA`, `final_route=DEVICE_SETTING_FIX`.

Default `secondary_action=NO_ACTION` for all except the billing branch
(`RESUME_LINE_REBOOT`). `permission="NONE"` and `bill_id=""` unless the
branch sets them. `data_refuel_gb=0.0`, `charge_amount_usd=0.0`,
`carrier_update_required=false` unless the branch sets them.

`issue_type` reinforces branch selection but the device/line fields are
authoritative: `NO_SERVICE` -> sim/billing; `MOBILE_DATA` -> cap/roaming/data-
toggle; `MMS` -> permission; `SLOW_DATA` -> vpn/data-saver/network-mode.

### 2.2 Output schema variants — follow the provided answer_template.json

**train_002 style** (case_queue):
```
case_decisions[]: {case_id, customer_id, line_id, primary_action,
  secondary_action, permission, bill_id, charge_amount_usd, final_route}
queue_summary: {self_service_fixes, billing_recoveries, carrier_updates,
  human_transfers}
```
- `final_route` values seen: `SELF_SERVICE`, `BILLING_RECOVERY`.
- summary: `self_service_fixes` = count of SELF_SERVICE routes;
  `billing_recoveries` = count of BILLING_RECOVERY; `carrier_updates` =
  count of CARRIER_UPDATE; `human_transfers` = 0 (no human-transfer branch
  observed).

**train_005 style** (mobile_data_worklist):
```
case_decisions[]: {case_id, primary_action, secondary_action,
  data_refuel_gb, charge_amount_usd, carrier_update_required, final_route}
worklist_summary: {data_refuel_cases, carrier_updates, device_setting_fixes,
  human_transfers, total_estimated_customer_charge_usd}
```
- `final_route` values seen: `DATA_RECOVERY`, `CARRIER_UPDATE`,
  `DEVICE_SETTING_FIX`.
- `total_estimated_customer_charge_usd` = Σ `charge_amount_usd` across cases.

Preserve payload order. Action enums differ slightly between the two variants
(e.g. `TOGGLE_ROAMING` vs `ENABLE_LINE_ROAMING`; `REFUEL_DATA`) — emit the
action token the decision tree produces and that the template expects.

### 2.3 Plan reference (from `GET /api/plans`)

| plan_id | data_limit_gb | data_refueling_price_per_gb | monthly_price_usd |
|---|---|---|---|
| PLAN-BASIC | 5.0 | 5.0 | 40.0 |
| PLAN-PREMIUM | 15.0 | 2.0 | 65.0 |
| PLAN-PLUS | 999.0 | 0.1 | 85.0 |
| (PLAN-25 / others) | 25.0 | 3.0 | 120.0 |

Always read the plan from the API; do not hard-code these.

---

## 3. Family C — Enterprise export-complaint response package (train_003)

Input: `client_complaint_email.txt` (client name, product, approximate
incident reference) + `response_requirements.json` (required_fields,
`permission_users_to_include`, `naming_style`). Identify the incident from the
email's approximate reference (e.g. `INC-7301`), then assemble the package.
Output JSON per `answer_template.json`.

### 3.1 SOP

1. **Identify incident.** `GET /api/enterprise/incidents`, match on
   `incident_id` from the email (the "Approximate incident reference"). Confirm
   `enterprise_account_id`, `severity`, `engineering_owner`, `account_owner`,
   `product`, `status`.
2. **Confirm account.** `GET /api/enterprise/accounts`, match on
   `enterprise_account_id` to get `name`, `tier`, `finance_owner`.
3. **Failed export-run window.**
   `GET /api/enterprise/export-runs?incident_id=<incident_id>`.
   - `failure_window.start_date` = `run_date` of the FIRST `status=="FAILED"`
     run; `end_date` = `run_date` of the LAST `FAILED` run;
     `failed_days` = count of FAILED runs.
   - `backfill_days` = count of FAILED runs (= `failed_days`).
   - `root_cause_category` = concise phrase inferred from the FAILED runs'
     `failure_code` + the engineering message body
     (`GET /api/enterprise/messages?query=<client or failure keyword>`).
     Examples: `STALE_CREDENTIAL` + "credential rotation completed; scheduler
     pod still references old secret" -> `"stale credential after rotation"`;
     `STAGING_STORAGE_QUOTA` + "staging bucket reached quota" -> quota-related
     phrase. Lowercase descriptive phrase.
4. **SLA credit.** `GET /api/enterprise/sla/<enterprise_account_id>`.
   - `sla_credit_percent` = `monthly_export_credit_percent` WHEN the
     `credit_trigger` condition is met by the failure window (e.g. "3
     consecutive failed export runs" -> failed_days≥3; "critical export outage
     longer than 72 hours" -> failed_days≥3 days). Else 0.
   - If credit warranted -> `response_status = "NEEDS_FINANCE_REVIEW"` (finance
     must approve the credit). Other statuses: `NEEDS_ENGINEERING_REVIEW` if an
     unresolved engineering root cause needs sign-off and no credit;
     `READY_TO_SEND` if resolved with no credit; `UNDER_INVESTIGATION` if the
     incident is still open and root cause unconfirmed. (Only the finance-review
     branch is directly attested by gold.)
5. **Contributing alert issue.** From the engineering root-cause message: if its
   `channel` contains "archive" (e.g. `export-alerts-archive`) ->
   `ARCHIVED_ALERT_ROUTE`; else `NONE`; `UNKNOWN` only if no message found.
6. **Owners.** `engineering_owner` and `account_owner` come from the incident
   record. (Finance owner is used for share permissions.)
7. **Naming conventions** (from `response_requirements.naming_style` =
   "lowercase hyphen channel; client-date investigation folder; client export
   failure report title"), using the account `name`:
   - `channel_name` = client name lowercased, spaces -> hyphens
     (e.g. "Asteri Retail Inc." -> `asteri-retail-inc`).
   - `evidence_folder` = `"<Client Name> <Month Year> Investigation"` where
     Month Year comes from the incident `received_at` / failure window month
     (e.g. "Asteri Retail Inc. May 2026 Investigation").
   - `report_title` = `"<Client Name> Export Failure - Resolution Report"`.
8. **Share permissions.** Use `permission_users_to_include` from the
   requirements, in the listed order. Assign `"view"` to the user that is the
   account's `finance_owner`; assign `"edit"` to the other listed user(s).
   (INFERRED from one example: laura.brown=finance_owner->view,
   jun.chen->edit. Order preserved as listed in requirements.)

### 3.2 Output fields

```
incident_id, enterprise_account_id, root_cause_category, contributing_alert_issue,
failure_window {start_date, end_date, failed_days}, backfill_days,
sla_credit_percent, severity, engineering_owner, account_owner,
channel_name, evidence_folder, report_title,
share_permissions [{user, permission}], response_status
```
Enumerations: `contributing_alert_issue` ∈
`ARCHIVED_ALERT_ROUTE | NONE | UNKNOWN`; `severity` ∈
`Critical | High | Medium | Low`; `permission` ∈ `view | edit | upload_only`;
`response_status` ∈
`READY_TO_SEND | NEEDS_FINANCE_REVIEW | NEEDS_ENGINEERING_REVIEW | UNDER_INVESTIGATION`.

---

## 4. Pitfalls & conventions (all families)

- **Base URL:** never use `127.0.0.1:8057`; always `<remote-env-url>`.
- **Bandwidth floor is a RATIO, not absolute.** It is `0.70 × subscribed_mbps`
  per ticket; `subscribed_mbps` must be read from `GET /api/tickets/<id>`, not
  assumed. Do not apply a single global bandwidth number.
- **Flags are PRE-troubleshooting.** Gated tickets (account/auth/outage) get
  all three issue flags `false` and empty `outage_id` (except OUTAGE_WAIT).
- **Outage match requires `active==true` AND service_type membership**, not
  just service_area. Inactive outages in the same area do NOT gate.
- **Account 404 = INVALID_ACCOUNT** (different from Suspended). Auth failure is
  read from `authentication.last_login_status`/`account_recovery_status`, not
  from `status`.
- **Suspended accounts split by cause:** "overdue" -> OVERDUE_SUSPENSION +
  ACCOUNTS_PAYABLE; "hold"/other -> INELIGIBLE_ACCOUNT + no team. The line
  analogue (`suspension_reason=="OVERDUE_BILL"`) is the mobile billing branch.
- **POST flags decide RESOLVED vs ESCALATED**, not the root cause. A root cause
  only sets the escalation TEAM once escalation is already determined by
  remaining post-flags.
- **Escalation team keyword scan is case-insensitive substring** on
  `root_causes[]`; first matching category in the priority order
  (fiber/signal -> backbone/capacity -> provisioning -> billing) wins.
- **Preserve payload order** in all decision arrays; **sort by ticket_id /
  case_id** only for the audit id-lists.
- **Empty strings, not null:** `outage_id`, `bill_id` are `""` when not
  applicable. `escalation_team` / `route_team` use `NONE`, not null.
- **Mobile action vocabularies differ between the two variants** (e.g.
  `TOGGLE_ROAMING` phone-side vs `ENABLE_LINE_ROAMING` line-side; `REFUEL_DATA`
  vs `DATA_REFUEL`). Match the provided template's enum expectations.
- **Enterprise naming strings must follow the requirements `naming_style`
  exactly** (lowercase-hyphen channel; "<Client> <Mon Year> Investigation"
  folder; "<Client> Export Failure - Resolution Report" title).
- **SLA credit triggers the finance review** response_status; the percent comes
  straight from the SLA endpoint's `monthly_export_credit_percent`.
- **Probe the API; do not memorize record values.** Ticket ids, account ids,
  plan params, owners, etc. will change at test time — only the thresholds,
  ratios, maps, and formulas above are stable.
