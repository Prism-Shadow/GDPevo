---
name: support-console-operations
description: Use this skill for support-console tasks that ask you to resolve, classify, or route telecom/service tickets, contact-center mobile cases, mobile-data recovery worklists, or enterprise export incidents using TASK_ENV_BASE_URL plus local payloads/answer_template.json. It is especially relevant when the prompt says to use a shared support console API, preserve payload order, choose next support operations, classify blockers, assemble enterprise incident evidence, compute queue summaries, and return JSON only.
---

# Support Console Operations

Use this workflow when the task is an evidence-backed support-console decision task. The correct answer comes from the current payload files and the live support-console API, not from general troubleshooting assumptions.

## First Pass

1. Read the user prompt, every file under `payloads/`, and especially `payloads/answer_template.json`.
2. Identify the task family from the template keys:
   - `ticket_decisions`: fixed service ticket resolution or queue-quality classification.
   - `case_decisions`: mobile/contact-center case operation selection.
   - Enterprise incident fields such as `incident_id`, `failure_window`, `sla_credit_percent`, and `share_permissions`: export incident response package.
3. Use the base URL exactly as supplied in the prompt. Strip a trailing slash when building paths.
4. Start with `GET /health` and `GET /api/catalog` if endpoint names are uncertain.
5. Prefer direct lookups by IDs from the payload. Use `GET /api/search?q=<id-or-client-token>` to find linked records, especially account, bill, outage, message, and enterprise evidence.
6. Avoid broad collection reads. If a collection endpoint is the only practical source, immediately filter records to IDs, account names, incident IDs, service areas, or users from the current payload. Ignore generated or unrelated records.

Useful endpoints commonly exposed by the console:

- Fixed service: `/api/tickets/{ticket_id}`, `/api/diagnostics/{ticket_id}`, `/api/troubleshooting/{ticket_id}`, `/api/outages`, `/api/search`.
- Mobile cases: `/api/cases/{case_id}` or, if the environment exposes it, `/api/contact-center/cases/{case_id}`; then `/api/customers/{customer_id}`, `/api/lines/{line_id}`, `/api/devices/{device_id}`, `/api/plans/{plan_id}`, `/api/bills/{bill_id}`, and `/api/search`.
- Enterprise: `/api/enterprise/accounts/{account_id}`, `/api/enterprise/incidents/{incident_id}`, `/api/enterprise/sla/{account_id}`, `/api/enterprise/export-runs`, `/api/enterprise/messages`, and `/api/search`.

If a direct endpoint returns `not_found`, check `/api/catalog` for an alias and fall back to search. The live catalog is the tie-breaker for endpoint spelling.

## Output Rules

- Return only the JSON object requested by the answer template. No markdown, comments, or explanation.
- Use exactly the template keys and enum spellings. Do not add evidence fields unless the template asks for them.
- Preserve input order when the template says so. For cases, sort by ascending `case_id` when requested. For share permissions, preserve the user order from the requirements payload.
- Use template defaults consistently: empty string for missing IDs, `NONE` for no team/permission enum, `NO_ACTION` for no secondary action, `false` for inapplicable booleans, and numeric `0.0` for inapplicable charges or quantities.
- Compute summaries from your final decisions, not from source record counts.
- Validate with a JSON parser before finalizing.

## Fixed Service Ticket Rules

For each ticket row:

1. Fetch the ticket record. If the account ID from the payload does not resolve to an account record, classify the ticket as failed with an invalid-account blocker/route and no diagnostic requirement.
2. Fetch the account evidence through search if no direct account endpoint is available. Check `status` and `authentication`.
3. Check for an active outage that matches both the ticket `service_area` and the ticket `service_type`.
4. Apply blockers in this priority order before interpreting diagnostics:
   - Missing account: `FAILED`, no team, no diagnostics, invalid-account route/blocker.
   - Authentication failure or unrecovered account recovery: `FAILED`, no diagnostics, auth-failed route/blocker.
   - Suspended or held account/line: `FAILED`, no diagnostics. If the template has a `key_blocker`, choose the specific suspension reason such as overdue, fraud, or ineligible account. If the template asks for a `route_team`, overdue billing can route to `ACCOUNTS_PAYABLE`; if it asks for `escalation_team`, keep it `NONE` unless a real escalation is needed.
   - Matching active outage: `PENDING_ACTION`, no diagnostics, `outage_id` from the outage, outage-wait route/blocker, and count it as customer-waiting when that summary field exists.
5. Only after higher-priority blockers are cleared, fetch diagnostics and troubleshooting. Set the diagnostic-required flag true when these records are needed for the decision.
6. Set issue booleans from pre-troubleshooting evidence:
   - `latency_issue`: high latency or records/complaint indicating latency/packet delay.
   - `stability_issue`: high jitter, packet loss, signal loss, intermittent behavior, or stability-related root causes.
   - `bandwidth_issue`: measured bandwidth materially below subscribed bandwidth or complaint/diagnostics indicating poor speed.
7. Use troubleshooting outcome and root cause to decide resolution:
   - Configuration/profile drift that improves to acceptable post-troubleshooting metrics is `RESOLVED` through automated troubleshooting.
   - Physical line damage, signal loss, or line-work faults escalate to `FIELD_OPS`.
   - Backbone/capacity/congestion faults escalate to `NETWORK_ENGINEERING`.
   - Stale provisioning or provisioning mismatch that still needs account/system correction escalates to `TIER2_SUPPORT`.
   - Generated/noise diagnostic root causes should not override stronger outage, account, auth, billing, or issue-summary evidence.
8. When the template has both status and team fields, keep the fields coherent: resolved and pending-outage tickets normally have team `NONE`; escalated tickets have the specialist team; failed invalid/auth tickets normally have team `NONE`.

## Mobile Case Rules

For each case:

1. Fetch the case, then fetch its customer, line, device, plan, and any current bill. Search by `customer_id` is often the fastest way to locate a bill.
2. Resolve billing and suspension before device settings:
   - Suspended line with an overdue bill: primary action `SEND_PAYMENT_REQUEST`, secondary action `RESUME_LINE_REBOOT`, include the overdue bill ID and amount, and use the billing-recovery route.
   - Other suspensions or ambiguous account states should transfer to a human unless the template offers a more specific carrier-update route.
3. For no-service cases with an active line:
   - `airplane_mode: true` -> `TOGGLE_AIRPLANE_MODE`.
   - missing/inactive SIM -> `RESEAT_SIM`.
   - mobile data disabled -> `TOGGLE_MOBILE_DATA` if the issue is data/no connection.
   - APN/MMSC configuration problems -> `RESET_APN_REBOOT`.
4. For roaming/travel data:
   - Line-level roaming disabled -> `ENABLE_LINE_ROAMING`, mark carrier update required when that field exists, and use the carrier-update route.
   - Device phone roaming disabled while line roaming is enabled -> `TOGGLE_ROAMING` as a self-service/device fix.
5. For MMS/photo messaging:
   - Missing app permissions -> `GRANT_MESSAGING_PERMISSION`.
   - Fill `permission` as `sms`, `storage`, or `sms_and_storage` from the missing permission keys.
6. For slow mobile data:
   - Active VPN -> `DISCONNECT_VPN`.
   - Data saver enabled -> `TOGGLE_DATA_SAVER`.
   - Old or restrictive network mode -> `SET_NETWORK_MODE`.
   - Data used at/above plan limit and the payload gives an accepted data refuel amount -> `REFUEL_DATA`.
7. For data refuel:
   - `data_refuel_gb` is the accepted/refuel amount from the payload or a record explicitly authorizing it.
   - `charge_amount_usd = data_refuel_gb * plan.data_refueling_price_per_gb`, rounded to two decimals.
   - Use `0.0` for refuel and charge fields when not applicable.
8. Map action families to the final route enum available in the template:
   - Bill payment/resume -> `BILLING_RECOVERY`.
   - Line-level carrier changes -> `CARRIER_UPDATE`.
   - Data refuel -> `DATA_RECOVERY` when offered, otherwise the closest self-service recovery route.
   - Device toggles, permissions, VPN, SIM, APN, network mode -> `SELF_SERVICE` or `DEVICE_SETTING_FIX`, depending on the template.
   - Unsupported, contradictory, or safety-sensitive states -> `HUMAN_TRANSFER`.
9. Set `secondary_action` to `NO_ACTION` unless a bill recovery or other record explicitly requires a follow-up operation.

## Enterprise Export Incident Rules

1. Parse the complaint and requirement payloads for client name, product, incident reference, required output fields, naming style, and permission users.
2. Fetch the incident by ID when available. Otherwise search by client name and product, then use the incident whose account/product/summary matches the complaint.
3. Fetch the enterprise account and SLA contract from the incident `enterprise_account_id`.
4. Find export-run records matching the incident ID and enterprise account. If using a collection endpoint, filter strictly to that incident/account.
5. Derive the failure window from consecutive failed runs:
   - `start_date`: earliest failed run date in the incident window.
   - `end_date`: latest failed run date in the incident window.
   - `failed_days`: count of failed run dates.
   - `backfill_days`: number of failed days that need or received backfill, using export-run success/backfill evidence and complaint requirements.
6. Derive a concise `root_cause_category` from failure codes plus relevant messages. Normalize codes into lower-case business language and enrich with message evidence only when it matches the same client/incident.
7. Set `contributing_alert_issue` to `ARCHIVED_ALERT_ROUTE` when relevant alert/root-cause evidence was posted in an archive channel or states the alert route was archived. Use `NONE` when evidence shows no alert routing issue, and `UNKNOWN` only when required evidence is absent.
8. Use the incident/account records for engineering owner, account owner, severity, and enterprise account ID. Prefer explicit account owner from the incident when it is present.
9. Compute SLA credit from the SLA contract only when the trigger is met by the failed run evidence. If a credit is due, the response usually needs finance review.
10. Build response artifacts from the requirements naming style:
   - `channel_name`: lowercase, hyphenated client/account name with punctuation removed.
   - `evidence_folder`: client/account name plus the relevant month/year and an investigation label.
   - `report_title`: client/account name plus an export-failure resolution-report label.
11. For `share_permissions`, include exactly the users requested, in the requested order. Use explicit requirement or role evidence when present. As a default, finance/SLA reviewers get `view`, the primary editor/engineering collaborator gets `edit`, and `upload_only` is only for artifact-dropbox style requirements.
12. Choose `response_status` from remaining approval needs:
   - Credit due or finance owner review needed -> `NEEDS_FINANCE_REVIEW`.
   - Root cause, backfill, or incident owner evidence incomplete -> `NEEDS_ENGINEERING_REVIEW` or `UNDER_INVESTIGATION`, matching the template.
   - All evidence complete and no approval gate remains -> `READY_TO_SEND`.

## Final Check

Before returning:

- Every output item is backed by current payload/API evidence.
- Decision order matches the template requirement.
- Enum values are copied from the template, not paraphrased.
- Numeric charge, refuel, count, and percent fields are numbers, not strings.
- Summary totals equal the decisions you produced.
- The final response is parseable JSON and contains nothing else.
