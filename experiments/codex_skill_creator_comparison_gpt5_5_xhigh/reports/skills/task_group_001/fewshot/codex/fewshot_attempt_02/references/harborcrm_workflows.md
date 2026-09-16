# HarborCRM Workflows

## Common Setup

- Read the prompt, the answer template, and `/api/policies` first.
- Use the task-provided base URL and only the endpoints named in the prompt.
- Build canonical records in memory, then serialize one JSON object only.
- Keep top-level keys exact. Do not add notes, markdown, or extra fields.
- Expect policy sections such as `contact_hygiene`, `prospecting`, and `sponsor_handoff`; use them when the prompt asks for cleanup, qualification, or sponsor reconciliation rules.

## Event Handoff

Use this workflow for post-event sponsor reconciliation and sales handoff.

1. Pull the event, orders, badges, sponsor packages, invoices, CRM accounts, CRM contacts, CRM opportunities, and campaign members the prompt names.
2. Classify sponsors with `sponsor_handoff.status_enums` and the current order/invoice state.
3. Treat `paid_deferred`, `open_invoice`, and `proposal_only` as sponsor output statuses when the template calls for those values. Use the prompt and policy data to determine any `not_sponsor` exclusions.
4. Summarize sponsor revenue in integer USD. For open invoices, keep the outstanding balance separate when the template asks for it.
5. Identify qualified non-sponsor lead accounts only. Exclude sponsor attendees, inactive or canceled sponsor records, non-business badges, and already disqualified CRM accounts.
6. Use the event lead opportunity amount from the prompt or event data for each qualified lead account.
7. Set follow-up counts to the number of accounts that need action, not the number of contacts, unless the template says otherwise.
8. Map CRM actions from current CRM state: account creation or update, contact creation or update, and campaign-member creation or update.
9. Sort sponsor, lead, exclusion, and follow-up lists exactly as requested by the template.

## Trade-Show Prospecting

Use this workflow for exhibitor qualification and campaign-ready lead ranking.

1. Pull the trade-show record, exhibitors, meeting-interest data, CRM accounts, CRM contacts, and policies the prompt names.
2. Qualify exhibitors that make or OEM-build the target platforms described by the prompt and policy note. Exclude distributors, service-only firms, sensor-only firms, and research-only organizations when the prompt or policy says they are not targets.
3. Use `prospecting.platform_enums` and `prospecting.qualification_note` to keep platform labels and qualification boundaries consistent.
4. Split existing CRM overlap from new account creation. Record CRM account ids for overlaps and `null` for new accounts when the template expects that.
5. Rank leads with the prompt's ordering rules. When the prompt specifies demo request, score, breadth, or company name ordering, follow that order exactly.
6. Assign priority tiers and opportunity values from the prompt's rules. Do not invent new thresholds.
7. Keep excluded near misses visible with only the controlled exclusion reasons the template allows.
8. Sort qualified leads and exclusions exactly as requested, usually by company name unless the prompt overrides it.

## Import Batch Cleanup

Use this workflow for raw-contact cleanup, deduping, suppression, and import preparation.

1. Pull the import batch, raw contacts, suppression list, CRM accounts, CRM contacts, and policies the prompt names.
2. Use `contact_hygiene` to guide contact normalization and suppressions.
3. Normalize contact fields before comparison: email to lowercase trimmed text, phone to digits only, and names/company fields to trimmed text.
4. Remove suppressed rows, missing-contact rows, and duplicate rows according to the prompt's rules.
5. Keep one canonical row per duplicate group. Use the prompt's winning-row rule if it provides one. If it does not, choose a deterministic winner using the most complete contactable record and stable tie-breaking.
6. Populate `duplicate_summary` with only the removed duplicate keys and winner/loser row ids.
7. Populate `removal_summary` with unusable and suppressed rows using the template's reason enum.
8. Count import actions across the surviving cleaned contacts only.
9. Set `campaign_member_import_count` to the number of cleaned contacts that remain eligible for campaign import.
