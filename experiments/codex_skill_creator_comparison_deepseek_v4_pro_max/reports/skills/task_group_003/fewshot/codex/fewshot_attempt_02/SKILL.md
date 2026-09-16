---
name: telco-support-triage
description: >-
  Resolve telco support tickets, cases, and enterprise response packages using a
  shared support console REST API. Use when asked to classify service tickets,
  triage mobile or enterprise cases, prepare client complaint response packages,
  analyze queue quality, or recover mobile-data worklists from a telecom
  operator's support-console API. Typical triggers include CSV ticket batches,
  JSON case queues, enterprise complaint emails paired with response requirements,
  or mobile-data worklists with customer preferences.
---

# Telco Support Triage

## Overview

Use the shared support console API to fetch the records needed for each task,
then classify items and produce structured JSON output matching the provided
answer template. Every task follows the same pattern: read the payload file(s),
call the relevant API endpoints for each listed identifier, map the evidence to
classifications using the decision rules below, and output JSON that conforms
exactly to the answer template.

**Never guess.** Fetch every record from the API. If an API call fails or
returns no data, treat that as actionable evidence (e.g., invalid account,
auth failure).

## Workflow

1. Read the prompt, the payload file(s) under the input directory, and the
   answer template.
2. Identify every entity ID in the payload (ticket IDs, case IDs, account IDs,
   incident IDs, customer IDs, line IDs, bill IDs).
3. Fetch the corresponding records from the API using the endpoint catalog in
   [API Endpoints](references/api_endpoints.md). Call each endpoint exactly as
   listed.
4. Apply the classification rules in
   [Classification Rules](references/classification_rules.md) to map API
   evidence into the template enum choices.
5. Output only valid JSON that matches the answer template exactly. Preserve
   payload ordering for arrays. Quote all string values. Use numeric types for
   integers and decimals as specified.

## API Guidance

The base URL is always the task environment variable `<TASK_ENV_BASE_URL>`.
Substitute it literally.

Fetch every entity record before drawing conclusions. When a record is absent
or returns an error:

- Ticket calls returning 404 or empty means the account is invalid.
- Customer calls returning 404 means no matching customer.
- Enterprise calls: use the complaint email approximate reference to look up the
  real incident, then cross-reference with messages and export-runs.

For the full endpoint catalog see [API Endpoints](references/api_endpoints.md).
For how to map API evidence to classifications see
[Classification Rules](references/classification_rules.md).

## Task Types

The API supports five categories of task. Match the payload structure to the
right category:

**Ticket batch** — CSV of ticket_id rows with account_id, reported_service_type,
and a customer report or queue note. Resolve each ticket by pulling ticket,
diagnostic, outage, and account records. Output ticket_decisions with resolution
statuses and escalation routes.

**Case queue (mobile support)** — JSON array of cases with case_id and
reported_issue. Pull customer, line, bill, plan, and device records. Assign a
primary and secondary action from the mobile-action enum. Output case_decisions.

**Enterprise response package** — Complaint email plus
response_requirements.json. Pull the enterprise account, incident, export-runs,
messages, and SLA records. Fill in root cause, failure window, owners, severity,
permissions, and response status.

**Queue quality review** — CSV of tickets with a queue_note column. Classify
using the key-blocker and route-team enums instead of the full resolution route.
Output ticket_decisions with key_blocker and route_team.

**Mobile-data recovery worklist** — JSON array of cases with reported_issue plus
customer_preferences. Pull customer, line, bill, plan, and device records.
Focus on data-specific actions (refuel, roaming, data-saver, network mode,
mobile data toggle). Include data_refuel_gb and charge_amount_usd when
applicable.

## Important Rules

- Preserve payload ordering: output arrays must list items in the same order
  they appear in the input payload.
- The answer template is authoritative for output shape and enum values. Always
  read the template before output.
- When a field requires an empty string, an explicit NONE, or 0.0, use exactly
  that value — not null or omission.
- For summary fields, count items in the decisions array; do not derive from
  external sources.
- The tickets_requiring_customer_wait summary field counts tickets whose
  resolution requires the customer to wait for an external event (e.g., outage
  resolution).
