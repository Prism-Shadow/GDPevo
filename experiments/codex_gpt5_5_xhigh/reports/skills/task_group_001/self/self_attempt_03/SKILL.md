---
name: harborcrm-json-handoff
description: Use this skill for HarborCRM public API tasks that ask for CRM-ready JSON handoffs, post-event sponsor or badge reconciliation, trade-show prospecting summaries, or import-batch cleaning. It guides solvers to inspect the prompt and answer template, query only the public HarborCRM API endpoints supplied for the task, normalize and reconcile CRM records, apply exclusions and action conventions, sort deterministically, and return schema-exact JSON.
---

# HarborCRM JSON Handoff Solver

## Core Contract

Use the HarborCRM public API as the source of truth. Start from the task prompt and `input/payloads/answer_template.json`; the template controls required keys, allowed enum values, null-vs-empty-string choices, and sorting. Return one JSON object only, with no prose outside the JSON.

Do not inspect local environment source, hidden task files, prior outputs, notes, reports, or evaluator artifacts. Use the API base URL supplied by the runner. If an environment access note provides a remote base URL, prefer that and do not start or inspect a local service.

## Standard SOP

1. Read the prompt and answer template first. Extract the primary identifier (`event_id`, `show_id`, or `batch_id`), required endpoints, required top-level keys, enum values, date rules, currency/count precision, and explicit sort rules.
2. Fetch `/api/policies` early. It defines stable platform enums and sponsor handoff status vocabulary, but the prompt/template still win when they are more specific.
3. Fetch every public endpoint listed by the prompt for that task family. Typical joins include CRM accounts, contacts, opportunities, campaign members, invoices, sponsor orders/packages, badges, exhibitors, meeting interest, raw import rows, and suppression lists.
4. Build lookup maps before deciding: accounts by `account_id`, normalized account name, and domain; contacts by normalized email, phone, and account/name; campaign members by event/account/contact; invoices by event/account; meeting interest by company name; suppressions by normalized email and phone.
5. Normalize fields consistently: email is trimmed lowercase; phone is digits only; names are trimmed for display and compared case-insensitively; currency and counts are integers; follow-up dates are `YYYY-MM-DD`.
6. Decide records from joined facts, then compute summaries from the final decided arrays. Do not hand-enter totals that can drift.
7. Apply sorting last and validate that the final output parses as JSON, contains exactly the template-required fields, and uses only allowed enum values.

## Matching Habits

Prefer explicit IDs (`account_id`, `contact_id`, `crm_account_id`) over fuzzy matching. When an explicit ID is absent, use normalized company/account names and email domains as supporting evidence. Email match is the strongest contact match; phone is next; name plus account is a fallback.

Treat CRM account status carefully. Accounts already marked `disqualified` should not become qualified leads or import targets unless the prompt explicitly overrides that. Existing customer or prospect accounts can still be updated when the task asks for CRM overlap or handoff actions.

Use `null` only when the template permits it for missing IDs. Use empty strings for normalized email or phone fields when the template says empty string is allowed. Preserve source display names and websites unless the task asks for canonical CRM names.

## Event And Sponsor Reconciliation

For event tasks, fetch the event record, sponsor orders/packages, badges, invoices, CRM accounts, contacts, opportunities, campaign members, and policies. Use the event's `end_date` plus follow-up offsets to compute due dates when the template asks for lead or sponsor finance follow-up.

Classify sponsor account status from active sponsor order plus finance state:

- `paid_deferred`: confirmed sponsor with a paid/deferred invoice state.
- `open_invoice`: confirmed sponsor with an open invoice; compute open balance as invoice amount minus paid amount when not directly provided.
- `proposal_only`: proposal-stage sponsor order with no active paid/open invoice.
- `not_sponsor`: only when the template includes this as a badge/campaign classification, not as a paid sponsor revenue bucket.

Exclude canceled or inactive sponsor records from active sponsor status totals unless the template asks to list exclusions. Sponsor attendees are not non-sponsor leads. A badge from a sponsor company should be classified as sponsor-related even if the badge also looks contactable.

Qualified non-sponsor event leads usually require a business badge, usable contact/account facts, no sponsor relationship, and no disqualified CRM account. Use the event's lead opportunity amount for each qualified non-sponsor account when the prompt says to do so. Count one opportunity per qualified account, not per duplicate badge, unless the template explicitly asks for badge-level totals.

CRM action conventions for event handoff:

- Account action is create when no matching CRM account exists; update when an existing qualified account exists.
- Contact action is create when the account exists or will be created but no matching contact exists; update when a matching contact exists.
- Campaign member action is create/add when no member exists, update when a member exists but needs the event target status, no action when it already matches, and no import for excluded records.
- Sponsor finance follow-up targets are unpaid or open-invoice sponsor accounts; task count normally equals the number of accounts requiring finance follow-up.

Common event exclusions include sponsor attendee, inactive/canceled sponsor record, non-business badge, existing disqualified account, missing contact, and explicit no-import cases. Keep exclusion reason strings exactly as the template lists them.

## Trade-Show Prospecting

For prospecting tasks, fetch the trade show, exhibitors, meeting-interest records, CRM accounts, contacts if requested, and policies. Qualification is description-driven: include companies that build, manufacture, OEM-build, or integrate the target covered platforms for the campaign. Do not qualify companies that are only distributors, service providers, pure sensor vendors, research groups, media, or otherwise outside the requested market.

Use the policy platform enums in this order when present: `AUV`, `ROV`, `Underwater Camera`. A company can cover more than one platform; platform counts normally count each qualified company once per platform it covers.

Merge meeting interest by company name and preserve requested enrichment fields such as booth, country, website, requested demo flag, interest score, and notes-derived priority inputs when the template asks for them. If the prompt gives priority or opportunity-sizing thresholds, apply those exact thresholds. If no threshold is given, do not invent one.

CRM action conventions for prospecting:

- `update_existing` or `update_existing`-style values for qualified exhibitors with an existing CRM account ID or confident CRM account match.
- `create_account` for qualified exhibitors without existing CRM overlap.
- `no_import` for excluded exhibitors when the template asks to keep them visible.

Ranking and sorting are template-driven. For ranked lead lists, assign contiguous 1-based ranks after sorting by the prompt's priority rules, commonly demo request first, interest score descending, broader platform coverage, then company name. For non-ranked qualified lists, sort by `company_name` ascending unless told otherwise. Sort platforms internally in enum order.

## Import-Batch Cleaning

For import tasks, fetch the batch metadata, raw contacts, suppression list, CRM accounts, CRM contacts, and policies. Normalize every raw row before duplicate, suppression, and CRM matching decisions.

Contact hygiene conventions:

- Email key: trimmed lowercase email. Empty or whitespace-only email becomes `""`.
- Phone key: digits only. Empty or punctuation-only phone becomes `""`.
- A row with no usable email and no usable phone is generally unusable/missing-contact unless the prompt defines another contactability rule.
- Suppress a row when its normalized email or phone matches the suppression list or an existing opted-out CRM contact. Use the template's suppression/removal reason value exactly.

Duplicate conventions:

- Prefer normalized email as the duplicate key; use normalized phone when email is absent.
- Keep one winner per duplicate key. If the prompt does not specify a winner rule, choose the newest `captured_at`; break ties deterministically by source priority if provided, otherwise by stable row ID.
- Record removed duplicate row IDs in the duplicate/removal summaries. Do not count suppressed or unusable rows as clean imports.
- For clean contact IDs and source row IDs, use the winning raw row ID when the template asks for the winning row.

Import CRM action conventions:

- `update_existing` when the row matches an existing CRM account/contact that can be imported.
- `create_account` when the row is contactable and does not match an existing CRM account.
- `no_import` or `suppress` only when the template includes such values for surviving or removed rows; otherwise put excluded rows in the removal summary.
- Campaign-member import count is the number of surviving clean contacts that should become campaign members, excluding suppressed, unusable, duplicate-removed, and no-import rows.

## Output Conventions

Follow explicit sorting instructions from the template first. Common defaults:

- account/company lists: `account_name` or `company_name` ascending.
- contact-level exclusions: company name ascending, then contact name ascending.
- badge decisions: `badge_id` ascending.
- campaign-member actions: `subject_key` ascending.
- duplicate keys: key ascending.
- removed rows: source row ID ascending.
- account IDs: ascending.
- ranked leads: rank ascending after computing rank.

Use integer USD for revenue, open balances, opportunity estimates, and totals. Include zero-valued buckets required by the template even when no records fall into that bucket. Include empty arrays for required list fields with no members.

When the answer template is prose-like schema documentation rather than a literal JSON skeleton, still emit the actual JSON object with only the declared required fields and nested keys. Do not include `description`, `field_definitions`, or schema metadata unless the template requires those as answer fields.

## Pitfalls

- Do not turn sponsor contacts into sales leads.
- Do not count canceled sponsor orders as active sponsor revenue.
- Do not classify proposal-only sponsor orders as open invoices unless an invoice record supports that.
- Do not include CRM accounts with `status: "disqualified"` in qualified leads.
- Do not trust company name variants alone for duplicate or CRM matching when email/domain/ID evidence is available.
- Do not lose badge-only leads: if the template asks for normalized contact facts, include qualified contacts even when no CRM contact already exists.
- Do not add fields for explanation or confidence. The final response is machine-checked JSON.
- Recompute aggregate counts after exclusions, dedupe, and sorting; counts should match the arrays they summarize.
