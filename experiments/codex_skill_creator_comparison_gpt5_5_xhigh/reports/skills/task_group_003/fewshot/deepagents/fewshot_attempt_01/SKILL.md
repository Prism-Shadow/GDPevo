---
name: support-console-ops
description: Resolve support-console JSON tasks for offline service tickets, contact-center case queues, mobile-data recovery, queue-quality reviews, and enterprise export complaint packages. Use when the prompt references ticket batches, queue snapshots, case queues, mobile-data worklists, or export complaint evidence and requires a JSON answer matching a template.
---

# Support Console Ops

## Overview

Use this skill for staged support-console problems. Read the prompt payloads first, identify the task family, and fetch only the records needed from the support-console API. Keep the final answer JSON-only and match the template exactly.

## Workflow

1. Read the payload type and answer template.
2. Open [references/support-console.md](references/support-console.md) for the endpoint map and decision rules.
3. Look up the relevant records by ID, service area, line, device, bill, outage, incident, or account.
4. Apply the matching workflow below.
5. Emit only the requested JSON, preserving the required order and field names.

## Output Rules

- Preserve input order unless the template says to sort by `case_id`.
- Use exact enum values and number formats from the template.
- Leave unused strings empty and unused numeric fields at `0` or `0.0`.
- Do not add commentary, code fences, or extra keys.

## Task Family Guide

### Offline Ticket Batches
Use ticket, outage, diagnostics, and troubleshooting evidence. Mark outages as customer wait, access failures as ineligible, and plant or provisioning issues as escalations.

### Queue-Quality Reviews
Classify the blocker first, then assign the route team and diagnostic requirement from the blocker taxonomy.

### Contact-Center Case Queues
Pick the first corrective action that matches the issue, then choose a second action only when the evidence requires one. Fill bill, permission, and charge fields from the supporting records.

### Mobile-Data Recovery
Separate data refuels, carrier updates, and device-setting fixes. Use the plan refuel price when the case needs a top-up.

### Enterprise Export Complaints
Use incident, export-run, message, and SLA evidence to fill the report package, window, root cause, credit, owners, naming, and share permissions.
