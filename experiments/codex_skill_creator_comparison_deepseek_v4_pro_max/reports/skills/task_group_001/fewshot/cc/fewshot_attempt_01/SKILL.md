---
name: harbor-crm
description: Query the HarborCRM REST API to retrieve accounts, contacts, events, tradeshows, finance records, policies, import batches, and related business data, then cross-reference results, apply policy-driven qualification rules, and produce a strictly conformant JSON output. Use this skill whenever the user mentions HarborCRM, Harbor CRM, CRM data retrieval, event handoff, trade-show prospecting, batch import preparation, lead qualification, sponsor reconciliation, campaign-member management, or any task that asks you to query a CRM API and return structured JSON.
---

# HarborCRM API

Use the HarborCRM REST API (`<TASK_ENV_BASE_URL>`) to retrieve business data, cross-reference results across endpoints, apply policy-driven qualification, and produce strictly conformant JSON against a supplied answer template.

## Workflow

Follow this ordered approach for every HarborCRM task. Skip steps only when the task clearly does not need them.

### 1. Read the answer template first

The prompt always names an answer template file (usually `input/payloads/answer_template.json`). Read it immediately. It defines the exact output shape: required top-level keys, enum values for every controlled field, sort orders, nesting, and field presence/absence rules. Every structural decision flows from the template -- do not improvise key names, enum values, or sort directions.

When the template declares enum values (e.g., `"allowed_values": ["AUV", "ROV", "Underwater Camera"]`), use only those exact strings. When it declares sort orders, follow them literally. When it says "do not add fields not declared in this template", respect that.

### 2. Identify the data sources

From the prompt, extract:
- The task identifier: an `event_id`, `show_id`, or `batch_id`.
- The list of endpoints you will need. Common patterns:
  - Event tasks: `/api/events/{id}`, `/api/events/{id}/orders`, `/api/events/{id}/badges`, `/api/events/{id}/sponsor_packages`, `/api/finance/invoices?event_id={id}`
  - Tradeshow tasks: `/api/tradeshows/{id}`, `/api/tradeshows/{id}/exhibitors`, `/api/tradeshows/{id}/meeting_interest`
  - Import-batch tasks: `/api/import_batches/{id}`, `/api/import_batches/{id}/raw_contacts`, `/api/import_batches/{id}/suppression`
  - CRM tasks: `/api/crm/accounts`, `/api/crm/contacts`, `/api/crm/opportunities`, `/api/crm/campaign_members` (with `event_id` or `account_id` filter as needed)
  - Policy tasks: `/api/policies` (always fetch this when qualification rules are involved)

Fetch independent collections in parallel. See `references/api-catalog.md` for the full endpoint list and typical response shapes.

### 3. Read and apply the policies

`GET /api/policies` returns the qualification rules that determine who is in, who is out, and what actions to take. Read the policies endpoint carefully and translate every relevant rule into concrete conditions:

- **Sponsor policies** define which order/invoice states map to `paid_deferred`, `open_invoice`, `proposal_only`, and whether inactive/canceled sponsors must be excluded.
- **Lead-qualification policies** define which non-sponsor entities qualify (by platform, relationship type, account status, region, etc.) and which must be excluded (distributor-only, service-only, research-only, already-disqualified, non-business, etc.).
- **Import policies** define cleansing, deduplication, and suppression rules for batch contacts.
- **Prospecting policies** define qualified platform coverage, demo-request prioritization, and opportunity sizing tiers.

Treat policies as the source of truth. When a policy says "exclude accounts with status=disqualified", that overrides any other signal. Do not carry forward records that a policy explicitly excludes.

### 4. Cross-reference the data

Map records across endpoints to build a complete picture per entity. Common joins:

| Join | Left side | Right side | Match key |
|------|-----------|------------|-----------|
| Sponsor accounts | orders | accounts | `account_id` |
| Sponsor finance | orders | invoices | `invoice_id` or `account_id` |
| Badge attendees | badges | accounts, contacts | `company_name` to `account_name`, `contact_name` to contact record |
| Campaign members | campaign_members | accounts, contacts | `account_id`, `contact_id` |
| Exhibitors vs CRM | exhibitors | accounts | `company_name` to `account_name` |
| Import contacts vs CRM | raw_contacts | accounts, contacts | `email`, normalized `company_name` |
| Duplicate detection | raw_contacts | raw_contacts | `email` (normalized lowercase) |

**Matching rules:**
- Prefer exact ID matches (`account_id`, `contact_id`).
- When IDs are absent, match on normalized keys: lowercase trimmed email, digits-only phone, lowercase trimmed company name.
- When a sponsor has an order but no matching CRM account, treat it with whatever status the order and invoice data support -- do not force-fit it into a CRM account that does not exist.
- When a badge has no matching CRM account or contact, classify it as a badge-only lead. Normalize its email and phone for the output even when CRM data is missing.

### 5. Classify every record

For each entity in scope, assign the exact enum value required by the answer template. Common classification dimensions:

**Sponsor status** (from invoices + orders + policies):
- `paid_deferred`: full payment received or payment deferred by policy
- `open_invoice`: partial payment, balance outstanding
- `proposal_only`: no invoice issued yet

**Lead qualification** (from badges/contacts + policies):
- Determine whether the entity is a sponsor attendee, qualified non-sponsor lead, or excluded.
- For each qualified lead, classify the CRM action: `create_account`, `update_existing`, `create_contact`, `update_existing`, `add_campaign_member`, `no_action`, `no_import`.

**Exclusion reasons** (from policies):
- `sponsor_attendee`, `existing_disqualified`, `inactive_sponsor_record`, `non_business_badge`, `missing_contact`, `distributor_only`, `service_only`, `sensor_vendor_only`/`sensor_only`, `research_only`, `not_target_market`, `duplicate`, `suppressed`.

**Platform coverage** (from exhibitor data + policies):
- Use only the allowed enum values: `AUV`, `ROV`, `Underwater Camera`.

**Priority tiers** (from policies):
- `A`, `B`, `C` -- apply the policy's tiering rules exactly: score thresholds, demo-request status, platform breadth.

### 6. Build the output JSON

Construct the response object one top-level key at a time, following the answer template's structure exactly:

- Populate every required key with the correct type (object, array, string, integer).
- Use the template's enum values verbatim -- do not invent synonyms or abbreviations.
- Apply the template's sort orders: sort account lists by `account_name` ascending, badge lists by `badge_id` ascending, excluded records by `company_name` then `contact_name` ascending, ranked leads by `rank` ascending.
- For integer fields (counts, USD amounts), ensure they are genuine integers, not floats or strings.
- For dates, use `YYYY-MM-DD` format.
- For nullable fields (`"type": "string or null"`), use `null` (not `""` and not `"none"`) when no value exists.
- Normalize emails to lowercase trimmed strings and phones to digits-only strings. Use `""` only when the field is explicitly optional and no data is available.

**Counting rules:**
- Counts must reflect the actual number of records in the corresponding output arrays. If the output lists 3 qualified leads, the `qualified_lead_count` must be 3.
- CRM action counts (`accounts_create`, `accounts_update`, `contacts_create`, `contacts_update`, `campaign_members_create`, `campaign_members_update`, `no_import`, `suppress`) must sum consistently: every record in scope should be accounted for.

**Deduplication:**
- When handling import batches, deduplicate on normalized email first. Among duplicates, prefer the row with the richest data (most non-empty fields, earliest `captured_at`, or lowest `row_id` -- whichever the policy or template signals).
- Record every removed duplicate row in the removal summary with the correct reason and the winner's row ID.

### 7. Validate before returning

Before submitting the JSON:
- Check that every required top-level key from the template is present.
- Verify counts match their corresponding list lengths.
- Confirm all enum values are from the template's allowed set.
- Confirm sort orders match the template's directives.
- Strip any explanatory prose, markdown fences, or commentary. Return **only** the JSON object.

## Cross-referencing deep dive

The most error-prone step is matching records across API responses. Here is the detailed approach:

### Sponsor account reconciliation

1. Fetch the event's orders to get sponsor account IDs and package amounts.
2. Fetch the event's sponsor packages (if available) to confirm package names and amounts.
3. Fetch finance invoices filtered by `event_id`. Match each order to its invoice using `invoice_id` or `account_id`.
4. For each sponsor account, determine status from the invoice data: if `paid_amount >= package_amount` then `paid_deferred`; if `paid_amount > 0` but less than full then `open_invoice`; if no invoice exists then `proposal_only`.
5. Compute `open_balance = package_amount - paid_amount` for open-invoice sponsors.
6. Cross-reference with CRM accounts to get the correct `account_name`. If a sponsor appears in orders but not in CRM accounts, use the name from the order data.
7. Apply policies: exclude sponsors marked inactive or canceled.

### Badge-to-lead pipeline

1. Fetch the event's badges.
2. Fetch CRM accounts and contacts.
3. For each badge, match the company name to a CRM account (normalized comparison).
4. For each badge, match the contact name to a CRM contact under that account.
5. Classify each badge:
   - If the company matches a sponsor account: `sponsor_attendee`, exclude from lead pipeline.
   - If the badge has a non-business classification (per policy): `non_business_badge`, exclude.
   - If the company matches a CRM account with `status=disqualified`: `existing_disqualified`, exclude.
   - If the company has no matching CRM account and is not a sponsor: `qualified_non_sponsor_lead`, action `create_account_contact_campaign_member`.
   - If the company matches a CRM account but contact is new: `qualified_non_sponsor_lead`, action `create_contact_campaign_member`.
6. For each excluded badge, record the company name, contact name, and the primary exclusion reason.

### Campaign member decisions

1. Fetch existing campaign members for the event.
2. For each badge that falls into scope (sponsor attendees + qualified leads):
   - If the subject already has a campaign member record: `update` or `no_action` depending on whether status needs to change.
   - If the subject has no campaign member record: `create`.
   - Assign `target_status` based on classification: `attended_sponsor` for sponsor attendees, `attended` for qualified leads, `registered_sponsor` for sponsors with registrations but no badge scan.
3. For sponsor registrants without a badge scan, do not create campaign members from badge data, but record them if they appear in campaign member queries.

### Trade-show exhibitor qualification

1. Fetch exhibitors, meeting interest, CRM accounts, and policies.
2. For each exhibitor, check platform coverage against the prospecting policy's allowed platforms.
3. Check relationship type: distributors, service providers, sensor-only vendors, and research-only entities are typically excluded.
4. For qualified exhibitors, check if they exist in CRM (`crm_action = update_existing`) or not (`crm_action = create_account`).
5. Apply meeting-interest data: demo requests and interest scores drive priority tiering.
6. Rank per the task's sort order (usually demo-first, then score, then platform breadth, then company name).

### Import batch cleansing

1. Fetch raw contacts and suppression rules for the batch.
2. Fetch CRM accounts and contacts for overlap detection.
3. Normalize all emails and phones in the raw contacts.
4. Deduplicate on normalized email: for each duplicate group, pick a winner row (richest data) and mark the rest as `duplicate` removals.
5. Apply suppression: remove any row whose email matches a suppression rule; mark as `suppressed`.
6. Remove rows with missing contact data (`missing_contact`).
7. For surviving rows, classify CRM action by checking CRM overlap on account and contact.
8. Compute action totals and the campaign-member import count (surviving clean contacts that should become campaign members).

## Field-level rules

These rules apply regardless of the specific task:

- **Currency:** All monetary amounts are integers in USD. No decimal points, no currency symbols.
- **Null handling:** Fields declared as `string or null` or `null` in the template use JSON `null`, never the string `"null"` or empty string `""`. Fields declared as `string` with no null option use `""` when data is absent.
- **Empty arrays:** When a list has no entries, use `[]` not `null` or omission.
- **Sort stability:** All sorts are case-sensitive ascending (A-Z, then a-z) unless the template specifies otherwise.
- **Enum ordering in platform lists:** When the output includes a `platforms` array, sort its values in the order the template declares them (e.g., `AUV`, `ROV`, `Underwater Camera`), not by runtime encounter order.
- **Date formulas:** Follow-up due dates are typically computed from event dates (e.g., event end + N days). Use the event record's date fields when available; otherwise use the policy's stated window.

## Typical task patterns

Recognize which pattern the prompt matches, then lean into the corresponding section above:

| Pattern | Hallmarks | Primary sections |
|---------|-----------|------------------|
| Post-event handoff | event_id, badges, orders, sponsors, campaign members | Sponsor account reconciliation, Badge-to-lead pipeline, Campaign member decisions |
| Trade-show prospecting | show_id, exhibitors, meeting interest, platform coverage | Trade-show exhibitor qualification |
| Import batch preparation | batch_id, raw contacts, suppression, deduplication | Import batch cleansing |

Some tasks combine patterns (e.g., a post-event reconciliation that also includes badge-level handling and campaign member decisions). Apply every relevant section.

## Common mistakes to avoid

- **Inventing enum values.** The template is the authority. Do not write `"paid"` when the template says `"paid_deferred"`.
- **Sorting by the wrong field.** The template always specifies the sort key. Read it carefully and re-check before returning.
- **Using floats for currency.** All amounts are integer USD.
- **Omitting exclusion records.** Excluded records are part of the output schema. Populate them even when empty (`[]`).
- **Counting incorrectly.** If the output has 2 qualified leads, the count field must be 2. Recalculate counts from the final lists, not from intermediate state.
- **Wrapping JSON in markdown.** Return pure JSON. No ```json``` fences, no "Here is the result:" prose.
- **Overlooking policy details.** Policies may have compound conditions. Read them thoroughly and check every record against every applicable rule.
- **Using the wrong identifier for API calls.** `event_id` and `show_id` are distinct. Use the one the prompt specifies.

## Quick reference

For the complete list of HarborCRM API endpoints and their typical response fields, read `references/api-catalog.md`.
