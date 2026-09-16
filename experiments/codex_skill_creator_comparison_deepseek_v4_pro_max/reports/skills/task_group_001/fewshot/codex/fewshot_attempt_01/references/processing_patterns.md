# HarborCRM Processing Patterns

Reusable rules for reconciling HarborCRM API data into output JSON.

## Contact normalization

### Email

- Trim whitespace.
- Lowercase.
- If the result is empty or whitespace-only, use `""`.

### Phone

1. Strip all non-digit characters: spaces, parens, dashes, dots, plus signs, leading `1` if it appears after stripping non-digits and the remaining string is 11 digits starting with `1`.
2. Specifically: strip any chars that are not `0-9`. Then, if the resulting string is exactly 11 digits and starts with `1`, drop the leading `1` to get a 10-digit number.
3. If the resulting string is empty, use `""` (never null).

### Normalization script

Use `scripts/normalize_contact.py` for deterministic normalization or inline the rules above.

## Sponsor status classification

From orders and invoices for the event:

1. Group orders by `account_id`. An order exists if `order_status` is not `canceled`.
2. For each order, look up invoices by `account_id` + `event_id`.
3. For each non-canceled order:
   - If a matching invoice exists with `status == "paid_deferred"` → status is `paid_deferred`. Use invoice `paid_amount`, `amount`, `open_balance = amount - paid_amount`, and `invoice_id`.
   - If a matching invoice exists with `status == "open"` → status is `open_invoice`. Use invoice `paid_amount`, `amount`. `open_balance = amount - paid_amount`.
   - If no matching invoice exists (or order is `proposal_sent` without an invoice) → status is `proposal_only`. `package_amount` is the order `amount`. `paid_amount = 0`, `open_balance = 0`, `invoice_id = null`.
4. Exclude canceled orders entirely.

When the template uses the broader `sponsor_status` field with `not_sponsor`: treat `proposal_sent` orders without any invoice as `proposal_only`, and confirmed orders with invoices as above. `not_sponsor` is used only when an entity is never a sponsor for the event.

## CRM action determination

### For import batches

For each surviving clean contact:

- If the company matches an existing CRM account by name match or domain:
  - If the contact email appears in CRM contacts for that account → `crm_action = "update_existing"`, populate both `existing_account_id` and (if matched) `existing_contact_id`.
  - If the contact email does not appear in CRM contacts for that account → `crm_action = "update_existing"`, populate `existing_account_id`, `existing_contact_id = null`.
- If the company does not match any CRM account → `crm_action = "create_account"`, `existing_account_id = null`, `existing_contact_id = null`.

Accounts with `disqualified_reason` that is not null have `status = "disqualified"`. Contacts from disqualified accounts whose email appears in CRM are suppressed (`no_import` / `suppress`). Contacts from disqualified accounts NOT in CRM should be handled as `no_import` (not imported).

For the `import_action_totals`: `create_account` counts clean contacts with `crm_action = "create_account"`. `update_existing` counts clean contacts with `crm_action = "update_existing"`. `no_import` counts contacts not imported (disqualified). `suppress` counts suppressed contacts. `campaign_member_import_count` is the number of clean contacts that should be imported (all `create_account` + `update_existing`).

### For event handoffs (extended actions)

- **Sponsor attendees** (badge with company matching a sponsor order): Extended CRM action depends on whether the sponsor is already in campaign members. Sponsor attendees with existing campaign-member records get `no_action`. Sponsor attendees with badge-only presence (no existing campaign member) get `create_contact_campaign_member`.
- **Qualified non-sponsor leads**: Company already in CRM with existing account → `update_existing` for account, `create_contact` for contact, `add_campaign_member`. Company not in CRM → `create_account` for account, `create_contact` for contact, `add_campaign_member`. In badge-level decisions: `create_account_contact_campaign_member` when company is new, `create_contact_campaign_member` when company exists but contact does not, `add_campaign_member` when both exist.
- **Non-business badges** (student, press): `no_import`. Exclusion reason: `non_business_badge`.
- **Existing disqualified accounts**: If a badge's company matches a CRM account with non-null `disqualified_reason`: `no_import`. Reason: `existing_disqualified`.
- **Missing contact name**: If `contact_name` is empty → `no_import`. Reason: `missing_contact`.

### For campaign member actions

Compare badge data against existing campaign members for the event:

- If an existing campaign member record exists for the same `account_id` + `contact_id` → `action`: `no_action` if status is already correct, or `update` if a status transition is needed.
- If no existing campaign member exists → `action`: `create`.
- `target_status` is determined by the contact's classification: sponsor attendees → `attended_sponsor`, registered sponsors → `registered_sponsor`, qualified non-sponsor attendees → `attended`, excluded → `excluded`.
- Use `subject_key` format: `{account_id}:{contact_id}` for CRM-linked records, `badge:{badge_id}` for badge-only records.

## Duplicate resolution

For import batches, deduplication is by normalized email.

1. Normalize all emails in raw contacts.
2. Group by `email:{normalized_email}`.
3. For each group with more than one row, select the winner:
   - Prefer rows with a non-empty phone.
   - If still tied, prefer `partner_upload` over `webinar_form` over `manual_upload` over other sources.
   - If still tied, prefer the most recent `captured_at` timestamp.
   - If still tied, prefer the lower `row_id` (lexicographically).
4. All non-winner rows are removed with reason `duplicate`. The `duplicate_key` is `email:{normalized_email}`.
5. The winner's `row_id` is used as the `clean_contact_id`.

### Winner row fields used for the clean contact

The `source_row_id` is the winner's `row_id`. The `company_name`, `contact_name`, `email`, and `phone` come from the winner row. The `source_name` and `captured_at` come from the winner row.

## Suppression checking

For import batches:

1. Normalize each surviving contact's email and phone.
2. Check the normalized email against every entry in the suppression list. If a match is found (by email), remove the row with reason `suppressed`.
3. Also check: if a CRM contact with the same email has `opted_out = true`, suppress.
4. Suppression takes priority over duplicate removal: apply duplicate removal first, then suppression on the surviving rows.

## Exclusion logic

### Event badge exclusions

For each badge, determine exclusion:

1. **sponsor_attendee**: The badge's company matches a non-canceled sponsor order's `account_name` (or the badge's email matches a contact from a sponsor account). Sponsor attendees are excluded from the qualified lead list but are still noted.
2. **existing_disqualified**: The badge's company matches a CRM account where `disqualified_reason` is not null.
3. **non_business_badge**: `badge_type` is `student` or `press`.
4. **inactive_sponsor_record**: An order with `order_status == "canceled"` — exclude from sponsor status reporting.

### Trade-show exhibitor exclusions

Qualify exhibitors based on their `description` and the campaign policy:

- **distributor_only**: Exhibitor description indicates distribution/reselling without manufacturing.
- **service_only**: Exhibitor provides services/consulting, not platform building.
- **sensor_vendor_only** / **sensor_only**: Exhibitor builds sensors/probes only, not the platforms that carry them.
- **research_only**: Exhibitor is a research institution.
- **not_target_market**: Exhibitor does not operate in the target market.

For platform classification, read the exhibitor `description` to determine which of `AUV`, `ROV`, or `Underwater Camera` platforms they build/OEM. An exhibitor can cover multiple platforms.

## Follow-up due dates

- **Lead follow-up**: `event.end_date + followup_days_after_end` days. Format as YYYY-MM-DD.
- **Sponsor finance follow-up**: `event.end_date + sponsor_followup_days_after_end` days. Format as YYYY-MM-DD.

## Priority tier assignment (prospecting)

Unless the prompt specifies different rules (some prompt tasks define their own tier logic):

- **A**: `requested_demo == true` AND `interest_score >= 90`.
- **B**: `requested_demo == true` AND `interest_score >= 80` (but not A).
- **C**: All other qualified leads.

For opportunity sizing, use the amounts specified in the task prompt. If not specified, use the event's `lead_opportunity_amount` for event-based tasks.

## Sorting conventions

- **Sponsor statuses**: Sort by `account_name` ascending (case-sensitive, ASCII order).
- **Qualified leads**: Sort by `account_name` / `company_name` ascending.
- **Exclusions**: Sort by `company_name` ascending, then `contact_name` ascending.
- **Badge decisions**: Sort by `badge_id` ascending.
- **Campaign member actions**: Sort by `subject_key` ascending.
- **Clean contacts**: Sort by `clean_contact_id` ascending.
- **Duplicate keys**: Sort by `key` ascending.
- **Removed rows**: Sort by `row_id` ascending.
- **Ranked leads**: Sort by rank ascending (1-based contiguous).
- **Platform lists**: Always sort in enum order: `["AUV", "ROV", "Underwater Camera"]`.

## CRM action counting

For event handoffs:

- `accounts_create`: Count of non-sponsor leads with `crm_account_action == "create_account"`.
- `accounts_update`: Count with `crm_account_action == "update_existing"`.
- `contacts_create`: Count of contacts being created (all qualified leads get new contacts; also sponsor attendees not yet in CRM).
- `contacts_update`: Count of contacts being updated.
- `campaign_members_create`: Count of new campaign member records being created.
- `campaign_members_update`: Count of existing campaign member records being updated.

## Sponsor revenue totals

- `paid_deferred`: Sum of `paid_amount` (or `package_amount` for `paid_deferred` status) for all sponsors with `paid_deferred` status.
- `open_invoice`: Sum of `package_amount` for sponsors with `open_invoice` status.
- `proposal_only`: Sum of `package_amount` for sponsors with `proposal_only` status.
- `open_invoice_balance`: Sum of `open_balance` across all `open_invoice` sponsors.

For simplified sponsor reporting where only `amount_usd` is needed: use `paid_amount` for `paid_deferred`, the invoice `amount` for `open_invoice`, and the order `amount` for `proposal_only`.

## Badge-only contacts

When reporting contacts that only appear in badge scans (no CRM contact record), normalize email and phone and include them. Sort by `company_name` ascending.
