# HarborCRM CRM Reconciliation SOP

Use this skill for HarborCRM tasks that ask for CRM-ready JSON from public API data: post-event sponsor/lead handoffs, trade-show prospecting summaries, and contact import hygiene. Always read the staged prompt and answer template first, then shape the response exactly to the template.

## Core Workflow

1. Identify the requested object id: `event_id`, `show_id`, or `batch_id`.
2. Pull every public API source named or implied by the prompt before deciding: event/show metadata, sponsor orders/packages, badges or exhibitors, finance invoices, CRM accounts, CRM contacts, opportunities, campaign members, suppression lists, meeting-interest records, and policies.
3. Build joins using stable ids first, then normalized names/domains/emails as fallback.
4. Normalize data before matching:
   - Emails: trim and lowercase.
   - Phones: digits only; leave `""` when no phone exists.
   - Money and counts: integers.
   - Dates: calendar dates in `YYYY-MM-DD`; follow-up due dates are event end date plus the configured day offset.
5. Return JSON only. Do not add undeclared fields or explanatory prose.

## Event And Sponsor Handoff

Use event details, sponsor orders or packages, finance invoices, badges, CRM records, opportunities, campaign members, and policies together.

- Treat confirmed sponsor orders with paid/deferred invoices as `paid_deferred`.
- Treat confirmed sponsor orders with open invoices as `open_invoice`; open balance is invoice amount minus paid amount.
- Treat proposal-stage sponsor packages as `proposal_only`.
- Exclude canceled or inactive sponsor records from active sponsor status lists unless the template explicitly asks for not-sponsor decisions.
- Sponsor revenue totals should sum package or invoice amounts by controlled status. Keep open-invoice balance as its own value when requested.
- Finance follow-up targets are the unsettled sponsor accounts: open invoices and, when the prompt includes proposal handoff, proposal-only packages. Do not include fully paid/deferred sponsors in unpaid follow-up targets.

For badge decisions:

- Sponsor attendees are not non-sponsor leads, even if their badge type is `attendee`; match by sponsor account, company name, or ticket-contact context.
- Qualified non-sponsor leads are business attendees with usable contact facts, no sponsor linkage, and no disqualified CRM account.
- Non-business badges such as student or press records are excluded.
- Existing disqualified CRM accounts stay excluded even when the event scan score is high.
- A record with one usable contact channel is contactable unless the template defines missing contact more narrowly.

## CRM Actions

Choose actions from the template enums only.

- Existing valid CRM account, new contact: update the account and create or add the contact/campaign member.
- New account and new contact: create account, contact, and campaign member.
- Existing campaign member with the correct target status: `no_action`.
- Existing campaign member needing a new event status: `update`.
- Excluded lead-import rows: `no_import`.
- Keep lead-import decisions separate from campaign-member reconciliation when the template has both sections. A sponsor badge can be excluded from lead import while still having a campaign-member action.

Common campaign-member target statuses:

- Sponsor attendee with badge attendance: `attended_sponsor`.
- Sponsor ticket/contact without attendance badge: `registered_sponsor`.
- Qualified non-sponsor attendee: `attended`.
- Excluded badge or row: `excluded`.

## Trade-Show Prospecting

Use trade-show metadata, exhibitors, meeting interest, CRM accounts/contacts, and policies.

- Qualify exhibitors that manufacture or OEM-build covered platforms.
- Covered platform enums should be used exactly as supplied, normally ordered `AUV`, `ROV`, `Underwater Camera`.
- Count platform coverage by platform occurrence across qualified exhibitors, not just by lead count.
- Exclude adjacent companies that do not make target platforms:
  - Distributor or reseller only: `distributor_only`.
  - Services or consulting only: `service_only`.
  - Sensor vendor only: `sensor_vendor_only` or `sensor_only`, matching the template enum.
  - Research-only organizations: `research_only`.
- Existing CRM account overlap means `update_existing`; qualified exhibitors without CRM accounts are `create_account`.
- When ranking is requested, apply the prompt's rank keys in order. A common pattern is demo request first, interest score descending, broader platform coverage, then company name.
- When priority tiers are supplied, derive opportunity size strictly from the tier mapping in the prompt.

## Import Batch Hygiene

Use raw contacts, suppression data, CRM accounts, CRM contacts, and policies.

- Remove suppressed rows by normalized email or phone before import.
- Remove unusable rows with no usable contact channel.
- Deduplicate with normalized email as the strongest key when present; use the template's duplicate-key format, often `email:<normalized_email>`.
- Choose the winning duplicate row by explicit prompt rules. If none are given, prefer fresher, more complete, higher-confidence source rows while keeping the winner's source row id and timestamp.
- Clean-contact ids and source row ids should be the winning source row id when the template asks for that convention.
- Do not include duplicate, suppressed, or unusable rows in clean contacts or campaign-member import counts.
- Keep removal summaries sorted by row id and duplicate summaries sorted by duplicate key.

## Sorting And Field Conventions

Follow template ordering literally:

- Sponsor/account lists: `account_name` ascending.
- Qualified company lists: `company_name` ascending unless ranked output is requested.
- Ranked leads: contiguous `rank` starting at 1.
- Badge decisions: `badge_id` ascending.
- Campaign-member actions: `subject_key` ascending.
- Exclusions with people: `company_name` ascending, then `contact_name` ascending.
- Duplicate keys: key ascending.
- Removed rows: row id ascending.
- CRM account id lists: account id ascending.

Use `null` only where the template permits a missing id or invoice. Use `""` for normalized email or phone when the template allows an empty string.

## Pitfalls

- Do not infer from one source alone when the prompt asks for reconciliation; sponsor order, invoice, CRM, and badge facts can disagree.
- Do not count sponsor contacts as non-sponsor pipeline.
- Do not let canceled sponsor packages become active sponsors.
- Do not exclude a new contact just because another contact on the same account is opted out; suppression is contact-specific unless the prompt says otherwise.
- Do not double-count duplicate rows in import totals.
- Do not add prose, comments, or helper fields to the final JSON.
