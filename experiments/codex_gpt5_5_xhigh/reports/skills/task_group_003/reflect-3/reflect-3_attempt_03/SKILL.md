---
name: reflect-3
description: Use this skill for CRM/support-console service-ticket tasks that require reading staged payloads, querying support records, choosing operational actions/statuses, and returning strict JSON. Trigger for offline service-ticket batches, mobile support queues, enterprise export complaints, queue-quality or SLA handoff reviews, mobile-data recovery worklists, and any task asking for routing/status/action decisions from customer, line, bill, plan, device, outage, diagnostic, troubleshooting, export-run, incident, SLA, or owner records.
---

# CRM Service-Ticket SOP

## Core Workflow

1. Read the task prompt, every staged payload named by the prompt, and the answer template before querying records. Treat the payload as the source of item IDs, order, and required output fields.
2. Use the support-console base URL provided by the harness or access note when it differs from a default localhost URL in the prompt. Do not inspect environment source code.
3. Build a private evidence matrix for each payload item:
   - item ID and payload facts
   - console records consulted
   - blocker checks
   - selected operation/status
   - follow-up operation
   - summary bucket/count impact
4. Query by exact IDs first. When a list endpoint omits related collections, use the console search endpoint with the exact ticket, case, incident, or account ID to reveal diagnostics, troubleshooting, messages, export runs, contracts, or other linked evidence.
5. Emit only JSON conforming to the answer template. Keep key names, nesting, array order, data types, null/empty-string conventions, enum spelling, date formats, and summary count names exactly as the template requests.

## Fixed Service Tickets

For ticket batches and queue-quality reviews, join each ticket to account records, active outages by service area/service type, diagnostics, troubleshooting, and any authentication/account status evidence.

Apply this routing order:

1. Missing or invalid account: return to intake/account correction. Do not perform service changes against an unmatched account.
2. Active area outage: attach or route to the outage, include the outage owner/ETA if the template asks, and keep the ticket pending outage restoration rather than closing it from local troubleshooting.
3. Account suspension, account hold, overdue billing, or contract/account state blocker: route to billing/reactivation/account recovery before technical remediation.
4. Authentication or account-recovery failure: route to identity/account recovery. Do not classify it as a network fault.
5. Diagnostics root cause and troubleshooting result:
   - Voice profile stale with successful profile refresh and improved post-checks: ready to close or resolved.
   - Provisioning/configuration drift: perform profile refresh/provisioning sync and verify post-checks before closure.
   - Backbone/capacity root cause that remains degraded after reroute: network escalation, not closure.
   - Fiber drop damage, signal loss, physical line damage, or poor post-line-test metrics: field dispatch or physical plant escalation.
6. If post-troubleshooting metrics remain far below subscribed service or latency/jitter remain poor, keep the item open for escalation or verification even if a step was attempted.

## Mobile Queue And Data Recovery

For mobile cases, join case -> customer -> line -> bill -> plan -> device. Check commercial and carrier state before device toggles.

Use this operation logic:

- Suspended line with overdue bill: collect the amount due, then reactivate/verify service.
- Suspended line from ended contract: route to renewal/contract reactivation, not device troubleshooting.
- Missing SIM: replacement SIM or SIM activation flow. Locked SIM/PIN: unlock/PUK flow.
- Customer abroad with carrier/line roaming disabled: enable carrier roaming and verify roaming data.
- Customer abroad with carrier roaming enabled but phone roaming disabled: instruct/enable device roaming and verify data.
- Data used above plan allowance: add/refuel data. Calculate expected charge as `(data_used_gb - data_limit_gb) * data_refueling_price_per_gb`, rounded to money precision, when the template asks for a charge.
- Mobile data disabled on device: enable mobile data and verify a data session.
- Data saver enabled with slow data: disable data saver and rerun a speed test.
- Old network mode such as 3g-only: switch to the preferred current network mode and rerun speed test.
- VPN connected with poor speed: disconnect VPN and rerun speed test.
- MMS failures: distinguish missing app/storage permission from missing MMSC/APN profile; choose the specific permission or APN/MMSC repair and then retry MMS.

## Enterprise Export Complaints

For export complaints, identify the named enterprise account or incident from the complaint payload first; do not answer for every similar incident found by broad search.

Collect these evidence groups:

- Enterprise account: account name, tier, account owner, finance owner.
- Incident: incident ID, product, severity, status, received time, engineering owner.
- Export runs: failed run dates, run IDs, failure codes, exported counts, and first successful recovery run.
- Messages or internal notes: human-readable root-cause detail and remediation/backfill notes.
- SLA contract: credit trigger, credit percent, executive contact.

Derive the response package as follows:

- Failed export window is the consecutive failed run-date range tied to the incident, ending before the first successful recovery run.
- Root cause should combine the structured failure code with the explanatory message when available.
- SLA credit comes from the contract trigger and percent, not from severity alone.
- Owners should include account, engineering, finance, and executive/customer contacts when present.
- Response artifacts normally include incident summary, failed-run table/window, root-cause statement, SLA credit note, owner/next-action list, and customer response text only when the template asks for those artifacts.

## Summary And Audit Habits

- Preserve payload order in result arrays unless the template explicitly asks for sorting.
- Reconcile every summary count against the number of payload items before final output.
- Count categories from final classifications, not from raw records. An active outage, invalid account, billing block, or auth block can override diagnostic noise.
- Keep private audit notes while working, but include them in the JSON only if the answer template has an evidence, rationale, note, or audit field.
- Use exact IDs from the console. Do not normalize, abbreviate, or invent account/ticket/case IDs.
- Use ISO date strings from records. Use numeric money values when the template expects numbers.

## Common Pitfalls

- Do not let ticket/case summaries alone decide the action; confirm with account, line, bill, plan, device, outage, diagnostic, or export-run evidence.
- Ignore generated/filler records unless the staged payload names them.
- Do not answer all records from a broad search. The payload defines the worklist.
- Distinguish carrier/line roaming from phone roaming; they lead to different operations.
- Distinguish data allowance exhaustion from device setting problems; they lead to charges versus configuration fixes.
- Do not close tickets simply because troubleshooting ran. Close only when blocker state is cleared and post-checks support closure.
- Avoid adding helpful-looking fields, markdown, explanations, or synonym keys to the final JSON. Strict templates may reject a substantively correct analysis when the shape or vocabulary is improvised.
