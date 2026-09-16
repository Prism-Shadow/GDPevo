# HarborCRM API Catalog

Base URL: `<TASK_ENV_BASE_URL>` (supplied by the runner). All endpoints return JSON arrays or objects. No authentication is required for the public endpoints listed here.

## Events

### GET /api/events

Returns a list of all events. Each event object:

- `event_id` (string) — unique identifier
- `name` (string) — display name
- `campaign_code` (string) — associated campaign code
- `start_date` (string, YYYY-MM-DD)
- `end_date` (string, YYYY-MM-DD)
- `status` (string) — `completed` or `planned`
- `lead_opportunity_amount` (integer, USD) — per-lead opportunity amount for non-sponsor qualified leads
- `followup_days_after_end` (integer) — days after `end_date` for lead follow-up due date
- `sponsor_followup_days_after_end` (integer) — days after `end_date` for sponsor finance follow-up due date

### GET /api/events/{event_id}

Returns a single event object matching the path parameter.

### GET /api/events/{event_id}/orders

Returns a list of sponsor orders for the event. Each order:

- `account_id` (string)
- `account_name` (string)
- `amount` (integer, USD)
- `order_status` (string) — `confirmed`, `proposal_sent`, `canceled`
- `package_level` (string) — `platinum`, `gold`, `silver`, `bronze`
- `ticket_contacts` (list of strings) — contact names on the order
- `voucher_code` (string)
- `event_id` (string)

### GET /api/events/{event_id}/badges

Returns a list of badge scans for the event. Each badge:

- `badge_id` (string)
- `badge_type` (string) — `sponsor`, `attendee`, `student`, `press`, `speaker`
- `company_name` (string)
- `contact_name` (string)
- `email` (string) — raw email as captured
- `phone` (string) — raw phone as captured
- `job_title` (string)
- `scan_score` (integer)
- `session_interest` (string)
- `source` (string) — `badge_scan` or other source label
- `event_id` (string)

### GET /api/events/{event_id}/sponsor_packages

Returns the same shape as `/api/events/{event_id}/orders`. Use whichever the prompt references.

## Finance

### GET /api/finance/invoices?event_id={event_id}

Returns a list of invoices associated with the event. Each invoice:

- `invoice_id` (string)
- `account_id` (string)
- `account_name` (string)
- `amount` (integer, USD)
- `paid_amount` (integer, USD)
- `deferred_amount` (integer, USD) — amount that was deferred/received
- `status` (string) — `paid_deferred`, `open`, `void`
- `invoice_date` (string, YYYY-MM-DD)
- `due_date` (string, YYYY-MM-DD)
- `payment_date` (string or null, YYYY-MM-DD)
- `event_id` (string)

### GET /api/finance/invoices?account_id={account_id}

Same shape, filtered by account.

## Tradeshows

### GET /api/tradeshows

Returns a list of all tradeshows. Each show:

- `show_id` (string)
- `name` (string)
- `city` (string)
- `country` (string)
- `start_date` (string, YYYY-MM-DD)
- `end_date` (string, YYYY-MM-DD)
- `theme` (string) — description of the show's focus

### GET /api/tradeshows/{show_id}

Returns a single tradeshow object.

### GET /api/tradeshows/{show_id}/exhibitors

Returns a list of exhibitors for the show. Each exhibitor:

- `company_id` (string)
- `company_name` (string)
- `booth` (string)
- `country` (string)
- `website` (string)
- `description` (string) — company description text used for platform qualification
- `relationship_type` (string or null) — `distributor`, `service_provider`, `sensor_vendor`, `research`, or null for OEM/builders

### GET /api/tradeshows/{show_id}/meeting_interest

Returns a list of meeting-interest records. Each record:

- `company_id` (string)
- `company_name` (string)
- `requested_demo` (boolean)
- `interest_score` (integer)

## Import Batches

### GET /api/import_batches

Returns a list of all import batches. Each batch:

- `batch_id` (string)
- `campaign_code` (string)
- `source_description` (string)

### GET /api/import_batches/{batch_id}

Returns a single batch object.

### GET /api/import_batches/{batch_id}/raw_contacts

Returns a list of raw contacts in the batch. Each row:

- `row_id` (string)
- `company_name` (string)
- `contact_name` (string)
- `email` (string)
- `phone` (string)
- `source_name` (string) — one of: `badge_scan`, `sponsor_form`, `partner_upload`, `webinar_form`, `exhibitor_form`, `manual_upload`
- `captured_at` (string, ISO timestamp)

### GET /api/import_batches/{batch_id}/suppression

Returns a list of suppressed emails for the batch. Each entry:

- `email` (string) — normalized lowercase email
- `reason` (string)

## CRM

### GET /api/crm/accounts

Returns all CRM accounts. Query parameters: `?status={status}` (e.g. `prospect`, `customer`, `disqualified`), `?owner_region={region}`. Each account:

- `account_id` (string)
- `name` (string) — account/company name
- `industry` (string)
- `domain` (string)
- `status` (string) — `customer`, `prospect`, `disqualified`
- `disqualified_reason` (string or null) — e.g. `student_program_only`, `no_industrial_budget`
- `owner_region` (string) — `east`, `west`, `central`

### GET /api/crm/contacts

Returns all CRM contacts. Query parameters: `?account_id={account_id}`. Each contact:

- `contact_id` (string)
- `account_id` (string)
- `name` (string)
- `email` (string)
- `phone` (string)
- `title` (string)
- `opted_out` (boolean)
- `source_updated_at` (string, ISO timestamp)

### GET /api/crm/opportunities

Returns all CRM opportunities. Query parameters: `?event_id={event_id}`, `?account_id={account_id}`. Each opportunity:

- `opportunity_id` (string)
- `account_id` (string)
- `name` (string)
- `amount` (integer, USD)
- `stage` (string) — e.g. `closed_won`, `proposal`, `qualification`, `discovery`
- `close_date` (string, YYYY-MM-DD)
- `event_id` (string or null)

### GET /api/crm/campaign_members

Returns all CRM campaign members. Query parameters: `?event_id={event_id}`, `?account_id={account_id}`. Each member:

- `account_id` (string)
- `contact_id` (string)
- `event_id` (string)
- `status` (string) — `attended`, `attended_sponsor`, `registered_sponsor`, `registered`, `invited`, `previous_event`
- `last_activity_date` (string, YYYY-MM-DD)

## Policies

### GET /api/policies

Returns a single policy object with these keys:

- `contact_hygiene.note` — guidance on contact normalization
- `prospecting.platform_enums` — list of target platform enum values (`["AUV", "ROV", "Underwater Camera"]`)
- `prospecting.qualification_note` — guidance on exhibitor qualification
- `sponsor_handoff.note` — guidance on sponsor reconciliation
- `sponsor_handoff.status_enums` — list of sponsor status enum values (`["paid_deferred", "open_invoice", "proposal_only", "not_sponsor"]`)
