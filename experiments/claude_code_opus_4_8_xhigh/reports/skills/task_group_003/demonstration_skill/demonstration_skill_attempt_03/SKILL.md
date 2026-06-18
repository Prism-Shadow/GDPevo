---
name: crm-support-ticket-resolution
description: >-
  Resolve CRM support-console tasks by reading the shared read-only support
  console API and emitting the exact JSON the answer_template demands. Use this
  whenever a task asks you to triage/resolve a batch of service tickets, classify
  a ticket queue with key blockers, decide the next support operation for a mobile
  case queue or mobile-data worklist, or assemble an enterprise complaint /
  export-failure response package. Trigger on prompts mentioning "support console",
  "ticket batch", "case queue", "worklist", "resolve from the records", outage /
  diagnostic / troubleshooting gating, escalation teams, SLA credit, export runs,
  refuel/charge math, or any answer_template.json with ticket_decisions /
  case_decisions / queue_summary / incident response fields. The data lives in the
  console, never in assumptions — always look up the backing records.
---

# CRM Support-Console Ticket Resolution

You resolve same-day support work by reading records from a shared, read-only
support-console HTTP API and producing JSON that exactly matches the task's
`answer_template.json`. Every decision must be **evidence-backed** from console
records — never inferred from the customer's wording alone.

There are four recurring task families. Identify which one you have from the
answer template fields, then follow the matching SOP below. The detailed
decision tables for each family live in `references/`.

## Step 0 — Universal setup (do this every time)

1. **Read the inputs.** Open `prompt.txt` and every file under `payloads/`.
   The `answer_template.json` defines the EXACT output shape, field names, enum
   values, ordering rule, and number formatting. Treat it as the contract: emit
   only those keys, only those enum spellings, and respect its stated ordering
   ("preserve payload order" vs "ascending case_id order").
2. **Fix the base URL.** Prompts often say `http://127.0.0.1:8057`. The harness
   overrides this — use the base URL from `environment_access.md` (currently
   `http://127.0.0.1:8086`). If a different base URL is provided by the harness,
   that wins over anything in the prompt.
3. **Pull the backing record for every input row.** For each ticket/case/incident,
   GET its record plus all dependent records (account, outage, diagnostics,
   troubleshooting, line, device, bill, plan, SLA, export-runs, messages) BEFORE
   deciding. Use `curl -s <base>/api/...`. Endpoints are listed in
   `environment_access.md` and `/api/catalog`. `/api/search?q=` and
   `/api/enterprise/messages?query=` do full-text lookups when an ID is unknown.
4. **Output only JSON.** Return exactly one JSON object conforming to the template.
   No prose, no markdown fences. Numbers: honor "two decimals" / "one decimal"
   as the template states (e.g. `4.0`, `86.40`). Empty-when-not-applicable string
   fields are the literal empty string `""`, never null.
5. **Compute summaries by counting your own decisions.** Every family ends with a
   summary block whose counters must be derived by tallying the decision rows you
   just produced — recount, do not estimate. Verify each counter sums correctly.

## Identify the task family

| Signal in answer_template | Family | SOP |
|---|---|---|
| `ticket_decisions[]` with `final_resolution_status`, `resolution_route`, `latency_issue`/`stability_issue`/`bandwidth_issue`, `escalation_team` | **A. Ticket batch resolution** | below + `references/connectivity.md` |
| `ticket_decisions[]` with `key_blocker`, `route_team`, `diagnostic_required` | **B. Queue classification** | below + `references/connectivity.md` |
| `case_decisions[]` with `primary_action`, `permission`, `bill_id`, `final_route` (SELF_SERVICE/BILLING_RECOVERY/...) | **C. Mobile case queue** | `references/mobile.md` |
| `case_decisions[]` with `data_refuel_gb`, `carrier_update_required`, `final_route` (DATA_RECOVERY/...) | **D. Mobile-data worklist** | `references/mobile.md` |
| `incident_id`, `failure_window`, `sla_credit_percent`, `share_permissions`, `evidence_folder` | **E. Enterprise response package** | `references/enterprise.md` |

Families A and B are both connectivity-ticket triage and share the same gating
order and diagnostic thresholds — read `references/connectivity.md` for both.
They differ only in output fields and which enum names are used.

## The gating principle (connectivity families A & B)

The single most important rule: **gates are evaluated in a fixed order, and the
FIRST gate that fires decides the outcome.** Diagnostics/troubleshooting are only
consulted if every gate passes. Running diagnostics on a ticket that should have
been stopped by an earlier gate is the most common error.

Order (stop at the first match):

1. **Account validity** — account id not found in `/api/accounts` →
   FAILED, blocker INVALID_ACCOUNT (route INVALID_ACCOUNT). No diagnostics.
2. **Authentication** — account exists but auth is broken
   (`authentication.last_login_status == "FAILURE"` or
   `account_recovery_status == "FAILURE"`) → FAILED, AUTH_FAILED. No diagnostics.
3. **Account standing** — `status != "Active"` (e.g. "Suspended") →
   FAILED. The suspension *sub-reason* is read from the ticket/queue note text:
   "overdue" → OVERDUE_SUSPENSION routed to ACCOUNTS_PAYABLE; "fraud" →
   FRAUD_SUSPENSION. (Family A calls this INELIGIBLE_ACCOUNT, team NONE.)
   No diagnostics.
4. **Active outage** — an entry from `/api/outages?service_area=<area>` is
   `active: true` AND lists the ticket's `service_type` in `service_types` →
   PENDING_ACTION, blocker ACTIVE_OUTAGE, route OUTAGE_WAIT, `outage_id` set.
   This ticket "requires customer wait." No diagnostics (the network is the cause).
5. **Diagnostics & troubleshooting** — only now run the metric logic in
   `references/connectivity.md` to decide RESOLVED vs ESCALATED and the
   issue flags / escalation team.

Full enum mappings, thresholds, and the escalation-team routing table are in
`references/connectivity.md`.

## Mobile families (C & D)

For each case, the next operation is chosen from the device/line/bill records by
matching the case `issue_type` and the offending field. The two families share an
action vocabulary but differ in a subtle, important way around roaming and in
their output fields and routes. The complete decision tables, the
roaming distinction, the charge/refuel math, and the route mapping are in
`references/mobile.md`. Read it whenever the template has `primary_action`.

## Enterprise family (E)

Assemble an incident-response package by joining the incident, enterprise account,
SLA contract, export-runs, and messages. The failure window comes from consecutive
FAILED export runs; the SLA credit comes from the contract; owners come from the
incident; channel/folder/title follow naming conventions; share permissions follow
the requirements payload. Full field-by-field derivation is in
`references/enterprise.md`.

## Common misjudgments to avoid

- **Skipping a gate.** A suspended or auth-failed account never gets diagnostics,
  even if diagnostics records exist in the console. The gate order is absolute.
- **Reading metrics from the wrong record.** The issue flags
  (latency/stability/bandwidth) come from the *pre-fix* `/api/diagnostics/<id>`.
  Whether the ticket RESOLVED or ESCALATED is judged on the *post-fix*
  `/api/troubleshooting/<id>` numbers. Don't mix them up.
- **Trusting the customer's words over the records.** "Whole office outage" only
  becomes OUTAGE_WAIT if `/api/outages` actually shows an active matching outage.
  Otherwise it's a normal diagnostic case.
- **Honoring the prompt's stale base URL.** Always use the environment_access URL.
- **Order/format drift.** Preserve the template's row order, enum spellings, and
  decimal formatting. A correct decision in the wrong enum string still fails.
- **Hand-waving the summary.** Recount decisions; don't approximate.
- **Inventing values not present in records or requirements** (e.g. a user who
  isn't in the console — pull such users only from the requirements payload).
