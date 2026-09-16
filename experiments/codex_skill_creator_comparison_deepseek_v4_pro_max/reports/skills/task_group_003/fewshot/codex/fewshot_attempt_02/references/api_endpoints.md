# Support Console API Endpoints

Base URL: <TASK_ENV_BASE_URL> (substitute the environment variable literally).

All endpoints are read-only GET. No authentication is required.

## Endpoints by Domain

### Catalog & Search

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/catalog | Full service catalog listing available services, plans, and products |
| GET | /api/search | Search across entity types by keyword or partial identifier |

### Tickets

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/tickets | List all tickets |
| GET | /api/tickets/{ticket_id} | Single ticket detail including status, account link, service type, and reported issue |

**When ticket fetch returns 404 or empty:** Treat the associated account as invalid. The resolution route is INVALID_ACCOUNT and status is FAILED.

### Customers

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/customers | List all customers |
| GET | /api/customers/{customer_id} | Customer profile with billing status, associated lines, and account standing |

**When customer fetch returns 404:** The customer does not exist in the system. For case queues, this typically means a human transfer is needed.

### Lines

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/lines | List all lines |
| GET | /api/lines/{line_id} | Line detail: status (active, suspended, etc.), roaming state, network mode, data-saver status, APN settings, VPN status, Wi-Fi calling state, messaging permissions, and current plan assignment |

**Key line fields:** status, roaming_enabled, line_roaming_enabled, data_saver_on, network_mode, apn_configured, vpn_connected, wifi_calling_on, messaging_permissions, plan_id, mobile_data_on.

### Bills

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/bills | List all bills |
| GET | /api/bills/{bill_id} | Bill detail: total due, overdue status, line items, payment history |

**Key bill fields:** amount_due, overdue, status.

### Plans

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/plans | List all plans |
| GET | /api/plans/{plan_id} | Plan detail: name, data cap, roaming features, cost per refuel GB |

**Key plan fields:** data_cap_gb, roaming_supported, refuel_cost_per_gb.

### Devices

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/devices | List all devices |
| GET | /api/devices/{device_id} | Device detail: make, model, supported network modes, SIM type |

### Contact Center Cases

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/contact-center/cases | List all contact-center cases |
| GET | /api/contact-center/cases/{case_id} | Case detail with reported issue, associated customer/line, current status |

### Outages

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/outages | List all active and recent outages |
| GET | /api/outages/{outage_id} | Outage detail: affected area, service types, start time, estimated resolution |

**When an outage matches a ticket issue:** Set status to PENDING_ACTION, route to OUTAGE_WAIT, escalation team to NONE.

### Diagnostics & Troubleshooting

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/diagnostics/{ticket_id} | Diagnostic results for a ticket: latency, stability, bandwidth metrics, and fault indicators |
| GET | /api/troubleshooting/{ticket_id} | Automated troubleshooting results and recommended actions |

**When diagnostics show measurable issues:** Set diagnostic_needed to true and populate the corresponding boolean flags (latency_issue, stability_issue, bandwidth_issue) based on the response fields.

### Enterprise

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/enterprise/accounts | List all enterprise accounts |
| GET | /api/enterprise/accounts/{account_id} | Enterprise account with owners, channel, contact info, SLA tier |
| GET | /api/enterprise/incidents | List all enterprise incidents |
| GET | /api/enterprise/incidents/{incident_id} | Incident detail: severity, affected exports, timeline, engineering owner |
| GET | /api/enterprise/export-runs | List export runs across all enterprise accounts |
| GET | /api/enterprise/export-runs/{run_id} | Single export run: status, dates, failure reason |
| GET | /api/enterprise/messages | Enterprise messages including incident updates and alerts |
| GET | /api/enterprise/sla/{account_id} | SLA record for an account: credit percent, terms, thresholds |

**Enterprise workflow:** Start from the complaint email approximate incident reference, fetch the incident, then cross-reference with export-runs (for failure window) and messages (for root cause). Use the SLA endpoint for credit calculations.

## Fetching Strategy

1. Parse all entity IDs from the payload upfront.
2. Batch concurrent GET calls where possible — they are independent.
3. Check every response HTTP status. 404 or empty response is actionable evidence.
4. Cross-reference records: a ticket links to an account and outages; a case links to a customer, line, bill, plan, and device.
