---
name: harbor-crm
description: Prepare HarborCRM handoff, prospecting, and import-ready summaries using the HarborCRM REST API. Use this skill whenever the task involves a HarborCRM event audit, trade-show lead qualification, partner/webinar import batch cleaning, post-event reconciliation, or any HarborCRM API data work that requires cross-referencing events, finance, CRM accounts/contacts/campaign-members/opportunities, trade-show exhibitors, meeting interest, import batches, or policy metadata. Trigger on mentions of HarborCRM, event reconciliation, sponsor handoff, badge reconciliation, trade-show prospecting, qualified lead lists, CRM import batch preparation, contact deduplication, or campaign member reconciliation.
---

# HarborCRM Handoff and Prospecting

You are preparing structured HarborCRM handoff summaries by reading data from the
HarborCRM REST API and applying cross-referencing business rules. The API base
URL is supplied by the runner as `<TASK_ENV_BASE_URL>`. The runner also provides
a JSON answer template (payload) that defines the exact output shape, field
names, enums, and sort order. Always conform exactly to that template.

Return only the JSON response. Do not include explanatory prose outside the
JSON. Do not add fields not declared in the template. Use the exact value for
fields marked `required_value`.

The broader patterns are in [references/api-reference.md](references/api-reference.md) (endpoint
catalog with shapes) and [references/rules.md](references/rules.md) (cross-cutting
business rules for statuses, deduplication, exclusion, follow-up dates, CRM
actions, priority tiering, etc.). Read those when you need the full detail; the
rest of this file lays out the workflow you follow for common task families.

## General Workflow

1. **Read the template first.** The payload `answer_template.json` defines every
   required key, allowed enum value, sort order, and numeric type. Build your
   output to match it exactly.
2. **Ingest API data in parallel.** Fetch every endpoint the prompt and template
   imply you'll need. Use parallel requests; the API is fast and the results are
   small. Fetch policies early — they contain the authoritative enum lists and
   qualification notes.
3. **Apply business rules** from [references/rules.md](references/rules.md).
   These rules cover contact normalization, sponsor-status determination from
   invoices/orders, badge classification, duplicate resolution, suppression
   matching, platform classification from exhibitor descriptions, follow-up
   date arithmetic, and CRM action assignment.
4. **Sort output exactly as the template dictates.** Sorting rules live in the
   template. When the template says ascending by a field, sort
   case-insensitively ascending on that field. When the template specifies a
   controlled enum order, use that order.
5. **Count accurately.** Numeric fields are integers. Sums should match the
   itemized entries. Counts should match the lengths of the corresponding
   arrays. Double-check all aggregate fields before returning.

## Task Families

### Event Audit / Post-Event Handoff

Used when the template requires sponsor statuses, sponsor revenue summaries,
qualified lead accounts, excluded records, follow-up dates, and CRM action
counts. The data sources are:

- `GET /api/events/{event_id}` — event metadata, dates, lead opportunity amount
- `GET /api/events/{event_id}/orders` — sponsor orders with statuses and contacts
- `GET /api/events/{event_id}/badges` — scanned badge records
- `GET /api/finance/invoices?event_id={event_id}` — invoice status and payment data
- `GET /api/crm/accounts` — CRM account list with statuses and disqualification reasons
- `GET /api/crm/contacts` — CRM contact list
- `GET /api/crm/campaign_members?event_id={event_id}` — existing campaign members
- `GET /api/policies` — sponsor status enums and qualification notes

**Sponsor statuses** are derived by joining orders, invoices, and CRM accounts.
See the sponsor-status rule in [references/rules.md](references/rules.md).
Exclude canceled/inactive orders and inactive accounts. Sort by account_name
ascending.

**Qualified lead accounts** are non-sponsor badge attendees whose CRM account is
not disqualified. Cross-reference badge company names against CRM account names
using the fuzzy name-matching rule. For each qualified lead, decide
create_account vs update_existing based on whether a matching CRM account
exists. Assign the event's `lead_opportunity_amount` as the opportunity amount.
Contact details come from the badge, normalized per the contact-hygiene rule.
Sort by account_name ascending.

**Excluded records** list every badge (or campaign member) that was excluded,
with a controlled reason from the exclusion-reason rules. Sort by company_name
ascending, then contact_name ascending.

**Follow-up dates** use the date-arithmetic rule. Lead follow-up is event
`end_date + followup_days_after_end`. Sponsor finance follow-up is event
`end_date + sponsor_followup_days_after_end`.

### Full Post-Event Reconciliation

Extends the event-audit pattern with per-badge decisions, per-campaign-member
action plans, badge-only contact normalization, and exclusion counts. In
addition to the event-audit endpoints, pull
`GET /api/crm/opportunities?event_id={event_id}`.

**Badge decisions** classify every badge as `sponsor_attendee`,
`qualified_non_sponsor_lead`, or `excluded` using the badge-classification
rules. Each gets a `crm_action` (the full action string, e.g.
`create_account_contact_campaign_member`) and an `exclusion_reason` (or null).

**Campaign member actions** reconcile existing campaign members against badge
and order data. Members whose contacts appear in sponsor orders get
`target_status` of `attended_sponsor` or `registered_sponsor`. Badge-only leads
get `attended`. The `subject_key` uses the pattern
`{account_id}:{contact_id}` for existing members and `badge:{badge_id}` for new
badge-only entries. Sort by subject_key ascending.

**Badge-only contacts** are badge records that are not already CRM contacts.
Normalize email and phone per the hygiene rules.

**Exclusion counts** tally each exclusion reason as a separate integer.

### Trade-Show Prospecting

Used when the template requires a filtered, classified list of exhibitors for a
specific campaign. Data sources:

- `GET /api/tradeshows/{show_id}` — show metadata and theme
- `GET /api/tradeshows/{show_id}/exhibitors` — exhibitor records with descriptions
- `GET /api/tradeshows/{show_id}/meeting_interest` — demo requests and interest scores
- `GET /api/crm/accounts` — cross-reference for CRM status
- `GET /api/crm/contacts` — optional cross-reference (when template asks for it)
- `GET /api/policies` — platform enums and qualification notes

**Qualification**: read each exhibitor's `description` and decide whether the
company builds target platforms (qualifies) or is only adjacent (excluded). Use
the platform-classification rules in [references/rules.md](references/rules.md).
The policy's `qualification_note` gives the deciding criterion.

**Platform coverage**: list only the platforms the exhibitor actually covers,
from the policy's `platform_enums` list, sorted in the policy's enum order.

**Exclusion**: near-miss exhibitors that are close but don't qualify get an
exclusion reason from the controlled enum. Reasons like `distributor_only`,
`service_only`, `sensor_vendor_only`, `research_only`, or `not_target_market`.

**CRM overlap**: exhibitors whose `crm_account_id` is non-null and whose CRM
account exists with a non-disqualified status count as CRM overlap. Mark them as
`update_existing`; others as `create_account`.

### Ranked Trade-Show Prospecting

Same data sources as trade-show prospecting, but the template requires ranked
output with priority tiers and opportunity sizing. Apply these additional rules:

- **Ranking order**: demo-requested leads first, sorted by meeting interest
  score descending. Within equal scores, more platforms breaks ties. Within
  that, company name ascending breaks remaining ties. Non-demo leads follow after
  all demo leads, sorted by interest score descending, then platforms, then name.
- **Priority tiers**: assign A/B/C per the tiering rules in
  [references/rules.md](references/rules.md). The template or prompt specifies the
  thresholds and opportunity amounts.
- **CRM action**: `update_existing` when the exhibitor has a matching
  non-disqualified CRM account; `create_account` otherwise.

### Import Batch Preparation

Used when the template requires cleaning a raw contact batch for CRM import.
Data sources:

- `GET /api/import_batches` — batch listing
- `GET /api/import_batches/{batch_id}` — batch metadata with campaign_code
- `GET /api/import_batches/{batch_id}/raw_contacts` — raw import rows
- `GET /api/import_batches/{batch_id}/suppression` — suppression list (emails/phones to block)
- `GET /api/crm/accounts` — cross-reference existing CRM accounts
- `GET /api/crm/contacts` — cross-reference existing CRM contacts
- `GET /api/policies` — contact-hygiene rules

Process in this order:

1. **Normalize** every raw contact: trim/lowercase email, digits-only phone,
   trim company_name and contact_name. Drop rows where contact_name is empty or
   only whitespace (reason: `missing_contact`).
2. **Suppression check**: match each remaining row's normalized email or phone
   against the suppression list. Exact match on either field means the row is
   suppressed (reason: `suppressed`). Also check the CRM contacts list: any CRM
   contact with `opted_out: true` and matching email/phone suppresses the row.
3. **Deduplication**: group remaining rows by normalized email (when non-empty)
   or by normalized phone. Within each group choose the winner by latest
   `captured_at` timestamp. All other rows are removed as `duplicate`. Record
   the winner row_id and all removed row_ids.
4. **CRM cross-reference**: for each surviving clean contact, match company_name
   against CRM accounts using fuzzy name matching (see rules). If a matching
   account exists, `crm_action` is `update_existing` (even without a matching
   contact — contacts are created fresh if needed). If no match,
   `crm_action` is `create_account`. The `existing_account_id` and
   `existing_contact_id` are populated from the match when available, null
   otherwise. Suppressed rows get `crm_action: suppress`. Unusable rows
   (missing_contact) and suppressed rows that weren't suppressed but are now
   dead get `crm_action: no_import`.
5. **Campaign member count**: equals the number of clean contacts (excluding
   suppressed and unusable rows).

See [references/rules.md](references/rules.md) for the duplicate-key format,
fuzzy name matching details, and source_name enum mapping.
