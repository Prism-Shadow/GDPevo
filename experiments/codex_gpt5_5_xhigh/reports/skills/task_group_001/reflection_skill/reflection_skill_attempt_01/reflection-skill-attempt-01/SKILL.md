---
name: reflection-skill-attempt-01
description: HarborCRM workflow SOPs for generating exact JSON handoffs from the shared API. Use for HarborCRM event sponsor/lead reconciliation, trade-show prospecting, CRM import-batch cleanup, campaign-member decisions, sponsor finance follow-up, and answer-template-constrained outputs.
---

# HarborCRM Workflow SOP

## Core Workflow

1. Read only the task prompt and its answer template. Shape the response exactly to the template: required keys only, controlled enum values only, sorted lists as specified, integer USD/counts, and no prose outside JSON.
2. Use the supplied base URL. Check `/health` only if needed, then fetch the public records named by the prompt.
3. Join records with explicit IDs first, then exact company/account names, then normalized domains or normalized contact facts. Use `/api/policies` for controlled values and qualification intent.
4. Build the JSON from the template outward. Keep nulls, empty strings, and field names exactly as the template describes.
5. Recheck every aggregate from the emitted detail rows. Counts and totals should be derivable from the same rows in the answer.

Common public endpoints:

- Events: `/api/events/{event_id}`, `/api/events/{event_id}/orders`, `/api/events/{event_id}/badges`, `/api/events/{event_id}/sponsor_packages`, `/api/finance/invoices?event_id={event_id}`, `/api/crm/campaign_members?event_id={event_id}`
- CRM: `/api/crm/accounts`, `/api/crm/contacts`, `/api/crm/opportunities`
- Trade shows: `/api/tradeshows`, `/api/tradeshows/{show_id}/exhibitors`, `/api/tradeshows/{show_id}/meeting_interest`
- Import batches: `/api/import_batches`, `/api/import_batches/{batch_id}/raw_contacts`, `/api/import_batches/{batch_id}/suppression`
- Policies: `/api/policies`

## Normalization and Matching

- Normalize email by trimming and lowercasing.
- For event badge/lead outputs, normalize phone by stripping non-digits only. Do not add a leading country code that was not present.
- For import-batch hygiene, normalize US phones for matching by stripping non-digits and prefixing `1` to 10-digit US numbers. Use that normalized value in clean import rows, duplicate detection, suppression matching, and CRM contact matching.
- Match CRM accounts by supplied `crm_account_id`, exact account/company name, or email/website domain. Existing non-disqualified accounts use `update_existing`; missing accounts use `create_account`; disqualified accounts are excluded or `no_import`.
- Match contacts by normalized email first, then same-account normalized phone/name when email is missing. Opted-out or suppression-listed contacts must not be imported.

## Event Sponsor and Lead Handoffs

Sponsor status:

- Use event orders or sponsor packages as sponsor source rows. They may duplicate each other; do not double count.
- Skip canceled/inactive sponsor orders in active sponsor status lists unless the template explicitly asks for inactive records.
- `confirmed` plus invoice `paid_deferred` becomes `paid_deferred`.
- `confirmed` plus an open/unpaid invoice becomes `open_invoice`; `open_balance = invoice.amount - paid_amount`.
- `proposal_sent` with no invoice becomes `proposal_only`.
- Revenue totals sum package/order amounts by sponsor status. Track open invoice balance separately when requested.

Lead qualification:

- Qualified non-sponsor leads are business badge attendees that are contactable, not sponsor/proposal sponsor attendees, not non-business badges, and not tied to disqualified CRM accounts.
- Use the event `lead_opportunity_amount` for each qualified non-sponsor account unless the prompt gives another sizing rule.
- Lead follow-up due date is `event.end_date + followup_days_after_end`. Sponsor follow-up due date is `event.end_date + sponsor_followup_days_after_end`.
- Lead task count is the number of qualified lead accounts. Sponsor finance task count/accounts include both `open_invoice` and `proposal_only` sponsor accounts.

Exclusions:

- Treat sponsor order `ticket_contacts` as sponsor attendees even when no badge scan exists.
- Treat proposal-only sponsor attendees as sponsor attendees for exclusion from lead pipeline.
- Non-business badge types include `student`, `press`, and similar non-buyer records.
- If a record is both canceled/inactive sponsor-related and matched to a disqualified CRM account, prefer `existing_disqualified` when that enum is available.
- Sort exclusions exactly as requested, often by company then contact.

Campaign-member decisions:

- Existing campaign-member subject keys use `<account_id>:<contact_id>`.
- Badge-created campaign-member subject keys use `badge:<badge_id>`.
- Include existing sponsor campaign members even if the sponsor contact has no badge scan; normally this is `no_action` with the current sponsor target status.
- Create campaign members for qualified non-sponsor attended badges with target `attended`.
- Create campaign members for sponsor/proposal sponsor attendees when the template asks for detailed event reconciliation and the contact/member does not already exist; target `attended_sponsor`.
- Use `no_import` only for true non-import exclusions such as non-business or missing-contact records, not merely because a record is sponsor-related.

Useful event output fields:

- `sponsor_statuses`: one row per active sponsor/proposal sponsor account, sorted by account name.
- `qualified_lead_accounts`: one row per qualified non-sponsor account; include normalized contact facts, CRM create/update decisions, campaign-member action, and opportunity amount.
- `badge_decisions`: one row per badge, sorted by badge ID; classification and CRM action should agree.
- `campaign_member_actions`: include existing relevant members and create/update work implied by badges.
- `opportunity_summary` or `lead_pipeline_total`: sum only qualified non-sponsor opportunities.
- `sponsor_followup` or `follow_up.sponsor_finance_accounts`: include open-invoice and proposal-only sponsors.
- `crm_action_counts`: count the account/contact/campaign-member create/update work implied by qualified handoff rows.

## Trade-Show Prospecting

Qualification:

- Qualify exhibitors that build, manufacture, or OEM-integrate covered platforms. Covered platform enums are usually `AUV`, `ROV`, and `Underwater Camera`.
- Exclude adjacent companies that are distributor/reseller only, service/consulting/analytics only, sensor vendor only, research only, or outside the target market.
- Existing CRM overlap comes from `crm_account_id` or a confident CRM account match. Qualified existing accounts use `update_existing`; qualified new companies use `create_account`; excluded companies use `no_import`.

Classification:

- Derive `platforms` from exhibitor descriptions and sort them in policy/template enum order.
- Count a qualified exhibitor once per covered platform it supports.
- When priority is based on meeting interest and no different rule is given: `A` for requested demo with score at least 90, `B` for requested demo with score at least 80, and `C` otherwise.
- When ranking is requested, follow the prompt order exactly. A common ranking is requested demo first, interest score descending, broader platform coverage, then company name.
- Use opportunity sizes from the prompt. Do not invent opportunity amounts for templates that only ask for tiers and counts.

Useful trade-show fields:

- `qualified_exhibitors` or `ranked_leads`: include company ID/name, booth, country, website, sorted platforms, priority, CRM action/ID when requested, interest facts, and opportunity estimate when requested.
- `excluded_near_misses` or `excluded_exhibitors`: keep excluded adjacent companies visible with controlled reasons.
- `aggregate_counts` or `summary`: reconcile qualified total, excluded total, platform counts, priority counts, CRM overlap, and total estimated opportunity.

## Import-Batch Cleanup

Fetch the batch metadata, raw contacts, suppression list, CRM accounts, CRM contacts, and policies.

Cleaning rules:

- Remove rows with no usable contact method after normalization as `missing_contact`.
- Remove rows matching suppression by normalized email or normalized phone as `suppressed`.
- Detect duplicates with a prefixed key: `email:<normalized email>` when email exists, otherwise `phone:<normalized phone>`.
- Pick duplicate winners by latest `captured_at`. If timestamps tie, prefer more authoritative supplied sources such as `partner_upload` over form/webinar rows, then use row ID as a final deterministic tie-breaker.
- `clean_contact_id` and `source_row_id` should be the winning source row ID.
- Preserve the winning row's company/contact/source/captured fields, with normalized email and phone.

Import actions and totals:

- Clean rows matched to active CRM accounts use `update_existing`; unmatched clean rows use `create_account`.
- Suppressed rows are removed and counted as `suppress`.
- Duplicate and missing-contact removals are counted as `no_import`.
- `import_action_totals` should count both clean rows and removed rows: clean create/update actions, duplicate/missing rows as `no_import`, and suppressed rows as `suppress`.
- `campaign_member_import_count` is the count of surviving clean rows that should be imported as campaign members.

Useful import fields:

- `clean_contacts`: sort by `clean_contact_id`; include normalized contact facts, winning source metadata, CRM action, and existing IDs or nulls.
- `duplicate_summary.duplicate_keys`: sort by key; include prefixed key, winner row, and removed rows.
- `removal_summary.removed_rows`: sort by row ID; reasons are usually `duplicate`, `missing_contact`, or `suppressed`.

## Pitfalls

- Do not ignore sponsor ticket contacts just because they are not badge scans.
- Do not drop proposal-only sponsors from finance follow-up or sponsor attendee handling.
- Do not apply import-phone country-code normalization to event badge phone fields.
- Do not omit the `email:` or `phone:` prefix in duplicate keys when the template expects duplicate key strings.
- Do not compute import action totals from clean rows only.
- Do not include extra fields from API records just because they are available.
- Do not solve by prose: the final answer for HarborCRM tasks is usually one JSON object only.
