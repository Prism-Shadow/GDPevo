# API Endpoint Catalog

Base URL is provided in the task prompt as TASK_ENV_BASE_URL or similar placeholder. Substitute it for all paths below.

## Core entities

### Tickets

GET /api/tickets — list all tickets. Each item includes ticket_id, account_id, service_type, status, and associated metadata.

GET /api/tickets/{ticket_id} — single ticket detail. Returns the ticket record with account reference, reported service type, status, and any linked diagnostic/troubleshooting references.

### Accounts

GET /api/accounts — list all accounts.

GET /api/accounts/{account_id} — single account detail. Returns account status (active, suspended, ineligible), service subscriptions, and linked line/customer references.

### Customers (contact-center / mobile domain)

GET /api/customers — list all customers.

GET /api/customers/{customer_id} — single customer detail. Returns assigned line_id, plan_id, device_id, and customer status.

### Lines

GET /api/lines — list all lines.

GET /api/lines/{line_id} — single line detail. Returns line status (active, suspended), feature flags (data_saver, roaming_enabled, roaming_active, network_mode, vpn_active, wifi_calling), and permission state (sms, storage).

### Bills

GET /api/bills — list all bills.

GET /api/bills/{bill_id} — single bill detail. Returns amount_due, status (overdue, paid, current), and linked account/line.

### Plans

GET /api/plans — list all plans.

GET /api/plans/{plan_id} — single plan detail. Returns data_limit_gb, roaming_supported, features, and plan name.

### Devices

GET /api/devices — list all devices.

GET /api/devices/{device_id} — single device detail. Returns device model, supported network modes, and associated line.

## Contact-center

GET /api/contact-center/cases — list all cases.

GET /api/contact-center/cases/{case_id} — single case detail. Returns reported_issue, customer_id, assigned line references, and status.

## Operations

GET /api/outages — list all outages. Each outage includes outage_id, service_type (internet, voice, video), affected areas, and status (active, resolved, scheduled).

GET /api/diagnostics/{ticket_id} — diagnostic results for a ticket. Returns latency_ms, packet_loss_percent, stability_score, bandwidth_mbps, and authentication_state.

GET /api/troubleshooting/{ticket_id} — automated troubleshooting results. Returns actions_taken, success status, and remaining issues.

## Enterprise

GET /api/enterprise/accounts — list enterprise accounts.

GET /api/enterprise/accounts/{account_id} — single enterprise account. Returns company name, product subscriptions, assigned owners (engineering_owner, account_owner), and linked channels.

GET /api/enterprise/incidents — list enterprise incidents.

GET /api/enterprise/incidents/{incident_id} — single incident detail. Returns root_cause, severity, affected products, failure windows, export-run references, alert references, and resolution state.

GET /api/enterprise/export-runs — list export runs. Export run details include status, failure dates, backfill state, and data volume.

GET /api/enterprise/messages — list enterprise messages. Each message may contain alert routing info, system notifications, and owner references.

GET /api/enterprise/sla/{account_id} — SLA terms for an enterprise account. Returns credit_percent, severity thresholds, and applicable failure windows.

## General

GET /api/catalog — returns available endpoints and service descriptions.

GET /api/search — general search across entities.

## Common chaining patterns

### Ticket resolution chain
1. GET /api/tickets/{ticket_id} — get account_id, service_type, status
2. GET /api/accounts/{account_id} — check account standing
3. GET /api/diagnostics/{ticket_id} — check technical metrics
4. GET /api/troubleshooting/{ticket_id} — check automated fix results
5. GET /api/outages — filter by service_type for active outages

### Contact-center case triage chain
1. GET /api/contact-center/cases/{case_id} — get customer_id, reported issue
2. GET /api/customers/{customer_id} — get line_id, plan_id, device_id
3. GET /api/lines/{line_id} — check status, features, permissions
4. GET /api/bills/{bill_id} (if line is suspended) — check amount_due
5. GET /api/plans/{plan_id} — check data limits and roaming support

### Enterprise incident response chain
1. GET /api/enterprise/incidents/{incident_id} — get root cause, severity, export-run reference
2. GET /api/enterprise/accounts/{account_id} — get company name, owners, channels
3. GET /api/enterprise/export-runs — check failure dates, backfill status
4. GET /api/enterprise/messages — find alert routing info
5. GET /api/enterprise/sla/{account_id} — get credit terms

### Mobile data recovery chain
1. GET /api/contact-center/cases/{case_id} or worklist entry — get customer reference
2. GET /api/customers/{customer_id} — get line_id
3. GET /api/lines/{line_id} — check roaming, data_saver, network_mode, vpn
4. GET /api/plans/{plan_id} — check data limit (for refuel decisions)
5. GET /api/bills/{bill_id} (if applicable) — charge amounts

## Field reference by endpoint

| Endpoint | Key fields in response |
|---|---|
| /api/tickets/{id} | ticket_id, account_id, service_type, status |
| /api/accounts/{id} | account_id, status, service_subscriptions |
| /api/customers/{id} | customer_id, line_id, plan_id, device_id, status |
| /api/lines/{id} | line_id, status, data_saver, roaming_enabled, roaming_active, network_mode, vpn_active, wifi_calling, permissions |
| /api/bills/{id} | bill_id, amount_due, status, account_id, line_id |
| /api/plans/{id} | plan_id, data_limit_gb, roaming_supported, features |
| /api/devices/{id} | device_id, model, supported_network_modes |
| /api/outages | outage_id, service_type, affected_areas, status |
| /api/diagnostics/{ticket_id} | latency_ms, packet_loss_percent, stability_score, bandwidth_mbps, authentication_state |
| /api/troubleshooting/{ticket_id} | actions_taken, success, remaining_issues |
| /api/enterprise/incidents/{id} | incident_id, root_cause, severity, affected_products, failure_window, export_run_ids, alert_references, resolution_state |
| /api/enterprise/accounts/{id} | account_id, company_name, products, engineering_owner, account_owner, channels |
| /api/enterprise/export-runs | run_id, status, failure_dates, backfill_available, data_volume |
| /api/enterprise/messages | message_id, alert_route, content, timestamp |
| /api/enterprise/sla/{account_id} | credit_percent, severity_thresholds, failure_window_applicability |
