---
name: harborcrm-json-handoff
description: Solve HarborCRM API tasks that ask Codex to produce CRM-ready JSON handoffs from event, trade-show, sponsor, finance, badge, import-batch, CRM account, contact, campaign-member, policy, or meeting-interest data. Use when a prompt references HarborCRM, answer_template.json, CRM import cleanup, event sponsor or badge reconciliation, trade-show prospect qualification, duplicate or suppression handling, lead handoff, or campaign-member action summaries.
---

# HarborCRM JSON Handoff

## Core Workflow

1. Read the user prompt and `input/payloads/answer_template.json` first. Treat the template as the response contract: preserve required top-level keys, field names, enum spellings, `null` versus empty string conventions, integer currency/counts, and sorting rules. Return one JSON object only.
2. Query the runner-provided HarborCRM base URL. Use the endpoint list from the prompt or environment-access file; if a route is unavailable, continue with the available related routes and do not invent records.
3. Build normalized lookup tables before reasoning:
   - Accounts by `account_id`, normalized company name, and domain.
   - Contacts by `contact_id`, normalized email, digits-only phone, and account plus normalized contact name.
   - Opportunities by event/show/account when those fields exist.
   - Campaign members by event/campaign plus account/contact pair.
   - Event sponsors, orders, packages, invoices, badges, exhibitors, meeting-interest rows, raw import rows, and suppression rows by their natural IDs plus normalized company/contact keys.
4. Prefer explicit policy records and prompt-specific rules over defaults. Use defaults below only when the task asks for the same HarborCRM pattern and no policy field overrides it.
5. Assemble the JSON directly from derived facts, then validate it against the template: no prose, no undeclared fields, sorted arrays, exact enum values, and complete aggregate totals.

Use `scripts/harborcrm_helpers.py` when useful for portable normalization, platform classification, default exclusion classification, due-date arithmetic, and import dedupe tie-breaking.

## Normalization

- Normalize email as trimmed lowercase. Use `""` for missing email when the template expects a string.
- Normalize phone as digits only, preserving country code digits if supplied. Use `""` for missing phone when the template expects a string.
- Normalize company/contact names for matching by lowercasing, removing punctuation, collapsing whitespace, and stripping common company suffix noise only for lookup. Preserve display names from the source record chosen for output.
- Match existing CRM accounts by explicit `crm_account_id` first, then account ID from joins, then domain, then strong normalized company-name match. Do not match to accounts whose CRM status or disqualification fields make them ineligible unless the schema asks to report an exclusion.
- Match existing contacts by explicit `contact_id` first, then normalized email, then phone, then account plus normalized contact name. Treat opted-out contacts or suppression matches as suppression/removal when the task is an import-cleaning workflow.

## Event And Badge Reconciliation

- Compute lead follow-up due dates as event `end_date` plus `followup_days_after_end`; compute sponsor finance due dates as `end_date` plus `sponsor_followup_days_after_end`.
- Consider only active sponsor/order/package rows for sponsor status. Ignore canceled or inactive sponsor records except when the template asks for excluded records.
- Classify sponsor finance status with the template's enum:
  - `paid_deferred`: sponsor has a package/order amount and the invoice/payment state is fully paid, closed-won, or otherwise not currently collectible.
  - `open_invoice`: sponsor has an invoice or receivable with positive unpaid balance. Count full package/order amount in open-invoice revenue and the unpaid portion in open balance.
  - `proposal_only`: sponsor has a sponsor package/order/proposal amount but no invoice/payment record yet.
  - `not_sponsor`: use only when the schema explicitly asks to classify non-sponsors in a sponsor-status list.
- Sponsor finance follow-up targets are unpaid sponsor accounts: `open_invoice` plus `proposal_only`, sorted as requested. Paid/deferred accounts are not finance follow-up targets.
- Classify badge rows:
  - `sponsor_attendee` when the badge account/company belongs to an active sponsor.
  - `qualified_non_sponsor_lead` when the badge is business-eligible, not a sponsor, not suppressed, not missing usable contact facts, and not matched to a disqualified CRM account.
  - `excluded` for non-business badges, existing disqualified accounts, missing usable contact, inactive sponsor rows when requested, or other controlled exclusion reasons in the template.
- Non-business badges include student, academic/research-only, press/media, personal, vendor/service-only, and other badge types that the prompt or policy excludes from sales handoff.
- For qualified non-sponsor leads, use the event's `lead_opportunity_amount` per qualified account unless the prompt gives a different sizing rule. Opportunity totals are that amount times the number of qualified non-sponsor accounts.
- Campaign-member actions should reflect the actual CRM state:
  - Existing correct member/status: `no_action`.
  - Existing member requiring status change: `update` or template-specific update enum.
  - Missing member for existing account/contact: create/add campaign member.
  - New contact under existing account: create contact plus campaign member.
  - New account/contact: create account, contact, and campaign member.
  - Excluded rows: `no_import` when the schema wants an action row; omit them when the schema only wants importable campaign-member actions.
- Badge-only contact lists mean badge-derived contacts without an existing CRM contact. Include new sponsor contacts as well as non-sponsor leads when the schema wording is broad; exclude existing CRM contacts and excluded badges.

## Trade-Show Prospecting

- Join exhibitors with meeting-interest rows by `company_id` when present, otherwise normalized `company_name`.
- Determine platform coverage from exhibitor descriptions, notes, policy tags, and prompt wording. Emit platforms only from the template's allowed order, typically `AUV`, `ROV`, `Underwater Camera`.
- Qualify exhibitors that manufacture, OEM-build, or embed target platform hardware relevant to the campaign. Do not qualify pure distributors/resellers, service operators/consultancies, sensor-only vendors, research-only organizations, analytics-only companies with no platform hardware, or exhibitors outside the target market.
- Map common exclusions to the template's enum spellings:
  - Distributor/reseller only: `distributor_only`.
  - Service/operator/consulting only: `service_only`.
  - Sensor-only vendor: use `sensor_vendor_only` or `sensor_only`, matching the template.
  - Research/academic only: `research_only`.
  - Outside campaign target: `not_target_market` when available.
- Mark CRM overlap from exhibitor `crm_account_id`, account-domain match, or strong company-name match. Qualified exhibitors with overlap usually use `update_existing`; new qualified exhibitors use `create_account`; excluded exhibitors use `no_import` if the schema has an action field.
- Use prompt-specific ranking and opportunity sizing exactly when supplied. If no ranking rule is supplied, sort by the template. If no tier policy is supplied, default to: `A` for requested-demo interest with score at least 90, `B` for requested-demo interest with score at least 80, and `C` for other qualified exhibitors.
- Platform counts count membership, not exclusive companies: a company with two platforms increments both platform totals.

## Import Batch Cleanup

- Fetch batch metadata, raw contacts, suppression rows, CRM accounts, CRM contacts, and policies when available.
- Normalize each raw row's email and phone before suppression and dedupe checks.
- Remove unusable rows with no usable email and no usable phone as `missing_contact`, even if a display contact name exists.
- Remove suppressed rows when normalized email or phone matches suppression records, opted-out CRM contacts, or policy-defined suppression criteria. Count them under the suppression action/summary fields, not as duplicates.
- Dedupe remaining usable, non-suppressed rows by normalized email when present; otherwise by normalized phone. Emit duplicate keys with `email:` or `phone:` prefixes when the template asks for them.
- Choose the winning duplicate row by explicit policy/source priority if present. Otherwise use this stable fallback: higher source trust, latest `captured_at`, then lexicographically greatest `row_id`. Default source trust from highest to lowest is `sponsor_form`, `partner_upload`, `exhibitor_form`, `badge_scan`, `webinar_form`, `manual_upload`.
- For each surviving clean row, choose CRM action from account/contact lookup:
  - Existing eligible account: `update_existing`.
  - No eligible account: `create_account`.
  - Existing ineligible or suppressed contact: use the template's no-import/suppress path.
- Import action totals are across original raw rows: clean surviving rows count by their CRM action, duplicate and missing-contact removals count as `no_import`, and suppression removals count as `suppress`. Campaign-member import count is the number of surviving clean contacts that should be imported into the batch campaign.

## Final Checks

- Re-read the template after deriving the answer and remove any fields the schema did not declare.
- Use exact enum spelling from the current template, even when similar examples use different spellings.
- Sort every list by the explicit template rule. For ranked lists, assign contiguous 1-based ranks after sorting by the requested criteria.
- Sum amounts and counts from the rows actually emitted or intentionally classified; do not double-count duplicate companies unless the schema counts platform memberships.
- Do not copy example answer values into new tasks. Use the live task's prompt, template, API data, and policies.
