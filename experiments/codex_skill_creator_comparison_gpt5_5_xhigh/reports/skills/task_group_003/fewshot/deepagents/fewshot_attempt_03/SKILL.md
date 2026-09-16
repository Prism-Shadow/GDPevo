---
name: support-console-solver
description: Inspect the live support-console API, follow IDs from payload files, and return only JSON that matches the supplied answer template. Use when a prompt references the shared support console, offline ticket batches, contact-center case queues, mobile-data recovery, queue-quality review, or enterprise export complaints and asks for evidence-based JSON instead of assumptions.
---

# Support Console Solver

## Workflow

1. Read the prompt, payload files, and answer template first.
2. Call `/api/catalog` and trust the live catalog over any stale endpoint list in the prompt.
3. Search every payload identifier with `search?q=ID`, then fetch exact linked records for any IDs returned.
4. Ignore unrelated generated records or other matches that do not belong to the current payload.
5. Preserve payload order and fill only the fields that exist in the current template.

## Evidence Graphs

- Ticket batches: `ticket -> account -> outage -> diagnostics -> troubleshooting`
- Contact-center cases: `case -> customer -> line -> device -> bill -> plan`
- Enterprise complaints: `incident -> enterprise account -> export runs -> messages -> SLA contract`

## Ticket Decisions

- Treat a missing or synthetic account ID as invalid.
- Treat suspended, contract-ended, or otherwise ineligible accounts as a failure unless the template asks for a billing-specific route.
- If an active outage matches service area and service type, route to outage wait and capture the outage ID.
- If diagnostics and troubleshooting show a recoverable issue, mark the ticket resolved and use the auto-troubleshooting route.
- If the evidence points to physical damage, backbone capacity, or provisioning drift that does not clear, escalate to the matching team in the current template.
- Set `diagnostic_needed` true when diagnostics or troubleshooting are required to justify the decision.
- Derive symptom flags from the report and evidence, not from the ticket label alone.

## Contact-Center Cases

- Read the current template before deciding, because some variants ask for `permission`, `bill_id`, and charge fields while others ask for data refuel and carrier-update fields.
- Prefer the least invasive action that matches the device or line evidence.
- If SIM status is missing or absent, use SIM reseating.
- If the line is suspended for an overdue bill, use the billing-recovery path and include the bill amount.
- If line roaming is disabled, enable line roaming and treat it as a carrier-side update.
- If line roaming is enabled but phone roaming is off, toggle roaming on the device.
- If MMS or photo messaging is blocked and storage permission is missing, grant the messaging permission before anything else.
- For slow data, check blockers in this order: data saver, VPN, network mode, then mobile data disabled.
- If the usage limit was reached and the customer accepts refueling, calculate the charge from the plan refuel price and the requested gigabytes.

## Enterprise Export Complaints

- Use the incident, enterprise account, export-run, message, and SLA records together.
- Set the failure window from the first failed run date through the last consecutive failed run date.
- Set `backfill_days` to the number of failed days that must be regenerated.
- Use the strongest concise cause label supported by the runs and messages.
- Use `ARCHIVED_ALERT_ROUTE` when the operational alert evidence exists only in an archive or retired alert channel.
- Keep owner fields aligned with the incident and account records.
- Preserve the share-permission order from the requirements and give each person the least privilege that fits the request.
- Mark `NEEDS_FINANCE_REVIEW` when the package still needs credit approval, `NEEDS_ENGINEERING_REVIEW` when the root cause or remediation is not yet settled, `UNDER_INVESTIGATION` when key evidence is still missing, and `READY_TO_SEND` only when the package is complete.

## Output Rules

- Return only JSON.
- Use exact enum values from the current template.
- Keep numeric formatting exact: two decimals for currency, one decimal for refuel gigabytes.
- Do not invent IDs, dates, charges, or permissions that are not supported by evidence.
