---
name: crm-support-ticket-resolution
description: >-
  Resolve CRM support-console tasks against the shared read-only support API and
  emit JSON that conforms to the task's answer_template.json. Use this skill
  whenever a task asks you to act as a support analyst / contact-center lead /
  queue-quality analyst / enterprise support lead and to classify, route, or
  decide outcomes for service tickets, mobile cases, mobile-data worklists, or
  enterprise export incidents from support-console records. Triggers include:
  resolving a batch of offline/service tickets, choosing the next support
  operation for mobile/line cases, classifying a queue before SLA handoff,
  computing data-refuel charges, or preparing an enterprise export-complaint
  response package (root cause, failure window, SLA credit, owners, channel,
  evidence folder, report title, share permissions). Apply it even when the
  prompt does not name "support console" explicitly but references tickets,
  accounts, outages, diagnostics, lines, devices, plans, bills, cases, or
  enterprise incidents/export-runs and wants a structured decision.
---

# CRM Support-Console Ticket Resolution

You resolve support-console tasks by reading live records from a shared,
read-only HTTP API and producing JSON that exactly matches the task's
`answer_template.json`. Every decision must be backed by a record you actually
fetched — never assume a value, and never carry over an answer from a previous
task. The data changes per task; the **rules** below are what transfer.

## 0. Orient before you act

1. Read `prompt.txt` and every file under `payloads/`. The `answer_template.json`
   is the contract: it tells you the exact output keys, enum values, ordering
   rule, and number formatting. Mirror it precisely.
2. Confirm the API base URL. The harness may override the prompt's URL via an
   `environment_access.md` file or instructions; **that override wins**. Train
   prompts said `8057` but the real base was `http://127.0.0.1:8086`. If unsure,
   `curl <base>/health` and `curl <base>/api/catalog` to confirm it is live and
   to see available endpoints/record counts.
3. Identify which **task family** you are in (the answer_template shape is the
   tell), then open the matching reference file and follow its SOP:

   | If the output has keys like…                                              | Family | Reference |
   |---------------------------------------------------------------------------|--------|-----------|
   | `ticket_decisions[]` with `latency_issue/stability_issue/bandwidth_issue`, `resolution_route`, `batch_summary` | Internet/service ticket batch | `references/ticket_resolution.md` |
   | `ticket_decisions[]` with `key_blocker`, `route_team`, `queue_summary`    | Queue classification before SLA handoff | `references/ticket_resolution.md` |
   | `case_decisions[]` with `primary_action`, `permission`, `bill_id`, `final_route` | Mobile contact-center cases | `references/mobile_cases.md` |
   | `case_decisions[]` with `data_refuel_gb`, `carrier_update_required`, `worklist_summary` | Mobile-data recovery worklist | `references/mobile_cases.md` |
   | `incident_id`, `failure_window`, `sla_credit_percent`, `share_permissions` | Enterprise export incident response | `references/enterprise_incident.md` |

## 1. Universal working rules

- **Read-only, GET only.** Endpoints (relative to base): `/api/accounts/<id>`,
  `/api/tickets/<id>`, `/api/outages?service_area=<area>`,
  `/api/diagnostics/<ticket_id>`, `/api/troubleshooting/<ticket_id>`,
  `/api/cases/<id>`, `/api/lines/<id>`, `/api/devices/<id>`, `/api/plans/<id>`,
  `/api/bills`, `/api/customers?customer_id=<id>`,
  `/api/enterprise/accounts/<id>`, `/api/enterprise/incidents/<id>`,
  `/api/enterprise/export-runs?incident_id=<id>`,
  `/api/enterprise/sla/<enterprise_account_id>`,
  `/api/enterprise/messages?query=<text>`, `/api/search?q=<text>`.
- **Resolve every item from records, in payload order.** Preserve the order the
  answer_template specifies (usually "payload order" or "ascending id").
- **A missing record is signal, not an error.** `{"error":"not_found"}` for an
  account usually means INVALID_ACCOUNT, not "skip it". Distinguish a 404 from a
  record whose field merely has an empty/falsey value.
- **Gates run before diagnostics.** In every family there is an ordered set of
  hard gates (invalid account, auth failure, suspension, active outage). The
  FIRST gate that fires decides the outcome, and you must NOT run/report the
  later diagnostic steps for that item — set the diagnostic booleans to
  `false`/`NONE` because no diagnostic was actually performed. This is the most
  common source of error: do not "helpfully" fill in diagnostic flags for a
  ticket that was short-circuited by an outage or a suspension.
- **Match the answer_template's number formatting** (e.g., charges to two
  decimals, refuel GB to one decimal) and its enum spellings exactly. An enum
  value that is not in the template's list is always wrong.
- **Compute every summary by counting your own per-item decisions.** Summaries
  are derived, never independent — they must be internally consistent with the
  array above them (e.g., the four status counts sum to the number of items;
  `total_estimated_customer_charge_usd` equals the sum of the per-case charges).

## 2. Evidence discipline (why this matters)

The records are designed so the "obvious" reading of the customer complaint is
sometimes contradicted by the data — e.g., a phone reports "roaming on" but the
*line* has roaming disabled, or a complaint says "three days" but the export
runs show four failures. Always let the **record values** win over the prose,
and confirm the exact field the rule keys on (status, reason code, failure
code, channel name) rather than pattern-matching on the human summary. A useful
habit: for each item, write down the one or two field values that determined
the decision, so the routing is traceable and you catch yourself when a value
disagrees with the narrative.

## 3. Output

Return **only** the JSON object, conforming key-for-key to
`answer_template.json` (no commentary, no extra keys, no markdown fences unless
the harness asks). Re-read the template once more before emitting to confirm
key names, enum casing, ordering, array lengths, and numeric formats. Then
verify the summary counts against your per-item decisions.

The per-family reference files contain the concrete enums, thresholds,
formulas, routing tables, and worked reasoning patterns. Read the one that
matches your task before deciding anything.
