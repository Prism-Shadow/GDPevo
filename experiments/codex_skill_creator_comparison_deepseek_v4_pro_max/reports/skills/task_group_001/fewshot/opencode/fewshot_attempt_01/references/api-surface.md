# HarborCRM API Surface

Complete endpoint reference. All endpoints are read-only (`GET`). No authentication. The base URL is supplied by the runner as `<BASE_URL>`.

## Events domain

### `GET /api/events`
Returns all events. Each event object includes:
- `event_id` — stable string identifier
- `name` — display name
- `start_date` — ISO date string
- `end_date` — ISO date string
- `lead_opportunity_amount` — integer USD amount to use for qualified leads from this event

### `GET /api/events/{event_id}`
Returns a single event object.

### `GET /api/events/{event_id}/orders`
Returns sponsor orders for the event. Each order includes:
- `account_id` — links to CRM accounts
- `package_name` — sponsor package identifier
- `package_amount` — integer USD total price

### `GET /api/events/{event_id}/badges`
Returns badge scans/registrations for the event. Each badge includes:
- `badge_id` — unique string identifier
- `contact_name` — attendee name (may be empty)
- `company_name` — attendee's stated company (may be empty)
- `email` — attendee email (may be empty)
- `phone` — attendee phone (may be empty)
- `badge_type` — enum: `business`, `press`, `student`, `exhibitor`, `speaker`

### `GET /api/events/{event_id}/sponsor_packages`
Returns the sponsor package definitions for the event. Each package includes:
- `package_id`
- `name`
- `amount` — integer USD

## Finance domain

### `GET /api/finance/invoices?event_id={event_id}`
Returns invoices associated with an event. Each invoice includes:
- `invoice_id` — unique string identifier
- `event_id` — links to event
- `account_id` — links to CRM account
- `total_amount` — integer USD invoice total
- `paid_amount` — integer USD paid to date
- `status` — `paid`, `partial`, `issued`

### `GET /api/finance/invoices?account_id={account_id}`
Returns invoices for a specific CRM account.

## CRM domain

### `GET /api/crm/accounts`
Returns all CRM accounts. Filterable by:
- `?status={status}` — e.g., `active`, `disqualified`, `inactive`
- `?owner_region={owner_region}` — e.g., `EMEA`, `AMER`, `APAC`

Each account includes:
- `account_id` — unique string identifier
- `account_name` — company display name
- `status` — `active`, `disqualified`, or `inactive`
- `owner_region` — sales region
- `website` — company URL
- `domain` — extracted email domain (if available)

### `GET /api/crm/contacts`
Returns all CRM contacts. Filterable by:
- `?account_id={account_id}`

Each contact includes:
- `contact_id` — unique string identifier
- `account_id` — links to account (may be null for unaffiliated contacts)
- `name` — contact display name
- `email` — contact email
- `phone` — contact phone

### `GET /api/crm/opportunities`
Returns all CRM opportunities. Filterable by:
- `?event_id={event_id}`
- `?account_id={account_id}`

Each opportunity includes:
- `opportunity_id` — unique string identifier
- `event_id` — source event (may be null)
- `account_id` — linked account
- `amount` — integer USD
- `stage` — pipeline stage

### `GET /api/crm/campaign_members`
Returns all CRM campaign members. Filterable by:
- `?event_id={event_id}`
- `?account_id={account_id}`

Each campaign member includes:
- `campaign_member_id` — unique string identifier
- `event_id` — source event
- `account_id` — linked account
- `contact_id` — linked contact
- `status` — `attended`, `registered`, `attended_sponsor`, `registered_sponsor`, `excluded`

## Trade-shows domain

### `GET /api/tradeshows`
Returns all trade-shows. Each show includes:
- `show_id` — stable string identifier
- `name` — display name
- `start_date` — ISO date string
- `end_date` — ISO date string
- `venue` — location string

### `GET /api/tradeshows/{show_id}`
Returns a single trade-show object.

### `GET /api/tradeshows/{show_id}/exhibitors`
Returns exhibitors for a trade-show. Each exhibitor includes:
- `company_id` — unique string identifier (different namespace from CRM account_id)
- `company_name` — display name
- `booth` — booth number
- `country` — country string
- `website` — company URL
- `relationship_type` — `oem`, `distributor`, `service_provider`, `sensor_vendor`, `research`
- `platforms` — list of platform strings (e.g., `["AUV", "ROV"]`)

### `GET /api/tradeshows/{show_id}/meeting_interest`
Returns meeting interest records for a trade-show. Each record includes:
- `company_id` — links to an exhibitor
- `interest_score` — integer 0-100
- `requested_demo` — boolean

## Import domain

### `GET /api/import_batches`
Returns all import batches. Each batch includes:
- `batch_id` — unique string identifier
- `campaign_code` — associated campaign identifier
- `created_at` — ISO timestamp

### `GET /api/import_batches/{batch_id}`
Returns a single import batch object.

### `GET /api/import_batches/{batch_id}/raw_contacts`
Returns raw contact rows for a batch. Each row includes:
- `row_id` — unique string identifier
- `company_name` — stated company (may be empty)
- `contact_name` — stated contact name (may be empty)
- `email` — stated email (may be empty)
- `phone` — stated phone (may be empty)
- `source_name` — enum: `badge_scan`, `sponsor_form`, `partner_upload`, `webinar_form`, `exhibitor_form`, `manual_upload`
- `captured_at` — ISO timestamp

### `GET /api/import_batches/{batch_id}/suppression`
Returns the suppression list for a batch. Each entry includes:
- `email` — email to suppress (may be empty)
- `domain` — domain to suppress (may be empty)
- `company_name` — company to suppress (may be empty)

## Policies domain

### `GET /api/policies`
Returns the active business policies. The response varies by task context but typically includes:
- Lead opportunity amounts per event
- Follow-up date offset days for leads and finance
- Source priority ordering for import deduplication
- Platform coverage qualification rules for trade-show campaigns
- Controlled vocabulary definitions
- Campaign codes for import batches
- Priority tier thresholds (score minimums, demo request rules)
- Opportunity amounts by priority tier

Always fetch policies first — they drive every downstream business decision.
