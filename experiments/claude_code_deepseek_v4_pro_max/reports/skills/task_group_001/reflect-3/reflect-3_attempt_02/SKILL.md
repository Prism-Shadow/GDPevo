# HarborCRM Task Group Skill

## Environment

The shared HarborCRM API is at `${GDPEVO_ENV_BASE_URL}`. All data is read-only via GET endpoints. No write operations are needed or available.

## Core API Endpoints

Events, tradeshows, and import batches share a common pattern:
- `GET /api/events/{event_id}` — event metadata (dates, follow-up windows, lead opportunity amount, campaign code)
- `GET /api/events/{event_id}/orders` — sponsor orders (account, amount, order_status, ticket_contacts, voucher_code)
- `GET /api/events/{event_id}/badges` — badge scans (badge_type, company_name, contact_name, email, phone)
- `GET /api/events/{event_id}/sponsor_packages` — synonym for /orders
- `GET /api/finance/invoices?event_id={event_id}` — invoices (status, paid_amount, deferred_amount)
- `GET /api/tradeshows` — list of all trade shows
- `GET /api/tradeshows/{show_id}/exhibitors` — exhibitors with descriptions, CRM account links
- `GET /api/tradeshows/{show_id}/meeting_interest` — interest scores and demo requests
- `GET /api/import_batches` — batch metadata (campaign_code)
- `GET /api/import_batches/{batch_id}/raw_contacts` — rows to clean
- `GET /api/import_batches/{batch_id}/suppression` — suppression list (email/phone/reason)
- `GET /api/crm/accounts` — CRM accounts (disqualified_reason, domain, status, industry)
- `GET /api/crm/contacts` — CRM contacts (opted_out, email, phone)
- `GET /api/crm/opportunities` — all opportunities across events
- `GET /api/crm/campaign_members?event_id={event_id}` — existing campaign member records
- `GET /api/policies` — policy enums and notes (sponsor_handoff status_enums, prospecting platform_enums)

## Data Normalization

**Email:** lowercase, trim whitespace. Empty or whitespace-only → `""`.

**Phone:** strip all non-digit characters. Keep the result as-is — do NOT add a country-code prefix if the source lacks one. If the source has no phone, use `""`.

## Sponsor Status Determination

For each sponsor order from `/events/{id}/orders`:

| Order Status    | Invoice Status  | Sponsor Status   |
|-----------------|-----------------|------------------|
| confirmed       | paid_deferred   | paid_deferred    |
| confirmed       | open            | open_invoice     |
| proposal_sent   | (no invoice)     | proposal_only    |
| canceled        | —               | exclude entirely |

- **paid_deferred:** package_amount = invoice amount, paid_amount = invoice paid_amount, open_balance = 0
- **open_invoice:** package_amount = invoice amount, paid_amount = invoice paid_amount, open_balance = amount − paid_amount
- **proposal_only:** package_amount = order amount, invoice_id = null, paid_amount = 0, open_balance = 0

**Sponsor revenue totals:**
- `paid_deferred` = sum of package_amount for paid_deferred sponsors
- `open_invoice` = sum of package_amount for open_invoice sponsors
- `proposal_only` = sum of package_amount for proposal_only sponsors
- `open_invoice_balance` = sum of open_balance for open_invoice sponsors (i.e., total unpaid)

**Sponsor finance follow-up:** all sponsors with open_invoice or proposal_only need follow-up. The due date is `end_date + sponsor_followup_days_after_end`. List the account names sorted ascending.

## Badge Classification & Lead Qualification

For each badge from `/events/{id}/badges`, classify in priority order:

1. **sponsor_attendee** — badge_type is "sponsor", OR the badge's company has an active sponsor order (confirmed or proposal_sent). Excluded from lead pipeline.
2. **inactive_sponsor_record** — the badge's company has a canceled sponsor order. Excluded.
3. **non_business_badge** — badge_type is "student" or "press". Excluded.
4. **existing_disqualified** — the badge's company matches a CRM account with a non-null `disqualified_reason`. Excluded.
5. **qualified_non_sponsor_lead** — everything else. Include in lead pipeline.

For each qualified lead:
- `opportunity_amount` = event's `lead_opportunity_amount` (per-lead)
- `crm_account_action` = `update_existing` if a non-disqualified CRM account exists for the company; `create_account` otherwise
- `crm_contact_action` = `create_contact` unless the contact's normalized email matches an existing CRM contact
- `campaign_member_action` = `add_campaign_member`
- `lead_pipeline_total` = sum of opportunity_amount across all qualified leads

**Lead follow-up due date:** `end_date + followup_days_after_end`.

## Campaign Member Actions

Reconcile badge scans against existing campaign members:
- Qualified leads with badge scans → `create` campaign member, target_status `attended`
- Sponsor attendees with badge scans → `create` campaign member, target_status `attended_sponsor` (unless one already exists at that status → `no_action`)
- Existing campaign members with no badge scan → `no_action` (keep current status)
- Excluded badge holders → campaign member action `no_import`, target_status `excluded`
- Sort campaign member actions by `subject_key` ascending. Use `"{account_name}|{contact_name}"` format.

## Badge-Only Contacts

For each qualified non-sponsor lead that exists only as a badge scan (no CRM contact), include in `badge_only_contacts` with normalized email and phone. Sort by `company_name` ascending.

## Prospecting / Exhibitor Qualification

For trade-show prospecting tasks:

**Qualification rule:** An exhibitor is qualified if its description indicates it **builds or OEM-manufactures** AUV, ROV, or Underwater Camera platforms. Companies that only distribute, resell, provide services, or make sensors without building platforms are excluded.

**Exclusion reasons** (use the most specific match):
- `distributor_only` — reseller, distributor, dealer
- `service_only` — consulting, services, analytics without hardware manufacturing
- `sensor_vendor_only` — builds sensors/probes but not platforms
- `research_only` — research/lab use only, no commercial platform manufacturing
- `not_target_market` — catch-all for non-matching

**Platform classification:** Derive from the exhibitor description. A platform is counted if the company builds it. Sort platforms in enum order: `"AUV"`, `"ROV"`, `"Underwater Camera"`.

**Priority tier assignment** (unless task specifies otherwise):
- `A` — requested demo AND interest_score ≥ 90
- `B` — requested demo AND interest_score ≥ 80
- `C` — all other qualified leads

**Tier opportunity amounts:** A = $120,000, B = $90,000, C = $50,000 (when amounts not specified in the task).

**Ranking:** demo request first (true before false), then interest_score descending, then platform count descending (broader coverage first), then company_name ascending.

**CRM overlap:** existing_crm_overlap_count = count of qualified leads whose `crm_account_id` is non-null. List matching account IDs sorted ascending.

## Batch Import Cleaning

For import batch tasks:

**Deduplication:** Match raw contacts by normalized email. For each duplicate group, the **winner** is the row with the latest `captured_at` timestamp. When timestamps are tied, the row with the alphabetically-lower `row_id` wins.

**Suppression:** Any raw contact whose normalized email or phone matches an entry in the suppression list is suppressed (removed from import). Check both email AND phone against the suppression list.

**Missing contact:** A row with empty email AND empty phone after normalization is unusable — removed as `missing_contact`.

**Clean contacts** include only the importable surviving rows (winners after dedup, not suppressed, not missing contact). Each gets:
- `crm_action` = `update_existing` if company has a non-disqualified CRM account, `create_account` otherwise
- `existing_account_id` = CRM account_id if exists, else null
- `existing_contact_id` = CRM contact_id if matching contact exists, else null
- Use the winning row's values for all data fields (company_name, captured_at, source_name, etc.)

**Removal summary:** `removed_rows` includes ALL removed rows (duplicates, suppressed, missing_contact) sorted by `row_id` ascending. Count duplicates separately in `duplicate_summary.duplicate_removed_count`. Count suppressed in `suppressed_removed_count`. Count missing-contact in `unusable_removed_count`.

**Import action totals:** Count only the crm_action values across clean contacts (`create_account`, `update_existing`). Do not count `no_import` or `suppress` unless those rows appear in clean_contacts.

**Campaign member import count:** Number of clean contacts (equals `create_account` + `update_existing` counts).

## Exclusion Counts

When a task requires per-reason exclusion counts:
- `sponsor_attendee` — badge holders from active sponsor companies
- `non_business_badge` — student or press badge types
- `existing_disqualified` — badge holders from CRM-disqualified accounts (only when no higher-priority reason applies)
- `missing_contact` — rows with no email AND no phone

## Sorting Rules (by output section)

- `sponsor_statuses` — by `account_name` ascending
- `qualified_lead_accounts` — by `account_name` ascending
- `excluded_records` — by `company_name` ascending, then `contact_name` ascending
- `badge_decisions` — by `badge_id` ascending
- `campaign_member_actions` — by `subject_key` ascending
- `badge_only_contacts` — by `company_name` ascending
- `qualified_exhibitors` / `ranked_leads` — by rank (if present) or `company_name` ascending
- `excluded_near_misses` / `excluded_exhibitors` — by `company_name` ascending
- `clean_contacts` — by `clean_contact_id` ascending
- `duplicate_keys` — by `key` ascending
- `removed_rows` — by `row_id` ascending
- Account name/id lists — ascending order
- Platforms within a list — in enum order: `["AUV", "ROV", "Underwater Camera"]`

## Key Pitfalls

1. **Phone normalization:** strip non-digits only; do not add a `1` prefix for US numbers unless the source data already includes it.
2. **Canceled sponsors:** use `inactive_sponsor_record` as the exclusion reason, not `existing_disqualified`, even if the CRM account is also disqualified.
3. **Sponsor attendees with attendee badges:** a badge with badge_type "attendee" from a company that has an active sponsor order is still a `sponsor_attendee` exclusion.
4. **Press badges:** treat as `non_business_badge`, same as student.
5. **Email normalization:** lowercase AND trim. A field that is only whitespace normalizes to `""`.
6. **Tied dedup timestamps:** when `captured_at` matches, the alphabetically-lower `row_id` wins.
7. **Clean contacts vs removed rows:** do NOT include suppressed or no_import rows in `clean_contacts`. Only importable rows (create_account, update_existing) belong there.
8. **Platform derivation:** read exhibitor descriptions carefully — "builds ROVs with camera arrays" means ROVs (cameras are integrated, not standalone). "OEM underwater camera manufacturer" means Underwater Camera.
9. **Sponsor revenue totals:** `open_invoice` is the TOTAL invoice amount, not the unpaid portion. The unpaid portion goes in `open_invoice_balance`.
10. **Date arithmetic:** follow-up due dates are `end_date + followup_days_after_end`. Use ISO 8601 date format (YYYY-MM-DD).
