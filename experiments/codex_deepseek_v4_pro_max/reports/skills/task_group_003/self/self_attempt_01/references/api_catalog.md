# Support Console API Catalog

Base URL: resolved from `<TASK_ENV_BASE_URL>` or `environment_access.md`. All endpoints are GET-only.

## Endpoints by Domain

### Tickets
- `/api/tickets` — List all tickets
- `/api/tickets/{ticket_id}` — Single ticket detail

### Accounts
- `/api/accounts` — List all accounts
- `/api/accounts/{account_id}` — Single account detail

### Customers
- `/api/customers` — List all customers
- `/api/customers/{customer_id}` — Single customer detail

### Lines & Devices
- `/api/lines` — List all lines
- `/api/lines/{line_id}` — Single line detail
- `/api/devices` — List all devices
- `/api/devices/{device_id}` — Single device detail

### Plans & Billing
- `/api/plans` — List all plans
- `/api/plans/{plan_id}` — Single plan detail
- `/api/bills` — List all bills
- `/api/bills/{bill_id}` — Single bill detail

### Diagnostics & Troubleshooting
- `/api/diagnostics/{ticket_id}` — Diagnostic data for a ticket
- `/api/troubleshooting/{ticket_id}` — Troubleshooting steps for a ticket

### Outages
- `/api/outages` — List active outages

### Cases
- `/api/cases` — List all cases
- `/api/cases/{case_id}` — Single case detail
- `/api/contact-center/cases` — Contact-center case list
- `/api/contact-center/cases/{case_id}` — Single contact-center case

### Enterprise
- `/api/enterprise/accounts` — Enterprise account list
- `/api/enterprise/accounts/{account_id}` — Single enterprise account
- `/api/enterprise/incidents` — Enterprise incident list
- `/api/enterprise/incidents/{incident_id}` — Single enterprise incident
- `/api/enterprise/export-runs` — Export run history
- `/api/enterprise/messages` — Enterprise message log
- `/api/enterprise/sla/{account_id}` — SLA record for an enterprise account

### Search
- `/api/search` — General search endpoint

## Common Enum Values

### Resolution Status
`RESOLVED | PENDING_ACTION | ESCALATED | FAILED`

### Route Teams
`NONE | TIER2_SUPPORT | FIELD_OPS | NETWORK_ENGINEERING | ACCOUNTS_PAYABLE`

### Key Blockers
`NONE | ACTIVE_OUTAGE | INVALID_ACCOUNT | AUTH_FAILED | OVERDUE_SUSPENSION | FRAUD_SUSPENSION | NETWORK_CAPACITY | PROVISIONING_STALE | PHYSICAL_LINE_FAULT`

### Resolution Routes
`AUTO_TROUBLESHOOTING | OUTAGE_WAIT | ESCALATION | INELIGIBLE_ACCOUNT | AUTH_FAILED | INVALID_ACCOUNT`

### Case Actions
`TOGGLE_AIRPLANE_MODE | RESEAT_SIM | RESET_APN_REBOOT | SEND_PAYMENT_REQUEST | RESUME_LINE_REBOOT | TRANSFER_HUMAN | TOGGLE_MOBILE_DATA | TOGGLE_ROAMING | ENABLE_LINE_ROAMING | REFUEL_DATA | TOGGLE_DATA_SAVER | SET_NETWORK_MODE | DISCONNECT_VPN | GRANT_MESSAGING_PERMISSION | TOGGLE_WIFI_CALLING | NO_ACTION`

### Final Routes (Cases)
`SELF_SERVICE | BILLING_RECOVERY | CARRIER_UPDATE | HUMAN_TRANSFER`

### Final Routes (Data Recovery)
`DATA_RECOVERY | CARRIER_UPDATE | DEVICE_SETTING_FIX | HUMAN_TRANSFER`

### Permissions
`NONE | sms | storage | sms_and_storage`

### Severity
`Critical | High | Medium | Low`

### Response Status (Enterprise)
`READY_TO_SEND | NEEDS_FINANCE_REVIEW | NEEDS_ENGINEERING_REVIEW | UNDER_INVESTIGATION`

### Permission Types
`view | edit | upload_only`
