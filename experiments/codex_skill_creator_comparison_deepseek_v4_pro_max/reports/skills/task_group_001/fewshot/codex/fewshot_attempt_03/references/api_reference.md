# HarborCRM API Reference

Base URL is supplied by the runner. All endpoints return JSON arrays or objects.
No authentication is required for the endpoints listed below.

## Events

### GET /api/events
Returns all events. Each event object includes:
- event_id, name, start_date, end_date, status, lead_opportunity_amount

### GET /api/events/{event_id}
Returns a single event object.

### GET /api/events/{event_id}/orders
Returns sponsor orders for the event. Each order:
- order_id, event_id, account_id, package_id, amount, status

### GET /api/events/{event_id}/badges
Returns badge scans for the event. Each badge:
- badge_id, event_id, contact_name, company_name, email, phone, badge_type

### GET /api/events/{event_id}/sponsor_packages
Returns sponsor packages for the event. Each package:
- package_id, event_id, name, amount

## Finance

### GET /api/finance/invoices?event_id={event_id}
Returns invoices for an event. Each invoice:
- invoice_id, event_id, account_id, total_amount, paid_amount, status

### GET /api/finance/invoices?account_id={account_id}
Returns invoices for an account.

## CRM

### GET /api/crm/accounts
Returns all CRM accounts. Each account:
- account_id, account_name, status, owner_region, website, phone

Filter with ?status={status} or ?owner_region={owner_region}.

### GET /api/crm/contacts
Returns all CRM contacts. Each contact:
- contact_id, account_id, first_name, last_name, email, phone

Filter with ?account_id={account_id}.

### GET /api/crm/opportunities
Returns all opportunities. Each opportunity:
- opportunity_id, event_id, account_id, amount, stage

Filter with ?event_id={event_id} or ?account_id={account_id}.

### GET /api/crm/campaign_members
Returns all campaign members. Each member:
- member_id, event_id, account_id, contact_id, status, source

Filter with ?event_id={event_id} or ?account_id={account_id}.

## Tradeshows

### GET /api/tradeshows
Returns all tradeshows.

### GET /api/tradeshows/{show_id}
Returns a single tradeshow object:
- show_id, name, start_date, end_date, location

### GET /api/tradeshows/{show_id}/exhibitors
Returns exhibitors for the show. Each exhibitor:
- company_id, company_name, booth, country, website, platforms (array of strings), relationship_type

### GET /api/tradeshows/{show_id}/meeting_interest
Returns meeting interest records. Each record:
- company_id, company_name, requested_demo (boolean), interest_score (integer), notes

## Import Batches

### GET /api/import_batches
Returns all import batches.

### GET /api/import_batches/{batch_id}
Returns a single batch. Each batch:
- batch_id, name, campaign_code, created_at, status, source

### GET /api/import_batches/{batch_id}/raw_contacts
Returns raw contact rows for the batch. Each row:
- row_id, company_name, contact_name, email, phone, source_name, captured_at

### GET /api/import_batches/{batch_id}/suppression
Returns suppression list entries for the batch. Each entry:
- email, reason, suppressed_at

## Policies

### GET /api/policies
Returns the full policy document. Structure varies by task but typically includes:
- Business badge type identifiers
- Non-business badge type identifiers
- Platform/product qualification rules for tradeshows
- Sponsor status classification rules
- Follow-up due date offsets (in business days)
- Lead opportunity amounts
- Priority tier amounts
- Deduplication rules for import batches
- Suppression rules
- Exclusion criteria
