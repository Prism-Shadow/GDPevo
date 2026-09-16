# HarborCRM API Reference

Base URL is supplied by the runner as `<TASK_ENV_BASE_URL>` (typically `http://task-env:9001/`). All endpoints are GET. No authentication is required.

## Event endpoints

### GET /api/events

Returns all events as a JSON array.

| Field | Type | Description |
|-------|------|-------------|
| event_id | string | Unique event identifier (e.g., "neural_ops_2026") |
| name | string | Display name |
| campaign_code | string | CRM campaign code (e.g., "EVT-EXAMPLE-2026") |
| start_date | string | ISO date `YYYY-MM-DD` |
| end_date | string | ISO date `YYYY-MM-DD` |
| status | string | Event lifecycle status (e.g., `completed`) |
| followup_days_after_end | integer | Days after end_date for lead follow-up due date |
| sponsor_followup_days_after_end | integer | Days after end_date for sponsor finance follow-up due date |
| lead_opportunity_amount | integer | USD opportunity amount applied per qualified non-sponsor lead account |

### GET /api/events/{event_id}

Single event record. Same fields as the list endpoint.

### GET /api/events/{event_id}/orders

Sponsor orders for the event.

| Field | Type | Description |
|-------|------|-------------|
| account_id | string | CRM account ID |
| account_name | string | Account display name |
| amount | integer | Package amount in USD |
| event_id | string | Parent event ID |
| order_status | string | `confirmed`, `proposal_sent`, or `canceled` |
| package_level | string | e.g., `platinum`, `gold`, `silver`, `bronze` |
| ticket_contacts | array[string] | Contact names associated with the order |
| voucher_code | string | Order voucher code |

**Important**: Canceled orders (`order_status: "canceled"`) are NOT active sponsors. Exclude them from sponsor status lists and from sponsor-attendee exclusion logic.

### GET /api/events/{event_id}/badges

Badge scans for the event.

| Field | Type | Description |
|-------|------|-------------|
| badge_id | string | Unique badge identifier (e.g., "bdg_example") |
| badge_type | string | `sponsor`, `attendee`, `student`, or other non-business categories |
| company_name | string | Company name as entered on the badge |
| contact_name | string | Contact full name |
| email | string | Raw email (may have case/whitespace issues) |
| phone | string | Raw phone (varying formats) |
| job_title | string | Job title |
| event_id | string | Parent event ID |
| scan_score | integer | Engagement score from badge scans |
| session_interest | string | Topics the attendee expressed interest in |
| source | string | Data source (typically `badge_scan`) |

### GET /api/events/{event_id}/sponsor_packages

Available sponsor package tiers. Used when the answer template references package-level enrichment beyond what orders provide.

### GET /api/events/{event_id}/orders

Alias: also available as `/api/events/{event_id}/orders`.

## Finance endpoints

### GET /api/finance/invoices?event_id={event_id}

Invoices filtered by event.

| Field | Type | Description |
|-------|------|-------------|
| invoice_id | string | Unique invoice identifier (e.g., "inv_example_1001") |
| account_id | string | CRM account ID |
| account_name | string | Account display name |
| amount | integer | Total invoice amount in USD |
| paid_amount | integer | Amount paid in USD |
| deferred_amount | integer | Amount marked deferred in USD |
| status | string | `paid_deferred` or `open` |
| due_date | string | ISO date `YYYY-MM-DD` |
| invoice_date | string | ISO date `YYYY-MM-DD` |
| payment_date | string | ISO date or null |
| event_id | string | Linked event ID |

**Sponsor status mapping from invoice status**:
- `status: "paid_deferred"` → sponsor status `paid_deferred`
- `status: "open"` → sponsor status `open_invoice` (open balance = `amount - paid_amount`)

### GET /api/finance/invoices?account_id={account_id}

Invoices filtered by account.

## CRM endpoints

### GET /api/crm/accounts

All CRM accounts.

| Field | Type | Description |
|-------|------|-------------|
| account_id | string | Unique account identifier |
| name | string | Company/account name |
| status | string | `customer`, `prospect`, `disqualified`, or other |
| disqualified_reason | string or null | If non-null, the account is disqualified (e.g., `student_program_only`, `no_industrial_budget`) |
| domain | string | Company domain |
| industry | string | Industry classification |
| owner_region | string | `west`, `central`, `east`, etc. |

### GET /api/crm/accounts?status={status}

Accounts filtered by status value.

### GET /api/crm/accounts?owner_region={owner_region}

Accounts filtered by owner region.

### GET /api/crm/contacts

All CRM contacts.

| Field | Type | Description |
|-------|------|-------------|
| contact_id | string | Unique contact identifier |
| account_id | string | Parent CRM account ID |
| name | string | Contact full name |
| email | string | Normalized email (lowercase) |
| phone | string | Normalized phone (digits only) |
| title | string | Job title |
| opted_out | boolean | Whether the contact has opted out of communications |
| source_updated_at | string | ISO timestamp of last update |

**Note**: CRM contacts already have normalized email and phone. When matching raw or badge contacts against CRM contacts, normalize the incoming data first so it matches the CRM format.

### GET /api/crm/contacts?account_id={account_id}

Contacts filtered by parent account.

### GET /api/crm/opportunities

All opportunities.

| Field | Type | Description |
|-------|------|-------------|
| opportunity_id | string | Unique opportunity ID |
| account_id | string | Parent CRM account ID |
| event_id | string | Linked event (may be null) |
| name | string | Opportunity name |
| amount | integer | Opportunity amount in USD |
| stage | string | `closed_won`, `proposal`, or other pipeline stage |
| close_date | string | ISO date |

### GET /api/crm/opportunities?event_id={event_id}

Opportunities linked to a specific event.

### GET /api/crm/opportunities?account_id={account_id}

Opportunities for a specific account.

### GET /api/crm/campaign_members

All campaign-member records.

| Field | Type | Description |
|-------|------|-------------|
| account_id | string | CRM account ID |
| contact_id | string | CRM contact ID |
| event_id | string | Linked event ID |
| status | string | `attended_sponsor`, `registered_sponsor`, `attended`, or other |
| last_activity_date | string | ISO date of last activity |

### GET /api/crm/campaign_members?event_id={event_id}

Campaign members filtered by event.

### GET /api/crm/campaign_members?account_id={account_id}

Campaign members filtered by account.

## Trade-show endpoints

### GET /api/tradeshows

All trade shows.

| Field | Type | Description |
|-------|------|-------------|
| show_id | string | Unique show identifier (e.g., "marine_expo_2026") |
| name | string | Display name |
| city | string | Host city |
| country | string | Host country |
| start_date | string | ISO date `YYYY-MM-DD` |
| end_date | string | ISO date `YYYY-MM-DD` |
| theme | string | Show theme/description |

### GET /api/tradeshows/{show_id}

Single trade-show record.

### GET /api/tradeshows/{show_id}/exhibitors

Exhibitors for a show.

| Field | Type | Description |
|-------|------|-------------|
| company_id | string | Unique exhibitor identifier (e.g., `exh_ms_001`) |
| company_name | string | Company name |
| show_id | string | Parent show ID |
| booth | string | Booth number |
| country | string | Company country |
| website | string | Company website URL |
| description | string | Company description — this is the primary text for qualification and platform classification |
| crm_account_id | string or null | Linked CRM account ID if known |

### GET /api/tradeshows/{show_id}/meeting_interest

Meeting interest data for a show.

| Field | Type | Description |
|-------|------|-------------|
| company_name | string | Company name (matches exhibitor company_name) |
| show_id | string | Parent show ID |
| interest_score | integer | Numeric interest score |
| requested_demo | boolean | Whether the exhibitor requested a demo |
| notes | string | Free-text notes from the interaction |

## Import-batch endpoints

### GET /api/import_batches

All import batches.

| Field | Type | Description |
|-------|------|-------------|
| batch_id | string | Unique batch identifier (e.g., "webinar_import_batch") |
| name | string | Display name |
| campaign_code | string | CRM campaign code (e.g., "WEB-EXAMPLE-2026") |
| received_at | string | ISO timestamp of batch receipt |
| source_system | string | Origin system |

### GET /api/import_batches/{batch_id}

Single batch record.

### GET /api/import_batches/{batch_id}/raw_contacts

Raw contact rows to clean.

| Field | Type | Description |
|-------|------|-------------|
| row_id | string | Unique row identifier (e.g., `fw_001`) |
| batch_id | string | Parent batch ID |
| company_name | string | Raw company name |
| contact_name | string | Raw contact name |
| email | string | Raw email (may have case/whitespace issues) |
| phone | string | Raw phone (varying formats) |
| source_name | string | Source type: `badge_scan`, `sponsor_form`, `partner_upload`, `webinar_form`, `exhibitor_form`, `manual_upload` |
| captured_at | string | ISO timestamp of capture |
| city | string | City |
| country | string | Country |
| interest | string | Free-text interest description |

### GET /api/import_batches/{batch_id}/suppression

Suppression list for the batch.

| Field | Type | Description |
|-------|------|-------------|
| email | string | Email to suppress |
| phone | string | Phone to suppress (digits only, may be empty) |
| reason | string | `global_opt_out`, `privacy_request`, `role_account`, etc. |

**Suppression matching**: A raw contact is suppressed if its normalized email OR normalized phone matches any entry in the suppression list. Check both independently — a match on either is sufficient.

## Policy endpoint

### GET /api/policies

Global business rules. Response structure:

```json
{
  "contact_hygiene": {
    "note": "Prepare contacts for CRM import using normalized, contactable records."
  },
  "prospecting": {
    "platform_enums": ["AUV", "ROV", "Underwater Camera"],
    "qualification_note": "Use exhibitor descriptions and company context to decide whether an account builds target underwater platforms or is only adjacent to them."
  },
  "sponsor_handoff": {
    "note": "Reconcile event, finance, and CRM records before final handoff.",
    "status_enums": ["paid_deferred", "open_invoice", "proposal_only", "not_sponsor"]
  }
}
```

The `platform_enums` and `status_enums` arrays are the canonical enum value sets. The answer template may declare a subset; use the values defined here when the template is permissive.
