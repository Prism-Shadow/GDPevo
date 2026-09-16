# HarborCRM API Endpoints Reference

All endpoints are relative to the base URL supplied by the runner (typically `<TASK_ENV_BASE_URL>`).

## Events

### GET /api/events
Returns the list of all events.

Response fields per event:
- `event_id` — string identifier
- `name` — display name
- `start_date` / `end_date` — ISO date strings
- `lead_opportunity_amount` — integer USD, the per-lead opportunity amount for this event

### GET /api/events/{event_id}
Returns a single event by id. Same fields as the list endpoint.

### GET /api/events/{event_id}/orders
Returns sponsor orders for the event.

Response fields per order:
- `order_id`
- `account_id` — CRM account id
- `account_name` — display name
- `package_amount` — integer USD
- `status` — active/canceled/etc.

### GET /api/events/{event_id}/badges
Returns badge scans for the event.

Response fields per badge:
- `badge_id`
- `contact_name`
- `company_name`
- `email` / `phone` — raw contact info
- `badge_type` — business/press/student/academic/guest/etc.
- `scanned_at` — ISO timestamp

### GET /api/events/{event_id}/sponsor_packages
Returns sponsor package details for the event.

Response fields per package:
- `package_id`
- `account_id`
- `package_name`
- `amount` — integer USD

## Finance

### GET /api/finance/invoices?event_id={event_id}
Returns invoices for a specific event.

Response fields per invoice:
- `invoice_id`
- `account_id`
- `account_name`
- `event_id`
- `amount` — total invoice amount
- `paid_amount` — amount paid so far
- `status` — paid/partial/open/etc.

### GET /api/finance/invoices?account_id={account_id}
Returns invoices for a specific CRM account.

## CRM

### GET /api/crm/accounts
Returns all CRM accounts. Filter with `?status=…` or `?owner_region=…`.

Response fields per account:
- `account_id`
- `name` — company name
- `status` — active/disqualified/closed/etc.
- `owner_region`
- `website`
- `phone`

### GET /api/crm/contacts
Returns all CRM contacts. Filter with `?account_id=…`.

Response fields per contact:
- `contact_id`
- `account_id`
- `first_name` / `last_name` / `name` — contact name fields
- `email`
- `phone`
- `title`

### GET /api/crm/opportunities
Returns all opportunities. Filter with `?event_id=…` or `?account_id=…`.

Response fields per opportunity:
- `opportunity_id`
- `account_id`
- `event_id`
- `amount` — integer USD
- `stage`
- `close_date`

### GET /api/crm/campaign_members
Returns all campaign members. Filter with `?event_id=…` or `?account_id=…`.

Response fields per member:
- `campaign_member_id`
- `campaign_id`
- `account_id`
- `contact_id`
- `event_id`
- `status` — attended/registered/sent/invited/etc.

## Trade Shows

### GET /api/tradeshows
Returns the list of all trade shows.

Response fields per show:
- `show_id`
- `name`
- `start_date` / `end_date`

### GET /api/tradeshows/{show_id}
Returns a single trade show by id.

### GET /api/tradeshows/{show_id}/exhibitors
Returns exhibitors for the trade show.

Response fields per exhibitor:
- `company_id`
- `company_name`
- `booth`
- `country`
- `website`
- `relationship_type` — OEM/distributor/service_provider/sensor_vendor/research/etc.
- `platforms` — array of platform strings
- `requested_demo` — boolean

### GET /api/tradeshows/{show_id}/meeting_interest
Returns meeting interest records for the trade show.

Response fields per record:
- `company_id`
- `company_name`
- `interest_score` — integer
- `requested_demo` — boolean
- `notes`

## Import Batches

### GET /api/import_batches
Returns the list of all import batches.

Response fields per batch:
- `batch_id`
- `name`
- `campaign_code`
- `source`
- `created_at`

### GET /api/import_batches/{batch_id}
Returns a single import batch by id.

### GET /api/import_batches/{batch_id}/raw_contacts
Returns raw contact records for the batch.

Response fields per raw contact:
- `row_id`
- `company_name`
- `contact_name`
- `email`
- `phone`
- `source_name` — badge_scan/sponsor_form/partner_upload/webinar_form/exhibitor_form/manual_upload
- `captured_at` — ISO timestamp

### GET /api/import_batches/{batch_id}/suppression
Returns suppression records for the batch.

Response fields per suppression record:
- `suppression_id`
- `email` — the address to suppress
- `reason`

## Policies

### GET /api/policies
Returns the policy document. This endpoint always provides the authoritative qualification rules.

Typical policy fields:
- `lead_qualification` — rules for lead qualification
- `excluded_badge_types` — badge types to exclude
- `excluded_relationship_types` — exhibitor relationship types to exclude
- `target_platforms` — allowed platform enums
- `follow_up_days_lead` — days after event end for lead follow-up
- `follow_up_days_finance` — days after event end for finance follow-up
- `opportunity_amounts` — tiered or flat opportunity amounts

Always read policies before applying any classification decision.
