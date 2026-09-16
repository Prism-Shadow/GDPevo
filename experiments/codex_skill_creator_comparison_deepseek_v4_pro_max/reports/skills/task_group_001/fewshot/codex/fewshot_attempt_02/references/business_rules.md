# HarborCRM Business Rules & Controlled Enums

## Policy-Driven Decisions

Always call `GET /api/policies` first. The policies response contains:

- **Qualification criteria**: which badge types, exhibitor relationship types, or platform categories qualify for handoff
- **Exclusion lists**: disqualified CRM account IDs, suppressed domains, non-business badge types
- **Opportunity amounts**: per-event lead opportunity amounts (integer USD)
- **Follow-up windows**: lead follow-up offset (e.g., "60 days after event end") and sponsor finance follow-up offset (e.g., "60 days after event end" or "45 days after event end")
- **Deduplication keys**: how to match contacts across sources (email normalization, phone normalization)
- **Platform definitions**: which platform values (AUV, ROV, Underwater Camera) map to which exhibitor criteria

## Controlled Enum Catalogs

### Sponsor Statuses (Post-Event)

| Value | Meaning |
|-------|---------|
| `paid_deferred` | Sponsor invoice fully paid; no finance follow-up needed |
| `open_invoice` | Sponsor has unpaid balance; finance follow-up required |
| `proposal_only` | Sponsor order has no invoice yet; finance follow-up required |
| `not_sponsor` | Account is not an event sponsor (used in train_004 variant schema) |

Determine status by joining sponsor orders to invoices. If an active order has no associated invoice, status is `proposal_only`. If the invoice balance is 0, status is `paid_deferred`. If the invoice has an open balance, status is `open_invoice`. Canceled orders are excluded.

### Exclusion Reasons (Post-Event)

| Value | Meaning |
|-------|---------|
| `sponsor_attendee` | Contact belongs to a company that sponsored the event |
| `existing_disqualified` | CRM account is already in `disqualified` status |
| `inactive_sponsor_record` | Sponsor order is `canceled` |
| `non_business_badge` | Badge type does not meet business qualification criteria |

### Exclusion Reasons (Trade-Show Prospecting)

| Value | Meaning |
|-------|---------|
| `distributor_only` | Exhibitor is a distributor, not an OEM |
| `service_only` | Exhibitor provides services, not platforms |
| `sensor_vendor_only` | Exhibitor sells sensors only, not platforms |
| `research_only` | Exhibitor is academic/research, not commercial |
| `not_target_market` | Exhibitor platforms don't match campaign criteria |

### CRM Account Actions

| Value | Meaning |
|-------|---------|
| `create_account` | Account does not exist in CRM; create new |
| `update_existing` | Account already exists in CRM; update record |
| `no_import` | Do not import this record |

### CRM Contact Actions

| Value | Meaning |
|-------|---------|
| `create_contact` | Contact does not exist in CRM; create new |
| `update_existing` | Contact already exists in CRM; update record |

### Campaign Member Actions

| Value | Meaning |
|-------|---------|
| `add_campaign_member` | Add person as member of the event/show campaign |
| `create` | Create a new campaign member record (alternate schema) |
| `update` | Update an existing campaign member record |
| `no_action` | No change to campaign membership |
| `no_import` | Do not import as campaign member |

### Classification (Badge-Level)

| Value | Meaning |
|-------|---------|
| `sponsor_attendee` | Badge from a sponsoring company |
| `qualified_non_sponsor_lead` | Badge qualifies for sales handoff |
| `excluded` | Badge is excluded from handoff |

### Import CRM Actions (Batch)

| Value | Meaning |
|-------|---------|
| `create_account` | New account needed; contact is import-ready |
| `update_existing` | Account exists; contact matched to existing record |
| `no_import` | Row not imported (duplicate, unusable, suppressed) |
| `suppress` | Row suppressed by suppression list |

### Target Status (Campaign Members)

| Value | Meaning |
|-------|---------|
| `attended_sponsor` | Sponsor contact who attended the event |
| `registered_sponsor` | Sponsor contact who registered but did not attend |
| `attended` | Non-sponsor contact who attended |
| `excluded` | Campaign member excluded |

### Priority Tiers

| Value | Meaning |
|-------|---------|
| `A` | Highest priority; typically demo-requested with high score |
| `B` | Medium priority; demo-requested with moderate score |
| `C` | Standard priority; no demo or lower score |

### Platform Enums

| Value | Meaning |
|-------|---------|
| `AUV` | Autonomous Underwater Vehicle |
| `ROV` | Remotely Operated Vehicle |
| `Underwater Camera` | Underwater camera platform |

Always sort platforms in this order: AUV, ROV, Underwater Camera.

### Source Names (Import Batch)

| Value | Description |
|-------|-------------|
| `badge_scan` | Captured via event badge scan |
| `sponsor_form` | Submitted via sponsor lead form |
| `partner_upload` | Provided by event partner |
| `webinar_form` | Submitted via webinar registration |
| `exhibitor_form` | Submitted via exhibitor lead form |
| `manual_upload` | Manually uploaded by staff |

## Normalization Conventions

### Email
- Trim whitespace
- Lowercase all characters
- If no email provided, use empty string `""`

### Phone
- Strip all non-digit characters (parentheses, hyphens, spaces, country-code `+`)
- If no phone provided, use empty string `""`
- Leading country codes (e.g., `1` for US/Canada) are preserved as digits

## Duplicate Key Format (Import Batch)

Duplicate keys use the format `{field}:{normalized_value}`:

- `email:dana.ruiz@helioware.example` — match by normalized email
- Policies define which field to use for dedup (typically email)

When duplicates are found, select the **winner** by source priority (defined in policies) and earliest `captured_at` as tiebreaker. All other rows are `removed_row_ids`.

## Removal Reasons (Import Batch)

| Value | Meaning |
|-------|---------|
| `duplicate` | Row is a duplicate of a winning row |
| `missing_contact` | Row has no contact name (unusable) |
| `suppressed` | Row matched a suppression-list entry |

## Follow-Up Date Calculation

Compute dates from the event end date or task runtime:

1. Read the policy's `lead_followup_offset_days` and add it to the event's end date
2. Read the policy's `sponsor_finance_followup_offset_days` and add it to the event's end date
3. Format as `YYYY-MM-DD`

For trade-show tasks, follow-up dates are typically not required unless the template specifies them.

## Sorting Rules

Always enforce the sort order declared in the answer template. Common patterns:

- **Accounts and companies**: `account_name` or `company_name` ascending (lexicographic)
- **Badges**: `badge_id` ascending
- **Excluded records**: primary sort by `company_name` ascending, then `contact_name` ascending
- **Duplicate keys**: `key` ascending
- **Removed rows**: `row_id` ascending
- **Qualified leads (standard)**: `account_name` ascending
- **Ranked leads**: rank ascending (1-based contiguous)
- **Excluded exhibitors**: `company_name` ascending
