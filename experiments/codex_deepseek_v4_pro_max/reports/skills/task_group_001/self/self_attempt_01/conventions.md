## Data Conventions

### Normalization

| Field | Rule |
|---|---|
| Email | Lowercase, trimmed. Empty string `""` if missing. |
| Phone | Digits only (strip `+`, `-`, `(`, `)`, spaces). Empty string `""` if missing. |
| USD amounts | Integer (whole dollars). Never output floats. |
| Dates | `YYYY-MM-DD` string. |
| Counts | Integer. |
| IDs | String, preserved exactly as returned by API. |

### Controlled Enums

#### Sponsor Statuses
- `paid_deferred` — fully paid or payment deferred
- `open_invoice` — invoice issued, not fully paid
- `proposal_only` — no invoice, proposal only
- `not_sponsor` — not a sponsor

#### CRM Actions (Account/Contact)
- `create_account` — account not found in CRM
- `update_existing` — account already in CRM
- `create_contact` — contact not found under matched account
- `update_existing` — contact already exists under matched account
- `no_import` — record should not be imported
- `suppress` — record suppressed (email/domain on suppression list)

#### Campaign Member Actions
- `create` — new campaign member record
- `update` — update existing campaign member
- `no_action` — no change needed
- `no_import` — do not import
- `add_campaign_member` — add as campaign member

#### Campaign Member Target Statuses
- `attended` — non-sponsor attendee with badge scan
- `attended_sponsor` — sponsor-affiliated attendee
- `registered_sponsor` — sponsor registrant, no scan
- `excluded` — excluded from campaign

#### Exclusion Reasons (Event)
- `sponsor_attendee` — affiliated with a sponsor
- `non_business_badge` — press, guest, staff, or other non-business badge type
- `existing_disqualified` — CRM account already disqualified
- `missing_contact` — no usable contact name
- `inactive_sponsor_record` — canceled or inactive sponsor

#### Exclusion Reasons (Import Batch)
- `duplicate` — removed as duplicate
- `missing_contact` — no contact name
- `suppressed` — email/domain suppressed

#### Exclusion Reasons (Trade Show)
- `distributor_only` — distributor, not OEM/builder
- `service_only` — service provider only
- `sensor_vendor_only` — sensor vendor, not platform builder
- `sensor_only` — sensor vendor (shorter form)
- `research_only` — research institution
- `not_target_market` — does not match campaign target market

#### Platform Enums (Trade Show)
- `AUV` — Autonomous Underwater Vehicle
- `ROV` — Remotely Operated Vehicle
- `Underwater Camera` — underwater camera platform

#### Priority Tiers
- `A` — highest priority
- `B` — medium priority
- `C` — lowest priority

#### Source Names (Import Batch)
- `badge_scan`
- `sponsor_form`
- `partner_upload`
- `webinar_form`
- `exhibitor_form`
- `manual_upload`

### Sorting Conventions

- All sorts are ascending and case-sensitive unless noted otherwise.
- String sorts are lexicographic.
- When a template says "Sort in the enum order shown here", list items in that declared order.
- ID-based sorts (badge_id, row_id) are lexicographic string sorts.

### API Call Patterns

- Always fetch `/api/policies` when follow-up windows or decision thresholds might be policy-driven.
- When cross-referencing exhibitors/contacts against CRM, fetch all accounts and contacts (no filter) to ensure complete matching, unless the task specifically scopes the lookup.
- For event tasks, fetch the event, its orders, badges, sponsor packages, invoices, campaign members, and CRM accounts/contacts/opportunities.
- For trade-show tasks, fetch the show, its exhibitors, meeting interest, CRM accounts, and contacts.
- For import-batch tasks, fetch the batch, its raw contacts, suppression list, CRM accounts, and contacts.
