# HarborCRM CRM Reconciliation SOP

Use this skill for HarborCRM tasks that ask for a strict JSON handoff, import cleanup, sponsor reconciliation, or trade-show prospecting summary.

## Core Workflow

1. Read the prompt and answer template first. Copy the required top-level keys, nested keys, enum spellings, null/empty-string conventions, and sort rules exactly. Do not add explanatory prose or undeclared fields.
2. Query only the public HarborCRM endpoints named or implied by the prompt. Build lookup maps for CRM accounts, CRM contacts, opportunities, campaign members, policies, and the task-specific event, show, batch, badge, exhibitor, invoice, order, suppression, or meeting-interest records.
3. Normalize before matching: lowercase and trim emails; strip phones to digits only; compare account/company names case-insensitively and also use supplied `crm_account_id` or `account_id` fields when present.
4. Reconcile source records before counting. Decide inclusion/exclusion at the record level, then derive totals from the final included sets.
5. Emit integers for USD amounts and counts. Use `null` only where the template permits it; use `""` for missing normalized email or phone when the schema says empty strings are allowed.

## Sponsor And Event Handoffs

- Treat confirmed sponsor orders with paid/deferred invoices as `paid_deferred`.
- Treat confirmed sponsor orders with open invoices as `open_invoice`; report the full invoice/order amount as revenue and the unpaid portion separately as open balance.
- Treat proposal-sent sponsor orders without an invoice as `proposal_only`. They remain sponsor follow-up targets and should not become qualified non-sponsor leads.
- Exclude canceled or inactive sponsor records from active sponsor status lists. If an exclusion list is requested, use the template's inactive/canceled sponsor reason.
- Sponsor finance follow-up normally includes `open_invoice` and `proposal_only` sponsor accounts; sort account names as the template specifies and total the unpaid sponsor exposure.
- Compute follow-up dates by adding the event's configured lead or sponsor follow-up day count to the event end date, unless the prompt gives a different rule.

## Lead Qualification

- Qualified non-sponsor event leads are business badge/contact records that are contactable and not sponsors, not from canceled sponsor records, not non-business attendees, and not CRM accounts already marked disqualified.
- Exclude sponsor attendees and sponsor ticket contacts from lead lists. Press, student, academic-only, role-only, or other non-business records belong in exclusions when the template asks for them.
- A phone-only business badge can qualify when the schema allows empty email and the phone is present after normalization.
- Use the event's stated lead opportunity amount for every qualified non-sponsor account unless the prompt gives a different sizing rule.
- Lead pipeline totals are derived from the final qualified account list, not from all badge scans.

## CRM Action Conventions

- Existing non-disqualified CRM account: `update_existing`.
- No matching CRM account: `create_account`.
- Existing matching contact under the account: `update_existing`; otherwise create the contact when the record is importable.
- Campaign member already present with the desired status: `no_action`.
- Campaign member present but needing a new status/activity: `update` or `update_campaign_member`.
- Importable subject with no campaign member: `create`, `add_campaign_member`, or the template's create-account/contact/campaign-member enum.
- Excluded or suppressed rows should use `no_import` or `suppress` only when the schema asks for an action on those rows; otherwise keep them in the removal/exclusion section.
- Action totals must match the scope implied by the template: surviving clean contacts for import batches, qualified handoff work for lead summaries, or all badge/campaign subjects for event reconciliations.

## Import Cleanup

- Apply suppression and unusable-contact rules before final import. Suppression can match normalized email or normalized phone.
- Remove records with no usable contact route when the template has a missing-contact reason.
- Deduplicate by normalized email first, with normalized phone as a fallback when email is absent. Keep duplicate summaries sorted by key.
- Use the winning source row's `row_id` as both `clean_contact_id` and `source_row_id` when the template says to use the winning row.
- Preserve source fields from the winning row unless the prompt explicitly asks for CRM-canonical account names or enriched values.
- Sort clean contacts by `clean_contact_id`, duplicate keys by `key`, and removed rows by `row_id`.

## Trade-Show Prospecting

- Qualify exhibitors only when they manufacture, OEM-build, or clearly provide covered platforms. For these tasks the platform enum order is `AUV`, `ROV`, `Underwater Camera`.
- Count every platform an exhibitor actually covers. For example, a company making ROVs with its own camera arrays can count for both `ROV` and `Underwater Camera`.
- Exclude distributor-only, service/analytics-only, sensor-vendor-only, research-only, and not-target-market exhibitors using the controlled reason values from the template.
- Existing CRM overlap is based on supplied exhibitor `crm_account_id` or a reliable CRM account match. Existing qualified accounts are updates; new qualified exhibitors are account creates.
- Use meeting-interest records for `requested_demo`, `interest_score`, and priority when available. If the prompt gives tier or ranking rules, follow them exactly.
- For ranked lead lists, rank demo requests first, then interest score descending, then broader platform coverage, then company name ascending. Ranks are 1-based and contiguous.

## Sorting And Output Checks

- Apply every template ordering rule after all records are finalized.
- Common sorts: sponsor/account lists by `account_name`; qualified/excluded exhibitors by `company_name`; badge decisions by `badge_id`; exclusions by `company_name` then `contact_name`; ranked lists by `rank`.
- Sort platform arrays in enum order: `AUV`, `ROV`, `Underwater Camera`.
- Sort ID lists ascending when the template asks for account IDs, row IDs, or duplicate keys.
- Recompute all summary counts from the emitted arrays: qualified totals, excluded totals, platform counts, priority counts, opportunity totals, open invoice balances, and action totals.

## Pitfalls

- Do not turn proposal-only sponsors into non-sponsor leads.
- Do not include canceled sponsors in active sponsor status totals.
- Do not count only paid cash for open invoices; report full revenue amount and separate open balance.
- Do not import CRM accounts already marked disqualified, even if a badge or exhibitor otherwise looks qualified.
- Do not invent country codes or punctuation in normalized phones; keep only the digits present in the source value.
- Do not use free-text reasons or statuses when the template gives controlled enums.
- Do not rely on local source code or unstaged files; the prompt, template, policies, and public HarborCRM API data are the source of truth.
