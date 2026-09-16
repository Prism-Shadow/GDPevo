# Support Console API Reference

All endpoints are under `<TASK_ENV_BASE_URL>`, which will be provided in the task prompt. The API is read-only (GET only) and requires no authentication.

## Catalog

`GET /api/catalog` returns the full endpoint list and aggregate record counts. Call this first if you need to verify available endpoints or record-count ranges.

## Accounts

### `GET /api/accounts`

Returns an array of all accounts.

### `GET /api/accounts/{account_id}`

```json
{
  "account_id": "ACC-xxxx",
  "name": "string",
  "service_area": "SA-nn",
  "status": "Active | Suspended | Closed | Hold",
  "tier": "standard | premium | enterprise",
  "authentication": {
    "last_login_at": "ISO timestamp",
    "last_login_status": "SUCCESS | FAILED | LOCKED",
    "account_recovery_status": "string (empty when none)"
  }
}
```

**Decision relevance:** If an account doesn't exist (404), the ticket is INVALID_ACCOUNT. If `status` is "Suspended", check the suspension context (bill overdue, fraud). If `authentication.last_login_status` is anything but "SUCCESS", the ticket may be AUTH_FAILED.

## Tickets

### `GET /api/tickets`

Returns an array of all tickets.

### `GET /api/tickets/{ticket_id}`

```json
{
  "ticket_id": "TCK-xxxx",
  "account_id": "ACC-xxxx",
  "service_area": "SA-nn",
  "service_type": "internet | video | voice",
  "status": "OPEN | CLOSED",
  "subscribed_mbps": "integer",
  "created_at": "ISO timestamp",
  "issue_summary": "string"
}
```

**Decision relevance:** Use `service_area` and `service_type` for outage matching. Use `service_type` to determine whether diagnostics apply (internet and video tickets usually have diagnostic records; pure voice may not). Use `subscribed_mbps` as a baseline for bandwidth comparisons in diagnostics.

## Outages

### `GET /api/outages`

Returns an array of all outages.

```json
{
  "outage_id": "OUT-xxxx",
  "active": "boolean",
  "service_area": "SA-nn",
  "service_types": ["internet", "video", "voice"],
  "impact_score": "float 0.0-1.0",
  "started_at": "ISO timestamp",
  "eta_hours": "integer"
}
```

**Decision relevance:** Match a ticket to an outage when the ticket's `service_area` matches the outage's `service_area` AND the ticket's `service_type` is listed in the outage's `service_types`. Only `active: true` outages apply. When a match exists, the resolution route is OUTAGE_WAIT and the status is PENDING_ACTION.

## Diagnostics

### `GET /api/diagnostics/{ticket_id}`

```json
{
  "ticket_id": "TCK-xxxx",
  "bandwidth_mbps": "float",
  "latency_ms": "float",
  "jitter_ms": "float",
  "root_causes": ["string enum values"],
  "started_at": "ISO timestamp",
  "completed_at": "ISO timestamp"
}
```

**Decision relevance:** Thresholds for issue flags:
- **Latency issue:** `latency_ms` > 100
- **Stability/jitter issue:** `jitter_ms` > 30
- **Bandwidth issue:** `bandwidth_mbps` < 80% of `subscribed_mbps`
- **Diagnostic needed:** true for internet/video tickets unless an outage covers them

Root cause values include `CONFIGURATION_DRIFT`, `NETWORK_CAPACITY`, `PHYSICAL_LINE_FAULT`, `PROVISIONING_STALE`, and others. Use these to determine escalation paths and blockers.

## Troubleshooting

### `GET /api/troubleshooting/{ticket_id}`

```json
{
  "ticket_id": "TCK-xxxx",
  "steps": ["PROFILE_REFRESH", "PROVISIONING_SYNC", "..."],
  "post_bandwidth_mbps": "float",
  "post_latency_ms": "float",
  "post_jitter_ms": "float",
  "started_at": "ISO timestamp",
  "completed_at": "ISO timestamp"
}
```

**Decision relevance:** If troubleshooting steps exist and post-repair metrics are healthy (latency < 100, jitter < 30, bandwidth >= 80% subscribed), the ticket can be marked RESOLVED via AUTO_TROUBLESHOOTING. If post-repair metrics are still bad or no troubleshooting record exists, escalate based on the root cause.

## Customers

### `GET /api/customers`

Returns an array of all customers.

### `GET /api/customers/{customer_id}`

```json
{
  "customer_id": "CUST-xxxx",
  "name": "string",
  "phone_number": "string",
  "status": "Active | Suspended | Inactive"
}
```

## Lines

### `GET /api/lines`

Returns an array of all lines (filter by `customer_id` if needed).

### `GET /api/lines/{line_id}`

```json
{
  "line_id": "LINE-xxxx",
  "customer_id": "CUST-xxxx",
  "device_id": "DEV-xxxx",
  "plan_id": "PLAN-xxxx",
  "phone_number": "string",
  "status": "Active | Suspended",
  "suspension_reason": "OVERDUE_BILL | FRAUD | empty when Active",
  "roaming_enabled": "boolean",
  "data_used_gb": "float",
  "contract_end_date": "YYYY-MM-DD"
}
```

**Decision relevance:**
- `status: "Suspended"` + `suspension_reason: "OVERDUE_BILL"` -> billing recovery path
- `roaming_enabled: false` -> ENABLE_LINE_ROAMING (carrier update) or TOGGLE_ROAMING (self-service), depending on whether the line plan supports roaming
- `data_used_gb` compared to the plan's `data_limit_gb` -> refuel decision

## Devices

### `GET /api/devices/{device_id}`

```json
{
  "device_id": "DEV-xxxx",
  "model": "string",
  "sim_status": "active | missing | error",
  "signal_strength": "good | fair | poor | none",
  "mobile_data_enabled": "boolean",
  "phone_roaming_enabled": "boolean",
  "data_saver_mode": "boolean",
  "airplane_mode": "boolean",
  "network_mode_preference": "4g_5g_preferred | 3g_only | lte_only",
  "vpn_connected": "boolean",
  "wifi_calling_enabled": "boolean",
  "messaging_permissions": {
    "sms": "boolean",
    "storage": "boolean"
  },
  "can_send_mms": "boolean",
  "mmsc_url_present": "boolean",
  "speed_test": "no_connection | slow | fair | good"
}
```

**Decision relevance:** This is the primary source for device-setting fixes. Key mappings:
- `sim_status: "missing"` -> RESEAT_SIM
- `airplane_mode: true` -> TOGGLE_AIRPLANE_MODE
- `mobile_data_enabled: false` -> TOGGLE_MOBILE_DATA
- `phone_roaming_enabled: false` (while line roaming is on) -> TOGGLE_ROAMING
- `data_saver_mode: true` -> TOGGLE_DATA_SAVER
- `network_mode_preference: "3g_only"` -> SET_NETWORK_MODE
- `vpn_connected: true` -> DISCONNECT_VPN
- `messaging_permissions.storage: false` (MMS issue) -> GRANT_MESSAGING_PERMISSION with `permission: storage`
- `can_send_mms: false` or `mmsc_url_present: false` -> TRANSFER_HUMAN (carrier-level MMSC issue)

## Plans

### `GET /api/plans`

Returns an array of all plans.

### `GET /api/plans/{plan_id}`

```json
{
  "plan_id": "PLAN-xxxx",
  "name": "string",
  "data_limit_gb": "float (999 means effectively unlimited)",
  "data_refueling_price_per_gb": "float",
  "monthly_price_usd": "float"
}
```

**Decision relevance:** Compare `data_limit_gb` to the line's `data_used_gb`. If usage exceeds the limit, a data refuel is needed. Use `data_refueling_price_per_gb` to calculate the charge for a refuel of a given GB amount. Customer preferences may specify a refuel amount that differs from the default.

## Bills

### `GET /api/bills`

Returns an array of all bills. Filter by `customer_id` to find a specific customer's bills.

```json
{
  "bill_id": "BILL-xxxx",
  "customer_id": "CUST-xxxx",
  "amount_due_usd": "float",
  "due_date": "YYYY-MM-DD",
  "status": "Paid | Overdue | Pending"
}
```

**Decision relevance:** When a line is suspended for overdue payment, find the customer's bill with `status: "Overdue"`. Use `bill_id` and `amount_due_usd` for the payment request action.

## Contact-Center Cases

### `GET /api/cases`

Returns an array of all cases.

### `GET /api/cases/{case_id}`

```json
{
  "case_id": "CASE-xxxx",
  "customer_id": "CUST-xxxx",
  "line_id": "LINE-xxxx",
  "device_id": "DEV-xxxx",
  "issue_type": "NO_SERVICE | MOBILE_DATA | MMS | BILLING",
  "summary": "string",
  "customer_location": "home | abroad | office",
  "opened_at": "ISO timestamp"
}
```

**Decision relevance:** The `issue_type` and `customer_location` provide the initial routing hint, but the actual decision must be based on device, line, plan, and bill records.

## Enterprise Incidents

### `GET /api/enterprise/incidents`

Returns an array of all incidents.

### `GET /api/enterprise/incidents/{incident_id}`

```json
{
  "incident_id": "INC-xxxx",
  "enterprise_account_id": "ENT-xxxx",
  "product": "monthly_export | dashboard_refresh | ...",
  "severity": "Critical | High | Medium | Low",
  "status": "UNDER_INVESTIGATION | RESOLVED",
  "summary": "string",
  "account_owner": "string user id",
  "engineering_owner": "string user id",
  "received_at": "ISO timestamp"
}
```

**Decision relevance:** Use `severity` directly. Use `engineering_owner` and `account_owner` for assignments. Navigate to the enterprise account for `account_owner` details and `finance_owner`.

## Enterprise Accounts

### `GET /api/enterprise/accounts`

Returns an array of all enterprise accounts.

### `GET /api/enterprise/accounts/{enterprise_account_id}`

```json
{
  "enterprise_account_id": "ENT-xxxx",
  "name": "string",
  "tier": "Enterprise | Strategic",
  "account_owner": "string user id",
  "finance_owner": "string user id"
}
```

**Decision relevance:** Use `name` for channel and folder naming. Use `finance_owner` for share-permission user lists when finance review is needed.

## Export Runs

### `GET /api/enterprise/export-runs`

Returns an array of all export runs. Filter by `enterprise_account_id` and `incident_id` to find runs for a specific incident.

```json
{
  "run_id": "RUN-xxx",
  "enterprise_account_id": "ENT-xxxx",
  "incident_id": "INC-xxxx",
  "run_date": "YYYY-MM-DD",
  "status": "FAILED | SUCCEEDED",
  "failure_code": "STALE_CREDENTIAL | BUCKET_QUOTA | empty for successes",
  "exported_record_count": "integer (0 for failures)"
}
```

**Decision relevance:** Failed runs define the failure window (start date = first failed run, end date = last failed run, failed_days = count of consecutive failing days). The `failure_code` determines the root cause category. A succeeding run after the failure window confirms backfill is possible; backfill_days = failed_days. SLA credit percent comes from the SLA endpoint, not from the export runs.

## Enterprise Messages

### `GET /api/enterprise/messages`

Returns an array of all messages. Filter by incident context (channel, author, account references).

```json
{
  "message_id": "MSG-xxxx",
  "author": "string user id",
  "channel": "export-alerts-archive | account-escalations | data-platform | support",
  "body": "string",
  "created_at": "ISO timestamp"
}
```

**Decision relevance:** Messages reveal root cause context (e.g., credential rotation, bucket quota) and SLA references. Check `channel` values:
- `"export-alerts-archive"` -> signals ARCHIVED_ALERT_ROUTE contributing alert issue
- `"account-escalations"` -> may contain SLA credit information
- `"data-platform"` -> platform-level root cause details

## Enterprise SLA

### `GET /api/enterprise/sla/{enterprise_account_id}`

```json
{
  "enterprise_account_id": "ENT-xxxx",
  "credit_trigger": "string describing what triggers a credit",
  "monthly_export_credit_percent": "integer",
  "executive_contact": "email string"
}
```

**Decision relevance:** Use `monthly_export_credit_percent` as the `sla_credit_percent`. If no SLA credit entry exists for the account or the credit percent is 0, no credit applies.

## Naming Conventions

When the task provides naming-style instructions (e.g., "lowercase hyphen channel", "client-date investigation folder", "client export failure report title"), apply them to derive these values:

- **Channel name:** Lowercase, hyphenated version of the enterprise account name (e.g., "Acme Corp" -> "acme-corp")
- **Evidence folder:** "{Account Name} {Incident Month Year} Investigation" (e.g., "Acme Corp June 2026 Investigation")
- **Report title:** "{Account Name} Export Failure - Resolution Report" (e.g., "Acme Corp Export Failure - Resolution Report")

## Response Status Determination

The `response_status` for enterprise incident responses follows this logic:
- If SLA credit > 0, start with `NEEDS_FINANCE_REVIEW` (finance must approve the credit before sending)
- If engineering analysis is incomplete or root cause is uncertain, use `NEEDS_ENGINEERING_REVIEW`
- If still investigating, use `UNDER_INVESTIGATION`
- Only use `READY_TO_SEND` when all evidence is clear, owners are assigned, and no finance approval is needed

## Error Handling

- If a single-item endpoint returns 404, the referenced entity doesn't exist. Mark as FAILED with the appropriate invalidation reason.
- If the API returns an empty array for a collection, there is no data of that type. Don't fabricate records.
- If a diagnostic or troubleshooting record doesn't exist for a ticket, proceed without it; mark `diagnostic_needed` based on service type.
