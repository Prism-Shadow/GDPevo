# Decision Rules

Domain-specific resolution logic for each task type. Apply these rules after
querying the API for all relevant records.

## Ticket Batch (offline service tickets)

Payload: CSV with `ticket_id`, `account_id`, `reported_service_type`, `customer_report`.

For each ticket, determine `final_resolution_status`, boolean flags, `outage_id`,
`escalation_team`, and `resolution_route` as follows:

### Query Sequence

1. `GET /api/tickets/{ticket_id}` -- confirms ticket exists and fetches linked account/line.
2. `GET /api/diagnostics/{ticket_id}` -- latency, packet loss, bandwidth, stability.
3. `GET /api/troubleshooting/{ticket_id}` -- auto-resolvability, outage linkage, field-ops need.
4. `GET /api/outages` -- cross-reference with ticket service type and area.
5. `GET /api/customers/{customer_id}` or `/api/enterprise/accounts/{account_id}` -- account status.

### Resolution Logic

**RESOLVED (AUTO_TROUBLESHOOTING)**: When the diagnostic endpoint reports measurable
issues (latency, packet-loss, bandwidth) AND the troubleshooting endpoint
indicates auto-resolvable steps. Set all three boolean flags (latency_issue,
stability_issue, bandwidth_issue) based on the diagnostic values: true when
above/below normal thresholds.

**PENDING_ACTION (OUTAGE_WAIT)**: When troubleshooting or the outage list links the
ticket to an active outage. Populate `outage_id` from the linked outage. Set all
boolean flags to false since the root cause is the outage, not the line.

**ESCALATED (ESCALATION)**: When troubleshooting indicates `requires_field_ops` or
the diagnostic shows a physical-line issue beyond remote fix. Escalation team:

- `FIELD_OPS` when the issue involves physical infrastructure (line work, cabling,
  hardware replacement indicated by diagnostic or troubleshooting).
- `NETWORK_ENGINEERING` when the issue is backbone/capacity related.
- `TIER2_SUPPORT` for provisioning or configuration issues.

**FAILED**: When the account is ineligible, suspended, invalid, or unreachable.

- `INELIGIBLE_ACCOUNT` when the account has an active hold or suspension.
- `INVALID_ACCOUNT` when the account_id does not match any registered account.
- `AUTH_FAILED` when the customer record shows authentication failures.

Set all boolean flags to false for FAILED records. Set `escalation_team` to `NONE`.

### Summary

Count final_resolution_status values. `tickets_requiring_customer_wait` is the
count of PENDING_ACTION tickets (those waiting on outage restoration).

---

## Contact-Center Queue (mobile support cases)

Payload: JSON with `cases` array, each with `case_id` and `reported_issue`.

### Query Sequence

1. Derive `customer_id` from the case numbering pattern. For CASE-NNNN, the
   customer is CUST-NNNN and the line is LINE-NNNN.
2. `GET /api/customers/{customer_id}` -- verify customer and get associated records.
3. `GET /api/lines/{line_id}` -- line status, roaming, mobile data, data saver,
   network mode, VPN status, messaging permissions, APN settings, data usage.
4. `GET /api/bills` -- find bill for this customer, check status (overdue/paid).
5. `GET /api/plans/{plan_id}` -- plan details and refuel rate.
6. `GET /api/devices/{device_id}` -- device capabilities, SIM status.

### Primary/Secondary Action Selection

Match the reported issue to the line's actual state from API responses:

| Reported issue pattern | Primary action | Condition |
|------------------------|---------------|-----------|
| No service after commute/travel | `RESEAT_SIM` | SIM status shows unseated or not detected |
| No service after commute/travel | `TOGGLE_AIRPLANE_MODE` | If SIM is seated but line shows airplane mode |
| No service after commute/travel | `RESET_APN_REBOOT` | If SIM and radio are fine but APN is misconfigured |
| Line suspended, ready to pay | `SEND_PAYMENT_REQUEST` | Bill exists and is overdue |
| Line suspended, ready to pay | `RESUME_LINE_REBOOT` | Set as secondary after payment |
| Traveling abroad, no mobile data | `TOGGLE_ROAMING` | Roaming is off on device but line supports it |
| Traveling abroad, no mobile data | `ENABLE_LINE_ROAMING` | Line roaming not provisioned on carrier side |
| Messaging app cannot send photos | `GRANT_MESSAGING_PERMISSION` | Messaging permissions are missing |
| Mobile data works but is slow | `DISCONNECT_VPN` | VPN is active on the line |
| Mobile data works but is slow | `TOGGLE_DATA_SAVER` | Data saver is enabled |
| Mobile data works but is slow | `SET_NETWORK_MODE` | Line is on a legacy network mode |
| No data | `TOGGLE_MOBILE_DATA` | Mobile data is disabled on the line |

**Secondary action**: Usually `NO_ACTION`. Use a second action only when the fix
requires a sequenced pair (e.g., SEND_PAYMENT_REQUEST then RESUME_LINE_REBOOT,
or two settings toggles needed together).

**Permission**: Set to `storage` when the primary action is `GRANT_MESSAGING_PERMISSION`
and the line needs storage permission for photo attachments. Set to `sms` when
the line needs SMS permission. Set to `sms_and_storage` when both are needed.
Otherwise `NONE`.

**Bill ID and charge**: Populate `bill_id` and `charge_amount_usd` only when the
line is suspended for an overdue bill. The charge amount is the bill's `amount_due`,
formatted to two decimal places. Otherwise empty string and 0.0.

### Final Route

- `SELF_SERVICE` for any fix the customer can perform (SIM reseat, toggles, settings).
- `BILLING_RECOVERY` when a payment request is needed.
- `CARRIER_UPDATE` when the carrier must provision a setting (roaming enablement).
- `HUMAN_TRANSFER` when no automated action can resolve the issue.

---

## Enterprise Investigation (client export complaint)

Payload: `client_complaint_email.txt` and `response_requirements.json`.

### Query Sequence

1. Extract the incident reference from the email body.
2. `GET /api/enterprise/incidents/{incident_id}` -- severity, root cause, times.
3. `GET /api/enterprise/accounts/{account_id}` -- company name, plan, owners.
4. `GET /api/enterprise/export-runs` (filter by account and approximate date range) --
   identify the failed run window, backfill availability.
5. `GET /api/enterprise/messages` (filter by incident or account) -- find alert
   messages that may indicate contributing issues.
6. `GET /api/enterprise/sla/{account_id}` -- SLA tier and credit percentage.

### Field Determination

**incident_id**: From the email reference, verified against the API response.

**enterprise_account_id**: From the incident response's `account_id` field.

**root_cause_category**: Concise summary derived from the export-run `failure_reason`
field combined with message content. Look for credentials, configuration, pipeline
errors, timeout, or data format issues. Phrase as a short category like "stale
credential after rotation", "pipeline timeout", or "schema mismatch".

**contributing_alert_issue**: Set to `ARCHIVED_ALERT_ROUTE` when enterprise messages
show an alert that was archived or misrouted rather than delivered to the
engineering team. Otherwise `NONE`. Use `UNKNOWN` only when the messages suggest
an alert issue but the nature is unclear.

**failure_window**: Derive `start_date`, `end_date`, and `failed_days` from the
export-run records. Count consecutive days with failed exports. Format dates as
`YYYY-MM-DD`.

**backfill_days**: Set to `failed_days` when export-run records show backfill is
available for all failed days. Set to a lower number when only partial backfill
is available. Set to 0 when no backfill exists.

**sla_credit_percent**: Read from the SLA endpoint's `credit_percent` field. Output
as an integer (e.g., 15).

**severity**: From the incident response, mapped to `Critical`, `High`, `Medium`, or `Low`.

**engineering_owner**: From the enterprise account's `engineering_owner` field.

**account_owner**: From the enterprise account's `account_owner` field.

**channel_name**: Lowercase-hyphenated company name from the account response.

**evidence_folder**: `{Company Name} {Month Year} Investigation` using the failure
window's start month/year.

**report_title**: `{Company Name} Export Failure - Resolution Report`.

**share_permissions**: From the `permission_users_to_include` list in
`response_requirements.json`. Map each user to a permission level. The first
listed user typically gets `view`, subsequent users get `edit`. When the
requirements specify a particular mapping, follow that.

**response_status**: `NEEDS_FINANCE_REVIEW` when an SLA credit applies (>0%).
`NEEDS_ENGINEERING_REVIEW` when the root cause is not fully diagnosed.
`UNDER_INVESTIGATION` when messages are incomplete. `READY_TO_SEND` when all
evidence is complete and no credit review is needed.

---

## Queue-Quality Review (SLA handoff review)

Payload: CSV with `ticket_id`, `account_id`, `reported_service_type`, `queue_note`.

### Query Sequence

1. `GET /api/tickets/{ticket_id}` -- verify ticket and account linkage.
2. `GET /api/diagnostics/{ticket_id}` -- diagnostic findings.
3. `GET /api/outages` -- cross-reference with ticket service type and area.
4. `GET /api/customers/{customer_id}` or `/api/enterprise/accounts/{account_id}` --
   account standing.

### Classification Logic

Determine `final_resolution_status`, `route_team`, `key_blocker`, and
`diagnostic_required`:

**PENDING_ACTION**: When the ticket is linked to an active outage. `key_blocker` is
`ACTIVE_OUTAGE`. `route_team` is `NONE`. No diagnostic needed.

**RESOLVED**: When no outage or account blocker exists and diagnostic/
troubleshooting confirms auto-resolution is possible. Set `diagnostic_required`
to true (the diagnostic was needed to confirm). `key_blocker` is `NONE`.
`route_team` is `NONE`.

**FAILED**: When a fundamental account or billing problem prevents resolution.

- `INVALID_ACCOUNT` when the account_id does not exist.
- `AUTH_FAILED` when customer authentication is broken.
- `OVERDUE_SUSPENSION` when the account is suspended for non-payment; `route_team`
  is `ACCOUNTS_PAYABLE`.
- `FRAUD_SUSPENSION` when the account has a fraud hold.

`route_team` is `NONE` for invalid/auth failures, `ACCOUNTS_PAYABLE` for overdue
suspension. No diagnostic needed for FAILED records (`diagnostic_required` false).

**ESCALATED**: When a specialist team is needed.

- `NETWORK_CAPACITY` with `route_team` `NETWORK_ENGINEERING` for backbone/capacity
  errors. `diagnostic_required` true.
- `PHYSICAL_LINE_FAULT` with `route_team` `FIELD_OPS` for physical line issues.
  `diagnostic_required` true.
- `PROVISIONING_STALE` with `route_team` `TIER2_SUPPORT` for configuration or
  provisioning mismatches. `diagnostic_required` true.

---

## Mobile-Data Recovery (data recovery worklist)

Payload: JSON with `cases` array and `customer_preferences`.

### Query Sequence

1. Derive `customer_id` and `line_id` from case numbering (CASE-NNNN maps to
   CUST-NNNN and LINE-NNNN).
2. `GET /api/lines/{line_id}` -- data usage, data limit, mobile data state,
   roaming state, data saver, network mode, VPN.
3. `GET /api/plans/{plan_id}` -- refuel rate per GB, plan data limit.
4. `GET /api/customers/{customer_id}` -- verify account status.

### Action Selection Logic

**Data stopped after usage limit**: `REFUEL_DATA`. Check customer_preferences for
the accepted refuel GB amount and whether the customer wants a plan change.
Set `data_refuel_gb` to the accepted amount from preferences. Calculate
`charge_amount_usd` as `refuel_gb × plan.refuel_rate_per_gb`. Round to two
decimals. `final_route` is `DATA_RECOVERY`.

**Traveler has roaming on phone but no data**: Check line's `roaming_enabled`.
If false, `ENABLE_LINE_ROAMING` with `carrier_update_required` true and
`final_route` `CARRIER_UPDATE`. If roaming is enabled on line but not on device,
`TOGGLE_ROAMING` with `final_route` `DEVICE_SETTING_FIX`.

**Slow data and data-saver icon visible**: `TOGGLE_DATA_SAVER` with `final_route`
`DEVICE_SETTING_FIX`.

**Slow data on older network mode**: `SET_NETWORK_MODE` with `final_route`
`DEVICE_SETTING_FIX`.

**No data after settings change**: `TOGGLE_MOBILE_DATA` with `final_route`
`DEVICE_SETTING_FIX`.

**Slow data with VPN active**: `DISCONNECT_VPN` with `final_route` `DEVICE_SETTING_FIX`.

### Secondary Action

Almost always `NO_ACTION` for mobile-data recovery. Use only when a sequenced
pair of operations is needed (e.g., refuel then toggle).

### Summary

Count cases by `final_route`. `total_estimated_customer_charge_usd` is the sum
of all `charge_amount_usd` values, formatted to two decimals.

---

## General Rules

### Account ID Validation

When an account ID from a payload matches no account in the API, classify the
record as FAILED with `resolution_route` `INVALID_ACCOUNT` and `key_blocker`
`INVALID_ACCOUNT`. Do not attempt diagnostics or escalation.

### Output Format

Output only the JSON object conforming to the answer template. Do not wrap in
markdown code fences. Do not include explanatory text. The JSON must be valid
and parseable by standard JSON parsers.

### Record Order

Preserve the exact order of records from the input payload in the output array.

### Precision

- Monetary values: two decimal places (e.g., `86.40`, `4.00`, `0.00`).
- GB values: one decimal place (e.g., `2.0`, `0.0`).
- Integer values (counts, percentages): whole numbers, no decimals.
