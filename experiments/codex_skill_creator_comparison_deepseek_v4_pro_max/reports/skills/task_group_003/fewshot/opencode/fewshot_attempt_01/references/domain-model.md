# Domain Model

How the support console's entities relate and the cross-references to follow.

## Entity Graph

```
Ticket ──account_id──> Account
Ticket ──ticket_id──> Diagnostic
Ticket ──ticket_id──> Troubleshooting
Ticket ──account_id──> Outage (via affected_accounts list)

Case ──customer_id──> Customer
Case ──line_id──────> Line ──bill_id──> Bill
                        Line ──plan_id──> Plan
                        Line ──device_id──> Device

Enterprise Incident ──enterprise_account_id──> Enterprise Account
Enterprise Incident ──incident_id────────────> Export Runs (by date range)
Enterprise Incident ──incident_id────────────> Messages (by date range)
Enterprise Account ──account_id──────────────> SLA
```

## Entity Fields

### Ticket
- `ticket_id`: primary key
- `account_id`: cross-reference to the customer account
- `status`: current ticket state (open, in_progress, resolved, closed)
- `reported_service_type`: internet, voice, video
- `created_at`, `updated_at`: timestamps

### Diagnostic
- `ticket_id`: which ticket this diagnostic is for
- `latency_ms`: round-trip latency in milliseconds
- `jitter_ms`: jitter in milliseconds
- `packet_loss_pct`: packet loss percentage
- `uptime_hours`: hours of uptime
- `stability_score`: 0.0-1.0 stability rating
- `bandwidth_mbps`: measured bandwidth
- `signal_db`: signal strength in dB
- `error_log`: freeform error messages

### Troubleshooting
- `ticket_id`: which ticket this is for
- `fixable`: boolean, whether automatic troubleshooting can resolve it
- `recommended_actions`: list of suggested fix actions
- `required_team`: when not fixable, the team that must handle it
- `notes`: troubleshooting notes

### Outage
- `outage_id`: primary key
- `affected_accounts`: array of account_ids affected
- `status`: active, resolved, scheduled
- `description`: what the outage affects
- `started_at`, `estimated_resolution`: timestamps

### Case
- `case_id`: primary key
- `customer_id`: cross-reference to the customer
- `line_id`: cross-reference to the line
- `reported_issue`: customer's description of the problem
- `status`: open, in_progress, resolved, closed
- `created_at`: when the case was opened

### Customer
- `customer_id`: primary key
- `name`: customer name
- `status`: active, suspended, closed
- `billing_status`: current, overdue, paid
- `plan_id`: cross-reference to the plan

### Line
- `line_id`: primary key
- `customer_id`: back-reference to the customer
- `status`: active, suspended, cancelled
- `phone_number`: the line's phone number
- `roaming_enabled`: boolean
- `data_saver_on`: boolean
- `network_mode`: 2G, 3G, 4G, 5G, LTE
- `mobile_data_on`: boolean
- `vpn_connected`: boolean
- `bill_id`: cross-reference to the bill (when applicable)
- `plan_id`: cross-reference to the plan
- `device_id`: cross-reference to the device
- `permissions`: flags for sms, storage, messaging capabilities

### Bill
- `bill_id`: primary key
- `customer_id`: cross-reference to the customer
- `amount_due`: dollar amount owed
- `status`: paid, overdue, pending
- `due_date`: when payment is due
- `billing_period`: date range

### Plan
- `plan_id`: primary key
- `name`: plan name
- `data_cap_gb`: monthly data cap in GB (null if unlimited)
- `roaming_included`: boolean
- `features`: list of included features
- `monthly_cost`: base monthly cost

### Device
- `device_id`: primary key
- `model`: device model name
- `supported_network_modes`: array of supported modes (e.g. ["4G", "5G"])
- `capabilities`: device feature flags

### Enterprise Incident
- `incident_id`: primary key
- `enterprise_account_id`: cross-reference to the enterprise account
- `severity`: Critical, High, Medium, Low
- `status`: open, investigating, resolved
- `created_at`, `resolved_at`: timestamps
- `root_cause`: description of root cause
- `engineering_owner`: user ID of the responsible engineer
- `channel_name`: the communication channel or service name
- `description`: incident description

### Enterprise Account
- `account_id`: primary key
- `company_name`: the enterprise company name
- `account_owner`: user ID of the account manager
- `contract_tier`: service tier level
- `sla_terms`: summary of SLA commitments

### Export Run
- `run_date`: date of the export run
- `status`: success or failed
- `records_exported`: number of records in the run
- `error_message`: failure reason (empty on success)

### Message
- `id`: message identifier
- `timestamp`: when the message was generated
- `category`: system, alert, notification
- `content`: message body
- `alert_route`: where the alert was routed (or archive status)

### SLA
- `account_id`: cross-reference to the enterprise account
- `credit_percent`: SLA credit percentage for breaches
- `covered_services`: which services are covered
- `breach_days`: days of SLA breach

## Navigation Rules

1. Start from the entity in the payload (ticket, case, or incident ID).
2. Fetch that entity to get cross-reference IDs.
3. Fetch every referenced entity. Never stop at the first hop when the
   fetched entity itself contains more IDs.
4. Treat missing or null IDs as "not applicable." Do not fetch an endpoint
   with an empty ID.
5. API responses that return errors (404, 500) for a specific ID are evidence
   that the entity does not exist. Use this to drive account validation
   failures (e.g. invalid account, auth failure).
