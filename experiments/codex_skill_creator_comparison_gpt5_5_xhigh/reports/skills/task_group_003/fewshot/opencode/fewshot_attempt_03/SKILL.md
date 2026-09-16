---
name: support-console-resolution
description: Resolve structured support-console API tasks that ask Codex to classify service tickets, choose contact-center or mobile-data recovery operations, or prepare enterprise export-incident response JSON. Use for prompts with a shared support console base URL, payloads/answer_template.json, ticket batches, queue snapshots, mobile case worklists, diagnostics, outages, customer/line/device/bill/plan records, enterprise export runs, SLA credits, or response packages.
---

# Support Console Resolution

Use this skill to produce the exact JSON object requested by a support-console task. The tasks are evidence reconciliation problems: payload files identify the work items, the API contains the authoritative records, and `answer_template.json` defines the required schema and enum vocabulary.

## Required Workflow

1. Read the prompt, every file in `payloads/`, and the current task's environment access note. Use only the listed base URL and allowed endpoints.
2. Read `payloads/answer_template.json` first. Preserve required item order from the payload unless the template explicitly says to sort.
3. Gather records from the API before deciding. Prefer exact ID lookups; use `/api/search?q=<id-or-client-name>` when an account or contact-center case does not have a direct allowed endpoint.
4. Optionally run the bundled collector:

   ```bash
   python skill/scripts/collect_support_console_evidence.py \
     --base-url "$TASK_ENV_BASE_URL" \
     --payload-dir payloads \
     --output evidence.json
   ```

   If there is no `TASK_ENV_BASE_URL` variable, pass the base URL from the environment access note. The collector writes evidence only; it does not create the final answer.
5. Fill only fields present in the answer template. Use empty strings, `0.0`, `false`, and `NONE` for non-applicable fields when the template expects those sentinel values.
6. Return only valid JSON. Do not include Markdown, commentary, citations, or evidence notes in the final response.

## Evidence Checklist

For ticket batches or queue snapshots, gather for each ticket:

- Payload row and `/api/tickets/{ticket_id}`.
- Account state through `/api/search?q=<account_id>`; select the `accounts` record when present.
- Active outages from `/api/outages` matching the ticket `service_area` and `service_type`.
- `/api/diagnostics/{ticket_id}` and `/api/troubleshooting/{ticket_id}` unless a preliminary blocker makes diagnostics irrelevant.

For mobile/contact-center case queues or worklists, gather for each case:

- Case record. If a contact-center direct endpoint is unavailable or ambiguous, use `/api/search?q=<case_id>` and select the `cases` record.
- Customer, line, device, plan, and all bills for the case's customer.
- Any customer preferences embedded in the payload, especially accepted data refuel amounts.

For enterprise export complaints, gather:

- Incident ID, client name, product, required fields, and permission users from the payloads.
- Enterprise incident, enterprise account, export runs, related messages, and SLA record.
- Use message search by client/product/root-cause terms to find operational notes that are not directly linked by incident ID.

## Ticket Rules

Apply preliminary blockers before diagnostics:

- No matching account record for the payload account ID: `FAILED`; use `INVALID_ACCOUNT` when the template has `key_blocker`, or `INVALID_ACCOUNT`/`INELIGIBLE_ACCOUNT` according to the available `resolution_route` enum.
- Suspended account or line: `FAILED`. If the template supports blockers and the evidence says overdue, use `OVERDUE_SUSPENSION` with `ACCOUNTS_PAYABLE`; otherwise use the template's ineligible-account route.
- Authentication recovery or last login failure: `FAILED` with `AUTH_FAILED`.
- Active matching outage: `PENDING_ACTION`; no diagnostics required; include the outage ID if the template has an `outage_id` field.

When diagnostics apply:

- Set diagnostic-required fields to `true` only for tickets that reached diagnostics/troubleshooting.
- Mark latency issues when diagnostic latency is about 100 ms or higher.
- Mark stability issues when jitter is about 30 ms or higher, or the diagnostic root cause indicates signal loss, capacity, provisioning, or line instability.
- Mark bandwidth issues when measured bandwidth is materially below the ticket's subscribed Mbps.
- Treat troubleshooting as successful when post-check latency is below about 100 ms, jitter below about 30 ms, and bandwidth is close to the subscribed rate.

Resolution mapping:

- Successful troubleshooting: `RESOLVED`, no route team, `AUTO_TROUBLESHOOTING` when that route field exists.
- Physical line, fiber, drop damage, or signal-loss causes: `ESCALATED` to `FIELD_OPS`; blocker `PHYSICAL_LINE_FAULT` when available.
- Backbone or network-capacity causes: `ESCALATED` to `NETWORK_ENGINEERING`; blocker `NETWORK_CAPACITY`.
- Stale provisioning causes: `ESCALATED` to `TIER2_SUPPORT`; blocker `PROVISIONING_STALE`.
- If post-troubleshooting metrics remain bad and no more specific cause is available, escalate to the most specific team implied by root cause; otherwise use `TIER2_SUPPORT`.

Compute summaries from the decisions after all rows are filled. Count status fields exactly as emitted. Count route-team totals only for route-team fields present in the template, and count customer-wait tickets as outage-driven `PENDING_ACTION` rows.

## Mobile and Contact-Center Rules

Use this precedence order so a clear account or line blocker wins over lower-level device symptoms:

1. Suspended line for overdue billing: `SEND_PAYMENT_REQUEST`; `RESUME_LINE_REBOOT` as follow-up when available; include the overdue bill ID and amount; route `BILLING_RECOVERY`.
2. Messaging/MMS failures:
   - Missing SMS and/or storage permission: `GRANT_MESSAGING_PERMISSION`; set `permission` to `sms`, `storage`, or `sms_and_storage`.
   - Missing MMS/APN configuration: use `RESET_APN_REBOOT` when the template allows it; otherwise transfer.
3. No-service failures:
   - Missing SIM: `RESEAT_SIM`.
   - Airplane mode on: `TOGGLE_AIRPLANE_MODE`.
   - No clear self-service device setting and no account blocker: use the safest allowed network reset action, then transfer only if no listed action fits.
4. Roaming/mobile-data failures while abroad:
   - Line roaming disabled: `ENABLE_LINE_ROAMING`, mark carrier update required when that field exists, route `CARRIER_UPDATE`.
   - Device roaming disabled while the line allows roaming: `TOGGLE_ROAMING`, self-service/device-setting route.
5. Data-limit exhaustion:
   - If line usage meets or exceeds plan limit and payload preferences include an accepted refuel amount, choose `REFUEL_DATA`, set the GB amount, and compute charge as accepted GB times plan refuel price.
   - If refuel requires customer consent that is not present, transfer to a human.
6. Device setting slow-data/no-data fixes:
   - VPN connected: `DISCONNECT_VPN`.
   - Data saver on: `TOGGLE_DATA_SAVER`.
   - Old or restricted network mode: `SET_NETWORK_MODE`.
   - Mobile data disabled: `TOGGLE_MOBILE_DATA`.

For fields that are not part of the current template, do not invent them. For route summaries, count by emitted `final_route`: self-service/device-setting fixes, billing recoveries, carrier updates, data refuel cases, human transfers, and total estimated charge as requested.

## Enterprise Export Response Rules

1. Identify the incident from the complaint or requirements. Use the incident record for severity, owners, enterprise account ID, product, and current status.
2. Match export runs by incident ID first, then by enterprise account and product if needed. The failure window is the contiguous set of failed run dates tied to the incident; `failed_days` is its count. `backfill_days` normally matches the number of failed days unless explicit evidence says otherwise.
3. Derive the root-cause category from failure codes plus operational messages. Prefer a concise lowercase human phrase over a raw code; include the key mechanism from messages when it changes the meaning.
4. Set `contributing_alert_issue` to `ARCHIVED_ALERT_ROUTE` when relevant alert evidence is in an archive/archived alert channel instead of an active alert path. Use `NONE` when alert routing is normal and `UNKNOWN` only when evidence is insufficient.
5. Get SLA credit from the SLA endpoint or explicit account-escalation messages. If a nonzero credit is owed, choose `NEEDS_FINANCE_REVIEW` unless requirements say finance approval has already happened. If technical evidence is still unresolved, choose engineering review or investigation instead of ready-to-send.
6. Use account and incident records for account owner, engineering owner, and finance owner. Build names requested by the template from the client name and failure context:
   - Channel: lowercase hyphen slug of the client name.
   - Evidence folder: client name plus incident month/year plus an investigation label, matching the stated naming style.
   - Report title: client name plus export failure/resolution wording, matching the stated naming style.
7. Preserve `share_permissions` user order from requirements. Give finance/review-only owners view access unless requirements say otherwise; give response collaborators edit access. Use upload-only only when explicitly requested.

## Final Validation

Before answering, compare the object against `answer_template.json`:

- All required top-level keys are present.
- Every enum value appears in the template.
- IDs are copied from payload/API records, not inferred from neighboring examples.
- Item order matches the payload/template instruction.
- Summary counts equal the emitted decision rows.
- Number formatting matches the template, especially one-decimal GB values and two-decimal USD values.
