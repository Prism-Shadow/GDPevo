# Support Console API Schemas

Every endpoint returns JSON. Single-item lookups return the record object; list endpoints return an array. Use `jq` or string filtering when searching list responses. All IDs follow a consistent prefix pattern (e.g., `TCK-`, `ACC-`, `CUST-`, `LINE-`, `DEV-`, `PLAN-`, `BILL-`, `CASE-`, `ENT-`, `INC-`, `RUN-`, `OUT-`, `MSG-`).

## Tickets

### List: `GET /api/tickets`

Returns an array. Each ticket has:

| Field | Type | Description |
|---|---|---|
| ticket_id | string | Unique ticket identifier |
| account_id | string | Owning account ID |
| created_at | string (ISO 8601) | Ticket creation timestamp |
| issue_summary | string | Brief problem description |
| service_area | string | Geographic area code (e.g., SA-17) |
| service_type | string | One of: `internet`, `video`, `voice` |
| status | string | Ticket status (typically `OPEN`) |
| subscribed_mbps | number | Subscribed bandwidth in Mbps |

### Single: `GET /api/tickets/{ticket_id}`

Same fields as list item.

## Accounts

### Single: `GET /api/accounts/{account_id}`

Returns 404 `{"error": "not_found"}` for invalid accounts.

| Field | Type | Description |
|---|---|---|
| account_id | string | Account identifier |
| name | string | Business/account name |
| service_area | string | Area code |
| status | string | `Active`, `Suspended`, or similar |
| tier | string | Service tier (e.g., `standard`, `Enterprise`) |
| authentication | object | Contains `last_login_at`, `last_login_status`, `account_recovery_status` |

## Outages

### List: `GET /api/outages`

Returns an array. Each outage has:

| Field | Type | Description |
|---|---|---|
| outage_id | string | Unique outage identifier |
| active | boolean | Whether the outage is ongoing |
| eta_hours | number | Estimated hours to resolution |
| impact_score | number (0–1) | Severity score |
| service_area | string | Affected area code |
| service_types | array of strings | Affected service types |
| started_at | string (ISO 8601) | Outage start time |

Match tickets to outages by `service_area` overlapping AND `service_types` containing the ticket's `service_type`. Only `active: true` outages block resolution.

## Diagnostics

### Single: `GET /api/diagnostics/{ticket_id}`

| Field | Type | Description |
|---|---|---|
| ticket_id | string | Ticket identifier |
| bandwidth_mbps | number | Measured bandwidth |
| latency_ms | number | Measured latency in ms |
| jitter_ms | number | Measured jitter in ms |
| root_causes | array of strings | Detected root cause codes |
| started_at | string (ISO 8601) | Diagnostic start |
| completed_at | string (ISO 8601) | Diagnostic completion |

Root cause codes include: `CONFIGURATION_DRIFT`, `FIBER_DROP_DAMAGE`, `SIGNAL_LOSS`, `BACKBONE_CAPACITY`, `NETWORK_CAPACITY`, `PROVISIONING_STALE`, `VOICE_PROFILE_STALE`, `PHYSICAL_LINE_FAULT`, `GENERATED_NOISE` (non-deterministic, treat as noise).

## Troubleshooting

### Single: `GET /api/troubleshooting/{ticket_id}`

| Field | Type | Description |
|---|---|---|
| ticket_id | string | Ticket identifier |
| steps | array of strings | Actions taken |
| post_bandwidth_mbps | number | Bandwidth after fix |
| post_latency_ms | number | Latency after fix |
| post_jitter_ms | number | Jitter after fix |
| started_at | string (ISO 8601) | Troubleshooting start |
| completed_at | string (ISO 8601) | Troubleshooting completion |

Compare post values against diagnostic values to gauge improvement. Steps include: `PROFILE_REFRESH`, `PROVISIONING_SYNC`, `LINE_TEST`, `SIGNAL_REFRESH`, `VOICE_PROFILE_REFRESH`, `BACKBONE_REROUTE_ATTEMPT`, `PROVISIONING_ADJUSTMENT`, `GENERATED_CHECK` (non-deterministic, ignore).

## Customers

### List: `GET /api/customers`

Returns an array. Each customer has:

| Field | Type | Description |
|---|---|---|
| customer_id | string | Customer identifier |
| name | string | Customer name |
| phone_number | string | Phone number |
| status | string | Usually `Active` |

### Single: `GET /api/customers/{customer_id}`

Same fields.

## Lines

### List: `GET /api/lines`

### Single: `GET /api/lines/{line_id}`

| Field | Type | Description |
|---|---|---|
| line_id | string | Line identifier |
| customer_id | string | Owning customer |
| device_id | string | Associated device |
| plan_id | string | Associated plan |
| phone_number | string | Phone number |
| status | string | `Active`, `Suspended` |
| suspension_reason | string | `OVERDUE_BILL`, `FRAUD`, or empty |
| roaming_enabled | boolean | Line-level roaming toggle |
| data_used_gb | number | Current billing cycle data usage |
| contract_end_date | string | Contract end date |

## Devices

### Single: `GET /api/devices/{device_id}`

| Field | Type | Description |
|---|---|---|
| device_id | string | Device identifier |
| model | string | Device model name |
| sim_status | string | `active`, `missing` |
| signal_strength | string | `none`, `poor`, `fair`, `good`, `excellent` |
| speed_test | string | `no_connection`, `poor`, `fair`, `good`, `excellent` |
| mobile_data_enabled | boolean | Device-side mobile data toggle |
| phone_roaming_enabled | boolean | Device-side roaming toggle |
| airplane_mode | boolean | Airplane mode state |
| vpn_connected | boolean | VPN active |
| data_saver_mode | boolean | Data saver active |
| wifi_calling_enabled | boolean | WiFi calling state |
| network_mode_preference | string | `4g_5g_preferred`, `3g_only`, etc. |
| can_send_mms | boolean | MMS capability |
| mmsc_url_present | boolean | MMSC configured |
| messaging_permissions | object | `{sms: boolean, storage: boolean}` |

## Plans

### Single: `GET /api/plans/{plan_id}`

| Field | Type | Description |
|---|---|---|
| plan_id | string | Plan identifier |
| name | string | Plan name |
| monthly_price_usd | number | Monthly cost |
| data_limit_gb | number | Monthly data cap in GB |
| data_refueling_price_per_gb | number | Cost per additional GB |

## Bills

### List: `GET /api/bills`

| Field | Type | Description |
|---|---|---|
| bill_id | string | Bill identifier |
| customer_id | string | Customer |
| amount_due_usd | number | Amount owed |
| due_date | string | Due date |
| status | string | `Paid`, `Overdue`, `Issued` |

### Single: `GET /api/bills/{bill_id}`

Same fields.

## Contact-Center Cases

### Single: `GET /api/contact-center/cases/{case_id}`

| Field | Type | Description |
|---|---|---|
| case_id | string | Case identifier |
| customer_id | string | Customer |
| line_id | string | Line |
| device_id | string | Device |
| issue_type | string | `NO_SERVICE`, `MOBILE_DATA`, `SLOW_DATA`, `MMS` |
| customer_location | string | `home`, `abroad` |
| summary | string | Issue description |
| opened_at | string (ISO 8601) | Case open time |

## Enterprise Accounts

### List: `GET /api/enterprise/accounts`

### Single: `GET /api/enterprise/accounts/{account_id}`

| Field | Type | Description |
|---|---|---|
| enterprise_account_id | string | Account identifier |
| name | string | Organization name |
| tier | string | Service tier |
| account_owner | string | User ID of account owner |
| finance_owner | string | User ID of finance contact (optional) |

## Enterprise Incidents

### List: `GET /api/enterprise/incidents`

### Single: `GET /api/enterprise/incidents/{incident_id}`

| Field | Type | Description |
|---|---|---|
| incident_id | string | Incident identifier |
| enterprise_account_id | string | Owning enterprise account |
| product | string | Affected product (e.g., `monthly_export`) |
| severity | string | `Critical`, `High`, `Medium`, `Low` |
| status | string | Incident status |
| summary | string | Description |
| account_owner | string | User ID |
| engineering_owner | string | User ID |
| received_at | string (ISO 8601) | When reported |

## Export Runs

### List: `GET /api/enterprise/export-runs`

| Field | Type | Description |
|---|---|---|
| run_id | string | Run identifier |
| enterprise_account_id | string | Enterprise account |
| incident_id | string | Associated incident |
| run_date | string (YYYY-MM-DD) | Date of run |
| status | string | `SUCCEEDED`, `FAILED` |
| failure_code | string | `STALE_CREDENTIAL`, `STAGING_STORAGE_QUOTA`, `RATE_LIMIT`, `TIMEOUT`, or empty |
| exported_record_count | number | Records exported (0 on failure) |

## Messages

### List: `GET /api/enterprise/messages`

| Field | Type | Description |
|---|---|---|
| message_id | string | Message identifier |
| author | string | User ID of author |
| body | string | Message content |
| channel | string | Channel name |
| created_at | string (ISO 8601) | Timestamp |

## SLA Contracts

### Single: `GET /api/enterprise/sla/{enterprise_account_id}`

| Field | Type | Description |
|---|---|---|
| enterprise_account_id | string | Account identifier |
| credit_trigger | string | Condition that triggers credit |
| monthly_export_credit_percent | number | Credit percentage for export failures |
| executive_contact | string | Email of executive contact |

## Catalog

### `GET /api/catalog`

Lists all available endpoints and aggregate record counts. Use for discovery but not for detailed record data. The `notes` field confirms this is a public catalog — task targets are not exposed.
