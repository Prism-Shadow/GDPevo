# HarborCRM API Reference

All endpoints are public GETs at `<TASK_ENV_BASE_URL>`. No authentication is required.

## Policies

`GET /api/policies`

Returns metadata about platform enums, qualification rules, and sponsor handoff enums.

```json
{
  "contact_hygiene": { "note": "..." },
  "prospecting": {
    "platform_enums": ["AUV", "ROV", "Underwater Camera"],
    "qualification_note": "..."
  },
  "sponsor_handoff": {
    "note": "...",
    "status_enums": ["paid_deferred", "open_invoice", "proposal_only", "not_sponsor"]
  }
}
```

## Events

`GET /api/events` — list of all events. Each event has:

| Field | Type | Notes |
|---|---|---|
| `event_id` | string | Primary key |
| `name` | string | Display name |
| `campaign_code` | string | e.g. `EVT-NOPS-2026` |
| `start_date` | string (YYYY-MM-DD) | |
| `end_date` | string (YYYY-MM-DD) | |
| `followup_days_after_end` | integer | Lead follow-up = end_date + this |
| `sponsor_followup_days_after_end` | integer | Finance follow-up = end_date + this |
| `lead_opportunity_amount` | integer USD | Per-account amount for non-sponsor leads |
| `status` | string | Usually `completed` |

`GET /api/events/{event_id}` — single event (same shape).

## Event sub-resources

### Orders

`GET /api/events/{event_id}/orders`

| Field | Type | Notes |
|---|---|---|
| `account_id` | string | CRM account ID |
| `account_name` | string | |
| `amount` | integer USD | Package amount |
| `order_status` | string | `confirmed`, `proposal_sent`, `canceled` |
| `package_level` | string | `platinum`, `gold`, `silver`, `bronze`, `community` |
| `ticket_contacts` | list[string] | Contact names tied to this order |
| `voucher_code` | string | |
| `event_id` | string | |

### Sponsor Packages

`GET /api/events/{event_id}/sponsor_packages` — same shape as orders.

### Badges

`GET /api/events/{event_id}/badges`

| Field | Type | Notes |
|---|---|---|
| `badge_id` | string | Unique ID |
| `badge_type` | string | `sponsor`, `attendee`, `student`, `press` |
| `company_name` | string | |
| `contact_name` | string | |
| `email` | string | Raw; needs normalization |
| `phone` | string | Raw; needs normalization |
| `job_title` | string | |
| `scan_score` | integer | |
| `session_interest` | string | |
| `source` | string | `badge_scan` |
| `event_id` | string | |

## Finance

`GET /api/finance/invoices?event_id={event_id}`

`GET /api/finance/invoices?account_id={account_id}`

| Field | Type | Notes |
|---|---|---|
| `invoice_id` | string | |
| `account_id` | string | |
| `account_name` | string | |
| `amount` | integer USD | Total invoice amount |
| `deferred_amount` | integer USD | |
| `paid_amount` | integer USD | |
| `due_date` | string (YYYY-MM-DD) | |
| `invoice_date` | string (YYYY-MM-DD) | |
| `payment_date` | string or null | |
| `status` | string | `paid_deferred`, `open` |
| `event_id` | string | |

## CRM

### Accounts

`GET /api/crm/accounts`

`GET /api/crm/accounts?status={status}`

`GET /api/crm/accounts?owner_region={owner_region}`

| Field | Type | Notes |
|---|---|---|
| `account_id` | string | Primary key |
| `name` | string | Account/company name |
| `status` | string | `customer`, `prospect`, `disqualified` |
| `disqualified_reason` | string or null | e.g. `student_program_only`, `no_industrial_budget` |
| `domain` | string | |
| `industry` | string | |
| `owner_region` | string | `west`, `central`, `east` |

### Contacts

`GET /api/crm/contacts`

`GET /api/crm/contacts?account_id={account_id}`

| Field | Type | Notes |
|---|---|---|
| `contact_id` | string | Primary key |
| `account_id` | string | FK to account |
| `name` | string | Contact display name |
| `email` | string | Normalized in CRM |
| `phone` | string | Normalized digits-only in CRM |
| `title` | string | |
| `opted_out` | boolean | |
| `source_updated_at` | string (ISO timestamp) | |

### Opportunities

`GET /api/crm/opportunities`

`GET /api/crm/opportunities?event_id={event_id}`

`GET /api/crm/opportunities?account_id={account_id}`

| Field | Type | Notes |
|---|---|---|
| `opportunity_id` | string | |
| `account_id` | string | |
| `name` | string | |
| `amount` | integer USD | |
| `stage` | string | `closed_won`, `proposal`, `qualification`, `discovery` |
| `close_date` | string (YYYY-MM-DD) | |
| `event_id` | string | |

### Campaign Members

`GET /api/crm/campaign_members`

`GET /api/crm/campaign_members?event_id={event_id}`

`GET /api/crm/campaign_members?account_id={account_id}`

| Field | Type | Notes |
|---|---|---|
| `account_id` | string | |
| `contact_id` | string | |
| `event_id` | string | |
| `status` | string | `attended_sponsor`, `registered_sponsor`, `attended`, `excluded` |
| `last_activity_date` | string (YYYY-MM-DD) | |

## Trade Shows

`GET /api/tradeshows`

`GET /api/tradeshows/{show_id}`

| Field | Type | Notes |
|---|---|---|
| `show_id` | string | Primary key |
| `name` | string | |
| `city` | string | |
| `country` | string | |
| `start_date` | string (YYYY-MM-DD) | |
| `end_date` | string (YYYY-MM-DD) | |
| `theme` | string | |

### Exhibitors

`GET /api/tradeshows/{show_id}/exhibitors`

| Field | Type | Notes |
|---|---|---|
| `company_id` | string | `exh_{show}_{n}` format |
| `company_name` | string | |
| `booth` | string | |
| `country` | string | |
| `website` | string | |
| `description` | string | Used for platform qualification |
| `crm_account_id` | string or null | FK to CRM account |
| `show_id` | string | |

### Meeting Interest

`GET /api/tradeshows/{show_id}/meeting_interest`

| Field | Type | Notes |
|---|---|---|
| `company_name` | string | |
| `interest_score` | integer | |
| `requested_demo` | boolean | |
| `notes` | string | |
| `show_id` | string | |

## Import Batches

`GET /api/import_batches`

| Field | Type | Notes |
|---|---|---|
| `batch_id` | string | e.g. `my_import_batch` |
| `campaign_code` | string | e.g. `WEB-FALL-2026` |
| `name` | string | |
| `received_at` | string (ISO timestamp) | |
| `source_system` | string | |

`GET /api/import_batches/{batch_id}` — single batch.

### Raw Contacts

`GET /api/import_batches/{batch_id}/raw_contacts`

| Field | Type | Notes |
|---|---|---|
| `row_id` | string | Unique within batch |
| `batch_id` | string | |
| `company_name` | string | |
| `contact_name` | string | |
| `email` | string | Raw; needs normalization |
| `phone` | string | Raw; needs normalization |
| `captured_at` | string (ISO timestamp) | |
| `source_name` | string | `badge_scan`, `sponsor_form`, `partner_upload`, `webinar_form`, `exhibitor_form`, `manual_upload` |
| `city` | string | |
| `country` | string | |
| `interest` | string | |

### Suppression List

`GET /api/import_batches/{batch_id}/suppression`

| Field | Type | Notes |
|---|---|---|
| `email` | string | Normalized email to suppress |
| `phone` | string | Normalized phone |
| `reason` | string | `global_opt_out`, `privacy_request`, `role_account` |
