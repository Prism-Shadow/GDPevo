# HarborCRM Data Model

Entity descriptions, field meanings, and cross-entity join keys. Everything here is inferred from the API response shapes; confirm against the actual responses at runtime.

## Core entities

### Account (CRM)
Represents a company in the CRM. Central hub for contacts, opportunities, and campaign membership.

| Field | Type | Description |
|-------|------|-------------|
| `account_id` | string | Primary key. Stable across the API. |
| `account_name` | string | Company display name. |
| `status` | enum | `active`, `disqualified`, or `inactive`. |
| `owner_region` | string | Sales region assignment. |
| `website` | string | Company URL. |
| `domain` | string | Extracted email domain for matching. |

### Contact (CRM)
Represents a person at an account.

| Field | Type | Description |
|-------|------|-------------|
| `contact_id` | string | Primary key. |
| `account_id` | string | Foreign key to Account. Null when unaffiliated. |
| `name` | string | Contact display name. |
| `email` | string | Contact email. |
| `phone` | string | Contact phone number. |

### Opportunity (CRM)
Represents a sales opportunity linked to an account and optionally an event.

| Field | Type | Description |
|-------|------|-------------|
| `opportunity_id` | string | Primary key. |
| `event_id` | string | Source event. Null for non-event opportunities. |
| `account_id` | string | Foreign key to Account. |
| `amount` | integer | USD amount. |
| `stage` | string | Pipeline stage. |

### Campaign Member (CRM)
Links an account/contact to an event campaign with a participation status.

| Field | Type | Description |
|-------|------|-------------|
| `campaign_member_id` | string | Primary key. |
| `event_id` | string | Source event. |
| `account_id` | string | Foreign key to Account. |
| `contact_id` | string | Foreign key to Contact. |
| `status` | enum | `attended`, `registered`, `attended_sponsor`, `registered_sponsor`, `excluded`. |

## Event domain entities

### Event
A conference, summit, or field day that generates badges, orders, and leads.

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | string | Primary key. |
| `name` | string | Display name. |
| `start_date` | string | ISO date. |
| `end_date` | string | ISO date. Key for follow-up date calculations. |
| `lead_opportunity_amount` | integer | USD amount per qualified lead from this event. |

### Event Order
A sponsor's purchase of a sponsor package for an event.

| Field | Type | Description |
|-------|------|-------------|
| `account_id` | string | Foreign key to Account. The sponsoring company. |
| `package_name` | string | Package identifier. |
| `package_amount` | integer | USD total price. |

### Badge
A scanned or registered attendee at an event.

| Field | Type | Description |
|-------|------|-------------|
| `badge_id` | string | Primary key. |
| `contact_name` | string | Attendee name. May be empty. |
| `company_name` | string | Stated company. May be empty. |
| `email` | string | Attendee email. May be empty. |
| `phone` | string | Attendee phone. May be empty. |
| `badge_type` | enum | `business`, `press`, `student`, `exhibitor`, `speaker`. |

### Sponsor Package
A defined sponsorship tier for an event.

| Field | Type | Description |
|-------|------|-------------|
| `package_id` | string | Primary key. |
| `name` | string | Package name. |
| `amount` | integer | USD price. |

## Finance domain

### Invoice
A bill issued against a sponsor order.

| Field | Type | Description |
|-------|------|-------------|
| `invoice_id` | string | Primary key. |
| `event_id` | string | Foreign key to Event. |
| `account_id` | string | Foreign key to Account. |
| `total_amount` | integer | USD invoice total. |
| `paid_amount` | integer | USD paid to date. |
| `status` | enum | `paid`, `partial`, `issued`. |

## Trade-show domain

### Tradeshow
An industry expo with exhibitors and meeting interest.

| Field | Type | Description |
|-------|------|-------------|
| `show_id` | string | Primary key. |
| `name` | string | Display name. |
| `start_date` | string | ISO date. |
| `end_date` | string | ISO date. |
| `venue` | string | Location. |

### Exhibitor
A company exhibiting at a trade-show. Separate namespace from CRM accounts.

| Field | Type | Description |
|-------|------|-------------|
| `company_id` | string | Primary key. Different from CRM account_id. |
| `company_name` | string | Display name. |
| `booth` | string | Booth number. |
| `country` | string | Country. |
| `website` | string | Company URL. |
| `relationship_type` | enum | `oem`, `distributor`, `service_provider`, `sensor_vendor`, `research`. |
| `platforms` | list[string] | Platform coverage (e.g., `["AUV", "ROV", "Underwater Camera"]`). |

### Meeting Interest
Records interest level and demo requests from exhibitors.

| Field | Type | Description |
|-------|------|-------------|
| `company_id` | string | Foreign key to Exhibitor. |
| `interest_score` | integer | 0-100 score. |
| `requested_demo` | boolean | Whether a demo was requested. |

## Import domain

### Import Batch
A batch of raw contacts awaiting CRM import.

| Field | Type | Description |
|-------|------|-------------|
| `batch_id` | string | Primary key. |
| `campaign_code` | string | Associated campaign. |
| `created_at` | string | ISO timestamp. |

### Raw Contact
A single row in an import batch before processing.

| Field | Type | Description |
|-------|------|-------------|
| `row_id` | string | Primary key. |
| `company_name` | string | May be empty. |
| `contact_name` | string | May be empty. |
| `email` | string | May be empty. |
| `phone` | string | May be empty. |
| `source_name` | enum | `badge_scan`, `sponsor_form`, `partner_upload`, `webinar_form`, `exhibitor_form`, `manual_upload`. |
| `captured_at` | string | ISO timestamp. |

### Suppression Entry
A record in a batch's suppression list.

| Field | Type | Description |
|-------|------|-------------|
| `email` | string | Email to suppress. May be empty. |
| `domain` | string | Domain to suppress. May be empty. |
| `company_name` | string | Company to suppress. May be empty. |

## Cross-entity join keys

The following pairs are the primary ways entities relate:

| From | To | Join key |
|------|----|----------|
| Event Order | CRM Account | `account_id` |
| Badge | CRM Account | company_name → account_name (normalized) |
| Badge | CRM Contact | email (normalized) → contact.email (normalized) |
| Invoice | Event | `event_id` |
| Invoice | CRM Account | `account_id` |
| Campaign Member | Event | `event_id` |
| Campaign Member | CRM Account | `account_id` |
| Campaign Member | CRM Contact | `contact_id` |
| Opportunity | Event | `event_id` |
| Opportunity | CRM Account | `account_id` |
| Exhibitor | CRM Account | company_name → account_name (normalized) |
| Meeting Interest | Exhibitor | `company_id` |
| Raw Contact | CRM Account | company_name → account_name (normalized) |
| Raw Contact | CRM Contact | email (normalized) → contact.email (normalized) |
| Suppression | Raw Contact | email (normalized) or company_name (normalized) |

## Relationship type to exclusion reason mapping

For trade-show prospecting, the exhibitor's `relationship_type` directly maps to the exclusion reason when that type is not qualified:

| `relationship_type` | Exclusion reason if excluded |
|---------------------|---------------------------|
| `distributor` | `distributor_only` |
| `service_provider` | `service_only` |
| `sensor_vendor` | `sensor_vendor_only` |
| `research` | `research_only` |

When an exhibitor has a qualifying relationship_type but is excluded for another reason (e.g., platform mismatch), use `not_target_market`.
