**HarborCRM Task Solver**

Use this skill when the prompt involves HarborCRM data enrichment, classification, reconciliation, or import preparation. The skill covers event audits, trade-show prospecting, batch import cleaning, and post-event reconciliation.

**Core Workflow**

1. **Read the prompt and answer template** — Every task ships an `input/payloads/answer_template.json` (or equivalent). Parse it first to understand required keys, enum values, sort orders, and field types. The template is the contract you must satisfy.
2. **Fetch all relevant API data** — Call every HarborCRM endpoint that the prompt references. The API base URL is always supplied by the runner as `<TASK_ENV_BASE_URL>` or the `GDPEVO_ENV_BASE_URL` environment variable. See the API reference below for the full endpoint catalog.
3. **Apply business rules** — Use policy data (`GET /api/policies`) and task-specific instructions to filter, classify, and enrich records. Never skip this step; the raw API data is always broader than what the template expects.
4. **Produce JSON-only output** — Return exactly one JSON object matching the template. No explanatory prose outside the JSON. No extra keys.

**API Reference**

All endpoints are read-only GET. No authentication is required for business endpoints. The base URL is `<TASK_ENV_BASE_URL>`.

- Events: `/api/events`, `/api/events?status=<status>`, `/api/events/{event_id}`
- Event details: `/api/events/{event_id}/orders`, `/api/events/{event_id}/badges`, `/api/events/{event_id}/sponsor_packages`
- Finance: `/api/finance/invoices?event_id=<event_id>`, `/api/finance/invoices?account_id=<account_id>`
- CRM Accounts: `/api/crm/accounts`, `/api/crm/accounts?status=<status>`, `/api/crm/accounts?owner_region=<owner_region>`
- CRM Contacts: `/api/crm/contacts`, `/api/crm/contacts?account_id=<account_id>`
- CRM Opportunities: `/api/crm/opportunities`, `/api/crm/opportunities?event_id=<event_id>`, `/api/crm/opportunities?account_id=<account_id>`
- CRM Campaign Members: `/api/crm/campaign_members`, `/api/crm/campaign_members?event_id=<event_id>`, `/api/crm/campaign_members?account_id=<account_id>`
- Trade Shows: `/api/tradeshows`, `/api/tradeshows/{show_id}`, `/api/tradeshows/{show_id}/exhibitors`, `/api/tradeshows/{show_id}/meeting_interest`
- Import Batches: `/api/import_batches`, `/api/import_batches/{batch_id}`, `/api/import_batches/{batch_id}/raw_contacts`, `/api/import_batches/{batch_id}/suppression`
- Policies: `/api/policies`

**Common Classification Patterns**

*Sponsor Status Classification*

Determine sponsor financial status by cross-referencing orders, invoices, and sponsor packages from the event endpoints. Use only these controlled values:
- `paid_deferred` — invoice exists and is fully paid (paid_amount equals package_amount or invoice amount).
- `open_invoice` — invoice exists with unpaid balance (paid_amount < invoice amount).
- `proposal_only` — sponsor has an order/package but no invoice exists.

When computing totals, `paid_deferred` and `open_invoice` aggregate the package amount; `open_invoice_balance` uses only the unpaid portion of open invoices. Unpaid sponsor accounts are those with `open_invoice` or `proposal_only` status (proposals have no balance but still need follow-up for conversion).

*Lead Qualification*

A record is a qualified non-sponsor lead when:
- The company is not a sponsor for the event.
- The company's CRM account is not already disqualified (check account status).
- For badge-based tasks, the badge is a business badge (not press, student, or other non-business type).

CRM actions for qualified leads:
- `create_account` — the company has no existing CRM account.
- `update_existing` — the company already has a CRM account.
- Contacts follow the same pattern: `create_contact` when no matching contact exists, `update_existing` when one does.
- Campaign members should be created with `add_campaign_member`.

*Exclusion Categories*

Records that do not qualify as leads should appear in the exclusion/near-miss list with one of these reasons:
- `sponsor_attendee` — the contact belongs to a sponsor company.
- `existing_disqualified` — the CRM account status indicates disqualification.
- `non_business_badge` — the badge type is press, student, academic, or similar.
- `missing_contact` — no usable contact information exists.

For trade-show prospecting, use:
- `distributor_only` — exhibitor is a distributor, not a manufacturer/OEM.
- `service_only` — exhibitor provides services only, not products.
- `sensor_vendor_only` / `sensor_only` — exhibitor sells components, not platforms.
- `research_only` — exhibitor is a research institution.

*Import Batch Preparation*

When preparing an import batch:
- Deduplicate by email (primary key). The winner is the most complete row; prefer rows with phone, then most recent `captured_at`. Report duplicate keys with winner and removed row IDs.
- Suppress contacts matching the suppression list (check the batch's `/suppression` endpoint).
- Mark rows with missing contact name as `missing_contact`.
- Determine CRM action: `create_account` for new companies, `update_existing` for known CRM accounts, `no_import` for duplicate/unusable rows, `suppress` for suppressed rows.

*Contact Normalization*

- `normalized_email` — lowercase, trimmed. Empty string if not provided.
- `normalized_phone` — digits only, no formatting. Empty string if not provided.

*Badge Classification*

Classify each badge scan into exactly one category:
- `sponsor_attendee` — the badge company matches a sponsor account for the event.
- `qualified_non_sponsor_lead` — non-sponsor, business badge, CRM account not disqualified.
- `excluded` — non-business badge type or disqualified CRM account.

CRM actions for badges:
- `create_account_contact_campaign_member` — new company, new contact, needs campaign membership.
- `create_contact_campaign_member` — existing company, new contact, needs campaign membership.
- `add_campaign_member` — existing company and contact, just needs campaign membership.
- `update_campaign_member` — campaign member record already exists and needs status update.
- `no_action` — sponsor attendee already tracked (campaign member exists with attended_sponsor status).
- `no_import` — excluded badge with no usable data.

*Campaign Member Actions*

For each campaign member record:
- `create` — no existing campaign member record; create one.
- `update` — campaign member exists but status needs updating.
- `no_action` — campaign member exists with correct status, no change needed.
- `no_import` — excluded record, do not import.

Target status values: `attended_sponsor` (sponsor who attended), `registered_sponsor` (sponsor registered but didn't attend), `attended` (non-sponsor who attended), `excluded` (non-business or disqualified).

*Priority Tiers and Opportunity Sizing*

When ranking leads by tier:
- `A` — highest priority. For demo-based ranking: requested demo AND interest score ≥ 90.
- `B` — medium priority. For demo-based ranking: requested demo AND interest score ≥ 80.
- `C` — standard priority. All other qualified leads.

Opportunity amounts use the event's lead opportunity amount (from event data or policy) for event-based tasks. For tier-based tasks, the prompt specifies tier amounts.

**Sorting Rules**

Always apply the sort order specified in the prompt or answer template. Common patterns:
- Sort sponsor/account lists by `account_name` ascending.
- Sort qualified leads by `company_name` ascending unless a custom ranking is specified.
- Sort excluded records by `company_name` ascending, then `contact_name` ascending.
- Sort badge decisions by `badge_id` ascending.
- Sort campaign member actions by `subject_key` ascending.
- Sort duplicate keys and removed rows by their natural identifiers ascending.

**Common Aggregations**

- `sponsor_revenue_totals` — sum package amounts by status; open_invoice_balance sums unpaid portions only.
- `lead_pipeline_total` — sum of opportunity amounts for all qualified non-sponsor leads.
- `crm_action_counts` — count each CRM action type (accounts_create, accounts_update, contacts_create, contacts_update, campaign_members_create, campaign_members_update).
- `import_action_totals` — count create_account, update_existing, no_import, suppress actions.
- `exclusion_counts` — count exclusions by reason category.
- `aggregate_counts` / `summary` — qualified totals, platform counts, priority counts, excluded counts.

**Follow-Up Dates**

When the prompt requires follow-up due dates, compute them from event dates or the current date using policy rules. Lead follow-up typically has a longer window than sponsor finance follow-up. Each due date is a `YYYY-MM-DD` string.

**Error Handling**

- If an API endpoint returns empty or errors, treat missing data as empty lists/objects rather than failing.
- If a required field in the template cannot be determined, use `null` (for nullable fields) or `0`/`""` (for numeric/string fields) rather than omitting the field.
- Always validate that the final JSON parses and that every required key from the template is present.

**Execution Checklist**

Before producing the final output, verify:
- [ ] Every required top-level key from the answer template is present.
- [ ] All enum values match the allowed values exactly (case-sensitive).
- [ ] Sort orders match the prompt/template specification.
- [ ] Numeric values are integers where required, with correct units (USD, counts).
- [ ] Excluded records have a valid reason from the controlled vocabulary.
- [ ] CRM action counts are internally consistent (they sum to the right totals).
- [ ] The output is pure JSON with no surrounding prose or markdown fences.

**Key Principle**

The HarborCRM API provides raw data. The prompt provides business logic. The answer template provides structure. Your job is to bridge all three: fetch data, apply rules, fill the template. Do not invent data, do not skip exclusion rules, and do not add fields the template does not declare.
