---
name: support-console-resolver
description: Resolve telecom support-console tickets, cases, and enterprise incidents by querying a shared REST API and producing structured JSON decisions from an answer template. Use this skill whenever the task involves a support console base URL (paths like /api/tickets, /api/diagnostics, /api/outages, /api/cases, /api/enterprise/incidents), resolving service tickets from CSV or JSON batches, triaging contact-center or mobile-data cases, investigating enterprise export failures, auditing queue quality before SLA handoff, or any workflow that requires looking up support-console API records and filling out a provided decision template.
---

# Support Console Resolver

How to navigate a telecom support console API, resolve tickets, cases, and
enterprise incidents from records rather than assumptions, and produce decisions
that conform to a provided answer template.

## Core Principles

**Every decision is an API lookup, never a guess.** The reported issue text in
a payload gives you a starting point, but the resolution must come from the API
records. When you see a ticket, case, or incident identifier, fetch its full
record. Then follow every cross-reference it contains.

**Parallelize all independent fetches.** When you have a batch of N items,
fetch all individual records, diagnostics, and related resources simultaneously
in one wave. Serial fetches waste time and risk hitting rate limits
unnecessarily late.

**Conform to the template, not to habit.** Every task provides an
`answer_template.json` with strict fields, enum values, and ordering
requirements. Read it before you write the output. Enum values in the output
must appear exactly as written in the template. Do not invent synonyms.

## How to Approach Any Task

1. Read the prompt to understand the role and identify the task type.
2. Read every payload file. Note which entity IDs are present and which
   cross-references you will need to follow.
3. Read the answer template. Note every field, its type, its allowed enum
   values, and any ordering constraints.
4. Identify the relevant API endpoints for this task type using the
   [API Endpoints](references/api-endpoints.md) reference.
5. Fetch all primary records in a single parallel wave: every individual
   ticket, case, or incident in the batch, plus any list endpoints (outages,
   export-runs, messages) that cover all items.
6. From the primary records, extract every cross-reference (account_id,
   customer_id, line_id, bill_id, etc.) and fetch all secondary records in a
   second parallel wave: diagnostics, troubleshooting records, customers,
   lines, bills, plans, devices, SLA records, and enterprise accounts.
7. For each item, apply the decision rules in
   [Resolution Patterns](references/resolution-patterns.md) to map the API
   evidence to template fields.
8. Build the output JSON matching the template structure, field order, and
   enum constraints exactly.
9. Compute summary counts by tallying the decisions you already made; do not
   calculate them independently.

## Task Types and Their API Footprints

The prompt and payloads signal which workflow applies. A single task may
combine patterns; when it does, apply each pattern to the corresponding subset
of items.

### Ticket Resolution

**Prompt signals:** "support operations analyst", "queue-quality analyst",
"service tickets", "ticket batch", "queue snapshot", "SLA handoff",
"same-day batch", "classify each ticket"

**Payloads:** CSV with columns that include `ticket_id` and `account_id`
(typically also `reported_service_type`, `customer_report`, or `queue_note`).

**API footprint:** Tickets, diagnostics, troubleshooting, outages.
Use [API Endpoints](references/api-endpoints.md#tickets-and-diagnostics).

**Decision logic:** [Resolution Patterns](references/resolution-patterns.md#ticket-resolution).

### Contact-Center Case Triage

**Prompt signals:** "contact-center lead", "mobile support queue", "case queue",
"choose the support operation"

**Payloads:** JSON with a `cases` array containing `case_id` and
`reported_issue`. May include `customer_preferences`.

**API footprint:** Cases, customers, lines, bills, plans, devices.
Use [API Endpoints](references/api-endpoints.md#contact-center-and-customers).

**Decision logic:** [Resolution Patterns](references/resolution-patterns.md#case-triage).

### Enterprise Incident Response

**Prompt signals:** "enterprise support lead", "export complaint",
"structured response package", "client export complaint", "formal response"

**Payloads:** Complaint email (`.txt`) with client identity and incident
reference, plus response requirements (`.json`) with field list, permission
users, and naming conventions.

**API footprint:** Enterprise incidents, accounts, export-runs, messages, SLA.
Use [API Endpoints](references/api-endpoints.md#enterprise).

**Decision logic:** [Resolution Patterns](references/resolution-patterns.md#enterprise-incidents).

### Mobile Data Recovery

**Prompt signals:** "mobile-data recovery analyst", "data recovery",
"mobile data worklist", "data refuel", "carrier update"

**Payloads:** JSON with a `cases` array plus `customer_preferences` mapping
case IDs to accepted refuel amounts and plan-change preferences.

**API footprint:** Cases, customers, lines, devices, plans.
Use [API Endpoints](references/api-endpoints.md#contact-center-and-customers).

**Decision logic:** [Resolution Patterns](references/resolution-patterns.md#mobile-data-recovery).

## Domain Model Overview

The console models a multi-tenant telecom provider. Each entity carries
cross-references you must follow to reach a decision. The full reference is at
[Domain Model](references/domain-model.md).

Key relationship chains to follow:

- **Ticket** to `account_id` to diagnostic, troubleshooting, outage matching
- **Case** to `customer_id` + `line_id` to Customer to Line to Bill, Plan, Device
- **Enterprise Incident** to `enterprise_account_id` to export-runs, messages,
  SLA, account details

When an API response includes an ID you do not yet have, fetch that resource.
Empty or null IDs signal that relationship does not apply.

## Parallel Fetch Strategy

Structure your API calls in two waves:

**Wave 1 (primary records):** Every ticket, case, or incident listed in the
payload, fetched by individual GET. Also fetch the list endpoints that serve
all items: `/api/outages`, `/api/enterprise/export-runs`,
`/api/enterprise/messages`.

**Wave 2 (secondary records):** Every diagnostic, troubleshooting record,
customer, line, bill, plan, device, SLA, or enterprise account referenced by
Wave 1 results. Gather all IDs first, then fetch everything in one parallel
batch.

After Wave 2 you have all the evidence needed to make decisions. Do not make
additional API calls during decision-writing unless the template demands a
field that none of your fetched records covers.

## Output Rules

1. **Preserve item order** as directed by the template. Common directives are
   "preserve payload order" (CSV row order) or "preserve ascending case_id
   order." Follow them literally.
2. **Use exact enum strings.** If the template defines
   `RESOLVED | PENDING_ACTION | ESCALATED | FAILED`, do not write `Closed`,
   `Pending`, or any other variant.
3. **Empty strings for absent references.** Use `""` for fields like
   `outage_id`, `bill_id`, or `escalation_team` when no value applies.
4. **Zero for absent numerics.** Use `0.0` or `0` for `charge_amount_usd`,
   `data_refuel_gb`, or similar fields that do not apply to the decision.
5. **Boolean false for absent conditions.** Set `diagnostic_needed`,
   `latency_issue`, `stability_issue`, `bandwidth_issue`, and
   `carrier_update_required` to `false` when the API evidence does not
   support them.
6. **Derive summary counts from the decisions array.** Tally the actual
   `final_resolution_status`, `final_route`, or equivalent category values in
   the decisions you produced. Do not estimate or compute summaries
   independently; that guarantees drift.
7. **Match summary field names to the template.** Some templates name the
   summary object `batch_summary`, others `queue_summary` or
   `worklist_summary`. Use the name the template provides.

## Common Pitfalls

- **Resolving from the reported issue text instead of the API.** The payload
  text hints at which endpoints to query; it is not the resolution itself.
- **Fetching records one at a time.** Batch all independent GETs into parallel
  waves.
- **Stopping at the first record.** A ticket's `account_id` leads to account
  validation; a case's `line_id` leads to the line, the plan, and the device.
  Follow every cross-reference the API gives you.
- **Inventing enum values not in the template.** The template is the schema
  contract. Read it before writing output.
- **Computing summaries that do not match the decisions.** Count from the
  decisions array you built; never recalculate.
- **Using a non-existent base URL.** The base URL comes from the prompt
  (often as `<TASK_ENV_BASE_URL>` or a specific host:port). Do not hardcode
  it. If the prompt uses a placeholder, substitute it from the environment.
