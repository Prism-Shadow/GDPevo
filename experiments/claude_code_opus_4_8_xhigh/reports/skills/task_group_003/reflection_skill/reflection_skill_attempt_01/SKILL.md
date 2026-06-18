---
name: crm-ticket-resolution
description: >-
  Resolve CRM support-console tickets and cases into a strict JSON answer template.
  Use this whenever a task asks you to classify, route, or resolve service tickets,
  mobile support cases, mobile-data worklists, or enterprise incident/export complaints
  by reading records from a read-only support-console API and returning structured JSON
  (final_resolution_status, resolution_route, primary_action, sla_credit_percent,
  share_permissions, batch/queue/worklist summaries, etc.). Trigger it even when the
  prompt only says "resolve this batch", "classify the queue", "choose the next operation",
  or "prepare the response package" without naming a schema — the work is the same:
  join records across the console, apply the gating SOP, then emit template-conformant JSON.
---

# CRM Ticket & Case Resolution

You are a support-operations analyst. Each task hands you a batch/queue/worklist (CSV or
JSON) plus an `answer_template.json`. Your job: for every item, look up the truth in the
shared support console, apply the correct decision SOP, and emit JSON that conforms exactly
to the template. Decisions must come from console records, never from assumptions about the
customer's prose.

These SOPs are distilled from graded mistakes. The pitfalls called out below are real errors
that cost points; read them as "do not repeat this."

## 0. Environment & output discipline (applies to every task)

- **Base URL is always `http://127.0.0.1:8086`.** The prompt text often says `8057` (or
  another port). Ignore it — the harness override wins. Send only GET requests.
- Start with `GET /api/catalog` to see available collections and record counts. Use
  `GET /api/search?q=<id-or-text>` to pull every record touching an id in one call — this is
  the fastest way to join an account/ticket/case to its related records.
- **Conform to the template literally.** Preserve the requested item order (the template
  says e.g. "preserve payload order" or "ascending case_id order"). Output every field the
  template lists, using the exact enum spellings. Output ONLY the JSON object — no prose,
  no markdown fences.
- **Numbers:** emit the number; `4.0` and `4.00` are numerically equal and both accepted, so
  don't agonize over trailing zeros — but DO respect "one decimal" vs "two decimal" intent
  for `data_refuel_gb` (one) vs `charge_amount_usd` (two). Use `0.0`/`0.00` when not
  applicable, never `null` or empty string for a numeric field.
- **`""` (empty string), not `null`,** for inapplicable string fields (`outage_id`,
  `bill_id`, etc.). `"NONE"` is for enum fields that have a NONE member.
- **Recompute every summary by tallying your own per-item decisions.** A summary that
  doesn't equal the count of your rows is an automatic loss. Tally last, after all rows.

## 1. Pick the workflow

| Signal in prompt / template | Workflow | Reference |
|---|---|---|
| tickets, `final_resolution_status`, `resolution_route`/`key_blocker`, outages, diagnostics | **Ticket classification** | §2 |
| mobile cases, `primary_action`, `permission`, `final_route` SELF_SERVICE/BILLING/CARRIER | **Mobile case actions** | §3 |
| mobile-data worklist, `data_refuel_gb`, `carrier_update_required`, `total_estimated...charge` | **Mobile-data recovery** | §3 |
| enterprise incident, export complaint, `sla_credit_percent`, `share_permissions` | **Enterprise response package** | §4 |

Read `references/decision-rules.md` for the full enum→cause→team lookup tables and the
field-by-field semantics. Read it whenever you are unsure which enum value or team to emit.

## 2. Ticket classification SOP (offline ticket batch / queue snapshot)

Per ticket, resolve the account, then walk these gates **strictly in order**. The FIRST gate
that matches decides the outcome; stop there. This ordering is load-bearing — a billing
suspension must not be diagnosed, and an outage must not be escalated.

1. **Account not found** (lookup returns `not_found`, or the account id doesn't exist) →
   `INVALID_ACCOUNT`, status **FAILED**, team **NONE**, `diagnostic_required/needed = false`.
2. **Authentication failure** (`authentication.last_login_status == "FAILURE"` or
   `account_recovery_status == "FAILURE"`) → `AUTH_FAILED`, status **FAILED**, team **NONE**,
   diagnostic false.
   - PITFALL I HIT: I escalated auth failures to TIER2_SUPPORT. Wrong. Auth failure is a hard
     **FAILED with team NONE** — it is not an escalation. Do not invent a team for it.
3. **Account suspended** (`account.status == "Suspended"`) → status **FAILED**, diagnostic
   false. The **route_team depends on the suspension reason**, read from the ticket's
   `issue_summary`/`queue_note` (and `line.suspension_reason` for mobile):
   - overdue / billing / "overdue notice" → `key_blocker = OVERDUE_SUSPENSION`, team
     **ACCOUNTS_PAYABLE**.
   - fraud → `key_blocker = FRAUD_SUSPENSION`, team appropriate to the enum (often NONE).
   - generic "account hold" with no billing reason → resolution_route `INELIGIBLE_ACCOUNT`,
     team **NONE**.
   - PITFALL I HIT (twice): I marked suspended accounts **ESCALATED**. Wrong — suspension is
     **FAILED**, not ESCALATED. And I added ACCOUNTS_PAYABLE to a generic hold that had no
     overdue signal. Only route to ACCOUNTS_PAYABLE when the text actually says overdue/billing.
     A FAILED row CAN still carry a non-NONE team (e.g. ACCOUNTS_PAYABLE) — status and team are
     independent fields.
4. **Active outage** covering this ticket → status **PENDING_ACTION**, `key_blocker =
   ACTIVE_OUTAGE` / route `OUTAGE_WAIT`, team **NONE**, diagnostic false, and this row counts
   toward `tickets_requiring_customer_wait`. An outage matches ONLY when ALL of:
   `outage.active == true` **AND** `outage.service_area == ticket.service_area` **AND**
   `ticket.service_type ∈ outage.service_types`. A near-miss on any of the three is NOT a match.
5. **Otherwise diagnose.** Pull `GET /api/diagnostics/<ticket_id>` and
   `GET /api/troubleshooting/<ticket_id>`. These tickets have `diagnostic_required/needed =
   true`. Auto-troubleshooting runs; judge the **post-troubleshooting** metrics against SLA
   (§2.1). If all metrics are back within SLA → **RESOLVED**, route `AUTO_TROUBLESHOOTING`,
   team NONE. If any metric is still out of SLA → **ESCALATED**, route `ESCALATION`, team by
   root cause (§2.2).

### 2.1 SLA thresholds (NOT documented in the API — apply these inferred cutoffs)

A metric is **within SLA** when:
- `latency_ms <= 100`
- `jitter_ms <= 30`
- `bandwidth_mbps >= ~85% of the ticket's subscribed_mbps` (a value in the high-80s%/low-90s%
  passes; ~81% or below fails. The exact floor is between 81% and 90% — treat clearly-low
  bandwidth as failing and only-slightly-below as borderline-failing.)

A ticket is RESOLVED only when **all three** post-troubleshooting metrics pass. If even one
fails, the result is **ESCALATED**.
- PITFALL I HIT: when post-troubleshooting left latency at 121 ms (and bandwidth ~81%) I
  called it `PENDING_ACTION`. Wrong — still-out-of-SLA after auto-fix is **ESCALATED**, not
  PENDING_ACTION. **PENDING_ACTION is reserved for the outage-wait gate (#4)**, not for
  partially-fixed metrics.

### 2.2 Issue flags vs. resolution — two different metric reads

When the template has `latency_issue` / `stability_issue` / `bandwidth_issue` booleans,
compute them from the **diagnostic (pre-troubleshooting)** metrics, using the same cutoffs:
`latency_issue = diag.latency_ms > 100`, `stability_issue = diag.jitter_ms > 30`,
`bandwidth_issue = diag.bandwidth_mbps < ~85% of subscribed`. (stability == jitter.)
For any ticket stopped at a gate (#1–#4) set all three flags `false` and diagnostic `false` —
those tickets never reach diagnosis. So: **issue flags read the pre-fix diagnostic; the
RESOLVED/ESCALATED status reads the post-fix troubleshooting.** Don't conflate them.

### 2.3 Root cause → escalation team (read diagnostic `root_causes`)

- `FIBER_DROP_DAMAGE`, `SIGNAL_LOSS`, physical line faults → **FIELD_OPS**
  (`key_blocker = PHYSICAL_LINE_FAULT`).
- `BACKBONE_CAPACITY`, network capacity → **NETWORK_ENGINEERING**
  (`key_blocker = NETWORK_CAPACITY`).
- `PROVISIONING_STALE` (and other software/config faults that auto-fix didn't fully clear) →
  **TIER2_SUPPORT** (`key_blocker = PROVISIONING_STALE`).
- `CONFIGURATION_DRIFT`, `VOICE_PROFILE_STALE` → these usually auto-resolve cleanly →
  RESOLVED, team NONE. Only escalate if post metrics remain out of SLA.
- Ignore diagnostics whose `root_causes` contain `GENERATED_NOISE` — those are decoy/filler
  records, not your ticket's real cause.

## 3. Mobile case / data-recovery SOP

Join `case → line → device → bill → plan` (use `/api/cases/<id>`, `/api/lines/<id>`,
`/api/devices/<id>`, `/api/bills`, `/api/plans/<id>`). Diagnose the device/line state, not the
customer's wording. Single-step fixes get `secondary_action = NO_ACTION`; only add a secondary
when the primary genuinely requires a follow-up (e.g. payment then line resume).

Route by where the fix lives:
- **Device-side toggle** (mobile data, data-saver, VPN, airplane mode, network mode, SIM
  reseat, messaging permission, **device** `phone_roaming_enabled`) → `SELF_SERVICE` /
  `DEVICE_SETTING_FIX`, no charge, no carrier update.
- **Line/carrier-side change** (the **line** `roaming_enabled` flag, network provisioning) →
  `CARRIER_UPDATE`, `carrier_update_required = true`.
  - Roaming-abroad disambiguation (a recurring trap): if `line.roaming_enabled == true` but
    `device.phone_roaming_enabled == false`, the gap is on the device → `TOGGLE_ROAMING` +
    SELF_SERVICE. If `line.roaming_enabled == false` (regardless of the device), the line needs
    it → `ENABLE_LINE_ROAMING` + CARRIER_UPDATE. Check both flags before choosing.
- **Billing block** (`line.status == "Suspended"` with overdue bill; bill `status ==
  "Overdue"`) → `SEND_PAYMENT_REQUEST` (primary) + `RESUME_LINE_REBOOT` (secondary),
  `BILLING_RECOVERY`, `bill_id` set, `charge_amount_usd = bill.amount_due_usd`.
- **Genuinely unresolvable by self/carrier/billing** → `TRANSFER_HUMAN` / `HUMAN_TRANSFER`.

Messaging-permission cases: grant exactly the missing permission(s). Check
`device.messaging_permissions` — grant only the false one(s). MMS photo failures are typically
the `storage` permission; if both `sms` and `storage` are missing use `sms_and_storage`. Don't
over-grant a permission that's already true.

Data refuel (`REFUEL_DATA`): when the customer over-ran `plan.data_limit_gb`. Use the
customer's accepted amount from `customer_preferences` when given (don't compute full overage if
they accepted a smaller top-up and refused a plan change). `data_refuel_gb = accepted_gb`,
`charge_amount_usd = accepted_gb * plan.data_refueling_price_per_gb`. Sum all per-case charges
into `total_estimated_customer_charge_usd`.

## 4. Enterprise response-package SOP

Identify the incident, then assemble the package from evidence. Endpoints:
`/api/enterprise/incidents/<id>`, `/api/enterprise/accounts`, `/api/enterprise/export-runs?
incident_id=<id>`, `/api/enterprise/sla/<enterprise_account_id>`,
`/api/enterprise/messages?query=<text>`.

- **Structured / looked-up fields — get these exactly right (they are graded strictly):**
  `incident_id`, `enterprise_account_id`, owners (`engineering_owner`, `account_owner` from the
  incident record), `severity` (from the incident), `sla_credit_percent` (from the SLA contract
  / escalation message), `contributing_alert_issue` (e.g. `ARCHIVED_ALERT_ROUTE` when the
  root-cause alert landed in an archived channel).
- **`failure_window` / `failed_days` / `backfill_days`:** count the **FAILED** export runs for
  the incident. Window = first..last failed run date; `failed_days` = that count; `backfill_days`
  = the number of failed days that must be re-run (= failed_days; the later SUCCEEDED run is the
  recovery, not a failed day).
- **`share_permissions`:** output users in the EXACT order listed in the requirements'
  `permission_users_to_include` — do not re-sort. Assign permission per role (finance/reviewer →
  `view`; contributor/editor → `edit`; intake-only → `upload_only`).
- **`response_status`:** if the response hinges on issuing an SLA credit, it `NEEDS_FINANCE_REVIEW`
  even if every fact is known. Use `READY_TO_SEND` only when nothing requires another team's
  sign-off.
- **Free-text / constructed name fields** (`root_cause_category`, `channel_name`,
  `evidence_folder`, `report_title`): follow the `naming_style` instructions and prefer concise,
  human-readable prose drawn from the evidence (e.g. "stale credential after rotation") over a
  raw enum code. These are the lowest-confidence fields; spend effort on the structured fields
  above first, then phrase names naturally per the requested style rather than pasting machine
  codes.

## Final check before emitting

1. Every template field present, enum spellings exact, item order preserved.
2. Each summary count re-derived from your rows and matches.
3. Numeric fields are numbers (right decimal intent), inapplicable strings are `""`, enum-NONE
   is `"NONE"`.
4. No prose, no fences — just the JSON object.
