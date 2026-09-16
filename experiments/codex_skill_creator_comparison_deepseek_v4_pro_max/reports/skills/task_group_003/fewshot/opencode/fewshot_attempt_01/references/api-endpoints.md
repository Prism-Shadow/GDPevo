# API Endpoints

All endpoints are GET. Append the path to the base URL from the prompt (e.g.
`<BASE>/api/tickets/{ticket_id}`).

## Tickets and Diagnostics

| Endpoint | Returns | Use When |
|---|---|---|
| `GET /api/tickets/{ticket_id}` | Individual ticket record with `account_id`, status, reported issue | Every ticket in a batch |
| `GET /api/diagnostics/{ticket_id}` | Diagnostic results: latency_ms, jitter_ms, packet_loss_pct, uptime_hours, stability_score, bandwidth_mbps, signal_db, error_log | Checking whether a ticket has a technical issue that auto-troubleshooting can fix |
| `GET /api/troubleshooting/{ticket_id}` | Troubleshooting report: recommended_actions, fixable flag, required_team when not fixable automatically | Deciding whether a ticket is auto-fixable or needs escalation |
| `GET /api/outages` | List of active outages: `outage_id`, `affected_accounts` array, status, description | Matching tickets against active outages |

## Contact Center and Customers

| Endpoint | Returns | Use When |
|---|---|---|
| `GET /api/cases/{case_id}` | Case record with `customer_id`, `line_id`, reported_issue, status | Every case in a queue or worklist |
| `GET /api/customers/{customer_id}` | Customer record: name, status, billing status, plan_id | Following a case's `customer_id` |
| `GET /api/lines/{line_id}` | Line record: status (active/suspended/etc.), roaming_enabled, data_saver_on, network_mode, mobile_data_on, vpn_connected, permission flags | Following a case's `line_id` |
| `GET /api/bills/{bill_id}` | Bill record: amount_due, status (paid/overdue/etc.), due_date | When a line is suspended and billing recovery might apply |
| `GET /api/plans/{plan_id}` | Plan record: name, data_cap_gb, roaming_included, features | When a plan constraint affects the resolution (e.g. roaming not included, data cap hit) |
| `GET /api/devices/{device_id}` | Device record: model, supported_network_modes, capabilities | When a device capability affects the resolution path |

## Enterprise

| Endpoint | Returns | Use When |
|---|---|---|
| `GET /api/enterprise/incidents/{incident_id}` | Incident record: `enterprise_account_id`, severity, status, created_at, resolved_at, root_cause, engineering_owner, channel_name | The starting point for any enterprise investigation |
| `GET /api/enterprise/accounts/{account_id}` | Enterprise account: company_name, account_owner, contract_tier, sla_terms | Following an incident's `enterprise_account_id` |
| `GET /api/enterprise/export-runs` | List of export runs: run_date, status (success/failed/etc.), records_exported, error_message | Finding the failed export window for an enterprise incident |
| `GET /api/enterprise/messages` | List of system messages: timestamp, category, content, alert_route | Finding the root cause message and any alert routing issues for an enterprise incident |
| `GET /api/enterprise/sla/{account_id}` | SLA record: credit_percent, covered_services, breach_days | Computing SLA credits for an enterprise incident |
