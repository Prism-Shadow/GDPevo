# Support-Console Case/Ticket Resolution Skill

## When to use
Use this skill for support-operations tasks that hand you a small batch/queue/worklist
(CSV or JSON) of tickets, mobile cases, or an enterprise complaint, and ask you to
classify each item and emit a strict JSON answer. Every decision must be derived from
records in the shared support-console REST API — never from the customer's free-text
report alone. The free-text note only hints where to look; the record fields decide.

## API base URL and lookup chaining
Base URL: `<remote-env-url>` (overrides any `127.0.0.1:8057` in prompts).
All endpoints are GET and read-only. Use `curl -s`.

Core endpoints and how to chain them:
- `GET /api/catalog` — endpoint list + record counts (sanity check only).
- Tickets: `GET /api/tickets/<id>` -> gives `account_id`, `service_area`, `service_type`,
  `subscribed_mbps`, `status`.
  - Then `GET /api/accounts/<account_id>` for account `status` + `authentication`.
  - `GET /api/outages?service_area=<area>` for active outages in that area.
  - `GET /api/diagnostics/<ticket_id>` for pre-fix metrics + `root_causes`.
  - `GET /api/troubleshooting/<ticket_id>` for post-fix metrics + `steps`.
- Mobile cases: `GET /api/cases/<id>` -> gives `customer_id`, `line_id`, `device_id`,
  `issue_type`, `customer_location`.
  - `GET /api/lines/<line_id>` (status, suspension_reason, roaming_enabled, data_used_gb, plan_id).
  - `GET /api/devices/<device_id>` (settings/toggles).
  - `GET /api/plans/<plan_id>` (data_limit_gb, data_refueling_price_per_gb).
  - `GET /api/bills` (filter by customer_id; find Overdue bill + amount_due_usd).
- Enterprise: `GET /api/enterprise/incidents/<id>`, `GET /api/enterprise/accounts`,
  `GET /api/enterprise/export-runs?incident_id=<id>`, `GET /api/enterprise/sla/<ent_acct_id>`,
  `GET /api/enterprise/messages?query=<text>` (single keyword works best; try the client
  name, "credential", "backfill", "alert", etc.).

A "not_found" / error account => the account ID is invalid (see INVALID_ACCOUNT rule).

## Output-format discipline (applies to every task)
- Return ONLY a JSON object conforming exactly to that task's `answer_template.json`.
- Preserve the input order of items (payload/CSV order, or ascending case_id when the
  template says so). Do not sort or drop items.
- Match enums EXACTLY (case + spelling). Booleans are real booleans.
- Numbers: respect stated precision — "two decimals" => 4.00, "one decimal" => 2.0.
- Empty string `""` for ID fields that don't apply (e.g. `outage_id`, `bill_id`), not null.
- Recompute every summary/count field from your own per-item decisions; an inconsistent
  summary loses points even when the items are right. Counts depend on the routes/statuses
  you assigned, so finalize items first, then tally.

---

## SOP 1 — Offline ticket batch resolution / queue triage
(answer template has `ticket_decisions[]` + a `batch_summary`/`queue_summary`)

For each ticket, evaluate blockers in this PRIORITY order. The FIRST that matches decides
status/route/blocker; stop there.

1. **Invalid account** — `GET /api/accounts/<id>` returns not_found, OR the ticket's
   account_id does not match the `ACC-` pattern (e.g. `BAD-####`).
   => status FAILED, route/blocker INVALID_ACCOUNT, team NONE, diagnostic = false.
2. **Auth failure** — account `authentication.last_login_status == "FAILURE"` or
   `account_recovery_status == "FAILURE"`.
   => status FAILED, blocker AUTH_FAILED (route AUTH_FAILED), team NONE, diagnostic = false.
3. **Suspended / overdue** — account `status == "Suspended"`.
   => status **FAILED** (a suspension cannot be cleared in-session), blocker OVERDUE_SUSPENSION,
   team ACCOUNTS_PAYABLE (when that team enum exists; else NONE), diagnostic = false.
   In a route-only template with INELIGIBLE_ACCOUNT, use route INELIGIBLE_ACCOUNT.
   PITFALL: a suspended/overdue account is FAILED, NOT PENDING_ACTION.
4. **Active outage** — `GET /api/outages?service_area=<area>` has an entry with
   `active == true` AND the ticket's `service_type` is in its `service_types`.
   => status PENDING_ACTION (customer must wait), blocker ACTIVE_OUTAGE,
   route OUTAGE_WAIT (route-template) / team NONE, set `outage_id`, diagnostic = false.
5. **Otherwise a real service issue** — run diagnostics + troubleshooting logic below.

Service-issue resolution (account Active, no outage):
- Read diagnostics (pre) and troubleshooting (post) metrics. `diagnostic_required`/
  `diagnostic_needed` = true for these real service tickets.
- Compute issue flags from the DIAGNOSTIC (pre-fix) metrics:
  - `latency_issue`  = latency_ms  > 100
  - `stability_issue`= jitter_ms   > 30
  - `bandwidth_issue`= bandwidth_mbps < ~80% of subscribed_mbps
    (note: bandwidth can legitimately exceed the subscribed rate -> no issue then)
- Decide RESOLVED vs ESCALATED from the POST-troubleshooting metrics:
  - If post latency_ms <= ~100 AND post jitter_ms <= ~30 (issue cleared)
    => status RESOLVED, route AUTO_TROUBLESHOOTING, team NONE.
  - If post metrics are STILL above threshold (troubleshooting did not fix it)
    => status ESCALATED, route ESCALATION, pick team by root cause:
      - FIBER_DROP_DAMAGE / SIGNAL_LOSS / physical line fault -> FIELD_OPS
        (blocker PHYSICAL_LINE_FAULT)
      - BACKBONE_CAPACITY / network capacity -> NETWORK_ENGINEERING
        (blocker NETWORK_CAPACITY)
      - PROVISIONING_STALE / CONFIGURATION_DRIFT / profile issues -> TIER2_SUPPORT
        (blocker PROVISIONING_STALE)
- For non-service blockers (rules 1-4) all three issue flags can be false; the flags are
  only graded meaningfully for diagnosed service tickets.

Summary block: count statuses (RESOLVED/PENDING_ACTION/ESCALATED/FAILED) and route teams
(TIER2_SUPPORT/FIELD_OPS/NETWORK_ENGINEERING/ACCOUNTS_PAYABLE) across your decisions.
`tickets_requiring_customer_wait` = number of PENDING_ACTION / OUTAGE_WAIT tickets.

---

## SOP 2 — Contact-center / mobile-data case triage
(answer template has `case_decisions[]` + a `queue_summary`/`worklist_summary`)

For each case, pull line + device (+ bill/plan as needed) and pick the SINGLE root-cause fix.
Read the actual device/line FIELD that contradicts working service; the reported issue text
just points you at the category.

Diagnosis -> action map:
- `line.status == "Suspended"` with `suspension_reason == "OVERDUE_BILL"`: customer wants to
  pay -> primary SEND_PAYMENT_REQUEST, secondary RESUME_LINE_REBOOT, `bill_id` = the Overdue
  bill, `charge_amount_usd` = that bill's `amount_due_usd`, route BILLING_RECOVERY.
- `device.sim_status == "missing"` (no service): primary RESEAT_SIM, route SELF_SERVICE.
- `device.mobile_data_enabled == false`: primary TOGGLE_MOBILE_DATA, route DEVICE_SETTING_FIX
  (or SELF_SERVICE).
- `device.data_saver_mode == true` (slow data): primary TOGGLE_DATA_SAVER,
  route DEVICE_SETTING_FIX.
- `device.vpn_connected == true` (slow data): primary DISCONNECT_VPN, route SELF_SERVICE.
- `device.network_mode_preference` is an old mode (e.g. "3g_only") on slow data:
  primary SET_NETWORK_MODE, route DEVICE_SETTING_FIX. (NOT a carrier update.)
- Roaming abroad (`customer_location == "abroad"`, no data):
  - If the DEVICE roaming is off (`phone_roaming_enabled == false`) but the line is fine
    -> primary TOGGLE_ROAMING, this is a device toggle => route SELF_SERVICE,
    `carrier_update_required = false`.
  - If the LINE roaming is off (`line.roaming_enabled == false`) -> primary
    ENABLE_LINE_ROAMING, route CARRIER_UPDATE, `carrier_update_required = true`.
- MMS can't send photos (`can_send_mms == false`): missing messaging permission.
  primary GRANT_MESSAGING_PERMISSION, set `permission` to exactly the missing one(s):
  `sms`, `storage`, or `sms_and_storage` (check `messaging_permissions.sms`/`.storage`;
  the value off is the one to grant). Route SELF_SERVICE.
- Over data limit (`line.data_used_gb` > plan `data_limit_gb`, data stopped):
  primary REFUEL_DATA. `data_refuel_gb` = the customer's `accepted_refuel_gb` from
  preferences (respect `does_not_want_plan_change`). `charge_amount_usd` =
  data_refuel_gb * plan `data_refueling_price_per_gb`. Route DATA_RECOVERY.
- Nothing actionable / out of scope -> TRANSFER_HUMAN, route HUMAN_TRANSFER.

`secondary_action` = NO_ACTION unless a clear follow-up is implied (e.g. resume+reboot
after a payment). `permission` = NONE unless granting messaging permission.

Route vs carrier_update_required — CRITICAL distinction (cost points until corrected):
- CARRIER_UPDATE / `carrier_update_required = true` is ONLY for line/carrier-side changes,
  chiefly ENABLE_LINE_ROAMING (line.roaming_enabled was false).
- Anything the agent flips on the device (roaming toggle, mobile-data toggle, data-saver,
  network-mode, VPN, SIM reseat) is a device/self-service fix, NOT a carrier update.

Summary counts (recompute from your routes):
- data_refuel_cases = REFUEL_DATA cases; carrier_updates = CARRIER_UPDATE routes;
  device_setting_fixes = DEVICE_SETTING_FIX routes; human_transfers = HUMAN_TRANSFER routes;
  self_service_fixes = SELF_SERVICE routes; billing_recoveries = BILLING_RECOVERY routes.
- `total_estimated_customer_charge_usd` = sum of all per-case `charge_amount_usd`,
  two decimals. Charges only arise from data refuels and overdue-bill payments.

---

## SOP 3 — Enterprise export-complaint response package
(single flat object; identify the incident from the complaint email's reference)

Steps:
1. Identify the incident from the email's reference -> `GET /api/enterprise/incidents/<id>`.
   That record directly gives `enterprise_account_id`, `severity`, `engineering_owner`,
   `account_owner`, `product`, `status`. Copy these IDs/severity verbatim.
2. `GET /api/enterprise/export-runs?incident_id=<id>`: the consecutive FAILED runs define the
   failure window. `start_date` = first failed run_date, `end_date` = last failed run_date,
   `failed_days` = count of FAILED runs. The shared `failure_code` (e.g. STALE_CREDENTIAL) is
   the root-cause category. A later SUCCEEDED run is the recovery run, not a backfill.
3. `GET /api/enterprise/sla/<ent_acct_id>`: `sla_credit_percent` = the contract's export
   credit percent when its `credit_trigger` (e.g. "3 consecutive failed runs") is met.
4. `GET /api/enterprise/messages?query=<client/keyword>`: corroborate root cause; the channel
   a key alert landed in matters. If the credential/alert evidence was posted to an
   ARCHIVED alerts channel (channel name containing "archive"), set
   `contributing_alert_issue = ARCHIVED_ALERT_ROUTE`; else NONE (or UNKNOWN if truly unclear).
5. `share_permissions`: include exactly the users listed in `response_requirements`
   (`permission_users_to_include`), in that listed order. The finance/account stakeholder
   gets `view`; the engineering/working reviewer gets `edit`. (upload_only is rarely correct.)
6. Naming artifacts follow `naming_style`: produce a lowercase-hyphen channel slug from the
   client name (+ "export"/"incident"); a "<client-slug>-<date>" evidence folder; and a
   "<Client Full Name> Export Failure Report" title. Reuse the client's exact account `name`
   (including any "Inc.") for the title.
7. `response_status`: when an SLA credit must still be applied/approved, NEEDS_FINANCE_REVIEW;
   otherwise mirror the incident's own status (e.g. UNDER_INVESTIGATION).

Enterprise pitfalls learned:
- `backfill_days` is NOT automatically the failed-day count. Only count days that the
  evidence (messages/export-runs) explicitly says were (or must be) manually backfilled.
  If no backfill is confirmed for THIS client, use 0 — do not copy the failed_days number,
  and do not borrow a backfill figure that belongs to a different client's incident.
- Messages and SLA figures from OTHER incidents/clients show up in keyword searches.
  Always confirm the message's client/account matches the incident before using its
  numbers (credit %, backfill days, root cause).
- Copy owner user-ids and IDs exactly from the incident/account records; do not invent.

---

## General pitfalls (cross-task)
- Derive from records, not from the customer's wording. The note tells you the symptom
  category; the record field tells you the truth (and sometimes contradicts the note).
- Apply blocker precedence (invalid > auth > suspension > outage > service issue); a
  higher-priority blocker overrides any technical diagnosis underneath it.
- A fix only counts as RESOLVED when post-fix metrics actually clear thresholds; marginal
  improvement that stays above threshold is an ESCALATION.
- Recompute summaries last, strictly from your finalized per-item decisions.
- Keep precision and enum spelling exact; preserve item order.
