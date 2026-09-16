---
name: support-console-operator
description: "Resolve telecom support tickets, contact-center cases, enterprise incidents, and mobile-data issues using a shared REST support-console API. Use when the task involves: (1) a batch of offline service tickets needing classification and routing, (2) a contact-center queue of mobile cases requiring self-service or billing actions, (3) an enterprise client export-complaint investigation with SLA and evidence handling, (4) a queue-quality review of tickets before SLA handoff, or (5) a mobile-data recovery worklist with refuel or carrier-update operations. Trigger on prompts mentioning support tickets, case queues, incident investigations, SLA reviews, or mobile-data recovery with a shared API endpoint."
license: MIT
compatibility: designed for deepagents-code
---

# Support Console Operator

Resolve telecom support worklists by querying the support-console REST API and
producing structured JSON decisions. This skill covers ticket classification,
contact-center case handling, enterprise incident investigation, queue-quality
review, and mobile-data recovery.

## Core Workflow

Every task follows the same three-phase pattern:

1. **Parse input** -- Read the payload file(s) provided in the prompt. Payloads
   are CSV (ticket batches, queue snapshots) or JSON (case queues, worklists,
   response requirements, customer preferences). Also read the answer template
   JSON to know the exact output schema.

2. **Query the API** -- For every record in the payload, fetch relevant records
   from the support-console API. Cross-reference multiple endpoints to build a
   complete picture: tickets + diagnostics + outages, cases + customers + lines
   + bills + plans + devices, incidents + export-runs + messages + SLA + accounts.
   See [api_endpoints.md](references/api_endpoints.md) for every endpoint.

3. **Apply decision rules and emit JSON** -- Classify each record using the
   domain rules in [decision_rules.md](references/decision_rules.md). Fill the
   answer template exactly, preserving payload record order. Compute summary
   counts from the decisions. Output only valid JSON conforming to the template;
   do not wrap in markdown fences or add commentary.

## Environment

The prompt provides a placeholder `<TASK_ENV_BASE_URL>`. Replace it with the
actual base URL from the environment (typically `http://task-env:9003`). No
credentials are needed. All endpoints are GET-only.

## Task Types

The skill handles five task types, each with its own answer template and
decision surface. Read the payload carefully to determine which type applies,
then follow the matching rules in the decision-rules reference.

| Task | Typical payload | Key endpoints to query |
|------|----------------|----------------------|
| Ticket batch | `ticket_batch.csv` | tickets, diagnostics, troubleshooting, outages, customers, accounts, lines |
| Contact-center queue | `case_queue.json` | cases, customers, lines, bills, plans, devices |
| Enterprise investigation | `client_complaint_email.txt` + `response_requirements.json` | incidents, export-runs, messages, accounts, SLA |
| Queue-quality review | `queue_snapshot.csv` | tickets, diagnostics, outages, accounts, customers, lines |
| Mobile-data recovery | `mobile_data_worklist.json` | lines, customers, bills, plans, devices |

## Answer Templates

Every answer template is a JSON schema provided in the task payloads. Read it
before starting work. Templates define:

- Per-record decision fields (resolution status, actions, routes, blockers)
- Enumerated values for each field (see decision rules for when to use each)
- Summary aggregation fields (counts, totals)

Always preserve the order of records from the input payload in the output.

## API Query Strategy

- Query one record at a time per endpoint. Use the id-specific endpoints
  (`/api/tickets/{ticket_id}`, `/api/customers/{customer_id}`, etc.) for
  individual lookups after scanning list endpoints for matching ids.
- For tickets: start with `/api/tickets/{ticket_id}`, then cross-reference
  diagnostics, outages, and the account.
- For cases: start with `/api/customers/{customer_id}` (derive from case_id
  numbering), then fetch lines, bills, plans, and devices for that customer.
- For incidents: query `/api/enterprise/incidents/{incident_id}`, then
  export-runs and messages filtered by account and date range.
- For outages: query `/api/outages` and match by service area or affected
  accounts against the ticket/case record.

## Naming Conventions

When output fields require generated names (channels, folders, report titles):

- Channel names: lowercase-hyphenated client name (e.g. `asteri-retail-inc`)
- Evidence folders: `{Client Name} {Month Year} Investigation`
- Report titles: `{Client Name} Export Failure - Resolution Report`

Follow any explicit naming rules in the payload `response_requirements.json`.

## Summary Computations

Compute summary fields by counting the decisions made:

- Count each status/route/action category from the per-record decisions
- For monetary totals, sum the `charge_amount_usd` fields across all records
- For SLA credit percent, read the value from the SLA endpoint response

## References

- [api_endpoints.md](references/api_endpoints.md) -- Complete API endpoint catalog with response shapes
- [decision_rules.md](references/decision_rules.md) -- Domain-specific resolution logic for each task type
