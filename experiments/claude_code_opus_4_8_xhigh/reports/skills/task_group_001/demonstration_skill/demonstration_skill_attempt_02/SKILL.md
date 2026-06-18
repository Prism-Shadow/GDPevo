---
name: harborcrm-front-of-funnel
description: >-
  Solve HarborCRM front-of-funnel CRM/marketing tasks against the read-only HarborCRM JSON API:
  post-event sponsor reconciliation, finance/sponsor-status classification, trade-show
  prospecting & lead qualification, raw contact-import hygiene/dedup/suppression, badge
  reconciliation, follow-up due-date and task planning, and CRM create/update/no-action
  decisions. Use whenever a task references HarborCRM, an event_id, a trade-show show_id,
  an import batch, sponsor packages/invoices, badge scans, exhibitors, meeting interest,
  or asks for a JSON handoff/prospecting/import summary matching an answer_template.
---

# HarborCRM Front-of-Funnel Solver

HarborCRM is a shared read-only JSON CRM/marketing workspace. Tasks ask you to reconcile,
qualify, classify, and plan handoffs, then return exactly ONE JSON object that conforms to a
provided `input/payloads/answer_template.json`. The template is authoritative for shape,
key names, enum values, ordering, and which fields are required. The rules below explain HOW
to fill it correctly and WHY records get included/excluded.

## Golden rules

1. Output JSON ONLY. No prose outside the JSON. Add no keys not in the template; include all
   required keys. Match enum spellings exactly.
2. Obey every ordering rule in the template / prompt (usually a sort key, ascending). Sort
   deterministically; apply secondary sort keys when specified.
3. Currency is integer USD. Counts are integers. Dates are `YYYY-MM-DD`.
4. Derive everything from the live API data, not from memory. The `/api/policies` endpoint is
   intentionally sparse (just enum lists and notes) — the real rules come from the record
   contents and the conventions below.
5. Never invent data. Empty/absent email or phone becomes `""` (empty string), and missing
   account/contact IDs become `null` (follow the template's stated type for each field).

## API access

Base URL is supplied by the runner (e.g. `http://127.0.0.1:8080` or `:8067`). Use `curl -s`.
All responses are JSON. Endpoints:

- `GET /health` — sanity check + record counts.
- `GET /api/events`, `/api/events/{event_id}` — dates, `lead_opportunity_amount`,
  `followup_days_after_end`, `sponsor_followup_days_after_end`, `campaign_code`, `status`.
- `GET /api/events/{event_id}/orders` and `/sponsor_packages` — sponsor package rows with
  `account_id`, `amount`, `order_status` (confirmed | proposal_sent | canceled),
  `package_level`, `ticket_contacts`. (orders and sponsor_packages return the same rows.)
- `GET /api/events/{event_id}/badges` — badge scans: `badge_id`, `badge_type`,
  `company_name`, `contact_name`, `email`, `phone`, `scan_score`, `session_interest`.
- `GET /api/finance/invoices?event_id=<id>` (also `account_id=<id>`) — `invoice_id`, `amount`,
  `paid_amount`, `deferred_amount`, `status` (paid_deferred | open), `due_date`.
- `GET /api/crm/accounts` (filters `status=`, `owner_region=`) — `account_id`, `name`,
  `domain`, `status` (customer | prospect | disqualified), `disqualified_reason`.
- `GET /api/crm/contacts` (filter `account_id=`) — `contact_id`, `account_id`, `name`,
  `email`, `phone`, `opted_out`, `title`, `source_updated_at`.
- `GET /api/crm/opportunities` (filters `event_id=`, `account_id=`) — `amount`, `stage`.
- `GET /api/crm/campaign_members?event_id=<id>` (also `account_id=`) — `account_id`,
  `contact_id`, `status` (attended_sponsor | registered_sponsor | attended), `last_activity_date`.
- `GET /api/tradeshows`, `/api/tradeshows/{show_id}/exhibitors`,
  `/api/tradeshows/{show_id}/meeting_interest` — exhibitor `company_id`, `company_name`,
  `description`, `booth`, `country`, `website`, `crm_account_id`; meeting interest
  `interest_score`, `requested_demo`, `notes`, keyed by `company_name`.
- `GET /api/import_batches`, `/api/import_batches/{batch_id}/raw_contacts`,
  `/api/import_batches/{batch_id}/suppression`.

The API hosts MANY events/shows/batches beyond the one named in a task. Always scope to the
exact `event_id` / `show_id` / `batch_id` in the prompt.

## Cross-cutting normalization rules

- **Email normalization:** trim surrounding whitespace, lowercase the whole string. A blank
  or whitespace-only email becomes `""`. (Domain part is used for account matching.)
- **Phone normalization:** strip ALL non-digit characters; keep exactly the digits that
  remain. Do NOT add or remove a country code. `"+1 415 555 0188"` -> `"14155550188"`;
  `"415-555-0188"` -> `"4155550188"`; `"212-555-0166"` -> `"2125550166"`; `""` -> `""`.
- **Account existence / matching:** an exhibitor row carries `crm_account_id` directly. For
  badges/imports, match on the **email domain** to a CRM account's `domain` (e.g.
  `dana.ruiz@helioware.example` -> account with `domain: helioware.example`). Fall back to
  company-name match only if no domain match exists.
- **Contact existence:** a contact "exists" if a CRM contact under the matched account has the
  same person. Opted-out / "Former ..." contacts still exist as records but are not reusable
  as the campaign contact — a new badge/import person is still `create_contact`.
- **Disqualified accounts:** any account with `status == "disqualified"` (it carries a
  `disqualified_reason`) is excluded from qualified-lead handoff with reason
  `existing_disqualified`.

## Sponsor status classification (sponsor_handoff)

Enums: `paid_deferred`, `open_invoice`, `proposal_only`, `not_sponsor`.

For each sponsor package/order for the event:

- `order_status == "canceled"` -> NOT an active sponsor. Treat as `not_sponsor` if the
  template lists that account at all; otherwise drop it from `sponsor_statuses` entirely. Its
  badge attendees are handled by the badge/lead rules (often `existing_disqualified` or a
  plain non-sponsor), not as sponsor attendees.
- `order_status == "proposal_sent"` AND no invoice exists -> `proposal_only`
  (paid_amount 0, open_balance 0; `invoice_id` null).
- `order_status == "confirmed"` with an invoice whose `status == "paid_deferred"` (paid in
  full, payment deferred terms) -> `paid_deferred`.
- `order_status == "confirmed"` with an invoice whose `status == "open"` (paid_amount <
  amount) -> `open_invoice`; the open balance = `amount - paid_amount`.
- `package_amount` / `amount_usd` = the package `amount`. For open invoices report
  `paid_amount` and `open_balance` separately when the template asks.

**Revenue rollups:** sum `package_amount` per status into the by-status totals. Add a
separate `open_invoice_balance` = sum of open balances. "Unpaid sponsor total" = sum of
(open-invoice open balances) + (proposal_only amounts); unpaid sponsor account names are the
open_invoice and proposal_only accounts (sorted ascending). paid_deferred sponsors are fully
paid and NOT in the unpaid follow-up set.

## Badge reconciliation & lead qualification (event tasks)

Classify each badge for the event:

- **non-business badge** (`badge_type` in {`student`, `press`, ...} — anything not
  `attendee`/`sponsor`, e.g. student, press, media, academic) -> classification `excluded`,
  crm_action `no_import`, exclusion_reason `non_business_badge`.
- **sponsor attendee**: badge company matches an ACTIVE sponsor account (confirmed or
  proposal, not canceled), or the person is a sponsor `ticket_contact` -> classification
  `sponsor_attendee`, exclusion_reason `sponsor_attendee`. CRM action:
  - contact + campaign member already exist -> `no_action`;
  - account exists but contact missing -> `create_contact_campaign_member` (and the campaign
    member is created with target_status `attended_sponsor`).
- **existing disqualified**: badge company maps to a CRM account with `status == disqualified`
  -> excluded, reason `existing_disqualified`.
- **missing contact**: badge has neither a usable contact identity nor email/phone -> excluded,
  reason `missing_contact`.
- **qualified non-sponsor lead**: a business attendee whose account is not a sponsor and not
  disqualified -> classification `qualified_non_sponsor_lead`. CRM action depends on what
  exists: no account -> `create_account_contact_campaign_member`; account exists, contact
  missing -> `create_contact_campaign_member`; both exist -> `add_campaign_member`. New
  campaign members for non-sponsor leads use target_status `attended`.

**Campaign-member actions:** existing campaign-member rows for the event keep their current
`status` and are `no_action`. New leads/sponsor-attendees needing a member row are `create`
with the target_status above. Use `update` only when an existing member's status must change.

**Opportunity totals (non-sponsor leads):** every qualified non-sponsor lead gets the event's
`lead_opportunity_amount`. `lead_pipeline_total` / `open_opportunity_total_usd` =
count_of_qualified_leads x lead_opportunity_amount. `open_opportunity_count` = number of
qualified non-sponsor leads.

**badge_only_contacts** = the people who need contact creation from badges (qualified
non-sponsor leads, plus sponsor attendees whose contact is missing). Provide normalized email
and phone (empty string when absent). Sort as the template dictates (usually company_name).

**CRM action count rollups** sum the per-lead actions:
`accounts_create` = leads needing a new account; `accounts_update` = qualified leads whose
account already exists; `contacts_create` = new contacts; `campaign_members_create` = new
member rows. `*_update` buckets are usually 0 unless an existing record must change.

## Follow-up due dates and task counts

Read the event row:

- `lead_followup_due_date` = `end_date` + `followup_days_after_end` (calendar days).
- `sponsor_finance_due_date` / `sponsor_followup_due_date` = `end_date` +
  `sponsor_followup_days_after_end`.

Example: end_date 2026-09-16, followup_days_after_end 7 -> 2026-09-23; sponsor 3 ->
2026-09-19. Compute by date arithmetic, do not guess.

- **lead_task_count** = number of qualified lead accounts to follow up (one task each).
- **sponsor_finance_task_count** = number of sponsors needing finance follow-up = open_invoice
  + proposal_only sponsors. `sponsor_finance_accounts` = those account names, sorted ascending.

## Trade-show prospecting & qualification

Platform enums (ordered): `AUV`, `ROV`, `Underwater Camera`. Read each exhibitor's
`description` to decide qualification and platforms.

**Qualified** = the company itself MANUFACTURES / BUILDS / OEM-builds a target platform (AUV,
ROV, or underwater camera). Map description language to platforms (list in the enum order
above, including only the platforms the company actually builds):

- "builds/manufactures AUV / autonomous underwater vehicle / scout" -> `AUV`
- "builds/inspection-class ROV / remotely operated vehicle" -> `ROV`
- "designs/manufactures underwater camera modules / OEM camera" -> `Underwater Camera`
- A company can have multiple platforms (e.g. "AUVs and ROVs" -> `["AUV","ROV"]`).

**Excluded near-misses** (companies adjacent to the market but not platform builders). Pick the
controlled reason matching the template's allowed list:

- distributor / reseller / sales agent / "does not manufacture" -> `distributor_only`
  (relationship_type `distributor`).
- consulting / operates rented platforms / service team -> `service_only`
  (relationship_type `service_provider`).
- sensor-only vendor (e.g. dissolved-oxygen/salinity probes, no platform) -> `sensor_vendor_only`
  or `sensor_only` (use the exact enum the template lists; relationship_type `sensor_vendor`).
- research lab / university (no commercial build) -> `research_only` (relationship_type `research`).
- KEY SUBTLETY: in a "sensor integration" campaign, the qualified leads are the PLATFORM
  BUILDERS who would integrate the sensor, NOT the sensor vendors. The sensor vendor is an
  excluded near-miss (`sensor_vendor_only`/`sensor_only`). Analytics/software companies that
  merely USE partner camera/ROV feeds and have "no hardware manufacturing" are `service_only`.

**CRM action for exhibitors:** if `crm_account_id` is non-null -> `update_existing` (it is an
existing-CRM overlap; collect its id for overlap counts). If null -> `create_account`.
Excluded exhibitors are `no_import`.

**Priority tier + opportunity sizing** (from meeting_interest, matched by company_name):

- Tier `A` = `requested_demo == true` AND `interest_score >= 90`.
- Tier `B` = `requested_demo == true` AND `interest_score >= 80` (and not A).
- Tier `C` = everything else qualified (no demo, or score < 80).
- Opportunity USD by tier when the prompt specifies (commonly A=120000, B=90000, C=50000) —
  ALWAYS use the dollar amounts the current prompt states; the tier letters are stable but the
  dollar mapping is task-specific.

**Ranking qualified leads** (when ranked output is required), apply in order:
1. `requested_demo` true before false; 2. `interest_score` descending;
3. broader platform coverage (more platforms first); 4. `company_name` ascending.
Assign 1-based contiguous `rank`.

**Aggregates:** `qualified_total` / `qualified_lead_count` = qualified count;
`platform_counts` / `platform_coverage_counts` = number of qualified companies that build each
platform (a multi-platform company counts in each of its platforms); `priority_counts` =
qualified companies per A/B/C; overlap count = qualified companies with a non-null
`crm_account_id` (list their account ids ascending); `total_estimated_opportunity_usd` = sum of
qualified opportunity estimates.

## Raw contact-import hygiene (import_batch tasks)

Pipeline per raw row (then roll up). Process all rows; classify each into exactly one
disposition.

1. **Normalize** email (trim+lowercase) and phone (digits-only) for every row.
2. **Usability / missing_contact:** a row with no usable email AND no usable phone (and no
   real contact identity) is unusable -> reason `missing_contact`, action bucket `no_import`.
3. **Suppression:** if the normalized email OR phone matches any row in the batch
   `/suppression` list (any reason: global_opt_out, privacy_request, role_account) -> removed,
   reason `suppressed`, action bucket `suppress`. Suppression matches by email/phone regardless
   of the company name on the raw row.
4. **Deduplicate** the remaining rows by identity key — primarily `email:<normalized_email>`
   (use phone key if no email). Within a duplicate group choose ONE winner:
   - Winner = the row with the LATEST `captured_at`.
   - Tie-break (same `captured_at`): higher source precedence wins. Observed precedence:
     `partner_upload` / `sponsor_form` / `exhibitor_form` (curated) beat `webinar_form` /
     `badge_scan` / `manual_upload` (self-serve). When in doubt prefer the
     partner/sponsor/exhibitor-sourced row over a webinar/manual row.
   - Losers -> removed, reason `duplicate`, action bucket `no_import`. Record the
     `duplicate_keys` entry: `{ key, winner_row_id, removed_row_ids[] }`.
5. **Surviving winners become clean_contacts.** For each, carry the winner row's fields
   (company_name, contact_name, captured_at, source_name) and the normalized email/phone.
   Decide `crm_action` by matching the email domain to a CRM account:
   - matched account exists -> `update_existing` (set `existing_account_id`; set
     `existing_contact_id` only if a matching CRM contact exists, else `null`).
   - no matched account -> `create_account` (`existing_account_id` = null,
     `existing_contact_id` = null).
   - (`no_import`/`suppress` as clean_contact crm_action values are for rows you would still
     list; usually removed rows are reported only under removal_summary.)

**Rollups:**
- `duplicate_removed_count` = number of removed duplicate rows.
- `suppressed_removed_count` = number of suppressed rows.
- `unusable_removed_count` = number of missing_contact rows.
- `removed_rows` = all removed rows `{row_id, reason}` (reason in {duplicate, missing_contact,
  suppressed}), sorted by `row_id`.
- `import_action_totals` counts EVERY raw row by final disposition:
  `create_account` + `update_existing` = surviving winners; `no_import` = duplicates +
  missing_contact; `suppress` = suppressed. The four buckets must sum to the total raw rows.
- `campaign_member_import_count` = number of surviving clean_contacts (they all become campaign
  members of the batch campaign).
- `clean_contact_id` / `source_row_id` = the winning row's `row_id`.

## Common output fields & conventions

- Ordering: sponsor_statuses / qualified leads / accounts by `account_name` or `company_name`
  ascending; excluded by company then contact name; badge_decisions by `badge_id`; clean
  contacts by `clean_contact_id`; removed rows by `row_id`; duplicate keys by `key`; ranked
  leads by `rank`.
- Use exact enum spellings from the template (`paid_deferred`, `open_invoice`, `proposal_only`,
  `not_sponsor`; `create_account`/`update_existing`/`add_campaign_member`/`no_action`/
  `no_import`; `sponsor_attendee`/`non_business_badge`/`existing_disqualified`/`missing_contact`;
  platform and tier enums). When two templates spell the same concept differently
  (`sensor_vendor_only` vs `sensor_only`), use the one in the CURRENT template.
- `null` vs `""`: account/contact/invoice IDs that don't exist are `null`; absent
  email/phone strings are `""`.

## Common misjudgments to avoid

- Counting canceled sponsor packages as active sponsors. Canceled = drop from sponsor revenue;
  it is not paid/open/proposal.
- Treating a sensor vendor as a qualified prospect in a sensor-integration campaign. The
  qualified leads BUILD the platform; the sensor maker is an excluded near-miss.
- Treating analytics/software/consulting firms that use partner hardware as qualified — they
  are `service_only` (no manufacturing).
- Forgetting that proposal_only sponsors are "unpaid" for finance follow-up (the full amount is
  outstanding) even though there is no invoice yet.
- Adding/removing a country code during phone normalization — just keep the digits present.
- Reusing an opted-out / former CRM contact as the campaign contact instead of creating the
  new badge/import person (account is update; contact is still create).
- Picking the wrong dedup winner — winner is the LATEST captured_at, then higher source
  precedence; losers are `no_import` duplicates, not deletions of the surviving record.
- Including disqualified, sponsor, non-business, or missing-contact records in the qualified
  lead list — each has its own exclusion reason.
- Off-by-one on follow-up dates — add the day offset to `end_date` exactly.

## Step-by-step SOPs

### A. Post-event sponsor reconciliation / CRM handoff
1. GET the event; record end_date, lead_opportunity_amount, both follow-up day offsets.
2. GET orders/sponsor_packages + invoices; classify each sponsor (canceled->drop;
   proposal_sent->proposal_only; confirmed+paid_deferred->paid_deferred; confirmed+open->
   open_invoice with balance). Build sponsor_statuses + revenue rollups.
3. GET badges; classify each (non-business / sponsor attendee / existing disqualified /
   missing contact / qualified non-sponsor lead) using accounts + contacts + campaign_members.
4. Decide CRM actions per badge/lead (create/update/add member/no_action/no_import); build
   badge_only_contacts with normalized email/phone.
5. GET campaign_members; existing rows no_action, new ones create with target_status.
6. Compute opportunity totals (count x lead_opportunity_amount), unpaid sponsor totals, both
   follow-up due dates and task counts, exclusion counts, and CRM action-count rollups.
7. Emit JSON in template order, sorted as required.

### B. Trade-show prospecting / qualification
1. GET exhibitors + meeting_interest for the show; GET CRM accounts.
2. For each exhibitor read the description: qualified builder -> map platforms; else excluded
   with controlled relationship/reason.
3. CRM action: crm_account_id non-null -> update_existing (overlap); null -> create_account;
   excluded -> no_import.
4. Tier from demo + interest_score (A>=90 demo, B>=80 demo, else C); opportunity USD from the
   prompt's tier mapping.
5. Rank (demo, score desc, platform breadth, name) if required; compute aggregates
   (qualified_total, platform/priority counts, overlap ids, total opportunity).
6. Emit JSON in template order, sorted as required.

### C. Raw contact-import hygiene
1. GET raw_contacts + suppression for the batch; GET CRM accounts/contacts.
2. Normalize email/phone for all rows.
3. Remove unusable (missing_contact), then suppressed (email/phone match), then dedup by
   email/phone key (winner = latest captured_at, tie-break source precedence).
4. Surviving winners -> clean_contacts; set crm_action via domain match (update_existing with
   existing_account_id, else create_account); existing_contact_id only if contact matches.
5. Roll up removal counts, duplicate keys, import_action_totals (all rows summed), and
   campaign_member_import_count (= survivors).
6. Emit JSON in template order, sorted as required.
