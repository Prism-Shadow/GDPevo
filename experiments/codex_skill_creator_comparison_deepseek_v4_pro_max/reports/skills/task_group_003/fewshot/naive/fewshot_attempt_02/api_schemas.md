# API Response Schemas

Expected response shapes for each endpoint. All endpoints return JSON.
Array endpoints return `[]`; singleton endpoints return `{}`.

## Account endpoints

### GET /api/accounts
Array of:
```json
{
  "account_id": "string",
  "name": "string",
  "service_area": "string",
  "status": "Active | Suspended",
  "tier": "string",
  "authentication": {
    "last_login_at": "ISO-8601",
    "last_login_status": "SUCCESS | FAILURE",
    "account_recovery_status": "string"
  }
}
```

### GET /api/accounts/{account_id}
Single object as above. Returns 404 for invalid account IDs.

## Ticket endpoints

### GET /api/tickets
Array of:
```json
{
  "ticket_id": "string",
  "account_id": "string",
  "created_at": "ISO-8601",
  "issue_summary": "string",
  "service_area": "string",
  "service_type": "internet | video | voice",
  "status": "OPEN | CLOSED",
  "subscribed_mbps": "number"
}
```

### GET /api/tickets/{ticket_id}
Single object as above.

## Diagnostic endpoints

### GET /api/diagnostics/{ticket_id}
Single object:
```json
{
  "ticket_id": "string",
  "started_at": "ISO-8601",
  "completed_at": "ISO-8601",
  "latency_ms": "number",
  "jitter_ms": "number",
  "bandwidth_mbps": "number",
  "root_causes": ["string array"]
}
```
Common `root_causes` values: `CONFIGURATION_DRIFT`, `VOICE_PROFILE_STALE`,
`FIBER_DROP_DAMAGE`, `SIGNAL_LOSS`, `BACKBONE_CAPACITY`, `PROVISIONING_STALE`,
`GENERATED_NOISE`.

### GET /api/troubleshooting/{ticket_id}
Single object:
```json
{
  "ticket_id": "string",
  "started_at": "ISO-8601",
  "completed_at": "ISO-8601",
  "steps": ["string array"],
  "post_bandwidth_mbps": "number",
  "post_jitter_ms": "number",
  "post_latency_ms": "number"
}
```

## Outage endpoints

### GET /api/outages
Array of:
```json
{
  "outage_id": "string",
  "active": "boolean",
  "service_area": "string",
  "service_types": ["string array"],
  "started_at": "ISO-8601",
  "eta_hours": "number",
  "impact_score": "number"
}
```

## Customer, Line, Device, Plan, Bill endpoints

### GET /api/customers
Array of:
```json
{
  "customer_id": "string",
  "name": "string",
  "phone_number": "string",
  "status": "Active | Suspended"
}
```

### GET /api/lines
Array of:
```json
{
  "line_id": "string",
  "customer_id": "string",
  "device_id": "string",
  "phone_number": "string",
  "plan_id": "string",
  "status": "Active | Suspended",
  "suspension_reason": "string (empty when Active)",
  "roaming_enabled": "boolean",
  "data_used_gb": "number",
  "contract_end_date": "YYYY-MM-DD"
}
```

### GET /api/lines/{line_id}
Single object as above.

### GET /api/devices/{device_id}
Single object:
```json
{
  "device_id": "string",
  "model": "string",
  "sim_status": "active | missing",
  "airplane_mode": "boolean",
  "mobile_data_enabled": "boolean",
  "data_saver_mode": "boolean",
  "network_mode_preference": "4g_5g_preferred | 3g_only | 2g_only",
  "phone_roaming_enabled": "boolean",
  "vpn_connected": "boolean",
  "wifi_calling_enabled": "boolean",
  "signal_strength": "none | poor | fair | good | excellent",
  "speed_test": "no_connection | poor | fair | good | excellent",
  "can_send_mms": "boolean",
  "mmsc_url_present": "boolean",
  "messaging_permissions": {
    "sms": "boolean",
    "storage": "boolean"
  }
}
```

### GET /api/plans/{plan_id}
Single object:
```json
{
  "plan_id": "string",
  "name": "string",
  "monthly_price_usd": "number",
  "data_limit_gb": "number",
  "data_refueling_price_per_gb": "number"
}
```

### GET /api/bills
Array of:
```json
{
  "bill_id": "string",
  "customer_id": "string",
  "due_date": "YYYY-MM-DD",
  "amount_due_usd": "number",
  "status": "Paid | Overdue"
}
```

## Case endpoints

### GET /api/cases
Array of:
```json
{
  "case_id": "string",
  "customer_id": "string",
  "line_id": "string",
  "device_id": "string",
  "opened_at": "ISO-8601",
  "issue_type": "NO_SERVICE | MOBILE_DATA | SLOW_DATA",
  "customer_location": "home | abroad",
  "summary": "string"
}
```

### GET /api/cases/{case_id}
Single object as above.

## Enterprise endpoints

### GET /api/enterprise/accounts
Array of:
```json
{
  "enterprise_account_id": "string",
  "name": "string",
  "tier": "Enterprise | Strategic",
  "account_owner": "string",
  "finance_owner": "string"
}
```

### GET /api/enterprise/accounts/{account_id}
Single object as above.

### GET /api/enterprise/incidents
Array of:
```json
{
  "incident_id": "string",
  "enterprise_account_id": "string",
  "engineering_owner": "string",
  "account_owner": "string",
  "product": "string",
  "severity": "Critical | High | Medium | Low",
  "status": "string",
  "summary": "string",
  "received_at": "ISO-8601"
}
```

### GET /api/enterprise/incidents/{incident_id}
Single object as above.

### GET /api/enterprise/export-runs
Array of:
```json
{
  "run_id": "string",
  "incident_id": "string",
  "enterprise_account_id": "string",
  "run_date": "YYYY-MM-DD",
  "status": "FAILED | SUCCEEDED",
  "failure_code": "string (empty when SUCCEEDED)",
  "exported_record_count": "number"
}
```

### GET /api/enterprise/messages
Array of:
```json
{
  "message_id": "string",
  "author": "string",
  "body": "string",
  "channel": "string",
  "created_at": "ISO-8601"
}
```

### GET /api/enterprise/sla/{enterprise_account_id}
Single object:
```json
{
  "enterprise_account_id": "string",
  "executive_contact": "string",
  "credit_trigger": "string",
  "monthly_export_credit_percent": "number"
}
```
