# Support Console Reference

## API map

- Tickets: `/api/tickets/<ticket_id>`, `/api/diagnostics/<ticket_id>`, `/api/troubleshooting/<ticket_id>`, `/api/outages`
- Accounts and queue cases: `/api/accounts`, `/api/accounts/<account_id>`, `/api/cases/<case_id>`, `/api/customers/<customer_id>`, `/api/lines/<line_id>`, `/api/devices/<device_id>`, `/api/bills/<bill_id>`, `/api/plans/<plan_id>`
- Enterprise: `/api/enterprise/incidents/<incident_id>`, `/api/enterprise/export-runs`, `/api/enterprise/messages`, `/api/enterprise/sla/<enterprise_account_id>`

## What to trust

- Tickets are usually sparse; rely on diagnostics, troubleshooting, and outage state.
- Accounts expose status plus authentication state; use them for auth-failure and suspension checks.
- Lines expose status, roaming, suspension, and plan linkage.
- Devices expose airplane mode, data saver, VPN, network mode, MMS permissions, roaming, and mobile data state.
- Enterprise incidents expose owners, severity, and product; export runs expose failure windows and failure codes; messages often name the root cause or credit rule.

## Batch heuristics

### Ticket triage

- Active outage covering the service area or service type -> `PENDING_ACTION` / `OUTAGE_WAIT`.
- Recoverable configuration or signal issue that improves in troubleshooting -> `RESOLVED` / `AUTO_TROUBLESHOOTING`.
- Line work, fiber damage, backbone capacity, or provisioning mismatch -> `ESCALATED`, usually to `FIELD_OPS`, `NETWORK_ENGINEERING`, or `TIER2_SUPPORT` as the blocker suggests.
- Invalid account or failed auth / ineligible line -> `FAILED`.

### Queue review

- `ACTIVE_OUTAGE` -> pending action, no team.
- `INVALID_ACCOUNT` or `AUTH_FAILED` -> failed, no team.
- `OVERDUE_SUSPENSION` -> failed, `ACCOUNTS_PAYABLE`.
- `NETWORK_CAPACITY` -> escalated, `NETWORK_ENGINEERING`.
- `PROVISIONING_STALE` -> escalated, `TIER2_SUPPORT`.
- `PHYSICAL_LINE_FAULT` -> escalated, `FIELD_OPS`.

### Mobile cases

- No service after commute with active SIM and weak or none signal -> `RESEAT_SIM`.
- Suspended line with an overdue bill -> `SEND_PAYMENT_REQUEST` then `RESUME_LINE_REBOOT`.
- Abroad with roaming off -> `ENABLE_LINE_ROAMING` and mark carrier update when required by the template.
- MMS or photo failure with storage permission off -> `GRANT_MESSAGING_PERMISSION`.
- Slow data with VPN connected -> `DISCONNECT_VPN`.
- Slow data with data saver on -> `TOGGLE_DATA_SAVER`.
- Slow data with older network mode -> `SET_NETWORK_MODE`.
- No data after settings change when mobile data is off -> `TOGGLE_MOBILE_DATA`.
- Usage-limit data stop and the customer accepts refuel -> `REFUEL_DATA` at the plan's refueling price.

### Enterprise export complaints

- Incident = complaint incident ID.
- Failure window = consecutive failed export-run dates before recovery.
- Backfill days = failed days.
- Root cause = failure code plus message evidence.
- SLA credit = contract or SLA record.
- Channel name = lowercase hyphen client name.
- Evidence folder and report title must follow the naming style in the requirements.
- Share permissions must keep the order given by the requirements.
- Use `NEEDS_FINANCE_REVIEW` when credit handling is the remaining decision; use `NEEDS_ENGINEERING_REVIEW` when root cause or remediation is still incomplete; use `READY_TO_SEND` only when both are settled.

## Formatting

- `charge_amount_usd` uses two decimals.
- `data_refuel_gb` uses one decimal.
- `failed_days` and `sla_credit_percent` are integers.
- Use `0.0`, `0.00`, empty strings, or `false` only where the template calls for them.
