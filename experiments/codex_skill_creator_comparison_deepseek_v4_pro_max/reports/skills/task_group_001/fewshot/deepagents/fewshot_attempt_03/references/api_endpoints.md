## Event & Trade Show Endpoints

### GET /api/events
Returns list of events. Each event has `event_id`, `name`, `start_date`, `end_date`, `lead_followup_days`, `sponsor_followup_days`.

### GET /api/events/{event_id}
Single event object. Fields: `event_id`, `name`, `start_date`, `end_date`, `lead_followup_days`, `sponsor_followup_days`, `lead_opportunity_amount` (integer USD).

### GET /api/events/{event_id}/orders
List of sponsor orders for the event. Each order: `order_id`, `account_id`, `account_name`, `package_name`, `package_amount` (integer USD), `status` (`confirmed`, `pending`, `cancelled`, `draft`), `invoice_id` or null.

### GET /api/events/{event_id}/badges
List of badge scans/registrations. Each badge: `badge_id`, `contact_name`, `company_name`, `email` (raw, may be empty/null), `phone` (raw, may be empty/null), `badge_type` (e.g., `business`, `press`, `student`, `exhibitor`, `sponsor`, `speaker`), `scan_timestamp` (ISO).

### GET /api/events/{event_id}/sponsor_packages
List of sponsor packages offered for this event. Each package: `package_id`, `package_name`, `package_amount` (integer USD), `package_tier`.

## Finance Endpoints

### GET /api/finance/invoices?event_id={event_id}
List of invoices tied to an event. Each invoice: `invoice_id`, `account_id`, `account_name`, `event_id`, `total_amount` (integer USD), `paid_amount` (integer USD), `open_balance` (integer USD), `status` (`paid`, `partial`, `open`), `due_date` (ISO date or null).

### GET /api/finance/invoices?account_id={account_id}
Same invoice shape, filtered by account.

## CRM Account & Contact Endpoints

### GET /api/crm/accounts
List of all CRM accounts. Each account: `account_id` (string like `acct_*`), `account_name`, `status` (`active`, `disqualified`, `inactive`), `owner_region` (nullable string), `website` (nullable), `country` (nullable).

### GET /api/crm/accounts?status={status}
Filter accounts by status value.

### GET /api/crm/accounts?owner_region={owner_region}
Filter accounts by owner region.

### GET /api/crm/contacts
List of all CRM contacts. Each contact: `contact_id` (string like `cont_*`), `account_id` (or null), `contact_name`, `email` (nullable), `phone` (nullable), `company_name` (derived from account).

### GET /api/crm/contacts?account_id={account_id}
Filter contacts by account.

## Opportunity & Campaign Endpoints

### GET /api/crm/opportunities
List of all opportunities. Each opportunity: `opportunity_id`, `account_id`, `account_name`, `event_id` (nullable), `amount` (integer USD), `stage` (e.g., `prospecting`, `qualified`, `closed_won`, `closed_lost`), `close_date` (ISO date).

### GET /api/crm/opportunities?event_id={event_id}
Filter opportunities by event.

### GET /api/crm/opportunities?account_id={account_id}
Filter opportunities by account.

### GET /api/crm/campaign_members
List of campaign members. Each member: `campaign_member_id`, `campaign_code` (e.g., `EVENT-neuralops_2026`), `account_id` (nullable), `contact_id` (nullable), `subject_key` (e.g., `acct_*:cont_*` or `badge:bdg_*`), `status` (`attended`, `registered`, `sent`, `attended_sponsor`, `registered_sponsor`, `excluded`), `source` (e.g., `badge_scan`, `order`).

### GET /api/crm/campaign_members?event_id={event_id}
Filter campaign members by event (campaign codes match `EVENT-{event_id}`).

### GET /api/crm/campaign_members?account_id={account_id}
Filter by account.

## Import Batch Endpoints

### GET /api/import_batches
List of import batches. Each batch: `batch_id`, `batch_name`, `campaign_code`, `source_system`, `total_rows`, `created_at` (ISO).

### GET /api/import_batches/{batch_id}
Single batch metadata with `total_rows` and `campaign_code`.

### GET /api/import_batches/{batch_id}/raw_contacts
List of raw contact rows awaiting import. Each row: `row_id` (e.g., `fw_001`), `company_name`, `contact_name`, `email` (raw), `phone` (raw), `source_name` (e.g., `badge_scan`, `sponsor_form`, `partner_upload`, `webinar_form`, `exhibitor_form`, `manual_upload`), `captured_at` (ISO timestamp).

### GET /api/import_batches/{batch_id}/suppression
List of suppression entries for the batch. Each entry: `suppression_id`, `row_id` (nullable), `email` (nullable), `phone` (nullable), `reason` (string).

## Trade Show Endpoints

### GET /api/tradeshows
List of all trade shows. Each show: `show_id`, `name`, `start_date`, `end_date`, `venue`, `city`, `country`.

### GET /api/tradeshows/{show_id}
Single trade show object, same shape as list item.

### GET /api/tradeshows/{show_id}/exhibitors
List of exhibitors. Each exhibitor: `company_id` (e.g., `exh_ms_001`), `company_name`, `booth`, `country`, `website`, `relationship_type` (e.g., `manufacturer`, `distributor`, `service_provider`, `sensor_vendor`, `research`), `platforms` (list of strings, may include `AUV`, `ROV`, `Underwater Camera`).

### GET /api/tradeshows/{show_id}/meeting_interest
List of meeting/demo interest records. Each record: `company_id`, `company_name`, `requested_demo` (boolean), `interest_score` (integer 0-100).

## Policy Endpoint

### GET /api/policies
Returns a policy object with nested rules. Known sub-keys used across tasks:
- `sponsor_statuses`: allowed status values for sponsor reporting
- `lead_qualification`: rules for which badge types qualify
- `prospecting_platforms`: list of platform values that qualify for prospecting campaigns (e.g., `["AUV", "ROV", "Underwater Camera"]`)
- `priority_tiers`: tier definitions (`A`, `B`, `C`) with score and demo thresholds
- `opportunity_amounts`: per-tier USD values
