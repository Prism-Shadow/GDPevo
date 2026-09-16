# Support Console API Reference

This reference documents the REST endpoints of the shared support-console API.
All endpoints are read-only GET calls with no authentication required. The base
URL is provided as `<TASK_ENV_BASE_URL>` in every task. Replace that token
literally in every request.

Always start by reading the catalog to confirm which endpoints are live.

## Catalog

```
GET <TASK_ENV_BASE_URL>/api/catalog
```

Returns:

| Field | Type | Meaning |
|-------|------|---------|
| endpoints | string[] | Live API paths |
| generated_at | ISO 8601 string | Catalog generation timestamp |
| notes | string | Usage notes |
| record_counts | object | Count of records per domain |

The catalog is the authoritative list of endpoints for the current environment.
Use it to plan your fetch set; do not assume a fixed list.

## Ticket & Account Domain

### GET /api/tickets/<ticket_id>

| Field | Type | Meaning |
|-------|------|---------|
| ticket_id | string | Ticket identifier |
| account_id | string | Owning account; use for account lookup |
| created_at | ISO 8601 string | When the ticket was opened |
| issue_summary | string | Brief description of the reported problem |
| service_area | string | e.g. "SA-17"; key for outage matching |
| service_type | string | "internet", "video", or "voice" |
| status | string | Usually "OPEN" for unresolved tickets |
| subscribed_mbps | number | Contracted bandwidth in Mbps |

### GET /api/accounts/<account_id>

Returns 404 / error when the account does not exist or is unreachable.

| Field | Type | Meaning |
|-------|------|---------|
| account_id | string | Account identifier |
| authentication | object | See authentication sub-object |
| name | string | Account display name |
| service_area | string | Service area code |
| status | string | "Active" or "Suspended" |
| tier | string | "standard" or "Enterprise" |

Authentication sub-object:

| Field | Type | Meaning |
|-------|------|---------|
| account_recovery_status | string | Empty when normal |
| last_login_at | ISO 8601 string | Last login timestamp |
| last_login_status | string | "SUCCESS" or "FAILURE" |

Key decision signals:
- Account not found (404) -> invalid / ineligible account
- `status` is "Suspended" -> account is blocked
- `last_login_status` is "FAILURE" -> authentication problem

### GET /api/diagnostics/<ticket_id>

May still return data even for suspended or invalid accounts; always attempt
this call.

| Field | Type | Meaning |
|-------|------|---------|
| ticket_id | string | Ticket identifier |
| bandwidth_mbps | number | Measured bandwidth |
| jitter_ms | number | Jitter in milliseconds |
| latency_ms | number | Latency in milliseconds |
| root_causes | string[] | Root cause codes; see Root Causes table |
| started_at | ISO 8601 string | Diagnostic start time |
| completed_at | ISO 8601 string | Diagnostic end time |

Root causes:

| Code | Meaning | Resolution path |
|------|---------|----------------|
| GENERATED_NOISE | Non-actionable noise; no real diagnostic signal | Treat as if diagnostics returned nothing useful |
| CONFIGURATION_DRIFT | Config mismatch that auto-troubleshooting can fix | Apply the troubleshooting steps |
| PROVISIONING_STALE | Stale provisioning record | Escalate to TIER2_SUPPORT |
| FIBER_DROP_DAMAGE | Physical fiber damage | Escalate to FIELD_OPS |
| SIGNAL_LOSS | Signal degradation | Escalate to FIELD_OPS (often paired with FIBER_DROP_DAMAGE) |
| BACKBONE_CAPACITY | Backbone capacity exhaustion | Escalate to NETWORK_ENGINEERING |

### GET /api/troubleshooting/<ticket_id>

Returns troubleshooting results. The troubleshooting endpoint may not exist for
every ticket; check the catalog and the diagnostic root causes before calling.

| Field | Type | Meaning |
|-------|------|---------|
| ticket_id | string | Ticket identifier |
| started_at | ISO 8601 string | Troubleshooting start |
| completed_at | ISO 8601 string | Troubleshooting end |
| steps | string[] | Steps taken (e.g. PROFILE_REFRESH, PROVISIONING_SYNC, LINE_TEST, SIGNAL_REFRESH) |
| post_bandwidth_mbps | number | Bandwidth after fix |
| post_jitter_ms | number | Jitter after fix |
| post_latency_ms | number | Latency after fix |

Evaluate post values against the ticket thresholds to determine whether the fix
stuck. If post values are still degraded, escalation may be appropriate.

### GET /api/outages

Returns the full outage list as an array. No single-outage endpoint is
available; filter the list by `service_area` and check `active` and
`service_types`.

| Field | Type | Meaning |
|-------|------|---------|
| outage_id | string | e.g. "OUT-9102" |
| active | boolean | Whether the outage is ongoing |
| eta_hours | number | Estimated resolution hours |
| impact_score | number | 0.0-1.0 severity |
| service_area | string | Affected area; match against ticket.service_area |
| service_types | string[] | Affected service types; check includes ticket.service_type |
| started_at | ISO 8601 string | Outage start time |

A ticket is blocked by an outage when there is an active outage whose
`service_area` matches the ticket's `service_area` and whose `service_types`
array contains the ticket's `service_type`.

## Contact Center Domain

### GET /api/cases/<case_id>

Also available as a collection at `/api/cases`.

| Field | Type | Meaning |
|-------|------|---------|
| case_id | string | Case identifier |
| customer_id | string | Link to customer record |
| line_id | string | Link to line record |
| device_id | string | Link to device record |
| customer_location | string | "home" or "abroad" |
| issue_type | string | "NO_SERVICE", "MOBILE_DATA", "MMS", "SLOW_DATA" |
| opened_at | ISO 8601 string | When the case was opened |
| summary | string | Human-readable issue description |

### GET /api/customers/<customer_id>

| Field | Type | Meaning |
|-------|------|---------|
| customer_id | string | Customer identifier |
| name | string | Customer name |
| phone_number | string | Phone number |
| status | string | Usually "Active" |

### GET /api/lines/<line_id>

| Field | Type | Meaning |
|-------|------|---------|
| line_id | string | Line identifier |
| customer_id | string | Owning customer |
| device_id | string | Associated device |
| plan_id | string | Plan identifier (e.g. "PLAN-PREMIUM") |
| phone_number | string | Phone number |
| data_used_gb | number | Monthly data consumption |
| roaming_enabled | boolean | Whether carrier-side roaming is on |
| status | string | "Active" or "Suspended" |
| suspension_reason | string | Empty when active; "OVERDUE_BILL" when suspended |
| contract_end_date | string | "YYYY-MM-DD" |

### GET /api/devices/<device_id>

| Field | Type | Meaning |
|-------|------|---------|
| device_id | string | Device identifier |
| model | string | Device model name |
| sim_status | string | "active" or "missing" |
| mobile_data_enabled | boolean | Master data switch |
| phone_roaming_enabled | boolean | Device-side roaming toggle |
| data_saver_mode | boolean | Data saver feature state |
| network_mode_preference | string | "4g_5g_preferred", "3g_only", etc. |
| vpn_connected | boolean | Whether a VPN is active on the device |
| can_send_mms | boolean | MMS capability |
| mmsc_url_present | boolean | MMSC configuration present |
| messaging_permissions | object | { sms, storage } boolean flags |
| signal_strength | string | "none", "poor", "fair", "good", "excellent" |
| speed_test | string | "no_connection", "poor", "fair", "excellent" |
| airplane_mode | boolean | Airplane mode state |
| wifi_calling_enabled | boolean | WiFi calling state |

### GET /api/bills

Returns the full bill list. Filter by `customer_id` to find bills for a given
customer.

| Field | Type | Meaning |
|-------|------|---------|
| bill_id | string | Bill identifier |
| customer_id | string | Owning customer |
| amount_due_usd | number | Amount outstanding |
| due_date | string | "YYYY-MM-DD" |
| status | string | "Overdue" or "Paid" |

### GET /api/plans/<plan_id>

| Field | Type | Meaning |
|-------|------|---------|
| plan_id | string | Plan identifier |
| name | string | Human-readable plan name |
| data_limit_gb | number | Monthly data cap in GB |
| data_refueling_price_per_gb | number | Price per GB for refueling |
| monthly_price_usd | number | Monthly subscription price |

## Enterprise Domain

### GET /api/enterprise/incidents/<incident_id>

| Field | Type | Meaning |
|-------|------|---------|
| incident_id | string | Incident identifier |
| enterprise_account_id | string | Owning enterprise account |
| product | string | Affected product (e.g. "monthly_export") |
| severity | string | "Critical", "High", "Medium", "Low" |
| status | string | Current incident status |
| summary | string | Incident description |
| received_at | ISO 8601 string | When the incident was reported |
| engineering_owner | string | Engineering owner user ID |
| account_owner | string | Account owner user ID |

### GET /api/enterprise/accounts/<enterprise_account_id>

| Field | Type | Meaning |
|-------|------|---------|
| enterprise_account_id | string | Enterprise account identifier |
| name | string | Enterprise client name |
| tier | string | "Enterprise" or "Strategic" |
| account_owner | string | Account owner user ID |
| finance_owner | string | Finance owner user ID |

### GET /api/enterprise/export-runs

Returns the full export runs list. Filter by `enterprise_account_id` to find
runs for a specific account.

| Field | Type | Meaning |
|-------|------|---------|
| run_id | string | Export run identifier |
| enterprise_account_id | string | Owning enterprise account |
| incident_id | string | Associated incident |
| run_date | string | "YYYY-MM-DD" of the run |
| status | string | "FAILED" or "SUCCEEDED" |
| failure_code | string | Empty on success; e.g. "STALE_CREDENTIAL" |
| exported_record_count | number | Records exported (0 on failure) |

### GET /api/enterprise/messages

Returns the full message list. Filter by the enterprise account, incident ID,
or channel name to find relevant messages.

| Field | Type | Meaning |
|-------|------|---------|
| message_id | string | Message identifier |
| author | string | Author user ID |
| body | string | Message text |
| channel | string | Channel name (lowercase, hyphens) |
| created_at | ISO 8601 string | Message timestamp |

### GET /api/enterprise/sla/<enterprise_account_id>

| Field | Type | Meaning |
|-------|------|---------|
| enterprise_account_id | string | Enterprise account identifier |
| credit_trigger | string | Condition that activates the SLA credit |
| monthly_export_credit_percent | number | Credit percentage owed |
| executive_contact | string | Executive email |

## Record Identifier Correlation

Records link through these foreign-key relationships:

- **ticket** -> **account**: `ticket.account_id` = `account.account_id`
- **ticket** -> **outage**: `ticket.service_area` = `outage.service_area`
- **case** -> **customer**: `case.customer_id` = `customer.customer_id`
- **case** -> **line**: `case.line_id` = `line.line_id`
- **case** -> **device**: `case.device_id` = `device.device_id`
- **line** -> **plan**: `line.plan_id` = `plan.plan_id`
- **line** -> **device**: `line.device_id` = `device.device_id`
- **line** -> **customer**: `line.customer_id` = `customer.customer_id`
- **bill** -> **customer**: `bill.customer_id` = `customer.customer_id`
- **incident** -> **enterprise account**: `incident.enterprise_account_id` = `enterprise_account.enterprise_account_id`
- **export run** -> **enterprise account** and **incident**: via `enterprise_account_id` and `incident_id`
- **SLA contract** -> **enterprise account**: via `enterprise_account_id`

When the worklist provides a ticket_id, follow the chain: ticket -> account,
ticket -> diagnostics, ticket -> troubleshooting, account -> via service_area
to outages. When the worklist provides a case_id, follow case -> customer, case
-> line, line -> device, line -> plan, and customer -> bills when relevant.
