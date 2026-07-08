---
name: reflect-3
description: Use this skill for CRM/support-console service-ticket tasks that ask Codex to resolve batches of offline tickets, mobile support queues, mobile data recovery worklists, queue-quality handoffs, or enterprise export complaint response packages. It is especially relevant when the prompt provides payload files and an answer_template.json, asks for JSON-only output, or requires joining ticket/case records to accounts, outages, diagnostics, troubleshooting, customer lines, bills, plans, devices, enterprise incidents, export runs, messages, and SLA records.
---

# CRM Support Ticket SOP

## Core Workflow

1. Read the prompt, every payload file, and `payloads/answer_template.json` before querying records.
2. Use the support-console base URL supplied by the harness or environment. If the prompt names a localhost URL but a staged access note supplies a different base URL, use the supplied base URL.
3. Check `/health`, then query `/api/catalog` when available. The catalog is the fastest way to discover record endpoints and avoid guessing.
4. Fetch only the records needed to support the payload rows. Use list endpoints for joins and detail endpoints for individual IDs when they exist.
5. Join records by stable IDs:
   - Ticket work: ticket -> account -> matching outage by service area/service type -> diagnostics -> troubleshooting.
   - Mobile case work: case -> customer -> line -> bill -> plan -> device.
   - Enterprise export work: complaint/client/product/incident reference -> enterprise account -> incident -> export runs -> messages -> SLA.
6. Make the row-level decisions first. Compute all summaries from those finished rows; do not estimate summary counts independently.
7. Return only JSON conforming to the template. Preserve requested row order exactly.

## Output Conventions

- Use the exact enum spellings from the template.
- Use `""` for required empty strings and `0.0` or `0.00` for required zero numeric values. Do not use `null` unless the template explicitly allows it.
- Preserve payload order unless the template says to sort, such as ascending case ID.
- Include all required fields in every row, even when not applicable.
- Format money with two decimals and data-refuel quantities with the precision requested by the template.
- Recalculate summaries after any row-level change. Team counts count the row's selected route/team field, not the blocker category.

## Ticket Routing Rules

Apply blockers in this order, because earlier blockers usually make later diagnostics irrelevant:

1. **Invalid account**: If the account ID has no matching account record or is clearly invalid, classify as failed/invalid. Do not require diagnostics.
2. **Authentication failure**: If account authentication shows failed login/recovery and the issue is authentication-related, classify with the auth-failure blocker/route. Do not let generic diagnostics override this.
3. **Suspension or account hold**: Suspended accounts, overdue holds, and overdue bills route to billing/account recovery. Use pending action when the customer or billing process must clear the block; use the relevant bill or amount if requested.
4. **Active outage**: A matching active outage by service area and service type routes to outage wait/active outage. Include the outage ID when the template has one. Outage rows normally do not need diagnostics.
5. **Technical diagnostics**: For valid, active accounts with no outage, use diagnostics and troubleshooting evidence rather than relying on the report text alone.

Technical routing patterns:

- Configuration drift, stale voice profiles, and similar profile/provisioning issues that troubleshooting fixes can be resolved through auto troubleshooting or Tier 2, depending on the template's route choices.
- Physical line damage, fiber drop damage, signal loss, or line-work symptoms route to field operations.
- Backbone capacity, severe latency/jitter, or capacity root causes route to network engineering.
- Provisioning stale after a move or service change routes to Tier 2 or escalation unless post-troubleshooting metrics clearly normalize.
- Generated/noise root causes should not override stronger account, outage, auth, suspension, or named diagnostic causes.

When symptom booleans are required:

- Set latency from diagnostic latency, not just the customer's wording.
- Set stability from jitter, packet loss, signal loss, intermittent connectivity, or equivalent diagnostics.
- Set bandwidth from measured bandwidth below the subscribed service level.
- For invalid-account, suspended-account, auth-failure, and outage-wait rows, keep symptom booleans false unless the template specifically asks for diagnostic symptoms despite the blocker.

`diagnostic_required` or `diagnostic_needed` should be true for active technical issues that require diagnostic evidence, and false for terminal/admin blockers such as invalid account, outage wait, auth failure, or suspension.

For customer-wait summaries, count only rows whose selected route is explicitly outage/customer wait when the template names outage wait. Do not automatically count every pending action as customer wait.

## Mobile Case Rules

Check billing and line state before device settings:

- Suspended line with overdue bill: `SEND_PAYMENT_REQUEST`, then `RESUME_LINE_REBOOT` when a secondary action is requested. Include the overdue bill ID and amount. Route to billing recovery.
- Missing SIM or SIM not active for no-service reports: `RESEAT_SIM`.
- Airplane mode on: `TOGGLE_AIRPLANE_MODE`.
- Mobile data disabled: `TOGGLE_MOBILE_DATA`.
- Customer abroad with phone roaming off: `TOGGLE_ROAMING`.
- Customer abroad with phone roaming on but line roaming disabled: `ENABLE_LINE_ROAMING` and mark carrier update required.
- Data used over the plan limit: use `REFUEL_DATA` only when the payload or records show accepted refuel quantity. Charge accepted GB times the plan's per-GB refuel price. Respect "does not want plan change" preferences.
- Data saver enabled with slow data: `TOGGLE_DATA_SAVER`.
- Old or restricted network mode, such as `3g_only`, with slow data: `SET_NETWORK_MODE`.
- VPN connected with slow data: `DISCONNECT_VPN`.
- MMS/photo-send failures with missing messaging permission: `GRANT_MESSAGING_PERMISSION` and set the permission enum to the missing permission, such as `storage`, `sms`, or `sms_and_storage`.
- MMS failures with missing MMSC/APN evidence: `RESET_APN_REBOOT`.
- If no record-supported self-service, billing, carrier, or device-setting fix applies, route to human transfer.

For mobile summaries:

- Count data refuel cases only when the primary action is `REFUEL_DATA`.
- Count carrier updates only when the selected action requires carrier-side line updates.
- Count device setting fixes for local phone setting changes such as mobile data, roaming toggle, data saver, network mode, VPN, SIM reseat, airplane mode, and messaging permissions.
- Sum customer charges from row-level charge amounts, not from plan monthly prices.

## Enterprise Export Complaint Rules

Use the complaint email to identify the client, product, and approximate incident, then verify each field against enterprise support records.

- Enterprise account ID comes from the matched enterprise account, not from the incident number.
- Incident fields such as severity, engineering owner, account owner, and status come from the incident record.
- Failure window comes from consecutive failed export runs for the incident. Use the first and last failed run dates and count failed run days.
- Backfill days should match failed days only when export/message evidence supports manual backfill or a later successful recovery covering those days.
- Root cause should combine structured failure codes with message evidence. Prefer concise operational categories such as stale credential, stale scheduler secret, quota exhaustion, or similar record-supported causes.
- Mark an archived alert-route issue when the root-cause or alert evidence was posted only in an archive channel or otherwise indicates an archived alert path.
- SLA credit comes from the enterprise SLA record or explicit account-escalation evidence, not from severity alone.
- Response status should reflect the evidence state. Do not mark a package ready if the incident is still under investigation or required finance/engineering review evidence is missing.

For response artifacts:

- Follow the naming instructions exactly. Use lowercase hyphen slugs for channel and folder names, and human-readable title case for report titles.
- Derive names from the client, product, date, and artifact purpose only when the records do not provide an exact artifact name.
- Be consistent about whether to include legal suffixes such as "Inc." based on the requirement wording. If it says "client" and the client name includes the suffix, include it unless a naming example or existing artifact omits it.
- For share permissions, include only required users, preserve the requested user order, and choose permissions from role evidence or requirement text. Do not add inferred users.

## Final Audit

Before returning:

- Validate JSON syntax.
- Compare every output key against `answer_template.json`.
- Confirm row order and ID preservation.
- Confirm every enum value is valid.
- Confirm all empty fields use the template's empty convention.
- Recompute every summary count and total from row-level decisions.
- Scan for unsupported assumptions from prompt prose; every operational decision should trace to a console record or payload preference.
