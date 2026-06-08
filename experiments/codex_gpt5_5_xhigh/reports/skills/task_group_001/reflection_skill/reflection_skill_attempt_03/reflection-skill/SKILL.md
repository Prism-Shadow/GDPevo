---
name: reflection-skill
description: HarborCRM workflow SOPs for event sponsor reconciliation, badge and campaign-member handoffs, trade-show prospect qualification, and import-batch cleanup using the public HarborCRM API. Use when Codex must produce JSON answers from HarborCRM task prompts, answer templates, CRM/event/tradeshow/import endpoints, policy data, and business rules for task_group_001-style evaluations.
---

# HarborCRM Workflow SOP

## Core Workflow

1. Read the task prompt and `input/payloads/answer_template.json` first. Treat the template as the contract for required keys, enum spelling, nullability, sorting, and numeric precision.
2. Use the runner-provided API base URL. If absent in a local run, use the URL stated in the prompt. Confirm with `GET /health` only if useful.
3. Fetch only public endpoints needed for the task:
   - Events: `/api/events/{event_id}`, `/orders`, `/badges`, `/sponsor_packages`, `/api/finance/invoices?event_id=...`, `/api/crm/campaign_members?event_id=...`
   - CRM: `/api/crm/accounts`, `/api/crm/contacts`, `/api/crm/opportunities`
   - Trade shows: `/api/tradeshows`, `/api/tradeshows/{show_id}/exhibitors`, `/api/tradeshows/{show_id}/meeting_interest`
   - Imports: `/api/import_batches`, `/api/import_batches/{batch_id}/raw_contacts`, `/api/import_batches/{batch_id}/suppression`
   - Policy: `/api/policies`
4. Build lookup maps by account id, account name, contact id, normalized email, normalized phone, event id, company name, and row id.
5. Produce one JSON object only. Do not add fields that are not in the template. Recompute all totals from the included rows after sorting.

## Normalization

- Email: trim whitespace and lowercase. Use `""` when no email is supplied and the schema permits an empty string.
- Phone: strip every non-digit character. Do not add, remove, or infer a country code. A source phone without leading `1` stays without leading `1`.
- Company matching:
  - Prefer exact CRM account id when an API row provides it.
  - Otherwise match by normalized company name or email domain when needed.
  - For import clean rows, preserve the winning source row's company name instead of replacing it with the CRM canonical name, while still filling `existing_account_id`.
- Contact matching: match normalized email first, then phone, then account plus contact name when needed. Respect `opted_out` and suppression records.
- Dates: follow-up dates are event `end_date` plus the configured number of days. Output date-only strings in `YYYY-MM-DD`.

## Event Sponsor And Badge Handoffs

### Sponsor Status

- Include active sponsor package/order rows with `confirmed` or `proposal_sent` statuses. Omit canceled sponsor orders from sponsor status lists unless the template explicitly asks for canceled records.
- Map statuses:
  - Confirmed order with invoice status `paid_deferred`: `paid_deferred`
  - Confirmed order with open invoice: `open_invoice`
  - Proposal order and no invoice: `proposal_only`
  - Non-sponsor rows only use `not_sponsor` when the template explicitly asks sponsor status decisions for non-sponsor accounts.
- `package_amount` or `amount_usd` is the order/package amount, not the paid amount.
- `open_balance` is invoice amount minus paid amount. `open_invoice_balance` totals only open balances.
- Sponsor finance follow-up accounts are open-invoice sponsors plus proposal-only sponsors. Sort names ascending and count one task per account unless the template says otherwise.

### Sponsor Contact Exclusions

- Exclude active and proposal sponsor ticket contacts from non-sponsor lead handoff, even if the contact does not appear in badge scans.
- Excluded sponsor ticket contacts should appear in exclusion lists when the schema requests excluded records.
- Proposal-only sponsor attendees are still sponsor attendees for badge classification and campaign-member target status.
- If a canceled/inactive sponsor account is already a disqualified CRM account, prefer `existing_disqualified` over an inactive-sponsor reason.

### Badge Classification

- `sponsor_attendee`: badge company/contact belongs to a confirmed or proposal sponsor package, including proposal-only accounts.
- `qualified_non_sponsor_lead`: business attendee with usable contact facts, not a sponsor, not an existing disqualified CRM account.
- `excluded`: non-business badge types, missing contactability, or existing disqualified accounts.
- Treat `student`, `press`, and similar non-buyer badge types as `non_business_badge`.
- A missing email is acceptable when a phone exists. Use `missing_contact` only when the record lacks usable contactability or contact identity required by the template.
- Existing disqualified CRM accounts are excluded regardless of scan score or apparent fit.

### CRM And Campaign Actions

- New qualified account plus new contact: `create_account_contact_campaign_member`.
- Existing account with no matching contact: `create_contact_campaign_member`.
- Existing account and contact without event campaign member: `add_campaign_member` or action `create`, per template enum.
- Existing campaign member needing status change: `update_campaign_member` or action `update`.
- Existing campaign member already at target status: `no_action`.
- Sponsor attendee with a missing CRM contact can still need `create_contact_campaign_member`; do not mark it `no_import` solely because it is excluded from non-sponsor lead pipeline.
- Campaign member subject keys commonly use:
  - Existing CRM subject: `{account_id}:{contact_id}`
  - Badge-only subject: `badge:{badge_id}`
- Target statuses:
  - Sponsor attended: `attended_sponsor`
  - Sponsor registered/no badge attendance: `registered_sponsor`
  - Non-sponsor attended lead: `attended`
  - Excluded record: `excluded`
- `badge_only_contacts` means contacts whose usable facts come from badge data and require creation or handoff. Include sponsor attendees too when they require contact/campaign creation.

### Event Totals And Field Meanings

- `lead_pipeline_total` or `open_opportunity_total_usd` equals qualified non-sponsor account count times the event `lead_opportunity_amount`, unless the template gives per-tier amounts.
- `lead_task_count` is usually the number of qualified non-sponsor handoff accounts.
- CRM action counts should reflect the included handoff work, not every raw API row.
- Sort exactly as the template says. If unspecified, use stable alphabetical ordering by account/company/name and deterministic ids for technical lists.

## Import Batch Cleanup

1. Normalize email and phone on every raw row.
2. Remove unusable rows with no usable contactability or required contact identity.
3. Apply suppression using the batch suppression list and CRM contact `opted_out` facts. A match on normalized email or normalized phone is enough.
4. Deduplicate surviving rows by normalized email when present, otherwise by normalized phone. Keep the duplicate key string in the form the template expects, commonly `email:{normalized_email}`.
5. Choose duplicate winners with this priority:
   - Latest `captured_at`
   - Higher-trust source when timestamps tie, with partner uploads preferred over webinar forms
   - Deterministic row id tie-break if still tied
6. The clean contact id and source row id are the winning row id.
7. Clean rows use fields from the winning raw row. Fill CRM ids from matched existing CRM records.
8. `crm_action`:
   - `update_existing`: matched active CRM account or contact should be updated
   - `create_account`: no existing account
   - `no_import`: duplicate or unusable removed row, when counted in action totals
   - `suppress`: suppressed removed row, when counted in action totals
9. Removal summaries include duplicate, suppressed, and missing-contact rows sorted by row id.
10. `import_action_totals` often counts both imported winners and removed rows: clean create/update winners, `no_import` for duplicates plus unusable rows, and `suppress` for suppressed rows.
11. `campaign_member_import_count` counts surviving clean contacts that should be imported into the batch campaign.

## Trade-Show Prospecting

### Qualification

- Qualified exhibitors build or OEM-build target platforms covered by policy:
  - `AUV`: autonomous underwater vehicles, autonomous scouts, AUV platform builders
  - `ROV`: remotely operated vehicles, inspection/cleaning ROV platform builders
  - `Underwater Camera`: underwater camera modules, camera arrays, OEM camera manufacturers
- Exclude adjacent companies that do not build target platforms:
  - Distributor/reseller/sales agent only: `distributor_only`
  - Service/consulting/operator/analytics-only with no hardware manufacturing: `service_only`
  - Sensor-only vendor/probe maker: use the exact enum from the template, such as `sensor_vendor_only` or `sensor_only`
  - Research lab only: `research_only`
  - Outside market: `not_target_market` when the template permits it
- Existing disqualified CRM accounts can remain excluded even when their product names mention target platforms.

### Priority, Ranking, And Counts

- Use meeting-interest records by company name. Default missing `requested_demo` to `false` and missing score to `0`.
- Common priority rule when no other rule is given:
  - `A`: requested demo and score at least 90
  - `B`: requested demo and score at least 80
  - `C`: all other qualified leads
- Common opportunity sizing when specified by task: map priority tier to the task's USD amount exactly.
- Rank qualified leads by the task's ordering. A common pattern is demo request first, then interest score descending, then broader platform coverage, then company name.
- Sort platform arrays in policy enum order: `AUV`, `ROV`, `Underwater Camera`.
- Platform coverage counts count platform mentions across qualified exhibitors, so one exhibitor with two platforms increments two counters.
- Existing CRM overlap counts only qualified exhibitors with a non-null CRM account id. Sort overlap account ids ascending.
- Existing qualified CRM accounts get `update_existing`; qualified exhibitors without CRM account id get `create_account`; excluded exhibitors get `no_import`.

## Common Pitfalls

- Do not infer phone country codes. Digits-only means "keep the digits present after stripping punctuation."
- Do not limit sponsor exclusions to badge scans. Sponsor package ticket contacts can be excluded records.
- Do not let a canceled sponsor label override an existing CRM disqualification reason.
- Do not treat proposal-only sponsors as ordinary non-sponsor leads. They stay out of non-sponsor pipeline and still need sponsor finance/campaign handling where applicable.
- Do not canonicalize import `company_name` to CRM account name; use the winning source row.
- Do not count only clean contacts in import action totals when the schema expects `no_import` and `suppress` counts for removed rows.
- Do not use one global enum for exclusion reasons. The same business reason may be spelled differently across templates.
- Recompute counts after final filtering, not from raw endpoint totals.
