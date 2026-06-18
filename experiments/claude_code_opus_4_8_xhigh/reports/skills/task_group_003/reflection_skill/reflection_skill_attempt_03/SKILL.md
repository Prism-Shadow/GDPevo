---
name: crm-support-ticket-resolution
description: >-
  Resolve CRM support-console service tickets, mobile-data/line cases, and enterprise
  export-failure complaints into the exact JSON an answer_template.json asks for. Use
  this whenever a task hands you a ticket batch (CSV/JSON), a case/worklist queue, or an
  enterprise complaint email plus an answer_template, and tells you to read from a
  support console (e.g. an API like http://127.0.0.1:80xx with /api/tickets,
  /api/accounts, /api/diagnostics, /api/cases, /api/lines, /api/devices,
  /api/enterprise/*). Triggers on phrases like "resolve this batch of tickets",
  "classify each ticket", "choose the next support operation", "queue summary",
  "data-recovery worklist", "SLA credit", "export failed", "response package",
  even when the prompt does not name this skill. Captures the corrected SOPs,
  gating order, field definitions, charge formulas, naming conventions, and the
  specific pitfalls that produce wrong answers.
---

# CRM Support Ticket Resolution

This skill turns support-console records into the precise JSON an `answer_template.json`
demands. The work is rule-application, not free judgment: every field is decided by a
record you can read from the console, by a fixed threshold, or by a naming/formatting
convention. The mistakes that cost points are subtle (conflating two fields, guessing a
threshold, slugging a name the wrong way), so this skill front-loads the exact rules.

## 0. Universal setup (do this first, every task)

1. **Base URL override.** The prompt often says `http://127.0.0.1:8057`, but an
   `environment_access.md` (or harness note) almost always overrides it with a different
   port (seen: `8086`). Use the override. Check `/health` and `/api/catalog` first to
   confirm the API is up and see endpoint names + record counts.
2. **Read the answer_template.json literally.** It is the spec. Note every field, its
   enum set, its type (integer vs number-with-two-decimals vs boolean vs string), and any
   inline instruction like `"preserve payload order"`, `"empty string when none applies"`,
   `"order by user as listed in requirements"`. Output ONLY keys in the template, in the
   template's structure. Do not invent fields.
3. **Preserve order.** Emit array rows in the order the template says — usually the input
   payload order or ascending id order. The summary block is computed from your own rows.
4. **Resolve from records, never assumptions.** For every entity id in the payload, fetch
   its record. Resolve linked ids too (ticket→account, case→line→device→bill→plan,
   incident→enterprise account→sla→export-runs→messages).
5. **Recompute the summary from your decisions.** After filling every row, count the
   summary fields by tallying your own rows. A single wrong row silently corrupts two
   summary counts (one bucket too high, one too low) — recount, don't eyeball.

## 1. Recognize "GENERATED_NOISE" filler and ignore it

The console seeds synthetic filler so that a record EXISTS for every id, even when it is
irrelevant. Treat these as "no real signal":

- Diagnostics whose `root_causes` is `["GENERATED_NOISE"]` and troubleshooting whose
  `steps` is `["GENERATED_CHECK"]` are filler. Their metric numbers are random and
  meaningless. Do NOT compute issue flags or "fixed/not-fixed" from them.
- Bulk messages authored by `generated.user` with bodies like `"Generated support
  message 17"` are noise. The real evidence is the handful of human-authored,
  topically-specific messages.
- A ticket gated by an account state or an outage (see gating order) will usually have
  filler diagnostics — that is expected; the decision was made before any diagnostic.

When diagnostics/troubleshooting are filler, set diagnostic flags to `false`/`NONE` and
all issue flags to `false`.

## 2. The wireline ticket SOP (tasks: ticket batch, queue classification)

These tasks resolve internet/video/voice tickets into a status + route + blocker + flags.
**Apply the gates in this exact order and stop at the first that fires** — order is the
single most common source of wrong routes.

### Gating order (highest precedence first)

1. **Account does not exist** (`/api/accounts/<id>` returns `{"error":"not_found"}`, or
   the payload id is obviously malformed like `BAD-####`) →
   status `FAILED`, route `INVALID_ACCOUNT`/team `NONE`, no diagnostic.
2. **Account authentication failed** (`authentication.account_recovery_status == "FAILURE"`
   and/or `last_login_status == "FAILURE"`) →
   status `FAILED`, route `AUTH_FAILED`/team `NONE`, no diagnostic.
3. **Account suspended** (`status == "Suspended"`) →
   status `FAILED`. If the queue tracks blockers/teams, blocker `OVERDUE_SUSPENSION`
   (or `FRAUD_SUSPENSION` if the note/record says fraud) and route the remediation team
   `ACCOUNTS_PAYABLE`. No diagnostic.
   **PITFALL I hit:** a suspended account is `FAILED`, NOT `ESCALATED`, even though it is
   routed to `ACCOUNTS_PAYABLE`. `final_resolution_status` answers "can support complete
   THIS service request?" (no — the account is blocked → FAILED). `route_team` answers
   "who must act next?" (Accounts Payable). These two fields are independent; don't let a
   non-NONE route pull the status to ESCALATED.
4. **Active outage covering this service** — query
   `/api/outages?service_area=<ticket.service_area>`; an outage applies when it is
   `active == true` AND its `service_types` includes the ticket's `service_type` →
   status `PENDING_ACTION`, route `OUTAGE_WAIT`/team `NONE`, set `outage_id`, the customer
   must wait. No diagnostic needed (the blocker is the network, not the customer).
5. **Otherwise run diagnostics + troubleshooting** (account is Active, no outage):
   - Read `/api/diagnostics/<ticket_id>` (pre-fix metrics + `root_causes`) and
     `/api/troubleshooting/<ticket_id>` (the steps run + post-fix metrics).
   - If `root_causes` is filler (GENERATED_NOISE) something upstream should have gated it;
     re-check the account/outage gates.
   - Decide RESOLVED vs ESCALATED from whether troubleshooting actually fixed it (below).

### Did troubleshooting fix it? (RESOLVED vs ESCALATED)

Judge health on the **post-fix** metrics from the troubleshooting record:

- Healthy if `post_latency_ms <= 100` AND `post_jitter_ms <= 30`. Bandwidth a little under
  the subscribed rate is still acceptable (a voice line restored to 93 of 100 Mbps with
  latency 79/jitter 18 counted as RESOLVED).
- Healthy post-metrics → status `RESOLVED`, blocker `NONE`, team `NONE`, route
  `AUTO_TROUBLESHOOTING`.
- Still unhealthy post-fix (or a physical/structural root cause that an automated step
  cannot repair) → status `ESCALATED`, route `ESCALATION`, and pick the team + blocker
  from the root cause:
  - `FIBER_DROP_DAMAGE` / `SIGNAL_LOSS` / physical line fault → `FIELD_OPS`
    (blocker `PHYSICAL_LINE_FAULT`).
  - `BACKBONE_CAPACITY` / capacity / congestion → `NETWORK_ENGINEERING`
    (blocker `NETWORK_CAPACITY`).
  - `PROVISIONING_STALE` / provisioning mismatch → `TIER2_SUPPORT`
    (blocker `PROVISIONING_STALE`).

### Issue flags (`latency_issue` / `stability_issue` / `bandwidth_issue`)

These describe the customer's problem, so compute them from the **pre-fix DIAGNOSTIC**
metrics (not post-fix, not the troubleshooting record), and only for tickets that actually
ran a real diagnostic (gates 1–4 → all flags `false`, `diagnostic_needed/required` false):

- `latency_issue` = `diagnostics.latency_ms > 100`
- `stability_issue` = `diagnostics.jitter_ms > 30`
- `bandwidth_issue` = `diagnostics.bandwidth_mbps < ticket.subscribed_mbps`

`diagnostic_needed` / `diagnostic_required` is `true` only when a real diagnostic drove the
decision (gate 5 with non-filler root causes), `false` for the account/outage gates.

See `references/wireline_decision_table.md` for the full enum maps and worked rows.

## 3. The mobile case / data-recovery SOP (tasks: case queue, worklist)

For each case read `/api/cases/<id>`, then its `line_id` (`/api/lines/<id>`), `device_id`
(`/api/devices/<id>`), the customer's bill (`/api/bills`, keyed by customer_id), and the
plan (`/api/plans/<plan_id>`). The case's `issue_type`/`summary` tells you what symptom to
fix; the device/line fields tell you which single setting is wrong. Pick the one action
that addresses the broken field.

### Symptom → action map (most common)

- **NO_SERVICE + `device.sim_status == "missing"`** → `RESEAT_SIM` (self-service).
- **NO_SERVICE + line `Suspended` / `suspension_reason == "OVERDUE_BILL"`** → primary
  `SEND_PAYMENT_REQUEST`, secondary `RESUME_LINE_REBOOT`, set `bill_id`,
  `charge_amount_usd` = the overdue bill's `amount_due_usd`, route `BILLING_RECOVERY`.
- **MOBILE_DATA / no-data while roaming** — roaming has TWO layers; fix whichever is OFF:
  - device `phone_roaming_enabled == false` (line roaming already on) → `TOGGLE_ROAMING`
    (a device toggle), `carrier_update_required` false, route `SELF_SERVICE`.
  - line `roaming_enabled == false` (device roaming already on) → `ENABLE_LINE_ROAMING`
    (a carrier/line change), `carrier_update_required` true, route `CARRIER_UPDATE`.
  - **PITFALL:** do not reflexively pick the same action for every "abroad" case — read
    both flags and act on the one that is false. `TOGGLE_ROAMING` ≠ `ENABLE_LINE_ROAMING`.
- **MOBILE_DATA + `device.mobile_data_enabled == false`** → `TOGGLE_MOBILE_DATA`
  (DEVICE_SETTING_FIX). This is a device setting fix, NOT a data-recovery/refuel case.
- **MOBILE_DATA + line `data_used_gb` >= plan `data_limit_gb` (cap hit)** → `REFUEL_DATA`,
  route `DATA_RECOVERY`. See charge formula below.
- **SLOW_DATA + `device.data_saver_mode == true`** → `TOGGLE_DATA_SAVER` (DEVICE_SETTING_FIX).
- **SLOW_DATA + `device.network_mode_preference == "3g_only"`** (older mode) →
  `SET_NETWORK_MODE` (DEVICE_SETTING_FIX).
- **SLOW_DATA + `device.vpn_connected == true`** → `DISCONNECT_VPN` (SELF_SERVICE).
- **MMS / "cannot send photos" + `device.can_send_mms == false`** →
  `GRANT_MESSAGING_PERMISSION`. Set `permission` to the missing one(s) from
  `device.messaging_permissions`: photos need `storage`; texts need `sms`; both missing →
  `sms_and_storage`; otherwise `NONE`. (Photos failing usually = `storage`.)
- Nothing resolvable / explicit human need → `TRANSFER_HUMAN` / `HUMAN_TRANSFER`.

Use `secondary_action` only when a second operation is genuinely required (e.g. resume the
line AFTER payment); otherwise `NO_ACTION`.

### Charge formula and number formatting

- **Data refuel charge** = `refuel_gb * plan.data_refueling_price_per_gb`. Honor an
  explicit `customer_preferences.accepted_refuel_gb` (refuel exactly what the customer
  accepted, e.g. 2.0 GB at $2.00/GB = $4.00) rather than auto-topping to the overage.
- `data_refuel_gb`: one decimal (e.g. `2.0`), `0.0` when not applicable.
- `charge_amount_usd`: two decimals conceptually; `0.00` when no charge. (JSON `4.0` and
  `4.00` are numerically equal — emitting `4.0` is fine; do not turn a number into a
  string to force trailing zeros.)
- `total_estimated_customer_charge_usd` in the summary = sum of all per-case charges.
- `permission` enum values are lowercase: `NONE | sms | storage | sms_and_storage`.

See `references/mobile_decision_table.md` for the full device-field cheat sheet and route maps.

## 4. The enterprise export-complaint SOP (task: response package)

Trace the evidence chain: complaint email names an incident ref + client + product →
`/api/enterprise/incidents/<id>` (owners, severity, status) →
`/api/enterprise/accounts/<id>` (client name, `account_owner`, `finance_owner`) →
`/api/enterprise/sla/<ent_account_id>` (credit trigger + percent) →
`/api/enterprise/export-runs?incident_id=<id>` (the FAILED run dates + `failure_code`, and
the later SUCCEEDED backfill run) → `/api/enterprise/messages?query=<client>` (root-cause
narrative + the channel an alert was mis-routed to).

### Field rules

- `failure_window`: from the consecutive `FAILED` export-runs — `start_date` = first failed
  `run_date`, `end_date` = last failed `run_date`, `failed_days` = count of failed runs.
- `backfill_days` = number of failed days reprocessed by the SUCCEEDED backfill run
  (normally equals `failed_days`).
- `sla_credit_percent` = the SLA contract's percent for this product when the credit
  trigger is met (integer percent).
- `severity`, `engineering_owner`, `account_owner` = copy from the incident record.
- `contributing_alert_issue` = `ARCHIVED_ALERT_ROUTE` when a root-cause message shows the
  alert landed in an archived channel (e.g. channel `export-alerts-archive`); else `NONE`.
- `root_cause_category`: **a concise human-readable prose phrase, NOT the raw failure_code
  enum.** The template says "concise root-cause category inferred from ... evidence."
  **PITFALL I hit:** I returned the raw code `STALE_CREDENTIAL`; the expected value was the
  prose `stale credential after rotation` (paraphrase what the engineer's message actually
  describes). Lower-case prose, a few words, faithful to the message.

### Naming conventions — parse `naming_style` clause-by-clause, literally

`response_requirements.json` gives a terse `naming_style` like
`"lowercase hyphen channel; client-date investigation folder; client export failure report
title"`. Map each clause to its field and follow it EXACTLY. **PITFALL I hit:** I
over-engineered descriptive slugs and got every naming field wrong. The corrected
conventions:

- **`channel_name`** ("lowercase hyphen channel") = the CLIENT NAME slugified to
  lowercase-hyphen, nothing more. `Asteri Retail Inc.` → `asteri-retail-inc`. Do NOT append
  a descriptive suffix like `-export-failure`.
- **`evidence_folder`** ("client-date investigation folder") = Title-case client name +
  space + `Month YYYY` (of the failure window) + space + literal word `Investigation`:
  `Asteri Retail Inc. May 2026 Investigation`. NOT a slug, NOT an ISO date.
- **`report_title`** ("client export failure report title") = Title-case client name +
  `Export Failure - Resolution Report`: `Asteri Retail Inc. Export Failure - Resolution
  Report`.

When the convention is terse, prefer the simplest literal reading (plain client name) over
a clever descriptive string.

### share_permissions and response_status

- `share_permissions`: include exactly the users in `permission_users_to_include`, in that
  listed order. Permission level is role-based: the **finance reviewer gets `view`**
  (read-only sign-off) and the **engineering/technical reviewer gets `edit`**.
  **PITFALL I hit:** I gave both `view`; the technical reviewer should get `edit`. If a
  user's role is not stated in the data, infer it from the user list's evident pairing
  (finance owner vs the other reviewer).
- `response_status`: `NEEDS_FINANCE_REVIEW` when an SLA credit is being issued (finance
  must sign off the credit) — this beats `READY_TO_SEND` even after root cause + backfill
  are confirmed. Use `NEEDS_ENGINEERING_REVIEW` if root cause is still unconfirmed,
  `UNDER_INVESTIGATION` if the incident itself is unresolved.

See `references/enterprise_response.md` for the full evidence-chain checklist and field map.

## 5. Pre-submit checklist (catch the silent killers)

- [ ] Output contains exactly the template's keys, correct nesting, correct types.
- [ ] Array rows are in the required order; ids copied exactly (no transposition).
- [ ] Every gate/route was decided from a fetched record, with the gating order respected.
- [ ] `final_resolution_status` vs `route_team` are not conflated (suspended = FAILED + a
      route; outage = PENDING_ACTION; only technical-unfixed = ESCALATED).
- [ ] Issue flags from PRE-fix diagnostics; filler diagnostics → flags false.
- [ ] Charges computed with the right formula and decimal places; summary totals re-summed.
- [ ] Summary counts re-tallied from the final rows (each bucket sums to the row count).
- [ ] Enum values match the template's spelling/case exactly (e.g. lowercase `storage`).
- [ ] Naming fields follow `naming_style` literally; prose root-cause not raw code;
      reviewer permissions role-based.
