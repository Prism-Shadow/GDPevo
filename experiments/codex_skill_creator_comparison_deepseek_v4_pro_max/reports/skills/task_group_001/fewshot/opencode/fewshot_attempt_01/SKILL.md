---
name: harbor-crm-integration
description: Integrate HarborCRM REST API data for post-event reconciliation, trade-show exhibitor prospecting, contact import batch preparation, campaign member management, and cross-entity CRM workflows. Use whenever a task mentions HarborCRM, event reconciliation, trade-show lead qualification, contact import cleaning, sponsor finance handoff, CRM data merge, badge-based lead handoff, or any multi-entity data integration against the HarborCRM API — even if the user doesn't name it directly.
---

# HarborCRM Integration

Work with the HarborCRM REST API to fetch, cross-reference, classify, and produce structured JSON output across events, finance, CRM, trade-shows, and import pipelines.

## How to approach any HarborCRM task

1. **Read the answer template** the task provides. It defines every required key, allowed enum value, sort order, and field type. The template is the authoritative schema for the output.

2. **Fetch `/api/policies` first.** Policies carry the business rules that drive qualification, opportunity sizing, follow-up offsets, source priorities, and controlled vocabulary. Everything else follows from them.

3. **Pull all relevant API data in parallel.** The API has no dependencies between endpoints — fetch event+orders+badges+sponsor_packages together, or tradeshow+exhibitors+meeting_interest together. Then fetch invoices, CRM entities, and campaign members in a second wave once you know which IDs to filter by.

4. **Match entities by ID first, then by normalized email, then by normalized company name.** See [references/data-model.md](references/data-model.md) for the exact join keys between entities.

5. **Classify records using policy-driven rules, not hardcoded values.** Sponsor statuses, badge classifications, lead qualification, CRM actions, and exclusion reasons all flow from policy data combined with entity state.

6. **Return a single JSON object with no surrounding prose.** The output must conform exactly to the answer template — no extra keys, no omitted required keys, correct enum values, integer counts, and the exact sorting the template demands.

## Common workflows

### Post-event reconciliation

Given an event_id and an answer template:

- Fetch the event, its orders, badges, and sponsor packages together.
- Fetch invoices filtered by `event_id`.
- Fetch CRM accounts, contacts, opportunities, and campaign members filtered by `event_id` where supported.
- **Sponsor statuses**: Join orders → invoices by account_id. Classify each sponsor as `paid_deferred` (fully paid), `open_invoice` (has invoice with outstanding balance), or `proposal_only` (order exists, no invoice). Sort by account_name ascending.
- **Sponsor revenue**: Sum package_amount per status. For open_invoice, also sum open_balance separately.
- **Badge classification**: Cross-reference badge company_name/email against sponsor account_ids. A badge belongs to a sponsor if its company matches a sponsor account. Classify each badge as `sponsor_attendee`, `qualified_non_sponsor_lead`, or `excluded`.
- **Exclusions**: Exclude sponsor attendees, badges with non-business types, contacts from CRM accounts with disqualified status, and badges missing contact names. List each excluded record with company_name, contact_name, and the controlled exclusion reason. Sort by company_name then contact_name ascending.
- **Qualified leads**: Non-sponsor, non-excluded badges. For each, determine CRM action by checking whether the account and contact already exist. Use the event's lead opportunity amount from policies (not a per-account negotiation).
- **CRM action counts**: Count accounts_create, accounts_update, contacts_create, contacts_update, campaign_members_create, campaign_members_update across all qualified leads.
- **Follow-up dates**: Add the policy-defined lead follow-up offset days to the event end date for lead tasks. Use a shorter offset for sponsor finance tasks. Task counts equal the number of qualified leads and the number of sponsors needing finance follow-up (open_invoice + proposal_only).

### Trade-show exhibitor prospecting

Given a show_id, campaign identifier, and answer template:

- Fetch the tradeshow, exhibitors, and meeting interest records together.
- Fetch CRM accounts and policies.
- **Qualification**: Policies define which exhibitor relationship types (OEM, distributor, service_provider, sensor_vendor, research) qualify for the campaign. Exhibitors whose relationship_type is not in the qualifying set are excluded.
- **Platform assignment**: Each exhibitor has a list of platforms. Map these to the controlled enum allowed by the template (typically AUV, ROV, Underwater Camera). Sort platforms in the enum order specified.
- **Priority tiers**: Policies define thresholds using meeting_interest scores and demo requests. When an exhibitor has no meeting interest record, default interest_score to 0 and requested_demo to false.
- **Ranking**: Apply the ranking rules from the task template. Common pattern: demo-requested first, then descending interest score, then broader platform coverage, then company name ascending.
- **CRM matching**: Check each qualified exhibitor against CRM accounts by company name. Assign `update_existing` when a match is found, `create_account` otherwise.
- **Opportunity sizing**: Use policy-defined or template-specified amounts by priority tier, not per-exhibitor negotiated values.
- **Exclusions**: For each non-qualifying exhibitor, record the company_id, company_name, and the controlled exclusion reason (`distributor_only`, `service_only`, `sensor_vendor_only`, `research_only`, `not_target_market`). Sort by company_name ascending.
- **Aggregate counts**: Qualified total, platform counts per enum value, priority counts per tier, excluded total.

### Import batch preparation

Given a batch_id and answer template:

- Fetch the import batch, raw contacts, and suppression list together.
- Fetch CRM accounts, contacts, and policies.
- **Deduplication**: Group raw contacts by normalized email (lowercase, trimmed). For groups with multiple rows, pick a winner using source priority from policies. Record removed duplicates with the dedup key (format `"email:<normalized_email>"`), winner row_id, and removed row_ids.
- **Suppression**: Remove rows whose normalized email or normalized company name appears in the suppression list.
- **Unusable rows**: Remove rows with missing contact_name. The removal reason is `missing_contact`.
- **CRM matching**: For each surviving contact, look up existing CRM accounts by normalized company name or email domain. Look up existing CRM contacts by normalized email. Populate existing_account_id (or null) and existing_contact_id (or null).
- **CRM actions**: Assign `create_account` for new companies, `update_existing` for matched companies, `suppress` for suppression matches, `no_import` for unusable rows.
- **Clean contacts**: Sort by clean_contact_id (which equals the winning source row_id) ascending.
- **Removal summary**: List all removed rows with row_id and reason. Sort by row_id ascending. Count unusable_removed and suppressed_removed separately.
- **Campaign member count**: Every surviving clean contact with crm_action `create_account` or `update_existing` counts toward campaign member import.

### Campaign member management

When a task requires campaign member create/update/no-action decisions:

- Fetch existing campaign members filtered by `event_id`.
- Cross-reference with badge classifications and sponsor registrations.
- **No action**: Existing campaign members for sponsor attendees or registrants who are already correctly tracked.
- **Create**: Qualified non-sponsor badge leads not yet in campaign members, plus sponsor attendees who need campaign member records.
- **Update**: Existing campaign members whose status needs correction.
- **No import**: Excluded badges (non-business, missing contact, disqualified).
- Target status values: `attended` (non-sponsor attendee), `attended_sponsor` (sponsor attendee), `registered_sponsor` (sponsor registrant who didn't attend).
- Sort campaign member actions by subject_key ascending.

## Entity resolution

When joining records across API endpoints, use these strategies in order:

1. **By ID**: account_id, contact_id, badge_id, company_id — exact match, always preferred.
2. **By normalized email**: Lowercase, trim whitespace. Used for contact-level matching.
3. **By normalized company name**: Lowercase, strip punctuation and common suffixes (Inc, LLC, Ltd, Corp), trim. Use for account-level matching.
4. **By email domain**: Extract domain from email, match to known company domains from CRM accounts.

When multiple CRM accounts match the same normalized company name, prefer the one with matching email domain or the most recently modified.

## Classification reference

Every classification value must come from the answer template's allowed enums. These are common across HarborCRM tasks but always verify against the specific template:

**Sponsor financial status**: `paid_deferred`, `open_invoice`, `proposal_only`
- `paid_deferred`: Invoice exists and paid_amount equals or exceeds package_amount.
- `open_invoice`: Invoice exists with paid_amount less than package_amount.
- `proposal_only`: Sponsor order exists but no invoice has been issued (invoice_id is null).

**Badge classification**: `sponsor_attendee`, `qualified_non_sponsor_lead`, `excluded`
- `sponsor_attendee`: Badge holder's company matches a sponsor account.
- `qualified_non_sponsor_lead`: Non-sponsor, business badge type, account not disqualified.
- `excluded`: Non-business badge, disqualified CRM account, or missing required fields.

**Badge exclusion reasons**: `sponsor_attendee`, `non_business_badge`, `existing_disqualified`, `missing_contact`, `inactive_sponsor_record`

**Trade-show exclusion reasons**: `distributor_only`, `service_only`, `sensor_vendor_only`, `research_only`, `not_target_market`

**CRM actions** (accounts/contacts): `create_account`, `update_existing`, `create_contact`, `no_import`, `suppress`

**Campaign member actions**: `create`, `update`, `no_action`, `no_import`

**Campaign member target statuses**: `attended`, `attended_sponsor`, `registered_sponsor`, `excluded`

**Platform enums**: `AUV`, `ROV`, `Underwater Camera` (always sort in this order)

**Priority tiers**: `A`, `B`, `C`

**Import source names**: `badge_scan`, `sponsor_form`, `partner_upload`, `webinar_form`, `exhibitor_form`, `manual_upload`

## Normalization rules

Apply these consistently across all workflows:

- **Email**: Convert to lowercase, trim leading/trailing whitespace. Use empty string `""` when not supplied.
- **Phone**: Strip all characters except digits (0-9). Use empty string `""` when not supplied. Do not add country code prefixes unless the raw data already includes them.
- **Company name for matching**: Lowercase, remove punctuation (periods, commas, hyphens), collapse whitespace. Remove common legal suffixes (Inc, LLC, Ltd, Corp, Co, GmbH, Pty Ltd). For display, always use the original casing from the source data.
- **Dedup keys**: Format as `"email:<normalized_email>"` for email-based dedup, `"phone:<normalized_phone>"` for phone-based.

## Sorting conventions

When the answer template specifies a sort order, follow it exactly. These defaults apply when the template is less explicit:

- Account/company names: ascending, case-insensitive alphabetical.
- IDs (account_id, badge_id, row_id, company_id): ascending alphanumeric.
- Ranks: numeric ascending, 1-based and contiguous.
- Platforms within a list: always the enum order `AUV`, `ROV`, `Underwater Camera`.
- Excluded records: by `company_name` ascending, then `contact_name` ascending.
- Duplicate keys: by key string ascending.
- Removed rows: by row_id ascending.

## Numeric and date conventions

- **All monetary amounts**: integers (whole USD). No decimals, no currency symbols inside values.
- **Counts**: integers.
- **Dates**: ISO 8601 `YYYY-MM-DD` strings.
- **Nullable fields**: Use JSON `null` for absent IDs. Use `""` for absent strings.
- **invoice_id** is `null` when no invoice exists (proposal_only sponsors).

## Fetch strategy

The HarborCRM API is read-only and stateless. Optimize for parallelism:

- **Wave 1**: Fetch the primary entity (event/tradeshow/batch) plus all its directly-related collections (orders, badges, sponsor_packages, exhibitors, meeting_interest, raw_contacts, suppression). Also fetch policies.
- **Wave 2**: Fetch CRM entities filtered by the IDs or event_ids discovered in Wave 1. Also fetch invoices filtered by event_id or account_id.
- **No write operations**: All endpoints are GET only. The output JSON represents intended CRM actions, not executed ones.

When a filter parameter is available (event_id, account_id, status, owner_region), use it to limit result size.

## Error handling

- When a referenced entity ID produces no match in a join, skip that record. If the template provides an exclusion list, include it there with an appropriate reason.
- When an invoice shows zero paid_amount, classify the sponsor as `open_invoice` with `open_balance` equal to the full `package_amount`.
- When a badge has no associated company, classify it as excluded with reason `non_business_badge` or `missing_contact` depending on what data is absent.
- When a trade-show exhibitor has no meeting_interest record, default `interest_score` to 0 and `requested_demo` to false.
- When multiple CRM records match, prefer the one with matching domain, then the most recently modified, then the lowest ID.

## Reference files

- [references/api-surface.md](references/api-surface.md) — Complete endpoint catalog with query parameters and response shapes.
- [references/data-model.md](references/data-model.md) — Entity descriptions, field meanings, and cross-entity join keys.
