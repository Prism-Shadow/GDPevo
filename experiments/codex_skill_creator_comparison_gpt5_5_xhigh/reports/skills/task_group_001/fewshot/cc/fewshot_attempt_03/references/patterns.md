# HarborCRM Patterns

## Common

- Use the prompt’s answer template as the source of truth.
- Query only the endpoints that support the template.
- Use `/api/policies` for controlled enums and qualification notes.
- Match CRM records by normalized values, not raw display strings.
- Keep all counts as integers.

## Sponsor handoff

Use these endpoints when the template is about event sponsor reconciliation:

- `/api/events/{event_id}`
- `/api/events/{event_id}/orders`
- `/api/events/{event_id}/badges`
- `/api/events/{event_id}/sponsor_packages`
- `/api/finance/invoices?event_id={event_id}`
- `/api/crm/accounts`
- `/api/crm/contacts`
- `/api/crm/opportunities`
- `/api/crm/campaign_members?event_id={event_id}`
- `/api/policies`

Apply these rules:

- Classify sponsor rows from orders and invoices.
- Use `paid_deferred` when the sponsor is paid in full but recorded as deferred.
- Use `open_invoice` when an invoice has a remaining balance.
- Use `proposal_only` when an order exists without an invoice.
- Use `not_sponsor` only if the template asks for it.
- Revenue totals use package amount by status. Track open balance separately for open invoices.
- Exclude sponsor contacts, canceled or inactive sponsor records, non-business badges, and disqualified CRM accounts from the qualified lead list.
- Use the event lead opportunity amount for each qualified non-sponsor account.
- Derive follow-up due dates from the event end date plus the event-specific offsets.
- For sponsor finance follow-up, include accounts that still need invoice or proposal work, not paid-deferred sponsors.
- If the template includes badge or campaign-member actions, keep sponsor attendees separate from lead qualification. A sponsor attendee may still need create/update/no-action treatment.

## Trade-show prospecting

Use these endpoints when the template is about exhibitors:

- `/api/tradeshows/{show_id}`
- `/api/tradeshows/{show_id}/exhibitors`
- `/api/tradeshows/{show_id}/meeting_interest`
- `/api/crm/accounts`
- `/api/crm/contacts`
- `/api/policies`

Apply these rules:

- Keep only exhibitors that genuinely make or OEM-build the target platforms.
- Treat distributor, service, research, sensor-vendor, and other near misses using the controlled exclusion reasons in the template.
- Use meeting interest and requested demo as ranking signals when the template asks for ranking.
- Sort allowed platforms in the policy order: `AUV`, `ROV`, `Underwater Camera`.
- Existing CRM accounts map to `update_existing`. New companies map to `create_account`.
- For tiered templates, use the prompt’s A/B/C thresholds and assign the matching opportunity estimate.
- Count platform coverage once per qualified lead.
- For summary templates, derive totals from the qualified list and the exclusion list, not from the raw exhibitor count.

## Import cleanup

Use these endpoints when the template is about a batch import:

- `/api/import_batches/{batch_id}/raw_contacts`
- `/api/import_batches/{batch_id}/suppression`
- `/api/crm/accounts`
- `/api/crm/contacts`
- `/api/policies`

Apply these rules:

- Normalize email and phone before deduping or suppression matching.
- Use normalized email as the duplicate key.
- Keep the newest `captured_at`; if tied, keep the later raw row.
- Suppression wins over everything else when a row matches the suppression list by normalized email or phone.
- Remove rows with no usable contact information.
- `clean_contacts` should contain only the surviving rows; use the winning `row_id` for both `clean_contact_id` and `source_row_id`.
- Duplicate rows are `no_import`. Suppressed rows are `suppress`.
- `import_action_totals` count every raw row.
- `campaign_member_import_count` is the number of surviving cleaned contacts that should be imported.
