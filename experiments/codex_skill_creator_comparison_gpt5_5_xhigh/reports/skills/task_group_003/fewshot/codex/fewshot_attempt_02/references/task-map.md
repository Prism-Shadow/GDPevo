# Task Map

## Common rules

- Use only the staged payloads and the task-environment API.
- Preserve the payload order in every decision list.
- Treat the answer template as the source of truth for field names, enum literals, and numeric precision.
- Derive summary counts and totals from the finalized item rows.
- Fetch linked records by ID before inferring anything from free-text summaries.

## Offline service tickets

Typical inputs: `ticket_batch.csv`

Typical endpoints: `/api/tickets`, `/api/accounts`, `/api/outages`, `/api/diagnostics/<ticket_id>`, `/api/troubleshooting/<ticket_id>`.

Use this path when the task asks for `final_resolution_status`, issue flags, `outage_id`, `escalation_team`, or `resolution_route`.

- Match an active outage to `OUTAGE_WAIT` and populate `outage_id`.
- Use `AUTO_TROUBLESHOOTING` when diagnostics or troubleshooting evidence clears the issue.
- Use `ESCALATION` when the record needs field repair or network intervention.
- Use `INELIGIBLE_ACCOUNT`, `AUTH_FAILED`, or `INVALID_ACCOUNT` when account state blocks service.
- Set issue flags only when supported by the ticket text or diagnostics.

## Contact-center queue

Typical inputs: `case_queue.json`

Typical endpoints: `/api/cases`, `/api/customers`, `/api/lines`, `/api/bills`, `/api/plans`, `/api/devices`.

Use this path when the task asks for `primary_action`, `secondary_action`, `permission`, `bill_id`, `charge_amount_usd`, or `final_route`.

- Route no-service, SIM, signal, airplane-mode, roaming, mobile-data, VPN, or Wi-Fi calling issues to the matching device or line action.
- Use billing recovery when the line is suspended for an overdue bill and the customer is ready to pay.
- Use roaming updates when travel or carrier-side roaming is the blocker.
- Use `GRANT_MESSAGING_PERMISSION` when MMS/photo sending needs storage or messaging access.
- Use `REFUEL_DATA` only when the customer accepts a top-up; compute the charge from the plan pricing.
- Use `NO_ACTION` as the filler secondary action when only one step is needed.

## Enterprise export complaint

Typical inputs: complaint email plus `response_requirements.json`

Typical endpoints: `/api/enterprise/incidents`, `/api/enterprise/export-runs`, `/api/enterprise/messages`, `/api/enterprise/accounts`, `/api/enterprise/sla/<enterprise_account_id>`.

Use this path when the task asks for incident metadata, failure windows, root cause, SLA credit, owners, channels, evidence folders, report titles, or share permissions.

- Derive `incident_id`, `enterprise_account_id`, owners, and severity from the incident record.
- Derive the failure window from the consecutive failed export runs.
- Derive backfill days from the failed run span that must be replayed.
- Infer the root cause from run failure codes plus message evidence.
- Use the message channel or archived-route evidence for `contributing_alert_issue`.
- Use the SLA record for the credit percent.
- Follow the requirement file for naming, folder, and permission order.

## Queue-quality review

Typical inputs: `queue_snapshot.csv`

Typical endpoints: `/api/tickets`, `/api/outages`, `/api/diagnostics/<ticket_id>`, `/api/troubleshooting/<ticket_id>`.

Use this path when the task asks for `final_resolution_status`, `route_team`, `key_blocker`, or `diagnostic_required`.

- Use `PENDING_ACTION` for active outages.
- Use `FAILED` for invalid accounts or auth failures.
- Route overdue suspension to `ACCOUNTS_PAYABLE`.
- Route capacity problems to `NETWORK_ENGINEERING`.
- Route provisioning problems to `TIER2_SUPPORT`.
- Route physical line faults to `FIELD_OPS`.
- Set `diagnostic_required` when the handoff needs diagnostic confirmation.

## Mobile-data recovery

Typical inputs: `mobile_data_worklist.json`

Typical endpoints: `/api/cases`, `/api/customers`, `/api/lines`, `/api/bills`, `/api/plans`, `/api/devices`.

Use this path when the task asks for `primary_action`, `secondary_action`, `data_refuel_gb`, `charge_amount_usd`, `carrier_update_required`, or `final_route`.

- Use `REFUEL_DATA` for usage-limit recovery when the customer accepts the top-up.
- Use roaming actions when the case is travel-related and the line or device is not set up for roaming.
- Use device-setting actions for data saver, network mode, mobile data, VPN, or roaming toggles.
- Use `TRANSFER_HUMAN` when self-service cannot resolve the case.
- Mark `carrier_update_required` only when the fix needs a carrier-side change.
- Compute charges from the plan or refuel pricing and round to two decimals.

## Final check

- Preserve ordering.
- Match every enum exactly.
- Return only JSON, with no markdown fences or commentary.
