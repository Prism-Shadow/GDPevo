# HarborCRM Public-API CRM Handoff Skill

Use this skill for HarborCRM tasks that ask for an import-ready JSON answer from public API data, especially event sponsor/lead handoffs, trade-show prospecting lists, and contact import batches.

## Operating Procedure

1. Read the prompt and the provided answer template first. Treat the template as the contract: exact top-level keys, nested keys, enum spellings, null vs empty string, date format, and sorting rules.
2. Use only the HarborCRM base URL supplied by the runner or prompt. Query public endpoints named in the prompt, plus shared CRM/policy endpoints when listed. Do not inspect local source code or unstaged task files.
3. Fetch policy metadata early. It usually defines the controlled sponsor statuses, platform enums, and hygiene expectations, while the template defines the final field names.
4. Build small lookup tables before deciding records: accounts by account_id, normalized account name, and domain; contacts by contact_id, normalized email, and digits-only phone; campaign members by event/show and contact/account; invoices and opportunities by event_id/account_id.
5. Normalize once and reuse: lowercase trimmed emails; phone numbers as digits only; company/contact names trimmed; dates as `YYYY-MM-DD`; currency and counts as integers.
6. Classify every source record into exactly one output path when the template expects exclusions or removals. Keep reasons mutually exclusive and use only allowed enum values.
7. Produce one JSON object only. Do not add explanatory prose, markdown, comments, or undeclared fields.

## Data-Source Habits

- Event handoffs commonly need event details, sponsor orders or sponsor packages, badge scans, finance invoices filtered by `event_id`, CRM accounts, contacts, opportunities, campaign members, and policies.
- Trade-show prospecting commonly needs the show record, exhibitors, meeting-interest records, CRM accounts/contacts, and policies.
- Import-batch preparation commonly needs the batch list, raw contacts, suppression list, CRM accounts/contacts, and policies.
- Prefer IDs over names for joins. When an ID is absent, use normalized email/domain/name cautiously, and do not merge merely similar company names unless another stable key supports it.
- If two endpoint names expose the same sponsor-order shape, use the endpoint named by the prompt and reconcile by `account_id`.

## Event Sponsor And Lead Handoffs

- Active sponsor records are confirmed orders and, when the prompt/template asks for proposal status, proposal-stage orders. Canceled or inactive sponsor records are not active sponsors and should be excluded or separately recorded when the template requests it.
- Sponsor status conventions:
  - `paid_deferred`: active sponsor with paid/deferred finance status from invoices.
  - `open_invoice`: active sponsor with an open invoice; open balance is invoice amount minus paid amount.
  - `proposal_only`: active proposal without an invoice/payment record.
  - `not_sponsor`: use only where the template explicitly allows sponsor status rows for non-sponsors.
- Sponsor revenue totals normally sum package/order amounts by sponsor status. Track `open_invoice_balance` separately from package totals.
- Qualified non-sponsor leads come from business badge/attendee records that are not sponsor attendees, not tied to inactive sponsor exclusions, not non-business badges, not missing usable contact facts when contactability is required, and not already disqualified in CRM.
- Exclude sponsor contacts and sponsor badge attendees from non-sponsor lead lists even when their scan score or contact details look strong.
- Existing CRM accounts with `status` of `disqualified` or a disqualification reason should be excluded with the template's controlled reason.
- Non-business badge types such as student or press are exclusions when the task asks for sales handoff leads.
- Use the event's `lead_opportunity_amount` for each qualified non-sponsor account unless the prompt gives a different sizing rule.
- Follow-up due dates are computed from the event end date plus the event's lead or sponsor follow-up day offsets. Output dates as `YYYY-MM-DD`.
- Sponsor finance follow-up normally targets unpaid/open-invoice sponsor accounts. Include proposal-only accounts only if the prompt asks for proposal follow-up.
- Campaign-member actions:
  - No existing member: create/add campaign member.
  - Existing member with different target status: update.
  - Existing member already at target status: no action.
  - Excluded/non-importable record: no import/no action, following the template enum.
- Campaign-member target status usually follows classification: sponsor attendee to sponsor status, qualified attendee to attended/registered lead status, excluded records to excluded only when the template asks for explicit excluded campaign members.
- CRM action counts should be derived from the actual row-level actions in the output, not estimated independently.

## Trade-Show Prospecting

- Qualification is description-driven. Target exhibitors are companies that manufacture, OEM-build, or integrate covered underwater platforms, especially `AUV`, `ROV`, and `Underwater Camera` when those are the policy/template enums.
- Platform lists must use only allowed enum strings and should be sorted in enum order, not alphabetical order when the template gives an enum order.
- Existing `crm_account_id` or a confident CRM account match means `update_existing`; no CRM account match for a qualified exhibitor means `create_account`; excluded exhibitors usually use `no_import`.
- Common exclusion reasons:
  - `distributor_only`: reseller/dealer/sales agent without manufacturing or OEM build authority.
  - `service_only`: consultant/operator/service provider using rented or partner platforms.
  - `sensor_vendor_only` or `sensor_only`: sensor/probe vendor without platform manufacturing.
  - `research_only`: lab/research organization without commercial platform fit.
  - `not_target_market`: adjacent software, analytics, or unrelated market when allowed by the template.
- Meeting interest enriches and ranks qualified leads but does not by itself override a non-target exhibitor description.
- For ranked prospecting lists, follow the prompt's rank formula exactly. A common pattern is requested demo first, interest score descending, broader platform coverage, then company name ascending; assign 1-based contiguous ranks after sorting.
- Priority tiers and opportunity estimates are prompt-specific. Do not carry thresholds or dollar amounts from one task to another unless the prompt repeats them.
- Platform coverage counts count qualified exhibitors that cover each platform; one exhibitor can increment multiple platform counts.

## Import-Batch Contact Hygiene

- Normalize raw rows before suppression or duplicate checks: email lowercase/trimmed, phone digits only, blank strings for missing normalized values.
- Remove unusable rows when the row lacks usable contactability required by the task, commonly no normalized email and no normalized phone.
- Apply suppression using normalized email or normalized phone. Suppressed rows should not survive into clean contacts or campaign-member import counts.
- De-duplicate surviving rows by the strongest available contact key, usually normalized email first and phone when email is absent. Record duplicate summaries using the exact key format the template expects.
- Winner selection should follow any prompt or policy rule. If none is provided, use a deterministic rule such as latest `captured_at`, then lowest row_id as a tie-breaker.
- Removed rows should be listed once with one reason, such as `duplicate`, `missing_contact`, or `suppressed`.
- For cleaned contacts, preserve the winning row's source metadata and use the winning row_id wherever the template says the clean contact id is the winning source row_id.
- CRM overlap should prefer existing contact match by normalized email or phone; otherwise match account by account_id/domain/name if reliable. Existing contact/account implies update; no account/contact implies creation, subject to the template's action enum.
- Campaign-member import count is the number of surviving clean contacts that should actually be imported into the batch campaign.

## Output And Sorting Conventions

- Obey each template's stated ordering over any domain preference.
- Common sort rules:
  - Account/company lists: `account_name` or `company_name` ascending.
  - Badge decisions: `badge_id` ascending.
  - Clean contacts: clean id/source row id ascending unless the template says otherwise.
  - Duplicate keys: key ascending.
  - Removed rows: row_id ascending.
  - Ranked leads: rank ascending after applying the rank formula.
  - Existing CRM ID lists: ID ascending.
- Use `null` only where the template allows nullable fields; otherwise use empty string for missing normalized email/phone or string fields.
- Keep all aggregate totals synchronized with the detail rows. Recount after sorting and after applying exclusions.
- Currency fields are integer USD. Do not include decimals, currency symbols, or formatted strings.
- Date fields are ISO dates only, not timestamps, unless the template asks for original timestamps such as `captured_at`.

## Pitfalls

- Do not let sponsor attendees become non-sponsor leads.
- Do not treat canceled sponsor orders as active sponsors.
- Do not count `deferred_amount` as open balance; compute open balance from amount minus paid amount when needed.
- Do not qualify distributors, service operators, sensor-only vendors, research-only organizations, or analytics-only companies just because their notes mention target platforms.
- Do not ignore CRM disqualification or contact opt-out/suppression flags.
- Do not invent enum values. When two templates use slightly different enum names for the same concept, use the exact spelling in the current template.
- Do not add extra fields from the API to the output. The answer template wins over source richness.
- Do not rely on training-specific records, company names, or amounts. Recompute every answer from the current prompt, template, policies, and public API data.
