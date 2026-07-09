# HarborCRM Skill

## Environment

Base URL: use the API base URL supplied by the runner. All endpoints are relative to this base. Do not start local services or run setup scripts.

## API Endpoints by Domain

### Events
- `GET /api/events/{event_id}` — event metadata (dates, follow-up offsets, lead opportunity amount, campaign code)
- `GET /api/events/{event_id}/orders` — sponsor orders (account_id, amount, order_status, package_level, ticket_contacts)
- `GET /api/events/{event_id}/badges` — scanned badges (badge_type, company_name, contact_name, email, phone, scan_score)
- `GET /api/events/{event_id}/sponsor_packages` — same shape as orders

### Finance
- `GET /api/finance/invoices?event_id={event_id}` — invoices (amount, paid_amount, deferred_amount, status, due_date, payment_date)

### CRM
- `GET /api/crm/accounts` — all CRM accounts (account_id, name, domain, status, disqualified_reason)
- `GET /api/crm/contacts` — all CRM contacts (account_id, contact_id, email, name, phone, opted_out)
- `GET /api/crm/opportunities` — all opportunities (account_id, amount, stage, event_id)
- `GET /api/crm/campaign_members?event_id={event_id}` — event campaign members (account_id, contact_id, status, last_activity_date)

### Tradeshows
- `GET /api/tradeshows` — list all shows
- `GET /api/tradeshows/{show_id}/exhibitors` — exhibitors with company_id, description, booth, country, website, crm_account_id
- `GET /api/tradeshows/{show_id}/meeting_interest` — demo requests and interest scores

### Import Batches
- `GET /api/import_batches` — list batches
- `GET /api/import_batches/{batch_id}/raw_contacts` — raw contact rows
- `GET /api/import_batches/{batch_id}/suppression` — suppression list (email, phone, reason)

### Policies
- `GET /api/policies` — platform enums, qualification notes, sponsor status enums

## Sponsor Status Rules

Assign one of: `paid_deferred`, `open_invoice`, `proposal_only`, `not_sponsor`.

| Condition | Status |
|---|---|
| Invoice exists with `status: "paid_deferred"` (fully paid) | `paid_deferred` |
| Invoice exists with `status: "open"` (balance remaining) | `open_invoice` |
| Sponsor order exists but no invoice | `proposal_only` |
| Order `order_status: "canceled"` | exclude from sponsor list (inactive) |

- `open_balance` = `amount - paid_amount` for each sponsor line.
- For `paid_deferred`, `open_balance` is 0, `paid_amount` is full amount.
- For `proposal_only`, `invoice_id` is null, `paid_amount` is 0, `open_balance` is 0.
- Revenue totals aggregate by status. `open_invoice_balance` sums open balances of open-invoice sponsors.

## Badge Classification (Event Reconciliation Tasks)

Each badge gets one classification and one crm_action:

| Badge type / Company status | Classification | crm_action | exclusion_reason |
|---|---|---|---|
| `badge_type: "sponsor"` | `sponsor_attendee` | `no_import` | `sponsor_attendee` |
| Company has active sponsor order (any badge type) | `sponsor_attendee` | `no_import` | `sponsor_attendee` |
| `badge_type` is `student`, `press`, `vendor_staff`, etc. | `excluded` | `no_import` | `non_business_badge` |
| CRM account `status: "disqualified"` | `excluded` | `no_import` | `existing_disqualified` |
| Sponsor order `order_status: "canceled"` | `excluded` | `no_import` | `inactive_sponsor_record` |
| Missing contact_name (empty/whitespace only) | `excluded` | `no_import` | `missing_contact` |
| Attendee badge, company not a sponsor, account not disqualified | `qualified_non_sponsor_lead` | `create_account_contact_campaign_member` | null |

For qualified non-sponsor leads where the CRM account already exists, use `create_contact_campaign_member` instead of `create_account_contact_campaign_member`.

Apply exclusions in priority order: sponsor → inactive sponsor → non-business badge → disqualified → missing contact. The first matching exclusion is used.

## Campaign Member Actions (Event Reconciliation)

Create one entry per badge contact plus existing campaign members that need action:

- `subject_key`: `"{account_name} | {contact_name}"` (accessible sort key)
- `action`: `create` (new), `no_action` (existing, correct status), `no_import` (excluded)
- `target_status`: `attended_sponsor` for sponsor attendees, `attended` for qualified leads, `registered_sponsor` for sponsor contacts without a badge scan, `excluded` for excluded badges

Existing campaign members whose status is already correct get `action: "no_action"`.

## Tradeshow Prospecting Qualification

### Platform Assignment
Read the exhibitor `description` field. Assign platforms from the policy enums: `AUV`, `ROV`, `Underwater Camera`.

- **AUV**: builds/manufactures autonomous underwater vehicles
- **ROV**: builds/manufactures remotely operated vehicles
- **Underwater Camera**: builds/OEM-manufactures underwater camera hardware

Companies that ONLY distribute, resell, provide services, make sensors (not platforms), or do research/analytics without manufacturing hardware are **excluded**.

### Exclusion Reasons (controlled enum)
| Business type | `exclusion_reason` |
|---|---|
| Distributor/reseller, no manufacturing | `distributor_only` |
| Service/consulting/analytics, no hardware build | `service_only` |
| Sensor-only vendor, no platform build | `sensor_vendor_only` |
| Research-only, no product build | `research_only` |
| Does not serve target market | `not_target_market` |

For tasks using `relationship_type` + `exclusion_reason` pairs: map `distributor` → `distributor_only`, `service_provider` → `service_only`, `sensor_vendor` → `sensor_only`, `research` → `research_only`.

### Priority Tier Assignment
When explicit tier rules are provided in the task prompt, follow them. The default pattern (used when rules are not explicit):
- **A**: demo requested AND interest score ≥ 90 (USD 120,000)
- **B**: demo requested AND interest score ≥ 80 (USD 90,000)
- **C**: all other qualified (USD 50,000)

When the task defines specific opportunity amounts per tier, use those amounts. Otherwise, use the event's `lead_opportunity_amount`.

### Ranking
When ranking is required:
1. Demo requested first (true before false)
2. Interest score descending
3. Number of platforms covered descending (broader coverage first)
4. Company name ascending (alphabetical tiebreaker)

Ranks are 1-based and contiguous.

## Import Batch Cleaning

### Contact Normalization
- **Email**: trim whitespace, convert to lowercase. Empty after trim → empty string.
- **Phone**: extract digits only. Empty after extraction → empty string.

### Deduplication
- **Dedup key**: normalized email address.
- When multiple rows share the same normalized email, pick one winner.
- Winner selection: prefer the row with earliest `captured_at` (first capture wins). On timestamp tie, prefer the lower `row_id`.
- Use the winner's raw field values (company_name, contact_name, etc.) for the clean contact record.
- `clean_contact_id` = winning `row_id`. `source_row_id` = same winning `row_id`.

### Suppression
- Check each contact's normalized email and phone against the suppression list.
- If either matches → contact is suppressed (excluded from import).

### Missing Contact
- A row is unusable if `contact_name` is empty/whitespace only, OR if both normalized email AND normalized phone are empty.

### CRM Matching
- Match account by exact `company_name` match against CRM account `name`.
- Match contact by normalized email against CRM contact `email`.
- `crm_action`:
  - Account match AND contact match → `update_existing`
  - Account match, no contact match → `update_existing`
  - No account match, contact match → `update_existing`
  - No account match, no contact match → `create_account`
  - On suppression list → `suppress`
  - Missing contact → `no_import`
- `existing_account_id`: the matched CRM `account_id`, or null.
- `existing_contact_id`: the matched CRM `contact_id`, or null.

### Clean Contacts
- Include ONLY contacts with `crm_action` of `create_account` or `update_existing`.
- Suppressed and no_import rows go only in `removal_summary`, not in `clean_contacts`.

### Campaign Member Import Count
- Count of contacts in `clean_contacts` (the surviving importable contacts).

## Follow-Up Dates

- **Lead follow-up due date**: `end_date + followup_days_after_end` (ISO YYYY-MM-DD)
- **Sponsor finance due date**: `end_date + sponsor_followup_days_after_end` (ISO YYYY-MM-DD)
- If `start_date` equals `end_date` (single-day event), use that date as the base.

For events where only one follow-up offset is given, derive both dates from it.

## Sorting Rules (apply everywhere)

- Sort strings ascending alphabetically (case-sensitive, standard lexicographic).
- Sort lists of objects by the primary key specified in the template.
- Platform lists: always sort in enum order: `AUV`, `ROV`, `Underwater Camera`.
- Subject keys in campaign member actions: sort ascending by `subject_key`.
- Sponsor statuses and qualified leads: sort by `account_name`/`company_name` ascending.
- Excluded records: sort by `company_name` ascending, then `contact_name` ascending.
- Badge decisions: sort by `badge_id` ascending.
- Clean contacts: sort by `clean_contact_id` ascending.
- Duplicate keys: sort by `key` ascending.
- Removed rows: sort by `row_id` ascending.
- CRM account IDs in lists: sort ascending.

## Data Type Conventions

- All monetary amounts: integers (USD).
- All counts: integers.
- Boolean fields: JSON `true`/`false` (not strings).
- Nullable fields: JSON `null` when no value.
- Empty strings allowed for email/phone when no data was supplied.
- Dates: `YYYY-MM-DD` strings. Timestamps: ISO 8601 as returned by the API.

## Key Pitfalls

1. **Company name matching is exact**: "HelioWare Manufacturing" ≠ "HelioWare Mfg." in CRM. Use the winning row's exact company name for CRM lookups.
2. **Sponsor badge ≠ sponsor company**: A company with an active sponsor order makes ALL its badge holders sponsor attendees, even if their individual `badge_type` is `"attendee"`.
3. **Canceled ≠ inactive**: Only `order_status: "canceled"` is inactive. `proposal_sent` is an active (proposal_only) sponsor.
4. **Deferred revenue vs open balance**: `paid_deferred` means fully paid but revenue deferred for accounting — no follow-up needed. `open_invoice` means money is still owed — needs finance follow-up.
5. **Platform assignment from descriptions**: "Builds compact AUVs" → AUV; "camera modules" → Underwater Camera; "reseller" → no platform. Read descriptions literally; don't over-assign.
6. **Demo request drives ranking priority**: requested_demo=true always sorts before false, regardless of score.
7. **Suppression check happens during import cleaning**: contacts matching the suppression list by email or phone are excluded from import and counted as suppressed in totals.
8. **Empty email alone is not `missing_contact`**: a badge with a contact_name and phone but no email is still a valid lead unless the task explicitly requires email.
