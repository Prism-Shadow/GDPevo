---
name: harborcrm-reconciliation
description: Solve HarborCRM API tasks that require CRM, event, tradeshow, sponsor, campaign-member, or import-batch reconciliation into an exact JSON answer template.
---

# HarborCRM Reconciliation

Use this skill when a task mentions HarborCRM, CRM-ready handoff, post-event reconciliation, sponsor status, campaign members, tradeshow exhibitors, prospecting, or import-batch cleanup.

The usual task shape is:

1. Read the prompt and the provided answer template.
2. Fetch public HarborCRM API data from the base URL supplied by the runner.
3. Join task-specific records to shared CRM records.
4. Apply policy, qualification, exclusion, normalization, and sorting rules.
5. Return exactly one JSON object matching the template.

Do not emit explanatory prose outside the JSON.

## First Pass

- Read the prompt for the exact task ID, event ID, show ID, or import batch ID.
- Read the answer template and treat it as the output contract. Keep only declared fields, enum values, nullability, date formats, and ordering rules.
- Inventory the API endpoints named by the prompt. Fetch all relevant task-specific collections and shared CRM collections before reasoning.
- Prefer explicit policy data from the API or prompt over heuristic rules in this skill.
- If an endpoint path differs from the prompt, use only public business/index endpoints to discover the available equivalent; do not inspect source code, judge endpoints, or evaluator internals.

Useful shared collections commonly include:

- CRM accounts
- CRM contacts
- CRM opportunities
- CRM campaign members
- policy metadata, when exposed

Task-specific collections commonly include:

- events, badge scans, sponsor orders/packages, invoices
- tradeshows, exhibitors, meeting interest
- import batches, raw contacts, suppression lists

## Output Discipline

- Build the answer from the template, not from memory.
- Preserve required top-level keys and object keys exactly.
- Do not add undeclared fields.
- Use integers for USD amounts and counts unless the template says otherwise.
- Use JSON `null` where the template allows null; otherwise use empty strings only when the template calls for strings and no value exists.
- Sort every list by the template's rule. If no rule is provided, sort deterministically by the natural stable key such as name, ID, then contact name.
- Recalculate all summary counts and totals from the final included records.
- Validate that the final response parses as JSON and contains no prose before or after the object.

## Normalization

Normalize data before matching or deduping:

- Email: trim whitespace and lowercase. Use an empty string for missing email fields when the schema requires a string.
- Phone: strip every non-digit character. Preserve country/area digits that are present in the source. Use an empty string when missing.
- Company/account names: compare case-insensitively after trimming, collapsing repeated spaces, and ignoring light punctuation. Keep the original display name required by the output source.
- Domains: compare normalized website domains and email domains when names differ.
- Dates: compute due dates by adding task-provided day offsets to the event end date. Format as `YYYY-MM-DD`.

CRM matching priority:

1. Explicit IDs on the source record.
2. Exact normalized email to CRM contact.
3. Exact normalized phone to CRM contact.
4. Exact normalized company/account name.
5. Website or email domain to CRM account domain.

Treat an account as disqualified when its CRM status is disqualified or it has a disqualified reason. Do not import or qualify disqualified accounts as sales leads.

## Event Reconciliation

For event tasks, fetch the event details, sponsor/order/package data, badge scans, invoices or finance data, and shared CRM collections.

Sponsor status:

- Consider only active/current sponsor records for sponsor status output.
- Exclude canceled or inactive sponsor records from active sponsor revenue; if the template asks for exclusions, record them with the inactive sponsor reason.
- Use the task's controlled sponsor status enums. Common statuses are:
  - `paid_deferred`: active sponsor with a paid/closed-won or fully paid finance state.
  - `open_invoice`: active sponsor with an invoice or finance record that still has an open balance.
  - `proposal_only`: active sponsor/proposal/order without a payable invoice or paid state.
  - `not_sponsor`: only when the template explicitly asks to classify non-sponsors in a sponsor list.
- Use sponsor package/order amount as the sponsor amount unless the prompt or template says to use invoice amount.
- For open invoices, report both the full sponsor amount and the unpaid balance when fields are present.
- Sponsor finance follow-up targets are unpaid/open/proposal sponsor accounts. Sort names ascending and set the due date from the event sponsor-follow-up offset.

Badge and lead handling:

- Sponsor contacts are sponsor attendees, not non-sponsor leads. They may still require contact or campaign-member work if the template asks for badge-level handling.
- Qualified non-sponsor leads must be business badges from non-sponsor, non-disqualified accounts with usable contact information unless the prompt says otherwise.
- Exclude non-business badges such as student, academic/research-only, press/media, personal, service-only, or other policy-declared non-target records.
- Exclude existing disqualified CRM accounts even when a badge is otherwise business-like.
- Missing contact records are excluded when both usable email and usable phone are absent, or when the template/policy defines the row as missing contact.
- Use the event's lead opportunity amount for each qualified non-sponsor account unless the prompt gives another sizing rule.

CRM actions for event leads:

- Account action is create when no CRM account matches; update when an eligible existing CRM account matches.
- Contact action is create when no matching contact exists; update when an existing contact matches and source facts should refresh it.
- Campaign-member action is create/add when no member exists for the event/contact/account; update when a member exists but the target status changes; no action when an existing member already has the target state; no import for excluded records.
- Count account, contact, and campaign-member actions from the final decisions required by the output schema.

Common campaign-member target statuses:

- Sponsor attendee who attended: `attended_sponsor`.
- Sponsor contact registered but not badge-scanned: `registered_sponsor`.
- Qualified non-sponsor attendee: `attended`.
- Excluded record when represented as a campaign member: `excluded`.

## Tradeshow Prospecting

For tradeshow tasks, fetch the show record, exhibitors, meeting interest, CRM accounts, CRM contacts, and policy data when available.

Qualification:

- Qualified exhibitors are companies that make, OEM-build, or directly manufacture the target platforms named by the campaign policy.
- Do not qualify distributor-only, reseller-only, service-only, sensor-vendor-only, research-only, or not-target-market exhibitors unless the prompt explicitly includes them.
- Preserve requested enrichment fields from the exhibitor record, such as company ID, company name, booth, country, and website.
- Existing CRM overlap comes from `crm_account_id` on the exhibitor or a reliable CRM account match. Existing eligible accounts use update actions; unmatched qualified exhibitors use create actions.

Platform classification:

- `AUV`: autonomous underwater vehicles, AUV scouts, underwater drones when described as autonomous platform makers.
- `ROV`: remotely operated vehicles, inspection/cleaning ROVs, tethered underwater robots.
- `Underwater Camera`: underwater camera modules, camera arrays, optical/vision hardware for underwater platforms.
- Sort platform arrays in the enum order required by the template, not alphabetically unless the template says so.

Priority and ranking:

- Use priority, scoring, and opportunity sizing rules from the prompt first.
- If the prompt gives demo and interest score thresholds, apply them exactly.
- If ranking is required and the prompt gives tie-breakers, apply them in order. A common pattern is demo request first, interest score descending, broader platform coverage, then company name.
- If the output is not ranked, sort qualified exhibitors by the template rule, commonly company name ascending.

Exclusions:

- Keep excluded near misses visible when the template asks for them.
- Map descriptions to the template's exact exclusion enum. For example, use the template's spelling for distributor-only, service-only, sensor-only or sensor-vendor-only, research-only, and not-target-market categories.
- Excluded exhibitors usually have a `no_import` CRM action when the template includes CRM action.

Summaries:

- Qualified count is the number of final qualified exhibitors.
- Platform counts count each platform occurrence, so one company with two platforms increments both.
- Priority counts count final qualified exhibitors by priority tier.
- CRM overlap count counts qualified exhibitors linked to existing eligible CRM accounts.
- Total opportunity is the sum of final qualified opportunity estimates.

## Import Batch Cleanup

For import-batch tasks, fetch the batch metadata, raw contacts, suppression list, CRM accounts, CRM contacts, and policy data when available.

Row cleaning:

- Normalize email and phone before any suppression, dedupe, CRM matching, or output.
- A row is missing contact when it lacks usable email and phone, unless the prompt defines a different minimum.
- A row is suppressed when its normalized email or phone matches a suppression list entry or an opted-out CRM contact/policy exclusion.
- Suppressed rows are removed from clean contacts and counted under suppress/suppressed totals.

Dedupe:

- Deduplicate by normalized email when present. If no email exists, deduplicate by normalized phone. Use duplicate key strings in the template's required format, such as `email:<normalized>` or `phone:<normalized>`.
- Prefer a policy-provided source precedence when choosing the winning duplicate row.
- If no precedence is supplied, prefer higher-confidence sources over lower-confidence form/manual sources, then the latest captured timestamp, then the lexically stable row ID.
- Duplicate losers are removed rows with reason `duplicate` and usually count as `no_import`, not as create/update.
- The clean contact ID is usually the winning source row ID when the template says so.

CRM import action:

- Use `update_existing` when the cleaned row maps to an eligible CRM account.
- Use `create_account` when no eligible CRM account maps.
- Use `suppress` for suppressed rows.
- Use `no_import` for duplicate losers, missing-contact rows, disqualified existing accounts, or other excluded records.
- Existing contact ID should be filled only when an existing CRM contact matches by email, phone, or reliable account/name match. Otherwise use null when allowed.
- Campaign-member import count is the number of surviving cleaned contacts that should become members of the batch campaign.

Removal summaries:

- `unusable_removed_count` counts missing-contact or otherwise unusable rows, not duplicate or suppression removals unless the template says otherwise.
- `suppressed_removed_count` counts suppressed rows.
- `duplicate_removed_count` counts duplicate loser rows.
- Sort removed rows and duplicate keys exactly as required by the template.

## Final Validation Checklist

Before returning:

- Every required key in the template is present.
- No undeclared keys are present.
- All enum values exactly match the template.
- All date strings and integer fields have the required format/type.
- All list ordering rules are satisfied.
- Summary totals reconcile to included records.
- Exclusion counts reconcile to excluded or badge-decision records.
- Phone and email fields are normalized.
- CRM create/update/no-action counts reconcile to the decision lists.
- The answer is a single JSON object with no markdown fence and no prose.
