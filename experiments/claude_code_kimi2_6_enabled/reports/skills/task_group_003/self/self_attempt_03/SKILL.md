# CRM Support Console Task Group Skill

## Environment
- **Base URL**: `GDPEVO_ENV_BASE_URL=http://34.46.77.124:8003` (overrides any local references in prompts).
- **Server**: SupportConsole/1.0 (Python/3.11.2).
- **Caution**: Standard REST paths (`/tickets`, `/cases`, `/agents`, `/customers`, `/sla`, `/refund`, etc.) consistently return `{"error": "not_found"}`. Endpoint discovery via common naming conventions is unreliable for this console. If an endpoint is not stated explicitly in the prompt or `environment_access.md`, treat it as unknown and follow payload-driven reasoning rather than guessing.

## General Workflow
1. Read `prompt.txt` in the task directory to identify the analyst persona and objective.
2. Read all files under `input/payloads/`. There may be multiple payloads (e.g., a data file plus `response_requirements.json`).
3. Read `input/payloads/answer_template.json` before reasoning. The template defines the exact output schema, field names, types, and ordering rules.
4. Resolve each item using **support-console records** referenced in the prompt, not assumptions. If the remote API does not expose the expected resource, rely on the local payload data and any explicit rules or enums in the template.
5. Return **only** JSON that conforms to the answer template. No markdown fences, no extra commentary.

## Task Type Guidance

### Task Type A: Ticket/Case Batch Resolution (train_001, train_002, train_005)
- Input: CSV or JSON list of tickets/cases with IDs and issue summaries.
- For each item, determine:
  - **Primary action/operation** (enum values are listed in the answer template).
  - **Secondary/follow-up action** (if applicable; use `"NONE"` or `"NO_ACTION"` when absent).
  - **Routing/escalation**: agent assignment, queue, or final route enum.
  - **Financial fields**: refund eligibility, charge amounts, or data-refuel GB. Respect exact decimal precision specified in the template (usually 2 decimals for currency, 1 for GB).
- **Ordering**: Preserve ascending `case_id` / `ticket_id` order unless the template explicitly says otherwise.

### Task Type B: Complaint Response Package (train_003)
- Input: `client_complaint_email.txt` + `response_requirements.json`.
- Output schema includes:
  - `incident_summary`: root cause, failed export window, evidence references.
  - `sla_credit`: boolean + amount (2 decimals).
  - `owners`: primary, secondary, client contacts.
  - `response_artifacts`: acknowledgments, action items, preventive measures.
  - `tone`: enum (`APOLOGETIC`, `INVESTIGATIVE`, `REASSURING`).
- Derive dates/times from the email body and requirements. Use ISO-8601 when the template expects it.

### Task Type C: SLA/Queue Quality Review (train_004)
- Input: `queue_snapshot.csv` with columns such as `ticket_id`, `status`, `priority`, `created_at`, `first_response_at`, `resolved_at`, `agent_id`.
- Output includes:
  - `sla_compliant`: boolean for the whole snapshot.
  - `violations`: array of non-compliant ticket IDs.
  - `avg_response_time_seconds` / `avg_resolution_time_seconds`: numeric averages.
  - `agent_workload`: count of tickets per agent.
  - `capacity_flag`: enum (`WITHIN_CAPACITY`, `AT_CAPACITY`, `OVER_CAPACITY`).
- **Rounding**: average times are typically floats; follow the template’s precision guidance (often integer seconds or one decimal).
- **Sorting**: agents in `agent_workload` usually appear in ascending agent ID order.

## Schema & Output Conventions
- **Field names**: copy exactly from the answer template; do not camelCase or snake_case differently.
- **Enums**: use the exact uppercase strings shown in the template descriptions (e.g., `TOGGLE_MOBILE_DATA`, `REFUEL_DATA`, `DATA_RECOVERY`, `HUMAN_TRANSFER`, `APOLOGETIC`, `WITHIN_CAPACITY`).
- **Null/Not-applicable handling**:
  - Numeric not-applicable defaults: `0.0` (1-decimal fields) or `0.00` (2-decimal fields).
  - String not-applicable defaults: `"NONE"`, `"NO_ACTION"`, or `"N/A"` per template annotation.
  - Boolean not-applicable defaults: `false` unless the context implies `true`.
- **Dates/Times**: Prefer ISO-8601 (`YYYY-MM-DDTHH:MM:SSZ`) when the template expects datetime strings.
- **Currency**: always two decimal places (`12.00` not `12`).
- **Data refuel**: always one decimal place (`2.0` not `2`).

## Common Pitfalls
1. **Do not invent API paths**. If the prompt says "use the shared support console API" but does not name an endpoint, and common paths return 404, reason from the local payload and template enums rather than brute-forcing routes.
2. **Do not assume agent availability**. When assigning cases, check the `agents` list in the payload for `max_cases` or current load before overflow logic.
3. **Do not ignore customer preferences**. Payloads like `customer_preferences` (train_005) override default operations (e.g., `does_not_want_plan_change` forces a refuel instead of plan change).
4. **Do not reorder items**. The template often explicitly says "preserve ascending case_id order."
5. **Do not omit zero-valued fields**. When a numeric field is "not applicable," supply the zero default shown in the template description rather than omitting the key.
6. **Do not add wrapper keys**. The output should be a single JSON object matching the template root structure, not wrapped in `{"result": ...}`.

## API Interaction Rules (if endpoints are provided in a future prompt)
- Use `GET` for record retrieval unless the prompt specifies `POST`.
- Send `Accept: application/json` header.
- If the endpoint returns a nested record (e.g., ticket with embedded customer and device), flatten only as required by the answer template; preserve original IDs for cross-referencing.
- If a ticket/case is missing from the API response, flag it in `violations` or `unresolved_items` rather than fabricating data.
