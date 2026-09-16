# HarborCRM API Catalog

All endpoints are accessed at <TASK_ENV_BASE_URL>. No authentication is needed for the public endpoints listed here.

## Events

### `GET /api/events`

Returns a list of all events.

### `GET /api/events/{event_id}`

Returns a single event record. Typical fields: `event_id`, `name`, `start_date`, `end_date`, `venue`, `status`.

### `GET /api/events/{event_id}/orders`

Returns sponsor orders for the event. Typical fields: `order_id`, `account_id`, `account_name`, `package_id`, `package_name`, `amount`, `invoice_id`, `status`. An order's `status` can indicate active, canceled, or inactive sponsorship.

### `GET /api/events/{event_id}/badges`

Returns badge scans for the event. Typical fields: `badge_id`, `first_name`, `last_name`, `company_name`, `email`, `phone`, `badge_type`, `scanned_at`. The `badge_type` field distinguishes business attendees from press, exhibitor, guest, or other non-business types.

### `GET /api/events/{event_id}/sponsor_packages`

Returns available sponsor packages for the event. Typical fields: `package_id`, `name`, `amount`, `benefits`.

## Finance

### `GET /api/finance/invoices?event_id={event_id}`

Returns invoices associated with an event. Typical fields: `invoice_id`, `account_id`, `account_name`, `event_id`, `amount`, `paid_amount`, `status`, `issued_date`, `due_date`.

### `GET /api/finance/invoices?account_id={account_id}`

Returns invoices for a specific account.

## CRM

### `GET /api/crm/accounts`

Returns all CRM accounts. Typical fields: `account_id`, `account_name`, `status`, `owner_region`, `industry`, `website`, `phone`, `created_date`. The `status` field uses values like `active`, `disqualified`, `inactive`, or `prospect`.

### `GET /api/crm/accounts?status={status}`

Filters accounts by status.

### `GET /api/crm/accounts?owner_region={owner_region}`

Filters accounts by owner region.

### `GET /api/crm/contacts`

Returns all CRM contacts. Typical fields: `contact_id`, `account_id`, `first_name`, `last_name`, `email`, `phone`, `title`.

### `GET /api/crm/contacts?account_id={account_id}`

Returns contacts for a specific account.

### `GET /api/crm/opportunities`

Returns all opportunities. Typical fields: `opportunity_id`, `account_id`, `event_id`, `amount`, `stage`, `close_date`.

### `GET /api/crm/opportunities?event_id={event_id}`

Returns opportunities for a specific event.

### `GET /api/crm/opportunities?account_id={account_id}`

Returns opportunities for a specific account.

### `GET /api/crm/campaign_members`

Returns all campaign members. Typical fields: `campaign_member_id`, `campaign_id`, `account_id`, `contact_id`, `status`, `source`. Campaign member `status` values typically include `attended`, `registered`, `attended_sponsor`, `registered_sponsor`, and `sent`.

### `GET /api/crm/campaign_members?event_id={event_id}`

Returns campaign members for a specific event.

### `GET /api/crm/campaign_members?account_id={account_id}`

Returns campaign members for a specific account.

## Tradeshows

### `GET /api/tradeshows`

Returns a list of all tradeshows.

### `GET /api/tradeshows/{show_id}`

Returns a single tradeshow record. Typical fields: `show_id`, `name`, `start_date`, `end_date`, `location`.

### `GET /api/tradeshows/{show_id}/exhibitors`

Returns exhibitors for the tradeshow. Typical fields: `company_id`, `company_name`, `booth`, `country`, `website`, `platforms` (array of strings), `relationship_type` (e.g., `oem`, `distributor`, `service_provider`, `sensor_vendor`, `research`).

### `GET /api/tradeshows/{show_id}/meeting_interest`

Returns meeting interest records for the tradeshow. Typical fields: `company_id`, `company_name`, `requested_demo` (boolean), `interest_score` (integer).

## Import Batches

### `GET /api/import_batches`

Returns a list of all import batches.

### `GET /api/import_batches/{batch_id}`

Returns a single import batch. Typical fields: `batch_id`, `name`, `campaign_code`, `created_date`, `status`.

### `GET /api/import_batches/{batch_id}/raw_contacts`

Returns raw contacts in the batch. Typical fields: `row_id`, `company_name`, `contact_name`, `email`, `phone`, `source_name`, `captured_at`. The `source_name` field uses enum values like `badge_scan`, `sponsor_form`, `partner_upload`, `webinar_form`, `exhibitor_form`, `manual_upload`.

### `GET /api/import_batches/{batch_id}/suppression`

Returns suppression rules for the batch. Typical fields: `email`, `reason`, `added_date`.

## Policies

### `GET /api/policies`

Returns policy records that govern qualification, exclusion, and processing rules. Policies have varied structures depending on their domain, but typically include fields like `policy_id`, `policy_name`, `domain` (e.g., `sponsor`, `lead_qualification`, `import`, `prospecting`), and domain-specific rule sections. Read the full response and extract every relevant rule for the task at hand.
