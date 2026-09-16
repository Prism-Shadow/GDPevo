---
name: support-console-ops
description: Resolve support-console tasks that classify tickets, queue cases, mobile recovery actions, or enterprise export complaints into strict JSON from a provided answer template. Use when the prompt references the shared support console API, ticket/case/export payloads, or asks for ordered decision rows, summaries, owners, routing, or response packages.
---

# Support Console Ops

Use this skill for any task that turns support-console records into exact JSON.

## Workflow

1. Read the prompt, payload files, and answer template together.
2. Identify the task family: service tickets, queue or mobile cases, enterprise export response, or queue-quality review.
3. Use `/api/search?q=...` first when the prompt gives a name, incident code, ticket code, or symptom instead of a direct ID.
4. Open the direct record endpoints and all linked records. Load [support-console-map.md](references/support-console-map.md) for the endpoint map and field cues.
5. Fill only the template keys. Preserve input order or any ordering rule stated in the template.
6. Keep enum values exact, use the requested numeric precision, and use empty strings or zeros only where the template allows them.
7. Derive summaries by counting the finalized rows, not by guessing.
8. Return JSON only.

## Family Notes

- Service tickets: combine ticket, account, outage, diagnostics, and troubleshooting evidence before choosing resolved, pending, escalated, or failed.
- Queue and mobile cases: join case, customer, line, device, bill, and plan records before choosing action, follow-up, permission, charge, and route.
- Enterprise export complaints: use incident, export-run, message, account, and SLA records to set the incident window, root cause, owners, credit, and share permissions.
- Queue-quality reviews: classify the blocker from the records, then map it to the correct route team and resolution status.

## Sanity Check

Before replying, verify that every required field is present, every list has the expected order, and the JSON has no extra prose or markdown.
