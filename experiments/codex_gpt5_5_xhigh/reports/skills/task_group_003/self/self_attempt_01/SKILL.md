---
name: crm-service-ticket-sop
description: Use this skill for CRM/support-console tasks that ask Codex to resolve or classify support tickets, mobile service cases, queue snapshots, or enterprise export complaints using customer, account, line, bill, plan, device, outage, diagnostic, SLA, or incident records. Trigger whenever the task says to use a shared support console API and return JSON matching an answer template.
---

# CRM Service Ticket SOP

## Operating Loop

1. Read the prompt, every input payload, and the answer template before querying records.
2. Use the support-console base URL from the harness/prompt; if a staged `environment_access.md` provides `GDPEVO_ENV_BASE_URL`, use that. Check `/health` only to confirm the service is reachable.
3. Do not inspect local environment source, evaluator files, train answers, judge feedback, or other attempts. Resolve from payloads plus support-console records.
4. Prefer targeted lookups for known IDs:
   - `/api/tickets/<ticket_id>`, `/api/accounts/<account_id>`, `/api/diagnostics/<ticket_id>`
   - `/api/cases/<case_id>`, `/api/lines/<line_id>`, `/api/devices/<device_id>`, `/api/customers/<customer_id>`
   - `/api/bills/<bill_id>`, `/api/plans/<plan_id>`
5. Use `/api/search?q=<exact id or keyword>` to gather cross-record evidence. Search ticket IDs, account IDs, service areas, incident IDs, enterprise account IDs, client names, products, channels, owners, and important failure keywords. Filter search results back to the exact case/account/incident so nearby generated records do not leak into the decision.
6. Return only JSON conforming to the answer template. No prose, markdown, comments, or extra keys.

## Output Conventions

- Preserve the ordering requested by the template: payload order for ticket decisions, ascending `case_id` for case decisions, and listed requirement order for share permissions.
- Use exact enum spellings from the template. Use booleans as booleans, numbers as numbers, empty strings for non-applicable IDs, `NONE` for non-applicable enum fields, and `NO_ACTION` for unused secondary actions.
- Format money and totals to two decimal places as numeric values; format GB values to one decimal place when requested.
- Include every summary key from the template, even when the count is zero. Compute summaries from the final emitted decisions, not from the input notes.
- Keep an evidence scratch table while working: input ID, records fetched, decisive evidence, chosen status/action/route, charge, and summary bucket. This prevents count drift.

## Fixed-Line Ticket Rules

For each ticket, gather ticket, account, diagnostics, troubleshooting, and any active outage returned by searching the ticket `service_area`.

Apply blockers first:
- Missing account record: `FAILED`, invalid-account blocker/route, no escalation team.
- Account authentication failure or failed recovery: `FAILED`, auth-failed blocker/route, no technical escalation.
- Suspended or ineligible account: use the template's billing/ineligible path. Prefer `ACCOUNTS_PAYABLE` when a team is required; use an overdue/fraud suspension blocker when available. Do not treat account suspension as a network fault.
- Active outage matching the ticket service area and service type: `PENDING_ACTION`, route `OUTAGE_WAIT`, include `outage_id`, set customer-wait counters, and avoid duplicating with a network escalation.

Then classify technical evidence:
- Successful troubleshooting with acceptable post metrics generally resolves via `AUTO_TROUBLESHOOTING`. Configuration/profile/provisioning refreshes can resolve when post latency/jitter/bandwidth are materially improved.
- Physical line evidence such as `FIBER_DROP_DAMAGE`, `SIGNAL_LOSS`, or physical-line-fault language escalates to `FIELD_OPS`.
- Backbone/capacity evidence escalates to `NETWORK_ENGINEERING`.
- Stale voice profile or simple provisioning drift routes to `TIER2_SUPPORT` only when automation did not sufficiently recover; otherwise mark resolved.
- Ignore vague `GENERATED_NOISE` as a root cause unless other records support it.

Issue flags:
- `latency_issue`: high latency or latency-rooted complaint/diagnostic, especially if still high after troubleshooting.
- `stability_issue`: high jitter, packet loss, signal loss, intermittent/drop-call evidence, or physical-line root cause.
- `bandwidth_issue`: measured bandwidth materially below subscribed speed, or speed/throughput complaint supported by diagnostics.
- `diagnostic_needed` / `diagnostic_required`: true when the ticket still needs diagnostic evidence for handoff or when unresolved technical routing depends on it; false for invalid accounts, auth failures, known active outages, billing blockers, and already-resolved automation.

## Mobile Case Rules

For each case, gather the case, line, device, customer, current bill, and plan. Bill IDs commonly follow the customer/case number (`BILL-<number>`), but confirm with the API. Use plan data limit and refuel price for charges.

Prioritize actions:
- Suspended line with `OVERDUE_BILL`: `SEND_PAYMENT_REQUEST`, then `RESUME_LINE_REBOOT`; include the bill ID, amount due, and `BILLING_RECOVERY`.
- Suspended line for fraud or unclear reason: `TRANSFER_HUMAN` / `HUMAN_TRANSFER`.
- No service: airplane mode on -> `TOGGLE_AIRPLANE_MODE`; missing/ejected SIM -> `RESEAT_SIM`; otherwise use `TRANSFER_HUMAN` if records do not show a self-service fix.
- Mobile data disabled on device -> `TOGGLE_MOBILE_DATA`.
- Traveling/abroad: phone roaming disabled -> `TOGGLE_ROAMING`; carrier/line roaming disabled -> `ENABLE_LINE_ROAMING` and mark carrier update required. If both are disabled, carrier enable is primary and device roaming can be secondary.
- Data usage at/over plan limit with accepted refuel -> `REFUEL_DATA`; `data_refuel_gb` is the accepted GB and charge is accepted GB times plan refuel price.
- Slow data: data saver on -> `TOGGLE_DATA_SAVER`; old network mode such as 3G-only -> `SET_NETWORK_MODE`; VPN connected -> `DISCONNECT_VPN`; otherwise transfer if no record-supported device fix exists.
- MMS/photos: missing SMS or storage permission -> `GRANT_MESSAGING_PERMISSION` and set `permission` to `sms`, `storage`, or `sms_and_storage`; missing MMSC/APN evidence -> `RESET_APN_REBOOT`.
- Wi-Fi calling specific issue -> `TOGGLE_WIFI_CALLING`.

Route mobile cases from the operation actually chosen:
- Device toggles/settings/permissions usually route to `SELF_SERVICE` or `DEVICE_SETTING_FIX`.
- Refuels route to `DATA_RECOVERY`.
- Carrier-side enablement routes to `CARRIER_UPDATE`.
- Payment/resume routes to `BILLING_RECOVERY`.
- Unclear, fraud, or unsupported states route to `HUMAN_TRANSFER`.

## Enterprise Export Complaint Rules

Build the response package from incident, enterprise account, export runs, messages, SLA contract, owners, folders/channels, and response requirements.

- Search by incident ID first, then enterprise account/client name and product. Use export runs tied to the same `incident_id` and `enterprise_account_id`.
- Failure window is the consecutive failed run dates: min date, max date, and count. `backfill_days` should match failed days only when a later success or message confirms backfill/recovery; otherwise leave the response under review if the template allows.
- Infer `root_cause_category` from failure codes plus message evidence. Keep it concise and operational, such as stale credential/configuration, scheduler secret mismatch, pipeline capacity, or unknown.
- Set `contributing_alert_issue` to `ARCHIVED_ALERT_ROUTE` when the relevant alert evidence is in an archive/stale alert channel; use `NONE` when the route was normal, `UNKNOWN` when evidence is missing.
- Pull SLA credit from the SLA contract only if the trigger matches the observed failure. If finance approval or credit eligibility is ambiguous, use a finance-review response status.
- Owners come from incident/account records. Preserve owner user IDs exactly.
- Generate artifact names from requirements: lowercase hyphen channel names, client/date investigation folder names, and a client export failure report title.
- `READY_TO_SEND` requires supported root cause, failure window, backfill/recovery, SLA credit, owners, channel/folder/title, and permissions. Otherwise choose the narrowest review status: finance review for credit ambiguity, engineering review for unresolved cause/backfill, or under investigation for broad evidence gaps.

## Summary Habits

- Count statuses independently from teams/routes; one ticket can contribute to both a status count and a team count.
- Customer-wait counts usually include active outage waits and customer/payment/carrier actions, not internal engineering or field escalations.
- Mobile summaries: count refuel cases when `REFUEL_DATA` is primary or secondary; count carrier updates when the route/update flag says carrier work is required; count device fixes from self-service setting actions; sum only customer charges actually emitted.
- Before final output, compare array lengths to input worklists, verify order, verify all enum values are allowed by the template, and recalculate every summary total from the decision rows.

## Pitfalls

- Do not answer from the customer narrative alone. The decisive evidence is often in account status, service-area outage search, diagnostics, troubleshooting, device settings, or SLA messages.
- Do not let broad search results from similar generated IDs contaminate a case. Match exact ticket/case/account/incident IDs.
- Do not mark active outages as resolved because troubleshooting exists; outage wait wins when the outage matches service area and service type.
- Do not escalate billing, auth, invalid-account, or suspension blockers as network failures.
- Do not omit empty/non-applicable fields. Templates expect explicit empty strings, zeroes, `NONE`, or `NO_ACTION`.
