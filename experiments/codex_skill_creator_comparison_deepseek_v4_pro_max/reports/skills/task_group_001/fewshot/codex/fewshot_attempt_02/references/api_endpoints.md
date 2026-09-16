# HarborCRM API Endpoint Catalog

Base URL is supplied by the runner as `<TASK_ENV_BASE_URL>`. All endpoints
return JSON arrays or objects. No authentication is required.

## Endpoint Index

### Events

| Endpoint | Returns |
|----------|---------|
| `GET /api/events` | List of all events |
| `GET /api/events/{event_id}` | Single event detail (name, dates, opportunity amount) |
| `GET /api/events/{event_id}/orders` | Sponsor orders for the event |
| `GET /api/events/{event_id}/badges` | Badge scans for the event |
| `GET /api/events/{event_id}/sponsor_packages` | Sponsor package definitions for the event |

### Trade Shows

| Endpoint | Returns |
|----------|---------|
| `GET /api/tradeshows` | List of all trade shows |
| `GET /api/tradeshows/{show_id}` | Single trade show detail |
| `GET /api/tradeshows/{show_id}/exhibitors` | Exhibitors for the show |
| `GET /api/tradeshows/{show_id}/meeting_interest` | Meeting interest records for the show |

### Finance

| Endpoint | Returns |
|----------|---------|
| `GET /api/finance/invoices?event_id={event_id}` | Invoices for an event |
| `GET /api/finance/invoices?account_id={account_id}` | Invoices for an account |

### CRM

| Endpoint | Returns |
|----------|---------|
| `GET /api/crm/accounts` | All CRM accounts |
| `GET /api/crm/accounts?status={status}` | Accounts filtered by status |
| `GET /api/crm/accounts?owner_region={owner_region}` | Accounts by region |
| `GET /api/crm/contacts` | All CRM contacts |
| `GET /api/crm/contacts?account_id={account_id}` | Contacts for an account |
| `GET /api/crm/opportunities` | All opportunities |
| `GET /api/crm/opportunities?event_id={event_id}` | Opportunities for an event |
| `GET /api/crm/opportunities?account_id={account_id}` | Opportunities for an account |
| `GET /api/crm/campaign_members` | All campaign members |
| `GET /api/crm/campaign_members?event_id={event_id}` | Members for an event campaign |
| `GET /api/crm/campaign_members?account_id={account_id}` | Members for an account |

### Import Batches

| Endpoint | Returns |
|----------|---------|
| `GET /api/import_batches` | List of all import batches |
| `GET /api/import_batches/{batch_id}` | Single batch detail (campaign code, metadata) |
| `GET /api/import_batches/{batch_id}/raw_contacts` | Raw rows to import |
| `GET /api/import_batches/{batch_id}/suppression` | Suppressed contact identifiers |

### Policies

| Endpoint | Returns |
|----------|---------|
| `GET /api/policies` | Business rules: qualification criteria, opportunity amounts, follow-up windows, dedup keys, exclusion lists, platform definitions |

## Entity Relationships

```
Event
 ├── orders ──────────────► Finance invoices (by invoice_id)
 ├── badges ──────────────► CRM contacts / accounts (by company_name, email)
 ├── sponsor_packages ────► Package amounts
 └── campaign_members ────► CRM campaign members (by event_id)

Trade Show
 ├── exhibitors ──────────► CRM accounts (by company_name, domain)
 └── meeting_interest ────► Demo requests, scores (by exhibitor company_id)

Import Batch
 ├── raw_contacts ────────► CRM accounts / contacts (by email, domain)
 └── suppression ─────────► Blacklisted identifiers

CRM Account
 ├── contacts ────────────► CRM contacts (by account_id)
 ├── opportunities ───────► Pipeline deals (by account_id or event_id)
 └── campaign_members ────► Campaign participation (by account_id)
```

## Typical Entity Shapes

### Event
```json
{
  "event_id": "string",
  "name": "string",
  "start_date": "YYYY-MM-DD",
  "lead_opportunity_amount": integer_usd
}
```

### Sponsor Order
```json
{
  "account_id": "string",
  "invoice_id": "string or null",
  "status": "active|canceled",
  "package_amount": integer_usd
}
```

### Invoice
```json
{
  "invoice_id": "string",
  "account_id": "string",
  "event_id": "string",
  "total_amount": integer_usd,
  "paid_amount": integer_usd,
  "balance": integer_usd
}
```

### Badge
```json
{
  "badge_id": "string",
  "event_id": "string",
  "contact_name": "string",
  "company_name": "string",
  "email": "string",
  "phone": "string",
  "badge_type": "string",
  "scan_date": "ISO timestamp"
}
```

### Exhibitor
```json
{
  "company_id": "string",
  "company_name": "string",
  "booth": "string",
  "country": "string",
  "website": "string",
  "relationship_type": "string",
  "platforms": ["string"]
}
```

### Meeting Interest
```json
{
  "company_id": "string",
  "show_id": "string",
  "requested_demo": boolean,
  "interest_score": integer
}
```

### CRM Account
```json
{
  "account_id": "string",
  "account_name": "string",
  "status": "active|disqualified|canceled",
  "owner_region": "string",
  "website": "string"
}
```

### CRM Contact
```json
{
  "contact_id": "string",
  "account_id": "string or null",
  "contact_name": "string",
  "email": "string",
  "phone": "string"
}
```

### Raw Contact (Import)
```json
{
  "row_id": "string",
  "company_name": "string",
  "contact_name": "string",
  "email": "string",
  "phone": "string",
  "source_name": "string",
  "captured_at": "ISO timestamp"
}
```

### Suppression Entry
```json
{
  "identifier": "string",
  "match_field": "email|domain|phone"
}
```
