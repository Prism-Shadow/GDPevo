---
name: support-console
description: Solve support-console tasks that use the shared support-console API and require strict JSON output from ticket batches, mobile case queues, queue-quality reviews, or enterprise incident/export response packages. Use when the prompt asks you to read payload files, follow linked support records, and return only JSON that matches an answer template.
---

# Support Console

Use this skill for any task that resolves records from the shared support-console API and emits a strict JSON answer.

## Workflow
1. Read the prompt, answer template, and every file in `payloads/`.
2. Identify the task family: ticket batch, mobile case queue, queue-quality review, or enterprise response package.
3. Query the task environment for the exact IDs in the payload, then follow linked records until every template field is supported by evidence.
4. Build the JSON to match the template exactly. Preserve input order unless the template says ascending order.
5. Return JSON only. No markdown, prose, or code fences.

## Record lookup
See [references/support-console.md](references/support-console.md) for the endpoint map and the field cues that matter in each task family.

## Output rules
- Match enum values exactly.
- Use empty strings and zero values when the template says "none" or "not applicable".
- Derive summary counts from the per-record decisions.
- Do not invent IDs, charges, credits, or dates when the records do not support them.
- Prefer the most specific record tied to the requested ID over broader search results.

## When in doubt
- For tickets, inspect ticket, outage, diagnostics, troubleshooting, and account records.
- For mobile cases, inspect case, line, customer, device, bill, and plan records.
- For enterprise packages, inspect incident, export-run, message, and SLA records.
- If the prompt gives a naming rule, follow it literally for channels, folders, and report titles.
