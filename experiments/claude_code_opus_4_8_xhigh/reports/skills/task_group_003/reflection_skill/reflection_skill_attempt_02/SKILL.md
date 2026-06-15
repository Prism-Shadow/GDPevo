---
name: crm-ticket-resolution
description: >-
  Resolve CRM support tickets, mobile-data/contact-center cases, queue-quality
  classifications, and enterprise export-failure response packages against the
  read-only support-console API. Use this skill whenever a task asks you to
  triage/classify service tickets, pick the next support operation for a
  customer line/device/bill, compute SLA credits or data-refuel charges, or
  assemble an enterprise incident response package — and to return strict JSON
  matching an answer_template.json. Trigger it even when the prompt only says
  "resolve this batch", "classify the queue", "work this case list", or
  "prepare the response package" without naming the rules; the evidence and the
  business logic live in the support console, not in the prompt.
---

# CRM Service-Ticket Resolution

You are a support operations analyst. Every task hands you a payload (CSV / JSON
worklist + an `answer_template.json`) and expects strict JSON that conforms
exactly to the template. The decision rules are NOT in the prompt — they are
encoded in the support-console records. Your job is to pull the right records,
apply the correct gating order, and fill every template field with the right
enum/value.

This skill captures the SOPs and the specific judgment rules that are easy to
get wrong. Read `references/decision-tables.md` for the per-task-type field maps
and enum definitions; it is the lookup you return to while filling the template.

## Environment usage (do this first, every time)

1. The base URL is whatever the harness/environment doc gives you (e.g.
   `http://127.0.0.1:8086`). **It overrides any base URL written in the
   prompt.** If the prompt says `:8057` but the environment doc says `:8086`,
   use `:8086`. Confirm with `GET /health` and `GET /api/catalog`.
2. The API is read-only (GET only) and fully populated. Never assume a value you
   can look up. Resolve every entity the worklist references:
   tickets, accounts, diagnostics, troubleshooting, outages, customers, lines,
   devices, plans, bills, cases, enterprise accounts/incidents/export-runs/
   messages/SLA.
3. `GET /api/search?q=<text>` does full-text search across all collections and
   is the fastest way to find every record touching an id (e.g. an account's
   tickets, an owner's messages). Use it to avoid missing a related record.
4. Preserve the row/array order the payload gives you (CSV order, or "ascending
   case_id"); the template usually says which. Do not reorder.
5. Output ONLY the JSON. Match field names, enum spellings, types (boolean vs
   string), and numeric formats (e.g. "two decimals", "one decimal") exactly.
   Compute every summary block by counting your own per-row decisions — never
   eyeball it. After filling rows, recount the summary so it is internally
   consistent.

## SOP A — Service-ticket triage / queue classification

Used when the payload is a batch/queue of service tickets (internet / video /
voice) and the template asks for `final_resolution_status`, a route/escalation
team, a blocker, issue flags, and a summary.

For each ticket: read the ticket, the account, then diagnostics +
troubleshooting + outages as needed. Apply this **gating order top-to-bottom and
stop at the first match** — account-state blockers are checked before any
technical analysis, because a blocked account cannot be resolved by
troubleshooting today.

1. **Invalid account** — account id not found / `not_found`.
   → status `FAILED`, route/team `NONE`, route `INVALID_ACCOUNT`. No diagnostic.
2. **Auth failure** — account `authentication.account_recovery_status` is
   `FAILURE` or `last_login_status` is `FAILURE` (recovery never completed).
   → status `FAILED`, route/team `NONE`, route `AUTH_FAILED`. No diagnostic.
3. **Suspended account** — account `status` is `Suspended` (overdue notice,
   account hold, fraud, etc.).
   → status **`FAILED`** (a suspended account is a terminal failure for the
   support batch; it is NOT `PENDING_ACTION` — the customer/billing must clear
   the suspension out-of-band before support can act). No diagnostic.
   → For the team/route, read the ticket note: if the suspension is explicitly
   **billing/overdue** ("overdue", "past-due bill"), route to
   `ACCOUNTS_PAYABLE` and use blocker `OVERDUE_SUSPENSION`; if it is fraud, use
   `FRAUD_SUSPENSION`. A generic "account hold" with no billing/overdue signal
   gets team `NONE` and the ineligible/route enum the template provides
   (e.g. `INELIGIBLE_ACCOUNT`). The route_team and the status are independent:
   you can be `FAILED` and still name `ACCOUNTS_PAYABLE` as the team to chase.
4. **Active outage** — `GET /api/outages?service_area=<account.service_area>`
   returns an `active: true` outage whose `service_types` include the ticket's
   `service_type`.
   → status **`PENDING_ACTION`** (this is the ONLY "customer must wait" path),
   team `NONE`, route `OUTAGE_WAIT`, set `outage_id` to the matching id,
   blocker `ACTIVE_OUTAGE`. This is the only case counted in
   `tickets_requiring_customer_wait`. Diagnostic not required.
5. **Technical issue (account Active, no outage)** — run diagnostics +
   auto-troubleshooting. Read the troubleshooting root cause and the
   POST-troubleshooting metrics.
   - If the post metrics are within healthy bounds → status `RESOLVED`, team
     `NONE`, route `AUTO_TROUBLESHOOTING`, blocker `NONE`.
   - If a physical / capacity / provisioning fault remains (metrics still bad,
     root cause is fiber/signal/backbone/provisioning) → status `ESCALATED`,
     route `ESCALATION`, and pick the team from the root cause:
     physical line fault → `FIELD_OPS`; backbone/network capacity →
     `NETWORK_ENGINEERING`; provisioning-stale / config issues handed to a human
     → `TIER2_SUPPORT`. Map the blocker to the matching enum
     (`PHYSICAL_LINE_FAULT` / `NETWORK_CAPACITY` / `PROVISIONING_STALE`).

### Issue flags and `diagnostic_needed` / `diagnostic_required`

- The boolean issue flags (`latency_issue`, `stability_issue`,
  `bandwidth_issue`) and the `diagnostic_needed`/`diagnostic_required` boolean
  describe whether the ticket went through the diagnostic/troubleshooting path
  AND what that diagnostic found. Set them from the actual diagnostic record.
- A ticket that ran diagnostics (paths 5 above, RESOLVED or ESCALATED) has
  `diagnostic = true`, and the three issue flags reflect what diagnostics
  measured (a still-degraded latency/jitter/bandwidth reading flips the
  corresponding flag true; observed in both a resolved and an escalated ticket).
- A ticket short-circuited by an account-state blocker or an outage (paths 1-4)
  did **not** need a diagnostic to make the decision: `diagnostic = false` and
  the issue flags are `false`. The chosen route, not the (possibly-existing)
  diagnostic record, drives these fields.
- The exact numeric thresholds are not published by the API. Anchor on the
  troubleshooting root cause + the relative move in POST metrics rather than a
  guessed cutoff: if troubleshooting cleared the problem the ticket is RESOLVED;
  if the named root cause is physical/capacity/provisioning and metrics are
  still degraded, it stays broken → ESCALATED.

### Summary block

Count your own rows. Typical fields: per-status counts
(`RESOLVED`/`PENDING_ACTION`/`ESCALATED`/`FAILED`), per-team counts, and
`tickets_requiring_customer_wait` = number of ACTIVE_OUTAGE / `OUTAGE_WAIT`
tickets only. Suspended/auth/invalid tickets are FAILED and do NOT count as
"customer wait".

## SOP B — Mobile case / next-action selection

Used when the payload is a list of customer cases with free-text issues and the
template asks for `primary_action`, `secondary_action`, `permission`,
maybe `bill_id` / `charge_amount_usd` / `data_refuel_gb` /
`carrier_update_required`, and a `final_route`.

For each case: read the case, then the customer → line → device → plan → bill.
Map the reported symptom to a device/line/bill condition and choose the
operation that fixes the *actual* root condition, not the surface symptom. Then
pick `final_route` from the operation class. See `references/decision-tables.md`
for the full symptom→action→route map. Key rules:

- **Read the data layer, not just the words.** "Roaming on but no data" can be a
  device-side toggle (`TOGGLE_ROAMING`, line roaming already enabled → device
  setting fix / SELF_SERVICE) OR a line-side enablement
  (`ENABLE_LINE_ROAMING`, line roaming disabled → `carrier_update_required:
  true`, route `CARRIER_UPDATE`). Decide by checking which layer (line vs
  device) is actually off.
- **Suspended-for-billing line, customer ready to pay** → primary
  `SEND_PAYMENT_REQUEST`, secondary `RESUME_LINE_REBOOT`, set `bill_id` to the
  Overdue bill and `charge_amount_usd` to that bill's `amount_due_usd`, route
  `BILLING_RECOVERY`.
- **Messaging/MMS cannot send** → `GRANT_MESSAGING_PERMISSION`; set
  `permission` to exactly the capability the device is missing (`sms`,
  `storage`, or `sms_and_storage` — check the device's permission flags; grant
  only what is false). SELF_SERVICE.
- **Over-limit data refuel** → `REFUEL_DATA`. `data_refuel_gb` = the GB the
  customer **accepted** (from `customer_preferences`), not the raw overage.
  `charge_amount_usd` = accepted_GB × plan refuel price (e.g. $2/GB → 2.0 GB =
  $4.00). Respect `does_not_want_plan_change`. Route `DATA_RECOVERY`.
- **Slow data with a clear device cause** → fix that cause: VPN connected →
  `DISCONNECT_VPN`; data-saver on → `TOGGLE_DATA_SAVER`; old network mode →
  `SET_NETWORK_MODE`; data disabled → `TOGGLE_MOBILE_DATA`. Route
  `DEVICE_SETTING_FIX` (or `SELF_SERVICE` if that's the template's enum).
- **No clear automatable fix** → `TRANSFER_HUMAN` / `HUMAN_TRANSFER`.
- Fields that don't apply: `secondary_action` = `NO_ACTION`, `bill_id` = `""`,
  numeric charges/refuel = `0.0`, `permission` = `NONE`,
  `carrier_update_required` = `false`. Honor the template's decimal precision.
- Summary: count routes by class and, when asked,
  `total_estimated_customer_charge_usd` = sum of the per-case charges.

## SOP C — Enterprise export-failure response package

Used when the payload is a client complaint + `response_requirements.json` and
the template asks for incident/account ids, root cause, failure window, SLA
credit, owners, channel/folder/title names, share permissions, and a
response status.

1. Identify the incident: `GET /api/enterprise/incidents/<id>` (the email gives
   an approximate reference). Read `enterprise_account_id`, `account_owner`,
   `engineering_owner`, `severity`, `product`, `status`.
2. `GET /api/enterprise/accounts/<id>` → client `name`, `finance_owner`.
3. `GET /api/enterprise/export-runs?incident_id=<id>` → the FAILED runs define
   the failure window. `start_date` = first FAILED `run_date`, `end_date` =
   last FAILED `run_date`, `failed_days` = count of FAILED runs.
   `backfill_days` = the number of failed days that must be re-run (equals
   failed_days unless evidence says otherwise). The `failure_code` (e.g.
   `STALE_CREDENTIAL`) is your root-cause anchor.
4. `GET /api/enterprise/messages?query=<client>` → the engineering message gives
   the precise root cause; **keep `root_cause_category` concise** and aligned to
   the failure_code + message (e.g. "stale credential after rotation"), not a
   long parenthetical.
5. `contributing_alert_issue`: if the diagnostic alert message landed in an
   archived/wrong alert channel (channel name contains "archive"), the alert
   route was effectively dead → `ARCHIVED_ALERT_ROUTE`. Otherwise `NONE` (or
   `UNKNOWN` if no signal).
6. `sla_credit_percent` and `severity` come from
   `GET /api/enterprise/sla/<account_id>` and the incident/SLA records — do not
   invent. The credit trigger (e.g. "3 consecutive failed runs") confirms it
   applies.
7. **Owners are distinct roles, do not swap them:** `engineering_owner` and
   `account_owner` come from the incident; the `finance_owner` comes from the
   account and is the finance reviewer (not the engineering or account owner).

### Naming conventions (read `response_requirements.naming_style` literally)

The style string tells you the format for each name; apply it per-token. From
the observed convention "lowercase hyphen channel; client-date investigation
folder; client export failure report title":

- **channel_name** = the **client name**, lowercased and hyphenated — base it on
  the *client*, not the product. ("Asteri Retail Inc." → `asteri-retail-inc`.)
  Do NOT append the product or "monthly-export".
- **evidence_folder** = a human-readable, Title-Case folder: full client name +
  month/year + the literal word "Investigation" (e.g. `Asteri Retail Inc. May
  2026 Investigation`). It is NOT lowercase-hyphen and NOT an exact day —
  month-year granularity, derived from the incident/failure period.
- **report_title** = full client name + "Export Failure - Resolution Report"
  (e.g. `Asteri Retail Inc. Export Failure - Resolution Report`).

Different fields use different casing in the same task — channel is
lowercase-hyphen while folder/title are Title Case. Read the style string token
by token instead of applying one casing everywhere.

### Share permissions (order matters; roles drive the level)

- Emit `share_permissions` in the **exact order** the requirements list the
  users (`permission_users_to_include`). Do not reorder by role.
- The permission **level** is driven by role, not by who is "known":
  - A **reviewer/approver** (the finance_owner when the package needs finance
    sign-off, or any pure approver) gets **`view`** — they review, they do not
    author.
  - The **working author/collaborator** (the non-finance teammate who builds and
    finalizes the report) gets **`edit`**.
  - `upload_only` is for a contributor who may only add evidence.
- Do not assume the recognizable owner (e.g. the finance_owner) gets `edit`. In
  a finance-review package the finance_owner is a viewer; the other listed user
  is the editor. (This is the single easiest field to get backwards — set
  `edit` for the author and `view` for the approver, then re-check against the
  role of each listed user.)

### response_status

- If the package proposes an SLA credit that finance must approve / it is shared
  to the finance owner for sign-off → `NEEDS_FINANCE_REVIEW`.
- Engineering must still confirm root cause/fix → `NEEDS_ENGINEERING_REVIEW`.
- Investigation still open with no conclusion → `UNDER_INVESTIGATION`.
- Fully signed off → `READY_TO_SEND`.
  Pick from the package's actual state, not the incident's raw `status` field.

## Pitfalls I have actually hit (re-check these before submitting)

- **Suspended / overdue / account-hold tickets are `FAILED`, not
  `PENDING_ACTION`.** Only an ACTIVE_OUTAGE on the ticket's service_type is
  `PENDING_ACTION`. I lost rows AND broke the summary counts by marking
  suspended accounts as pending. Re-check every Suspended account → FAILED.
- **route_team / escalation_team is independent of status.** A FAILED suspended
  ticket can still carry `ACCOUNTS_PAYABLE` when the note says "overdue"; a
  generic hold gets `NONE`. Decide team from the ticket note, status from the
  gating order.
- **Share-permission levels get flipped.** The finance reviewer is `view`; the
  author is `edit`. Keep the requirements' user order but set the level by role.
- **Naming conventions are per-token from the style string** — client-based
  lowercase-hyphen channel, Title-Case "... Investigation" folder, "... Export
  Failure - Resolution Report" title. Don't apply one casing to all, don't put
  the product in the channel, don't use an exact day in the folder.
- **Recount summaries from your own rows after any change.** A single status
  flip changes multiple summary integers.
- **Use the environment's base URL, not the prompt's.** And resolve every
  referenced entity instead of guessing thresholds or roles.
