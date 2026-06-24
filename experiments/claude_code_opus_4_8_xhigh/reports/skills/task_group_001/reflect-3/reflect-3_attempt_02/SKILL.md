---
name: harborcrm-front-of-funnel
description: End-to-end SOP for HarborCRM front-of-funnel CRM-marketing tasks — event sponsor/post-event handoff reconciliation, trade-show prospecting, and raw contact-import hygiene — over the read-only HarborCRM data API.
---

# HarborCRM Front-of-Funnel Solver

You produce ONE JSON object that exactly matches the task's `answer_template.json`. No prose
outside the JSON. Add no keys not in the template; keep every key the template declares.

## Environment / API (HTTP-only; use curl or python urllib, never WebFetch)
Base URL is supplied by the runner (e.g. `<remote-env-url>`).
Read-only endpoints:
- `GET /api/policies` — controlled enums (sponsor status, platform enums, qualification note).
- `GET /api/events`, `/api/events/{id}`, `/api/events/{id}/orders`, `/api/events/{id}/badges`,
  `/api/events/{id}/sponsor_packages`
- `GET /api/finance/invoices?event_id={id}`
- `GET /api/crm/accounts`, `/api/crm/contacts`, `/api/crm/opportunities`,
  `/api/crm/campaign_members?event_id={id}`
- `GET /api/tradeshows`, `/api/tradeshows/{show_id}/exhibitors`,
  `/api/tradeshows/{show_id}/meeting_interest`
- `GET /api/import_batches`, `/api/import_batches/{batch_id}/raw_contacts`,
  `/api/import_batches/{batch_id}/suppression`

`crm/accounts`, `crm/contacts`, `crm/opportunities` are GLOBAL (not event-scoped) — fetch once
and filter yourself. Always GET `/api/policies` first to lock the enums.

Decide the task family from the prompt:
1. **Sponsor / post-event handoff reconciliation** (event_id; orders+invoices+badges+campaign_members).
2. **Trade-show prospecting** (show_id; exhibitors+meeting_interest).
3. **Raw contact-import hygiene** (batch_id; raw_contacts+suppression).

---

## Normalization rules (apply everywhere)
- **email**: trim leading/trailing whitespace, then lowercase. Empty/whitespace-only → `""`.
- **phone**: keep digits only (strip `+ ( ) - . spaces`). Empty → `""`.
  Do NOT strip a leading country-code `1`; e.g. `"+1 415 555 0188"` → `"14155550188"`,
  but `"(415) 555-0188"` → `"4155550188"` (no `1` was present). Keep exactly the digits given.
- A contact is "contactable" if it has a non-empty email OR non-empty phone after normalization.

## Account matching (existing vs new)
- Match a lead/exhibitor/badge company to a CRM account by **account name** and/or **email
  domain == account.domain**. If matched → existing account (update). If no match → create.
- A CRM account with `status == "disqualified"` (non-null `disqualified_reason`) is DISQUALIFIED.
- A CRM contact with `opted_out == true` is suppressed; do not treat it as a usable contact, but a
  NEW differently-named badge/lead contact at that same account is still a fresh contact.

---

## FAMILY 1 — Sponsor / post-event handoff reconciliation
(Seen as: full handoff audit, and as badge-level reconciliation. Output shape varies by template;
the underlying decision rules below are constant.)

### Event facts to read
`end_date`, `start_date`, `followup_days_after_end`, `sponsor_followup_days_after_end`,
`lead_opportunity_amount`, `name`, `campaign_code`.

### Sponsor status (one row per sponsor account = each order/sponsor_package account)
Join order/package → finance invoice (by account_id+event). Controlled status enum:
`paid_deferred`, `open_invoice`, `proposal_only`, `not_sponsor`.
- order_status `confirmed` + invoice.status `paid_deferred` (paid_amount == amount) → **paid_deferred**.
- order_status `confirmed` + invoice.status `open` (paid_amount < amount, incl. paid_amount 0)
  → **open_invoice**; `open_balance = amount - paid_amount`.
- order_status `proposal_sent` + NO invoice → **proposal_only** (invoice_id null, paid 0, open_balance 0).
- order_status `canceled` → NOT an active sponsor; EXCLUDE the record (reason `inactive_sponsor_record`),
  do not emit a sponsor_status row for it.
- `amount`/`package_amount` is the order/package amount as integer USD.
- For revenue-by-status totals: bucket each active sponsor's **package/invoice amount** by its status
  (paid_deferred amount, open_invoice amount, proposal_only amount). For open invoices also report the
  **open balance separately** (`open_invoice_balance = sum(amount - paid_amount)`).

### CONFIRMED RULE — sponsor finance follow-up set
"Sponsor finance handoff / unpaid sponsors" = **ALL not-fully-paid active sponsors =
open_invoice PLUS proposal_only** (NOT just open invoices). Include proposal_only accounts in the
finance follow-up account list, count, and unpaid total. (do X: include proposal_only; not Y: only
open_invoice.) paid_deferred (fully paid) is excluded from unpaid follow-up.
- `unpaid_sponsor_total_usd` = sum of those accounts' amounts (open_invoice amount + proposal_only amount).

### Follow-up due dates (date arithmetic — calendar days, roll over month length)
- lead/qualified follow-up due = `end_date + followup_days_after_end` days.
- sponsor finance follow-up due = `end_date + sponsor_followup_days_after_end` days.
  (e.g. end 2026-09-16 +7 → 2026-09-23; +3 → 2026-09-19.) Format `YYYY-MM-DD`.

### Badge classification → qualified non-sponsor leads vs exclusions
For each badge:
- `badge_type` sponsor, OR the contact is a sponsor account's `ticket_contacts` member →
  classification **sponsor_attendee**; exclusion_reason `sponsor_attendee`.
- Non-business badge types (`student`, `press`) → classification **excluded**;
  exclusion_reason `non_business_badge`; crm_action `no_import`.
- Company maps to a DISQUALIFIED CRM account → exclude; reason `existing_disqualified`.
- A canceled-sponsor company → reason `inactive_sponsor_record`.
- Otherwise (business attendee, account not disqualified, not a sponsor contact) →
  **qualified_non_sponsor_lead**.
- `missing_contact`: badge with neither email nor phone after normalization.
- Reason precedence when several apply (prompt lists them in this order): sponsor_attendee →
  inactive_sponsor_record → non_business_badge → existing_disqualified → missing_contact.

### CRM create-vs-update for qualified leads / badge handling
- Account exists (non-disqualified) → `update_existing` (account) / for the badge a
  `create_contact_campaign_member` if the badge person is a new contact.
- No account → `create_account` / `create_account_contact_campaign_member`.
- Each qualified lead becomes a NEW campaign member → `add_campaign_member` (a create).
- Existing campaign members: if they only registered and did not attend (no badge) → `no_action`
  (keep `registered_sponsor`). Sponsor attendees already members with status `attended_sponsor`
  → `no_action`/`update_campaign_member`. New attendees get target_status `attended`
  (non-sponsor) or `attended_sponsor` (sponsor contact who attended).
- campaign-member target_status enum: `attended_sponsor`, `registered_sponsor`, `attended`, `excluded`.

### Opportunities & pipeline
- Use the event's `lead_opportunity_amount` as the opportunity amount for EACH qualified non-sponsor
  lead. `lead_pipeline_total` / open-opportunity total = (#qualified leads) × lead_opportunity_amount;
  count = #qualified leads. `lead_opportunity_amount_usd` field = the per-lead constant itself.
- Integer USD everywhere.

### Counts / task counts
- `lead_task_count` = number of qualified non-sponsor leads.
- `sponsor_finance_task_count` = number of unpaid sponsors (open_invoice + proposal_only).
- crm_action_counts: accounts_create/update, contacts_create/update,
  campaign_members_create/update derived from the per-lead create-vs-update decisions above.

### Sorting (Family 1)
- sponsor_statuses by `account_name` asc.
- qualified_lead_accounts / qualified_non_sponsor_account_names by `account_name` asc.
- badge_decisions by `badge_id` asc.
- campaign_member_actions by `subject_key` asc.
- excluded_records by `company_name` asc, then `contact_name` asc.
- badge_only_contacts by `company_name` asc; list only the qualified non-sponsor badge leads,
  with normalized_email/normalized_phone.

---

## FAMILY 2 — Trade-show prospecting  (HIGH CONFIDENCE — fully validated)
Goal: qualified import-ready exhibitors that **make / OEM-build** the target underwater platforms.
Platform enum (always this order): `AUV`, `ROV`, `Underwater Camera`.

### Qualify vs exclude (read the exhibitor `description`)
QUALIFIED = the company **manufactures / builds / designs / OEM-builds** one or more target
platforms. Assign every platform it builds:
- "AUV", "autonomous underwater vehicle", "AUV scouts" → AUV.
- "ROV", "remotely operated", "inspection-class ROV", "pen-cleaning ROV" → ROV.
- "underwater camera", "camera modules", "camera arrays", "OEM underwater camera",
  camera arrays mounted on its own ROVs → Underwater Camera. (do X: count "camera arrays" on a
  built ROV as Underwater Camera; that was correct.)
EXCLUDE (near-miss) when the company does NOT build platforms. relationship_type → exclusion_reason:
- distributor / reseller / sales agent / "does not manufacture" → `distributor` / `distributor_only`.
- service / consulting / operates rented platforms / analytics-dashboard-only / "no hardware
  manufacturing" → `service_provider` / `service_only`.
- sensor-only / probe maker for integration by others → `sensor_vendor` / `sensor_only`
  (some templates spell the near-miss reason `sensor_vendor_only` — use the template's enum).
- research/academic only → `research` / `research_only`.
- `not_target_market` only if an enum offers it and nothing else fits.
- Excluded exhibitors always get crm_action `no_import` and stay in the exclusion list.

### CRM action for qualified
- exhibitor `crm_account_id` present → `update_existing`, carry that id as crm_account_id.
- `crm_account_id` null → `create_account`, crm_account_id null.
- `existing_crm_overlap_*` = the qualified exhibitors that already have a crm_account_id;
  list those account ids ascending.

### Priority tiers & opportunity sizing (join meeting_interest by company_name)
- A = requested_demo == true AND interest_score >= 90  → USD 120000.
- B = requested_demo == true AND interest_score >= 80  → USD 90000.
- C = everything else qualified (incl. no demo, or demo with score < 80) → USD 50000.
  (These exact tier dollar values appear in the prospecting prompts; reuse them. The 90/80 demo
  thresholds also apply even when a prompt only names the campaign and not the thresholds.)
- A company with no meeting_interest row → treat requested_demo false, score 0 → tier C.

### Ranking (when template asks for ranked_leads)
Sort by: requested_demo true first, then interest_score DESC, then broader platform coverage
(more platforms first), then company_name asc. Assign contiguous 1-based `rank`.

### Aggregates
- qualified_total / qualified_lead_count, excluded count.
- platform_coverage_counts: count qualified exhibitors that include each platform (a multi-platform
  company increments every platform it builds).
- priority_counts A/B/C; total_estimated_opportunity_usd = sum of opportunity_estimate_usd.

### Sorting (Family 2)
- qualified/ranked list per template (company_name asc, or rank asc when ranked).
- excluded list by `company_name` asc.
- platforms within each item in enum order AUV, ROV, Underwater Camera.

---

## FAMILY 3 — Raw contact-import hygiene
Goal: dedupe + suppress + classify raw rows for CRM import.
`campaign_code` comes from the import_batch record (e.g. `WEB-FALL-2026`).

### Per-row processing
1. Normalize email/phone (rules above) on every raw row.
2. **Suppression**: a row is suppressed if its normalized email matches a suppression `email`
   OR its normalized phone matches a suppression `phone` (suppression phones are already digits).
   Suppressed rows → crm_action `suppress`, removal reason `suppressed`.
3. **Missing contact**: no usable email AND no usable phone → crm_action `no_import`,
   removal reason `missing_contact` (counts as "unusable").
4. **Dedup**: group surviving rows by normalized email (primary key). Pick ONE winner per group;
   the losers are removed with reason `duplicate`.
   - clean_contact_id / source_row_id = the WINNING row's `row_id`; carry the winning row's
     company_name/contact_name/email/phone/source_name/captured_at.
   - duplicate_keys: `{key, winner_row_id, removed_row_ids[]}`, key = the normalized email; sort
     by key asc; removed_row_ids are the loser row_ids.
   - NOTE (uncertain across rounds): winner tiebreak — within the same dedup key prefer the row by
     a deterministic rule. Test order: lowest `row_id`, else earliest `captured_at`, else latest.
     When two rows share the same captured_at, break by lowest row_id. Compute counts the same way
     regardless of which row is named winner.
5. **CRM action for surviving unique contacts**: company matches an existing CRM account
   (name or email-domain) → `update_existing` with `existing_account_id` set
   (existing_contact_id usually null if the person is new). No match → `create_account`
   (existing_account_id/existing_contact_id null).

### Output assembly
- `clean_contacts`: the importable surviving winners. (Whether suppressed/missing winners also
  appear here flagged with crm_action suppress/no_import vs. live only in removal_summary was NOT
  resolvable from feedback — keep clean_contacts to the importable create/update rows and put
  suppressed/missing/duplicate rows in removal_summary; report import_action_totals over ALL unique
  decisions.) Sort by `clean_contact_id` asc.
- `duplicate_summary`: {duplicate_removed_count, duplicate_keys[]}.
- `removal_summary`: {unusable_removed_count (missing), suppressed_removed_count,
  removed_rows[{row_id, reason}]}; reason enum `duplicate|missing_contact|suppressed`;
  sort removed_rows by `row_id` asc.
- `import_action_totals`: integer counts of `create_account`, `update_existing`, `no_import`,
  `suppress` across the unique deduped decisions (one decision per unique key:
  create/update for importable, suppress for suppressed, no_import for missing).
- `campaign_member_import_count`: number of surviving importable cleaned contacts
  (create_account + update_existing rows) to add to the batch campaign.
- source_name enum: `badge_scan, sponsor_form, partner_upload, webinar_form, exhibitor_form,
  manual_upload` (carry the winning row's value).

---

## Output discipline (all families)
- Match the template's keys and value enums EXACTLY; integers for all USD and counts (no decimals,
  no currency symbols).
- Use the literal required_value strings (show_id, campaign codes) where the template fixes them.
- Apply every declared sort; nested lists (platforms) also have their own ordering.
- Empty strings (not null) for missing normalized email/phone unless the template says null.
- Recompute every total/count from your own derived rows so they stay internally consistent.

## Concrete "do X, not Y" lessons from feedback
- DO include proposal_only sponsors in the sponsor finance follow-up set/count/total; NOT only
  open_invoice sponsors.
- DO exclude canceled-sponsor orders entirely from sponsor_status rows and tag them
  `inactive_sponsor_record`; NOT as a sponsor row and NOT (preferentially) as existing_disqualified.
- DO count "camera arrays"/OEM camera language as the `Underwater Camera` platform; do not drop it.
- DO use demo-then-score≥90→A / score≥80→B / else→C with $120k/$90k/$50k even when a prompt omits
  the thresholds (the rule is stable across prospecting tasks).
- DO key dedup and suppression on the NORMALIZED email/phone (trim+lowercase email, digits-only
  phone); never on the raw string.
- DO derive opportunity pipeline from the event's `lead_opportunity_amount` × qualified-lead count,
  not from CRM opportunity records for the event.
