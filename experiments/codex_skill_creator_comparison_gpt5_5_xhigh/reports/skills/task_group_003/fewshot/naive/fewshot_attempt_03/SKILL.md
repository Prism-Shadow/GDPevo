---
name: support-console-operations-solver
description: Solve support-console ticket, mobile case, and enterprise export response tasks by querying the read-only task API and filling the provided JSON template.
---

# Support Console Operations Solver

Use this skill when a task asks you to resolve support tickets, mobile support cases, mobile-data worklists, or enterprise export complaints using a shared support-console API.

Always produce only the JSON requested by the task's provided answer template.

## Required Workflow

1. Read the task prompt, every payload file, and the answer template.
2. Read the task's environment access note for `<TASK_ENV_BASE_URL>` and allowed endpoints. Use only read-only business endpoints; never call a judge endpoint.
3. Query the API for every target record. Do not infer IDs, customer records, lines, plans, bills, diagnostics, or enterprise data from naming patterns alone.
4. Build one output object that exactly matches the answer template: same top-level keys, exact enum spellings, JSON booleans, strings for inapplicable IDs as `""`, and numeric zeros as `0.0` when a numeric amount field is present.
5. Recompute every summary count from the decisions immediately before returning.

Useful lookup pattern:

```bash
BASE="<TASK_ENV_BASE_URL-without-trailing-slash>"
curl -sS "$BASE/api/catalog"
curl -sS "$BASE/api/search?q=<id-or-client-name>"
```

If a direct contact-center case endpoint listed in the access note is unavailable, use `/api/search?q=<case_id>` and take the result whose collection is `cases`. The catalog may also reveal equivalent public path names. Still use only public read-only records.

## Ordering Rules

- Ticket batch decisions: preserve payload row order.
- Queue quality ticket decisions: preserve payload row order.
- Case decisions: sort by ascending `case_id` unless the prompt explicitly says to preserve payload order.
- `share_permissions`: preserve the user order listed in the response requirements.
- Output field order should follow the template for readability.

## Ticket And Queue Quality Tasks

For each payload ticket:

1. Fetch the ticket record and confirm the payload account/service values against API evidence.
2. Find the account record, usually through `/api/search?q=<account_id>` if a direct account endpoint is not listed.
3. Check for an active outage matching both `service_area` and `service_type`.
4. For eligible non-outage tickets, fetch diagnostics and troubleshooting for the ticket.

Decision priority:

- Invalid account: if no account record exists for the payload account, set `FAILED`, no diagnostic, no team, and use `INVALID_ACCOUNT` or `INVALID_ACCOUNT` blocker/route where that field exists.
- Authentication failure: if account authentication shows failed login or failed recovery for the issue, set `FAILED`, no diagnostic, no team, and `AUTH_FAILED`.
- Suspended or ineligible account: set `FAILED` with no diagnostic. Use the most specific blocker/route available from account status, line/account reason, and intake note. Overdue suspension routes to `ACCOUNTS_PAYABLE` in queue-quality schemas that include route teams; generic ineligible-account schemas usually keep team `NONE`.
- Active outage: set `PENDING_ACTION`, no diagnostic, no team, include the matching `outage_id` when the template has that field, and use `OUTAGE_WAIT` or `ACTIVE_OUTAGE` as applicable.
- Resolved by troubleshooting: set `RESOLVED`, team `NONE`, blocker `NONE`, and route `AUTO_TROUBLESHOOTING` when present.
- Not resolved by troubleshooting and root cause requires ownership: set `ESCALATED` and map the root cause to the appropriate escalation team.

Escalation mapping:

- Backbone, regional capacity, network saturation, or capacity root causes: `NETWORK_ENGINEERING`; blocker `NETWORK_CAPACITY`.
- Provisioning mismatch, stale provisioning, stale profile after move, or service profile mismatch: `TIER2_SUPPORT`; blocker `PROVISIONING_STALE` when available.
- Fiber drop damage, physical line faults, signal loss after line work, or premises/field repair causes: `FIELD_OPS`; blocker `PHYSICAL_LINE_FAULT` when available.
- Overdue billing suspension: `ACCOUNTS_PAYABLE`; blocker `OVERDUE_SUSPENSION`.
- Fraud suspension: use `FRAUD_SUSPENSION`; route to a human/escalation team only if the template has an appropriate enum.

Diagnostic fields:

- `diagnostic_needed` and `diagnostic_required` are true only for eligible, non-outage tickets where diagnostics/troubleshooting are part of the resolution or escalation evidence.
- Set latency issue true when latency is materially high or the issue/root cause is latency/packet-loss related. A practical threshold from the examples is around 100 ms, but account for the service type and notes.
- Set stability issue true when jitter is elevated, packet loss/signal loss is present, or the customer reports intermittent service.
- Set bandwidth issue true when measured bandwidth is materially below subscribed speed or the issue/root cause is slow speed/capacity. Compare diagnostics to `subscribed_mbps`.
- For invalid, auth-failed, suspended, or outage-wait cases, issue booleans are false.

Ticket summaries:

- Count `RESOLVED`, `PENDING_ACTION`, `ESCALATED`, and `FAILED` directly from decision statuses.
- Count team keys such as `TIER2_SUPPORT`, `FIELD_OPS`, `NETWORK_ENGINEERING`, and `ACCOUNTS_PAYABLE` from the route/escalation team field, excluding `NONE`.
- `tickets_requiring_customer_wait` is the count of decisions waiting on an active outage.

## Mobile Case And Data Recovery Tasks

For each case:

1. Get the case record by case ID, using `/api/search?q=<case_id>` if needed.
2. Fetch the customer, line, device, plan, and bill records referenced by the case and line.
3. Choose the smallest operation that directly fixes the evidence-backed cause. Do not choose a billing or carrier update when a device setting alone explains the issue.

Action priority:

- Suspended line with overdue bill: `SEND_PAYMENT_REQUEST`; secondary `RESUME_LINE_REBOOT`; include the overdue bill ID and amount; final route `BILLING_RECOVERY`.
- Suspended line for non-billing reasons or contract ended with no self-service fix: `TRANSFER_HUMAN`; final route `HUMAN_TRANSFER`.
- Airplane mode enabled: `TOGGLE_AIRPLANE_MODE`.
- Missing/unseated/inactive SIM with no service: `RESEAT_SIM`.
- Abroad/traveling with phone roaming disabled: `TOGGLE_ROAMING`.
- Abroad/traveling with phone roaming enabled but line roaming disabled: `ENABLE_LINE_ROAMING`; carrier update required; final route `CARRIER_UPDATE`.
- Data usage at or above plan limit and the payload gives accepted refuel GB: `REFUEL_DATA`; charge is accepted GB multiplied by the plan's `data_refueling_price_per_gb`; final route `DATA_RECOVERY`.
- Mobile data disabled: `TOGGLE_MOBILE_DATA`.
- Data saver enabled for slow data: `TOGGLE_DATA_SAVER`.
- Old or restrictive network mode such as 3G-only for slow data: `SET_NETWORK_MODE`.
- VPN connected for slow or blocked data: `DISCONNECT_VPN`.
- MMS/photo send failure with missing messaging permission: `GRANT_MESSAGING_PERMISSION`; set permission to `sms`, `storage`, or `sms_and_storage` based on missing flags.
- MMS/data configuration missing, such as absent MMSC/APN while permissions are present: `RESET_APN_REBOOT`.
- Wi-Fi calling issue with Wi-Fi calling disabled: `TOGGLE_WIFI_CALLING`.
- If no evidence-backed self-service, billing, or carrier operation applies: `TRANSFER_HUMAN` for unresolved active complaints; otherwise `NO_ACTION`.

Mobile output fields:

- `secondary_action` is `NO_ACTION` except for the overdue-bill recovery flow, where the follow-up is line resume and reboot.
- `permission` is `NONE` except for `GRANT_MESSAGING_PERMISSION`.
- `bill_id` is blank except for billing recovery.
- `charge_amount_usd` is `0.0` except for overdue bill payment or data refuel.
- `data_refuel_gb` is the accepted refuel amount for `REFUEL_DATA`; otherwise `0.0`.
- `carrier_update_required` is true for carrier-side line changes such as enabling line roaming; otherwise false.

Route mapping:

- In contact-center schemas with `SELF_SERVICE`, route device-only fixes and permission changes to `SELF_SERVICE`.
- In data-recovery schemas, route `REFUEL_DATA` to `DATA_RECOVERY`, carrier-side line changes to `CARRIER_UPDATE`, device setting fixes to `DEVICE_SETTING_FIX`, and transfers to `HUMAN_TRANSFER`.
- In billing schemas, route overdue recovery to `BILLING_RECOVERY`.

Mobile summaries:

- `self_service_fixes`, `billing_recoveries`, `carrier_updates`, and `human_transfers` count `final_route` values.
- `data_refuel_cases` counts `REFUEL_DATA`.
- `device_setting_fixes` counts data-worklist decisions whose route is `DEVICE_SETTING_FIX`.
- `total_estimated_customer_charge_usd` is the sum of all `charge_amount_usd` values in the worklist.

## Enterprise Export Complaint Tasks

For structured enterprise response packages:

1. Parse the complaint for client name, product, severity, approximate incident ID, requested artifacts, and requested users.
2. Query enterprise accounts, incidents, export runs, messages, and the SLA contract for the selected enterprise account.
3. Select the incident by exact incident reference when present; otherwise match client, product, timing, and complaint summary.
4. Filter export runs by selected incident and product/account. The failure window is the consecutive failed-run span relevant to the complaint: earliest failed date, latest failed date, and count of failed days.
5. `backfill_days` normally equals the failed-day count when messages or a subsequent successful run confirm manual backfill/recovery; otherwise mark the response as needing engineering review.
6. Derive `root_cause_category` as a concise lowercase phrase from both failure codes and messages. Translate codes into plain language and enrich with message evidence; do not output raw codes unless the template explicitly asks for codes.
7. Set `contributing_alert_issue` to `ARCHIVED_ALERT_ROUTE` when root-cause or alert evidence was posted to an archive/archived alert route; `NONE` when normal evidence shows no such issue; `UNKNOWN` when evidence is insufficient.
8. Use `severity`, `engineering_owner`, and `account_owner` from the selected incident or enterprise account records.
9. Determine SLA credit from the SLA contract and account-escalation messages. Apply the percent only when the failure window satisfies the trigger.
10. Build response artifacts from the requirement naming style:
    - Lowercase hyphen channel from the client/account name.
    - Investigation folder using the client name and the failure month/year.
    - Export failure report title using the client name and product/failure theme.
11. For listed permission users, preserve the required order. Assign explicit permissions from requirements when provided. If only users are listed, use evidence-based roles: finance/account approvers get `view`; engineering or artifact collaborators get `edit`; upload-only participants get `upload_only`. If roles are not discoverable, use the conservative pattern of first reviewer as `view` and subsequent collaborator as `edit`.
12. Set response status:
    - `NEEDS_FINANCE_REVIEW` when an SLA credit must be handled.
    - `NEEDS_ENGINEERING_REVIEW` when root cause, recovery, or backfill is incomplete.
    - `UNDER_INVESTIGATION` when the incident is still unresolved and required evidence is missing.
    - `READY_TO_SEND` only when all required evidence is complete and no finance or engineering review remains.

## Final Validation

Before returning:

- Compare the output against the answer template key by key.
- Confirm every payload item has exactly one decision and no non-payload item appears.
- Check every enum value is one of the template's allowed values.
- Ensure inapplicable IDs are `""`, not `null`.
- Recalculate all summaries from the final decisions.
- Return only valid JSON, with no markdown or explanation.
