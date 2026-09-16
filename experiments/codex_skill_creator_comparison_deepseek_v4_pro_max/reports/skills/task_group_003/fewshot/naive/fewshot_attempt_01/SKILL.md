---
name: support-console-resolver
description: Resolve telco support tickets, cases, and enterprise incidents by querying a shared REST API and mapping evidence to structured JSON decisions. Use when the task involves a support console API, ticket/case input payloads, and an answer template.
---

# Support Console Resolver

## Overview

This skill solves tasks that require querying a telco support console REST API to diagnose issues and produce structured JSON decisions. The API exposes customer, account, line, bill, plan, device, outage, diagnostic, troubleshooting, and enterprise records. Every task follows the same loop: read the input payload, fetch all relevant records from the API, apply decision rules to classify each item, fill the answer template, and emit only valid JSON.

## Workflow

### Step 1: Orient from the workspace

Read `prompt.txt` first. It tells you the analyst role, which payload file(s) to use, and where the API lives. Then read `payloads/answer_template.json` so you know the exact output schema before you touch the API. Finally, read every payload file listed in the prompt.

The API base URL is always given as `<TASK_ENV_BASE_URL>`. Substitute the actual value before making any request.

### Step 2: Query the API for every entity

For each ticket, case, or incident in the payload, query the relevant endpoints. Use `curl` with `--fail-with-body -s` so you see response bodies and detect HTTP errors. Do not assume data; always verify from the API.

The API reference is in [api_reference.md](api_reference.md). Common lookup chains:

- **Ticket diagnosis**: `/api/tickets/{id}` → `/api/diagnostics/{id}` + `/api/troubleshooting/{id}` + `/api/outages` + `/api/customers/{customer_id}`
- **Case triage (mobile)**: `/api/cases/{id}` or `/api/contact-center/cases/{id}` → `/api/customers/{id}` → `/api/lines/{id}` → `/api/bills/{id}` → `/api/plans/{plan_id}` → `/api/devices/{device_id}`
- **Enterprise incident**: `/api/enterprise/incidents/{id}` → `/api/enterprise/accounts/{id}` → `/api/enterprise/export-runs` + `/api/enterprise/messages` + `/api/enterprise/sla/{account_id}`
- **Quality review**: `/api/tickets/{id}` → `/api/diagnostics/{id}` + `/api/outages` + `/api/customers/{customer_id}`

### Step 3: Apply decision rules

Map every API response field to the answer template enums. The decision trees are documented in [decision_trees.md](decision_trees.md). Key rules:

- An active outage covering the ticket's service type resolves to `PENDING_ACTION` / `OUTAGE_WAIT`. Never escalate an outage; the customer must wait.
- An account with `status` other than `active` resolves to `FAILED` / `INELIGIBLE_ACCOUNT` (or `INVALID_ACCOUNT` for a nonexistent account).
- Authorisation failures on the account (`auth_status: failed`) resolve to `FAILED` / `AUTH_FAILED`.
- Physical infrastructure faults (line cuts, field damage) escalate to `FIELD_OPS`.
- Network backbone or capacity issues escalate to `NETWORK_ENGINEERING`.
- Provisioning or configuration mismatches escalate to `TIER2_SUPPORT`.
- Overdue or suspended accounts route to `ACCOUNTS_PAYABLE`.
- A clean diagnostic with no outage and an active account resolves via `AUTO_TROUBLESHOOTING` to `RESOLVED`.

For mobile cases, map the reported issue to the correct action using the symptom-to-action table in [decision_trees.md](decision_trees.md). Always check the customer, line, bill, plan, and device records to confirm the root cause before picking an action.

### Step 4: Compute summaries

Count the decisions into the summary object. Each summary field must match reality: if a ticket is `RESOLVED`, increment `batch_summary.RESOLVED` by 1. If no tickets are `ESCALATED`, the count is `0`, not omitted. Double-check every count before finalising.

For monetary amounts, use the exact values from API responses (bill `total_due`, plan `data_addon_rate_per_gb` × requested GB). Format to the precision shown in the template: two decimals for USD amounts, one decimal for GB.

### Step 5: Emit the answer

Write the complete filled template to the answer destination. The output must be **valid JSON only** — no markdown fences, no commentary, no trailing text. Preserve the exact field order and structure from `answer_template.json`.

## Important rules

- **Preserve input order**: Tickets and cases in the decisions array must appear in the same order they arrived in the payload.
- **Use exact enum values**: Copy enum strings exactly from the answer template. Do not invent new statuses, action names, or route labels.
- **Required but absent = empty string**: For string fields that are not applicable, use `""`. For numeric fields that are not applicable, use `0` or `0.0` as the template specifies. For booleans, use `false`.
- **API returns 404**: The account/ticket/case does not exist. Classify as `FAILED` / `INVALID_ACCOUNT`.
- **API returns 401/403**: Treat as an `AUTH_FAILED` classification.
- **Parallelise queries**: Query all independent endpoints for a batch concurrently with parallel `curl` calls. This is essential for same-day batch handling.
- **Customer preferences override defaults**: When the payload includes explicit customer preferences (e.g. accepted refuel GB), use those values instead of computing a default from the plan.

## Reference files

- [api_reference.md](api_reference.md) — every endpoint, its response shape, and field meanings
- [decision_trees.md](decision_trees.md) — complete decision tables for tickets, cases, and enterprise incidents
