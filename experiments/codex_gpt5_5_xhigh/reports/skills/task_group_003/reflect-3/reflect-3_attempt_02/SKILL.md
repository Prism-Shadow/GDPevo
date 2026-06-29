---
name: reflect-3
description: Resolve CRM/support-console service-ticket tasks that require looking up live account, ticket, mobile line/device/bill/plan, outage, diagnostic, export incident, or enterprise message records and returning strict JSON decisions. Use this skill whenever a prompt asks for support operations triage, queue quality review, mobile-data recovery, service-ticket routing, SLA handoff, enterprise export complaint response packages, or summary counts from a support console.
---

# Reflect-3 CRM Support SOP

Use this skill for support-console tasks where the answer must be inferred from CRM records rather than from the intake text alone.

## Core Workflow

1. Read the prompt, payload, and answer template first.
2. Use the support-console base URL supplied by the task or environment. If the prompt mentions a local default but the harness provides a different shared console URL, use the harness URL.
3. For every listed item, retrieve the authoritative records before deciding:
   - Fixed-line tickets: ticket, account, active outages, then diagnostics only if still needed.
   - Mobile cases: case, line, device, plan, and bill.
   - Enterprise export complaints: enterprise account, incident, export runs, and internal messages.
4. Preserve the payload order unless the template explicitly says to sort by an ID.
5. Return only JSON conforming to the answer template. Do not include explanations, comments, Markdown, or extra keys.
6. After filling decisions, recompute all summary counts from the decisions, not from memory.

## Fixed-Line Service Tickets

Resolve high-level blockers before diagnostics:

- Missing account record: mark the ticket failed/invalid. Use no escalation team and do not require diagnostics.
- Authentication failure or unrecovered account recovery: mark failed/auth failed. Use no escalation team and do not require diagnostics.
- Suspended account from overdue billing or account hold: mark failed/ineligible or overdue suspension. Route to `ACCOUNTS_PAYABLE` when a team field is available. Do not require diagnostics.
- Active outage matching both service area and service type: mark pending/customer-wait or outage wait. Use the matching outage ID when requested, no escalation team, and no diagnostics.
- Only run diagnostics after the ticket survives the account, auth, suspension, and outage checks.

Diagnostic routing:

- `VOICE_PROFILE_STALE`: usually a resolved self-contained/profile refresh outcome, with diagnostics required, no blocker, and no handoff team.
- `CONFIGURATION_DRIFT`: usually auto-troubleshooting/resolved with no handoff team.
- `PROVISIONING_STALE`: route to `TIER2_SUPPORT` as an escalation or provisioning stale blocker, especially after moves or service reprovisioning.
- `BACKBONE_CAPACITY`: route to `NETWORK_ENGINEERING` with a network capacity blocker.
- `FIBER_DROP_DAMAGE` or `SIGNAL_LOSS`: route to `FIELD_OPS` with a physical line fault blocker.

Metric flags and blockers:

- Treat latency above roughly 100 ms as a latency issue when diagnostics are in scope.
- Treat jitter around 40 ms or higher, or physical/signal-loss causes, as a stability issue. Jitter in the low 30s alone is not enough.
- Treat measured bandwidth far below the subscribed rate as a bandwidth issue when diagnostics are in scope.
- For outage, invalid-account, auth-failed, or suspended-account routes, leave diagnostic issue flags false unless the template explicitly asks for historical diagnostic facts.

Summary habits:

- Count pending/customer-wait tickets only from active outage wait decisions.
- Team summary counts are counts of decisions routed to that team, not counts of all possible causes.
- Status counts must match the final status assigned to each listed ticket.

## Mobile Support Cases

Lookup order: case -> line -> device -> plan -> bill. Use the smallest operation that directly addresses the observed setting, status, or allowance issue.

Common actions:

- Missing SIM or device reports no SIM: `RESEAT_SIM`.
- Airplane mode on: `TOGGLE_AIRPLANE_MODE`.
- Mobile data disabled: `TOGGLE_MOBILE_DATA`.
- Phone roaming disabled while the line is roaming-enabled: `TOGGLE_ROAMING`.
- Customer abroad, phone roaming on, but line roaming disabled: `ENABLE_LINE_ROAMING`, carrier update required, route `CARRIER_UPDATE`.
- Line suspended for overdue bill: `SEND_PAYMENT_REQUEST`, then `RESUME_LINE_REBOOT`; include bill ID and overdue amount, route `BILLING_RECOVERY`.
- Data usage exceeds the plan limit and the customer accepts a refuel: `REFUEL_DATA`; charge accepted GB multiplied by the plan refuel price per GB; route `DATA_RECOVERY`.
- Data saver enabled with slow data: `TOGGLE_DATA_SAVER`.
- Old or limited network mode such as `3g_only`: `SET_NETWORK_MODE`.
- VPN connected with slow data: `DISCONNECT_VPN`.
- Messaging/MMS failure from missing app permission: `GRANT_MESSAGING_PERMISSION` and set `permission` to `sms`, `storage`, or `sms_and_storage` based on the missing device permissions.
- MMS/APN profile problems with no permission issue: use the APN reset/reboot action when available.

Mobile output rules:

- Use `NO_ACTION` for secondary action unless the workflow specifically requires a follow-up, such as resuming a line after payment.
- Put `0.0` data refuel GB and `0.00` charge when not applicable.
- `carrier_update_required` is true only for carrier/line-side changes, not ordinary phone setting toggles.
- Count final routes in the summary: data recovery, carrier update, device setting fix, billing recovery, self-service, or human transfer according to the template labels.
- Total estimated customer charge is the sum of explicit charges only.

## Enterprise Export Complaint Packages

Use console evidence in this order:

1. Match the client to an enterprise account.
2. Match the complaint reference to the incident.
3. Read export runs for that incident. The failed run dates define the failure window; count consecutive failed days.
4. Use the next successful run or backfill evidence to confirm recovery/backfill. Backfill days normally equal the failed export days requiring recovery.
5. Read internal messages for root-cause details, SLA credit terms, alert routing issues, and owner context.
6. Use incident fields for severity and engineering owner; use account fields for account owner and finance owner.

Enterprise decision rules:

- Root cause should be concise but evidence-based: combine the export failure code with internal-message detail when the message explains the failure.
- If the relevant alert or root-cause message was posted only in an archive/archived alert channel, set the alert issue to `ARCHIVED_ALERT_ROUTE`.
- SLA credit percent must come from contract/account/internal-message evidence. Do not invent a credit from severity alone.
- Construct response artifacts from the payload naming requirements when no console artifact record exists:
  - Lowercase hyphen channel names should use a slugified client and incident/subject phrase.
  - Investigation folders should include the client and relevant incident/response date as requested.
  - Report titles should be human-readable and include the client plus export failure subject.
- Share permissions must include only the users requested by the payload, in the requested order. Use role evidence when available; otherwise choose conservative access aligned to the review purpose.
- Choose response status from missing work:
  - `READY_TO_SEND` only when root cause, failed window, backfill, credit handling, owners, artifacts, and permissions are all resolved.
  - `NEEDS_FINANCE_REVIEW` when SLA credit is present but finance approval/handling is not clearly complete.
  - `NEEDS_ENGINEERING_REVIEW` when root cause or backfill is not confirmed.
  - `UNDER_INVESTIGATION` when the incident remains unresolved and required evidence is still incomplete.

## Final JSON QA

Before returning:

- Compare every enum value to the answer template exactly.
- Preserve required ordering: payload order for ticket/worklist rows, ascending ID only when the template says so, and requested user order for permissions.
- Ensure booleans are real JSON booleans, not strings.
- Use empty strings for non-applicable IDs when the template asks for strings.
- Recalculate all summaries from the final decisions.
- Make sure no decision relies only on customer wording when console records contradict or refine it.
