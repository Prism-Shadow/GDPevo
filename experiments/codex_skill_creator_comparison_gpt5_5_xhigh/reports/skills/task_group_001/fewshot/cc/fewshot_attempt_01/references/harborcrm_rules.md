# HarborCRM Reconciliation Rules

Use these rules together with the specific task prompt and `answer_template.json`. The prompt and template win over this reference when they give more specific instructions.

## Contents

- [Universal Preparation](#universal-preparation)
- [Event Handoff And Badge Reconciliation](#event-handoff-and-badge-reconciliation)
- [Trade-Show Prospecting](#trade-show-prospecting)
- [Import-Batch Cleanup](#import-batch-cleanup)
- [Final Validation Checklist](#final-validation-checklist)

## Universal Preparation

- Normalize email by trimming whitespace and lowercasing. Preserve an empty string when no usable email exists.
- Normalize phone by keeping digits only. Preserve an empty string when no usable phone exists.
- Normalize company and contact names for matching by trimming whitespace and comparing case-insensitively; keep the original API spelling in output unless the template asks for a cleaned value.
- Prefer explicit IDs over fuzzy matching. Use `crm_account_id`, `account_id`, `contact_id`, `event_id`, `show_id`, and `batch_id` when records provide them.
- Match CRM accounts in this order: explicit account ID, exact normalized company name, website/email domain against account domain, then obvious short-name variants. Do not treat a disqualified account as a qualified lead.
- Match contacts in this order: explicit contact ID, normalized email, then same account plus normalized contact name. Do not reuse an unrelated contact just because the account matches.
- Build campaign-member subject keys from the fields in the data or template. When no subject key exists, use a stable key from account/contact IDs or from the source badge/raw row ID.
- Derive due dates from event end dates plus the follow-up day offsets supplied by the event or prompt.

## Event Handoff And Badge Reconciliation

Gather event detail, sponsor/order/package/invoice data, badge or attendee scans, CRM accounts, contacts, opportunities, and campaign members when available.

Sponsor status decisions:

- Include active sponsor records only. Exclude canceled or inactive sponsor records unless the template asks to surface them in exclusions.
- Use `paid_deferred` for active sponsors with fully paid invoices, closed-won sponsorship opportunities, or an equivalent paid state where revenue is recognized later.
- Use `open_invoice` for active sponsors with an invoice that has unpaid balance. Include the full package or sponsorship amount in sponsor revenue totals, and separately sum the unpaid open balance when the schema asks for it.
- Use `proposal_only` for active sponsor commitments or sponsorship opportunities that have no invoice yet and are not closed won.
- Treat open-invoice and proposal-only sponsors as finance follow-up targets unless the prompt narrows the target set.

Badge and lead decisions:

- Classify sponsor contacts and sponsor-company badge scans as sponsor attendees, not non-sponsor leads.
- Exclude non-business badges such as press, students, schools, labs, personal/non-company records, and missing-contact rows when the schema has those reasons.
- Exclude CRM accounts whose status or reason marks them disqualified.
- A qualified non-sponsor lead is a business badge/account that is not a sponsor attendee, not disqualified, and has enough contact/account information to import.
- Use the event's lead opportunity amount for each unique qualified non-sponsor account unless the prompt provides a different sizing rule.
- For new non-sponsor companies, create account, contact, and campaign member. For existing accounts, update the account and create or update the contact based on contact matching.
- For sponsor attendees, create or update contacts and campaign members only when the template asks for badge-level or campaign-member reconciliation; otherwise record them as exclusions.
- Existing campaign members with the target status normally require `no_action`; existing members with a lesser or stale status require `update`; absent members require `create`.

Event aggregates:

- Sum lead pipeline from unique qualified non-sponsor accounts.
- Count CRM actions from the final create/update/no-action decisions, not from raw badge count.
- Sort sponsor statuses by account name unless instructed otherwise.
- Sort badge decisions and campaign-member actions by the template keys.
- Sort exclusion rows by the exact ordering rule in the template.

## Trade-Show Prospecting

Gather show detail, exhibitors, meeting interest, CRM accounts, contacts, opportunities, and policy data when available.

Qualification:

- Qualify exhibitors that manufacture, OEM-build, or own covered platform products matching the campaign.
- Do not qualify distributors, dealers, resellers, rental fleets, consultants, service-only businesses, analytics-only software providers, sensor-only vendors, research-only organizations, or companies outside the target market.
- Keep near misses visible in the requested exclusion list with one of the enum reasons allowed by the template.

Platform coverage:

- Use `AUV` for autonomous underwater vehicles, autonomous scouts, AUV mapping platforms, or equivalent platform manufacturing.
- Use `ROV` for remotely operated vehicles, inspection ROVs, resident ROVs, pen-cleaning ROVs, or equivalent ROV manufacturing.
- Use `Underwater Camera` for underwater camera modules, OEM camera systems, imaging rigs, or optics products that are themselves covered by the campaign.
- Sort platforms in the enum order from the template.

Priority, ranking, and CRM action:

- Use priority-tier thresholds from the prompt or policy. If none are specified, treat demo-requested high-interest exhibitors as highest priority, demo-requested medium-interest exhibitors as middle priority, and all other qualified exhibitors as lower priority.
- If the prompt gives a rank order, apply it exactly. Common ranking is demo requested first, interest score descending, broader platform coverage, then company name.
- Mark exhibitors with an existing CRM account as `update_existing`; otherwise mark them `create_account` when qualified. Excluded exhibitors normally use `no_import`.
- Preserve required enrichment fields such as booth, country, website, requested demo, interest score, and company ID from the API.

Trade-show aggregates:

- Count qualified exhibitors after exclusions.
- Platform counts are coverage counts, so a multi-platform exhibitor increments each covered platform.
- Existing CRM overlap counts should use unique account IDs sorted as requested.
- Total estimated opportunity is the sum of per-lead estimates after priority assignment.

## Import-Batch Cleanup

Gather batch metadata, raw contacts, suppression records, CRM accounts, CRM contacts, and policy data when available.

Cleaning order:

1. Normalize email and phone for every raw row.
2. Mark rows unusable when both normalized email and normalized phone are empty.
3. Mark rows suppressed when normalized email or normalized phone matches a suppression record, global opt-out, privacy request, role-account rule, or opted-out CRM contact if the prompt or policy says to use CRM opt-outs.
4. Deduplicate the remaining usable, non-suppressed rows by normalized email when present; otherwise deduplicate by normalized phone.
5. Choose one winner per duplicate key, then remove the losing row IDs with reason `duplicate`.

Duplicate winner selection:

- Use explicit source priority from policy when provided.
- Without explicit policy, prefer sources that imply stronger verified engagement in this order: badge scan, sponsor form, partner upload, exhibitor form, webinar form, manual upload.
- Break ties by newest `captured_at`; if still tied, choose a stable row ID order and document the chosen winner in the output fields requested by the template.

Import actions:

- A surviving row with a matched non-disqualified CRM account normally uses `update_existing`.
- A surviving row with no matched CRM account normally uses `create_account`.
- A row removed for duplicate or missing contact normally counts as `no_import`.
- A row removed for suppression counts as `suppress`.
- Set `existing_account_id` and `existing_contact_id` from CRM matching; use `null` when no match exists.
- Count campaign-member imports from surviving clean contacts that should enter the batch campaign.

Import aggregates:

- `duplicate_removed_count` equals the number of duplicate loser rows.
- `suppressed_removed_count` equals rows removed for suppression.
- `unusable_removed_count` equals rows removed for missing usable contact information.
- `removed_rows` should include every removed row with the controlled reason requested by the template.
- Sort clean contacts, duplicate keys, and removed rows exactly as the template says.

## Final Validation Checklist

- Compare every key against the template, including nested required keys.
- Confirm enum spellings match the template exactly.
- Recompute all totals from output lists after exclusions.
- Confirm all nulls, empty strings, booleans, dates, and integers use the expected JSON types.
- Confirm arrays are sorted after all records are finalized.
- Return only the final JSON object.
