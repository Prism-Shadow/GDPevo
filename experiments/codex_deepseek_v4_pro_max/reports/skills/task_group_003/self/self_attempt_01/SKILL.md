---
name: support-console
description: Resolve support-console analysis tasks by reading structured prompts and payloads, querying a GET-only REST API for evidence, classifying tickets/cases against enumerated answer templates, and producing compliant JSON output with batch summaries. Use when given a task directory containing prompt.txt and payloads/ with answer_template.json, involving ticket triage, case routing, enterprise incident response, queue-quality review, or mobile-data recovery against a support console API.
---

## Task Intake

When given a task directory containing a `prompt.txt` and `payloads/` subdirectory:

1. Read `prompt.txt` first. Identify:
   - The persona/role assigned (e.g., support operations analyst, contact-center lead, queue-quality analyst).
   - The API base URL placeholder (`<TASK_ENV_BASE_URL>`). Resolve it from environment or from `environment_access.md`.
   - Which payload file(s) contain the work items.
   - Which payload file is the answer template (always named or described in the prompt).

2. Read every file in `payloads/`. Typically this includes:
   - One or more input payloads (CSV, JSON, or plain text) containing the worklist.
   - An `answer_template.json` defining the required output schema with enums, field types, and formatting rules.
   - Optionally, a supplemental requirements file (e.g., `response_requirements.json`) with additional constraints such as naming conventions, permission users, or required fields.

3. Internalize the answer template fully before making any decisions. Every field, enum value, and ordering constraint in the template is mandatory.

## API Usage

- Only use the endpoints listed in the environment access document. All endpoints are GET-only.
- Look up every piece of data from the API; never assume or fabricate.
- When resolving a ticket or case, query the smallest set of relevant endpoints needed to reach a decision. Common lookup patterns:
  - For tickets: `/api/tickets/{ticket_id}`, `/api/accounts/{account_id}`, `/api/outages`, `/api/diagnostics/{ticket_id}`, `/api/troubleshooting/{ticket_id}`.
  - For cases: `/api/cases/{case_id}`, `/api/customers/{customer_id}`, `/api/lines/{line_id}`, `/api/bills/{bill_id}`, `/api/plans/{plan_id}`, `/api/devices/{device_id}`.
  - For enterprise tasks: `/api/enterprise/accounts/{account_id}`, `/api/enterprise/incidents/{incident_id}`, `/api/enterprise/export-runs`, `/api/enterprise/messages`, `/api/enterprise/sla/{account_id}`.
- If an account or ticket ID is malformed or absent from the API, classify it accordingly (e.g., `INVALID_ACCOUNT`, `FAILED`) rather than guessing.
- When the payload references a customer report (e.g., "no service", "slow data"), cross-reference that report with API evidence to determine the root cause and appropriate action.

## Decision Framework

### Classification

Every work item must be assigned a resolution status and, where applicable, a routing target:

- **RESOLVED**: The issue can be addressed through automated actions, self-service guidance, or a known outage where the fix is already in progress and no escalation is needed.
- **PENDING_ACTION**: The issue requires a customer-side action (e.g., payment, SIM reseat, settings change) or a carrier-side update that has been submitted but not yet confirmed.
- **ESCALATED**: The issue requires a human team (TIER2_SUPPORT, FIELD_OPS, NETWORK_ENGINEERING, ACCOUNTS_PAYABLE) and cannot be resolved by the analyst alone.
- **FAILED**: The item cannot be processed due to invalid account, authentication failure, or irrecoverable data mismatch.

### Action Selection

When a work item requires choosing from an action enum:
- Match the reported symptom and API evidence to the most precise action available.
- If multiple actions could apply, choose the one that addresses the root cause rather than the symptom.
- A secondary action (follow-up) should only be set when the template requires it and the situation warrants a second step; otherwise use the `NO_ACTION` or `NONE` sentinel.

### Monetary Values

- Charge amounts must reflect actual bill or plan data queried from the API.
- Use the exact decimal precision specified in the template (e.g., `number with two decimals` means `"0.00"` format).
- When no charge applies, use `0.00` (or the template-specified zero sentinel).

### Permissions

When the template includes permission fields:
- Derive required permissions from the action (e.g., messaging fixes need `sms`, photo attachments need `storage`).
- When both SMS and storage actions are needed, use `sms_and_storage` if available; otherwise `NONE`.

## Output Rules

1. Return **only** valid JSON that matches the answer template exactly. No markdown fences, no explanatory text, no trailing commentary.
2. Preserve the order of work items as they appear in the input payload.
3. Fill every field in the template. Use the correct enum value, empty-string sentinel (`""`), or zero sentinel as defined by the template.
4. Compute summary counts from the decisions made; do not estimate or hard-code them.
5. Follow any naming conventions provided in requirements files (e.g., lowercase-hyphen channel names, date-prefixed folder names, client-specific report titles).

## Summary Aggregation

Every answer template includes a summary section. Count each work item exactly once in the relevant category. For nested summaries (e.g., per-team breakdowns within a queue summary), ensure totals are consistent with the individual item decisions.
