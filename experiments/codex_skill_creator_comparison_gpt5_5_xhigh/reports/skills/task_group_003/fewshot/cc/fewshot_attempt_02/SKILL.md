---
name: support-console-json-resolver
description: Resolve support-console operations tasks that require reading local payload files, querying a TASK_ENV_BASE_URL support console API, classifying service tickets, contact-center or mobile-data cases, queue SLA handoffs, and enterprise export complaints, then returning strict JSON matching payloads/answer_template.json. Use this skill whenever the prompt mentions support console records, service tickets, mobile support cases, data recovery worklists, queue-quality review, SLA handoff, enterprise export incidents, or structured support-response packages.
---

# Support Console JSON Resolver

Use this skill to turn local support-operation payloads plus support-console API evidence into the exact JSON requested by an `answer_template.json`.

## Workflow

1. Read the user prompt and every file under the task's `payloads/` directory, especially `answer_template.json`.
2. Determine the support-console base URL from the prompt, environment, or task access note. Do not invent records from payload text.
3. Collect linked API evidence with the bundled helper:

   ```bash
   python scripts/collect_support_console.py payloads --base-url "$TASK_ENV_BASE_URL" --output /tmp/support_console_evidence.json
   ```

   Run that from the skill root, or substitute the installed skill path if the files live elsewhere. Adjust `payloads` and the base URL path to the actual locations in the current workspace. If `TASK_ENV_BASE_URL` is not set, pass the literal base URL from the task.

4. Read `/tmp/support_console_evidence.json`, then read [decision-rules.md](references/decision-rules.md) for the relevant task family.
5. Fill the template exactly. Preserve required item ordering, enum spelling, empty-string conventions, and numeric/boolean types.
6. Recompute summary counts from the completed decisions.
7. Validate that the final response parses as JSON and has no extra prose. Return only the JSON object.

## Task Family Detection

- `ticket_batch.csv` or `queue_snapshot.csv`: fixed-service ticket routing. Use ticket, account, outage, diagnostic, and troubleshooting evidence.
- `case_queue.json` or `mobile_data_worklist.json`: contact-center or mobile-data case routing. Use case, customer, line, bill, plan, and device evidence.
- `client_complaint_email.txt` with `response_requirements.json`: enterprise export response package. Use incident, enterprise account, export-run, SLA, and message evidence.

## API Notes

- Start with `/api/catalog` if endpoint names are unclear.
- Ticket tasks commonly use `/api/tickets/{ticket_id}`, `/api/accounts/{account_id}`, `/api/outages`, `/api/diagnostics/{ticket_id}`, and `/api/troubleshooting/{ticket_id}`.
- Mobile/contact-center tasks commonly use `/api/cases/{case_id}` or `/api/contact-center/cases/{case_id}`, then `/api/customers/{customer_id}`, `/api/lines/{line_id}`, `/api/devices/{device_id}`, `/api/plans/{plan_id}`, and `/api/bills`.
- Enterprise tasks commonly use `/api/search`, `/api/enterprise/incidents/{incident_id}`, `/api/enterprise/accounts/{account_id}`, `/api/enterprise/export-runs`, `/api/enterprise/messages`, and `/api/enterprise/sla/{account_id}`.

When API evidence and payload wording conflict, trust the API unless the prompt explicitly says the payload overrides it.
