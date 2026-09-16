
# API Reference

Base URL: `<TASK_ENV_BASE_URL>` (substituted from the prompt). All endpoints are `GET`. No authentication required.

## Core entities

### Tickets

`GET /api/tickets/{ticket_id}`

Returns a ticket object with `ticket_id`, `account_id`, `service_type`, `status`, `priority`, `reported_issue`, and `created_at`. The `account_id` links to the customer account.

`GET /api/tickets`

Returns a list of all tickets. Use when the prompt asks for a queue-wide view.

### Customers

`GET /api/customers/{customer_id}`

Returns `customer_id`, `name`, `account_status` (one of `active`, `suspended`, `overdue`, `closed`, `fraud_hold`), `auth_status` (one of `active`, `failed`, `pending`), and `plan_id`.

`GET /api/customers`

Returns the full customer list.

### Lines

`GET /api/lines/{line_id}`

Returns `line_id`, `customer_id`, `status` (one of `active`, `suspended`, `inactive`), `roaming_enabled`, `network_mode` (e.g. `4G`, `5G`, `3G`), `mobile_data_enabled`, `data_saver_enabled`, `vpn_connected`, and `device_id`.

`GET /api/lines`

Returns all lines.

### Bills

`GET /api/bills/{bill_id}`

Returns `bill_id`, `customer_id`, `total_due`, `due_date`, `status` (one of `paid`, `unpaid`, `overdue`, `pending`), and line items.

`GET /api/bills`

Returns all bills.

### Plans

`GET /api/plans/{plan_id}`

Returns `plan_id`, `plan_name`, `data_limit_gb`, `data_addon_rate_per_gb`, `roaming_included`, and `service_types`.

`GET /api/plans`

Returns all plans.

### Devices

`GET /api/devices/{device_id}`

Returns `device_id`, `model`, `os_version`, `supported_network_modes`, and `messaging_permissions` (an object with `sms` and `storage` booleans).

`GET /api/devices`

Returns all devices.

## Diagnostics and troubleshooting

`GET /api/diagnostics/{ticket_id}`

Returns diagnostic results for the account/line tied to the ticket. Fields include `latency_ms`, `packet_loss_percent`, `bandwidth_mbps`, `stability_score`, and any `error_flags`. Use these to populate boolean flags like `latency_issue`, `stability_issue`, `bandwidth_issue`.

`GET /api/troubleshooting/{ticket_id}`

Returns recommended troubleshooting steps and whether auto-resolution is possible. When auto-troubleshooting is available and no other blocker exists, resolve as `AUTO_TROUBLESHOOTING`.

## Outages

`GET /api/outages`

Returns a list of active outages. Each outage has `outage_id`, `service_types` affected, `region`, `status`, `start_time`, and `estimated_restoration`. Match a ticket's `service_type` against an outage's `service_types` to determine if the ticket falls under an active outage.

## Contact center

`GET /api/contact-center/cases`
`GET /api/contact-center/cases/{case_id}`

Returns case objects. Use alongside `/api/cases/{case_id}` for mobile support queues.

`GET /api/cases`
`GET /api/cases/{case_id}`

Case objects with `case_id`, `customer_id`, `line_id`, `reported_issue`, `status`, and `created_at`.

## Enterprise

`GET /api/enterprise/accounts/{account_id}`

Returns `account_id`, `account_name`, `status`, `sla_tier`, `engineering_owner`, `account_owner`, `primary_contact`, and `products`.

`GET /api/enterprise/incidents/{incident_id}`

Returns `incident_id`, `account_id`, `severity`, `status`, `affected_product`, `start_time`, `end_time`, `root_cause_category`, and `contributing_alert_issue`.

`GET /api/enterprise/incidents`

Returns all enterprise incidents.

`GET /api/enterprise/export-runs`

Returns a list of export jobs with `run_id`, `account_id`, `date`, `status` (one of `success`, `failed`, `pending`), and `failure_reason`. Filter by account and date range to find failure windows.

`GET /api/enterprise/messages`

Returns system messages and alerts for enterprise accounts. Includes `message_id`, `account_id`, `timestamp`, `severity`, and `content`. Look for root-cause messages near the failure window.

`GET /api/enterprise/sla/{account_id}`

Returns `account_id`, `sla_tier`, `uptime_percent`, `credit_percent`, and `backfill_days`. The `credit_percent` is the SLA credit owed for a qualifying failure.

## Catalog

`GET /api/catalog`

Returns the full service and product catalog. Use for context on service types and product mappings.

## Health

`GET /health`

Returns API health status. Use to confirm connectivity before starting.
