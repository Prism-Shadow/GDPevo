---
name: task-group-001-fewshot-attempt-03
description: HarborCRM JSON-output procedures for event sponsor/lead reconciliation, tradeshow prospecting, and CRM import-batch cleanup using HarborCRM API data and answer templates. Use when a task asks Codex to produce structured JSON from HarborCRM events, sponsor packages/orders, badges, invoices, CRM accounts/contacts/opportunities, campaign members, tradeshow exhibitors/meeting interest, import batches/raw contacts/suppression, or policy metadata.
---

# HarborCRM Input/Output Skill

## Core Workflow

1. Read the user prompt and `input/payloads/answer_template.json` first.
2. Use the API base URL supplied by the runner or prompt. Fetch only the records needed for the requested `event_id`, `show_id`, or `batch_id`, plus CRM and policy lookup data.
3. Return exactly one JSON object matching the template: no prose, no extra keys, no missing required keys, exact enum spelling, integer counts/USD, and required sort order.
4. Validate the final object with `jq` or an equivalent JSON parser before answering.

Useful API paths:

- Policies: `GET /api/policies`
- Event work: `GET /api/events/{event_id}`, `/orders`, `/badges`, `/sponsor_packages`, `/api/finance/invoices?event_id={event_id}`, `/api/crm/campaign_members?event_id={event_id}`
- CRM lookups: `GET /api/crm/accounts`, `/api/crm/contacts`, `/api/crm/opportunities`
- Tradeshow work: `GET /api/tradeshows`, `/api/tradeshows/{show_id}/exhibitors`, `/api/tradeshows/{show_id}/meeting_interest`
- Import batches: `GET /api/import_batches`, `/api/import_batches/{batch_id}/raw_contacts`, `/api/import_batches/{batch_id}/suppression`

## Normalization

- Normalize emails by trimming whitespace and lowercasing. Use `""` when no email is supplied and the template expects a string.
- Normalize phones to digits only. Use `""` when no phone is supplied and the template expects a string.
- Match accounts by explicit `account_id`/`crm_account_id` first, then normalized company name, then email/website domain when names vary.
- Treat CRM accounts with `status: "disqualified"` or a `disqualified_reason` as excluded; do not update or import them as qualified leads.
- Match contacts by normalized email first, then phone/name under the matched account. An existing account does not imply an existing contact.
- Compute event due dates as `event.end_date + followup_days_after_end` or `event.end_date + sponsor_followup_days_after_end`, formatted `YYYY-MM-DD`.

## Event Sponsor And Lead Reconciliation

Use event details, sponsor orders/packages, invoices, badges, CRM records, and campaign members together.

Sponsor statuses:

- Treat `confirmed` and `proposal_sent` sponsor orders as active. Exclude `canceled` or inactive orders from active sponsor status lists.
- `paid_deferred`: active sponsor with a paid/deferred invoice or fully paid invoice. Use the order/package amount as revenue, include invoice fields when the template asks.
- `open_invoice`: active sponsor with an open invoice or unpaid balance. Use full order/package amount for sponsor revenue totals and separately calculate `open_balance = invoice.amount - invoice.paid_amount`.
- `proposal_only`: active proposal sponsor without an invoice. Use the order/package amount, `invoice_id: null`, and zero paid/open invoice balance unless the template asks for unpaid proposal total.
- Finance follow-up targets are `open_invoice` plus `proposal_only` sponsors. Count one task per account. If an unpaid total is requested, use open invoice balances plus proposal amounts.
- `sponsor_packages` can mirror `orders`; do not double count if both endpoints return the same records.

Badge and lead decisions:

- Active sponsor contacts include sponsor badge scans, active sponsor order `ticket_contacts`, badges whose company matches an active sponsor account, and existing sponsor campaign members.
- Exclude active sponsor contacts from non-sponsor leads with `sponsor_attendee`, but still create/update contact or campaign-member work for them when the template asks for badge-level handling.
- Exclude non-business badge types such as `student` and `press` with `non_business_badge`.
- Exclude matched CRM disqualified accounts with `existing_disqualified`; this takes precedence over inactive/canceled sponsor history.
- Use `inactive_sponsor_record` only when a record is tied to an inactive/canceled sponsor and no stronger exclusion applies.
- Qualified non-sponsor leads are business attendees that are not active sponsors, not disqualified, and have usable contact/company facts. Use the event `lead_opportunity_amount` for each qualified account.
- Account action is `update_existing` when a non-disqualified account exists; otherwise `create_account`. Contact action is `update_existing` only when the person already exists; otherwise `create_contact`.

Campaign-member handling:

- Existing campaign member at the desired status is `no_action`.
- Sponsor target statuses are usually `attended_sponsor` for sponsor badge attendance and `registered_sponsor` for sponsor records without attendance.
- Qualified non-sponsor badge attendance usually targets `attended`.
- If both `account_id` and `contact_id` are known, use subject keys like `account_id:contact_id` when requested. If a contact must be created from a badge, use `badge:{badge_id}`.
- Badge-level exclusion counts count badge decisions, not every sponsor order contact, unless the template defines them differently.

Common event output fields:

- `sponsor_statuses`: active sponsor accounts sorted by `account_name`; amounts are integer USD.
- `sponsor_revenue_totals`: sum sponsor package/order amounts by controlled status; keep open invoice balance separate.
- `qualified_lead_accounts`: one row per qualified non-sponsor account, sorted as the template requires.
- `lead_pipeline_total` or `open_opportunity_total_usd`: number of qualified non-sponsor accounts times the event lead opportunity amount unless the prompt provides another sizing rule.
- `excluded_records`/`badge_decisions`: use controlled reasons only.
- `crm_action_counts`: count the CRM work implied by imported lead/contact/campaign-member decisions, not excluded no-op records.

## Tradeshow Prospecting

Use show metadata, exhibitors, meeting interest, CRM accounts, and policies.

Qualification:

- Qualify exhibitors that build, manufacture, design, or OEM-integrate target platforms from the policy enum: `AUV`, `ROV`, `Underwater Camera`.
- Exclude adjacent companies that do not build target platforms:
  - distributor/dealer/reseller only: `distributor_only`
  - consulting, service, operations, analytics, or rented-equipment service only: `service_only`
  - sensor/probe-only vendor: use the template enum, commonly `sensor_vendor_only` or `sensor_only`
  - research/lab only: `research_only`
  - unrelated market: `not_target_market` when allowed
- Sort each lead's `platforms` in policy enum order: `AUV`, `ROV`, `Underwater Camera`.

Interest, priority, and sizing:

- Join meeting interest by company name. If no record exists, use `requested_demo: false` and a zero/blank score only if the template needs those fields.
- Use prompt-specified priority and opportunity rules whenever provided.
- Learned default when no other rule is supplied: demo requested with score >= 90 is tier `A`; demo requested with score >= 80 is tier `B`; all other qualified leads are tier `C`.
- When tier opportunity amounts are supplied, assign per tier and sum integer USD.

CRM and counts:

- Use exhibitor `crm_account_id` or CRM account matching for overlap. Existing non-disqualified accounts get `update_existing`; new qualified exhibitors get `create_account`; excluded exhibitors get `no_import`.
- `platform_counts` count each qualified exhibitor once per covered platform, so a multi-platform exhibitor increments multiple platform counters.
- Include all required count buckets, even when the value is zero.
- If the prompt asks for ranking, sort demo requests first, then interest score descending, then broader platform coverage, then company name ascending, and assign contiguous 1-based ranks. Otherwise follow the template's sort rule, often company name ascending.

## Import Batch Cleanup

Use batch metadata, raw contacts, suppression records, CRM accounts, CRM contacts, and policies.

Cleaning order:

1. Normalize email and phone for every raw row.
2. Remove unusable rows with neither normalized email nor normalized phone as `missing_contact`.
3. Remove suppressed rows when normalized email or phone matches the suppression endpoint, or when a matched CRM contact is opted out. Count these as `suppress`.
4. Deduplicate remaining contactable rows.
5. Produce clean contacts only for dedupe winners that survive suppression.

Dedupe:

- Prefer duplicate key `email:{normalized_email}` when email exists; otherwise use `phone:{normalized_phone}`.
- Choose the winning row by higher-confidence source, then newest `captured_at`, then deterministic `row_id`. Source confidence learned from examples: `sponsor_form`/`partner_upload`/`exhibitor_form` outrank `webinar_form`/`badge_scan`, which outrank `manual_upload`.
- `clean_contact_id` and `source_row_id` should both be the winning row id unless the template instructs otherwise.
- Keep the winning row's company name, contact name, source, and timestamp; do not silently replace display values with CRM canonical names.

Import actions and summaries:

- Clean winner with existing non-disqualified account: `update_existing`.
- Clean winner without an existing account: `create_account`.
- Duplicate removals and missing-contact removals count as `no_import`.
- Suppressed removals count as `suppress`.
- `import_action_totals` counts all raw rows by final action, not just clean contacts.
- `campaign_member_import_count` counts surviving clean contacts that will be imported as campaign members.
- Sort clean contacts, duplicate keys, and removed rows exactly as the template specifies.

## Pitfalls

- Follow the answer template over habit: field names vary (`sponsor_status` vs `status`, `add_campaign_member` vs `create`, `sensor_vendor_only` vs `sensor_only`).
- Use full sponsor package/order amount for sponsor revenue by status; keep unpaid balances in separate fields.
- Proposal-only sponsors have no invoice but still require sponsor finance follow-up.
- Canceled sponsor orders are not active sponsors.
- Active sponsor order contacts may need to appear in exclusions even if they did not scan a badge.
- Existing account overlap does not mean existing contact overlap.
- Do not import or update disqualified CRM accounts as qualified leads.
- Do not let a high meeting-interest score qualify a distributor, service provider, sensor-only vendor, or research-only exhibitor.
- Sort at the end after all inclusion/exclusion decisions are final.
