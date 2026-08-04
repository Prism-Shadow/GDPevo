# Support Console API Catalog

All endpoints are read-only GET. Base URL is provided by the task environment.

## Accounts & Customers

| Endpoint | Returns |
|---|---|
| `GET /api/accounts` | All accounts |
| `GET /api/accounts/{account_id}` | Single account with status, plan refs, suspension flags |
| `GET /api/customers` | All customers |
| `GET /api/customers/{customer_id}` | Single customer with linked accounts, lines, preferences |

## Tickets

| Endpoint | Returns |
|---|---|
| `GET /api/tickets` | All tickets |
| `GET /api/tickets/{ticket_id}` | Single ticket with status, reported issue, linked account, resolution notes |
| `GET /api/diagnostics/{ticket_id}` | Latency, stability, bandwidth metrics for the ticket's service |
| `GET /api/troubleshooting/{ticket_id}` | Recommended resolution steps and auto-fix eligibility |

## Cases

| Endpoint | Returns |
|---|---|
| `GET /api/cases` | All cases |
| `GET /api/cases/{case_id}` | Single case with status, customer, line, and resolution info |
| `GET /api/contact-center/cases` | Contact-center cases |
| `GET /api/contact-center/cases/{case_id}` | Single contact-center case detail |

## Lines & Devices

| Endpoint | Returns |
|---|---|
| `GET /api/lines` | All lines |
| `GET /api/lines/{line_id}` | Single line with status (active, suspended, roaming), device ref, plan ref |
| `GET /api/devices` | All devices |
| `GET /api/devices/{device_id}` | Single device with capabilities and settings state |

## Plans & Billing

| Endpoint | Returns |
|---|---|
| `GET /api/plans` | All plans |
| `GET /api/plans/{plan_id}` | Plan detail with data caps, roaming policy, throttling rules |
| `GET /api/bills` | All bills |
| `GET /api/bills/{bill_id}` | Single bill with amount due, status, line items |

## Outages

| Endpoint | Returns |
|---|---|
| `GET /api/outages` | Active and recent outages with affected areas, severity, estimated restoration |

## Enterprise

| Endpoint | Returns |
|---|---|
| `GET /api/enterprise/accounts` | All enterprise accounts |
| `GET /api/enterprise/accounts/{account_id}` | Enterprise account with SLA tier, owners, channel |
| `GET /api/enterprise/incidents` | All enterprise incidents |
| `GET /api/enterprise/incidents/{incident_id}` | Incident detail with severity, window, root cause |
| `GET /api/enterprise/export-runs` | Export run history with status, dates, failure reasons |
| `GET /api/enterprise/messages` | Incident-related messages and alerts |
| `GET /api/enterprise/sla/{account_id}` | SLA terms, credit percentages, breach history |

## Search

| Endpoint | Returns |
|---|---|
| `GET /api/search?q={query}` | Cross-entity search results |

## Catalog

| Endpoint | Returns |
|---|---|
| `GET /api/catalog` | Full API endpoint listing |
