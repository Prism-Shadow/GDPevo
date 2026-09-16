# HarborCRM API Endpoint Reference

Base URL is supplied by the runner as `<TASK_ENV_BASE_URL>`. All endpoints are read-only GET. No authentication is required.

## Events

### `GET /api/events/{event_id}`

Returns a single event object.

Fields:
- `event_id` (string) — stable identifier
- `name` (string) — display name
- `campaign_code` (string) — e.g. `EVT-NOPS-2026`
- `status` (string) — `completed`, `active`, etc.
- `start_date` (string, ISO date)
- `end_date` (string, ISO date)
- `followup_days_after_end` (integer) — days after end_date for lead follow-up
- `sponsor_followup_days_after_end` (integer) — days after end_date for sponsor finance follow-up
- `lead_opportunity_amount` (integer, USD) — per-lead opportunity amount for this event

### `GET /api/events/{event_id}/orders`

Returns a list of sponsor orders for the event.

Fields per order:
- `account_id` (string)
- `account_name` (string)
- `amount` (integer, USD) — package amount
- `event_id` (string)
- `order_status` (string) — `confirmed`, `proposal_sent`, `canceled`
- `package_level` (string) — `platinum`, `gold`, `silver`, `bronze`, `community`
- `ticket_contacts` (list of strings) — contact names with tickets
- `voucher_code` (string)

### `GET /api/events/{event_id}/badges`

Returns a list of badge scans for the event.

Fields per badge:
- `badge_id` (string)
- `badge_type` (string) — `sponsor`, `attendee`, `press`, `student`, `academic`
- `company_name` (string)
- `contact_name` (string)
- `email` (string) — raw, unnormalized
- `phone` (string) — raw, unnormalized
- `event_id` (string)
- `job_title` (string)
- `scan_score` (integer)
- `session_interest` (string)
- `source` (string) — `badge_scan` is the usual value

### `GET /api/events/{event_id}/sponsor_packages`

Returns the same list as orders (same schema). The two endpoints return identical data for the same event_id.

## Finance

### `GET /api/finance/invoices?event_id={event_id}`

Returns invoices for the event. May return fewer invoices than there are orders — proposal-only orders have no invoice.

Fields per invoice:
- `invoice_id` (string)
- `account_id` (string)
- `account_name` (string)
- `event_id` (string)
- `amount` (integer, USD) — total invoice amount
- `deferred_amount` (integer, USD)
- `paid_amount` (integer, USD)
- `status` (string) — `paid_deferred`, `open`, `canceled`
- `invoice_date` (string, ISO date)
- `due_date` (string, ISO date)
- `payment_date` (string or null, ISO date)

### `GET /api/finance/invoices?account_id={account_id}`

Returns invoices for a specific CRM account across all events.

## CRM

### `GET /api/crm/accounts`

Returns all CRM accounts. Can be filtered with `?status={status}` or `?owner_region={owner_region}`.

Fields per account:
- `account_id` (string)
- `name` (string) — company/account display name
- `domain` (string) — email domain
- `industry` (string)
- `owner_region` (string) — `west`, `central`, `east`
- `status` (string) — `customer`, `prospect`, `disqualified`
- `disqualified_reason` (string or null) — e.g. `student_program_only`, `no_industrial_budget`

### `GET /api/crm/contacts`

Returns all CRM contacts. Can be filtered with `?account_id={account_id}`.

Fields per contact:
- `contact_id` (string)
- `account_id` (string)
- `name` (string) — contact display name
- `email` (string) — already normalized (lowercase)
- `phone` (string) — already digits-only
- `title` (string)
- `opted_out` (boolean)
- `source_updated_at` (string, ISO timestamp)

### `GET /api/crm/opportunities`

Returns all CRM opportunities. Can be filtered with `?event_id={event_id}` or `?account_id={account_id}`.

Fields per opportunity:
- `opportunity_id` (string)
- `name` (string)
- `account_id` (string)
- `event_id` (string)
- `amount` (integer, USD)
- `stage` (string) — `closed_won`, `proposal`, `qualification`
- `close_date` (string, ISO date)

### `GET /api/crm/campaign_members`

Returns all CRM campaign members. Can be filtered with `?event_id={event_id}` or `?account_id={account_id}`.

Fields per member:
- `account_id` (string)
- `contact_id` (string)
- `event_id` (string)
- `status` (string) — `attended_sponsor`, `registered_sponsor`, `attended`, `excluded`
- `last_activity_date` (string, ISO date)

## Policies

### `GET /api/policies`

Returns the policy metadata object. Always fetch this first.

Fields:
- `contact_hygiene.note` — guidance for import cleaning
- `prospecting.platform_enums` — allowed platform values: `["AUV", "ROV", "Underwater Camera"]`
- `prospecting.qualification_note` — guidance for exhibitor qualification
- `sponsor_handoff.status_enums` — allowed sponsor statuses: `["paid_deferred", "open_invoice", "proposal_only", "not_sponsor"]`
- `sponsor_handoff.note` — guidance for sponsor reconciliation

## Tradeshows

### `GET /api/tradeshows`

Returns a list of all tradeshows.

Fields per tradeshow:
- `show_id` (string)
- `name` (string)
- `theme` (string)
- `city` (string)
- `country` (string)
- `start_date` (string, ISO date)
- `end_date` (string, ISO date)

### `GET /api/tradeshows/{show_id}`

Returns a single tradeshow object (same fields as above).

### `GET /api/tradeshows/{show_id}/exhibitors`

Returns a list of exhibitors for the tradeshow.

Fields per exhibitor:
- `company_id` (string) — e.g. `exh_ms_001`
- `company_name` (string)
- `description` (string) — free-text description used to determine qualification and platform coverage
- `booth` (string)
- `country` (string)
- `website` (string)
- `crm_account_id` (string or null) — link to existing CRM account
- `show_id` (string)

### `GET /api/tradeshows/{show_id}/meeting_interest`

Returns meeting-interest records for exhibitors at the tradeshow.

Fields per record:
- `company_name` (string) — matches exhibitor company_name
- `interest_score` (integer)
- `requested_demo` (boolean)
- `notes` (string)
- `show_id` (string)

## Import Batches

### `GET /api/import_batches`

Returns all import batches.

Fields per batch:
- `batch_id` (string)
- `name` (string)
- `campaign_code` (string)
- `source_system` (string)
- `received_at` (string, ISO timestamp)

### `GET /api/import_batches/{batch_id}`

Returns a single batch object (same fields as above).

### `GET /api/import_batches/{batch_id}/raw_contacts`

Returns the raw contact rows for the batch.

Fields per row:
- `row_id` (string)
- `batch_id` (string)
- `company_name` (string)
- `contact_name` (string)
- `email` (string) — raw, may have whitespace/case variations
- `phone` (string) — raw, may have formatting
- `city` (string)
- `country` (string)
- `interest` (string)
- `source_name` (string) — `badge_scan`, `sponsor_form`, `partner_upload`, `webinar_form`, `exhibitor_form`, `manual_upload`
- `captured_at` (string, ISO timestamp)

### `GET /api/import_batches/{batch_id}/suppression`

Returns suppression records for the batch.

Fields per record:
- `email` (string) — normalized
- `phone` (string) — digits-only
- `reason` (string) — `global_opt_out`, `privacy_request`, `role_account`
