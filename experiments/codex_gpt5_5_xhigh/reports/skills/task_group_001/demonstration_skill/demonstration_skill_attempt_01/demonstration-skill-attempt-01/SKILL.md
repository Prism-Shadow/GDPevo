---
name: task-group-001-fewshot-attempt-01
description: Produce HarborCRM JSON answers for evaluation tasks that provide prompts, answer_template.json files, and HarborCRM API data. Use when reconciling event sponsorships, badge leads, campaign members, finance invoices, trade-show prospecting, or import batch hygiene into exact JSON output schemas with controlled enums, counts, dates, and CRM actions.
---

# HarborCRM JSON Answer Procedures

## Operating Workflow

1. Read the user prompt and `input/payloads/answer_template.json` first. Treat the template as the contract: return exactly the requested top-level keys, field names, enum spellings, nullability, and ordering.
2. Use the API base URL supplied by the runner. Optionally check `/health`, then fetch only the endpoints needed for the task family.
3. Build normalized indexes before deciding actions:
   - Email: trim, lowercase, use empty string for blanks.
   - Phone: keep digits only; do not invent a country code.
   - Company/account: match exact names first, then normalized names, then email domain to CRM account `domain` when available.
   - Contacts: match normalized email first; if no email, use account plus normalized contact name or phone.
4. Derive decisions from API data, not from prose alone. Use the prompt only to choose the task family, target ID, required ranking, and any special sizing rules.
5. Emit JSON only. Validate mentally or with a JSON parser when possible. Do not add explanatory text, comments, or extra fields.

## API Checklist

For event handoff tasks, fetch:

- `/api/events/{event_id}`
- `/api/events/{event_id}/sponsor_packages` or `/api/events/{event_id}/orders`
- `/api/events/{event_id}/badges`
- `/api/finance/invoices?event_id={event_id}`
- `/api/crm/accounts`
- `/api/crm/contacts`
- `/api/crm/opportunities` when the template mentions opportunities
- `/api/crm/campaign_members?event_id={event_id}` when campaign-member actions are requested
- `/api/policies`

For trade-show prospecting tasks, fetch:

- `/api/tradeshows` and filter to the prompt's `show_id` if show metadata is needed
- `/api/tradeshows/{show_id}/exhibitors`
- `/api/tradeshows/{show_id}/meeting_interest`
- `/api/crm/accounts`
- `/api/crm/contacts` only if contact overlap is requested
- `/api/policies`

For import-batch hygiene tasks, fetch:

- `/api/import_batches` and filter to the prompt's `batch_id`
- `/api/import_batches/{batch_id}/raw_contacts`
- `/api/import_batches/{batch_id}/suppression`
- `/api/crm/accounts`
- `/api/crm/contacts`
- `/api/policies`

## Event Sponsor And Badge Handoff

Use active sponsor packages/orders plus invoices to determine sponsor status.

- Treat `confirmed` sponsor packages as active sponsors.
- Treat `proposal_sent` packages as active proposal sponsors.
- Treat `canceled` or inactive packages as non-active. Do not count them in sponsor revenue. If a badge/account is also CRM-disqualified, prefer `existing_disqualified` over an inactive-sponsor reason.
- `paid_deferred`: a confirmed sponsor whose invoice is paid/deferred or fully paid.
- `open_invoice`: a confirmed sponsor with an open invoice or paid amount below package amount.
- `proposal_only`: a proposal sponsor with no invoice.
- `not_sponsor`: use only when the template explicitly asks for non-sponsor candidates.
- Use sponsor package/order amount for revenue totals. Use invoice `paid_amount` only for paid/open-balance fields. Open balance is package or invoice amount minus paid amount.
- Finance follow-up accounts are `open_invoice` plus `proposal_only`, sorted by account name. Sponsor finance due date is event `end_date` plus `sponsor_followup_days_after_end`.

Badge and lead decisions:

- Lead due date is event `end_date` plus `followup_days_after_end`.
- Sponsor attendee means the badge company matches an active sponsor, the badge type is sponsor, or the badge contact belongs to a sponsor package. This includes proposal-only sponsors even if the badge type says attendee.
- Exclude sponsor attendees from non-sponsor lead pipeline.
- Exclude non-business badges such as student, press, academic, media, or other clearly non-commercial badge types.
- Exclude CRM accounts with `status: disqualified` or a non-null `disqualified_reason`; use `existing_disqualified`.
- Use `missing_contact` when a badge cannot produce a usable contact identity, normally no contact name plus no email/phone, or as directed by the template.
- Qualified non-sponsor lead accounts are business badges that are not active sponsors, not disqualified, and contactable. Use event `lead_opportunity_amount` per qualified account; pipeline totals are that amount times the qualified account count unless the prompt gives a different rule.

CRM actions for event leads:

- `crm_account_action`: `update_existing` when a non-disqualified CRM account is matched; otherwise `create_account`.
- `crm_contact_action`: `update_existing` when a contact is matched by normalized email/contact identity; otherwise `create_contact`.
- Campaign member action is create/add when no matching member exists, update when a matching member exists with the wrong target status, and no action when it already has the target status.
- For badge-level schemas, target status is usually `attended` for qualified non-sponsor badges, `attended_sponsor` for sponsor attendees with a badge scan, `registered_sponsor` for sponsor package contacts without attendance, and `excluded` for explicit no-import rows.
- `badge_only_contacts` means badge contacts not already represented by a CRM contact; include sponsor contacts too if the badge creates a contact.
- Count account/contact/campaign actions from the rows the template says are importable. Do not count finance follow-up as CRM account creation/update unless the schema explicitly asks.

Common event output ordering:

- Sponsor statuses by `account_name`.
- Qualified lead accounts by `account_name`.
- Excluded records by `company_name`, then `contact_name`.
- Badge decisions by `badge_id`.
- Campaign-member actions by `subject_key`.
- Account-name lists alphabetically.

## Trade-Show Prospecting

Qualify exhibitors from descriptions and the prospecting policy.

- Include companies that manufacture, build, OEM-build, or integrate target underwater platforms.
- Target platform enums are exactly `AUV`, `ROV`, and `Underwater Camera`; sort platform lists in that enum order.
- Exclude adjacent companies that do not build target platforms:
  - Distributor, reseller, dealer, sales agent only: `distributor_only`.
  - Service, consulting, analytics-only, operator, or rented-equipment service only: `service_only`.
  - Sensor/probe/component vendor with no platform build: use `sensor_vendor_only` or `sensor_only`, matching the template enum.
  - University, lab, research-only, or academic group: `research_only`.
  - Outside the campaign's target market: `not_target_market` when that enum exists.
- Preserve requested enrichment fields from exhibitors: `company_id`, `company_name`, `booth`, `country`, `website`, and any template-specific fields.
- Existing CRM overlap comes from exhibitor `crm_account_id` when present, or a CRM account name/domain match. Use `update_existing` for matched qualified exhibitors and `create_account` for unmatched qualified exhibitors. Excluded exhibitors usually use `no_import`.

Meeting interest and ranking:

- Join meeting interest by `company_name`. If a qualified exhibitor has no interest row, default `requested_demo` to false and `interest_score` to 0 unless the template says otherwise.
- If the prompt gives ranking rules, follow them exactly.
- The common robotics ranking is: demo request first, interest score descending, broader platform coverage descending, company name ascending. Assign contiguous 1-based ranks after sorting.
- Use prompt-provided opportunity sizing by tier. If unspecified but priority tiers are needed, a practical default is `A` for demo-requested score at least 90, `B` for demo-requested score at least 80, and `C` for other qualified leads.
- Platform coverage counts count platform appearances across qualified exhibitors, so a company with both ROV and Underwater Camera increments both.

Common trade-show output ordering:

- Unranked qualified exhibitors by `company_name`.
- Ranked leads by ascending `rank`.
- Excluded exhibitors or near misses by `company_name`.
- CRM overlap account IDs ascending.

## Import Batch Hygiene

Clean raw import rows into import-ready contacts.

1. Normalize email and phone for every raw row.
2. Remove unusable rows with no normalized email and no normalized phone. Use reason `missing_contact` unless the template defines a narrower unusable reason.
3. Remove suppressed rows when normalized email or phone matches the suppression endpoint, or when the matching CRM contact is opted out. Use reason `suppressed`.
4. Deduplicate the remaining rows:
   - Use duplicate key `email:{normalized_email}` when email exists.
   - Otherwise use `phone:{normalized_phone}`.
   - Pick one winner per duplicate key. Prefer higher-trust sources such as `partner_upload` and `sponsor_form` over generic forms or manual uploads; then prefer newer `captured_at`; then prefer richer contact data; then use row ID as a deterministic tie-breaker.
   - Record removed duplicate rows with reason `duplicate`.
5. Build each clean contact from the winning row's original company/contact/source/timestamp fields, but normalized email and phone.
6. Match CRM account by email domain, exhibitor/account ID when supplied, or normalized company name. Match CRM contact by normalized email.
7. Set `crm_action` to `update_existing` for a matched non-disqualified account, `create_account` for no account match, `suppress` for suppressed rows, and `no_import` for duplicates or unusable rows.

Import counts:

- `duplicate_removed_count` is the number of duplicate rows removed, not the number of duplicate groups.
- `duplicate_keys` include one object per duplicate group, sorted by key, with the winning row and removed rows sorted deterministically.
- `unusable_removed_count` counts missing-contact/no-contactable rows.
- `suppressed_removed_count` counts rows removed by suppression or opt-out.
- `import_action_totals.no_import` includes duplicate removals plus unusable removals.
- `import_action_totals.suppress` includes suppressed removals.
- `campaign_member_import_count` is the number of surviving clean contacts that will enter the campaign, usually clean contacts whose action is `create_account` or `update_existing`.

Common import output ordering:

- `clean_contacts` by `clean_contact_id`.
- `duplicate_summary.duplicate_keys` by key.
- `removal_summary.removed_rows` by `row_id`.

## Pitfalls

- Do not use current date for follow-up deadlines; use event dates and event-specific day offsets.
- Do not turn paid amount into sponsor revenue. Revenue totals use package/order amount; open balance is separate.
- Do not qualify sponsors as sales leads, including proposal-only sponsor attendees.
- Do not treat a canceled sponsor package as active sponsorship.
- Do not add `+1` to phones that lack it; normalized phone is only the digits present in the source.
- Do not infer a contact update from an account match alone; account and contact actions are separate.
- Do not count existing disqualified CRM accounts as qualified leads even when badge or meeting interest is strong.
- Do not rename enum values to nicer wording. Match the answer template exactly.
