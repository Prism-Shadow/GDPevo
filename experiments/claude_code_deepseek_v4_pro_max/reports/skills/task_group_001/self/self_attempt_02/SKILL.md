# HarborCRM Skill

## Environment

Base URL: `http://34.46.77.124:8001` (no auth required for public API). All `GET`.

## Endpoints by Task Type

### Event Reconciliation (train_001, train_004)
| Endpoint | Returns |
|---|---|
| `GET /api/events/{event_id}` | Event metadata, dates, campaign_code, followup_days, lead_opportunity_amount |
| `GET /api/events/{event_id}/orders` | Sponsor orders (same as sponsor_packages) |
| `GET /api/events/{event_id}/sponsor_packages` | Same as orders |
| `GET /api/events/{event_id}/badges` | Badge scans with contact info, badge_type, scan_score |
| `GET /api/finance/invoices?event_id={event_id}` | Invoices with paid_amount, deferred_amount, status |
| `GET /api/crm/accounts` | All CRM accounts (status, disqualified_reason) |
| `GET /api/crm/contacts` | All CRM contacts (opted_out, email, phone) |
| `GET /api/crm/opportunities` | All opportunities across events |
| `GET /api/crm/campaign_members?event_id={event_id}` | Existing campaign members |
| `GET /api/policies` | sponsor_handoff status_enums, contact_hygiene note |

### Trade-show Prospecting (train_002, train_005)
| Endpoint | Returns |
|---|---|
| `GET /api/tradeshows` | All trade shows |
| `GET /api/tradeshows/{show_id}/exhibitors` | Exhibitor list with company_id, description, crm_account_id |
| `GET /api/tradeshows/{show_id}/meeting_interest` | Interest scores, demo requests per company |
| `GET /api/crm/accounts` | CRM accounts for overlap detection |
| `GET /api/crm/contacts` | CRM contacts |
| `GET /api/policies` | prospecting platform_enums, qualification_note |

### Batch Import (train_003)
| Endpoint | Returns |
|---|---|
| `GET /api/import_batches` | All batches |
| `GET /api/import_batches/{batch_id}/raw_contacts` | Raw import rows with row_id, source_name, captured_at |
| `GET /api/import_batches/{batch_id}/suppression` | Suppression list (email, phone, reason) |
| `GET /api/crm/accounts` | CRM accounts for matching |
| `GET /api/crm/contacts` | CRM contacts for matching |
| `GET /api/policies` | contact_hygiene policy |

---

## Data Models & Field Conventions

### CRM Account
- `account_id` (string), `name` (string), `status` ("customer"|"prospect"|"disqualified")
- `disqualified_reason` (string|null) — non-null means disqualified
- `domain`, `industry`, `owner_region`

### CRM Contact
- `contact_id`, `account_id`, `name`, `email`, `phone`, `opted_out` (bool)
- An opted_out contact's email is treated as suppressed for new imports.

### Orders / Sponsor Packages
- `order_status`: "confirmed", "proposal_sent", "canceled"
- `ticket_contacts`: array of contact name strings — these are the sponsor attendees

### Invoices
- `status`: "paid_deferred" (fully paid), "open" (has unpaid balance)
- `paid_amount`, `amount`, `deferred_amount` — all integers (USD)
- `payment_date`: null if unpaid

### Badges
- `badge_type`: "sponsor", "attendee", "student", "press", "exhibitor"
- Business types: sponsor, attendee, exhibitor. Non-business: student, press.
- `email`, `phone` — raw format, needs normalization

### Campaign Members
- `status`: "attended_sponsor", "registered_sponsor", "attended"
- `last_activity_date`

### Exhibitors (trade shows)
- `company_id`, `company_name`, `description`, `crm_account_id` (string|null)
- `booth`, `country`, `website`

### Meeting Interest
- `company_name`, `interest_score` (int), `requested_demo` (bool), `notes`

### Import Raw Contacts
- `row_id`, `company_name`, `contact_name`, `email`, `phone`
- `captured_at` (ISO timestamp), `source_name` (controlled enum)
- `source_name` enum: "badge_scan", "sponsor_form", "partner_upload", "webinar_form", "exhibitor_form", "manual_upload"

### Suppression List
- `email`, `phone`, `reason` ("global_opt_out", "privacy_request", "role_account")

---

## Core Business Rules

### 1. Sponsor Status Determination

For each sponsor order for the event:

| Condition | Status |
|---|---|
| Invoice exists AND invoice.status == "paid_deferred" | **paid_deferred** |
| Invoice exists AND invoice.status == "open" | **open_invoice** |
| Order exists (confirmed/proposal_sent) AND no invoice | **proposal_only** |
| Order status == "canceled" | **not_sponsor** (inactive — exclude entirely) |

- `package_amount` = order.amount (integer USD)
- For paid_deferred: `paid_amount` = invoice.paid_amount, `open_balance` = 0
- For open_invoice: `paid_amount` = invoice.paid_amount, `open_balance` = invoice.amount - invoice.paid_amount
- For proposal_only: `paid_amount` = 0, `open_balance` = 0, `invoice_id` = null

### 2. Sponsor Revenue Totals

Sum `package_amount` (order.amount) by status:
- `paid_deferred`: sum of orders with paid_deferred status
- `open_invoice`: sum of orders with open_invoice status
- `proposal_only`: sum of orders with proposal_only status
- `open_invoice_balance`: sum of (invoice.amount - invoice.paid_amount) for open_invoice sponsors

All amounts in **integer USD** (no decimals).

### 3. Qualified Lead Identification (Event Tasks)

A badge scan is a **qualified non-sponsor lead** when ALL of:
- `badge_type` is a business badge (attendee, exhibitor — NOT student, press, sponsor)
- Company is NOT an active sponsor for this event (not in orders with confirmed/proposal_sent status)
- Company is NOT a canceled/inactive sponsor
- CRM account (matched by company_name) is NOT disqualified (status != "disqualified" and disqualified_reason == null)

Each qualified lead gets `opportunity_amount` = event's `lead_opportunity_amount`.

### 4. Exclusion Reasons (Event Tasks)

| Reason | Applies when |
|---|---|
| `sponsor_attendee` | Badge contact is listed in an active sponsor's `ticket_contacts` |
| `existing_disqualified` | CRM account matched by company_name has status="disqualified" or non-null disqualified_reason |
| `inactive_sponsor_record` | Company had a sponsor order for this event with order_status="canceled" |
| `non_business_badge` | badge_type is student, press, or other non-business types |

Excluded records sorted by `company_name` ascending, then `contact_name` ascending.

### 5. Follow-up Due Dates

- `lead_due_date`: event.end_date + event.followup_days_after_end days
- `sponsor_finance_due_date`: event.end_date + event.sponsor_followup_days_after_end days
- Date format: `YYYY-MM-DD`
- `lead_task_count`: number of qualified lead accounts
- `sponsor_finance_task_count`: number of sponsors needing finance follow-up (open_invoice + proposal_only)
- `sponsor_finance_accounts`: list of account names needing sponsor finance follow-up, sorted ascending

### 6. CRM Action Counts (Event Tasks)

Count distinct operations needed:
- `accounts_create`: qualified leads where company has no matching CRM account
- `accounts_update`: qualified leads where company matches an existing CRM account
- `contacts_create`: qualified leads where contact email does NOT match any existing CRM contact
- `contacts_update`: qualified leads where contact email matches an existing CRM contact
- `campaign_members_create`: all qualified leads (each needs a campaign member)
- `campaign_members_update`: existing campaign members whose status needs updating

### 7. Trade-show Exhibitor Qualification

An exhibitor is **qualified** when its `description` indicates the company **builds, manufactures, or OEM-integrates** target platforms (AUV, ROV, Underwater Camera).

An exhibitor is **excluded** when:
- **distributor_only**: reseller/dealer only, does not manufacture
- **service_only**: consulting/services only, no hardware manufacturing
- **sensor_vendor_only / sensor_only**: makes sensors but not platforms
- **research_only**: analytics/software only, no platform hardware
- **not_target_market**: doesn't fit any qualifying category

**Platform derivation**: Read the exhibitor `description` text to determine which platforms they build:
- **AUV**: autonomous underwater vehicles, AUV scouts, autonomous subs
- **ROV**: remotely operated vehicles, inspection ROVs, pen-cleaning ROVs
- **Underwater Camera**: camera modules, underwater cameras, camera arrays, imaging systems

Platform arrays sorted in enum order: `["AUV", "ROV", "Underwater Camera"]`.

### 8. Trade-show Priority Tiers

For tasks that require priority tier assignment:

| Tier | Criteria | Opportunity (USD) |
|---|---|---|
| A | requested_demo=true AND interest_score ≥ 90 | 120000 |
| B | requested_demo=true AND interest_score ≥ 80 | 90000 |
| C | All other qualified leads | 50000 |

Only qualified exhibitors with meeting_interest records get tiers.

### 9. Lead Ranking (train_005)

Sort qualified leads by these criteria in order:
1. `requested_demo` = true first
2. `interest_score` descending
3. Number of platforms covered (broader coverage first)
4. `company_name` ascending (alphabetical)

Assign 1-based contiguous `rank` after sorting.

### 10. CRM Overlap (Trade-show Tasks)

- If exhibitor `crm_account_id` is non-null → account exists in CRM → `crm_action`: "update_existing"
- If exhibitor `crm_account_id` is null → no CRM account → `crm_action`: "create_account"
- For excluded exhibitors: `crm_action`: "no_import"

### 11. Batch Import Processing Pipeline

**Step 1: Deduplicate by normalized email**
- Normalize email: trim whitespace, lowercase
- Group raw contacts by normalized email
- For each group with >1 row, determine winner:
  1. Row whose normalized email matches an existing CRM contact email (lowercase) wins
  2. Otherwise, earliest `captured_at` wins
  3. Tiebreak: lowest `row_id` (lexicographic string comparison)
- Remove non-winner duplicates; record in `duplicate_summary`

**Step 2: Remove unusable rows**
- `missing_contact`: normalized email is empty/whitespace-only AND normalized phone is empty/whitespace-only
- These go to `removal_summary` with reason "missing_contact"

**Step 3: Apply suppression**
- Match each surviving row against the suppression list:
  - Row's normalized email matches suppression email (case-insensitive) → suppressed
  - Row's normalized phone (digits only) matches suppression phone → suppressed
  - CRM contact with matching email has `opted_out: true` → suppressed
- Suppressed rows go to `removal_summary` with reason "suppressed"

**Step 4: Determine CRM actions for clean contacts**
- Match company to CRM account by `company_name` (case-insensitive exact match, or substring match of company names):
  - Match found → `crm_action`: "update_existing", set `existing_account_id`
  - No match → `crm_action`: "create_account", `existing_account_id`: null
- Match contact to CRM contact by normalized email:
  - Match found → set `existing_contact_id`
  - No match → `existing_contact_id`: null

### 12. Contact Normalization

- **Email**: trim leading/trailing whitespace, convert to lowercase. Empty string `""` if none.
- **Phone**: strip ALL non-digit characters (spaces, parens, dashes, dots, plus signs). Empty string `""` if none.
- Normalize BEFORE dedup and CRM matching.

### 13. Badge-level Processing (train_004)

For each badge, classify and determine CRM action:

**Classification:**
- `sponsor_attendee`: badge_type="sponsor" OR contact in active sponsor ticket_contacts
- `qualified_non_sponsor_lead`: business badge, non-sponsor, not disqualified
- `excluded`: non-business badge, disqualified account, or missing contact

**CRM action per badge:**
- Match badge company to CRM account, badge contact to CRM contact, then check campaign members
- `create_account_contact_campaign_member`: new account + new contact
- `create_contact_campaign_member`: existing account + new contact
- `add_campaign_member`: existing account and contact, no campaign member yet
- `update_campaign_member`: existing campaign member whose status needs changing
- `no_action`: existing campaign member already in correct state
- `no_import`: excluded badges

### 14. Campaign Member Status Mapping

- Sponsor attendees → target_status: "attended_sponsor" (if they attended) or "registered_sponsor"
- Non-sponsor attendees → target_status: "attended"
- Excluded → target_status: "excluded"

Existing campaign members whose `status` already matches the `target_status` → action: "no_action".

---

## Sorting Rules Summary

| Output list | Sort key(s) |
|---|---|
| sponsor_statuses | account_name ascending |
| qualified_lead_accounts | account_name ascending |
| excluded_records | company_name ascending, then contact_name ascending |
| qualified_exhibitors (train_002) | company_name ascending |
| excluded_near_misses | company_name ascending |
| ranked_leads (train_005) | rank ascending (1-based) |
| excluded_exhibitors (train_005) | company_name ascending |
| clean_contacts (train_003) | clean_contact_id ascending |
| duplicate_keys | key (normalized email) ascending |
| removed_rows | row_id ascending |
| badge_decisions (train_004) | badge_id ascending |
| campaign_member_actions | subject_key ascending |
| badge_only_contacts | company_name ascending |
| platforms array | enum order: AUV, ROV, Underwater Camera |
| sponsor_finance_accounts | account_name ascending |

---

## Common Pitfalls

1. **Phone normalization**: Strip ALL non-digit characters including `+`, `(`, `)`, `-`, `.`, and spaces. Leading country code digits are kept.
2. **Email normalization**: Only trim + lowercase. Do NOT remove dots or plus-address parts.
3. **Sponsor status from invoices, not orders**: Always check invoices for paid_deferred vs open_invoice. Use proposal_only only when NO invoice exists.
4. **Canceled orders = not a sponsor**: Exclude canceled orders from sponsor_statuses and revenue totals entirely. They are not "proposal_only".
5. **Disqualified accounts**: Check `disqualified_reason != null`, not just `status == "disqualified"`. An account can have a non-null disqualified_reason even if status says otherwise (defense in depth).
6. **Sponsor attendee exclusion**: Match badge contacts against `ticket_contacts` array in orders/sponsor_packages. Only active (non-canceled) sponsors count.
7. **Dedup winner selection**: CRM match first, then earliest captured_at, then lowest row_id. Check CRM contact match by normalized email before falling back to timestamp.
8. **Integer USD**: All monetary values are integers. Don't include decimal points.
9. **Boolean fields**: Use JSON `true`/`false`, not strings.
10. **null vs ""**: `invoice_id` and `existing_*_id` fields use `null` when absent. `email`/`phone` use `""` when empty.
11. **Platform derivation from descriptions**: Read the exhibitor description text to infer platforms. "Builds AUVs" → AUV, "camera modules/manufacturer" → Underwater Camera, "ROVs" → ROV. A company can have multiple platforms.
12. **Ranking tiebreakers**: When scores are equal, broader platform coverage wins. When coverage is equal, company_name ascending wins.
13. **Campaign member existing status check**: Don't create when an existing campaign member already has the correct target_status — that's a no_action.
14. **Suppression matching**: Check BOTH the /suppression endpoint AND CRM contacts with opted_out=true. The suppression list may duplicate opted-out CRM contacts — deduplicate removal reasons.
