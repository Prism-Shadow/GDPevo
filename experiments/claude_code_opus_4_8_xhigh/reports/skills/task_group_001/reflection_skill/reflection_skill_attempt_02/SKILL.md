---
name: harborcrm-front-of-funnel
description: >-
  Use this skill for any HarborCRM front-of-funnel CRM/marketing task that
  produces a structured JSON answer from the HarborCRM JSON API: post-event
  sponsor reconciliation and CRM handoff, trade-show exhibitor
  prospecting/qualification and lead ranking, raw contact-import hygiene and
  dedup, sponsor/lead follow-up planning, and CRM create/update/no-action
  decisions. Trigger it whenever a prompt references HarborCRM, an event_id,
  a show_id, an import batch, sponsor packages/invoices, badge scans,
  exhibitors, raw_contacts/suppression, campaign members, or asks you to
  reconcile, qualify, dedup, classify sponsor status, decide CRM actions, or
  emit a JSON object matching an answer_template.json. Use it even when the
  word "HarborCRM" is absent but the task is clearly one of these workflows.
---

# HarborCRM Front-of-Funnel Operations

HarborCRM tasks ask you to turn shared CRM/marketing source data into ONE strict
JSON object that matches a provided `answer_template.json`. The data is read-only
and fetched over HTTP. The hard part is never the JSON shape — it is applying the
exact business rules (source precedence, exclusions, normalization, status
classification, follow-up dates, dedup winners, CRM actions) consistently. This
skill encodes those rules so a fresh solver reproduces the official answers.

## Golden rule: the template and prompt are law

Before computing anything, read `input/payloads/answer_template.json` end to end and
re-read the prompt. The template defines exact keys, enum `allowed_values`, ordering
rules, and value types. The prompt defines the scope (which event/show/batch),
the qualification criteria, and the sizing/ranking rules.

- Emit ONLY the keys the template declares. Do not add extra keys. Do not include
  prose outside the JSON. If a template's `required_top_level_keys` omits a field
  that appears decoratively elsewhere (e.g. a `task_id`), follow `required_top_level_keys`.
- Use enum values verbatim. Enum vocabularies differ per task (e.g. one task uses
  `sensor_vendor_only`, another uses `sensor_only`; one uses `not_sponsor` and another
  does not). Always pull the allowed set from the current template, never from memory.
- Honor every ordering rule exactly (almost always ascending by a named field).
  Sort lists deterministically; ties resolve by the next stated key.
- Currency is integer USD. Counts are integers. Dates are `YYYY-MM-DD`.

## Environment / API usage

The base URL is in `environment_access.md` (e.g. `http://127.0.0.1:8080`). It is a
read-only JSON API; there are NO answer endpoints. Fetch raw records and compute
locally. Confirm reachability with `GET /health` (it also returns record counts,
useful for sanity checks).

Endpoints you will use (parameterized by id from the prompt):
`/api/events/{event_id}`, `/.../orders`, `/.../badges`, `/.../sponsor_packages`,
`/api/finance/invoices?event_id=`, `/api/crm/accounts`, `/api/crm/contacts?account_id=`,
`/api/crm/opportunities?event_id=`, `/api/crm/campaign_members?event_id=`,
`/api/tradeshows`, `/api/tradeshows/{show_id}/exhibitors`,
`/api/tradeshows/{show_id}/meeting_interest`, `/api/import_batches`,
`/api/import_batches/{batch_id}/raw_contacts`, `/.../suppression`, `/api/policies`.

`/api/policies` returns only high-level notes (platform enums, status enums, hygiene
notes). It will NOT spell out thresholds — derive concrete logic from this skill and
the prompt. When in doubt about a rule, fetch the relevant records and reason from the
data rather than guessing.

## Field definitions used across tasks

These are stable across the domain; apply them consistently.

### Email normalization
Lowercase and trim whitespace. An email that is empty, whitespace-only, or absent
normalizes to the empty string `""` (never `null` unless the template says null).
Do not alter the local part or domain otherwise.

### Phone normalization
Strip every non-digit character (spaces, `+`, `-`, `.`, parentheses). Keep the digits
exactly as they appear, INCLUDING a leading country-code digit when the source had one.
- `+1 (415) 555-0188` -> `14155550188` (the `+1` contributes a leading `1`).
- `415-555-0188` -> `4155550188` (no country code in source -> 10 digits, no added `1`).
- `1.206.555.0177` -> `12065550177`.
Never add a country code that was not present, and never strip a leading digit that was
present. Empty/absent phone -> `""`.

### Account matching (does this lead already exist in CRM?)
Match a lead's company to a CRM account by **email domain**, not by company-name string
(company names vary: "HelioWare Manufacturing" vs "HelioWare Mfg." both map to the
account whose `domain` is `helioware.example`). If a matching account exists ->
`update_existing` / mark `existing_account_id`. If none -> `create_account`.

### Contact matching (does this person already exist?)
A contact exists only if CRM `contacts` for that account already contain the person
(match by email, then name). An existing account with no matching contact still needs
`create_contact`. If neither exists, both account and contact are created.

## Workflow A: Post-event sponsor reconciliation & CRM handoff

(events + sponsor_packages + invoices + badges + accounts + contacts + opportunities +
campaign_members). Examples: "audit the post-event CRM handoff", "reconcile badge scans,
sponsor orders, finance state, and campaign members".

### A1. Sponsor status classification
Classify each sponsor account from its `order_status` (sponsor_packages) reconciled with
its finance invoice:
- `paid_deferred` — order confirmed AND invoice fully paid (`paid_amount == amount`,
  invoice status paid/paid_deferred).
- `open_invoice` — order confirmed AND an invoice exists with an open balance
  (`paid_amount < amount`; open_balance = `amount - paid_amount`).
- `proposal_only` — order is `proposal_sent` (no/issued invoice yet); no payment.
- `not_sponsor` — only when the template's enum includes it and the account isn't an
  active sponsor.
- **Canceled/inactive orders are NOT active sponsors.** A package with
  `order_status: canceled` (or otherwise inactive) is excluded from `sponsor_statuses`
  and surfaces only as an exclusion record (see A3). Active sponsor list = confirmed +
  proposal_sent orders.

Revenue rollups: sum `amount` per status. Report `open_invoice_balance` separately as the
sum of open balances (`amount - paid_amount`) for open invoices only.

### A2. Badge / lead classification (the exclusion list is BADGE-DRIVEN)
The set of attendees you classify comes from **badge scans**, not from sponsor
ticket_contacts and not from campaign members. A sponsor contact only appears as a
`sponsor_attendee` exclusion if that person actually has a badge. Do NOT invent exclusion
rows for sponsor ticket-holders who never scanned a badge.

For each badge decide, applying exclusion reasons in this PRECEDENCE order (first match wins):
1. `non_business_badge` — badge_type is student / press / academic / non-business.
2. `inactive_sponsor_record` — the badge's company has a canceled/inactive sponsor
   package. This OUTRANKS `existing_disqualified`: if a company is both CRM-disqualified
   and has a canceled sponsor record, use `inactive_sponsor_record`.
3. `sponsor_attendee` — the badge's company is an ACTIVE sponsor (badge_type sponsor, or
   company in active sponsor_packages). These are excluded from the lead handoff.
4. `existing_disqualified` — the badge's CRM account has `status: disqualified`.
5. Otherwise -> `qualified_non_sponsor_lead`.

Use the exact `exclusion_reason` enum from the template (a non-applicable reason is `null`).

### A3. Qualified non-sponsor leads
Qualified leads = business badges whose company is not an active sponsor, not
CRM-disqualified, and not tied to a canceled sponsor record. For each, set
`opportunity_amount` / `lead_opportunity_amount_usd` to the event's
`lead_opportunity_amount` (same value for every lead). `lead_pipeline_total` /
`open_opportunity_total_usd` = lead amount x lead count; `open_opportunity_count` = lead count.
Derive CRM actions via the account/contact matching rules above.

### A4. Campaign member actions (when the template asks for them)
Produce one action per relevant subject. Key conventions observed:
- Existing CRM campaign members (sponsors already in `campaign_members`) keep their record
  and get `no_action` with their current `target_status` (e.g. `attended_sponsor`,
  `registered_sponsor`). Their `subject_key` is `<account_id>:<contact_id>`.
- Badge-derived members (new leads, and sponsor attendees who scanned but aren't yet a
  campaign member) get `create`. Their `subject_key` is `badge:<badge_id>`.
  - A sponsor company's badge attendee who is NOT already a campaign member -> `create`
    with a sponsor target_status (e.g. `attended_sponsor`).
  - A qualified lead badge -> `create` with target_status `attended`.
- **Excluded / no_import badges (non-business, press, student) produce NO
  campaign_member_action row at all.** Do not emit a `no_import`/`excluded` member row for
  them. They show up only in `badge_decisions` and `exclusion_counts`.
- Sort by `subject_key` ascending (so `acct_...` keys sort before `badge:...` keys).

### A5. badge_only_contacts (normalized contact facts)
Include one entry for every badge that will result in a NEW contact being created — that is
qualified-lead badges AND sponsor-attendee badges whose person is not already a CRM contact.
Exclude no_import/non-business badges, and exclude people already present as CRM contacts.
Apply email + phone normalization. Sort by `company_name` ascending.

### A6. Follow-up dates and finance/sponsor follow-up — READ THE FIELD SEMANTICS
Dates come from the event: lead due = `end_date + followup_days_after_end`; sponsor due =
`end_date + sponsor_followup_days_after_end`. Add calendar days.

The follow-up POPULATION depends on the exact field name — this is a classic trap:
- A **finance / open-invoice follow-up** (e.g. `sponsor_finance_accounts`, an "open invoice
  balance" handoff) targets ONLY sponsors with an issued-but-unpaid invoice — i.e.
  `open_invoice` status. A `proposal_only` sponsor has no invoice and is NOT a finance
  follow-up.
- An **unpaid-sponsor follow-up** (e.g. `unpaid_sponsor_account_names` /
  `unpaid_sponsor_total_usd`) targets ALL active sponsors not fully paid — that is
  `open_invoice` PLUS `proposal_only`. The total is the amount still owed: the open balance
  for invoiced sponsors, and the full package/opportunity amount for uninvoiced
  (proposal_only) sponsors.
Decide which population a field wants from its name/description; do not assume the two are
the same.

### A7. crm_action_counts and exclusion_counts
These are pure tallies of the decisions you already made — recompute them from your own
lists so they reconcile exactly (e.g. `accounts_create` = number of leads with
`create_account`; each exclusion_reason count = number of badges with that reason).

## Workflow B: Trade-show prospecting / qualification & ranking

(tradeshows + exhibitors + meeting_interest + accounts + contacts + policies). Examples:
"prepare the qualified lead list", "CRM-ready prospecting summary", rank exhibitors.

### B1. Qualification
An exhibitor qualifies only if it **manufactures or OEM-builds** an in-scope platform
itself. Read the exhibitor `description` and decide from the language:
- "Manufactures / Builds / OEM ... [platform]" -> qualified; record exactly the in-scope
  platforms it builds.
- "reseller / dealer / distributor / regional supply of imported ..." -> NOT qualified;
  `distributor` / `distributor_only`.
- "analytics / dashboard / software / service, no hardware manufacturing" -> NOT qualified;
  `service_provider` / `service_only`.
- "sensor vendor only" (sells just the sensor, not the platform) -> `sensor_vendor` /
  `sensor_only` (or `sensor_vendor_only` per the template's enum).
- "research / university / lab only" -> `research` / `research_only`.
Map relationship_type and exclusion_reason to the template's exact enums (they vary per task).

### B2. Platforms
List only the in-scope platforms the exhibitor actually builds, sorted in the template's
enum order (typically `AUV`, `ROV`, `Underwater Camera`). A camera-array ROV builder gets
both `ROV` and `Underwater Camera`.

### B3. Ranking, tiers, opportunity sizing — use the prompt's exact spec
Ranking and tier thresholds are given in the prompt and differ per task. A representative
spec: rank by `requested_demo` true first, then `interest_score` descending, then broader
platform coverage (more platforms), then `company_name`. Tiers: e.g. `A` = demo + score>=90,
`B` = demo + score>=80, `C` = all other qualified, with per-tier dollar amounts stated in the
prompt. Always read the actual thresholds from the current prompt; never reuse another task's
numbers. Assign contiguous 1-based `rank`.

### B4. CRM action & overlap
Exhibitor `crm_account_id` present -> `update_existing`, carry the id; null ->
`create_account`, id null. Excluded exhibitors -> `no_import` and stay visible in the
exclusion list. `existing_crm_overlap` = qualified leads that already have a `crm_account_id`;
list those account ids ascending. `total_estimated_opportunity_usd` = sum of qualified leads'
opportunity estimates. Platform/priority/aggregate counts are tallies of your final lists.

## Workflow C: Raw contact-import hygiene & dedup

(import_batches + raw_contacts + suppression + accounts + contacts). Example: "prepare the
batch for CRM import".

Process order: normalize -> drop unusable -> drop suppressed -> dedup -> decide CRM action.

### C1. Normalize then triage each raw row
Normalize email (lowercase/trim) and phone (digits-only) first.
- `missing_contact` (unusable): the row has no usable contact identity — email AND phone are
  both empty after normalization. Such rows are removed and counted in
  `unusable_removed_count`.
- `suppressed`: the row's normalized email (or phone) appears in the batch suppression list.
  Removed and counted in `suppressed_removed_count`. (Suppression matches the person, not the
  company name — a row whose company differs but whose email/phone is suppressed is still
  suppressed.)

### C2. Dedup winner rule (the most error-prone part)
Group surviving rows by their dedup key = the **normalized email** (lowercase/trimmed),
with NO type prefix. (The duplicate `key` field in the output is the bare normalized email,
e.g. `dana.ruiz@helioware.example`, never `email:dana.ruiz@...`.)

Within a duplicate group, pick the WINNER by this layered rule:
1. Highest source trust. First-party / event-captured sources outrank third-party uploads.
   Observed precedence (high -> low): `badge_scan`, `sponsor_form`, `webinar_form`,
   `exhibitor_form`, then `partner_upload`, `manual_upload`. (Decisive evidence: at an
   identical capture timestamp, a `webinar_form` row beat a `partner_upload` row.)
2. Earliest `captured_at`.
3. Lowest `row_id` as a final deterministic tiebreaker.
The winner's field values (company_name, contact_name, normalized email/phone, source_name,
captured_at) populate the clean contact — do not merge fields from losers. `clean_contact_id`
and `source_row_id` = the winner's `row_id`. Losers are removed with reason `duplicate` and
listed in `removed_row_ids`; `duplicate_removed_count` = total losers removed.

### C3. CRM action per clean contact
Apply account/contact matching by email domain:
- Domain matches an existing account -> `update_existing`, set `existing_account_id`
  (and `existing_contact_id` if the person is already a contact, else null).
- No matching account -> `create_account`.
- `no_import` / `suppress` are used per the template where a row is intentionally not
  imported. `import_action_totals` tallies the clean contacts' actions; note `no_import`
  totals can include removed rows depending on the template's definition — recompute counts
  from your own removed/clean lists so they reconcile.
`campaign_member_import_count` = number of surviving clean contacts that become campaign
members for the batch campaign.

### C4. Ordering
Sort `clean_contacts` by `clean_contact_id` ascending, `duplicate_keys` by `key` ascending,
`removed_rows` by `row_id` ascending.

## Common pitfalls / mistakes to avoid

These are distilled from real reflection errors — each cost a wrong answer:

- **Sponsor "finance" follow-up vs "unpaid" follow-up are different populations.** Finance/
  open-invoice follow-up = `open_invoice` only. Unpaid-sponsor follow-up = `open_invoice` +
  `proposal_only`. Read the field name; never reflexively include or exclude proposal_only.
- **The post-event exclusion/attendee list is driven by BADGES, not by sponsor ticket
  contacts or campaign members.** Don't add `sponsor_attendee` exclusion rows for sponsors
  who never scanned a badge. Only badge-holders get classified.
- **`inactive_sponsor_record` outranks `existing_disqualified`.** A canceled sponsor package
  makes the attendee an inactive-sponsor exclusion even if the CRM account is also
  disqualified. Apply exclusion-reason precedence: non_business -> inactive_sponsor ->
  sponsor_attendee -> existing_disqualified.
- **Excluded / non-business / no_import badges produce NO campaign_member_action row.** Don't
  emit a "no_import"/"excluded" member entry for them.
- **Campaign-member `subject_key` follows a fixed convention:** `<account_id>:<contact_id>`
  for existing CRM members, `badge:<badge_id>` for badge-derived members. Don't key by
  company name. This also drives the `subject_key` sort order.
- **`badge_only_contacts` includes sponsor-attendee badges whose contact must be created**,
  not just brand-new lead companies. Anyone who needs a new contact created from badge data
  belongs here (except no_import badges and already-existing contacts).
- **Phone normalization keeps the leading country-code digit only if the source had one.**
  `+1 (415)...` -> `1415...`; `415-...` stays 10 digits. Don't add or drop a leading `1`.
- **Dedup key is the bare normalized email with no `email:` prefix.** And the dedup WINNER is
  the highest-trust source / earliest capture / lowest row_id — NOT the most recent upload.
  Picking the latest partner_upload over the original webinar_form is a common, wrong instinct.
- **Account matching is by email DOMAIN, not company-name string.** Company names vary across
  sources; the domain is the stable key to an existing account.
- **Enum vocabularies and sizing thresholds are per-task.** Pull allowed_values and dollar
  amounts from the current template/prompt every time; don't carry them over from another task.
- **Recompute all counts from your own final lists** (crm_action_counts, exclusion_counts,
  import_action_totals, aggregate_counts) so totals reconcile with the detail rows.
- **Emit only template-declared keys, in the required order, with integers for money/counts
  and `YYYY-MM-DD` dates. No prose outside the JSON.**

## Suggested execution checklist

1. Read the template and prompt; note exact keys, enums, ordering, sizing/threshold rules.
2. `GET /health`, then fetch only the records the prompt scopes (event/show/batch + CRM).
3. Classify / qualify per the workflow rules above.
4. Apply exclusion precedence and CRM-action matching (by domain) deterministically.
5. Normalize emails/phones; compute follow-up dates from event offsets.
6. Build detail lists, sort per ordering rules, then derive every count/rollup from them.
7. Validate against the template (keys present, enums valid, types/dates correct, no extras)
   and emit a single JSON object.
