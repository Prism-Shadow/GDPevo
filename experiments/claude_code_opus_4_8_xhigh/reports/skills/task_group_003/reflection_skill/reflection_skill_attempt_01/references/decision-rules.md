# Decision Rules Reference

Lookup tables and field semantics for the CRM ticket/case resolution skill. Read this when
unsure which enum value, team, route, or field meaning applies. Rules verified against the
support console at `http://127.0.0.1:8086`.

## Table of contents
1. Ticket classification — gate → outcome matrix
2. SLA thresholds and the two metric reads
3. Root cause → key_blocker → team
4. Mobile action → route mapping
5. Field-by-field semantics
6. Catalog of mistakes to avoid (from reflection)

---

## 1. Ticket classification — gate → outcome matrix

Apply gates top to bottom; first match wins. `diagnostic` means
`diagnostic_required` (queue template) or `diagnostic_needed` (batch template).

| Gate (first match wins) | status | route / key_blocker | team | diagnostic | flags |
|---|---|---|---|---|---|
| Account not found / bad id | FAILED | INVALID_ACCOUNT | NONE | false | all false |
| `last_login_status`/`account_recovery_status` == FAILURE | FAILED | AUTH_FAILED | NONE | false | all false |
| Suspended — overdue/billing reason | FAILED | OVERDUE_SUSPENSION / INELIGIBLE_ACCOUNT | ACCOUNTS_PAYABLE | false | all false |
| Suspended — fraud reason | FAILED | FRAUD_SUSPENSION | per enum (often NONE) | false | all false |
| Suspended — generic hold, no billing signal | FAILED | INELIGIBLE_ACCOUNT | NONE | false | all false |
| Active outage matches area+type | PENDING_ACTION | ACTIVE_OUTAGE / OUTAGE_WAIT | NONE | false | all false |
| Diagnosed, post-fix all metrics within SLA | RESOLVED | AUTO_TROUBLESHOOTING / NONE | NONE | true | pre-fix values |
| Diagnosed, post-fix any metric out of SLA | ESCALATED | ESCALATION / cause blocker | by root cause | true | pre-fix values |

Key independence: **status and team are separate fields.** A FAILED row may still carry a
non-NONE `route_team`/`escalation_team` (e.g. an overdue suspension is FAILED + ACCOUNTS_PAYABLE).
Do not assume FAILED forces team NONE, and do not assume a non-NONE team forces ESCALATED.

`tickets_requiring_customer_wait` counts exactly the rows that hit the active-outage gate.

### Outage match — all three required
`outage.active == true` AND `outage.service_area == ticket.service_area` AND
`ticket.service_type ∈ outage.service_types`. Query
`GET /api/outages?service_area=<ticket.service_area>` then verify type membership. A matching
area with the wrong service_type, or an inactive outage, is NOT a match — fall through to
diagnosis.

---

## 2. SLA thresholds and the two metric reads

Thresholds are NOT exposed by any endpoint; these are inferred from graded outcomes and must be
applied by hand.

Within-SLA means: `latency_ms <= 100`, `jitter_ms <= 30`,
`bandwidth_mbps >= ~85% of subscribed_mbps`.

Observed graded boundary (post-troubleshooting metrics):
- RESOLVED examples: lat 82/79, jit 21/18, bw 90.7%/93.0% of subscribed.
- ESCALATED examples: lat 121/176/198, jit 32/41/43, bw 81.3%/66.4%/59.6%.
- So the latency cut sits at 100 (82 passes, 121 fails); jitter at 30 (21 passes, 32 fails);
  bandwidth floor lies between 81.3% (fail) and 90.7% (pass) — use ~85% and treat 81% as failing.

A ticket is RESOLVED only if **all three** post metrics pass; any single failure ⇒ ESCALATED.
There is no "partially fixed" PENDING state — PENDING_ACTION belongs to the outage gate only.

Two distinct reads of the metrics:
- **Issue flags** (`latency_issue`, `stability_issue`=jitter, `bandwidth_issue`): computed from
  the **diagnostic / pre-troubleshooting** metrics. A flag is true when that pre-fix metric is
  out of SLA.
- **RESOLVED vs ESCALATED**: computed from the **troubleshooting / post-fix** metrics.

Gated tickets (gates 1–4) never reach diagnosis: all issue flags false, diagnostic false.

`GENERATED_NOISE` in a diagnostic's `root_causes` marks a decoy record — ignore it.

---

## 3. Root cause → key_blocker → escalation team

| diagnostic root_cause | key_blocker | team |
|---|---|---|
| FIBER_DROP_DAMAGE, SIGNAL_LOSS, physical faults | PHYSICAL_LINE_FAULT | FIELD_OPS |
| BACKBONE_CAPACITY, capacity | NETWORK_CAPACITY | NETWORK_ENGINEERING |
| PROVISIONING_STALE (not cleared by auto-fix) | PROVISIONING_STALE | TIER2_SUPPORT |
| CONFIGURATION_DRIFT, VOICE_PROFILE_STALE | usually clears → NONE | NONE (escalate only if post-fix still bad) |

Pick the team from the root cause only when the ticket actually escalates (post-fix metrics
still out of SLA). If auto-troubleshooting brought metrics back within SLA, it is RESOLVED with
team NONE regardless of the original root cause.

---

## 4. Mobile action → route mapping

| Situation (read from device/line/bill) | primary_action | route / flags |
|---|---|---|
| `mobile_data_enabled == false` | TOGGLE_MOBILE_DATA | DEVICE_SETTING_FIX |
| `data_saver_mode == true`, slow | TOGGLE_DATA_SAVER | DEVICE_SETTING_FIX |
| `vpn_connected == true`, slow | DISCONNECT_VPN | DEVICE_SETTING_FIX / SELF_SERVICE |
| `network_mode_preference` stuck on old (e.g. 3g_only), slow | SET_NETWORK_MODE | DEVICE_SETTING_FIX |
| `sim_status` missing | RESEAT_SIM | SELF_SERVICE |
| MMS photo fails, missing `messaging_permissions.storage` | GRANT_MESSAGING_PERMISSION (permission=storage) | SELF_SERVICE |
| abroad, line.roaming_enabled true, device.phone_roaming_enabled false | TOGGLE_ROAMING | SELF_SERVICE (device gap) |
| abroad, line.roaming_enabled false | ENABLE_LINE_ROAMING | CARRIER_UPDATE, carrier_update_required=true |
| over `plan.data_limit_gb` (data_used_gb > limit) | REFUEL_DATA | DATA_RECOVERY, charge = gb * price_per_gb |
| line Suspended w/ Overdue bill | SEND_PAYMENT_REQUEST + RESUME_LINE_REBOOT | BILLING_RECOVERY, bill_id + amount |
| nothing self/carrier/billing can fix | TRANSFER_HUMAN | HUMAN_TRANSFER |

Principle: the fix's **location** decides the route. Device toggles → SELF_SERVICE /
DEVICE_SETTING_FIX (no charge, no carrier update). Line/carrier provisioning → CARRIER_UPDATE.
Billing → BILLING_RECOVERY. Always check the actual flag values rather than the customer's
narrative — "roaming on but no data" can be either a device or a line gap depending on which
flag is off.

`permission` enum: `NONE` | `sms` | `storage` | `sms_and_storage`. Grant only the permission(s)
currently false. Do not list a permission that is already true.

`secondary_action`: `NO_ACTION` unless the primary genuinely needs a follow-up step (the clear
case is pay-then-resume for a billing block).

---

## 5. Field-by-field semantics

- `final_resolution_status`: RESOLVED | PENDING_ACTION | ESCALATED | FAILED. PENDING_ACTION =
  outage-wait only. FAILED = unworkable account state (not found / auth / suspended). ESCALATED
  = a real fault auto-fix couldn't clear, handed to a team.
- `resolution_route` / `final_route`: the path taken. Match it to the gate/action that fired.
- `escalation_team` / `route_team`: NONE | TIER2_SUPPORT | FIELD_OPS | NETWORK_ENGINEERING |
  ACCOUNTS_PAYABLE. Independent of status (see §1).
- `key_blocker`: the specific reason; use the enum member that matches the gate/cause.
- `diagnostic_needed` / `diagnostic_required`: true only for tickets that actually reach the
  diagnose step (gate 5). False for every gated ticket.
- `outage_id`: the matched outage id, else `""`.
- enterprise `sla_credit_percent`: integer percent from the SLA contract / escalation message.
- enterprise `failed_days` / `backfill_days`: count of FAILED export runs (backfill = re-run the
  failed days; the recovery SUCCEEDED run is not a failed day).
- enterprise `share_permissions`: keep the requirement's user order; permission by role
  (finance/review → view, contributor → edit, intake → upload_only).
- enterprise `response_status`: NEEDS_FINANCE_REVIEW when an SLA credit must be issued; otherwise
  READY_TO_SEND / NEEDS_ENGINEERING_REVIEW / UNDER_INVESTIGATION per evidence.

---

## 6. Catalog of mistakes to avoid (from reflection)

These are concrete errors made on the training set. Each cost graded fields.

1. **Escalating auth failures.** Auth FAILURE → FAILED + team NONE. It is not a TIER2 escalation.
2. **Escalating suspensions.** Suspended → FAILED, not ESCALATED. The team is set by the
   suspension reason, not by the status.
3. **Over-routing a generic hold.** Only send a suspension to ACCOUNTS_PAYABLE when the reason
   text says overdue/billing. A bare "account hold notice" with no billing signal → team NONE.
4. **Calling a half-fixed ticket PENDING_ACTION.** Post-troubleshooting metrics still out of SLA
   (e.g. latency 121 ms) → ESCALATED, not PENDING_ACTION. PENDING_ACTION is outage-wait only.
5. **Using too low a bandwidth floor.** 80% was too lenient; ~81% should fail. Use ~85% and lean
   toward "fail" for clearly-low bandwidth.
6. **Conflating the two metric reads.** Issue flags = pre-fix diagnostic; RESOLVED/ESCALATED =
   post-fix troubleshooting.
7. **Pasting raw enum codes into free-text fields.** For enterprise `root_cause_category` and
   the constructed name fields, write concise human prose per `naming_style`, not the machine code.
8. **Forgetting summaries are derived.** Always recount summary integers from your own rows;
   a mismatch is an automatic loss.
