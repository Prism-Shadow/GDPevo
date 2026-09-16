# HarborCRM Reference

## Shared Rules
- Treat the template as the source of truth for required keys, enums, sort order, null-vs-empty-string behavior, and which summary fields must be present.
- Use the prompt for task-family rules that the template does not encode.
- Use CRM account disqualification and opt-out/suppression data as hard stops unless the prompt explicitly says otherwise.
- Never copy values from staged answers into reusable instructions.

## Common Endpoint Groups
- Event handoff: `/api/events/{event_id}`, `/api/events/{event_id}/orders`, `/api/events/{event_id}/badges`, `/api/events/{event_id}/sponsor_packages`, `/api/finance/invoices?event_id=...`, `/api/crm/accounts`, `/api/crm/contacts`, `/api/crm/opportunities`, `/api/crm/campaign_members?event_id=...`, `/api/policies`
- Trade-show prospecting: `/api/tradeshows/{show_id}`, `/api/tradeshows/{show_id}/exhibitors`, `/api/tradeshows/{show_id}/meeting_interest`, `/api/crm/accounts`, `/api/crm/contacts`, `/api/policies`
- Import cleanup: `/api/import_batches/{batch_id}`, `/api/import_batches/{batch_id}/raw_contacts`, `/api/import_batches/{batch_id}/suppression`, `/api/crm/accounts`, `/api/crm/contacts`, `/api/policies`

## Event Handoff
Use this branch for prompts about event sponsor reconciliation, badge scans, sponsor packages, invoices, CRM campaigns, or follow-up handoff.

- Read event metadata for campaign code, event dates, and follow-up windows.
- Query sponsor orders/packages, badge records, invoices, CRM accounts, CRM contacts, CRM opportunities, and event campaign members as needed.
- Keep sponsor attendees separate from non-sponsor lead accounts.
- Use sponsor status enums exactly as the prompt/template allows. Do not invent extra statuses.
- Typical sponsor buckets:
  - `paid_deferred`: sponsor committed and financially settled or deferred per invoice logic.
  - `open_invoice`: sponsor committed with an unpaid balance.
  - `proposal_only`: sponsor opportunity exists but has not become a paid sponsor.
  - `not_sponsor`: only when the template explicitly allows it.
- If the template asks for badge decisions or campaign-member actions, keep sponsor-attendee records visible for CRM work but exclude them from lead qualification.
- Exclude sponsor contacts, inactive/canceled sponsor records, non-business badges, and already disqualified CRM accounts from the lead list.
- Qualified leads are non-sponsor business contacts that remain after exclusions.
- Use the event lead opportunity amount for each qualified non-sponsor account.
- Derive due dates from the event end date plus the policy/event follow-up windows.
- Sum sponsor revenue by status in integer USD. Keep open balance separate from revenue.
- Derive CRM action counts from the final qualified/excluded sets.
- Sort sponsor/account lists by `account_name` ascending unless the template says otherwise.
- Sort excluded records by `company_name` ascending, then `contact_name` ascending.

## Trade-Show Prospecting
Use this branch for prompts about exhibitors, meeting interest, platform coverage, and campaign prospecting.

- Fetch show metadata, exhibitors, meeting-interest data, CRM accounts, CRM contacts, and policies.
- Qualify only exhibitors that actually build or OEM-build the target platforms described by the prompt.
- Allowed platform enums are only `AUV`, `ROV`, and `Underwater Camera`.
- Exclude distributor-only, service-only, sensor-only, research-only, and not-target-market records.
- Use meeting interest and demo-request signals only when the prompt asks for ranking or sizing.
- If the prompt asks for ranked leads, follow its ranking keys exactly before any alphabetical tie-break.
- Existing CRM overlap means `update_existing`; otherwise use `create_account`.
- Count platform coverage from qualified exhibitors only.
- Sort by the template or prompt order rule. If the prompt gives a rank order, use contiguous 1-based ranks.

## Import Cleanup
Use this branch for prompts about raw contact batches, suppression lists, duplicates, or campaign-member import counts.

- Read the batch, raw contacts, suppression list, CRM accounts, CRM contacts, and policies.
- Normalize emails to lowercase trimmed strings.
- Normalize phones to digits only.
- Remove duplicates before import. If the prompt does not give a winner rule, prefer the most recent `captured_at`; if still tied, prefer the more authoritative source and the more complete record.
- Remove suppressed rows and rows with missing contact facts before counting survivors.
- Use `clean_contact_id` and `source_row_id` from the winning row unless the template says otherwise.
- Set `crm_action` from CRM overlap and suppression outcome.
- Count import actions from the cleaned survivors, not from removed rows.
- Set campaign-member import count to the number of surviving cleaned contacts.

## Output Discipline
- Emit one JSON object only.
- Do not wrap the result in markdown fences or explanatory prose.
- Do not add fields that the template does not declare.
