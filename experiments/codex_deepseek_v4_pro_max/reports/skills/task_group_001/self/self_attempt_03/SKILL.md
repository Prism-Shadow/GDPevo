## HarborCRM Data Processing Skill

This skill covers reusable operating rules for HarborCRM data-processing tasks across events, trade shows, CRM imports, and prospecting campaigns.

### Environment Setup

1. Read `environment_access.md` at the workspace root for the API base URL and allowed GET endpoints.
2. The runner supplies the base URL as `<TASK_ENV_BASE_URL>` or via the `GDPEVO_ENV_BASE_URL` variable.
3. All calls are GET only; no authentication.
4. Request headers: `Accept: application/json`.

### Input Discovery

Read these files before processing:

- `input/prompt.txt` — task objective, identifiers, and business rules.
- `input/payloads/answer_template.json` — exact output schema with required keys, field types, allowed enum values, sorting rules, and numeric precision.

### Data Gathering

Fetch all relevant API resources before joining and filtering:

- Batch fetch related collections (accounts, contacts, opportunities) and filter client-side if the API lacks a query parameter for the target key.
- Join datasets on shared identifiers: `event_id`, `account_id`, `show_id`, `batch_id`.
- Always fetch `/api/policies` when available — it defines qualification and exclusion rules.

### Processing Conventions

**Normalization**
- Email: lowercase, trimmed. Empty string (`""`) when missing.
- Phone: digits only. Empty string when missing.
- Dates: ISO 8601 (`YYYY-MM-DD`).

**Sorting**
- Follow the ordering rules declared in the answer template exactly.
- Common defaults: `account_name` ascending, `company_name` ascending, `badge_id` ascending, `row_id` ascending.
- Enum-typed list fields sort in the enum declaration order.

**Controlled Vocabularies**
- Use only the allowed values specified in the answer template for every enum field.
- Do not invent values; if a record fits no defined enum value, classify it under the closest applicable reason or flag it for review.

**Output Format**
- Return one valid JSON object matching the template schema.
- No explanatory prose outside the JSON.
- Do not add extra keys beyond the template.
- Counts and monetary values are integers; use integer USD for amounts.

### Common Business Patterns

**Sponsor Classification**
- Determine sponsor status from orders and invoices.
- Controlled statuses: `paid_deferred`, `open_invoice`, `proposal_only`, `not_sponsor`.
- Compute package amounts in integer USD; for open invoices track paid amount and open balance separately.

**Lead Qualification**
- Exclude sponsor-attendee contacts, inactive/canceled sponsor records, non-business badge types, and CRM accounts already marked disqualified.
- Only qualified non-sponsor leads pass through to the lead handoff.
- Derive opportunity amounts from event-level lead defaults or priority-tier tables in the prompt.

**Deduplication**
- When merging raw import contacts, select a winning row per duplicate key.
- Preserve the winning `row_id` as the `clean_contact_id` and `source_row_id`.
- Track removed duplicate row IDs per key in the duplicate summary.

**CRM Action Assignment**
- Common actions: `create_account`, `update_existing`, `no_import`, `suppress` (for contacts/accounts); `create`, `update`, `no_action`, `no_import` (for campaign members).
- If an existing CRM account matches a qualified entity, use `update_existing`; otherwise `create_account`.
- Suppressed or unqualified records get `no_import`.

**Exclusion Tracking**
- Every removed or excluded record must appear in the exclusion list with a controlled reason (e.g., `sponsor_attendee`, `non_business_badge`, `existing_disqualified`, `missing_contact`, `distributor_only`, `service_only`, `research_only`, `not_target_market`).
- Exclusion counts are aggregated by reason.

**Aggregate Computation**
- Compute totals: pipeline values, revenue by status, qualified/excluded counts, platform coverage, priority-tier counts.
- All computed values must be integers.

**Follow-Up Dates and Tasks**
- Lead follow-up and sponsor-finance follow-up use separate due dates derived from the event.
- Task counts reflect the number of accounts or records requiring action.

### Validation

- Confirm every required top-level key from the answer template is present.
- Verify all list items contain every required key.
- Check that every enum field uses an allowed value.
- Ensure sorting matches the template ordering rules.
- Validate that aggregate counts match the corresponding list lengths.
