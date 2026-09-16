# HarborCRM API Reference

Base URL is supplied by the runner as `<TASK_ENV_BASE_URL>` (typically `http://task-env:9001`). All endpoints are read-only `GET`. No authentication is required.

## Endpoint inventory

### Policies
```
GET /api/policies
```
Returns the rule metadata that drives every classification decision. Always fetch this first. It contains:
- Platform-to-relationship-type mappings for trade-show qualification
- Suppression lists (emails or domains that should be excluded)
- Tier thresholds (interest-score bands, priority-level definitions)
- Opportunity-amount schedules by tier
- Exclusion criteria for non-business badges, disqualified accounts
- Follow-up due-date offsets from event/show dates

### Events
```
GET /api/events
GET /api/events/{event_id}
```
Returns event metadata: `event_id`, `name`, dates. The event object provides the anchor date from which follow-up due dates are computed.

```
GET /api/events/{event_id}/orders
```
Returns sponsor orders for an event. Each order links to an `account_id`, has a `package_amount`, and may reference an `invoice_id`. Orders drive sponsor-status classification.

```
GET /api/events/{event_id}/badges
```
Returns badge scans for an event. Each badge has a `badge_id`, `contact_name`, `company_name`, `email`, `phone`, and a `badge_type`. The `badge_type` field distinguishes business badges from press/media/student/etc. Use this to filter non-business badges.

```
GET /api/events/{event_id}/sponsor_packages
```
Returns the available sponsor packages for an event with their pricing.

### Finance
```
GET /api/finance/invoices?event_id={event_id}
GET /api/finance/invoices?account_id={account_id}
```
Returns invoices. Each invoice has an `invoice_id`, `account_id`, `total_amount`, `paid_amount`, and a status field. The open balance is `total_amount - paid_amount`. An invoice with zero balance is fully paid; a positive balance means there is an open receivable.

### CRM
```
GET /api/crm/accounts
GET /api/crm/accounts?status={status}
GET /api/crm/accounts?owner_region={owner_region}
```
Returns CRM account records. Each account has an `account_id`, `account_name`, `status` (e.g. `active`, `disqualified`), and business metadata. Accounts with `status = "disqualified"` must be excluded from lead handoffs.

```
GET /api/crm/contacts
GET /api/crm/contacts?account_id={account_id}
```
Returns CRM contact records. Each contact has a `contact_id`, `account_id`, `name`, `email`, `phone`. Use `?account_id=` to find contacts for a specific account.

```
GET /api/crm/opportunities
GET /api/crm/opportunities?event_id={event_id}
GET /api/crm/opportunities?account_id={account_id}
```
Returns CRM opportunity records. Each opportunity has an `opportunity_id`, `account_id`, `event_id`, `amount`, and a status field. The event-level opportunity amount is used as the `opportunity_amount` for qualified non-sponsor leads.

```
GET /api/crm/campaign_members
GET /api/crm/campaign_members?event_id={event_id}
GET /api/crm/campaign_members?account_id={account_id}
```
Returns campaign-member records. Each member has a `campaign_member_id`, `event_id`, `account_id`, `contact_id`, and a `status` (e.g. `registered`, `attended`). The status drives campaign-member action decisions.

### Trade-shows
```
GET /api/tradeshows
GET /api/tradeshows/{show_id}
```
Returns trade-show metadata: `show_id`, `name`, dates, location.

```
GET /api/tradeshows/{show_id}/exhibitors
```
Returns exhibitor records. Each exhibitor has a `company_id`, `company_name`, `booth`, `country`, `website`, `relationship_type`, and `platforms` (an array of platform enums). The `relationship_type` drives qualification: only OEM/integrator-type exhibitors qualify; distributors, service providers, sensor vendors, and research-only exhibitors are excluded.

```
GET /api/tradeshows/{show_id}/meeting_interest
```
Returns meeting-interest records linking exhibitors to interest scores and demo requests. Each record has a `company_id`, `interest_score` (integer), and `requested_demo` (boolean).

### Import-batches
```
GET /api/import_batches
GET /api/import_batches/{batch_id}
```
Returns import-batch metadata: `batch_id`, `campaign_code`, creation date.

```
GET /api/import_batches/{batch_id}/raw_contacts
```
Returns raw contact rows to clean. Each row has a `row_id`, `company_name`, `contact_name`, `email`, `phone`, `source_name`, `captured_at`. Rows may be duplicated (same email appearing in multiple rows).

```
GET /api/import_batches/{batch_id}/suppression
```
Returns suppression entries for the batch. Each entry has a key (usually an email) that must be suppressed from the import.

## How records join

- **Event → Orders**: Join `orders[].account_id` to `accounts[].account_id`
- **Event → Badges**: Badges belong to the event; `badges[].company_name` loosely matches `accounts[].account_name`
- **Orders → Invoices**: Join `orders[].invoice_id` to `invoices[].invoice_id`
- **Badges → Contacts**: Match `badges[].contact_name` + `badges[].company_name` against CRM contacts
- **Exhibitors → CRM accounts**: Match `exhibitors[].company_id` or `company_name` against CRM accounts
- **Exhibitors → Meeting interest**: Join on `company_id`
- **Raw contacts → CRM accounts/contacts**: Match `company_name` and `contact_name`/`email` against CRM
- **Suppression → Raw contacts**: Match suppression keys (email) against raw-contact emails
