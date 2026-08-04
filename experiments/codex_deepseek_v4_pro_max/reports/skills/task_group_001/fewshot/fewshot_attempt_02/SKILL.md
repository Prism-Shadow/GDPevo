The agent is solving a HarborCRM data-integration task. The runner supplies a HarborCRM API base URL and an answer-template JSON file. The agent must gather data from public HarborCRM GET endpoints, apply business rules, and emit a single JSON response conforming to the template.

## Environment

Discover the API base URL from the runner environment. Precedence:
1. `<TASK_ENV_BASE_URL>`
2. `GDPEVO_ENV_BASE_URL` (from `environment_access.md`)

All endpoints are GET only with no authentication.

## API endpoint catalog

```
GET /api/events
GET /api/events?status=<status>
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

Use `curl -s` to call every needed endpoint in parallel before transforming. Prefer multiple concurrent `curl` calls when endpoints are independent.

## Answer template

Load the template from `input/payloads/answer_template.json`. Return JSON that exactly matches its declared top-level keys, required sub-keys, and allowed enum values. Never add undeclared keys.

## Common data-gathering strategy

1. Parse the prompt for the primary entity (event_id, show_id, batch_id, or account_id) and the campaign context.
2. Call the primary entity endpoint to confirm its shape and name.
3. Call all related child and cross-reference endpoints in parallel.
4. Call `/api/policies` when the task references a prospecting policy or compliance rule.
5. Cross-reference CRM accounts, contacts, opportunities, and campaign_members against the event/show/badge/batch records.

## Business rule patterns

### Sponsor classification
Classify sponsor accounts into controlled statuses:
- `paid_deferred` — invoice fully paid (paid_amount >= package_amount).
- `open_invoice` — invoice exists with unpaid balance (paid_amount < package_amount).
- `proposal_only` — sponsor package confirmed but no invoice yet.

Produce sponsor revenue totals including open invoice balance. Exclude inactive/canceled sponsors.

### Lead qualification
Qualified non-sponsor leads must NOT be:
- Sponsor attendees (any badge tied to a sponsor account).
- Inactive or canceled sponsor records.
- Non-business badge types (press, student, staff, guest).
- CRM accounts marked as disqualified.

Use the event's lead opportunity amount for each qualified non-sponsor account. If the event has a per-lead opportunity amount, multiply by qualified count; otherwise use the event's declared opportunity field.

### Exhibitor prospecting
For tradeshow campaigns: filter exhibitors by platform coverage defined in `/api/policies`. Qualified exhibitors build or integrate the target platform types. Exclude distributors, service-only firms, sensor-only vendors, and research-only entities using controlled exclusion reasons (`distributor_only`, `service_only`, `sensor_vendor_only`, `research_only`, `not_target_market`).

### Import batch cleaning
For import batch tasks: deduplicate by email (keep earliest `captured_at`), suppress contacts matching `/api/import_batches/{batch_id}/suppression`, remove rows missing both contact name and email, and cross-reference with existing CRM accounts/contacts to determine `create_account` vs. `update_existing`.

### Priority tier assignment
When the prompt defines priority tiers with demo-request and interest-score thresholds: apply exactly the stated rules. Common tiers map to opportunity sizing: A=120000, B=90000, C=50000 USD unless the prompt specifies otherwise.

## Output formatting rules

- Return **one JSON object only**. No explanatory prose, no markdown fences, no trailing text.
- **Dates**: `YYYY-MM-DD` format.
- **Phone numbers**: digits only, no separators, empty string when missing.
- **Email addresses**: lowercase, trimmed, empty string when missing.
- **USD amounts**: integer (no decimals, no currency symbols).
- **Counts**: integer.
- **Null vs. empty**: use `null` for absent optional identifiers; use `""` for missing contact fields.

## Sorting conventions

Sort rules are always stated in the template or prompt. When sorting:
- Sponsor statuses, qualified lead accounts, and badge-only contacts: sort by `account_name` or `company_name` ascending, then `contact_name` ascending.
- Excluded records: sort by `company_name` ascending, then `contact_name` ascending.
- Badge decisions: sort by `badge_id` ascending.
- Ranked leads: sort by rank ascending (1-based contiguous).
- Platforms within an item: sort in the enum declaration order (AUV, ROV, Underwater Camera).
- Duplicate keys: sort by key ascending.
- Removed rows: sort by row_id ascending.

## CRM action taxonomy

| Action | Meaning |
|---|---|
| `create_account` | Account does not exist in CRM; create it. |
| `update_existing` | Account exists in CRM; update its fields. |
| `create_contact` | Contact does not exist; create under the account. |
| `add_campaign_member` | Add contact as campaign member for the event/campaign. |
| `create_account_contact_campaign_member` | Create account, contact, and campaign member in one go. |
| `create_contact_campaign_member` | Create contact and campaign member under an existing account. |
| `no_action` | Record is present but requires no CRM write. |
| `no_import` | Record is excluded from import entirely. |
| `suppress` | Contact should be actively suppressed. |

## Follow-up date calculation

When the prompt does not specify follow-up dates, derive them from the event/show end date using the policy or a reasonable default (e.g., lead follow-up 30 days after event end; finance follow-up 7 days after event end). Always check `/api/policies` for stated follow-up windows.
