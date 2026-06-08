---
name: support-console-demonstration
description: Use this skill for task_group_003 support-console tasks that require producing answer.json from ticket batches, mobile support case queues, mobile data worklists, or enterprise export complaints. It gives the API lookup order, routing rules, output field meanings, and common pitfalls learned from official input/output examples.
---

# Support Console Input/Output Skill

## First Pass

1. Read the task prompt and `payloads/answer_template.json` before deciding fields. The templates differ across ticket, mobile, and enterprise tasks.
2. Use the base URL provided by the current task or harness. Confirm with `/health` if needed, then use `/api/catalog` to understand available support-console records.
3. Work only from the current input payload and API records. Do not infer from the customer wording alone when a ticket/case/incident id is available.
4. Return only JSON matching the template. Preserve requested ordering: ticket payload order for ticket batches, ascending `case_id` for case queues/worklists, and requirement order for share-permission users.

## API Lookup SOP

Ticket tasks:

- Fetch `/api/tickets/<ticket_id>` for service area, service type, account id, and subscribed speed.
- Fetch `/api/outages?service_area=<service_area>` and apply only active outages whose `service_types` include the ticket service type.
- Fetch `/api/diagnostics/<ticket_id>` and `/api/troubleshooting/<ticket_id>` for non-outage, eligible tickets.

Mobile case tasks:

- Fetch `/api/cases/<case_id>` to get `customer_id`, `line_id`, `device_id`, `issue_type`, and location.
- Fetch `/api/lines/<line_id>`, `/api/devices/<device_id>`, and `/api/plans/<plan_id>`.
- When a task asks for bill recovery, use the permitted bill source exposed by the task/API and copy the exact bill id and amount. Do not invent bill amounts.

Enterprise export tasks:

- Fetch `/api/enterprise/incidents/<incident_id>`.
- Fetch `/api/enterprise/export-runs?incident_id=<incident_id>`.
- Search `/api/enterprise/messages?query=<text>` with narrow terms from the client, product, incident, failure code, owner, and alert/root-cause words.
- Fetch `/api/enterprise/sla/<enterprise_account_id>` after the incident reveals the enterprise account.

## Ticket Classification Rules

Apply blockers before diagnostics:

- Active outage: set `PENDING_ACTION`, no diagnostic required/needed, route `OUTAGE_WAIT` when that field exists, and copy `outage_id`. Count it as customer wait.
- Invalid account or no matching account: set `FAILED`, blocker/route `INVALID_ACCOUNT`, no diagnostic.
- Account hold, overdue suspension, fraud suspension, or other ineligible account state: set `FAILED`, no diagnostic. If the template has only `resolution_route`, use `INELIGIBLE_ACCOUNT` for account holds/suspensions. If the template has `key_blocker`, use the specific enum such as `OVERDUE_SUSPENSION` or `FRAUD_SUSPENSION`; overdue billing handoff routes to `ACCOUNTS_PAYABLE`.
- Authentication never recovered or auth failure evidence: set `FAILED`, blocker/route `AUTH_FAILED`, no diagnostic.

For eligible non-outage tickets, use diagnostics and troubleshooting:

- `CONFIGURATION_DRIFT`, stale voice profile, or similar profile/provisioning refresh that troubleshooting fixes: `RESOLVED`, route/team `NONE`, `resolution_route` `AUTO_TROUBLESHOOTING`, diagnostic true.
- `VOICE_PROFILE_STALE`: usually `RESOLVED` after `VOICE_PROFILE_REFRESH`.
- `FIBER_DROP_DAMAGE`, `SIGNAL_LOSS`, or physical line faults: `ESCALATED`, team `FIELD_OPS`, blocker `PHYSICAL_LINE_FAULT`, diagnostic true.
- `BACKBONE_CAPACITY` or capacity/backbone root causes: `ESCALATED`, team `NETWORK_ENGINEERING`, blocker `NETWORK_CAPACITY`, diagnostic true.
- `PROVISIONING_STALE` that still needs manual correction: `ESCALATED`, team `TIER2_SUPPORT`, blocker `PROVISIONING_STALE`, diagnostic true.
- Ignore `GENERATED_NOISE` as a real root cause when stronger outage/account/auth evidence exists.

Issue booleans:

- Set `diagnostic_needed`/`diagnostic_required` true only for eligible tickets that need or used diagnostics; false for active outages and account/auth failures.
- Set `latency_issue` true for materially high latency on an eligible diagnostic ticket, commonly above roughly 100 ms or supported by latency/root-cause evidence.
- Set `stability_issue` true for high jitter, packet loss, signal-loss, or intermittent/stability root causes on an eligible ticket.
- Set `bandwidth_issue` true when diagnostic bandwidth is materially below subscribed speed, especially below about 80 percent, on an eligible ticket.
- For failed or outage-blocked tickets, leave latency/stability/bandwidth booleans false even if noisy diagnostic numbers exist.

Summaries:

- Count final statuses exactly by enum.
- Count route/team fields exactly by enum when the summary asks for team counts.
- `tickets_requiring_customer_wait` is the count of active-outage `PENDING_ACTION` tickets.

## Mobile Case Action Rules

Always combine case issue type with line and device facts.

Line/account blockers:

- `status: Suspended` with `suspension_reason: OVERDUE_BILL` and customer willingness to pay: primary `SEND_PAYMENT_REQUEST`, secondary `RESUME_LINE_REBOOT`, final route `BILLING_RECOVERY`, exact bill id/amount.
- Suspensions not recoverable by payment, ended contracts, fraud, SIM lock/PUK, unsupported states, or missing consent for a charge: `TRANSFER_HUMAN`, final route `HUMAN_TRANSFER`.

No service:

- `airplane_mode: true`: `TOGGLE_AIRPLANE_MODE`.
- `sim_status` missing/not seated: `RESEAT_SIM`.
- Active line with device-side no-signal but no SIM/account blocker may need a self-service radio/device action from the template.

Roaming and mobile data:

- Customer abroad, line roaming enabled, but `phone_roaming_enabled: false`: `TOGGLE_ROAMING`, self-service/device-setting route.
- Customer abroad, phone roaming on, but line `roaming_enabled: false`: `ENABLE_LINE_ROAMING`, `carrier_update_required: true`, final route `CARRIER_UPDATE`.
- `mobile_data_enabled: false`: `TOGGLE_MOBILE_DATA`, device-setting route.
- Data usage at/over `plan.data_limit_gb` with an accepted refuel amount: `REFUEL_DATA`; set `data_refuel_gb` to the accepted amount and charge `accepted_gb * data_refueling_price_per_gb`.
- Respect customer preferences such as no plan change; use refuel rather than plan migration when that is the accepted recovery.

Slow data:

- `data_saver_mode: true`: `TOGGLE_DATA_SAVER`.
- Old or restricted `network_mode_preference` such as `3g_only`: `SET_NETWORK_MODE`.
- `vpn_connected: true`: `DISCONNECT_VPN`.

MMS and messaging:

- Missing messaging permissions: `GRANT_MESSAGING_PERMISSION`; set `permission` to `sms`, `storage`, or `sms_and_storage` based on exactly what is false.
- Missing APN/MMSC evidence: `RESET_APN_REBOOT` when that enum is available.

Defaults and summaries:

- Use `secondary_action: NO_ACTION` unless a two-step operation is required, such as payment then line resume/reboot.
- Use `charge_amount_usd: 0.0` and empty `bill_id` when no charge/bill applies.
- For mobile-data worklists, classify `REFUEL_DATA` as `DATA_RECOVERY`, line-level roaming enable as `CARRIER_UPDATE`, and device toggles/settings as `DEVICE_SETTING_FIX`.
- For contact-center queues, self-service device actions count as `SELF_SERVICE`, overdue payment recovery as `BILLING_RECOVERY`, carrier line changes as `CARRIER_UPDATE`, and unresolved/manual cases as `HUMAN_TRANSFER`.
- Sum charges as numbers, not strings, with the requested decimal precision.

## Enterprise Export Response Rules

1. Identify the incident id from the email/reference, then fetch the incident record for account id, severity, owners, product, and status.
2. Determine `failure_window` from export runs with `status: FAILED`; use the first and last failed run dates and count failed days.
3. Set `backfill_days` to the failed-run count that requires or received manual backfill. If a later succeeded run or message confirms recovery, the response can still need finance review for credits.
4. Derive `root_cause_category` by humanizing the failure code and confirming with messages. For example, a stale credential code plus rotation/old-secret evidence becomes a concise stale-credential-after-rotation category.
5. Set `contributing_alert_issue` to `ARCHIVED_ALERT_ROUTE` when alert evidence is in an archive/archived-alert channel or clearly routed to an archive; use `NONE` when alert handling was normal, `UNKNOWN` when evidence is missing.
6. Fetch SLA terms and apply the credit only when the trigger is met, such as the required number of consecutive failed export runs.
7. Copy `engineering_owner`, `account_owner`, and `severity` from the incident unless stronger response requirements override them.
8. Build response artifacts from requirements:
   - `channel_name`: lowercase hyphenated client/legal name; keep corporate suffixes unless instructed otherwise.
   - `evidence_folder`: `<Client Name> <Month YYYY> Investigation`, based on the failure window month.
   - `report_title`: `<Client Name> Export Failure - Resolution Report` unless the requirements specify another title style.
   - `share_permissions`: include only required users, in the listed order. Use explicit permission evidence when present; if only two response-package users are listed, the usual convention is first `view`, second `edit`.
9. Set `response_status`: `NEEDS_FINANCE_REVIEW` when an SLA credit is owed; `NEEDS_ENGINEERING_REVIEW` when root cause/backfill/owner evidence is incomplete; `UNDER_INVESTIGATION` when the incident lacks enough resolution evidence; otherwise `READY_TO_SEND`.

## Common Pitfalls

- Do not let generic diagnostic noise override a clear outage, invalid account, auth failure, or suspension.
- Do not mark outage tickets as requiring diagnostics.
- Do not reorder records while sorting or grouping unless the template explicitly asks for ascending ids.
- Do not omit empty-string fields; templates often require `""` for non-applicable ids.
- Do not output explanatory text, Markdown, or comments around the final JSON.
