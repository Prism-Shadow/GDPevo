---
name: support-console-batch-solver
description: Resolve staged support-console batch tasks by querying the task environment API, joining ticket, case, line, device, bill, plan, outage, diagnostics, troubleshooting, and enterprise records, and returning exact JSON that matches the provided answer template. Use when the prompt points to the shared support console and asks for ticket triage, mobile queue actions, queue-quality review, or enterprise export response packages.
---

# Support Console Batch Solver

## Workflow

1. Read the prompt, payloads, and `payloads/answer_template.json` first.
2. Identify the task family, then query the shared support-console API at the task environment base URL.
3. Pull the records named in the payload, plus any linked records needed to confirm the decision.
4. Apply the task-family rules in [support_console.md](references/support_console.md).
5. Preserve the required ordering from the template or payload.
6. Return JSON only. Match enum strings, booleans, empty strings, and number precision exactly.

## Record lookup

- Tickets: use ticket, outage, diagnostics, and troubleshooting endpoints.
- Mobile cases: use case, customer, line, device, bill, plan, and account records.
- Enterprise exports: use incident, export-run, message, and SLA records.

## Output discipline

- Do not invent facts when the API has the answer.
- Do not reuse task-specific values across cases or add fields that are not in the template.
- When a template says preserve order, keep the payload order; when it says ascending case IDs, sort by `case_id`.
