---
name: reflection-support-console-skill
description: Use this skill for support-console evaluation tasks involving service tickets, mobile support cases, mobile data recovery worklists, or enterprise export incident responses. It gives a concrete SOP for querying the shared API, mapping records to answer-template fields, applying outage/account/mobile/SLA business rules, and avoiding common support-console pitfalls.
---

# Support Console SOP

Use this skill when a task asks for structured JSON from the shared support console. The goal is exact operational classification, not a narrative answer.

## Ground Rules

- Return only JSON that conforms to `payloads/answer_template.json`.
- Preserve the order required by the template or input payload: ticket payload order, ascending case id order, or requirement-listed user order.
- Use the base URL supplied by the harness or task prompt. Check `/health` if unsure.
- Query only records needed for IDs in the task payload, plus directly linked records. Avoid broad list dumps because they can mix unrelated generated records with the target evidence.
- Prefer console evidence over customer wording. Customer text is a clue; ticket/case/line/device/plan/incident records decide the fields.

## API Pattern

Typical calls:

- Service tickets: `/api/tickets/<ticket_id>`, `/api/outages?service_area=<area>`, `/api/diagnostics/<ticket_id>`, `/api/troubleshooting/<ticket_id>`.
- Mobile cases: `/api/cases/<case_id>`, then `/api/lines/<line_id>`, `/api/devices/<device_id>`, and `/api/plans/<plan_id>` when data limits or charges matter.
- Enterprise export incidents: `/api/enterprise/incidents/<incident_id>`, `/api/enterprise/export-runs?incident_id=<incident_id>`, `/api/enterprise/messages?query=<client-or-cause-text>`, and `/api/enterprise/sla/<enterprise_account_id>`.

If a task asks for billing fields, use the task-permitted bill or case evidence. Do not substitute the plan monthly price for an overdue balance; overdue charges are outstanding bill amounts and may differ from the plan price.

## Service Ticket Decisions

For each ticket, fetch the ticket first to get `service_area`, `service_type`, `account_id`, and subscribed speed. Then check active outages for that service area before interpreting diagnostics.

Decision priority:

1. Active outage matching the ticket service type:
   Use `PENDING_ACTION`, `OUTAGE_WAIT`, the outage id, team `NONE`, diagnostic false, and all issue booleans false. Count it as a customer-wait ticket.
2. Invalid or ineligible account:
   Invalid intake or missing account is `FAILED` with `INVALID_ACCOUNT`. Account hold or ineligible service is `FAILED` with `INELIGIBLE_ACCOUNT`; do not route it to Accounts Payable unless the template has an explicit overdue-suspension blocker/team field.
3. Suspension or auth blockers:
   Overdue/fraud suspension is `FAILED`; use `OVERDUE_SUSPENSION` or `FRAUD_SUSPENSION`, and route overdue items to `ACCOUNTS_PAYABLE` when a `route_team` field exists. Authentication failure is `FAILED`, `AUTH_FAILED`, team `NONE`, and diagnostic false. Do not escalate auth failures to Tier 2.
4. Technical diagnostics:
   Use diagnostic flags for technical routes only. As a guide, high latency is around 100 ms or more, stability problems include high jitter around 30 ms or more, and bandwidth issues are usually below about 80 percent of subscribed speed. Use original diagnostic symptoms for `latency_issue`, `stability_issue`, and `bandwidth_issue`, not post-fix metrics.
5. Remediation result:
   If troubleshooting/profile/provisioning refresh resolves the symptoms, choose `RESOLVED`, `AUTO_TROUBLESHOOTING` when present, and team `NONE`.
6. Escalation mapping:
   `FIBER_DROP_DAMAGE`, `SIGNAL_LOSS`, or physical line faults go to `FIELD_OPS`. `BACKBONE_CAPACITY` goes to `NETWORK_ENGINEERING`. `PROVISIONING_STALE` or a provisioning mismatch after move goes to `TIER2_SUPPORT`. Use `ESCALATED` for these unresolved technical blockers.

Queue `key_blocker` mapping:

- Active matching outage: `ACTIVE_OUTAGE`
- Invalid/missing account: `INVALID_ACCOUNT`
- Auth failure: `AUTH_FAILED`
- Overdue or fraud suspension: `OVERDUE_SUSPENSION` or `FRAUD_SUSPENSION`
- Backbone capacity: `NETWORK_CAPACITY`
- Provisioning stale: `PROVISIONING_STALE`
- Fiber/signal/line damage: `PHYSICAL_LINE_FAULT`
- Resolved refresh/profile cases: `NONE`

Summaries are simple counts of final statuses and route teams. Count route teams even when the status is `FAILED`, but only when the decision actually assigns a non-`NONE` team.

## Mobile Case Decisions

For every case, fetch the case, line, device, and plan. Decide from the first concrete blocker in this priority order:

1. Suspended line with overdue bill:
   `SEND_PAYMENT_REQUEST` followed by `RESUME_LINE_REBOOT`, route `BILLING_RECOVERY`, include the bill id and the outstanding charge amount.
2. No service from SIM/device state:
   Missing SIM means `RESEAT_SIM`. Airplane mode means `TOGGLE_AIRPLANE_MODE`. These are usually `SELF_SERVICE`.
3. Mobile data disabled:
   `TOGGLE_MOBILE_DATA`, route `DEVICE_SETTING_FIX` or `SELF_SERVICE` depending on the template.
4. Roaming:
   If the customer is abroad and line-level roaming is disabled, use `ENABLE_LINE_ROAMING`, set carrier update true when that field exists, and route `CARRIER_UPDATE`. If line roaming is enabled but phone roaming is off, use `TOGGLE_ROAMING` as a self-service/device setting fix.
5. Data limit/refuel:
   If `line.data_used_gb` exceeds `plan.data_limit_gb` and the customer accepts a refuel, use `REFUEL_DATA`. Charge is `accepted_refuel_gb * plan.data_refueling_price_per_gb`; do not suggest a plan change when the payload says the customer does not want one.
6. Slow data settings:
   VPN connected -> `DISCONNECT_VPN`; data saver on -> `TOGGLE_DATA_SAVER`; old network mode such as `3g_only` -> `SET_NETWORK_MODE`.
7. MMS/photo messaging:
   Missing SMS/storage permission -> `GRANT_MESSAGING_PERMISSION` and set `permission` to `sms`, `storage`, or `sms_and_storage`. Missing APN/MMSC evidence points to `RESET_APN_REBOOT`.
8. Human transfer:
   Use `TRANSFER_HUMAN` only when the records show no supported self-service, billing, carrier, data recovery, or device-setting fix.

Use `NO_ACTION` for secondary action unless a real follow-up is required. Queue/worklist summaries count by final route, and total charge is the sum of customer charges.

## Enterprise Export Response Decisions

Start from the complaint's incident id or client name. Fetch the incident, export runs, client/cause messages, and SLA contract.

Field rules:

- `incident_id`, `enterprise_account_id`, `severity`, `engineering_owner`, and `account_owner` come from the incident record.
- `failure_window` is the consecutive failed export-run range: earliest failed date, latest failed date, and count of failed days.
- `backfill_days` normally equals the failed-day count when a later success or explicit message confirms recovery/backfill.
- `root_cause_category` should be a concise human phrase from the failure code plus message evidence, such as "stale credential after rotation"; do not return raw enum text when the template asks for a category.
- `contributing_alert_issue` is `ARCHIVED_ALERT_ROUTE` when supporting evidence is in an archive/alerts archive channel or indicates alert routing was missed; otherwise use `NONE` unless evidence is ambiguous.
- `sla_credit_percent` comes from `/api/enterprise/sla/<enterprise_account_id>` or a client-specific account message.
- If an SLA credit is owed, set `response_status` to `NEEDS_FINANCE_REVIEW` even when engineering evidence is complete. Use `READY_TO_SEND` only when no finance/engineering review remains.

Naming conventions:

- `channel_name`: lowercase hyphen slug of the client's legal name, including suffixes like `inc` when present.
- `evidence_folder`: client legal name plus month/year investigation, in title case.
- `report_title`: client legal name plus "Export Failure - Resolution Report".
- `share_permissions`: preserve the users listed in requirements. Use explicit permissions if supplied; if only two collaborators are listed with no roles, the support-console convention is first user `view`, second user `edit`.

## Common Pitfalls

- Do not let an active outage also produce latency/stability/bandwidth flags.
- Do not mark account holds, overdue suspensions, invalid accounts, or auth failures as `PENDING_ACTION`; they are failures unless a template says otherwise.
- Do not route auth failures to Tier 2.
- Do not use generated/noise diagnostics to override a clear outage, account, suspension, auth, or provisioning clue.
- Do not estimate overdue bill charges from plan price.
- Do not return raw enterprise failure codes when a human root-cause category is requested.
- Do not mark enterprise SLA-credit responses ready to send before finance review.
