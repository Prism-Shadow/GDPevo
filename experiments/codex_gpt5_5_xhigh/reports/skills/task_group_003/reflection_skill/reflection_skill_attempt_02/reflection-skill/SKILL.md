---
name: reflection-skill
description: Use this skill for task_group_003 support-console tasks: offline service ticket routing, queue-quality ticket classification, mobile support case recovery, mobile data worklists, and enterprise export-incident response packages. It gives executable API SOPs, output field rules, routing/status judgments, billing and SLA handling, and pitfalls learned from blind train-task comparison.
---

# Support Console Workflow SOP

## Scope And Ground Rules

Use the task prompt's base URL and answer template. In this eval the shared console is usually exposed as `http://127.0.0.1:8028`; if the prompt or harness gives a different base URL, use that.

Work only from the current task input and the allowed support-console API. Do not inspect task outputs, evaluators, notes, test data, or environment source. Preserve required ordering exactly: ticket payload order for ticket tasks, ascending `case_id` when requested for case queues.

Before answering, read the task's `answer_template.json`; use its enum spellings exactly and return JSON only.

## API Workflow

Use targeted records, not broad assumptions.

- Tickets: call `/api/tickets/<ticket_id>`, then `/api/outages?service_area=<service_area>`, `/api/diagnostics/<ticket_id>`, and `/api/troubleshooting/<ticket_id>`.
- Mobile cases: call `/api/cases/<case_id>`, then `/api/lines/<line_id>`, `/api/devices/<device_id>`, and `/api/plans/<plan_id>` from the line. If exact `bill_id` or `charge_amount_usd` is requested, use bill records only when the current task/API exposes them; never substitute the plan's monthly price for an overdue amount.
- Enterprise incidents: call `/api/enterprise/incidents/<incident_id>`, `/api/enterprise/export-runs?incident_id=<incident_id>`, `/api/enterprise/messages?query=<client/product/incident terms>`, and `/api/enterprise/sla/<enterprise_account_id>`.
- Use `/api/catalog` only to confirm available endpoints and record shapes.

## Ticket Decisions

Resolve blockers in this priority order:

1. Active outage.
   If an active outage matches the ticket `service_area` and includes the ticket `service_type`, set status `PENDING_ACTION`, route `OUTAGE_WAIT` when that field exists, use the outage id, no escalation team, no diagnostic required, and set latency/stability/bandwidth flags false. Count it as a customer-wait ticket.
2. Account/auth eligibility blockers.
   Invalid account ids or "no matching account" -> `FAILED`, `INVALID_ACCOUNT`, no route team/escalation, diagnostic false.
   Account hold/ineligible account -> `FAILED`, `INELIGIBLE_ACCOUNT`, no escalation team, diagnostic false.
   Authentication failure -> `FAILED`, `AUTH_FAILED`, no route team, diagnostic false.
   Overdue suspension -> `FAILED`, `OVERDUE_SUSPENSION`, `ACCOUNTS_PAYABLE`, diagnostic false. Do not mark overdue suspension as pending just because the customer may later pay.
3. Network or provisioning root cause.
   Physical/fiber/signal-loss line issues -> `ESCALATED`, `FIELD_OPS`, diagnostic true.
   Backbone/capacity issues -> `ESCALATED`, `NETWORK_ENGINEERING`, `NETWORK_CAPACITY`, diagnostic true.
   Provisioning stale/mismatch after an attempted adjustment -> `ESCALATED`, `TIER2_SUPPORT`, `PROVISIONING_STALE`, diagnostic true unless the console explicitly says resolved.
4. Auto-fixable profile/config issues.
   Configuration drift or voice/profile stale issues that improve after troubleshooting -> `RESOLVED`, no route team/escalation, key blocker `NONE`, route `AUTO_TROUBLESHOOTING` when available, diagnostic true.

Diagnostic issue flags in batch ticket tasks refer to the pre-troubleshooting diagnostic evidence and should be false for outage/account-blocked tickets. Set:

- `latency_issue`: high latency or latency-related root cause.
- `stability_issue`: high jitter, packet loss, signal loss, or unstable service root cause.
- `bandwidth_issue`: diagnostic bandwidth materially below the subscribed tier or a bandwidth/signal root cause.

Queue summaries count final statuses and non-`NONE` route teams exactly from the per-ticket decisions.

## Mobile Case Decisions

Choose the first specific repair supported by line/device/plan evidence:

- Suspended line due to overdue bill: `SEND_PAYMENT_REQUEST` then `RESUME_LINE_REBOOT`, route `BILLING_RECOVERY`, include the actual bill id and overdue amount from bill evidence.
- No service with missing SIM: `RESEAT_SIM`, route `SELF_SERVICE`.
- Airplane mode enabled: `TOGGLE_AIRPLANE_MODE`, route `SELF_SERVICE`.
- Mobile data disabled on device: `TOGGLE_MOBILE_DATA`, route `SELF_SERVICE` or `DEVICE_SETTING_FIX` depending on the template's route enum.
- Abroad/no data with device roaming off but line roaming enabled: `TOGGLE_ROAMING`, self-service route.
- Abroad/no data with line roaming disabled but device roaming on: `ENABLE_LINE_ROAMING`, `carrier_update_required: true`, route `CARRIER_UPDATE`.
- MMS/photo messaging with missing permissions: `GRANT_MESSAGING_PERMISSION`; set `permission` to `sms`, `storage`, or `sms_and_storage` from the device permissions.
- Slow data with `data_saver_mode: true`: `TOGGLE_DATA_SAVER`.
- Slow data with old network preference such as `3g_only`: `SET_NETWORK_MODE`.
- Slow data with VPN connected: `DISCONNECT_VPN`.
- Usage above plan limit with accepted refuel amount: `REFUEL_DATA`; `data_refuel_gb` is the accepted amount and charge is `accepted_gb * data_refueling_price_per_gb`.
- Use `TRANSFER_HUMAN` only when records show no safe self-service, billing, carrier, or device-setting operation.

Use `NO_ACTION` as the secondary action unless the workflow is explicitly two-step, such as payment request followed by line resume/reboot. Summaries are direct counts by final route/action category, and total customer charge is the sum of actual bill/refuel charges.

## Enterprise Export Incidents

Build response packages from incident, export-run, message, and SLA evidence.

- `failure_window`: consecutive failed export-run dates; start is first failed run, end is last failed run, `failed_days` is the count.
- `backfill_days`: count failed days requiring or receiving manual backfill. A later successful run can confirm recovery but does not change the failed window.
- `root_cause_category`: concise phrase from failure codes plus messages. Prefer business-readable wording such as `stale credential after rotation` over raw enum names when messages support it.
- `contributing_alert_issue`: use `ARCHIVED_ALERT_ROUTE` when relevant alert evidence is in an archive/retired alert channel; otherwise use `NONE` or `UNKNOWN` according to evidence.
- Owners, severity, and account id come from the incident record.
- SLA credit percent comes from the SLA contract or explicit account message. Any nonzero SLA credit that still needs handling should set `response_status` to `NEEDS_FINANCE_REVIEW`, not `READY_TO_SEND`.
- `channel_name`: lowercase hyphenated legal client name, including suffixes like `inc`; do not append incident words unless requirements ask.
- `evidence_folder`: legal client name + month/year + `Investigation` in human title case.
- `report_title`: legal client name + `Export Failure - Resolution Report`.
- `share_permissions`: preserve the requested user order and use permission levels from requirements/evidence; when the package needs a reviewer and an editor, use view for the reviewer and edit for the owner/editor.

## Output Pitfalls

- Do not let generated/noise diagnostics override a matched outage or account blocker.
- Do not count `NONE` route teams in team summaries.
- Do not guess bill charges from plan price; exact charge amounts come from bill evidence or explicit task payloads.
- Do not mark provisioning stale as resolved merely because troubleshooting attempted an adjustment.
- Do not mark an SLA-credit enterprise package ready when finance review is still implied.
- Keep numeric fields as numbers, not strings, and use `0.0`/`0.00`-style values where the template asks for decimal precision.
