# HarborCRM Business Rules

This document codifies the reusable cross-cutting business rules derived from
HarborCRM handoff and prospecting tasks. Apply these rules across all task
families unless a specific task's prompt or template overrides them.

## Contact Hygiene and Normalization

### Email

Trim leading/trailing whitespace. Convert to lowercase. An email that is empty
or whitespace-only after trimming is treated as "no email provided."

### Phone

Strip all non-digit characters (spaces, dashes, dots, parentheses, leading
`+1`, leading `1` prefix, and similar formatting). The result is a digits-only
string. An empty result after stripping is "no phone provided." Keep the
leading country code if it appears in the raw data as `+{N}`; otherwise the
default US `1` prefix is already the convention on the data set.

### Contact Name

Trim whitespace. If empty or only whitespace, the record is `missing_contact`
and cannot be imported.

### Company Name

Trim whitespace. Use for fuzzy matching against CRM account names (see below).

## Sponsor Status Derivation

Derive sponsor status from the combination of orders and invoices. The
authoritative status values are in the `policies.sponsor_handoff.status_enums`
list.

For each sponsor order:
- If the order status is `canceled`, the sponsor is inactive. Exclude from
  sponsor statuses and revenue summaries.
- If an invoice exists and `invoice.status` is `paid_deferred`, the sponsor
  status is `paid_deferred`. Paid amount and open balance come from the
  invoice. The package amount is the order `amount`.
- If an invoice exists and `invoice.status` is `open`, the sponsor status is
  `open_invoice`. The paid amount is the invoice's `paid_amount`. The open
  balance is `amount - paid_amount`. The package amount is the order `amount`.
- If no invoice exists (or order status is `proposal_sent`), the sponsor
  status is `proposal_only`. The package amount is the order `amount`. Paid
  amount and open balance are zero. Invoice ID is null.

### Sponsor Revenue Totals

- `paid_deferred`: sum of package amounts for all `paid_deferred` status
  sponsors.
- `open_invoice`: sum of package amounts for all `open_invoice` status
  sponsors.
- `proposal_only`: sum of package amounts for all `proposal_only` status
  sponsors.
- `open_invoice_balance`: sum of open balances for all `open_invoice` status
  sponsors.

When a task asks for `unpaid_sponsor_total_usd` or similar, sum the amounts
that are not fully paid (open invoices + proposal-only, excluding
paid_deferred).

## Badge Classification and Exclusion

Classify each badge into one of three buckets:

### sponsor_attendee

A badge is `sponsor_attendee` when:
- The badge company name matches a confirmed or proposal sponsor order's
  account_name, OR
- The badge contact name appears in the `ticket_contacts` list of a
  confirmed or proposal sponsor order, OR
- The badge_type is `sponsor`.

Sponsor badges are excluded from lead lists but may still need CRM actions
(see CRM Actions below). Their exclusion reason is `sponsor_attendee`.

### excluded

A badge is `excluded` (not a lead) for any of these reasons:
- `non_business_badge`: badge_type is `student` or `press`.
- `existing_disqualified`: badge company name resolves to a CRM account with
  `status` of `disqualified`.
- `missing_contact`: badge has no contact_name (empty/whitespace only).

### qualified_non_sponsor_lead

All remaining non-sponsor, non-excluded badges with a usable contact name.

### Exclusion Counts

Tally each exclusion reason as a separate count across all badges. The
exclusion reasons are: `sponsor_attendee`, `non_business_badge`,
`existing_disqualified`, `missing_contact`.

## CRM Account Matching (Fuzzy)

When cross-referencing an external company name (from a badge, batch import, or
exhibitor) against the CRM account list:

1. Normalize both sides: lowercase, trim, collapse whitespace, strip trailing
   punctuation symbols (`,`, `.`, `Inc`, `Inc.`, `LLC`, `Ltd`, `Corp`,
   `Corp.`, etc.).
2. Test exact match on the normalized names.
3. If no exact match, test whether one normalized name is a prefix/suffix of
   the other (e.g., "HelioWare Mfg." matches "HelioWare Manufacturing").
4. If no prefix/suffix match, flag as "no match." The external record gets
   `create_account` if it is a qualified lead with no CRM account.
5. When the external name's domain/industry matches a CRM account and the
   names are close (sharing a root word), consider it a match. Use the CRM
   account's `domain` and `name` for this tiebreak.

A match exists only when the CRM account's `status` is not `disqualified`.
Disqualified accounts count as "no match" for lead purposes.

## CRM Actions

### For Leads (Event Audit / Reconciliation)

When a badge is a qualified non-sponsor lead:
- If badge company name matches an existing CRM account: the lead's account
  action is `update_existing`. The account and contact already exist, but the
  contact might need creating if the badge contact isn't already in CRM.
  Campaign member action is `add_campaign_member`.
- If badge company name has no CRM match: the lead needs full creation —
  `create_account` and `create_contact`, plus `add_campaign_member`.

When a badge is a sponsor attendee:
- If the badge contact isn't in CRM as a contact for the matching sponsor
  account, action is `create_contact_campaign_member`. If they are already a
  campaign member, action may be `no_action` or `update_campaign_member`.
- If the badge contact is already a campaign member with correct status,
  action is `no_action`.

### For Import Batch Contacts

For each surviving clean contact after deduplication and suppression:
- If CRM account match exists: `crm_action` is `update_existing`. Even
  without a matching contact, the account exists; the contact import creates
  a new contact under that account.
- If no CRM account match: `crm_action` is `create_account`.
- Suppressed rows: `crm_action` is `suppress`.
- Unusable rows (missing contact, duplicates): `crm_action` is `no_import`.

### CRM Action Counts

Standard count fields include:
- `accounts_create`: number of records getting `create_account`
- `accounts_update`: number of records getting `update_existing`
- `contacts_create`: number of records where a new contact must be created
- `contacts_update`: number of records where an existing contact is updated
- `campaign_members_create`: number of new campaign member adds
- `campaign_members_update`: number of existing campaign member updates

### Campaign Member Statuses

When reconciling existing campaign members:
- Members whose contacts appear as ticket contacts on confirmed sponsor
  orders and who have `status` `attended_sponsor` in campaign members are
  already correct → `no_action`.
- Members whose contacts appear as ticket contacts on confirmed sponsor
  orders but have `status` `registered_sponsor` → `no_action` (they didn't
  attend, but they registered).
- New badge-only leads → `create` with `target_status` `attended`.
- New sponsor badge attendees not already in campaign members → `create` with
  `target_status` `attended_sponsor`.

### Subject Key Format

- Existing CRM members: `{account_id}:{contact_id}`
- New badge-only entries (no CRM match): `badge:{badge_id}`

## Follow-Up Date Arithmetic

- Lead follow-up due date: `end_date + followup_days_after_end` (in days).
  Format as `YYYY-MM-DD`.
- Sponsor finance follow-up due date: `end_date + sponsor_followup_days_after_end`
  (in days). Format as `YYYY-MM-DD`.

These dates come from the event object.

## Follow-Up Task Counts

- `lead_task_count`: equals the number of qualified lead accounts.
- `sponsor_finance_task_count`: equals the number of sponsor accounts with
  outstanding financial action needed. This includes `open_invoice` sponsors
  (unpaid balance) and `proposal_only` sponsors (no payment yet). Fully paid
  `paid_deferred` sponsors do not need finance follow-up.

## Platform Classification (Trade Show Prospecting)

For each exhibitor at a trade show, read the `description` field and cross-
reference with CRM account info to decide classification.

### Qualification Decision

An exhibitor qualifies for the campaign when its description indicates it
builds or OEM-manufactures platforms in the target category. The policy's
`qualification_note` gives the guiding philosophy.

Key signals of qualification:
- Description explicitly mentions building, manufacturing, or OEM-producing
  the target platform types (AUVs, ROVs, underwater cameras).
- Description mentions OEM payload bays, sensor integration, or embedding
  sensors into platforms they build.
- CRM account industry is a platform-building domain (e.g., "Marine
  robotics", "Aquaculture robotics", "Underwater cameras").

Key signals of exclusion:
- Description says they distribute, resell, or are a sales agent for other
  brands (`distributor_only`).
- Description says they provide consulting, testing, or operational services
  without building platforms (`service_only`).
- Description says they make only sensors/probes, not platforms
  (`sensor_vendor_only` or `sensor_only`).
- Description is pure research or academic (`research_only`).
- Description is for a market the campaign doesn't target (`not_target_market`).

### Platform Coverage

List only the platform types the exhibitor actually covers from the policy's
`platform_enums`. Determine coverage from the exhibitor's description and
CRM account industry. Sort in the enum order listed in the policy.

### Priority Tiering (Ranked Prospecting)

When the task assigns priority tiers with opportunity sizing:

- `A`: demo requested + interest score >= 90. Opportunity value is specified
  in the task prompt (typically the highest tier value).
- `B`: demo requested + interest score >= 80 (but below 90). Opportunity
  value is the mid-tier value from the prompt.
- `C`: all other qualified leads (non-demo or score < 80). Lowest tier value.

### Ranking Order

Combine leads and sort them into a single ranked list:
1. Demo-requested leads first, sorted by interest score descending.
2. Within equal interest scores, more platforms breaks the tie.
3. Within that, company name ascending breaks remaining ties.
4. Non-demo leads follow after all demo leads, sorted by interest score
   descending, then platform count, then company name.
5. Assign contiguous 1-based ranks in this order.

## Import Batch Deduplication

### Duplicate Key

Group raw contacts by:
- Normalized email (when non-empty), using format `email:{normalized_email}`.
- Otherwise, by normalized phone, using format `phone:{normalized_phone}`.

Rows with empty email AND empty phone are not grouped; handle them
individually (they are likely `missing_contact`).

### Winner Selection

Within each group, the winner is the row with the latest `captured_at`
timestamp. If timestamps are equal, use the lowest `row_id` as tiebreaker.

All non-winning rows are removed with reason `duplicate`.

### Duplicate Key Format in Output

```json
{
  "key": "email:dana.ruiz@helioware.example",
  "winner_row_id": "fw_002",
  "removed_row_ids": ["fw_001"]
}
```

The key format is `email:{normalized_email}` for email-based groups and
`phone:{normalized_phone}` for phone-based groups.

## Suppression

Check each raw contact after normalization but before deduplication:

1. Match normalized email against each suppression list entry's normalized
   email. The suppression list emails are already normalized. If the
   suppression email is non-empty and matches exactly, suppress the row.
2. Match normalized phone against each suppression list entry's normalized
   phone. If the suppression phone is non-empty and matches exactly, suppress
   the row.
3. Also check the CRM contacts list: any CRM contact with `opted_out: true`
   whose normalized email or phone matches the raw row's normalized email or
   phone triggers suppression of that row.

Suppressed rows get removal reason `suppressed` and `crm_action: suppress`.

## Source Name Mapping

Batch import source names appear as-is: `webinar_form`, `partner_upload`,
`manual_upload`, `badge_scan`, `sponsor_form`, `exhibitor_form`. Use the
value directly from the raw contact, do not map or transform it.

## Relationship Type Classification (Ranked Prospecting)

When the template asks for `relationship_type` on excluded exhibitors:
- `distributor` → exclusion reason `distributor_only`
- `service_provider` → exclusion reason `service_only`
- `sensor_vendor` → exclusion reason `sensor_only`
- `research` → exclusion reason `research_only`

These map directly from what the exhibitor description reveals about their
business role.
