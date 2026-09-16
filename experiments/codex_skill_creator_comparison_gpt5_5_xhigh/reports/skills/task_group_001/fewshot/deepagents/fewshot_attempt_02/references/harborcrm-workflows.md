# HarborCRM Workflows

Use these rules after reading the user prompt, answer template, and live API
payloads. Treat the prompt and template as higher priority than these defaults.

## Shared Normalization

- Normalize email as trimmed lowercase. Use an empty string when no email is supplied and the schema expects a string.
- Normalize phone as digits only. Preserve country/area digits; do not format with punctuation.
- Match accounts by explicit `account_id`/`crm_account_id` first, then normalized exact company name, then domain from email/website when available.
- Match contacts by `contact_id` first, then normalized email, then normalized phone, then account plus contact name.
- Treat CRM accounts with `status` equal to `disqualified` or a non-empty `disqualified_reason` as excluded unless the prompt explicitly asks to report them.
- Use `null` only when the template allows null. Use empty strings for missing normalized email/phone fields declared as strings.
- Do all currency math in integer USD. Do all counts from the records that survive the relevant filters.

## Event Handoff and Sponsor Reconciliation

Fetch the event record, badge scans, sponsor/order/package records, finance
invoices when available, and shared CRM accounts, contacts, opportunities,
campaign members, and policies.

Sponsor status:

- Build the active sponsor set from sponsor packages, sponsor orders, sponsor endpoint records, or event-linked sponsorship opportunities. Ignore records marked canceled, inactive, void, or lost.
- Use `paid_deferred` for an active sponsor whose invoice/payment is fully paid, whose open balance is zero, or whose event sponsorship opportunity is closed/won.
- Use `open_invoice` for an active sponsor with an issued invoice and a positive open balance or partial payment.
- Use `proposal_only` for an active sponsor package/order/opportunity with no issued invoice or payment record.
- Use `not_sponsor` only when the output schema explicitly asks for non-sponsor rows.
- For sponsor totals, sum package/order/opportunity amount by status. Separately sum positive open invoice balances when the schema asks for open balance.
- Sponsor finance follow-up targets are `open_invoice` plus `proposal_only` sponsor accounts. The follow-up due date is event end date plus `sponsor_followup_days_after_end` unless the prompt supplies a different rule.

Badge and lead handling:

- Classify a badge as `sponsor_attendee` when its account/company is in the active sponsor set or its badge type is sponsor.
- Exclude sponsor attendees from non-sponsor lead lists and lead pipeline totals. Include them in badge-level outputs when the schema asks for badge decisions.
- Treat press, student, academic, personal, vendor-only, and similar non-business badge types as `non_business_badge`.
- Use `existing_disqualified` for badges or accounts matched to disqualified CRM accounts.
- Use `missing_contact` when a badge lacks enough contact facts to create or update a contact.
- A qualified non-sponsor event lead is a business badge that is contactable, not a sponsor attendee, and not disqualified.
- Use the event's `lead_opportunity_amount` for each qualified non-sponsor account unless the prompt gives another sizing rule.
- Lead follow-up due date is event end date plus `followup_days_after_end` unless the prompt supplies a different rule.

CRM action decisions:

- Account action is update when a non-disqualified CRM account already matches; otherwise create.
- Contact action is update when a matching active contact exists; otherwise create.
- Campaign member action is create/add when no member exists, update when an existing member has the wrong target status, and no action when the existing member is already correct.
- For sponsor campaign members, target sponsor attendee status for attended sponsor badges and registered sponsor status for sponsor records without a matching attended badge.
- For qualified non-sponsor attended badges, target attended status.
- Include badge-only contact facts when the schema asks for them and the badge implies contact creation/update, including sponsor contacts that are not yet represented in CRM.

## Trade-Show Prospecting

Fetch the trade-show record, exhibitors, meeting interest, policies, and shared
CRM accounts/contacts when CRM overlap or import action is requested.

Qualification:

- Use policy platform enums when present. Preserve the enum order in platform lists and platform count objects.
- Qualify exhibitors that manufacture, build, design, or OEM-build target platforms or modules requested by the campaign.
- For marine/aquaculture robotics campaigns, classify platforms from descriptions: AUV for autonomous underwater vehicles or drone scouts, ROV for remotely operated vehicles/inspection robots, and Underwater Camera for camera, optics, imaging, or camera-module manufacturers.
- Exclude distributor/reseller/agent-only companies as distributor-only.
- Exclude consulting, operations, rental, analytics-only, or service providers as service-only.
- Exclude standalone sensor/probe vendors that do not build target platforms as sensor-only or sensor-vendor-only, matching the template enum spelling.
- Exclude research/lab/academic-only organizations as research-only.
- Use not-target-market only when the template provides that enum and no more specific enum fits.

Meeting interest, priority, and ranking:

- Join meeting interest by normalized company name unless a company id is provided.
- Default missing interest to `requested_demo: false` and score `0` when the schema requires those fields.
- Follow prompt-specific priority thresholds and opportunity sizes exactly. When the prompt only asks for A/B/C priority without thresholds, use demo requested with score at least 90 as A, demo requested with score at least 80 as B, and all other qualified leads as C.
- When ranking is requested with demo priority, sort demo-requested leads first, then interest score descending, then broader platform coverage, then company name ascending. Assign contiguous 1-based ranks after sorting.
- Existing CRM overlap is based on exhibitor `crm_account_id` first, then account matching. Mark matching qualified exhibitors `update_existing`; mark unmatched qualified exhibitors `create_account`; mark excluded exhibitors `no_import` when the schema asks.

Aggregates:

- Qualified count is the number of qualified exhibitors.
- Excluded count is the number of excluded exhibitors requested by the schema.
- Platform counts count qualified exhibitors per platform; a multi-platform exhibitor increments each covered platform.
- Priority counts count qualified exhibitors by final priority.
- Total opportunity is the sum of per-lead opportunity estimates.

## Import Batch Cleanup

Fetch the import batch, raw contacts, suppression list, CRM accounts, CRM
contacts, and policies.

Cleaning:

- Normalize email and phone before suppression, duplicate, and CRM matching.
- Remove unusable rows that have neither normalized email nor normalized phone. Use reason `missing_contact` unless the template names a more specific reason.
- Suppress rows whose normalized email or phone appears in the suppression endpoint or in opted-out CRM contacts. Use reason `suppressed`.
- Build duplicate keys as `email:<normalized email>` when email exists, otherwise `phone:<normalized phone>`.
- Remove duplicate rows after unusable and suppressed rows. For each duplicate key, choose one winner and report all other row ids as duplicate removals.
- If the prompt or API provides source precedence, use it. Otherwise prefer higher-confidence sources in this order: `partner_upload`, `sponsor_form`, `exhibitor_form`, `webinar_form`, `badge_scan`, `manual_upload`. Then prefer newer `captured_at`, then more complete rows, then lexicographically larger row id as a deterministic tie-breaker.

Import actions and summaries:

- A surviving clean contact gets `update_existing` when a non-disqualified CRM account or contact matches; otherwise it gets `create_account`.
- Use the winning row id for both `clean_contact_id` and `source_row_id` when the template asks for both.
- Count duplicate removals and suppressed removals from removed rows, not from duplicate groups.
- In action totals, count duplicate and unusable removals under `no_import`; count suppressed removals under `suppress`; count surviving clean contacts under their CRM action.
- Campaign-member import count is the number of surviving clean contacts that should be imported to the batch campaign.

## Final JSON Checks

- Re-open the answer template immediately before finalizing.
- Include every required key and no undeclared fields unless the template is an example object rather than a strict schema.
- Apply every ordering rule from the template or prompt after computing all values.
- Validate JSON syntax with `python -m json.tool` or an equivalent parser before responding.
