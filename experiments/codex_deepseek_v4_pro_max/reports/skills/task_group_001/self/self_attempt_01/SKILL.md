## When to Use

Use this skill for any HarborCRM data-processing task — event handoff, trade-show prospecting, import-batch preparation, post-event reconciliation, or CRM campaign-member work. HarborCRM is the shared CRM marketing workspace exposed through a REST API.

## Core Operating Rules

### Input Discovery

Every HarborCRM task ships two input files:

- `prompt.txt` — task description, event/show/batch identifiers, relevant API routes, processing rules, and data-classification thresholds.
- `payloads/answer_template.json` — the required JSON output shape, including field names, types, controlled vocabularies, sorting rules, and response constraints.

Read both files completely before making any API call. The template is authoritative for output conformance; the prompt drives business logic.

### API Conventions

- Base URL is always supplied by the runner as `<TASK_ENV_BASE_URL>` (or `GDPEVO_ENV_BASE_URL`).
- All endpoints are GET only. No authentication is required.
- Known public endpoints:

```
GET /api/events
GET /api/events/{event_id}
GET /api/events/{event_id}/orders
GET /api/events/{event_id}/badges
GET /api/events/{event_id}/sponsor_packages
GET /api/finance/invoices?event_id=<event_id>
GET /api/finance/invoices?account_id=<account_id>
GET /api/crm/accounts
GET /api/crm/accounts?status=<status>
GET /api/crm/accounts?owner_region=<owner_region>
GET /api/crm/contacts
GET /api/crm/contacts?account_id=<account_id>
GET /api/crm/opportunities
GET /api/crm/opportunities?event_id=<event_id>
GET /api/crm/opportunities?account_id=<account_id>
GET /api/crm/campaign_members
GET /api/crm/campaign_members?event_id=<event_id>
GET /api/crm/campaign_members?account_id=<account_id>
GET /api/tradeshows
GET /api/tradeshows/{show_id}
GET /api/tradeshows/{show_id}/exhibitors
GET /api/tradeshows/{show_id}/meeting_interest
GET /api/import_batches
GET /api/import_batches/{batch_id}
GET /api/import_batches/{batch_id}/raw_contacts
GET /api/import_batches/{batch_id}/suppression
GET /api/policies
```

- A task's prompt may list a subset of these routes. Prefer the prompt's list, but use any endpoint above when the task logic requires it.

### Output Rules

- Return exactly one JSON object.
- Do not include explanatory prose, markdown fences, or any text outside the JSON object.
- Conform strictly to the template's required top-level keys, item keys, and field types.
- Do not add fields that are not declared in the template.
- When a template declares an enum for a field, use only those exact string values.

### Data Normalization

- **Email**: lowercase and trim. Empty string when no email is supplied.
- **Phone**: digits only (strip all non-numeric characters). Empty string when no phone is supplied.
- **Currency amounts**: always integers in USD. Round or truncate to whole dollars — never output floats.
- **Dates**: `YYYY-MM-DD` string format.
- **Counts**: integers.

### Sorting

Every template declares sorting rules. Apply them exactly:
- If a template says "Sort by X ascending", do a case-sensitive string sort on X.
- If a template says "Sort by badge_id ascending" or similar ID-based sort, sort lexicographically.
- If a template says "Sort in the enum order shown here", use that explicit order.

### CRM Matching and Action Classification

When comparing external records (exhibitors, badge scans, import rows) against existing CRM data:

- Match by company name against `/api/crm/accounts`. A match means the account already exists.
- Match by contact name + company against `/api/crm/contacts` within a matched account.
- If an account does not exist in CRM → crm_action is `create_account`.
- If an account exists in CRM → crm_action is `update_existing`.
- If a contact does not exist under a matched account → contact action is `create_contact`.
- If a contact already exists under a matched account → contact action is `update_existing`.
- Records that should not be imported at all → crm_action is `no_import`.

### Exclusion Patterns

Excluded records must always carry a `reason` or `exclusion_reason` drawn from the template's allowed enum. Common exclusion reasons across task types:

- **Sponsor-related**: `sponsor_attendee`, `inactive_sponsor_record` — records tied to sponsors, or sponsor records that are canceled/inactive.
- **Badge classification**: `non_business_badge` — press, guest, staff, or other non-business badge types.
- **CRM state**: `existing_disqualified` — an account already marked disqualified in CRM.
- **Contact quality**: `missing_contact` — no usable contact name.
- **Suppression**: `suppressed` — email or domain appears on the suppression list.
- **Duplicate**: `duplicate` — duplicate row removed in favor of a winning row.
- **Trade-show exclusions**: `distributor_only`, `service_only`, `sensor_vendor_only` (or `sensor_only`), `research_only`, `not_target_market`.

### Sponsor Status Classification

When a task involves sponsor financial reconciliation, classify sponsor accounts into one of these controlled statuses:

- `paid_deferred` — invoice fully paid, or payment deferred per policy.
- `open_invoice` — invoice issued but not fully paid.
- `proposal_only` — no invoice exists; only a proposal/sponsor package record.

Additional sponsor-related statuses that may appear: `not_sponsor`.

### Priority Tiering

When a trade-show prospecting task uses priority tiers (`A`, `B`, `C`):
- Tier assignment is driven by demo requests, interest scores, or both as specified in the prompt.
- Opportunity sizing per tier is task-specific — read it from the prompt, not from any fixed lookup.

### Campaign Member Handling

- For event-based tasks, campaign members come from `/api/crm/campaign_members?event_id=<event_id>`.
- Actions: `create`, `update`, `no_action`, `no_import`, `add_campaign_member`.
- Target statuses (when template requires them): `attended`, `attended_sponsor`, `registered_sponsor`, `excluded`.
- Members who attended (badge scan present) and are not excluded → target status `attended`.
- Members who are sponsor-affiliated → target status `attended_sponsor`.

### Follow-up Dates

- When a template asks for `lead_due_date` or `sponsor_finance_due_date`, derive it from event date + policy (typically 7–14 days post-event, unless a `/api/policies` entry overrides).
- Check `/api/policies` for any follow-up window policies and apply them.

### Import Batch Processing

For import-batch tasks (`/api/import_batches`):
- Deduplicate raw contacts by email (normalized) within the batch. The winning row is the earliest `captured_at` timestamp; if tied, prefer the lower `row_id`.
- Suppressed contacts are those whose email domain or exact email appears in the batch's suppression list.
- `unusable` rows are those with `missing_contact` (no contact name).
- Clean contacts are those surviving deduplication and not suppressed/unusable.

### Trade-Show Prospecting

For trade-show tasks (`/api/tradeshows`):
- Qualified exhibitors are those whose `relationship_type` or business description matches the campaign's target market and whose platform offerings match the campaign's platform enums.
- Use `/api/tradeshows/{show_id}/meeting_interest` for demo-request and meeting-interest-score data.
- Match exhibitors against `/api/crm/accounts` to determine `create_account` vs `update_existing`.

### Workflow

1. Read `prompt.txt` — extract identifiers (event_id, show_id, batch_id), task type, special processing rules, and threshold values.
2. Read `payloads/answer_template.json` — memorize every required key, allowed enum, sorting rule, and field type.
3. Call all relevant API endpoints. Pull every resource the prompt mentions (even indirectly).
4. Join and cross-reference the API responses to classify, qualify, exclude, and count.
5. Build the output object key-by-key from the template. Apply sorting rules last.
6. Return the JSON object with no surrounding text.
