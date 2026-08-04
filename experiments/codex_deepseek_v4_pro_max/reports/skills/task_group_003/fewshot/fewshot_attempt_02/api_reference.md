# Support Console API Reference

Base URL is resolved from the environment (see SKILL.md Step 1). No authentication.

## Catalog

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/catalog` | List all endpoints, fields, and entity relationships |

## Accounts

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/accounts` | List all accounts |
| GET | `/api/accounts/{account_id}` | Get a single account by ID |

## Tickets

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/tickets` | List all tickets |
| GET | `/api/tickets/{ticket_id}` | Get a single ticket by ID |
| GET | `/api/diagnostics/{ticket_id}` | Get diagnostic results for a ticket |
| GET | `/api/troubleshooting/{ticket_id}` | Get troubleshooting results for a ticket |

## Outages

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/outages` | List all outages (filter for active by account/region) |

## Customers & Mobile

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/customers` | List all customers |
| GET | `/api/customers/{customer_id}` | Get a single customer |
| GET | `/api/lines` | List all lines |
| GET | `/api/lines/{line_id}` | Get a single line |
| GET | `/api/devices` | List all devices |
| GET | `/api/devices/{device_id}` | Get a single device |
| GET | `/api/plans` | List all plans |
| GET | `/api/plans/{plan_id}` | Get a single plan |
| GET | `/api/bills` | List all bills |
| GET | `/api/bills/{bill_id}` | Get a single bill |

## Contact Center Cases

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/cases` | List all cases |
| GET | `/api/cases/{case_id}` | Get a single case |
| GET | `/api/contact-center/cases` | List contact-center cases |
| GET | `/api/contact-center/cases/{case_id}` | Get a single contact-center case |

## Enterprise

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/enterprise/accounts` | List enterprise accounts |
| GET | `/api/enterprise/accounts/{account_id}` | Get an enterprise account |
| GET | `/api/enterprise/incidents` | List enterprise incidents |
| GET | `/api/enterprise/incidents/{incident_id}` | Get an enterprise incident |
| GET | `/api/enterprise/export-runs` | List export runs (filter by account, date) |
| GET | `/api/enterprise/messages` | List messages (filter by incident) |
| GET | `/api/enterprise/sla/{account_id}` | Get SLA information for an enterprise account |

## Search

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/search` | Cross-entity search |
