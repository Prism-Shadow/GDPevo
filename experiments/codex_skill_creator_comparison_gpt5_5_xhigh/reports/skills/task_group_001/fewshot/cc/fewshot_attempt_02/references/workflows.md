# HarborCRM Reference

## Endpoint families

| Task family | Base record | Related collections |
| --- | --- | --- |
| Event handoff / reconciliation | `/api/events/{event_id}` | orders, badges, sponsor_packages, `/api/finance/invoices?event_id=...`, `/api/crm/campaign_members?event_id=...`, `/api/crm/accounts`, `/api/crm/contacts`, `/api/crm/opportunities`, `/api/policies` |
| Trade-show prospecting | `/api/tradeshows/{show_id}` | exhibitors, meeting_interest, `/api/crm/accounts`, `/api/crm/contacts`, `/api/policies` |
| Import cleanup | `/api/import_batches/{batch_id}` | raw_contacts, suppression, `/api/crm/accounts`, `/api/crm/contacts`, `/api/policies` |

## Normalization

- Trim whitespace.
- Lowercase emails.
- Convert phones to digits only.
- Use empty strings when no contactable value exists.
- Prefer canonical CRM account and contact names when a template asks for output names.

## Matching

- Prefer explicit IDs first.
- Fall back to normalized email.
- Fall back to company name or domain only when the prompt leaves no better key.
- When multiple rows collide, keep the most complete, contactable, and authoritative record unless the prompt or template names a different tie-breaker.

## Classification patterns

- Sponsor status: use the current finance state, not the opportunity stage.
- Sponsor attendee: exclude from lead handoff and mark as sponsor attendee or no action.
- Qualified non-sponsor lead: keep only contactable, non-disqualified accounts that match the prompt's fit rules.
- Prospecting: only platform builders or OEMs qualify; adjacency alone is not enough unless the prompt says otherwise.
- Near miss / exclusion: map to the template's controlled exclusion enum.
- CRM action: use `update_existing` when a matching CRM account or contact already exists, and `create_account` or `create_contact` when no match exists.
- Import duplicates: select one winning row per contact key; drop the rest as duplicates.
- Suppression: drop rows that match suppression records or lack usable contact info.

## Output discipline

- Do not add extra keys.
- Keep sort order stable.
- Recompute counts from the final output tables.
