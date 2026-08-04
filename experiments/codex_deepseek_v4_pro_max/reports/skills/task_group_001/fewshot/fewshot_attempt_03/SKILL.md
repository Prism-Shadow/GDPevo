## HarborCRM Data Analysis Skill

This skill equips an agent to perform CRM data handoff, reconciliation, prospecting, and batch‑import tasks against the **HarborCRM** REST API. HarborCRM is a fictional event, trade‑show, and CRM management system. All public endpoints are read‑only GET requests with no authentication.

### Environment Discovery

1. Read the local `environment_access.md` file (if present) for the API base URL. The URL is stored as `GDPEVO_ENV_BASE_URL` or may be supplied by the runner as `<TASK_ENV_BASE_URL>`.
2. Confirm the base URL ends with a trailing slash; append one if missing.
3. Test connectivity with a simple `GET` to the root or `/api/events` before starting.

### API Endpoint Catalog

Every task uses a subset of the following endpoints. All accept standard `?query=param` filtering and respond with JSON arrays or objects.

**Event & Order Endpoints**
- `GET /api/events` – list all events
- `GET /api/events/{event_id}` – single event detail (name, dates, lead opportunity amount)
- `GET /api/events/{event_id}/orders` – sponsor orders (package, amount, status)
- `GET /api/events/{event_id}/badges` – scanned attendee badges (company, contact, badge type, email, phone)
- `GET /api/events/{event_id}/sponsor_packages` – available sponsor package definitions

**Finance Endpoints**
- `GET /api/finance/invoices?event_id={event_id}` – invoices for an event
- `GET /api/finance/invoices?account_id={account_id}` – invoices for a CRM account

**CRM Endpoints**
- `GET /api/crm/accounts` – all CRM accounts; filterable by `?status=` and `?owner_region=`
- `GET /api/crm/contacts` – contacts; filterable by `?account_id=`
- `GET /api/crm/opportunities` – opportunities; filterable by `?event_id=` and `?account_id=`
- `GET /api/crm/campaign_members` – campaign memberships; filterable by `?event_id=` and `?account_id=`

**Trade‑Show Endpoints**
- `GET /api/tradeshows` – list all trade shows
- `GET /api/tradeshows/{show_id}` – single show detail
- `GET /api/tradeshows/{show_id}/exhibitors` – exhibitor records (company_id, company_name, platforms, booth, country, website, relationship_type)
- `GET /api/tradeshows/{show_id}/meeting_interest` – meeting‑interest scores per exhibitor (demo request flag, interest score)

**Import Batch Endpoints**
- `GET /api/import_batches` – list all import batches
- `GET /api/import_batches/{batch_id}` – batch detail
- `GET /api/import_batches/{batch_id}/raw_contacts` – raw import rows
- `GET /api/import_batches/{batch_id}/suppression` – suppression list for the batch

**Policy Endpoint**
- `GET /api/policies` – business‑rule metadata (qualification criteria, platform coverage, exclusion rules, due‑date offsets, campaign codes)

### General Workflow

1. **Read the prompt** to identify the task type and any provided identifiers (event_id, show_id, batch_id).
2. **Read the answer template** (`input/payloads/answer_template.json`) to understand the required output shape, field names, controlled vocabularies, and sorting rules.
3. **Fetch policies** (`GET /api/policies`) early — policies define qualification criteria, platform enums, exclusion rules, lead opportunity amounts, follow‑up due‑date offsets, and campaign codes.
4. **Fetch core data** from the endpoints relevant to the task. Always fetch CRM accounts and contacts to cross‑reference existing records.
5. **Classify and filter** records using the rules below.
6. **Normalize** contact fields (email, phone).
7. **Sort** results exactly as the template specifies.
8. **Return a single JSON object** with no explanatory prose outside the JSON.

### Sponsor Classification Rules

When a task involves event sponsors, classify each sponsor into exactly one controlled status:

- **`paid_deferred`** – the sponsor order is fully paid (paid amount equals package amount) OR the invoice shows zero open balance.
- **`open_invoice`** – an invoice exists with a positive open balance (paid amount < package amount).
- **`proposal_only`** – a sponsor order or package exists but no invoice has been issued.

For sponsor revenue totals, sum package amounts per status. For `open_invoice`, also report the sum of open balances separately. All monetary values are integers in USD.

Only active sponsor records are included; canceled or inactive sponsor records are excluded and logged in the exclusion list with reason `inactive_sponsor_record`.

### Lead Qualification Rules (Event Tasks)

For post‑event handoffs, qualified non‑sponsor leads are badge‑scanned attendees who:

- Do **not** belong to a sponsor company.
- Do **not** belong to a CRM account whose status is already disqualified (`existing_disqualified`).
- Hold a business‑type badge (not student, press, or other non‑business badges: `non_business_badge`).
- Have at least a contact name present in the badge data (not `missing_contact`).

For each qualified lead:
- Use the event's lead opportunity amount (from the event detail or policies) as the opportunity estimate.
- If the company already exists in CRM accounts, the account action is `update_existing`; otherwise `create_account`.
- If the contact already exists in CRM contacts under the same account, the contact action is `update_existing`; otherwise `create_contact`.
- The campaign member action is always `add_campaign_member` for qualified leads.

### Trade‑Show Prospecting Rules

For trade‑show prospecting tasks:

1. Fetch the show's exhibitors (`/api/tradeshows/{show_id}/exhibitors`) and meeting‑interest data (`/api/tradeshows/{show_id}/meeting_interest`).
2. Cross‑reference with CRM accounts (`/api/crm/accounts`) and CRM contacts (`/api/crm/contacts`).
3. Use policies to determine which platform coverage values and relationship types qualify.
4. **Qualified exhibitors** are those whose platforms overlap with the campaign's target platform set AND whose relationship type is not in the exclusion set (distributor, service provider, sensor vendor, research).
5. **Excluded near‑misses** are exhibitors that are close but excluded for a controlled reason:
   - `distributor_only` – relationship is distributor
   - `service_only` – relationship is service provider
   - `sensor_vendor_only` / `sensor_only` – relationship is sensor vendor
   - `research_only` – relationship is research
   - `not_target_market` – no platform overlap at all
6. When ranking is required: demo requests first, then by interest score descending, then by broader platform coverage, then by company name ascending.
7. Assign priority tiers and opportunity amounts per the task prompt's tier‑amount mapping.

### Batch Import Rules

For batch import preparation:

1. Fetch raw contacts and the suppression list.
2. Cross‑reference email addresses and phone numbers with existing CRM contacts for deduplication.
3. **Duplicate handling**: when multiple rows share the same email or phone, keep the row with the most authoritative source (partner_upload > webinar_form > exhibitor_form > badge_scan > sponsor_form > manual_upload) and earliest captured_at as tie‑breaker. Record removed duplicates.
4. **Suppression**: rows whose email or phone appears on the suppression list are flagged `suppress`.
5. **Unusable rows**: rows missing both contact name are flagged `missing_contact`.
6. **CRM actions** per clean contact:
   - `update_existing` if company matches an existing CRM account
   - `create_account` if no existing CRM account matches
   - `no_import` for unusable rows
   - `suppress` for suppressed rows
7. The campaign member import count is the number of clean contacts with `crm_action` of `create_account` or `update_existing`.

### Data Normalization Rules

- **Email**: lowercase, trim leading/trailing whitespace. Empty string `""` when no email is supplied.
- **Phone**: extract digits only; strip all non‑digit characters. Empty string `""` when no phone is supplied.
- **Monetary values**: always integers in USD. Sum at the level specified.
- **Dates**: `YYYY-MM-DD` format. Compute follow‑up due dates by adding the policy‑defined offset (in days) to the event or show date.
- **Country and website**: use values as returned by the API without modification.

### Controlled Vocabularies

| Domain | Values |
|---|---|
| Sponsor status | `paid_deferred`, `open_invoice`, `proposal_only` |
| CRM account action | `create_account`, `update_existing`, `no_import`, `suppress` |
| CRM contact action | `create_contact`, `update_existing` |
| Campaign member action | `add_campaign_member`, `create`, `update`, `no_action`, `no_import` |
| Campaign member target status | `attended`, `attended_sponsor`, `registered_sponsor`, `excluded` |
| Exclusion reasons (event) | `sponsor_attendee`, `existing_disqualified`, `inactive_sponsor_record`, `non_business_badge`, `missing_contact` |
| Exclusion reasons (tradeshow) | `distributor_only`, `service_only`, `sensor_vendor_only`, `sensor_only`, `research_only`, `not_target_market` |
| Relationship types | `distributor`, `service_provider`, `sensor_vendor`, `research` |
| Platforms | `AUV`, `ROV`, `Underwater Camera` |
| Priority tiers | `A`, `B`, `C` |
| Import source names | `badge_scan`, `sponsor_form`, `partner_upload`, `webinar_form`, `exhibitor_form`, `manual_upload` |
| Badge classification | `sponsor_attendee`, `qualified_non_sponsor_lead`, `excluded` |

### Sorting Rules

Sort rules are always specified in the answer template. Common patterns:

- Sponsor statuses: by `account_name` ascending.
- Qualified leads: by `account_name` or `company_name` ascending, unless ranked.
- Ranked leads: by `rank` ascending.
- Excluded records: by `company_name` ascending, then `contact_name` ascending (when both fields are present).
- Badge decisions: by `badge_id` ascending.
- Campaign member actions: by `subject_key` ascending.
- Clean contacts: by `clean_contact_id` ascending.
- Duplicate keys: by `key` ascending.
- Removed rows: by `row_id` ascending.
- Platform lists within an item: always in enum order (`AUV`, `ROV`, `Underwater Camera`).

### Response Format Rules

- Return **exactly one JSON object** matching the answer template shape.
- Do **not** include explanatory prose, markdown fences, or commentary outside the JSON.
- Include every top‑level key and required sub‑key from the template, even if the value is zero, empty, or null.
- Null vs. empty: use `null` for absent relational IDs (e.g., no matching CRM account); use `""` for absent strings (e.g., no email); use `0` for absent counts.

### Common Pitfalls

- Forgetting to fetch `/api/policies` — many business rules (platform lists, exclusion criteria, due‑date offsets, lead amounts) are policy‑driven.
- Crossing sponsor attendees into the qualified lead list — always filter out badge scans whose company matches a sponsor account.
- Using non‑integer monetary values — all amounts must be integers.
- Miscounting CRM action totals — derive them from the classified output lists, not from raw API counts.
- Sorting platform lists arbitrarily — always use the canonical enum order: `AUV`, `ROV`, `Underwater Camera`.
- Treating canceled/inactive sponsor records as active — check order/invoice status before including in sponsor summaries.
