---
name: demonstration-skill-attempt-02
description: HarborCRM JSON handoff procedures for tasks that ask Codex to use HarborCRM API data and an answer template to prepare event sponsor reconciliation, badge and campaign-member handoffs, trade-show prospecting summaries, or CRM import batch cleanup. Use when outputs must be JSON-only, template-shaped, policy-aware, sorted, normalized, and reconciled against HarborCRM accounts, contacts, opportunities, invoices, campaign members, exhibitors, or suppression records.
---

# HarborCRM JSON Handoffs

## Core Workflow

1. Read the user prompt and the provided `input/payloads/answer_template.json` first. Treat the template as the output contract: required keys, field names, enum spellings, sorting, numeric precision, and whether explanatory prose is forbidden.
2. Use the API base URL supplied by the runner. If a prompt gives a local default, use it only for local verification. Start with `/health` only to verify service availability when needed.
3. Fetch only endpoints relevant to the entity IDs in the prompt. Join API records in memory; do not infer from filenames or previous answers.
4. Normalize contacts before matching or emitting: email is trimmed and lowercased; phone is digits only; absent email or phone becomes `""` when the template wants a string and `null` only when the template says nullable.
5. Match CRM entities conservatively:
   - Prefer explicit `account_id`, `contact_id`, `crm_account_id`, `event_id`, `show_id`, and `batch_id`.
   - Otherwise match accounts by exact normalized name, domain from email or website, or obvious company alias only when supported by the API data.
   - Match contacts by normalized email first, then account plus exact contact name.
6. Calculate all totals from the emitted records, not from raw source counts. Use integer USD and integer counts.
7. Apply every ordering rule from the template at the end. If the template is silent, use deterministic alphabetical or ID order matching nearby examples.
8. Return one JSON object only. Do not add fields that are not declared by the template.

## API Map

Use these endpoint families as needed:

- Events: `/api/events/{event_id}`, `/api/events/{event_id}/orders`, `/api/events/{event_id}/badges`, `/api/events/{event_id}/sponsor_packages`
- Finance: `/api/finance/invoices?event_id={event_id}`
- CRM: `/api/crm/accounts`, `/api/crm/contacts`, `/api/crm/opportunities`, `/api/crm/campaign_members?event_id={event_id}`
- Trade shows: `/api/tradeshows`, `/api/tradeshows/{show_id}/exhibitors`, `/api/tradeshows/{show_id}/meeting_interest`
- Import batches: `/api/import_batches`, `/api/import_batches/{batch_id}/raw_contacts`, `/api/import_batches/{batch_id}/suppression`
- Policies: `/api/policies`

Policy enums observed in HarborCRM:

- Sponsor statuses: `paid_deferred`, `open_invoice`, `proposal_only`, `not_sponsor`
- Prospecting platforms, in output order: `AUV`, `ROV`, `Underwater Camera`

## Event Sponsor And Badge Handoffs

Fetch the event, orders or sponsor packages, invoices, badges, CRM accounts, contacts, opportunities, campaign members, and policies.

Sponsor status rules:

- Include active sponsor orders such as `confirmed` and `proposal_sent`; exclude canceled or inactive sponsor records unless the template explicitly asks to list exclusions.
- `paid_deferred`: an active sponsor has an invoice whose status is `paid_deferred`, or invoice paid amount covers the package amount.
- `open_invoice`: an active confirmed sponsor has an open invoice or a positive open balance.
- `proposal_only`: an active proposal has no invoice yet.
- Use the order or package amount as `package_amount` or `amount_usd`. For invoice-aware schemas, emit `invoice_id`, `paid_amount`, and `open_balance = amount - paid_amount`.
- Sponsor revenue totals sum package amounts by sponsor status. `open_invoice_balance` is a separate sum of unpaid balances, not a replacement for open invoice revenue.
- Sponsor finance follow-up targets are the unpaid or not-yet-invoiced sponsor accounts: `open_invoice` plus `proposal_only`. Paid-deferred sponsors do not need finance follow-up.

Date and task rules:

- Lead due date is `event.end_date + event.followup_days_after_end`.
- Sponsor finance due date is `event.end_date + event.sponsor_followup_days_after_end`.
- Lead task count is usually the number of qualified non-sponsor lead accounts.
- Sponsor finance task count is usually the number of sponsor finance follow-up accounts.

Badge classification:

- `sponsor_attendee`: badge type is sponsor, or the badge company matches an active sponsor order, including proposal-only sponsors. Sponsor attendees are excluded from non-sponsor lead pipeline.
- `qualified_non_sponsor_lead`: business attendee, not a sponsor, not a disqualified CRM account, and contactable.
- `excluded`: non-business badge, disqualified CRM account, missing usable contact facts, or another template-listed exclusion.
- Treat badge types such as `student` and `press` as `non_business_badge`.
- Treat CRM accounts with `status: disqualified` or non-null `disqualified_reason` as `existing_disqualified`.
- Use `missing_contact` when the record cannot support a CRM contact or campaign member, especially no normalized email and no normalized phone.

Lead and CRM action rules:

- For qualified non-sponsor accounts, use `event.lead_opportunity_amount` for each account and compute pipeline total as count times that amount.
- Existing CRM account means `update_existing`; missing account means `create_account`.
- Existing CRM contact means `update_existing` or campaign-only action; missing contact means create contact.
- Existing campaign member at the desired target status is `no_action`; existing member needing a status change is `update`; missing member is `create` or `add_campaign_member`, using the enum required by the template.
- For sponsor attendees, do not count them as leads, but still create contact or campaign-member work when the template asks for badge-level or campaign-member actions.
- `badge_only_contacts` should include badge-sourced contacts that need normalized contact facts for import, including qualified non-sponsor badge contacts and sponsor attendees that are not already represented as CRM contacts.
- Exclusion counts count classified reasons, including sponsor attendees when the template has a `sponsor_attendee` bucket.

Common event output fields:

- `sponsor_statuses`: sorted by `account_name`; include account identity, controlled status, amount, and invoice facts when requested.
- `qualified_lead_accounts` or `opportunity_summary`: sorted as requested; include account/contact actions, normalized contact facts, and event-level opportunity amount.
- `excluded_records` or `badge_decisions`: sort by template rule; use only allowed exclusion reason enums.
- `campaign_member_actions`: sort by `subject_key`; use target statuses such as `attended`, `attended_sponsor`, `registered_sponsor`, or `excluded` only if allowed.
- `crm_action_counts`: count only the CRM work implied by the specified handoff. In lead-only summaries, do not count sponsor finance follow-up as CRM action work.

## Trade-Show Prospecting

Fetch the show list, the show exhibitors, meeting interest, CRM accounts, contacts if needed, and policies. Join meeting interest by exact `company_name` unless a stronger ID is available.

Qualification rules:

- Qualify exhibitors that build, manufacture, design, or OEM-integrate target platforms.
- Extract platform coverage from description and campaign context:
  - `AUV`: AUVs, autonomous underwater vehicles, underwater drones or scouts.
  - `ROV`: ROVs, inspection robots, pen-cleaning ROVs.
  - `Underwater Camera`: underwater camera modules, camera arrays, optics or camera OEMs.
- Do not qualify adjacent companies that do not build target platforms.
- Use controlled exclusion reasons from the template:
  - Distributor, reseller, dealer, sales agent only: `distributor_only`
  - Services, consulting, operating rented vehicles, analytics dashboard without hardware manufacturing: `service_only`
  - Sensor-only vendor or probe maker without platform manufacturing: `sensor_vendor_only` or `sensor_only`, matching the template enum
  - Research or lab-only organization: `research_only`
  - Outside the campaign market: `not_target_market` when allowed

Ranking and prioritization:

- Sort platforms in enum order: `AUV`, `ROV`, `Underwater Camera`.
- Count each platform membership independently; a company covering two platforms increments both counts.
- Existing CRM overlap comes from exhibitor `crm_account_id` or a confident CRM account match. Sort overlap account IDs ascending.
- `crm_action` is `update_existing` for existing CRM accounts, `create_account` for new qualified accounts, and `no_import` for excluded exhibitors when requested.
- If the prompt defines ranking, follow it exactly. A common ranking is requested demo first, then meeting interest score descending, then broader platform coverage, then company name ascending.
- If the prompt defines tier amounts, use them exactly. A common pattern is A for demo requested with score at least 90, B for demo requested with score at least 80, and C otherwise; opportunity estimates then come from the prompt's tier amounts.
- If no ranking field is present, sort qualified and excluded exhibitors by `company_name` ascending.

Common trade-show output fields:

- `qualified_exhibitors`: company identity, sorted platforms, priority tier, booth, country, website.
- `ranked_leads`: contiguous 1-based rank plus CRM action, requested demo, interest score, priority tier, and opportunity estimate.
- `excluded_near_misses` or `excluded_exhibitors`: keep visible exclusions sorted by company name with the template's reason enum.
- `aggregate_counts` or `summary`: derive qualified totals, platform counts, priority counts, exclusion counts, CRM overlap counts, and total estimated opportunity from emitted lead rows.

## Import Batch Cleanup

Fetch `/api/import_batches`, the batch raw contacts, the batch suppression list, CRM accounts, CRM contacts, and policies.

Cleaning order:

1. Normalize email and phone on every raw row.
2. Remove suppressed rows when normalized email or normalized phone matches a suppression record. Count them as `suppress` and use removal reason `suppressed`.
3. Remove unusable rows when no usable contact channel remains, usually both normalized email and normalized phone are empty. Use removal reason `missing_contact`.
4. Dedupe the remaining contactable rows. Prefer duplicate key `email:{normalized_email}` when email exists, otherwise `phone:{normalized_phone}`.
5. Choose one winner per duplicate key. If the prompt or policy does not define precedence, prefer higher-signal sources, then latest `captured_at`, then a deterministic row-id tie-break. Observed high-signal sources include `sponsor_form`, `partner_upload`, `badge_scan`, `exhibitor_form`, then `webinar_form`, then `manual_upload`.
6. Emit only winners as clean contacts. Use the winning `row_id` as both `clean_contact_id` and `source_row_id` when the template asks for that convention.

Import action rules:

- `update_existing`: the surviving row matches an existing CRM account.
- `create_account`: no CRM account match exists.
- `no_import`: duplicate removals and unusable removals.
- `suppress`: suppression removals.
- Existing contact ID is non-null only when the normalized email or account plus contact name matches an existing CRM contact that is not merely an opted-out or suppressed person.
- Campaign member import count is the number of surviving clean contacts that should be imported as campaign members.

Common import output fields:

- `clean_contacts`: sort by `clean_contact_id`; include normalized email and phone, source facts from the winning row, CRM action, and existing IDs.
- `duplicate_summary`: sort duplicate keys by key; each item includes key, winner row, and removed row IDs.
- `removal_summary`: sort removed rows by `row_id`; counts separate unusable, suppressed, and duplicates if the template asks.
- `import_action_totals`: count every raw row into exactly one bucket: clean create/update, duplicate or unusable no-import, or suppress.

## Pitfalls

- Do not treat a canceled sponsor package as an active sponsor, even if the account appears in badges.
- Do not let sponsor attendees enter non-sponsor lead totals.
- Do not mark a sponsor as paid just because an invoice exists; compare status and open balance.
- Do not use paid amount as sponsor revenue; revenue totals use package or order amount.
- Do not drop qualified badge contacts just because email is blank when a phone is present.
- Do not overwrite a template enum with a similar enum from another task, especially `sensor_vendor_only` versus `sensor_only`.
- Do not count multi-platform exhibitors as one platform hit; count each platform separately.
- Do not include extra commentary outside the final JSON, even a short note.
