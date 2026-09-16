# API Surface Reference

Complete reference for every support-console REST endpoint, its response shape,
and the field types returned. All endpoints are read-only GET. The base URL is
always provided in the prompt as `<TASK_ENV_BASE_URL>`.

## Service-ticket domain

### `GET /api/tickets/{ticket_id}`

```json
{
  "ticket_id": "string",
  "account_id": "string",
  "service_area": "string (e.g. SA-17)",
  "service_type": "internet | video | voice",
  "subscribed_mbps": "number (internet only)",
  "issue_summary": "string",
  "status": "string",
  "created_at": "ISO 8601"
}
```

### `GET /api/accounts/{account_id}`

```json
{
  "account_id": "string",
  "name": "string",
  "status": "Active | Suspended | Closed",
  "service_area": "string",
  "tier": "standard | premium",
  "authentication": {
    "last_login_status": "SUCCESS | FAILURE | LOCKED",
    "last_login_at": "ISO 8601",
    "account_recovery_status": "string"
  }
}
```

### `GET /api/diagnostics/{ticket_id}`

```json
{
  "ticket_id": "string",
  "bandwidth_mbps": "number",
  "latency_ms": "number",
  "jitter_ms": "number",
  "root_causes": ["string array -- can be empty"],
  "started_at": "ISO 8601",
  "completed_at": "ISO 8601"
}
```

Common root_causes values: `CONFIGURATION_DRIFT`, `PHYSICAL_LINE_FAULT`,
`BACKBONE_CONGESTION`, `PROVISIONING_MISMATCH`, `SIGNAL_DEGRADATION`.

### `GET /api/troubleshooting/{ticket_id}`

```json
{
  "ticket_id": "string",
  "steps": ["string array -- e.g. PROFILE_REFRESH, PROVISIONING_SYNC"],
  "post_bandwidth_mbps": "number",
  "post_latency_ms": "number",
  "post_jitter_ms": "number",
  "started_at": "ISO 8601",
  "completed_at": "ISO 8601"
}
```

### `GET /api/outages`

Returns an array of outage objects:

```json
[
  {
    "outage_id": "string (e.g. OUT-9102)",
    "service_area": "string",
    "service_types": ["string array"],
    "active": "boolean",
    "eta_hours": "number",
    "impact_score": "number (0.0-1.0)",
    "started_at": "ISO 8601"
  }
]
```

Filter rules: match `service_area` AND `service_types` contains the ticket's
`service_type`. Only `active: true` outages affect current tickets.

## Mobile / contact-center domain

### `GET /api/cases/{case_id}`

```json
{
  "case_id": "string",
  "customer_id": "string",
  "line_id": "string",
  "device_id": "string",
  "issue_type": "NO_SERVICE | NO_DATA | SLOW_DATA | CANT_SEND_MMS | BILLING | TRAVEL | UNKNOWN",
  "summary": "string",
  "customer_location": "home | traveling | office",
  "opened_at": "ISO 8601"
}
```

### `GET /api/customers/{customer_id}`

```json
{
  "customer_id": "string",
  "name": "string",
  "phone_number": "string",
  "status": "Active | Suspended"
}
```

### `GET /api/lines/{line_id}`

```json
{
  "line_id": "string",
  "customer_id": "string",
  "device_id": "string",
  "plan_id": "string",
  "phone_number": "string",
  "status": "Active | Suspended | Cancelled",
  "roaming_enabled": "boolean",
  "suspension_reason": "string (empty if active)",
  "data_used_gb": "number",
  "contract_end_date": "YYYY-MM-DD"
}
```

### `GET /api/devices/{device_id}`

```json
{
  "device_id": "string",
  "model": "string",
  "sim_status": "ready | missing | error",
  "signal_strength": "none | poor | fair | good | excellent",
  "airplane_mode": "boolean",
  "mobile_data_enabled": "boolean",
  "data_saver_mode": "boolean",
  "network_mode_preference": "string (e.g. 3g_only, 4g_5g_preferred)",
  "phone_roaming_enabled": "boolean",
  "wifi_calling_enabled": "boolean",
  "vpn_connected": "boolean",
  "can_send_mms": "boolean",
  "mmsc_url_present": "boolean",
  "messaging_permissions": {
    "sms": "boolean",
    "storage": "boolean"
  },
  "speed_test": "string"
}
```

### `GET /api/plans/{plan_id}`

```json
{
  "plan_id": "string",
  "name": "string",
  "monthly_price_usd": "number",
  "data_limit_gb": "number",
  "data_refueling_price_per_gb": "number"
}
```

### `GET /api/bills`

Returns an array of bill objects:

```json
[
  {
    "bill_id": "string",
    "customer_id": "string",
    "amount_due_usd": "number",
    "due_date": "YYYY-MM-DD",
    "status": "Paid | Overdue | Pending"
  }
]
```

Filter by matching `customer_id` against the case's customer.

## Enterprise domain

### `GET /api/enterprise/accounts/{account_id}`

```json
{
  "enterprise_account_id": "string",
  "name": "string",
  "tier": "Enterprise | Strategic",
  "account_owner": "string (user id)",
  "finance_owner": "string (user id)"
}
```

### `GET /api/enterprise/incidents/{incident_id}`

```json
{
  "incident_id": "string",
  "enterprise_account_id": "string",
  "product": "string (e.g. monthly_export)",
  "severity": "Critical | High | Medium | Low",
  "status": "UNDER_INVESTIGATION | RESOLVED | CLOSED",
  "engineering_owner": "string (user id)",
  "account_owner": "string (user id)",
  "summary": "string",
  "received_at": "ISO 8601"
}
```

### `GET /api/enterprise/export-runs`

Returns an array of export-run objects:

```json
[
  {
    "run_id": "string",
    "enterprise_account_id": "string",
    "incident_id": "string",
    "run_date": "YYYY-MM-DD",
    "status": "FAILED | SUCCEEDED",
    "failure_code": "string (empty on success)",
    "exported_record_count": "number (0 on failure)"
  }
]
```

Filter by matching `enterprise_account_id` AND `incident_id` from the incident
record. The failure window is the span from earliest FAILED to latest FAILED
`run_date`. The `failure_code` gives the root cause category (map to plain
language: `STALE_CREDENTIAL` -> "stale credential after rotation",
`STAGING_STORAGE_QUOTA` -> "staging storage quota exceeded").

### `GET /api/enterprise/messages`

Returns an array of message objects:

```json
[
  {
    "message_id": "string",
    "author": "string (user id)",
    "body": "string",
    "channel": "string (e.g. export-alerts-archive, account-escalations, data-platform)",
    "created_at": "ISO 8601"
  }
]
```

Filter by scanning `author` (match owners), `body` (product/account name), and
`channel` (look for `export-alerts-archive` for root cause messages and
`account-escalations` for SLA credit messages).

### `GET /api/enterprise/sla/{enterprise_account_id}`

```json
{
  "enterprise_account_id": "string",
  "credit_trigger": "string (e.g. '3 consecutive failed export runs')",
  "monthly_export_credit_percent": "number",
  "executive_contact": "string (email)"
}
```

## Supplementary list endpoints

### `GET /api/accounts`

Returns array of all account objects. Used for existence checks.

### `GET /api/customers`

Returns array of all customer objects.

### `GET /api/lines`

Returns array of all line objects. Not listed in catalog but available.

### `GET /api/catalog`

Informational only. Returns the endpoint list and record counts. Not evidence
for decisions.
