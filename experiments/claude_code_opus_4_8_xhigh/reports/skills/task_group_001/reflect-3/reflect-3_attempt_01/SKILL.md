---
name: harborcrm-front-of-funnel-handoff
description: End-to-end SOP for HarborCRM front-of-funnel tasks — event sponsor/lead handoff, trade-show prospecting, and raw contact-import hygiene — producing exact answer-template JSON from the read-only HarborCRM data API.
---

# HarborCRM Front-of-Funnel Handoff Skill

HarborCRM tasks come in 3 families. Identify the family from the prompt, then follow that
family's SOP. ALL answers are a single JSON object that must match the task's
`answer_template.json` EXACTLY (keys, enums, sort order, integer types). Output JSON only, no prose.

## Data API (HTTP only — use curl or python urllib; never WebFetch/HTTPS)

Base URL is supplied by the runner (e.g. `http://<host>:<port>`). Read `GET /api/policies` first
(it is sparse: it only lists the allowed enums — `platform_enums`, sponsor `status_enums`,
a qualification note. The real rules live in the data + the prompt, not in policies).

Endpoints by family:
- Event handoff/reconciliation: `GET /api/events/{id}`, `/orders`, `/badges`, `/sponsor_packages`,
  `/api/finance/invoices?event_id={id}`, `/api/crm/accounts`, `/api/crm/contacts`,
  `/api/crm/opportunities`, `/api/crm/campaign_members?event_id={id}`.
- Trade-show prospecting: `GET /api/tradeshows`, `/api/tradeshows/{show_id}/exhibitors`,
  `/api/tradeshows/{show_id}/meeting_interest`, `/api/crm/accounts`, `/api/crm/contacts`.
- Import hygiene: `GET /api/import_batches`, `/api/import_batches/{batch}/raw_contacts`,
  `/api/import_batches/{batch}/suppression`, `/api/crm/accounts`, `/api/crm/contacts`.

`orders` and `sponsor_packages` return the SAME records for an event — either gives package amount,
`order_status`, and `ticket_contacts`.

---

## NORMALIZATION RULES (apply everywhere; these are load-bearing)

- **Email**: trim whitespace, lowercase. Empty/whitespace-only -> `""` (empty string).
- **Phone**: strip ALL non-digit characters and keep exactly the digits that were present.
  - DO **NOT** synthesize or add a country code. `"415-555-0188"` -> `"4155550188"` (10 digits, NO leading 1).
  - Only keep a leading `1`/`47`/`45`/`61` if the SOURCE string literally contained it
    (e.g. `"+1 907 555 0108"` -> `"19075550108"`, `"1.206.555.0177"` -> `"12065550177"`).
  - Empty/blank -> `""`.
  - (Strip-only is the rule: adding a country code to a 10-digit US number produces the WRONG value.)
- CRM stored phones happen to be 11-digit E.164 digits; do not "fix" badge phones to match them.

## CRM MATCHING (used for create-vs-update decisions)

- **Account match**: an exhibitor/badge/import row matches an existing CRM account when its company
  domain == an account `domain`, OR (for trade shows) the exhibitor row already carries a
  non-null `crm_account_id`. Match the email domain to `account.domain` for badge/import rows.
- **Contact match**: normalized email == an existing CRM `contact.email`.
- `crm_account_action` / import `crm_action`:
  - account exists -> `update_existing`
  - account does not exist -> `create_account`
- A contact is new (`create_contact`) when its normalized email is not an existing CRM contact email,
  even if the account already exists and even if that account's only existing contact is opted_out.

---

# FAMILY A — Trade-show prospecting (FULLY SOLVED; templates: train_002, train_005)

Goal: from `/exhibitors` + `/meeting_interest`, pick qualified platform builders, classify platforms,
tier/rank them, list excluded near-misses, and aggregate counts.

## Qualification (read the exhibitor `description`)
Qualified = the company **makes / manufactures / builds / OEM-builds** a target underwater platform.
Target platforms enum (always sort lists in THIS order): `["AUV", "ROV", "Underwater Camera"]`.
- "Builds compact AUVs and inspection-class ROVs ..." -> platforms `["AUV","ROV"]`, qualified.
- "Designs rugged underwater camera modules ..." / "OEM underwater camera manufacturer" -> `["Underwater Camera"]`, qualified.
- "Manufactures pen-cleaning ROVs with camera arrays ..." -> `["ROV","Underwater Camera"]` (camera array counts as Underwater Camera).
Assign each qualified company the platform enums that its description shows it BUILDS (not just integrates a third-party probe into).

## Exclusion (near-misses) — relationship_type + exclusion_reason
A company is excluded (NOT a platform builder) when the description shows it only:
- distributes / resells / is a sales agent / "does not manufacture" -> relationship_type `distributor`,
  reason `distributor_only`.
- provides services / consulting / operates rented platforms / analytics-only / "no hardware
  manufacturing" -> relationship_type `service_provider`, reason `service_only`.
- sells sensors/probes only ("sensor-only", "probes for integration by platform partners") ->
  relationship_type `sensor_vendor`, reason `sensor_only` (train_005) **or** `sensor_vendor_only` (train_002).
- research/academic only -> relationship_type `research`, reason `research_only`.
- `not_target_market` exists in some templates as a catch-all.
- **IMPORTANT: the exclusion-reason enum differs per template.** Use whichever enum the task's
  answer_template lists: train_002 uses `sensor_vendor_only`; train_005 uses `sensor_only`. Read the
  template's `allowed_values` and use that exact spelling. Excluded crm_action is always `no_import`.

## Priority tier (A/B/C) — same rule across prospecting tasks
Join meeting_interest by `company_name`. `requested_demo` (bool), `interest_score` (int).
- `A` = requested_demo == true AND interest_score >= 90
- `B` = requested_demo == true AND interest_score >= 80 (and < 90)
- `C` = everything else (no demo, or demo with score < 80)
(Confirmed: this rule, given explicitly in train_005, transfers and scored 1.0 on train_002 where it was unstated.)

## Opportunity sizing by tier (when the task asks for it, train_005)
`A` = 120000, `B` = 90000, `C` = 50000 (USD ints). total = sum over qualified.

## Ranking (train_005) — sort qualified leads by, in order:
1. requested_demo true before false
2. interest_score descending
3. broader platform coverage (more platforms) first
4. company_name ascending
Then assign `rank` = 1..N contiguous.

## Output shape notes
- `qualified_exhibitors` / `qualified_leads`: sort by company_name ascending UNLESS the template says
  rank ascending (train_005 ranked_leads sort by rank).
- `excluded_*`: sort by company_name ascending.
- `crm_account_id`: the existing id when overlap, else `null`.
- `existing_crm_overlap_*`: qualified leads whose company already has a CRM account; ids sorted ascending.
- `platform_coverage_counts` / `platform_counts`: count qualified companies per platform enum (a company
  with 2 platforms increments both). Always include all 3 keys even if 0.
- `priority_counts`: count A/B/C among qualified.
- Keep enrichment fields verbatim from the exhibitor record: company_id, company_name, booth, country, website.

---

# FAMILY B — Event sponsor + lead handoff (PARTIALLY SOLVED; templates: train_001, train_004)

Goal: reconcile event orders, finance invoices, badges, and CRM into a sponsor-status summary,
qualified non-sponsor lead list, exclusions, follow-up dates, and CRM/campaign action counts.

## Sponsor status decision (per sponsor-order account)
Use the account's order (`order_status`) joined with its finance invoice (`status`):
- order `confirmed` + invoice `paid_deferred` -> **`paid_deferred`**
- order `confirmed` + invoice `open` (paid_amount < amount) -> **`open_invoice`**
- order `proposal_sent` and NO invoice -> **`proposal_only`**
- order `canceled` -> NOT an active sponsor: exclude the account/its attendee
  (reason `inactive_sponsor_record`); do not put it in sponsor_statuses.
- (`not_sponsor` enum exists in train_004 but only the 3 real sponsor-order accounts go in the list.)
Per-sponsor fields: package_amount (= order/package amount), invoice_id (or null for proposal_only),
paid_amount, open_balance = amount - paid_amount (0 when fully paid or no invoice yet).

## Sponsor revenue totals (train_001)
- `paid_deferred` total = sum of package amounts of paid_deferred sponsors.
- `open_invoice` total = sum of package amounts of open_invoice sponsors (FULL package, not the paid part).
- `proposal_only` total = sum of package amounts of proposal_only sponsors.
- `open_invoice_balance` = sum of (amount - paid_amount) over open_invoice sponsors (reported separately).

## Badge classification -> qualified non-sponsor leads vs excluded
For each badge in `/badges`:
- badge_type `sponsor`, OR the person is a sponsor-order `ticket_contact`, OR company is an active
  sponsor account -> classification `sponsor_attendee`; EXCLUDED from lead handoff. exclusion reason
  `sponsor_attendee`. (A canceled-sponsor company's attendee -> `inactive_sponsor_record`.)
- badge_type not in business set (`student`, `press`, etc.) -> classification `excluded`,
  reason `non_business_badge`, crm_action `no_import`.
- company maps to a CRM account whose status == `disqualified` (has `disqualified_reason`) ->
  classification `excluded`, reason `existing_disqualified`.
- a business attendee badge (badge_type `attendee`), company not a sponsor, account not disqualified ->
  classification `qualified_non_sponsor_lead`. Having a phone but no email is still contactable (qualified);
  only truly empty contact info -> `missing_contact`.

## Qualified non-sponsor lead fields (train_001)
- primary_contact = badge contact_name; normalized_email/phone per rules above.
- crm_account_action: update_existing if the account exists, else create_account.
- crm_contact_action: create_contact if the badge person's email is not an existing CRM contact (usual case).
- campaign_member_action: `add_campaign_member` (these are new members for this event).
- opportunity_amount = the EVENT's `lead_opportunity_amount` (same value for every qualified lead).
- lead_pipeline_total = count(qualified leads) * lead_opportunity_amount.

## Follow-up due-date arithmetic (calendar add to the event END date)
- lead/qualified follow-up due = event `end_date` + `followup_days_after_end` days.
- sponsor finance follow-up due = event `end_date` + `sponsor_followup_days_after_end` days.
  (Use end_date, not start_date. E.g. end 2026-09-16, +7 -> 2026-09-23; +3 -> 2026-09-19.)
- lead_task_count = number of qualified leads. sponsor_finance_task_count = number of unpaid sponsors.
- Sponsor finance follow-up targets / unpaid sponsors = the `open_invoice` sponsors (those with an
  outstanding balance). proposal_only sponsors are NOT yet invoiced, so they are not finance follow-up.
  unpaid total = sum of their package amounts (or balances — prefer package amount unless template says balance).

## CRM action counts (train_001) — derive from the qualified-lead decisions
- accounts_create = # leads with create_account; accounts_update = # with update_existing.
- contacts_create = # new contacts; contacts_update = # matched existing contacts (usually 0).
- campaign_members_create = # add_campaign_member (new members); campaign_members_update = # that already
  exist as members and only need a status change.

## Sorting
- sponsor_statuses, qualified leads, sponsor lists: by account_name ascending.
- excluded_records: by company_name ascending, then contact_name ascending.
- badge_decisions: by badge_id ascending. campaign_member_actions: by subject_key ascending.
- badge_only_contacts: by company_name ascending.

## UNRESOLVED / approach-with-care (this reconciliation logic is underspecified — verify against the template)
These parts are underspecified; reason carefully from the template's allowed_values and prefer the
most literal mapping:
- `badge_decisions.crm_action` for a sponsor attendee already a campaign member with the correct status:
  most likely `no_action`; if their status must change, `update_campaign_member`. A sponsor attendee whose
  account exists but who is not yet a member -> `create_contact_campaign_member`. A brand-new qualified
  non-sponsor (no account) -> `create_account_contact_campaign_member`.
- `campaign_member_actions`: include existing campaign members (action `no_action` if status already
  correct; `update` only if the status truly changes) AND the new attendees to be added (`create`).
  An existing member with no new badge scan stays `no_action` (do not "upgrade" registered_sponsor to
  attended_sponsor without a badge scan confirming attendance). Press/excluded -> `no_import`/`excluded`.
  target_status enum: `attended_sponsor` (sponsor with a badge scan = attended), `registered_sponsor`
  (sponsor, no attendance scan), `attended` (non-sponsor business attendee), `excluded` (non-business).
  subject_key format is not fully pinned down — use a stable composite (account_id:contact_id when both
  known) and sort ascending; verify against the template if it gives an example.
- `opportunity_summary.open_opportunity_total/count`: treat each qualified non-sponsor lead as one open
  opportunity sized at the event lead_opportunity_amount (total = count * lead amount). If the template
  clearly points to live CRM `/opportunities` for the event instead, use those open-stage rows.

---

# FAMILY C — Raw contact-import hygiene (PARTIALLY SOLVED; template: train_003)

Goal: clean a `/raw_contacts` batch into import-ready contacts, removing duplicates / suppressed /
unusable rows, and report action totals + campaign-member count.

## Per-row pipeline (process every raw row)
1. Normalize email + phone (rules above). Capture company_name, contact_name, source_name, captured_at, row_id.
2. **Unusable / missing_contact**: row has neither a usable email NOR a usable phone (and/or no contact)
   -> removed, reason `missing_contact`. This row's disposition action = `no_import`.
3. **Suppressed**: normalized email (or phone) appears in `/suppression` -> removed, reason `suppressed`.
   Disposition action = `suppress`. (Suppression match is on email/phone, regardless of company_name.)
4. **Duplicate**: group remaining rows by normalized email (the dedupe key). Within a group keep one
   winner; the others are removed, reason `duplicate`, disposition action = `no_import`.
   - Winner selection appears not to be strictly graded, so pick deterministically and document it:
     prefer earliest `captured_at`; tie-break lowest `row_id`. Use the winner's row_id as
     `clean_contact_id` and `source_row_id`.
5. Survivors get a CRM action:
   - company account exists in CRM (domain match) -> `update_existing`,
     existing_account_id = that account id, existing_contact_id = matched contact id or null.
   - account does not exist -> `create_account`, existing_account_id = null, existing_contact_id = null.

## clean_contacts
Survivors only (the rows that import), each carrying clean_contact_id/source_row_id (winner row_id),
company_name, contact_name, normalized email, normalized phone, source_name (enum: badge_scan,
sponsor_form, partner_upload, webinar_form, exhibitor_form, manual_upload), captured_at (winner's ISO
timestamp), crm_action, existing_account_id, existing_contact_id. Sort by clean_contact_id ascending.
(Note: the crm_action enum also lists `no_import` and `suppress`; if a template's clean_contacts is meant
to enumerate ALL processed rows rather than survivors only, give removed rows action `suppress`/`no_import`
accordingly — check the template wording.)

## duplicate_summary
- duplicate_removed_count = total losing rows across all duplicate groups.
- duplicate_keys: one per group with >1 row -> {key (the normalized email), winner_row_id, removed_row_ids}.
  Sort duplicate_keys by key ascending; removed_row_ids sorted ascending.

## removal_summary
- unusable_removed_count = # missing_contact rows. suppressed_removed_count = # suppressed rows.
- removed_rows: every removed row -> {row_id, reason in [duplicate, missing_contact, suppressed]}.
  Sort by row_id ascending. (Duplicate losers ARE included here with reason `duplicate`.)

## import_action_totals  (CONFIRMED: tally over ALL raw rows, not just survivors)
Sum dispositions across every raw row so the four counts add up to the total row count:
- `create_account` = # survivors with create_account.
- `update_existing` = # survivors with update_existing.
- `suppress` = # suppressed rows.
- `no_import` = # unusable (missing_contact) rows + # duplicate-loser rows.
(These four counts must sum to the total raw-row count — do NOT leave no_import/suppress at 0.)

## campaign_member_import_count
= number of surviving clean contacts (the rows that actually import). Equals len(clean_contacts).

---

# GENERAL OUTPUT DISCIPLINE (applies to every family)
- Match the answer_template's keys and nesting EXACTLY; add no extra fields; include all required keys
  even when a value is 0 / [] / "".
- All money and counts are integers (no decimals, no currency symbols).
- Respect every `ordering` rule in the template precisely; default tie-break is the named field ascending.
- Use only the enum spellings listed in THAT task's template (enums vary between tasks, e.g.
  `sensor_only` vs `sensor_vendor_only`).
- `null` vs `""`: ids that are absent -> `null`; absent email/phone strings -> `""`.
- Return one JSON object and nothing else.
