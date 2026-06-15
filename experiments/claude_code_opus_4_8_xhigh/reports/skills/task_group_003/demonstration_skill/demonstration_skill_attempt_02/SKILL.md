---
name: crm-support-ticket-resolution
description: >-
  Resolve CRM service-ticket / support-queue tasks against the shared read-only
  support-console API. Use this whenever a task asks you to act as a support
  operations analyst, contact-center lead, queue-quality analyst, mobile-data
  recovery analyst, or enterprise support lead and to "resolve", "classify",
  "route", "triage", or "produce a structured response/summary" for tickets,
  cases, mobile lines, or enterprise export incidents, returning JSON that
  conforms to a provided answer_template.json. Trigger it for any payload of
  service tickets, a case/queue snapshot (CSV or JSON), a mobile worklist, or an
  enterprise complaint email, even if the prompt does not name this skill — the
  decisions must come from support-console records, never from assumptions.
---

# CRM Support-Ticket Resolution

You are resolving a batch of CRM support work by looking up authoritative
records in a shared, read-only support console and applying fixed business
conventions. The prompt gives you a payload (tickets, cases, a queue snapshot, a
mobile worklist, or an enterprise complaint) plus an `answer_template.json`.
Your job is to produce JSON that conforms exactly to that template, where every
field is justified by console records — not by the free-text customer report.

## Golden rules (apply to every task family)

1. **Records over reports.** The customer's words (CSV `customer_report`/
   `queue_note`, case `summary`, complaint email) only tell you where to look.
   The decision is driven by the structured record (account status, line/device
   flags, diagnostics, outages, export runs). When the report and the record
   disagree, trust the record.

2. **The answer_template is the contract.** Read it first. Use only the enum
   values it lists, the exact field names, and the stated ordering ("preserve
   payload order", "ascending case_id", "order as listed in requirements").
   Different tasks in this family expose slightly different enum sets — always
   map your conclusion to the closest value the *current* template offers, and
   never invent an enum the template does not contain.

3. **Gates short-circuit; later evidence is a distractor.** Eligibility/outage
   gates are evaluated in a strict order (see below). Once a gate fires, you
   stop — you do NOT run diagnostics, you do NOT set diagnostic flags, you do
   NOT escalate by root cause. The console will still happily return a
   diagnostics record for a suspended or invalid account; that record is a trap.
   If a gate fired, diagnostic-related booleans are `false` and any
   escalation/route reflects the gate, not the metrics.

4. **Output only the JSON.** No prose, no markdown fences, no commentary.
   Numbers must match the template's stated precision (e.g. "two decimals").

## Environment usage

- Base URL is **`http://127.0.0.1:8086`** for ALL lookups. It overrides any
  other base URL written in the prompt (prompts often say `8057` — ignore that).
- Read-only GET + JSON. Start with `GET /api/catalog` if unsure which endpoints
  exist; `GET /api/search?q=<text>` does a full-text search across every
  collection and is the fastest way to correlate scattered evidence (e.g. find
  the bill, line, case, and ticket that all mention one customer).
- Key endpoints: `/api/accounts/<id>`, `/api/tickets/<id>`,
  `/api/diagnostics/<ticket_id>`, `/api/troubleshooting/<ticket_id>`,
  `/api/outages?service_area=<area>`, `/api/cases/<id>`, `/api/lines/<id>`,
  `/api/devices/<id>`, `/api/bills`, `/api/plans/<id>`,
  `/api/enterprise/incidents/<id>`, `/api/enterprise/accounts/<id>`,
  `/api/enterprise/sla/<enterprise_account_id>`,
  `/api/enterprise/export-runs?incident_id=<id>`,
  `/api/enterprise/messages?query=<text>`.
- A lookup that returns `{"error": "not_found"}` is meaningful: it usually means
  an invalid/unknown account or record and is itself the answer (see gates).

## Choose the task family, then read its reference

Identify the family from the payload shape and the answer_template fields, then
read the matching reference file before deciding anything:

| Signal in payload / template | Family | Reference |
|---|---|---|
| Tickets with `final_resolution_status`, `resolution_route`, diagnostic booleans, outage_id | Connectivity ticket resolution | `references/connectivity_tickets.md` |
| Tickets with `key_blocker`, `route_team`, `diagnostic_required` (queue classify) | Queue triage / classification | `references/connectivity_tickets.md` |
| Cases/worklist with `primary_action`/`secondary_action`, line+device+bill | Mobile case actions | `references/mobile_cases.md` |
| Complaint email + enterprise incident, `sla_credit_percent`, `failure_window`, evidence/report/channel | Enterprise export response | `references/enterprise_response.md` |

The two ticket families share the same gating engine and diagnostic
conventions; they differ only in which enums the template exposes.

## Universal SOP

1. Read the prompt, the payload, and **the answer_template**. Note the exact
   output keys, enum sets, precision, and ordering for THIS task.
2. Identify the family and read its reference file.
3. For each work item, in payload order (or the ordering the template demands):
   look up the authoritative records, apply that family's decision procedure
   (gates first), and fill every output field from records.
4. Compute the summary/rollup section by tallying your per-item decisions. The
   summary must be internally consistent with the rows — recount, don't guess.
5. Emit JSON conforming exactly to the template. Validate field names, enum
   spellings, ordering, and numeric precision before returning.

## Common misjudgments to avoid

- **Trusting the customer narrative over the record.** "Cannot connect after an
  account hold" is not what makes a ticket FAIL — the account `status` being
  Suspended is.
- **Running diagnostics on a gated item.** If the account is invalid, auth has
  failed, the account is suspended, or there is a covering active outage, the
  diagnostics/troubleshooting records are irrelevant; do not let their numbers
  flip your flags or your route.
- **Reading post-troubleshooting metrics as "fixed".** A ticket is only RESOLVED
  if the *post* metrics clear every threshold. Marginal residuals (e.g. latency
  still just above the limit, bandwidth still below the floor) mean ESCALATE.
- **Escalating without checking the root cause family.** The escalation team /
  route is chosen from the diagnostic `root_causes`, not from the customer text.
- **Inventing enum values or owners.** Owners, percentages, windows, and
  categories all come from records (incident, SLA contract, export runs,
  messages). If the template lists an enum, your value must be one of them.
- **Miscounting the summary.** Recompute every rollup from your own rows.
