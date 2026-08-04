## When to use this skill

Use this skill whenever you need to read, reconcile, qualify, or prepare CRM data through the HarborCRM API. Typical triggers include event handoff audits, trade-show prospecting, batch import preparation, and post-event reconciliation.

## HarborCRM API access

All data lives behind the HarborCRM REST API. The runner provides the base URL in the environment variable `GDPEVO_ENV_BASE_URL` (or `<TASK_ENV_BASE_URL>` in prompts). No authentication is required for GET requests.

Every API call is a plain HTTP GET. Construct URLs as `{GDPEVO_ENV_BASE_URL}/api/{resource}` with optional query parameters. The API returns JSON arrays or objects.

Do not invent endpoint paths. Use only the endpoints listed in the environment access instructions or documented here.

## Available endpoints

### Events
- `GET /api/events` — list all events; optional `?status=<status>` filter
- `GET /api/events/{event_id}` — single event detail
- `GET /api/events/{event_id}/orders` — sponsor orders for an event
- `GET /api/events/{event_id}/badges` — badge scans for an event
- `GET /api/events/{event_id}/sponsor_packages` — sponsor packages for an event

### Finance
- `GET /api/finance/invoices?event_id=<event_id>` — invoices scoped to an event
- `GET /api/finance/invoices?account_id=<account_id>` — invoices scoped to an account

### CRM core
- `GET /api/crm/accounts` — all accounts; optional `?status=<status>` or `?owner_region=<region>`
- `GET /api/crm/contacts` — all contacts; optional `?account_id=<account_id>`
- `GET /api/crm/opportunities` — all opportunities; optional `?event_id=<event_id>` or `?account_id=<account_id>`
- `GET /api/crm/campaign_members` — all campaign members; optional `?event_id=<event_id>` or `?account_id=<account_id>`

### Trade shows
- `GET /api/tradeshows` — list all trade shows
- `GET /api/tradeshows/{show_id}` — single show detail
- `GET /api/tradeshows/{show_id}/exhibitors` — exhibitors for a show
- `GET /api/tradeshows/{show_id}/meeting_interest` — meeting-interest records for a show

### Import batches
- `GET /api/import_batches` — list all import batches
- `GET /api/import_batches/{batch_id}` — single batch detail
- `GET /api/import_batches/{batch_id}/raw_contacts` — raw contact rows in the batch
- `GET /api/import_batches/{batch_id}/suppression` — suppression list for the batch

### Policies
- `GET /api/policies` — business-rule policies that drive qualification criteria, priority tiers, opportunity sizing, follow-up timelines, and exclusion logic

## Core data model

The HarborCRM world is built on these entities, which you must cross-reference across endpoints:

- **Account** — a company or organization. Has `account_id`, `account_name`, `status`, `owner_region`. Accounts can be sponsors, prospects, or disqualified.
- **Contact** — a person. Has `contact_id`, `contact_name`, `email`, `phone`, and a foreign `account_id`.
- **Opportunity** — a potential deal. Has `amount`, `event_id`, `account_id`.
- **Campaign Member** — links a contact/account to an event or campaign. Has a `status` (e.g., `attended`, `registered`, `attended_sponsor`, `registered_sponsor`, `excluded`).
- **Event** — a conference or summit. Has `event_id`, `event_name`, `lead_opportunity_amount`.
- **Trade Show** — a trade show. Has `show_id`, `name`, `exhibitors` sub-resource.
- **Exhibitor** — a company at a trade show. Has `company_id`, `company_name`, `booth`, `country`, `website`, `platforms`, `relationship_type`.
- **Meeting Interest** — demo or meeting requests from exhibitors. Has `company_id`, `requested_demo` (boolean), `interest_score` (integer).
- **Badge** — a scanned badge at an event. Has `badge_id`, `company_name`, `contact_name`, `email`, `phone`, `badge_type`, `classification`.
- **Order** — a sponsor order. Has `account_id`, `package_amount`, `status`.
- **Invoice** — a finance invoice. Has `invoice_id`, `account_id`, `event_id`, `amount`, `paid_amount`, `open_balance`, `status`.
- **Import Batch** — a batch of raw contacts to import. Has `batch_id`, `campaign_code`. Contains `raw_contacts` rows and a `suppression` list.
- **Policy** — a rule document returned by `/api/policies`. Policies define qualification logic, priority tier thresholds, opportunity amounts, follow-up schedules, and exclusion rules.

## Primary workflow patterns

### 1. Event reconciliation (post-event handoff)

**Goal**: Produce a CRM-ready handoff after an event by reconciling sponsor orders, badge scans, invoices, and existing CRM records.

1. Fetch the event, its orders, badges, sponsor packages, and related invoices.
2. Fetch all CRM accounts, contacts, opportunities, and campaign members (filter by `event_id` where applicable).
3. Fetch `/api/policies` to determine lead opportunity amounts, follow-up due dates, and qualification rules.
4. Classify each sponsor account into a sponsor status using invoice/order data.
5. Classify each badge as sponsor_attendee, qualified_non_sponsor_lead, or excluded.
6. Determine CRM actions (create vs. update) for accounts, contacts, and campaign members by cross-referencing badges against existing CRM records.
7. Normalize contact fields: lowercase and trim emails, strip phone to digits only, use empty string when missing.
8. Assemble the output JSON conforming to the provided answer template. Sort lists as specified. Do not add fields outside the template.

### 2. Trade-show prospecting (campaign lead generation)

**Goal**: Identify qualified exhibitors from a trade show for a specific product campaign.

1. Fetch the trade show, its exhibitors, and its meeting-interest records.
2. Fetch all CRM accounts and contacts for overlap detection.
3. Fetch `/api/policies` to determine which platform categories qualify, priority-tier thresholds, and opportunity sizing.
4. Filter exhibitors: qualify those whose platforms match the campaign's target and whose relationship type is valid (exclude distributors, service-only, sensor-only, research-only, etc. as dictated by policy).
5. For each qualified exhibitor, determine `crm_action`: `create_account` if no existing CRM account matches, `update_existing` if one does.
6. Rank qualified exhibitors by the policy-specified sort order (typically demo request first, then interest score, then platform coverage breadth, then company name).
7. Assign priority tiers (A/B/C) and opportunity estimates per policy rules.
8. Track excluded exhibitors as near-misses with a controlled exclusion reason.
9. Produce aggregate counts: qualified total, platform coverage counts, priority counts, excluded total.

### 3. Batch import preparation

**Goal**: Clean, deduplicate, and classify raw contact rows from an import batch for CRM ingestion.

1. Fetch the import batch, its raw contacts, and its suppression list.
2. Fetch all CRM accounts and contacts for duplicate/existing-account detection.
3. Fetch `/api/policies` for any import-specific rules.
4. Normalize every raw contact row: lowercase email, digits-only phone.
5. Detect duplicate rows by the policy-defined duplicate key (typically normalized email). Keep one winner per key; mark the rest for removal.
6. Identify rows with missing contact name as unusable.
7. Identify rows whose email matches the suppression list as suppressed.
8. For surviving clean contacts, determine `crm_action` by matching against existing CRM accounts and contacts.
9. Produce the clean contact list, removal summary, duplicate summary, action totals, and campaign-member import count.

## Controlled vocabularies

Use only these exact values. See `vocabulary.md` for the full reference.

**Sponsor statuses**: `paid_deferred`, `open_invoice`, `proposal_only`, `not_sponsor`

**CRM account actions**: `create_account`, `update_existing`, `no_import`, `suppress`

**CRM contact actions**: `create_contact`, `update_existing`

**CRM campaign-member actions**: `add_campaign_member`, `create`, `update`, `update_campaign_member`, `no_action`, `no_import`

**Combined CRM actions** (for single-step badge handling): `create_account_contact_campaign_member`, `create_contact_campaign_member`

**Campaign-member target statuses**: `attended_sponsor`, `registered_sponsor`, `attended`, `excluded`

**Badge classifications**: `sponsor_attendee`, `qualified_non_sponsor_lead`, `excluded`

**Exclusion reasons**: `sponsor_attendee`, `existing_disqualified`, `inactive_sponsor_record`, `non_business_badge`, `missing_contact`, `duplicate`, `suppressed`, `distributor_only`, `service_only`, `sensor_vendor_only`, `sensor_only`, `research_only`, `not_target_market`

**Platform enums**: `AUV`, `ROV`, `Underwater Camera`

**Priority tiers**: `A`, `B`, `C`

**Contact source names**: `badge_scan`, `sponsor_form`, `partner_upload`, `webinar_form`, `exhibitor_form`, `manual_upload`

**Trade-show relationship types**: `distributor`, `service_provider`, `sensor_vendor`, `research`

## Data normalization rules

- **Email**: Convert to lowercase, trim whitespace. Use empty string `""` when no email is supplied.
- **Phone**: Strip all non-digit characters. Use empty string `""` when no phone is supplied.
- **Company/account name**: Use as-is from the source; do not transform.
- **IDs**: Preserve exact strings from API responses.

## Output conventions

- Return **one JSON object** and nothing else. No explanatory prose, no markdown fences.
- Conform exactly to the provided answer template. Do not add, remove, or rename keys.
- All counts are integers. All monetary amounts are integer USD (no decimals).
- Dates use `YYYY-MM-DD` format.
- Sort lists as specified in the template or task prompt. Common sort orders:
  - Accounts and companies by name ascending.
  - Badges by `badge_id` ascending.
  - Ranks by `rank` ascending.
  - IDs and keys ascending.
  - Platforms in enum order: `AUV`, `ROV`, `Underwater Camera`.

## Entity matching and resolution

When determining whether a badge, exhibitor, or import row corresponds to an existing CRM record:

1. Match by `account_id` first when a direct foreign key is present.
2. Match account by normalized company name (case-insensitive exact match).
3. Match contact within an account by normalized email (lowercase, trimmed).
4. If no email match, fall back to normalized phone (digits-only).
5. If no CRM match exists and the record is qualified, mark for `create_account` / `create_contact`.
6. If a CRM match exists and the record is qualified, mark for `update_existing`.
7. Disqualified CRM accounts propagate exclusion: any contact or badge linked to a disqualified account is excluded as `existing_disqualified`.

## Policy-driven decisions

Always fetch `/api/policies` early. The policy document controls:

- Which platforms, relationship types, or badge types qualify for a campaign.
- Priority-tier thresholds and opportunity dollar amounts.
- Follow-up due dates (often relative to event date or current date).
- Deduplication key logic (e.g., which field constitutes a duplicate).
- Suppression rules.

Treat policy values as authoritative over any defaults suggested in this skill.

## Error handling and edge cases

- If an endpoint returns an empty array or a 404-like empty object, treat it as "no data" rather than an error.
- If a referenced foreign key (e.g., `account_id` on a contact) points to a missing record, still process the entity but note the orphan.
- When a badge or import row has no usable contact name, it is excluded as `missing_contact`.
- Inactive or canceled sponsor records do not count toward sponsor revenue or lead pipeline.
- A sponsor's own personnel (badges from sponsor companies) are always excluded from lead qualification as `sponsor_attendee`.
- Non-business badge types (e.g., exhibitor, staff, guest) are excluded as `non_business_badge`.
