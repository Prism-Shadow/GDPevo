---
name: reflection-skill-attempt-02
description: Prepare HarborCRM JSON handoffs from the shared API for event sponsor/lead reconciliation, CRM import-batch cleanup, and trade-show prospecting tasks. Use when a task asks for HarborCRM API analysis involving events, badges, sponsor packages, finance invoices, CRM accounts/contacts/opportunities/campaign members, import batches, suppression lists, tradeshows, exhibitors, meeting interest, policies, controlled enums, action counts, follow-up dates, or import-ready JSON outputs.
---

# HarborCRM Workflow SOP

## Core Workflow

1. Read the task prompt and answer template first. Treat the template as the contract: preserve required keys, allowed enums, null-vs-empty-string rules, numeric precision, and sorting.
2. Query only the public HarborCRM endpoints needed for the requested entity IDs. Start with `/health` only to verify availability, then fetch specific records and shared CRM/policy tables.
3. Normalize joins before judging records:
   - Accounts: match by `account_id` when supplied; otherwise use exact/near company name and domain clues.
   - Contacts: match by `contact_id` when supplied; otherwise use normalized email first, then name plus account.
   - Campaign members: join by `event_id`, `account_id`, and `contact_id`.
   - Suppression: compare normalized email and digits-only phone.
4. Build the answer from source data, then recompute all totals from the output rows. Do not hand-enter counts.
5. Apply template sorting last. Use the exact ordering requested, including enum order for platform arrays.

## API Patterns

Use the base URL supplied by the runner. Common endpoints:

```text
GET /api/events
GET /api/events/{event_id}
GET /api/events/{event_id}/orders
GET /api/events/{event_id}/badges
GET /api/events/{event_id}/sponsor_packages
GET /api/finance/invoices?event_id={event_id}
GET /api/crm/accounts
GET /api/crm/contacts
GET /api/crm/opportunities
GET /api/crm/campaign_members?event_id={event_id}
GET /api/tradeshows
GET /api/tradeshows/{show_id}/exhibitors
GET /api/tradeshows/{show_id}/meeting_interest
GET /api/import_batches
GET /api/import_batches/{batch_id}/raw_contacts
GET /api/import_batches/{batch_id}/suppression
GET /api/policies
```

Always fetch `/api/policies` for controlled enums and business notes. It often disambiguates status enums and platform qualification.

## Normalization Rules

- Email: trim whitespace and lowercase. Use `""` when the template allows an empty missing email.
- Phone: strip non-digits only. Do not infer, prepend, or remove country codes.
- Dates: derive follow-up dates by adding the event's `followup_days_after_end` or `sponsor_followup_days_after_end` to `end_date`. Use `YYYY-MM-DD`.
- Currency and counts: output integer USD and integer counts.
- Existing CRM overlap: use provided `crm_account_id` when present; otherwise match to CRM account names/domains conservatively.

## Event Handoff Rules

Sponsor status:

- `paid_deferred`: confirmed sponsor with invoice status `paid_deferred`.
- `open_invoice`: confirmed sponsor with an open finance invoice. Report full package/invoice amount as sponsor revenue and open balance separately as `amount - paid_amount`.
- `proposal_only`: sponsor package/order in proposal state with no paid/open invoice.
- Exclude canceled/inactive sponsor packages from active sponsor status lists unless the template explicitly asks to list inactive records.

Sponsor exclusions and finance follow-up:

- Sponsor contacts include badge records with `badge_type: sponsor` and names in sponsor package `ticket_contacts`, even if no badge scan exists.
- Proposal-only ticket contacts are still sponsor contacts for exclusion from non-sponsor pipeline.
- Finance follow-up can include both open invoices and proposal-only sponsor packages when the template asks for unpaid sponsor accounts, not just invoiced balances.
- If an excluded sponsor-related account is also CRM-disqualified, prefer `existing_disqualified` when the template expects a single reason and the badge/contact is not an active sponsor ticket contact.

Lead qualification:

- Qualified non-sponsor leads must be business badges from non-sponsor, non-disqualified CRM accounts.
- Exclude non-business badge types such as student or press unless the prompt overrides this.
- Use the event's `lead_opportunity_amount` for each qualified non-sponsor account.
- Existing account plus missing contact usually means `update_existing` account and `create_contact`; new company means `create_account` and `create_contact`.
- Campaign-member create/update/no-action depends on current campaign members. Do not update disqualified or non-business exclusions unless asked.

Event output fields:

- `sponsor_revenue_totals.open_invoice` is the full open invoice/package amount; `open_invoice_balance` is the unpaid balance.
- `lead_pipeline_total` or open opportunity total equals qualified non-sponsor account count times the event lead opportunity amount.
- `lead_task_count` is usually the number of qualified lead accounts.
- `sponsor_finance_task_count` is usually the number of unpaid/open/proposal sponsor finance targets in the follow-up account list.
- For badge-level reconciliation, existing member subject keys should use `account_id:contact_id`; badge-only creates should use `badge:{badge_id}` when the template asks for `subject_key`.
- Proposal-only sponsor badge contacts can still need `create_contact_campaign_member` and a campaign-member `create` action with `attended_sponsor`, while staying out of non-sponsor opportunity totals.

## Import-Batch Cleanup Rules

Record classification:

- Remove rows with no usable contact channel when the task defines contactability as normalized email or phone.
- Remove suppressed rows when normalized email or phone matches batch suppression.
- Deduplicate before final clean output. Duplicate keys are usually normalized email when present, otherwise normalized phone.
- Surviving clean contacts get `clean_contact_id` and `source_row_id` from the winning raw row.

Duplicate winner selection:

- Prefer the richer/import-priority row, not simply the lowest row id. Later partner/import rows can beat earlier webinar rows, especially when they carry a more complete phone value such as a country code.
- If timestamps tie, choose the row with the more complete phone/source record; then use its company name, source, timestamp, and normalized phone in `clean_contacts`.

Import actions and counts:

- `update_existing`: normalized company/contact matches an existing CRM account/contact context.
- `create_account`: no existing CRM account match and the contact survives cleanup.
- `no_import`: count duplicate and unusable removals when the template includes removal action totals.
- `suppress`: count suppressed removals.
- `campaign_member_import_count` is the number of surviving clean contacts to add to the batch campaign.

## Trade-Show Prospecting Rules

Qualification:

- Qualify exhibitors that make or OEM-build covered platforms, not companies that only resell, service, operate, analyze, or supply sensors to those platforms.
- Controlled platform enums are usually `AUV`, `ROV`, and `Underwater Camera`. Sort platform arrays in that enum order.
- Infer platforms from descriptions:
  - AUV: autonomous underwater vehicles, scouts, drones.
  - ROV: remotely operated vehicles, inspection/cleaning robots.
  - Underwater Camera: OEM underwater camera modules, camera arrays, low-light inspection cameras.

Priority and ranking:

- When a prompt gives tier thresholds, apply them exactly. A common pattern is: demo requested and score at least 90 -> `A`; demo requested and score at least 80 -> `B`; otherwise `C`.
- For ranked lead lists, rank demo requests before non-demo, then higher interest score, then broader platform coverage, then company name.
- Opportunity estimates often map from priority tier; recompute total opportunity from ranked leads.

Exclusions:

- Distributor/reseller/sales agent only -> `distributor_only`.
- Consulting, operator, analytics-only, or service provider without platform manufacturing -> `service_only`.
- Sensor-only vendor -> `sensor_vendor_only` or `sensor_only`, matching the template enum.
- Research-only institution/lab -> `research_only`.
- Use the template's relationship enum if present, such as `distributor`, `service_provider`, `sensor_vendor`, or `research`.

## Common Pitfalls

- Do not add country codes during phone normalization. Only strip punctuation and spaces.
- Do not treat proposal-only sponsors as qualified non-sponsor leads just because their badge type is `attendee`.
- Do not omit sponsor ticket contacts from exclusions merely because they lack badge scans.
- Do not limit sponsor finance follow-up to open invoices when proposal-only packages are unpaid sponsor targets.
- Do not count only surviving import rows in `import_action_totals`; removed duplicates, unusable rows, and suppressions may contribute to `no_import` and `suppress`.
- Do not use task-specific examples as defaults. Re-read the prompt and template every time; enum names can vary by task (`sensor_vendor_only` vs `sensor_only`).
