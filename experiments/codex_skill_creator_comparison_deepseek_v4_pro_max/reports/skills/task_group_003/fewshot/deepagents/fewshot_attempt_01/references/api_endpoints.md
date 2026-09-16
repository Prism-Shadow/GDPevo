# Support Console API Reference

Base URL: `<TASK_ENV_BASE_URL>` (replace with actual URL, typically `http://task-env:9003`)

All endpoints use GET. No authentication required.

## Core Entity Endpoints

### Tickets

- `GET /api/tickets` -- List all tickets.
- `GET /api/tickets/{ticket_id}` -- Single ticket detail. Returns fields including:
  `ticket_id`, `account_id`, `status`, `service_type`, `description`, `created_at`,
  `customer_id`, `line_id`, `resolution_notes`.

### Customers

- `GET /api/customers` -- List all customers.
- `GET /api/customers/{customer_id}` -- Single customer detail. Returns fields including:
  `customer_id`, `name`, `email`, `phone`, `status`, `account_ids`, `line_ids`.

### Lines

- `GET /api/lines` -- List all lines.
- `GET /api/lines/{line_id}` -- Single line detail. Returns fields including:
  `line_id`, `customer_id`, `account_id`, `status` (active/suspended/disabled),
  `service_type` (internet/voice/video/mobile), `plan_id`, `device_id`,
  `roaming_enabled`, `mobile_data_enabled`, `data_saver_enabled`,
  `network_mode`, `vpn_active`, `messaging_permissions`, `apn_settings`,
  `data_usage_gb`, `data_limit_gb`.

### Bills

- `GET /api/bills` -- List all bills.
- `GET /api/bills/{bill_id}` -- Single bill detail. Returns fields including:
  `bill_id`, `customer_id`, `account_id`, `amount_due`, `due_date`,
  `status` (paid/overdue/pending), `period_start`, `period_end`.

### Plans

- `GET /api/plans` -- List all plans.
- `GET /api/plans/{plan_id}` -- Single plan detail. Returns fields including:
  `plan_id`, `name`, `data_limit_gb`, `roaming_included`, `price_monthly`,
  `refuel_rate_per_gb`.

### Devices

- `GET /api/devices` -- List all devices.
- `GET /api/devices/{device_id}` -- Single device detail. Returns fields including:
  `device_id`, `model`, `os_version`, `supported_network_modes`, `sim_status`.

## Support Diagnostics

### Diagnostics

- `GET /api/diagnostics/{ticket_id}` -- Diagnostic results for a ticket. Returns fields
  including: `latency_ms`, `packet_loss_percent`, `bandwidth_mbps`,
  `stability_score`, `diagnostic_summary`, `recommended_actions`.

### Troubleshooting

- `GET /api/troubleshooting/{ticket_id}` -- Automated troubleshooting guidance for a
  ticket. Returns fields including: `auto_resolvable`, `steps`, `requires_field_ops`,
  `outage_related`, `related_outage_id`.

### Outages

- `GET /api/outages` -- List all known outages. Returns fields including:
  `outage_id`, `service_area`, `affected_service_types`, `status` (active/resolved),
  `started_at`, `estimated_restoration`, `affected_account_ids`.

## Contact Center

- `GET /api/contact-center/cases` -- List all cases.
- `GET /api/contact-center/cases/{case_id}` -- Single case detail. Returns fields
  including: `case_id`, `customer_id`, `line_id`, `status`, `reported_issue`.

## Enterprise

### Accounts

- `GET /api/enterprise/accounts` -- List enterprise accounts.
- `GET /api/enterprise/accounts/{account_id}` -- Single enterprise account detail.
  Returns fields including: `account_id`, `company_name`, `status`, `plan`,
  `account_owner`, `engineering_owner`.

### Incidents

- `GET /api/enterprise/incidents` -- List enterprise incidents.
- `GET /api/enterprise/incidents/{incident_id}` -- Single incident detail. Returns
  fields including: `incident_id`, `account_id`, `severity`, `status`,
  `started_at`, `resolved_at`, `root_cause`, `affected_services`,
  `contributing_alerts`, `channel_name`.

### Export Runs

- `GET /api/enterprise/export-runs` -- List export runs. Query parameters may include
  `account_id`, `start_date`, `end_date`. Returns fields including: `run_id`,
  `account_id`, `date`, `status` (success/failed/pending), `failure_reason`,
  `backfill_available`.

### Messages

- `GET /api/enterprise/messages` -- List enterprise messages/alerts. Returns fields
  including: `message_id`, `account_id`, `timestamp`, `severity`, `category`,
  `content`, `related_incident_id`.

### SLA

- `GET /api/enterprise/sla/{account_id}` -- SLA agreement details for an enterprise
  account. Returns fields including: `account_id`, `sla_tier`, `credit_percent`,
  `uptime_guarantee`, `applicable_services`.

## Catalog and Search

- `GET /api/catalog` -- Full service catalog.
- `GET /api/search` -- Cross-entity search. Query parameters may include `q`, `type`.
