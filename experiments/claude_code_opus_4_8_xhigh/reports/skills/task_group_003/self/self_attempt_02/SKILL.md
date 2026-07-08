# SKILL: CRM Support-Console Task Solver

## When to use
Use this when a task asks you to triage/resolve a batch of **support tickets**, a
queue of **mobile cases**, or to build an **enterprise export-complaint response
package**, and tells you to "use the shared support console API" and "return only
JSON conforming to `payloads/answer_template.json`". You are given input payloads
(CSV/JSON + an `answer_template.json`) and must derive every decision from live API
records, not from assumptions or from the issue text alone.

## API base URL and lookup habits
- **Base URL: `<remote-env-url>`** (overrides any `127.0.0.1:8057`
  shown in prompts). Read-only. Confirm with `GET /health`, list with `GET /api/catalog`.
- Call with curl, e.g. `curl -s <remote-env-url>api/tickets/TCK-6101`.
- A missing record returns `{"error":"not_found"}` (HTTP 200) — treat that as the
  signal for INVALID_ACCOUNT / not-found, do not retry forever.
- Endpoints by record type and how they chain:
  - Tickets: `/api/tickets/<id>` -> gives `account_id`, `service_area`, `service_type`, `subscribed_mbps`.
  - Account: `/api/accounts/<account_id>` -> `status` (Active/Suspended), `authentication.last_login_status`, `authentication.account_recovery_status`.
  - Outage: `/api/outages?service_area=<area>` -> list; check `active` and whether ticket's `service_type` is in `service_types`.
  - Diagnostics: `/api/diagnostics/<ticket_id>` -> `root_causes` (list), `latency_ms`, `jitter_ms`, `bandwidth_mbps`.
  - Troubleshooting: `/api/troubleshooting/<ticket_id>` -> `steps`, `post_latency_ms`, `post_jitter_ms`, `post_bandwidth_mbps`.
  - Mobile cases: `/api/cases/<id>` -> `customer_id`, `line_id`, `device_id`, `issue_type`, `customer_location`.
  - Line: `/api/lines/<line_id>` -> `status`, `suspension_reason`, `roaming_enabled`, `data_used_gb`, `plan_id`.
  - Device: `/api/devices/<device_id>` -> sim_status, signal_strength, mobile_data_enabled, phone_roaming_enabled, data_saver_mode, network_mode_preference, vpn_connected, can_send_mms, mmsc_url_present, messaging_permissions{sms,storage}, airplane_mode, wifi_calling_enabled.
  - Plan: `/api/plans/<plan_id>` -> `data_limit_gb`, `data_refueling_price_per_gb`, `monthly_price_usd`.
  - Bills: `/api/bills` -> list keyed by `customer_id`; fields `bill_id`, `amount_due_usd`, `status` (Paid/Issued/Overdue), `due_date`. (Filter the full list by customer_id; there is no per-customer endpoint.)
  - Enterprise: `/api/enterprise/incidents/<id>`, `/api/enterprise/accounts`, `/api/enterprise/export-runs?incident_id=<id>`, `/api/enterprise/sla/<enterprise_account_id>`, `/api/enterprise/messages?query=<text>`.

## GLOBAL OUTPUT DISCIPLINE
- Return **only** the JSON object the template defines. No prose, no markdown fences.
- Match enum spelling EXACTLY (e.g. `RESOLVED`, `NETWORK_ENGINEERING`, `upload_only`, `Critical`). Wrong case/word = wrong.
- Preserve the array order the template demands: ticket families = **payload/CSV order**; case families = **ascending case_id order**.
- Numbers: charges = number with **two decimals** (e.g. `4.00`, `86.40`); data_refuel_gb = **one decimal** (`2.0`); counts = plain integers; percents = plain integer.
- Empty/absent string fields = `""` (e.g. `outage_id` when no outage, `bill_id` when no billing).
- The summary counts MUST be recomputed from your own per-row decisions (sum of statuses, routes, etc.). Don't eyeball them.

---

## FAMILY A — Offline ticket batch resolution (template has `ticket_decisions` + `final_resolution_status`, `resolution_route`, `escalation_team`, issue booleans)

For each ticket in payload order:
1. **Fetch ticket** -> account_id, service_area, service_type, subscribed_mbps.
2. **Fetch account.** Decision precedence (apply the FIRST that matches):
   - Account `not_found` -> status **FAILED**, route **INVALID_ACCOUNT**, escalation **NONE**, no diagnostic, outage "".
   - `authentication.last_login_status == "FAILURE"` or `account_recovery_status == "FAILURE"` -> status **FAILED**, route **AUTH_FAILED**, escalation **NONE**, no diagnostic.
   - Account `status == "Suspended"` -> status **PENDING_ACTION** (account ineligible for service work), route **INELIGIBLE_ACCOUNT**, escalation **ACCOUNTS_PAYABLE**, no diagnostic. (Suspension is a billing/account block, not a network fix.)
3. **Outage check** (only if account passed step 2): `GET /api/outages?service_area=`. If an outage with `active:true` exists AND the ticket's `service_type` is in its `service_types` -> status **PENDING_ACTION**, route **OUTAGE_WAIT**, escalation **NONE**, `outage_id` = that id, no diagnostic. This is a "customer must wait" ticket.
4. **Otherwise run diagnostics + troubleshooting** (`diagnostic_needed = true`). Read `root_causes`:
   - Auto-fixable causes (`CONFIGURATION_DRIFT`, `VOICE_PROFILE_STALE`, `PROVISIONING_STALE`, `GENERATED_NOISE`/`GENERATED_*`): troubleshooting resolves them -> status **RESOLVED**, route **AUTO_TROUBLESHOOTING**, escalation **NONE**.
   - Hard-fault causes that troubleshooting cannot fix -> status **ESCALATED**, route **ESCALATION**:
     - `BACKBONE_CAPACITY` -> escalation **NETWORK_ENGINEERING**.
     - `FIBER_DROP_DAMAGE` / `SIGNAL_LOSS` (physical line) -> escalation **FIELD_OPS**.
     - other unresolved/complex software issues a tier-1 script can't close -> **TIER2_SUPPORT**.
   - Tell auto-fix from hard-fault by the root cause name AND by whether post-troubleshooting metrics recovered toward SLA. Hard faults leave `post_latency_ms`/`post_bandwidth_mbps` still bad (e.g. latency stays >170 ms, bandwidth far below `subscribed_mbps`); auto-fixes show clear improvement.
5. **Issue booleans** (set from DIAGNOSTIC readings, the pre-fix snapshot, not the post values):
   - `latency_issue` = latency_ms high (rule of thumb: > ~100 ms, and clearly elevated vs a clean baseline ~40-80).
   - `stability_issue` = jitter_ms high (> ~40 ms) and/or intermittent connectivity.
   - `bandwidth_issue` = bandwidth_mbps materially below `subscribed_mbps`.
   - When a ticket short-circuits at step 2/3 (no diagnostic run), all three booleans are `false`.
6. **batch_summary**: count each status; `tickets_requiring_customer_wait` = number of OUTAGE_WAIT tickets (the customer must wait for an active outage to clear). Recompute from your rows.

### Variant — Queue-quality classification (template has `route_team` + `key_blocker` + `diagnostic_required`)
Same precedence logic, but the blocker is reported via the `key_blocker` enum and a free-text `queue_note`. Map:
| Situation | key_blocker | route_team | status | diagnostic_required |
|---|---|---|---|---|
| active outage covering service_type | ACTIVE_OUTAGE | NONE | PENDING_ACTION | false |
| account not_found | INVALID_ACCOUNT | NONE | FAILED | false |
| auth FAILURE | AUTH_FAILED | NONE | FAILED | false |
| Suspended + note says overdue/payment | OVERDUE_SUSPENSION | ACCOUNTS_PAYABLE | PENDING_ACTION (or ESCALATED) | false |
| Suspended + note says fraud/security | FRAUD_SUSPENSION | ACCOUNTS_PAYABLE | ESCALATED | false |
| diag root cause BACKBONE_CAPACITY, not recovered | NETWORK_CAPACITY | NETWORK_ENGINEERING | ESCALATED | true |
| diag root cause FIBER_DROP_DAMAGE/SIGNAL_LOSS | PHYSICAL_LINE_FAULT | FIELD_OPS | ESCALATED | true |
| diag root cause PROVISIONING_STALE | PROVISIONING_STALE | (NONE if troubleshooting fixed; else TIER2_SUPPORT) | RESOLVED or ESCALATED | true |
| auto-fixable, troubleshooting recovered | NONE | NONE | RESOLVED | true |
- **OVERDUE vs FRAUD suspension**: the account record only shows `status:"Suspended"` — there is NO fraud flag on it. Disambiguate from the `queue_note`/ticket text ("overdue notice"->OVERDUE; "fraud"/"security hold"->FRAUD). Bills are NOT linked to ticket-family accounts (bills key on CUST-*, not ACC-*), so don't try to read a bill to decide this.
- `queue_summary` counts every status AND every route_team value used. Recompute.

---

## FAMILY B — Mobile case triage (template has `primary_action`/`secondary_action`, `final_route`, sometimes `permission`/`bill_id`/`charge_amount`, or `data_refuel_gb`/`carrier_update_required`)

For each case (ascending case_id): fetch case -> line, device, plan, and (if billing) bills.
Decide the PRIMARY operation from the single dominant blocker, SECONDARY for a required follow-up (else `NO_ACTION`). Drivers (check in this priority):

1. **Line Suspended** (`line.status == "Suspended"`): if `suspension_reason == "OVERDUE_BILL"` -> primary **SEND_PAYMENT_REQUEST**, route **BILLING_RECOVERY**. Find the customer's **Overdue** bill, set `bill_id` to it and `charge_amount_usd` = its `amount_due_usd` (two decimals). Secondary often **RESUME_LINE_REBOOT** (resume the line after payment). Non-billing suspension (e.g. contract ended) -> **TRANSFER_HUMAN**, route HUMAN_TRANSFER.
2. **NO_SERVICE / SIM problem**: `device.sim_status == "missing"` -> **RESEAT_SIM**. SIM locked/PIN-locked (no self-fix) -> **TRANSFER_HUMAN**. `airplane_mode == true` -> **TOGGLE_AIRPLANE_MODE**.
3. **Abroad / roaming (MOBILE_DATA + customer_location "abroad" or "no data while roaming")**:
   - `line.roaming_enabled == false` (carrier side off) -> **ENABLE_LINE_ROAMING** (route CARRIER_UPDATE / carrier_update_required = true).
   - line roaming on but `device.phone_roaming_enabled == false` -> **TOGGLE_ROAMING** (device fix, SELF_SERVICE/DEVICE_SETTING_FIX).
4. **MOBILE_DATA "no data" at home**: `device.mobile_data_enabled == false` -> **TOGGLE_MOBILE_DATA**. After an APN/settings change broke data -> **RESET_APN_REBOOT**.
5. **Data exhausted (data_used_gb >= plan.data_limit_gb)**: -> **REFUEL_DATA**. Refuel amount = customer's accepted GB from `customer_preferences.<case>.accepted_refuel_gb` (if absent, the minimum needed to restore service). `charge_amount_usd` = refuel_gb * `plan.data_refueling_price_per_gb` (TWO decimals). `data_refuel_gb` = that GB (ONE decimal). Route DATA_RECOVERY. Respect `does_not_want_plan_change` -> do NOT propose a plan upgrade, only refuel.
6. **SLOW_DATA**: `device.vpn_connected == true` -> **DISCONNECT_VPN**. `device.data_saver_mode == true` -> **TOGGLE_DATA_SAVER**. `device.network_mode_preference == "3g_only"` (or other legacy mode) -> **SET_NETWORK_MODE** (to a 4g/5g preferred mode). These are DEVICE_SETTING_FIX / SELF_SERVICE.
7. **MMS (can't send photos)**: `device.can_send_mms == false`. If `messaging_permissions.storage == false` -> **GRANT_MESSAGING_PERMISSION** with `permission` = the missing perm (`storage`, `sms`, or `sms_and_storage`). If `mmsc_url_present == false` or APN broken -> **RESET_APN_REBOOT**. Often primary = grant permission, secondary = RESET_APN_REBOOT.
8. **Nothing actionable / needs an agent** -> **TRANSFER_HUMAN**, route HUMAN_TRANSFER.

- `permission` field: `NONE` unless a GRANT_MESSAGING_PERMISSION action is chosen; then the exact missing scope.
- `bill_id` / `charge_amount_usd`: empty `""` / `0.00` unless a billing or refuel charge applies.
- `final_route` mapping: self-service device toggles -> **SELF_SERVICE** (FAMILY-002) / **DEVICE_SETTING_FIX** (FAMILY-005); refuel -> **DATA_RECOVERY** (005); roaming carrier change -> **CARRIER_UPDATE**; overdue bill -> **BILLING_RECOVERY** (002); escalate to person -> **HUMAN_TRANSFER**.
- For the 005 worklist `total_estimated_customer_charge_usd` = sum of all per-case `charge_amount_usd` (two decimals). `carrier_update_required` true only for ENABLE_LINE_ROAMING / carrier-side changes.
- Summary counters: count cases by their `final_route`. Recompute.

---

## FAMILY C — Enterprise export-complaint response package (single flat object)

Inputs: a complaint email (names client, product, approximate `INC-####`) and `response_requirements.json` (lists `permission_users_to_include` and a `naming_style`).

1. **Identify incident**: `GET /api/enterprise/incidents/<INC>` (use the email's reference). Read `enterprise_account_id`, `severity`, `engineering_owner`, `account_owner`, `product`, `status`.
2. **Account**: `GET /api/enterprise/accounts`, find the matching `enterprise_account_id` -> `name` (client), `finance_owner`.
3. **Export runs**: `GET /api/enterprise/export-runs?incident_id=<INC>`. Sort by `run_date`. The FAILED runs (status `FAILED`, usually `exported_record_count:0`) form the failure window:
   - `failure_window.start_date` = first FAILED run_date; `.end_date` = last consecutive FAILED run_date; `.failed_days` = count of FAILED runs.
   - The first SUCCEEDED run after the failures is the recovery/backfill (its `exported_record_count` is the backfilled data).
   - `backfill_days` = number of failed days that were manually backfilled = `failed_days` (cross-check any message that states a backfill count).
   - `root_cause_category` = the `failure_code` on the failed runs, expressed as a concise category (e.g. `STALE_CREDENTIAL`, `STAGING_STORAGE_QUOTA`). Corroborate with the message body.
4. **SLA**: `GET /api/enterprise/sla/<enterprise_account_id>` -> `sla_credit_percent` = `monthly_export_credit_percent`. Verify the `credit_trigger` is actually met by the window (e.g. "3 consecutive failed runs", or "outage > 72 hours").
5. **Messages**: `GET /api/enterprise/messages?query=<client name>` (also try the engineering owner's name; `query=INC-####` often returns nothing — search by client/owner instead). Use the body to confirm root cause and the SLA percent.
   - `contributing_alert_issue`: if the root-cause/alert message sits in an **archived alert channel** (channel name contains `alert` + `archive`, e.g. `export-alerts-archive`) -> **ARCHIVED_ALERT_ROUTE** (the alert was missed because its route was archived). If alerts routed normally -> **NONE**. If no evidence either way -> **UNKNOWN**.
6. **Owners**: `engineering_owner` and `account_owner` come straight from the incident record (user ids like `delana.rao`). `finance_owner` (from the account) is used for finance review / share permission, not as account_owner.
7. **severity** = incident `severity` (Critical/High/Medium/Low — exact case).
8. **Constructed naming artifacts** — build from `naming_style`, lowercase + hyphens, using the client name and dates:
   - `channel_name`: lowercase hyphenated, client + topic (e.g. `asteri-retail-export-incident`). Follow the style string literally.
   - `evidence_folder`: client + date investigation folder (e.g. `asteri-retail-2026-05-12-investigation` using the failure start date).
   - `report_title`: a "client export failure report" title (e.g. `Asteri Retail Inc. Monthly Export Failure Report`).
   - Match the wording hints in `naming_style` precisely; keep client name spelling exactly as in the account `name`.
9. **share_permissions**: one entry per user in `permission_users_to_include`, IN THAT ORDER. Assign `permission` by role: the finance owner / reviewer (e.g. `laura.brown` is the account's finance_owner) gets **view**; a data/evidence contributor who only uploads artifacts gets **upload_only**; an editor of the package gets **edit**. Default a reviewer to `view`, an uploader to `upload_only`.
10. **response_status**:
    - If a SLA credit is owed and still needs finance sign-off -> **NEEDS_FINANCE_REVIEW**.
    - If root cause/backfill still unconfirmed by engineering -> **NEEDS_ENGINEERING_REVIEW**.
    - If the incident is still open with the window unresolved -> **UNDER_INVESTIGATION**.
    - Only **READY_TO_SEND** when window is closed, root cause confirmed, backfill done, SLA credit determined, and owners assigned. Lean toward NEEDS_FINANCE_REVIEW when a credit percentage is being granted but not yet approved.

---

## Common misjudgments / exclusion rules
- **Do NOT run/charge diagnostics** for tickets that short-circuit (invalid account, auth failure, suspended account, or active outage). `diagnostic_needed/diagnostic_required = false` there, and issue booleans stay false.
- **Do NOT escalate** auto-fixable root causes (CONFIGURATION_DRIFT, VOICE_PROFILE_STALE, PROVISIONING_STALE, GENERATED_*) — they resolve via troubleshooting (escalation NONE). Reserve escalation for hard faults (BACKBONE_CAPACITY -> NETWORK_ENGINEERING; FIBER/SIGNAL -> FIELD_OPS) and account/billing blocks (ACCOUNTS_PAYABLE).
- **Outage relevance**: only count an outage if it's `active:true` AND the ticket's `service_type` is in its `service_types`. An active outage in a different service area or for a different service does not apply.
- **Suspended account != fixable**: never route a suspended account to network troubleshooting. It is an account/billing block (ACCOUNTS_PAYABLE / INELIGIBLE_ACCOUNT / BILLING_RECOVERY).
- **Set issue booleans from the DIAGNOSTIC (pre-fix) readings**, not the post-troubleshooting values.
- **Refuel charge uses the line's actual plan** `data_refueling_price_per_gb` (PREMIUM $2, BASIC $5, PLUS $0.1, FAMILY $3...). Never assume a flat rate; always read the plan. Respect customer preferences (accepted GB, no plan change).
- **ENABLE_LINE_ROAMING (carrier side) vs TOGGLE_ROAMING (device side)** are different actions: check `line.roaming_enabled` first, then `device.phone_roaming_enabled`. Carrier change -> carrier_update_required/CARRIER_UPDATE.
- **Enterprise owners**: don't swap engineering_owner and account_owner; don't use finance_owner as account_owner. `query=INC-####` to messages usually returns empty — search by client name or owner.
- **failed_days = count of FAILED runs**, not (end-start) calendar diff; backfill_days normally equals failed_days. Cross-check with any message that explicitly states a day count.
- Recompute EVERY summary count from your own per-row decisions before emitting; a mismatch between rows and summary is an automatic error.
- Emit ONLY the JSON object; exact enum/string/number formatting is graded.
