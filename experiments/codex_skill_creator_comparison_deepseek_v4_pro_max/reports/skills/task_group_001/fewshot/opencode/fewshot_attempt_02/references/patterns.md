# HarborCRM Processing Patterns

This document captures the classification rules, join strategies, and aggregation patterns that recur across HarborCRM handoff tasks. Use it alongside the API reference to handle the cross-referencing step.

## Pattern A: Event Handoff (post-event CRM reconciliation)

Used when the task involves an event, badges, sponsor orders, invoices, CRM accounts/contacts/opportunities, and campaign members.

### A.1 Sponsor status classification

For each sponsor order found in `/api/events/{event_id}/orders`:

1. Look up the order's `invoice_id` in the invoices response.
2. Classify the sponsor account status using these controlled values:
   - `paid_deferred`: invoice exists AND `paid_amount >= total_amount` (fully paid or overpaid). Report `paid_amount` as the full invoice total, `open_balance = 0`.
   - `open_invoice`: invoice exists AND `paid_amount < total_amount`. Report `paid_amount` as what was paid, `open_balance = total_amount - paid_amount`.
   - `proposal_only`: no invoice exists for this order (`invoice_id` is null or not found). Report `paid_amount = 0`, `open_balance = 0`.
3. Use the order's `package_amount` for the `package_amount` field.
4. For `not_sponsor` (used in some templates): the account has no sponsor order at all.

### A.2 Sponsor revenue totals

Aggregate across sponsor statuses:
- `paid_deferred`: sum of `package_amount` for all `paid_deferred` sponsors
- `open_invoice`: sum of `package_amount` for all `open_invoice` sponsors
- `proposal_only`: sum of `package_amount` for all `proposal_only` sponsors
- `open_invoice_balance`: sum of `open_balance` across all `open_invoice` sponsors

All totals are integers in USD.

### A.3 Lead qualification from badges

For each badge in `/api/events/{event_id}/badges`:

1. **Sponsor attendee**: If the badge's `company_name` matches a sponsor account by name, classify as `sponsor_attendee`. These go to `excluded_records` with reason `sponsor_attendee` and receive `crm_action: "no_action"`. They are NOT included in qualified leads.

2. **Non-business badge**: If the badge's `badge_type` indicates press, student, or other non-business role, classify as `non_business_badge`. Exclude with reason `non_business_badge`.

3. **Existing disqualified**: If the badge's company matches a CRM account whose `status = "disqualified"`, exclude with reason `existing_disqualified`.

4. **Qualified non-sponsor lead**: All remaining badges. Look up the CRM account for this company. Determine CRM actions:
   - If an active CRM account already exists: `crm_account_action = "update_existing"`, `crm_contact_action` depends on whether the contact already exists in CRM for that account.
   - If no CRM account: `crm_account_action = "create_account"`, `crm_contact_action = "create_contact"`.
   - `campaign_member_action = "add_campaign_member"` for all qualified leads.
   - Use the event's lead opportunity amount for `opportunity_amount` (typically from `/api/crm/opportunities?event_id={event_id}`, use the recurring amount for non-sponsor leads).

### A.4 Follow-up dates

Compute follow-up due dates from policy rules or event dates:
- `lead_due_date` and `sponsor_finance_due_date` are typically derived by adding policy-defined offsets to the event date.
- `lead_task_count` = number of qualified lead accounts.
- `sponsor_finance_task_count` = number of sponsor accounts with open invoices or proposal-only status (unpaid sponsors).
- `sponsor_finance_accounts` = list of account names for those unpaid sponsors, sorted ascending.

### A.5 CRM action counts

Count each action type across all qualified leads:
- `accounts_create`: number of qualified leads with `crm_account_action = "create_account"`
- `accounts_update`: number with `crm_account_action = "update_existing"`
- `contacts_create`: number with `crm_contact_action = "create_contact"`
- `contacts_update`: number with `crm_contact_action = "update_existing"`
- `campaign_members_create`: number with `campaign_member_action = "add_campaign_member"`
- `campaign_members_update`: number with update action

### A.6 Normalized contact facts

For every badge (including sponsor badges that appear in badge-only contact lists):
- `normalized_email`: email string, lowercased and trimmed. Empty string `""` if no email is supplied.
- `normalized_phone`: digits only, all other characters stripped. Empty string `""` if no phone is supplied.

## Pattern B: Trade-show Prospecting (lead qualification from exhibitors)

Used when the task involves a trade-show, exhibitors, meeting interest, and CRM accounts.

### B.1 Qualification decision

For each exhibitor in `/api/tradeshows/{show_id}/exhibitors`:

1. Read the exhibitor's `relationship_type` and `platforms` arrays.
2. Consult `/api/policies` for the platform-to-qualification mapping. The policy defines which `relationship_type` values qualify and which are excluded.
3. **Qualified**: The exhibitor's platforms include at least one platform covered by the campaign policy AND the relationship type is one that the policy considers a target (typically OEM/integrator/builder, not distributor/service/sensor-vendor/research).
4. **Excluded**: Record in `excluded_near_misses` or `excluded_exhibitors` with the appropriate exclusion reason:
   - `distributor_only` / `distributor`: relationship is distributor
   - `service_only` / `service_provider`: relationship is service provider
   - `sensor_vendor_only` / `sensor_only` / `sensor_vendor`: relationship is sensor vendor
   - `research_only` / `research`: relationship is research institution
   - `not_target_market`: platforms don't match the campaign

### B.2 Platform enumeration

Platforms are always drawn from the controlled set `["AUV", "ROV", "Underwater Camera"]`. An exhibitor's platforms are the intersection of their declared platforms with this enum. List them in enum order: AUV first, then ROV, then Underwater Camera.

### B.3 Priority tier assignment

Tiers are `A`, `B`, `C`. The assignment logic varies by task but follows the policy:
- **Demo-driven ranking** (train_005 pattern): `A` for demo-requested leads with interest score ≥ 90, `B` for demo-requested leads with interest score ≥ 80, `C` for all other qualified leads.
- **Platform-driven** (train_002 pattern): Tiers may be assigned from policy rules about platform breadth or specific platform coverage.
- Always check `/api/policies` for the tier-assignment rules specific to the campaign.

### B.4 Opportunity sizing

Opportunity amounts are integers in USD, assigned by tier or by campaign policy:
- When tier-based: `A` = 120000, `B` = 90000, `C` = 50000 (or whatever the policy states).
- When event-based: use the event's lead opportunity amount.

### B.5 Ranking qualified leads

When the template requires ranked output:

1. Demo-requested leads first (`requested_demo = true`)
2. Within demo-requested, sort by `interest_score` descending
3. Within same demo/score group, more platforms first (broader coverage)
4. Within same platform count, `company_name` ascending
5. Non-demo-requested leads follow, sorted by score descending, then platforms, then name
6. Assign contiguous 1-based ranks

### B.6 CRM overlap

For each qualified exhibitor, check whether a CRM account already exists (match by `company_id` or `company_name`):
- If a matching CRM account exists: `crm_action = "update_existing"`, include the `crm_account_id`
- If no match: `crm_action = "create_account"`, `crm_account_id = null`
- Excluded exhibitors always get `crm_action = "no_import"`

### B.7 Aggregate counts

Compute:
- `qualified_total`: number of qualified exhibitors
- `platform_counts`: count of qualified exhibitors per platform (one exhibitor may contribute to multiple platform counts)
- `priority_counts`: count of qualified exhibitors per tier
- `excluded_near_misses_total`: number of excluded exhibitors
- `existing_crm_overlap_count`: number of qualified leads with `crm_action = "update_existing"`
- `existing_crm_overlap_account_ids`: list of those CRM account IDs, sorted ascending
- `total_estimated_opportunity_usd`: sum of opportunity estimates across all ranked leads

## Pattern C: Import-batch Cleaning

Used when the task involves raw contacts, deduplication, suppression, and CRM matching.

### C.1 Deduplication

1. Group raw contacts from `/api/import_batches/{batch_id}/raw_contacts` by normalized email (lowercase, trimmed).
2. Within each duplicate group, select the winner: the row with the most complete record (has both contact_name and company_name, then most non-empty fields). If still tied, pick the earliest `captured_at` timestamp.
3. For each duplicate group, record the winner's `row_id` and list all other `row_id` values as removed.
4. The winner becomes the `clean_contact_id` and `source_row_id`.

### C.2 Suppression

1. Read the suppression list from `/api/import_batches/{batch_id}/suppression`.
2. Any raw contact whose email matches a suppression key is removed with reason `"suppressed"`.

### C.3 Missing-contact removal

Any raw contact that lacks both `contact_name` and `company_name` (or has empty strings for both) is removed with reason `"missing_contact"`.

### C.4 CRM matching

For each surviving cleaned contact:

1. Check CRM accounts for a matching `company_name` (case-insensitive comparison is common; use exact match unless policy says otherwise).
2. If a match is found: `crm_action = "update_existing"`, set `existing_account_id` to the matched account ID. Check whether a contact with the same name/email already exists; if so, set `existing_contact_id`.
3. If no account match: `crm_action = "create_account"`, `existing_account_id = null`, `existing_contact_id = null`.
4. If the contact is suppressed: `crm_action = "suppress"`.

### C.5 Normalization

- `email`: lowercase, trimmed. Empty string `""` if none.
- `phone`: digits only. Empty string `""` if none.

### C.6 Source names

The `source_name` field takes one of these controlled values: `badge_scan`, `sponsor_form`, `partner_upload`, `webinar_form`, `exhibitor_form`, `manual_upload`. Use the value from the winning raw-contact row.

### C.7 Action totals

Count `crm_action` values across all clean contacts (including no_import and suppress entries):
- `create_account`: count of `crm_action = "create_account"`
- `update_existing`: count of `crm_action = "update_existing"`
- `no_import`: count of removed rows (duplicates + missing-contact)
- `suppress`: count of suppressed rows

### C.8 Campaign-member import count

The number of cleaned contacts that should be imported as campaign members: all surviving clean contacts minus any that are suppressed. In other words, count of `clean_contacts` entries whose `crm_action` is `"create_account"` or `"update_existing"`.

## Pattern D: Event Reconciliation (comprehensive)

Used when the task requires reconciling badges, sponsor orders, finance, and campaign members into a single handoff (train_004 pattern). This combines elements of Pattern A with additional campaign-member detail.

### D.1 Campaign-member actions

For each campaign member associated with the event (from `/api/crm/campaign_members?event_id={event_id}`), plus badge-only leads not yet in campaign members:

1. **Existing sponsor member, attended**: If the campaign member's account is a sponsor and status is `"attended"`, action = `"no_action"`, target_status = `"attended_sponsor"`.
2. **Existing sponsor member, registered only**: If the sponsor registered but did not attend, action = `"no_action"`, target_status = `"registered_sponsor"`.
3. **New badge-only lead**: If a badge contact does not match any existing campaign member, action = `"create"`, target_status = `"attended"` (for non-sponsor qualified leads) or `"attended_sponsor"` (for sponsor attendees who need a campaign-member record).
4. **Existing non-sponsor campaign member**: If already in campaign members and attended, decide between `"update"` or `"no_action"` based on whether the status already matches.
5. **Excluded badges**: action = `"no_import"`.

### D.2 CRM actions per badge

For each badge, the `crm_action` field uses these controlled values:
- `"create_account_contact_campaign_member"`: brand-new qualified non-sponsor lead with no CRM presence
- `"create_contact_campaign_member"`: existing CRM account, new contact
- `"add_campaign_member"`: existing CRM account and contact, just add the campaign-member record
- `"update_campaign_member"`: update an existing campaign-member record
- `"no_action"`: sponsor attendee with existing records, no work needed
- `"no_import"`: excluded badge (non-business, disqualified, missing contact)

### D.3 Exclusion counts

Count exclusion reasons across all badges:
- `sponsor_attendee`: count of badges classified as sponsor attendees
- `non_business_badge`: count classified as non-business badges
- `existing_disqualified`: count classified as existing disqualified
- `missing_contact`: count of badges missing contact info

These counts must be integers.

## General rules

### Normalization

Every email and phone field follows the same normalization:
- **email**: `.trim().toLowerCase()`. Empty string `""` when no email exists.
- **phone**: Strip all non-digit characters. Empty string `""` when no phone exists.

### Sorting discipline

Sorting rules in the answer template are mandatory. When the template says "Sort by X ascending", do exactly that with standard string comparison. When it specifies a secondary sort key ("by X ascending, then Y ascending"), apply both. Enum ordering (like platforms) follows the order stated in the template or policy, not alphabetical order.

### Integer types

All counts and USD amounts must be JSON integers, not floats. No decimal points, no string wrapping.

### Prose prohibition

Return only the JSON object. Do not add markdown fences, explanatory text, or comments outside the JSON structure, unless the template explicitly allows it.

### Enum discipline

Use only the exact enum strings listed in the template's `allowed_values` or `*_enum` lists. Do not invent variant spellings (e.g., use `"not_sponsor"` only if the template lists it; otherwise do not include it). When a template field declares `"type": "enum"`, the output value must be one of the allowed strings.

### Field completeness

A template that lists `required_keys` or `item_required_keys` defines the mandatory fields. Every object in the output must have all of those keys, even if the value is `null`, `0`, or `""` for that particular record.

### Null vs. empty

- Use `null` for missing reference IDs (`account_id`, `invoice_id`, `crm_account_id`, `existing_account_id`, `existing_contact_id`).
- Use `0` for numeric fields that have no value.
- Use `""` for string fields that have no value (normalized email/phone when absent).
- Use `[]` for empty arrays only when the template explicitly calls for an array field.
