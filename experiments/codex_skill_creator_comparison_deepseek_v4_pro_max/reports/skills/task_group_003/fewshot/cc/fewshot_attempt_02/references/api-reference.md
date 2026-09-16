# Support Console API Reference

This reference documents the shared telecom support-console REST API. Use it to understand endpoint shapes, response fields, and inter-entity relationships.

The API base URL is provided in the task prompt as `<TASK_ENV_BASE_URL>`. All endpoints are GET requests. No authentication is needed.

## Entity relationship diagram

```
Account  ─── Ticket (via account_id)
Account  ─── Customer (via name/account_id for enterprise)
Customer ─── Line (via customer_id)
Line     ─── Device (via device_id)
Line     ─── Plan (via plan_id)
Line     ─── Bill (via customer_id, bill_id)
Case     ─── Customer (via customer_id)
Case     ─── Line (via line_id)
Case     ─── Device (via device_id)

Enterprise Account ─── Incident (via enterprise_account_id)
Incident ─── Export Runs (via incident_id)
Enterprise Account ─── Messages (via enterprise_account_id)
Enterprise Account ─── SLA (via enterprise_account_id)

Diagnostics ─── Ticket (via ticket_id)
Troubleshooting ─── Ticket (via ticket_id)
Outages ─── Service Area (via service_area)
```

## Core endpoints

### GET /api/catalog

Returns the endpoint list and record counts. Always call this first in a new task to confirm the API is reachable.

**Response fields:** `endpoints` (list of paths), `generated_at`, `notes`, `record_counts` (map of entity type → count).

### GET /api/tickets

Returns all tickets. Each ticket has:

| Field | Type | Description |
|-------|------|-------------|
| `ticket_id` | string | Primary key |
| `account_id` | string | FK to Account |
| `created_at` | datetime | |
| `issue_summary` | string | |
| `service_area` | string | Geographic/service area |
| `service_type` | string | internet, video, voice |
| `status` | string | OPEN, CLOSED |
| `subscribed_mbps` | integer | Subscribed bandwidth |

### GET /api/tickets/{ticket_id}

Single ticket record. Same shape as the list element.

### GET /api/accounts

Returns all accounts. Each account has:

| Field | Type | Description |
|-------|------|-------------|
| `account_id` | string | Primary key |
| `name` | string | Account name |
| `service_area` | string | |
| `status` | string | Active, Suspended, etc. |
| `tier` | string | standard, premium, enterprise |
| `authentication` | object | `{last_login_at, last_login_status, account_recovery_status}` |

### GET /api/accounts/{account_id}

Single account record.

### GET /api/diagnostics/{ticket_id}

Diagnostic results for a ticket. Returns 404 if no diagnostics are available.

| Field | Type | Description |
|-------|------|-------------|
| `ticket_id` | string | |
| `started_at` | datetime | |
| `completed_at` | datetime | |
| `bandwidth_mbps` | float | Measured bandwidth |
| `latency_ms` | float | Measured latency |
| `jitter_ms` | float | Measured jitter |
| `root_causes` | array of strings | e.g., CONFIGURATION_DRIFT, BACKBONE_CONGESTION, PHY_FAULT |

### GET /api/troubleshooting/{ticket_id}

Troubleshooting history. Returns 404 if none available.

| Field | Type | Description |
|-------|------|-------------|
| `ticket_id` | string | |
| `started_at` | datetime | |
| `completed_at` | datetime | |
| `steps` | array | e.g., PROFILE_REFRESH, PROVISIONING_SYNC |
| `post_bandwidth_mbps` | float | |
| `post_latency_ms` | float | |
| `post_jitter_ms` | float | |

### GET /api/outages

Returns all outages. Filter to `active: true` when checking for current outages.

| Field | Type | Description |
|-------|------|-------------|
| `outage_id` | string | |
| `active` | boolean | |
| `eta_hours` | integer | |
| `impact_score` | float | 0-1 |
| `service_area` | string | |
| `service_types` | array of strings | internet, video, voice |
| `started_at` | datetime | |

## Contact-center endpoints

### GET /api/contact-center/cases

Returns all cases. Each case has:

| Field | Type | Description |
|-------|------|-------------|
| `case_id` | string | Primary key |
| `customer_id` | string | FK to Customer |
| `customer_location` | string | home, office, traveling |
| `device_id` | string | FK to Device |
| `issue_type` | string | NO_SERVICE, SLOW_DATA, BILLING, etc. |
| `line_id` | string | FK to Line |
| `opened_at` | datetime | |
| `summary` | string | |

### GET /api/contact-center/cases/{case_id}

Single case record.

### GET /api/customers

Returns all customers.

| Field | Type | Description |
|-------|------|-------------|
| `customer_id` | string | Primary key |
| `name` | string | |
| `phone_number` | string | |
| `status` | string | Active, Suspended |

### GET /api/customers/{customer_id}

Single customer.

### GET /api/lines

Returns all lines.

| Field | Type | Description |
|-------|------|-------------|
| `line_id` | string | Primary key |
| `customer_id` | string | FK to Customer |
| `device_id` | string | FK to Device |
| `plan_id` | string | FK to Plan |
| `phone_number` | string | |
| `status` | string | Active, Suspended |
| `suspension_reason` | string | Empty when not suspended |
| `contract_end_date` | date | |
| `data_used_gb` | float | |
| `roaming_enabled` | boolean | Line-side roaming toggle |

### GET /api/lines/{line_id}

Single line.

### GET /api/devices/{device_id}

Device state.

| Field | Type | Description |
|-------|------|-------------|
| `device_id` | string | |
| `model` | string | |
| `sim_status` | string | present, missing |
| `airplane_mode` | boolean | |
| `mobile_data_enabled` | boolean | |
| `phone_roaming_enabled` | boolean | Device-side roaming |
| `data_saver_mode` | boolean | |
| `vpn_connected` | boolean | |
| `network_mode_preference` | string | e.g., 4g_5g_preferred, 3g_only |
| `wifi_calling_enabled` | boolean | |
| `signal_strength` | string | none, low, medium, high |
| `speed_test` | string | no_connection, slow, normal |
| `can_send_mms` | boolean | |
| `mmsc_url_present` | boolean | |
| `messaging_permissions` | object | `{sms, storage}` both booleans |

### GET /api/bills/{bill_id}

Bill record.

| Field | Type | Description |
|-------|------|-------------|
| `bill_id` | string | |
| `customer_id` | string | |
| `amount_due_usd` | float | |
| `due_date` | date | |
| `status` | string | Paid, Overdue, Pending |

### GET /api/plans/{plan_id}

Plan details.

| Field | Type | Description |
|-------|------|-------------|
| `plan_id` | string | |
| `name` | string | |
| `data_limit_gb` | float | |
| `monthly_price_usd` | float | |
| `data_refueling_price_per_gb` | float | Price per GB for overage/refuel |

## Enterprise endpoints

### GET /api/enterprise/accounts

Returns all enterprise accounts.

| Field | Type | Description |
|-------|------|-------------|
| `enterprise_account_id` | string | |
| `name` | string | |
| `tier` | string | |
| `account_owner` | string | User ID |
| `finance_owner` | string | User ID |

### GET /api/enterprise/accounts/{enterprise_account_id}

Single enterprise account.

### GET /api/enterprise/incidents/{incident_id}

Incident record.

| Field | Type | Description |
|-------|------|-------------|
| `incident_id` | string | |
| `enterprise_account_id` | string | |
| `product` | string | e.g., monthly_export |
| `summary` | string | |
| `severity` | string | Critical, High, Medium, Low |
| `status` | string | |
| `engineering_owner` | string | User ID |
| `account_owner` | string | User ID |
| `received_at` | datetime | |

### GET /api/enterprise/export-runs?enterprise_account_id={id}

All export runs for an account. Filter client-side by `incident_id` to get runs for a specific incident.

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | string | |
| `enterprise_account_id` | string | |
| `incident_id` | string | |
| `run_date` | date | |
| `status` | string | SUCCEEDED, FAILED |
| `failure_code` | string | Empty on success |
| `exported_record_count` | integer | 0 on failure |

### GET /api/enterprise/messages?enterprise_account_id={id}

All messages for an account. Filter client-side by relevance.

| Field | Type | Description |
|-------|------|-------------|
| `message_id` | string | |
| `author` | string | |
| `body` | string | |
| `channel` | string | |
| `created_at` | datetime | |

### GET /api/enterprise/sla/{enterprise_account_id}

SLA contract.

| Field | Type | Description |
|-------|------|-------------|
| `enterprise_account_id` | string | |
| `credit_trigger` | string | Description of trigger condition |
| `executive_contact` | string | Email |
| `monthly_export_credit_percent` | integer | For monthly_export product |

## Common root causes from diagnostics

The `root_causes` array in diagnostics returns codes. Here is what they mean:

| Code | Meaning | Typical resolution |
|------|---------|-------------------|
| CONFIGURATION_DRIFT | Settings drifted from profile | Auto-troubleshooting (PROFILE_REFRESH + PROVISIONING_SYNC) |
| BACKBONE_CONGESTION | Backbone capacity saturated | Escalate to NETWORK_ENGINEERING |
| PHY_FAULT | Physical line damage/degradation | Escalate to FIELD_OPS |
| PROVISIONING_STALE | Provisioning out of sync | Escalate to TIER2_SUPPORT |

## Common export failure codes

| Code | Meaning | Root cause category |
|------|---------|-------------------|
| STALE_CREDENTIAL | Credentials rotated, scheduler not updated | stale credential after rotation |
| STAGING_STORAGE_QUOTA | Export storage bucket full | storage quota exceeded |
| RATE_LIMIT | API rate limiting | rate limit |
| TIMEOUT | Export job timed out | timeout |

## Boolean flag thresholds for diagnostics

When a ticket template asks for `latency_issue`, `stability_issue`, `bandwidth_issue`:

- **latency_issue**: `true` when `latency_ms` > 80
- **stability_issue**: `true` when `jitter_ms` > 20
- **bandwidth_issue**: `true` when `bandwidth_mbps` < 80% of `subscribed_mbps`

When none of these thresholds is exceeded but root causes suggest a recoverable problem, the ticket may still be RESOLVED via AUTO_TROUBLESHOOTING.

## Common channel naming pattern

For enterprise incident responses, the channel name follows this pattern:
Take the enterprise account name, convert to lowercase, replace spaces with hyphens.
Example: "Acme Corp." → "acme-corp"

## Evidence folder and report title patterns

- `evidence_folder`: "[Account Name] [Month YYYY] Investigation" — month and year come from the failure window start date.
- `report_title`: "[Account Name] Export Failure - Resolution Report"
