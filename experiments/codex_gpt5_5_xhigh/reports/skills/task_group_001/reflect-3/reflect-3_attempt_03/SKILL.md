# HarborCRM Reconciliation And Prospecting SOP

Use this skill for HarborCRM tasks that ask for JSON-only CRM handoffs, event reconciliations, trade-show prospect lists, or import-batch cleanup. Work from the staged prompt, its answer template, and the public HarborCRM API endpoints named or implied by the prompt. Do not add prose, extra fields, or alternative enum values to the final JSON.

## Source Habits

1. Read the answer template first and mirror its top-level keys, item keys, enum spelling, nullability, and ordering rules exactly.
2. Fetch all relevant public records before deciding: event or show metadata, sponsor orders/packages, badges, invoices, CRM accounts, CRM contacts, opportunities, campaign members, import raw rows, suppression lists, meeting-interest records, and policies.
3. Join records by the strongest key available: `account_id`, `contact_id`, `event_id`, `show_id`, `crm_account_id`, normalized email, normalized phone, then company/contact name only when IDs are absent.
4. Use policy enums as controlled values. For platform coverage, use only `AUV`, `ROV`, and `Underwater Camera` in that order.
5. Treat money as integer USD and dates as `YYYY-MM-DD`. Follow-up dates are event end date plus the event's configured follow-up day count.

## Output Conventions

1. Return one JSON object only. Keep field names exactly as declared in the template.
2. Use `null` for missing IDs when the template permits nulls. Use empty strings for missing normalized email or phone when the template says empty strings are allowed.
3. Normalize email with trim plus lowercase. Normalize phone by stripping non-digits; do not invent a country code that was not present.
4. For existing CRM matches, preserve the existing `account_id` or `contact_id`. For new accounts, use `null` account/contact IDs unless the template says otherwise.
5. Count summaries from the final included records, not from raw source rows, unless the field explicitly asks for removed or excluded records.

## Sorting Rules

1. Always apply the template's explicit sort order.
2. Common defaults: sponsors by `account_name`; qualified lead accounts by `account_name`; exhibitors and exclusions by `company_name`; badge decisions by `badge_id`; removed import rows by `row_id`; duplicate keys by `key`.
3. Sort platform lists as `AUV`, then `ROV`, then `Underwater Camera`.
4. For ranked prospect lists, follow the prompt's ranking chain exactly. When used, a common rank chain is demo request first, then interest score descending, then broader platform coverage, then company name.

## Sponsor And Event Handoff

1. Sponsor status comes from sponsor order/package plus invoice state:
   - Confirmed order with paid/deferred invoice: `paid_deferred`.
   - Confirmed order with an open invoice: `open_invoice`; open balance is invoice amount minus paid amount.
   - Proposal-sent sponsor package without an invoice: `proposal_only`.
   - Canceled or inactive sponsor records are excluded or marked with the template's inactive/canceled reason, not treated as active sponsors.
2. Sponsor revenue/status totals should use package or invoice amounts as integer USD, with open invoice balance reported separately when requested.
3. Sponsor finance follow-up usually includes both `open_invoice` and `proposal_only` accounts. It excludes `paid_deferred` accounts.
4. Sponsor attendees are not non-sponsor leads even when their badge type says attendee. A badge tied to an active sponsor account should be classified or excluded as sponsor-related according to the template.
5. Non-business badge types such as student or press are excluded as `non_business_badge`.
6. Existing CRM accounts with a disqualified status or disqualified reason should not be imported as qualified leads.

## Qualified Leads And CRM Actions

1. Qualified event leads are business, non-sponsor, non-disqualified badge records with usable contact facts. Phone-only contacts can qualify when the template permits an empty email.
2. Use the event's lead opportunity amount for each qualified non-sponsor event account when the prompt asks for event lead pipeline.
3. CRM account actions:
   - `create_account` when no CRM account exists.
   - `update_existing` when the CRM account already exists and is not disqualified.
4. CRM contact actions:
   - `create_contact` when the account exists but the specific contact does not.
   - `update_existing` only for a matching existing contact.
5. Campaign-member actions:
   - Create or add when the lead/contact is not already a campaign member.
   - Update when an existing campaign member has the wrong target status.
   - `no_action` when the existing member already has the target status.
   - `no_import` for excluded subjects.
6. Use target statuses from the template, commonly `attended`, `attended_sponsor`, `registered_sponsor`, or `excluded`.

## Trade-Show Prospecting

1. Qualify companies that manufacture or OEM-build covered platforms: AUVs, ROVs, underwater cameras, or qualifying multi-platform robotics/camera systems.
2. Exclude adjacent companies that do not build covered platforms:
   - Distributor/reseller only: `distributor_only`.
   - Service, consulting, operator, analytics-only, or no-hardware firms: `service_only`.
   - Sensor-only vendors: `sensor_vendor_only` or the exact sensor enum in the template.
   - Research-only organizations: `research_only`.
   - Out-of-market companies: `not_target_market`.
3. Existing CRM exhibitor accounts are `update_existing`; exhibitors without CRM accounts are `create_account`.
4. Meeting-interest data can drive priority tiers when no separate tier field exists. When the prompt gives thresholds, apply them literally, such as demo plus score at least 90 for `A`, demo plus score at least 80 for `B`, and all other qualified leads as `C`.
5. Opportunity estimates come from the prompt's tier mapping. Sum only qualified ranked leads.
6. Platform coverage counts count every platform assigned to each qualified company, so a multi-platform company increments multiple platform counters.

## Import Batch Cleanup

1. Normalize raw rows before matching: lowercase trimmed email, digits-only phone, and trimmed names/company names.
2. Apply suppression and unusable-contact rules before import, but keep removed rows out of `clean_contacts` unless the template explicitly says to include non-importable rows there.
3. `clean_contacts` should contain surviving importable winners only. Removed duplicate, suppressed, and missing-contact rows belong in removal summaries.
4. For duplicate groups, choose the best winner by latest `captured_at`; when tied, use the source priority implied by the template/source enum order. Use the winner row ID for both `clean_contact_id` and `source_row_id`.
5. Duplicate summaries should name the duplicate key consistently, identify the winner row, and list removed row IDs sorted.
6. `duplicate_removed_count` counts duplicate losers. `suppressed_removed_count` counts suppression removals. `unusable_removed_count` counts missing/unusable contact removals.
7. Import action totals and campaign-member import count should be based on surviving importable clean contacts, not removed rows.

## Pitfalls

1. Do not turn proposal-only sponsors into ordinary leads or canceled sponsors into active sponsors.
2. Do not count excluded badges, disqualified accounts, or removed import rows in lead pipeline totals.
3. Do not add unsupported enum values such as informal exclusion labels or custom CRM actions.
4. Do not sort by discovery order when the template gives a field order.
5. Do not infer platform coverage from generic interest alone; use exhibitor descriptions and the prospecting policy.
6. Do not include API diagnostics, reasoning, feedback, or explanatory text in the final JSON response.
