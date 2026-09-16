# HarborCRM API Reference

This catalog describes the public HarborCRM REST API endpoints, their response
shapes, and the fields available on each. The base URL is `<TASK_ENV_BASE_URL>`
supplied by the runner. All endpoints return JSON arrays or objects on GET.

## Policy Metadata

### GET /api/policies

Returns system-wide policy enums and notes that control business rules across
tasks.

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

The `platform_enums` list is the authoritative sort order for platform fields.
The `status_enums` list is the authoritative sponsor-status vocabulary.

## Events

### GET /api/events

Lists all events.

```json
[
  {
    "event_id": "string",
    "name": "string",
    "campaign_code": "string",
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "status": "completed|planned",
    "followup_days_after_end": "int",
    "sponsor_followup_days_after_end": "int",
    "lead_opportunity_amount": "int"
  }
]
```

### GET /api/events/{event_id}

Single event, same shape as an element of the events list.

### GET /api/events/{event_id}/orders

Sponsor orders for a single event.

```json
[
  {
    "event_id": "string",
    "account_id": "string",
    "account_name": "string",
    "voucher_code": "string",
    "package_level": "string",
    "amount": "int",
    "order_status": "confirmed|proposal_sent|canceled",
    "ticket_contacts": ["string"]
  }
]
```

### GET /api/events/{event_id}/badges

Scanned badge records. Each badge carries a `badge_type`, contact info,
and contextual fields.

```json
[
  {
    "badge_id": "string",
    "event_id": "string",
    "badge_type": "sponsor|attendee|student|press",
    "company_name": "string",
    "contact_name": "string",
    "email": "string",
    "phone": "string",
    "job_title": "string",
    "scan_score": "int",
    "session_interest": "string",
    "source": "string"
  }
]
```

### GET /api/events/{event_id}/sponsor_packages

Alias for `/api/events/{event_id}/orders`. Same shape.

## Finance

### GET /api/finance/invoices?event_id={event_id}

Invoice records tied to an event.

```json
[
  {
    "invoice_id": "string",
    "event_id": "string",
    "account_id": "string",
    "account_name": "string",
    "amount": "int",
    "paid_amount": "int",
    "deferred_amount": "int",
    "status": "paid_deferred|open|void",
    "invoice_date": "YYYY-MM-DD",
    "due_date": "YYYY-MM-DD",
    "payment_date": "YYYY-MM-DD|null"
  }
]
```

When `status` is `open` and `paid_amount > 0`, the open balance is
`amount - paid_amount`. When `status` is `paid_deferred`, the open balance
is zero. No invoice exists for `proposal_only` orders.

### GET /api/finance/invoices?account_id={account_id}

Same shape, filtered by CRM account ID.

## CRM

### GET /api/crm/accounts

All CRM accounts. Every task that cross-references CRM data pulls this endpoint.

```json
[
  {
    "account_id": "string",
    "name": "string",
    "domain": "string",
    "industry": "string",
    "owner_region": "string",
    "status": "customer|prospect|disqualified",
    "disqualified_reason": "string|null"
  }
]
```

### GET /api/crm/accounts?status={status}

Filter by `customer`, `prospect`, or `disqualified`.

### GET /api/crm/accounts?owner_region={owner_region}

Filter by region: `west`, `central`, `east`, `emea`, `apac`.

### GET /api/crm/contacts

All CRM contacts. Includes `opted_out` flag and normalized `phone`/`email`.

```json
[
  {
    "contact_id": "string",
    "account_id": "string",
    "name": "string",
    "email": "string",
    "phone": "string",
    "title": "string",
    "opted_out": "bool",
    "source_updated_at": "ISO-8601 timestamp"
  }
]
```

### GET /api/crm/contacts?account_id={account_id}

Filter by CRM account ID.

### GET /api/crm/opportunities

All CRM opportunities.

```json
[
  {
    "opportunity_id": "string",
    "name": "string",
    "event_id": "string",
    "account_id": "string",
    "amount": "int",
    "stage": "proposal|closed_won|closed_lost",
    "close_date": "YYYY-MM-DD"
  }
]
```

### GET /api/crm/opportunities?event_id={event_id}

Filter by event.

### GET /api/crm/opportunities?account_id={account_id}

Filter by account.

### GET /api/crm/campaign_members

All campaign member records.

```json
[
  {
    "event_id": "string",
    "account_id": "string",
    "contact_id": "string",
    "status": "attended_sponsor|registered_sponsor|attended",
    "last_activity_date": "YYYY-MM-DD"
  }
]
```

### GET /api/crm/campaign_members?event_id={event_id}

Filter by event.

### GET /api/crm/campaign_members?account_id={account_id}

Filter by account.

## Trade Shows

### GET /api/tradeshows

Lists all trade shows.

```json
[
  {
    "show_id": "string",
    "name": "string",
    "city": "string",
    "country": "string",
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "theme": "string"
  }
]
```

### GET /api/tradeshows/{show_id}

Single trade show, same shape as an element of the list.

### GET /api/tradeshows/{show_id}/exhibitors

Exhibitors at a trade show. Each exhibitor includes a `description` that is the
basis for qualification decisions.

```json
[
  {
    "show_id": "string",
    "company_id": "string",
    "company_name": "string",
    "booth": "string",
    "country": "string",
    "website": "string",
    "description": "string",
    "crm_account_id": "string|null"
  }
]
```

### GET /api/tradeshows/{show_id}/meeting_interest

Demo requests and interest scores for a show.

```json
[
  {
    "show_id": "string",
    "company_name": "string",
    "requested_demo": "bool",
    "interest_score": "int",
    "notes": "string"
  }
]
```

## Import Batches

### GET /api/import_batches

Lists import batches.

```json
[
  {
    "batch_id": "string",
    "name": "string",
    "campaign_code": "string",
    "source_system": "string",
    "received_at": "ISO-8601 timestamp"
  }
]
```

### GET /api/import_batches/{batch_id}

Single batch, same shape.

### GET /api/import_batches/{batch_id}/raw_contacts

Raw import rows with unnormalized contact data.

```json
[
  {
    "batch_id": "string",
    "row_id": "string",
    "company_name": "string",
    "contact_name": "string",
    "email": "string",
    "phone": "string",
    "city": "string",
    "country": "string",
    "interest": "string",
    "source_name": "webinar_form|partner_upload|manual_upload|badge_scan|sponsor_form|exhibitor_form",
    "captured_at": "ISO-8601 timestamp"
  }
]
```

### GET /api/import_batches/{batch_id}/suppression

Suppression entries for a batch (emails/phones to block).

```json
[
  {
    "email": "string",
    "phone": "string",
    "reason": "global_opt_out|privacy_request|role_account"
  }
]
```
