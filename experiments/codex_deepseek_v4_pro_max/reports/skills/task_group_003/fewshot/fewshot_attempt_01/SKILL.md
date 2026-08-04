---
name: support-console-analyst
description: Resolve support operations tasks by querying a shared support-console API and producing structured JSON answers. Use when a task provides a prompt, payload files, and an answer template that references records in the support-console API.
---

# Support Console Analyst

## Overview

This skill handles structured support-operations tasks where the agent must query a shared REST API (the "support console") to retrieve account, ticket, customer, line, device, plan, bill, incident, outage, diagnostic, troubleshooting, and related records, then produce a JSON answer that strictly conforms to a provided answer template.

Each task instance provides:
- `prompt.txt` – role description, the API base URL placeholder (`<TASK_ENV_BASE_URL>`), and references to payload and template files.
- `payloads/` – one or more input files (CSV, JSON, TXT) describing the entities that need resolution.
- `payloads/answer_template.json` – a JSON schema describing the exact shape of the required output.

## Workflow

### Step 1: Read the Task Inputs

1. Read `prompt.txt` to understand the role, the task domain, and which payload files to process.
2. Resolve `<TASK_ENV_BASE_URL>` to the actual base URL, typically from an environment variable (`GDPEVO_ENV_BASE_URL`) or the `environment_access.md` file.
3. Read every file in the `payloads/` directory, especially `answer_template.json`.

### Step 2: Discover and Query the API

The support-console API is read-only (GET only). Start by querying the catalog endpoint for a complete listing of available resources and their schemas:

```
GET {base_url}/api/catalog
```

Available endpoints include:

| Endpoint | Purpose |
|---|---|
| `/api/catalog` | Full API resource listing and schema reference |
| `/api/accounts` / `/api/accounts/{id}` | Account records |
| `/api/tickets` / `/api/tickets/{id}` | Support ticket records |
| `/api/outages` | Active and historical outage records |
| `/api/diagnostics/{ticket_id}` | Diagnostic results for a ticket |
| `/api/troubleshooting/{ticket_id}` | Troubleshooting actions and outcomes for a ticket |
| `/api/customers` / `/api/customers/{id}` | Customer profiles |
| `/api/lines` / `/api/lines/{id}` | Mobile/voice line records |
| `/api/devices` / `/api/devices/{id}` | Device records |
| `/api/plans` / `/api/plans/{id}` | Service plan records |
| `/api/bills` / `/api/bills/{id}` | Billing records |
| `/api/cases` / `/api/cases/{id}` | Contact-center case records |
| `/api/contact-center/cases` / `/api/contact-center/cases/{id}` | Contact-center case records (alternate path) |
| `/api/enterprise/accounts` / `/api/enterprise/accounts/{id}` | Enterprise account records |
| `/api/enterprise/incidents` / `/api/enterprise/incidents/{id}` | Enterprise incident records |
| `/api/enterprise/export-runs` | Enterprise export-run records |
| `/api/enterprise/messages` | Enterprise message/alert records |
| `/api/enterprise/sla/{account_id}` | SLA agreement details for an enterprise account |
| `/api/search` | General search endpoint |

### Step 3: Match Payload Entities to API Records

For each entity in the payload (ticket, case, account, incident, etc.):

1. Identify the entity type and its identifier from the payload.
2. Query the relevant API endpoint(s) to retrieve the full record(s).
3. Cross-reference related entities as needed. For example:
   - A ticket may require its associated account record, diagnostic results, troubleshooting history, and any active outages.
   - A case may require its associated customer, line, device, plan, and bill records.
   - An enterprise incident may require the enterprise account, incident details, export-run history, SLA terms, and message/alert records.

### Step 4: Classify and Decide

Use the API records — not assumptions — to determine classifications. Key classification dimensions observed across tasks:

- **Resolution status**: RESOLVED, PENDING_ACTION (e.g., waiting on outage), ESCALATED (needs a specialist team), FAILED (invalid account, auth failure, ineligible, etc.).
- **Route / escalation team**: Which team should handle the case (NONE, TIER2_SUPPORT, FIELD_OPS, NETWORK_ENGINEERING, ACCOUNTS_PAYABLE).
- **Blocker / root cause**: The key reason the entity cannot be resolved immediately (ACTIVE_OUTAGE, INVALID_ACCOUNT, AUTH_FAILED, OVERDUE_SUSPENSION, FRAUD_SUSPENSION, NETWORK_CAPACITY, PROVISIONING_STALE, PHYSICAL_LINE_FAULT, NONE).
- **Actions**: Device or account operations to perform (TOGGLE_AIRPLANE_MODE, RESEAT_SIM, RESET_APN_REBOOT, SEND_PAYMENT_REQUEST, RESUME_LINE_REBOOT, TOGGLE_MOBILE_DATA, TOGGLE_ROAMING, ENABLE_LINE_ROAMING, REFUEL_DATA, TOGGLE_DATA_SAVER, SET_NETWORK_MODE, DISCONNECT_VPN, GRANT_MESSAGING_PERMISSION, TOGGLE_WIFI_CALLING, TRANSFER_HUMAN, NO_ACTION).
- **Enterprise response fields**: Root cause category, failure window, backfill days, SLA credit, severity, owners, evidence folder, report title, share permissions, response status.

### Step 5: Build the Answer

Construct JSON that exactly matches `payloads/answer_template.json`:

- **Preserve order**: If the template or prompt specifies an ordering (e.g., preserve payload order, ascending case_id order, order by user as listed), follow it exactly.
- **Use exact enum values**: Only use the string values listed in the template's enum annotations. Do not invent new values.
- **Fill all required fields**: Every field in the template must be present in the output.
- **Summary counts must be accurate**: Numeric summaries must match the per-entity classifications exactly.
- **Conditional fields**: Fields marked "empty when not applicable" or "0.0 when not applicable" should use the appropriate zero/empty value rather than being omitted.

### Step 6: Validate the Output

1. Verify the output parses as valid JSON.
2. Verify every field from the answer template is present.
3. Verify all enum values are from the allowed set.
4. Verify summary counts match the item-level decisions.
5. Verify ordering requirements are met.
6. Verify all values come from API records, not assumptions.

## Payload Format Handling

- **CSV files**: Parse with a CSV reader. The first row is the header. Fields may contain commas within values.
- **JSON files**: Parse with a JSON parser. Arrays of objects are common for entity lists; use the keys provided.
- **Plain text files**: Read as-is. Extract relevant identifiers, names, and contextual clues.

## Error and Edge Cases

- **Missing API records**: If an entity ID cannot be found in the API, classify it as FAILED/INVALID_ACCOUNT (or the closest matching terminal status for the domain).
- **Ambiguous data**: Prefer API records over payload descriptions when they conflict.
- **Multiple related records**: When an entity has multiple related records, consider all of them for the most accurate classification.
- **No matching records**: Use the NONE enum variant for escalation_team, route_team, blocker, or similar fields when no specialist routing is needed.
