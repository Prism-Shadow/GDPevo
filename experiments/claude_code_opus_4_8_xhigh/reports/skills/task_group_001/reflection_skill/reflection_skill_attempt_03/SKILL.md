---
name: harborcrm-front-of-funnel-ops
description: >-
  Use for HarborCRM front-of-funnel CRM/marketing tasks that must return a single
  JSON object conforming to a provided answer_template: post-event sponsor
  reconciliation & CRM handoff, trade-show exhibitor prospecting/qualification &
  ranking, raw contact-import hygiene/dedup, and sponsor/lead follow-up planning
  with CRM create/update/no-action decisions. Provides the field definitions,
  source-precedence rules, normalization rules, classification enums, dedup winner
  logic, follow-up date math, and schema/output conventions needed to solve new,
  unseen HarborCRM tasks correctly.
---

# HarborCRM Front-of-Funnel Operations

HarborCRM is a read-only JSON API describing events, sponsors, badges, finance,
trade shows, exhibitors, import batches, and a shared CRM. Each task asks for ONE
JSON object that conforms exactly to a supplied `answer_template.json`. The work is
deterministic data reconciliation, not creativity: read the records, apply the
business rules below, and emit the exact schema.

## 0. Environment / API usage

- Base URL comes from `environment_access.md` (e.g. `http://127.0.0.1:8080`; some
  prompts mention `:8067`). Always read `environment_access.md` for the live URL.
  Use `curl -s`. Everything is HTTP + JSON; never look for server source files.
- Useful endpoints:
  - `GET /api/events/{id}`, `/orders`, `/badges`, `/sponsor_packages`
  - `GET /api/finance/invoices?event_id=<id>` (or `account_id=<id>`)
  - `GET /api/crm/accounts` (`?status=`, `?owner_region=`),
    `GET /api/crm/contacts` (`?account_id=`),
    `GET /api/crm/opportunities` (`?event_id=`, `?account_id=`),
    `GET /api/crm/campaign_members?event_id=<id>` (`?account_id=`)
  - `GET /api/tradeshows`, `/{show_id}/exhibitors`, `/{show_id}/meeting_interest`
  - `GET /api/import_batches`, `/{batch_id}/raw_contacts`, `/{batch_id}/suppression`
  - `GET /api/policies`
- `/api/policies` is high-level guidance only. The concrete numbers you need
  (follow-up offsets, lead opportunity amount, campaign_code, dates) live on the
  **event record** and **batch record**, not in policies. Always fetch the event
  before computing follow-up dates or lead amounts.
- Currency values are integers (USD). Keep them integers in output.

## 1. Output / schema conventions (apply to EVERY task)

- Return exactly one JSON object, no prose, no markdown fences around it.
- Emit **only** the keys declared in the template's `required_top_level_keys` /
  `required_*_keys`. Do **not** copy template *metadata* fields into the output.
  In particular `task_id`, `schema_version`, `description`, `required_*`, and a
  top-level `event_id` that is only template bookkeeping are NOT output fields
  unless they appear inside `required_top_level_keys`. (Pitfall corrected: a blind
  attempt wrongly added `task_id`/`schema_version`/`event_id` to the output.)
- Do not add fields the template doesn't declare.
- Use the controlled enum values verbatim; never invent enum values.
- Respect every `ordering` rule exactly. Sort strings ascending by the named field;
  when a secondary sort is given (e.g. company then contact), apply it as a tie-break.
  Sort lists of IDs/keys ascending as strings.
- JSON key order and whitespace do not matter; values, types, and membership do.
- Integers stay integers; booleans stay booleans; use `null` (not `""`) where the
  schema says "string or null".

## 2. Normalization rules (shared across tasks)

### Email
- Trim surrounding whitespace, then lowercase the entire address.
- A value that is empty or only whitespace becomes `""` (treated as "no email").
- Use the *normalized* form for matching/dedup and for output email fields.

### Phone
- Strip every non-digit character (spaces, `+`, `(`, `)`, `-`, `.`).
- **Keep exactly the digits that were present** — do not add and do not remove a
  country code. If the source had `+1`/leading `1`, the result keeps the leading
  `1` (e.g. `+1 (415) 555-0188` -> `14155550188`, `+1 (512) 555-0121` -> `15125550121`).
  If the source had no country code, none is added (e.g. `212-555-0166` -> `2125550166`,
  `206.555.0150` -> `2065550150`). (Pitfall corrected: do not normalize all phones to a
  canonical +1 form, and do not strip a present leading 1.)
- Empty/whitespace phone becomes `""`.

### Name / company matching
- Match CRM records by normalized email primarily, then by domain/company when
  asked. Company display names can differ across sources (e.g. "HelioWare
  Manufacturing" vs "HelioWare Mfg."); rely on email/domain/account_id for identity,
  not on the free-text company string.

## 3. Sponsor reconciliation & post-event handoff (tasks like 001, 004)

Inputs: event, orders/sponsor_packages, finance invoices, badges, CRM accounts,
CRM contacts, campaign_members, opportunities.

### Sponsor status classification (per sponsor account)
Use the controlled enum (`paid_deferred`, `open_invoice`, `proposal_only`,
`not_sponsor`). Decide from order status + invoice state:
- **proposal_only**: order/package status is `proposal_sent` (a proposal exists but
  no real invoice/payment). Amount = package amount; invoice_id null; paid 0; open 0.
- **paid_deferred**: there is an invoice fully covered (paid_amount == amount, often
  with a `deferred_amount`, invoice status `paid_deferred`). open_balance = 0.
- **open_invoice**: invoice exists but is not fully paid (`status: open`,
  paid_amount < amount). open_balance = amount - paid_amount.
- **canceled** sponsor orders/packages are NOT active sponsors — exclude them from
  sponsor_statuses entirely. (They surface elsewhere; see exclusions.)
- "active sponsor" = order status confirmed OR proposal_sent (i.e., not canceled).

### Revenue rollups
- Sum package amounts by status into integer USD buckets.
- Report `open_invoice_balance` (sum of open balances) separately from the
  `open_invoice` revenue bucket (which is the gross package amount).
- `unpaid_sponsor_*` / sponsor finance follow-up = sponsors that are NOT
  paid_deferred, i.e. `open_invoice` + `proposal_only`. Their names go in the
  follow-up list (sorted ascending) and their package amounts sum into the unpaid
  total. (E.g. open_invoice 21000 + proposal_only 9000 = 30000.)

### Sponsor attendees (a kind of exclusion)
A "sponsor attendee" is a person tied to an **active** (non-canceled) sponsor:
- They come from BOTH sources: `badge_type: sponsor` badges AND the
  `ticket_contacts` listed on active sponsor packages/orders. A ticket contact with
  no badge is still a sponsor attendee (pitfall corrected: a blind attempt only used
  sponsor-typed badges and missed ticket-contact-only sponsor attendees).
- Emit **one excluded/sponsor record per sponsor account**, keyed to that account's
  primary/known ticket contact (the contact that maps to a badge and/or an existing
  CRM contact). Do not multiply rows for additional unknown ticket-contact names that
  have neither a badge nor a CRM contact.
- Sponsor attendees are excluded from the qualified non-sponsor lead list.

### Qualified non-sponsor leads
A badge/attendee qualifies as a lead only if ALL hold:
- It is a **business** badge (badge_type `attendee`, not `student`/`press`/other
  non-business types — those are `non_business_badge`).
- Its account is NOT an active sponsor (sponsor attendees are excluded).
- Its CRM account is NOT `disqualified` (those are `existing_disqualified`).
- It has a usable contact (a contact name; missing contact => `missing_contact`).
Each qualified lead's opportunity amount = the event's `lead_opportunity_amount`.
`lead_pipeline_total` / open opportunity total = sum of those lead amounts.

### CRM create vs update vs no-action decisions
- Account: if the lead's company already exists as a CRM account -> `update_existing`
  (account action); if not -> `create_account`.
- Contact: if the person already exists as a CRM contact -> update; else create.
- Campaign member: if a campaign_member row already exists for that contact+event ->
  `update`/`no_action` as the schema's target_status dictates; else `create`/`add`.
- Existing sponsor contacts already present as campaign members generally need
  `no_action` (their member status like `attended_sponsor`/`registered_sponsor` is
  already set).

### badge_only_contacts (normalized facts for new people)
- Include EVERY badge whose contact must be **created** in CRM — i.e. crm_action
  contains `create_contact` — regardless of whether the badge is a qualified lead or
  a sponsor attendee. A sponsor attendee whose contact is not yet in CRM (action
  `create_contact_campaign_member`) STILL belongs in badge_only_contacts. (Pitfall
  corrected: a blind attempt limited this list to qualified non-sponsor leads and
  dropped a sponsor attendee who needed contact creation.)
- Exclude non-business/`no_import` badges and people who already exist as CRM
  contacts (`no_action`).
- Output normalized_email (lowercase/trimmed, `""` if none) and normalized_phone
  (digits only per the phone rule, `""` if none).

### campaign_member_actions.subject_key format
- For a person already in CRM, use `<account_id>:<contact_id>`
  (e.g. `acct_rivet_ai:cont_sofia_meyer`).
- For a badge-only new person, use `badge:<badge_id>` (e.g. `badge:bdg_0008`).
- Do NOT slugify names into the subject_key. Sort by subject_key ascending
  (so `acct_*` keys naturally sort before `badge:*`). (Pitfall corrected: a blind
  attempt used `company__contact` slugs instead of real IDs.)

### Follow-up due dates
- `event.end_date` + `followup_days_after_end` = lead follow-up due date.
- `event.end_date` + `sponsor_followup_days_after_end` = sponsor finance follow-up
  due date. Add calendar days; format `YYYY-MM-DD`.
- Task counts usually equal the number of items in the corresponding follow-up list.

### Exclusion reasons (use the most specific, controlled value)
Priority/decision order when more than one could apply — pick the reason the schema
intends per record:
- `sponsor_attendee` — person tied to an active sponsor.
- `non_business_badge` — student/press/other non-business badge type.
- `existing_disqualified` — the CRM account's `status` is `disqualified`
  (regardless of `disqualified_reason` text). A canceled-sponsor account whose CRM
  account is disqualified is `existing_disqualified`, NOT `inactive_sponsor_record`.
  Only use an `inactive_sponsor_record`-type reason if the template actually lists it
  and the record's disqualification comes specifically from a canceled sponsor order
  with no other disqualifier. (Pitfall corrected: a blind attempt labeled a
  disqualified account as `inactive_sponsor_record` when the account status was
  plainly `disqualified` -> should be `existing_disqualified`.)
- `missing_contact` — no usable contact name.
Always emit exclusion reasons only from the template's allowed enum; map your finding
to the closest allowed value, preferring an account-status disqualification over a
sponsor-state guess.

## 4. Trade-show exhibitor prospecting / qualification (tasks like 002, 005)

Inputs: exhibitors (with `description`, `crm_account_id`, booth/country/website),
meeting_interest (interest_score, requested_demo), CRM accounts, policies.

### Qualification
- Qualified = the exhibitor **builds or OEM-builds** the campaign's target platforms
  (read the `description`). Companies merely adjacent are excluded:
  - distributor/reseller/dealer -> `distributor_only` (relationship `distributor`)
  - service/analytics/dashboard-only, no hardware -> `service_only`
    (relationship `service_provider`)
  - sensor-only vendor (sells just the sensor, not the platform) -> `sensor_vendor_only`
    or `sensor_only` (match the template's exact enum) (relationship `sensor_vendor`)
  - research/academic-only -> `research_only` (relationship `research`)
  - not in the target market -> `not_target_market`
  Use the EXACT exclusion enum strings from THIS task's template (they vary, e.g.
  `sensor_vendor_only` vs `sensor_only`).

### Platforms (controlled enum, fixed order)
- Allowed: `AUV`, `ROV`, `Underwater Camera`. Always list a qualified lead's
  platforms in that enum order, never alphabetical.
- Map description keywords: "AUV"/autonomous underwater vehicle -> AUV;
  "ROV"/remotely operated -> ROV; "camera"/optics/imaging -> Underwater Camera.
- A company can have multiple platforms (e.g. ROV + Underwater Camera).
- `platform_coverage_counts` / `platform_counts` count how many qualified leads cover
  each platform (a multi-platform lead increments each of its platforms).

### CRM overlap & actions
- An exhibitor with a non-null `crm_account_id` is an existing CRM account ->
  `update_existing`; qualified exhibitors with null crm_account_id -> `create_account`.
- Excluded exhibitors -> `no_import`.
- `existing_crm_overlap_*` = qualified leads whose crm_account_id is non-null
  (count + the account_ids, sorted ascending).

### Priority tiers & opportunity sizing
- Tiering uses requested_demo + interest_score; the dollar amounts and thresholds are
  given in the prompt. Typical pattern:
  - `A` = demo requested AND score >= 90 (e.g. 120000)
  - `B` = demo requested AND score >= 80 (e.g. 90000)
  - `C` = everyone else qualified (e.g. 50000)
  Use the exact dollar values from the prompt; sum into `total_estimated_opportunity_usd`.
- If the prompt gives no meeting-interest signal for a company, treat requested_demo
  as false / no score for tiering (lands in C) unless told otherwise.

### Ranking (when a ranked list is required)
Sort by, in order: requested_demo true first, then interest_score descending, then
broader platform coverage (more platforms first), then company_name ascending. Assign
1-based contiguous `rank`. When only "sort by company_name ascending" is requested
(no rank), just alphabetize.

## 5. Raw contact-import hygiene & dedup (tasks like 003)

Inputs: import_batch (campaign_code), raw_contacts (row_id, source_name,
captured_at, email, phone, company/contact), suppression list, CRM accounts/contacts.

### Per-row disposition pipeline (apply in this order)
1. **Missing contact / unusable**: a row with no usable contact (e.g. blank/whitespace
   email AND no other identity, or no contact name) -> removed, reason
   `missing_contact`, counts toward `unusable_removed_count`.
2. **Suppressed**: if the row's normalized email OR normalized phone matches any
   suppression entry -> removed, reason `suppressed`, counts toward
   `suppressed_removed_count`. (Suppression matches on normalized email or phone.)
3. **Duplicate**: rows sharing the same identity key (normalized email; fall back to
   normalized phone if no email) collapse to one winner; losers removed with reason
   `duplicate`, counted in `duplicate_removed_count`.
4. **Survivors** become `clean_contacts`.

### Duplicate winner rule
- Winner = the row with the **most recent `captured_at`**.
- **Tie-break when captured_at is identical**: higher source-priority wins. Source
  priority (more authoritative first): `partner_upload` > `exhibitor_form` /
  `sponsor_form` > `webinar_form` > `badge_scan` > `manual_upload`. In practice
  partner_upload beats webinar_form on a timestamp tie. (Pitfall corrected: a blind
  attempt kept the webinar_form row on a tie; the partner_upload row should win.)
- The **winner's own field values** (its phone, email, source_name, captured_at,
  company_name) are what appear in the clean contact — do not merge fields from the
  loser. (This is why the surviving phone may carry a leading `1` from the winner even
  if the loser's phone lacked it.)
- `clean_contact_id` and `source_row_id` = the winning row's row_id.

### Duplicate key format
- Each `duplicate_keys` entry's `key` is prefixed by the field used:
  `email:<normalized_email>` (or `phone:<normalized_phone>` if matched by phone).
  Not the bare value. (Pitfall corrected: a blind attempt used the bare email as key.)
- `winner_row_id` + `removed_row_ids` (sorted ascending) list the collapse.
- Sort `duplicate_keys` by `key` ascending; sort `removed_rows` by `row_id` ascending;
  sort `clean_contacts` by `clean_contact_id` ascending.

### crm_action on a clean (surviving) contact
- Matches an existing CRM contact (by normalized email) -> `update_existing` with that
  contact's `existing_contact_id`/`existing_account_id` populated.
- Matches an existing CRM account but new person -> still `create_account`? No:
  use `update_existing` only when the match warrants it per template; otherwise a brand
  new company -> `create_account` with existing ids null. Populate
  `existing_account_id`/`existing_contact_id` (or null) from the actual CRM match.
- (A surviving contact is never `no_import`/`suppress`; those dispositions belong to
  removed rows.)

### import_action_totals (count EVERY raw row, not just survivors)
This is an aggregate over ALL raw rows by final disposition:
- `create_account`, `update_existing` = counts among the surviving clean contacts.
- `suppress` = number of rows removed for suppression.
- `no_import` = number of rows removed as **duplicate OR missing_contact/unusable**
  (i.e. removed rows that were not suppressed). So
  `no_import = duplicate_removed_count + unusable_removed_count`.
  (Pitfall corrected: a blind attempt set no_import to only the missing_contact count
  and omitted the removed duplicates, undercounting it.)
- The four buckets together must total the number of raw rows.

### campaign_member_import_count
- = number of surviving clean_contacts that should join the batch campaign
  (normally all survivors). Equals len(clean_contacts) unless a rule excludes some.

## 6. Common pitfalls / mistakes to avoid (distilled)

1. **Don't echo template metadata into the output.** `task_id`, `schema_version`,
   `description`, `required_*`, and bookkeeping `event_id` are not answer fields unless
   listed in `required_top_level_keys`.
2. **Sponsor attendees come from ticket_contacts too, not just sponsor badges.** Pull
   active-sponsor `ticket_contacts` in addition to `badge_type: sponsor` badges; emit
   one record per sponsor account keyed to its known/primary contact.
3. **`existing_disqualified` is driven by CRM account `status == "disqualified"`**,
   not by sponsor-order cancellation. Don't mislabel a disqualified account as an
   "inactive sponsor record."
4. **badge_only_contacts = everyone who needs a new contact created**, including
   sponsor attendees with `create_contact_*` actions — not only qualified leads.
5. **subject_key uses real IDs**: `<account_id>:<contact_id>` for known people,
   `badge:<badge_id>` for badge-only people. Never slugify names.
6. **Phone normalization preserves the present digits**: strip non-digits but keep a
   leading country-code `1` if it was there, and never fabricate one if it wasn't.
7. **Dedup winner = latest captured_at, tie broken by source priority**
   (partner_upload > webinar_form > manual_upload, etc.); the winner's own field values
   are used in the clean record.
8. **Duplicate keys are field-prefixed** (`email:...`), not bare values.
9. **import_action_totals.no_import includes removed duplicates AND unusable rows**;
   the four buckets must sum to the raw-row count.
10. **Use the exact enum spelling from THIS task's template** (e.g. `sensor_vendor_only`
    vs `sensor_only`, `not_sponsor` availability) and **the exact platform/enum ordering**
    given, not alphabetical.
11. **Fetch the event/batch record for the real numbers** (follow-up offsets,
    lead_opportunity_amount, campaign_code); `/api/policies` won't give them.
12. **Sort and tie-break exactly as specified**, and keep currency as integers.

## 7. Suggested solving procedure for any HarborCRM task

1. Read `environment_access.md` for the base URL; read the prompt and the
   `answer_template.json`. Enumerate the exact output keys, enums, and ordering rules.
2. Identify the task family (sponsor reconciliation / prospecting / import hygiene)
   and fetch all relevant endpoints (always include the event or batch record).
3. Classify/normalize each record using sections 2-5. Track exclusions with their
   most-specific allowed reason.
4. Compute rollups, follow-up dates, and CRM action counts; double-check that totals
   reconcile (e.g. action buckets sum to the row/record count).
5. Assemble ONLY the declared fields, apply sorting, verify enum spellings, and emit a
   single clean JSON object with no surrounding prose.
