---
name: harborcrm-handoff-solver
description: Solve HarborCRM public-API tasks for CRM event handoff, sponsor reconciliation, trade-show prospecting, and import-batch cleanup.
---

# HarborCRM Handoff Solver

Use this skill when a task asks for a JSON answer from HarborCRM event, trade-show, CRM, finance, campaign-member, or import-batch data. The answer template is authoritative: preserve its top-level keys, field names, enum spellings, null-vs-empty-string conventions, and ordering rules. Return one JSON object only.

## Standard SOP

1. Read the prompt and `input/payloads/answer_template.json` first. Copy the required shape mentally before fetching data; do not add explanatory fields.
2. Use only the HarborCRM public API base URL supplied by the runner or environment note. Do not inspect local source.
3. Fetch `/api/policies` plus the task-specific records. Policies are usually brief, so also use the prompt, template enums, descriptions, and CRM state.
4. Build lookup tables before classifying:
   - CRM accounts by `account_id`, normalized `name`, and `domain`.
   - CRM contacts by normalized `email`, digits-only `phone`, `contact_id`, and account.
   - Campaign members by event/campaign plus contact/account identifiers.
   - Finance invoices by `event_id` and `account_id`.
   - Trade-show meeting interest by normalized `company_name`.
5. Normalize consistently: trim strings; lowercase emails; strip all non-digits from phones; use `""` for missing normalized contact fields when the template says string, and `null` for absent IDs/invoices when the template allows null.
6. Compute classifications and counts from unique business entities at the level the template implies. Do not double-count one account because it has multiple badges, contacts, rows, or platform tags unless the field explicitly counts records.
7. Sort every list exactly as the template says. Validate final JSON for schema, enum values, integer money/counts, booleans, dates, and no prose.

## Data Source Habits

For event handoff tasks, fetch event details, sponsor orders or packages, badges, finance invoices filtered by event, CRM accounts, contacts, opportunities, campaign members filtered by event, and policies. The event record supplies `campaign_code`, `end_date`, lead opportunity amount, and follow-up day offsets.

For trade-show prospecting tasks, fetch trade-show metadata, exhibitors, meeting interest, CRM accounts/contacts as requested, and policies. Exhibitor descriptions and meeting interest are the main qualification signals.

For import-batch tasks, fetch import batches, the batch raw contacts, batch suppression records, CRM accounts, CRM contacts, and policies. Treat suppression and contact hygiene as removal/classification inputs, not as optional annotations.

Prefer stable IDs over names when present. When only names are available, compare trimmed lowercase names and use domain/email matches to confirm CRM overlap. Keep display names from the source record in the output unless a field explicitly asks for normalized text.

## Output Field Conventions

- Money is integer USD. Counts are integers. Dates are `YYYY-MM-DD`; event lead and sponsor follow-up due dates are usually `event.end_date` plus the corresponding day offset.
- Platform lists use the policy/template enum order: `AUV`, `ROV`, `Underwater Camera`.
- Existing IDs should be strings when known and `null` when absent if the template allows null.
- Normalized contact fields use lowercase trimmed email and digits-only phone; missing values are `""`.
- Controlled enums must match the template exactly, including values such as `paid_deferred`, `open_invoice`, `proposal_only`, `create_account`, `update_existing`, `no_import`, `add_campaign_member`, `create`, `update`, and `no_action`.

## Sponsor And Event Handoff

Treat confirmed sponsor orders as active sponsors. Map paid/deferred invoices to `paid_deferred`; confirmed sponsors with open invoices to `open_invoice`; proposal-stage sponsor records to `proposal_only` when the template supports it. Canceled or inactive sponsor records are not active revenue and should be excluded or marked with the template's inactive/canceled reason.

For sponsor revenue, sum package/order amounts by sponsor status. For open invoices, also compute open balance as invoice amount minus paid amount. Do not double-count if both orders and sponsor packages expose the same records. Finance follow-up usually targets unpaid/open invoice sponsor accounts, sorted by account name.

Sponsor contacts and sponsor badges are not qualified non-sponsor leads. Business attendee badges can become qualified non-sponsor leads only when the account is not a sponsor/proposal sponsor, is not disqualified in CRM, has usable contact information, and is not a non-business badge type. Use the event's lead opportunity amount per unique qualified non-sponsor account for pipeline totals.

For badge-level decisions, common classifications are:
- `sponsor_attendee`: active sponsor/proposal sponsor contact or badge.
- `qualified_non_sponsor_lead`: business badge/contact for a non-sponsor, non-disqualified account.
- `excluded`: non-business, missing contact, existing disqualified account, inactive sponsor record, or other template-defined exclusion.

For campaign members, compare the target status to existing members. Create when absent, update when present with the wrong status, `no_action` when already correct, and `no_import` for excluded records. Sponsor targets commonly use `attended_sponsor` or `registered_sponsor`; qualified non-sponsor attendance commonly uses `attended`.

## Trade-Show Prospecting

Qualify exhibitors that build or OEM-integrate target underwater platforms, not merely companies adjacent to them. Detect platforms from descriptions:
- `AUV`: autonomous underwater vehicles, drones, scouts, mapping vehicles.
- `ROV`: remotely operated vehicles, inspection ROVs, pen-cleaning ROVs.
- `Underwater Camera`: camera modules, camera arrays, underwater optics/camera manufacturers.

Exclude near misses with controlled reasons. Common patterns: distributors/resellers only, service/consulting/operators only, sensor/probe vendors only, research-only organizations, analytics/software without platform manufacturing, or otherwise not in the target market.

Use meeting interest for requested-demo flags, interest scores, ranking, and priority when the prompt defines thresholds. Existing CRM overlap usually means `update_existing`; no CRM account means `create_account`; excluded exhibitors usually use `no_import`. Platform coverage counts count qualified exhibitors that include each platform, so a multi-platform lead increments multiple platform buckets.

When ranking is requested, follow the prompt's ranking cascade exactly. If the template instead says alphabetical, sort by company name. Ranks should be 1-based and contiguous.

## Import-Batch Cleanup

Normalize every raw row before judging it. A row with no usable email and no usable phone is usually `missing_contact`. A row matching suppression by normalized email or phone is `suppressed` and should not survive into clean import contacts unless the template explicitly asks to retain suppressed rows.

Build duplicate keys from the strongest available contact identity, usually normalized email first, then normalized phone when email is blank. Remove duplicates deterministically. Prefer the task's stated winner rule; if none is stated, use a consistent hierarchy such as newest `captured_at`, then more complete contact data, then stable row ID. Record duplicate keys, winning row IDs, and removed row IDs as the template requires.

For surviving clean contacts, set `clean_contact_id` and `source_row_id` to the winning source row ID when requested. Fill `existing_account_id` and `existing_contact_id` from CRM matches. Use `update_existing` for existing CRM accounts/contacts that should receive the import, `create_account` for new accounts, and `no_import` or `suppress` only when those rows remain in the clean list by template design. Campaign-member import count should count surviving importable contacts, not removed, suppressed, or duplicate rows.

## Sorting Defaults

Use explicit template sorting first. Common HarborCRM defaults:
- Sponsor statuses: `account_name` ascending.
- Qualified lead accounts/exhibitors: `account_name` or `company_name` ascending unless ranked.
- Ranked leads: `rank` ascending.
- Excluded companies: `company_name` ascending; event excluded records often then `contact_name` ascending.
- Badge decisions: `badge_id` ascending.
- Campaign-member actions: `subject_key` ascending.
- Duplicate keys: `key` ascending; removed rows and row IDs ascending.
- CRM account ID lists: ID ascending.
- Names inside summary lists: ascending.

## Pitfalls

- The answer template beats assumptions from prior tasks. Some tasks want account-level records; others want badge-level or row-level records.
- Do not include train data values, solved examples, or any material from hidden/unseen tasks in a reusable skill.
- `order_status: proposal_sent` is sponsor-related but not paid revenue; `order_status: canceled` is not an active sponsor.
- Invoice `status: open` maps to `open_invoice`; `paid_deferred` is a sponsor status, not an unpaid balance.
- Existing CRM accounts with `status: disqualified` or a disqualification reason are exclusions even if the badge or meeting score looks strong.
- Non-business badges such as press/student/personal records are exclusions, not sales leads.
- Do not let sponsor attendees create non-sponsor opportunities or inflate lead task counts.
- Preserve controlled enum spellings like `sensor_vendor_only` versus `sensor_only`; similar-looking templates may use different values.
- Platform counts are not mutually exclusive. Priority counts and lead totals usually are.
- Validate JSON after construction; most mistakes are extra fields, wrong null/empty values, unsorted lists, or counts that do not match the final included records.
