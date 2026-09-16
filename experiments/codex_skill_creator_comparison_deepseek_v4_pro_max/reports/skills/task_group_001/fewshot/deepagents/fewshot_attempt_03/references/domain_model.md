## Core Domain Objects

### Events
Events are the top-level entity for post-event CRM handoff tasks. Key fields:
- `event_id`: Stable string identifier (e.g., `neuralops_2026`, `edgeai_field_2026`)
- `name`: Display name
- `start_date` / `end_date`: ISO date strings
- `lead_followup_days`: Integer days after end_date for lead follow-up deadline
- `sponsor_followup_days`: Integer days after end_date for sponsor finance follow-up deadline
- `lead_opportunity_amount`: Integer USD amount to use as per-lead opportunity value

### Sponsor Orders
Orders link sponsor accounts to an event. Key fields:
- `account_id`, `account_name`: The sponsor
- `package_amount`: Integer USD
- `status`: One of `confirmed`, `pending`, `cancelled`, `draft`
- `invoice_id`: String or null

### Sponsor Status Logic
Derive sponsor status by cross-referencing orders with invoices:

| Order Status | Invoice State          | Sponsor Status   |
|-------------|------------------------|------------------|
| confirmed   | paid (paid == total)   | paid_deferred    |
| confirmed   | partial/open (unpaid)  | open_invoice     |
| pending/draft | any or no invoice    | proposal_only    |
| cancelled   | any                    | inactive — exclude from sponsor_statuses |

Controlled status values: `paid_deferred`, `open_invoice`, `proposal_only`.

### Badge Scans
Badge scans represent individuals who attended or registered for an event. Key fields:
- `badge_id`: Unique string
- `contact_name`, `company_name`: Who and where
- `email`, `phone`: Raw contact data (may be empty/null)
- `badge_type`: Category — `business`, `sponsor`, `press`, `student`, `exhibitor`, `speaker`
- `scan_timestamp`: ISO timestamp

### Badge Classification Rules
For event handoff tasks, classify each badge:
1. **sponsor_attendee**: Company matches a sponsor account (active or inactive; cancelled orders still count as sponsor)
2. **non_business_badge**: badge_type is not `business` and not `sponsor` (press, student, exhibitor, speaker)
3. **existing_disqualified**: Company's CRM account has status = `disqualified`
4. **qualified_non_sponsor_lead**: business badge, non-sponsor company, not disqualified

### CRM Accounts
Accounts in the CRM. Key fields:
- `account_id`: String like `acct_*`
- `account_name`: Company name
- `status`: `active`, `disqualified`, `inactive`
- `owner_region`, `website`, `country`: optional metadata

### CRM Contacts
Contacts linked to accounts. Key fields:
- `contact_id`: String like `cont_*`
- `account_id`: Link to account (may be null)
- `contact_name`, `email`, `phone`

### Matching Rules
- **Account matching**: Match by `account_id` first, then by normalized `account_name`/`company_name` (case-insensitive, trimmed)
- **Contact matching**: Match by normalized email within the same account; fall back to normalized phone if email unavailable
- **CRM action for accounts**: `create_account` if no match found; `update_existing` if match found
- **CRM action for contacts**: `create_contact` if no match found; `update_existing` if match found

### Campaign Members
Records linking contacts to campaigns. Key fields:
- `campaign_code`: Convention is `EVENT-{event_id}` for event campaigns, or batch-specific codes
- `subject_key`: Composite key like `acct_{id}:cont_{id}` or `badge:{badge_id}`
- `status`: `attended`, `registered`, `sent`, `attended_sponsor`, `registered_sponsor`, `excluded`
- `source`: `badge_scan`, `order`, etc.

### Campaign Member Actions
For each contact that should appear in the campaign:
- **create**: New campaign member record needed (no existing record found)
- **update**: Existing campaign member found, status needs update
- **no_action**: Existing campaign member with correct status already
- **no_import**: Excluded contacts (sponsor attendees with existing records, non-business, disqualified)

When checking existing campaign members, match by `subject_key` (or by `account_id` + `contact_id` combination).

### Invoices
Financial records. Key fields:
- `invoice_id`: String
- `total_amount`, `paid_amount`, `open_balance`: Integer USD
- `status`: `paid`, `partial`, `open`
- `due_date`: ISO date or null

### Opportunities
Sales opportunities. Key fields:
- `opportunity_id`: String
- `account_id`, `account_name`: Target account
- `event_id`: Optional link to event
- `amount`: Integer USD
- `stage`: `prospecting`, `qualified`, `closed_won`, `closed_lost`

### Import Batches
Contact list imports awaiting CRM processing:
- `batch_id`: String identifier
- `campaign_code`: Associated campaign
- `raw_contacts`: List of rows with `row_id`, `company_name`, `contact_name`, `email`, `phone`, `source_name`, `captured_at`
- `suppression`: List of email/phone suppression entries that flag contacts to remove

### Import Batch Processing Rules
1. Normalize all emails and phones across raw contacts
2. **Deduplication**: Group by `email:{normalized_email}`. For duplicates, winner = row with most recent `captured_at` timestamp; break ties by lowest `row_id` alphanumerically
3. **Suppression**: Remove rows whose normalized email or normalized phone appears in any suppression entry
4. **Missing contact**: Remove rows where `contact_name` is empty/null/missing
5. **Remaining = clean contacts**: Each gets a `crm_action` based on CRM account/contact matching
6. `campaign_member_import_count` = count of clean contacts

### Trade Shows & Exhibitors
Trade show prospecting entities:
- **Trade show**: `show_id`, `name`, `start_date`, `end_date`
- **Exhibitor**: `company_id` (like `exh_*`), `company_name`, `booth`, `country`, `website`, `relationship_type`, `platforms` (list of strings)
- **Meeting interest**: `company_id`, `requested_demo` (boolean), `interest_score` (0-100)

### Trade Show Prospecting Rules
- **Qualification**: relationship_type = `manufacturer` AND at least one platform appears in the policy-defined `prospecting_platforms` list
- **Exclusion reasons map**:
  - `distributor` → `distributor_only`
  - `service_provider` → `service_only`
  - `sensor_vendor` → `sensor_vendor_only` or `sensor_only`
  - `research` → `research_only`
- **Priority tiers** (determined from policies + meeting interest):
  - `A`: requested_demo AND interest_score >= policy threshold (typically 90)
  - `B`: requested_demo AND interest_score >= policy threshold (typically 80)
  - `C`: all other qualified leads
- **Opportunity amounts per tier**: Read from policies; common values: A=120000, B=90000, C=50000
- **CRM action**: `update_existing` if company_id matches a CRM account; `create_account` otherwise; `no_import` for excluded
- **Ranking**: demo request (true first), interest_score descending, platform count descending, company_name ascending

## Cross-Cutting Rules

### Contact Normalization
- **Email**: lowercased, trimmed. Empty string if null/empty.
- **Phone**: digits only (strip all non-digit characters). Empty string if null/empty or no digits.
- **Deduplication key format**: `email:{normalized_email}` or `phone:{normalized_phone}`

### Date Arithmetic
- Follow-up due dates: `{event.end_date} + {event.lead_followup_days}` (calendar days) → YYYY-MM-DD
- Sponsor finance due date: `{event.end_date} + {event.sponsor_followup_days}` (calendar days) → YYYY-MM-DD

### Sorting Conventions
Unless the answer template specifies otherwise:
- Accounts/sponsors: by `account_name` ascending
- Qualified leads: by `account_name` or `company_name` ascending
- Excluded records: by `company_name` ascending, then `contact_name` ascending
- Badges: by `badge_id` ascending
- Duplicate keys: by `key` ascending
- Removed rows: by `row_id` ascending
- Platform lists within an item: use enum order (AUV, ROV, Underwater Camera)

### CRM Action Counts
Sum across all clean/handoff records:
- `accounts_create`: count of `create_account` actions
- `accounts_update`: count of `update_existing` actions (for accounts)
- `contacts_create`: count of `create_contact` actions
- `contacts_update`: count of `update_existing` actions (for contacts)
- `campaign_members_create`: count of new campaign member records
- `campaign_members_update`: count of campaign member status updates

### Output Discipline
- Return one JSON object only, matching the provided answer template
- Do not include explanatory prose outside the JSON
- Use integer values for all USD amounts and counts
- Use the exact enum values specified in the template
- Do not add fields not declared in the template
