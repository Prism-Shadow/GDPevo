# HarborCRM CRM-Marketing Task Solver

Transferable skill for solving HarborCRM post-event / prospecting / import-batch tasks.
Learned by iterating train tasks against the train-only judge. Generalized — no hardcoded
account names, ids, or numeric answers.

## 0. Environment

- Base API URL: supplied by the runner (e.g. `<remote-env-url>`). All data is read-only GET.
- Authoritative rule constants live at `GET /api/policies`:
  - `prospecting.platform_enums` = `["AUV","ROV","Underwater Camera"]`
  - `sponsor_handoff.status_enums` = `["paid_deferred","open_invoice","proposal_only","not_sponsor"]`
- Every task returns ONE JSON object only (no prose outside JSON), matching the provided `answer_template.json`.
- Re-read the answer template for EACH task: field names, enums, and ordering rules differ per task
  even within the same family. Do not assume a field from one task exists in another.

## 1. Data model (endpoints you will need)

- Events: `/api/events/{event_id}`, `/orders`, `/badges`, `/sponsor_packages`
- Finance: `/api/finance/invoices?event_id={event_id}`
- CRM: `/api/crm/accounts`, `/api/crm/contacts`, `/api/crm/opportunities`, `/api/crm/campaign_members?event_id={event_id}`
- Tradeshows: `/api/tradeshows`, `/api/tradeshows/{show_id}/exhibitors`, `/api/tradeshows/{show_id}/meeting_interest`
- Import batches: `/api/import_batches`, `/api/import_batches/{batch_id}/raw_contacts`, `/api/import_batches/{batch_id}/suppression`

Key cross-references: accounts have `account_id`, `domain`, `status` (customer/prospect/disqualified),
`disqualified_reason`. Contacts have `contact_id`, `account_id`, `email`, `opted_out`. Matching between
badge/import rows and CRM is by **email domain** for accounts and **exact email/name** for contacts.

## 2. Step-by-step solver workflow

### Step A — Classify the task family
Read the prompt + template top-level keys and decide:
- **Prospecting** (tradeshow exhibitors → qualified leads): keys like `qualified_exhibitors` / `ranked_leads`, `excluded_near_misses`, `aggregate_counts`. → workflow B.
- **Sponsor + lead handoff / reconciliation** (event badges + sponsor orders + finance): keys like `sponsor_statuses`, `qualified_lead_accounts` / `badge_decisions`, `follow_up`, `crm_action_counts` / `exclusion_counts`. → workflow C.
- **Import batch cleaning**: keys like `clean_contacts`, `duplicate_summary`, `removal_summary`, `import_action_totals`. → workflow D.

### Step B — Prospecting workflow
1. Fetch exhibitors + meeting_interest + accounts + policies.
2. For each exhibitor, decide **qualified vs excluded** using the description + company context:
   - QUALIFIED = the exhibitor **manufactures / OEM-builds** at least one target platform
     (`AUV`, `ROV`, `Underwater Camera`). "Builds", "manufactures", "OEM ... manufacturer" = builds.
   - EXCLUDED = only adjacent: distributor/reseller ("distributor_only"),
     service/consulting/operates-rented ("service_only"), sensor-only vendor ("sensor_vendor_only"/"sensor_only"),
     research/academic ("research_only"), or otherwise not a platform builder ("not_target_market" where allowed).
   - Map the company's platforms from the description (e.g. "AUVs and ROVs" → `[AUV, ROV]`;
     "underwater camera modules" → `[Underwater Camera]`). Sort platforms in enum order AUV, ROV, Underwater Camera.
3. Determine `priority_tier` from meeting_interest:
   - `A` = requested_demo AND interest_score ≥ 90
   - `B` = requested_demo AND interest_score ≥ 80
   - `C` = all other qualified leads
   (Apply the explicit rule in the prompt when present; the same thresholds are the implied default.)
4. Opportunity sizing by tier when the prompt gives amounts: A/B/C map to the stated USD figures
   (e.g. 120000 / 90000 / 50000). Use them verbatim.
5. CRM action per qualified lead: `create_account` if no `crm_account_id`, else `update_existing`.
   `crm_account_id` = the exhibitor's `crm_account_id` field (null when absent).
6. Ranking (when template wants `ranked_leads`): demo-requested first, then interest_score descending,
   then broader platform coverage (more platforms first), then company_name ascending. `rank` is 1-based contiguous.
7. Aggregates: `qualified_total`, `excluded_*_total`, `platform_counts` (count of qualified leads covering each platform),
   `priority_counts`, `existing_crm_overlap_count` + `existing_crm_overlap_account_ids` (qualified leads that have a CRM account, IDs ascending),
   `total_estimated_opportunity_usd` (sum of tier amounts).
8. Sort outputs exactly as the template states (usually company_name ascending, or rank ascending).

### Step C — Sponsor + lead handoff / reconciliation workflow
1. Fetch event, orders, badges, invoices, accounts, contacts, opportunities, campaign_members, policies.
2. **Sponsor statuses** (one row per ACTIVE sponsor account, sorted by account_name asc):
   - Match each sponsor order to its finance invoice by `account_id`.
   - `paid_deferred` = invoice `status` paid_deferred (paid_amount == amount, deferred).
   - `open_invoice` = invoice `status` open (paid_amount < amount).
   - `proposal_only` = order `order_status` proposal_sent AND no invoice.
   - Exclude **canceled** sponsor orders from sponsor_statuses (they go to excluded_records as `inactive_sponsor_record`).
   - `amount_usd` / `package_amount` = the order `amount`. `paid_amount` and `open_balance` (= amount − paid_amount) from the invoice.
   - `not_sponsor` enum value is reserved for non-sponsor accounts only when the template explicitly lists it and context requires it; do not invent it otherwise.
3. **Sponsor revenue totals** = sum of the **package/contract `amount`** per status bucket (NOT paid cash, NOT open balance):
   - `paid_deferred` = Σ package amounts of paid_deferred sponsors
   - `open_invoice` = Σ package amounts of open_invoice sponsors
   - `proposal_only` = Σ package amounts of proposal_only sponsors
   - `open_invoice_balance` = Σ open balances of open_invoice sponsors (reported separately)
4. **Follow-up dates**: `lead_due_date`/`lead_followup_due_date` = event `end_date` + `followup_days_after_end`.
   `sponsor_finance_due_date`/`sponsor_followup_due_date` = `end_date` + `sponsor_followup_days_after_end`.
5. **Sponsor finance follow-up targets** = sponsors that are **not fully paid** = `open_invoice` + `proposal_only`
   (do NOT include `paid_deferred`). `task_count` = number of those accounts; `unpaid_sponsor_total_usd` = Σ their package amounts.
6. **Qualified non-sponsor leads** come from event badges:
   - Include attendee-type badges whose company is NOT a sponsor (any order_status) and whose CRM account is not disqualified.
   - Use the event's `lead_opportunity_amount` per qualified account; `lead_pipeline_total` = count × that amount.
   - CRM account action: `update_existing` if a CRM account matches the badge email domain, else `create_account`.
   - CRM **contact** action: `create_contact` if that specific person is not already a CRM contact (even when the account exists),
     else `update_existing`. Match contacts by exact email/name, NOT by account.
   - `campaign_member_action` for qualified leads = `add_campaign_member` (they are new members).
7. **Excluded records** (badges filtered out), with controlled reasons:
   - `sponsor_attendee` — badge_type sponsor OR the badge company has a sponsor order (incl. proposal/canceled).
   - `non_business_badge` — student, press, or other non-business badge types.
   - `existing_disqualified` — the badge company's CRM account `status` is disqualified.
   - `inactive_sponsor_record` — a canceled sponsor record / its ticket contact.
   - When multiple reasons could apply to one record, prefer the most sponsor-specific one first
     (sponsor_attendee / inactive_sponsor_record) before existing_disqualified; a canceled sponsor's contact is `inactive_sponsor_record`.
8. **exclusion_counts** tally each exclusion reason across badges.
9. **crm_action_counts**: accounts_create/update and contacts_create/update follow the per-lead actions above;
   `campaign_members_create` = number of qualified leads; `campaign_members_update` = **0** (do not count excluded
   or disqualified existing members as updates).
10. For the richer reconciliation template (`badge_decisions`, `campaign_member_actions`, `opportunity_summary`,
    `badge_only_contacts`):
    - `badge_decisions`: one per badge, sorted by badge_id asc. `classification` ∈ {sponsor_attendee, qualified_non_sponsor_lead, excluded}.
      `crm_action` ∈ {create_account_contact_campaign_member (new account+contact+member), create_contact_campaign_member (existing account, new contact+member),
      add_campaign_member (existing contact), update_campaign_member (existing member reconciled), no_action, no_import}.
      `exclusion_reason` null when classification is qualified.
    - A badge with email="" but a phone present is still a valid qualified lead (badge_only_contact allows empty email).
    - `badge_only_contacts` = qualified leads with NO matching CRM account (normalized email lowercase-trimmed, phone digits-only; empty string allowed for missing email/phone).
    - Proposal-only sponsor attendees are EXCLUDED (sponsor_attendee) and are NOT created as campaign members (no_import).
    - `opportunity_summary.lead_opportunity_amount_usd` = the event lead opportunity amount applied to qualified non-sponsor accounts
      (report as the total pipeline = count × per-account amount); `open_opportunity_total_usd`/`open_opportunity_count` = existing OPEN CRM opportunities for the qualified accounts (usually 0 when they have no CRM account).
    - `campaign_member_actions`: existing sponsor members are reconciled (no_action when status already matches attendance; update otherwise);
      new qualified leads → create with target_status `attended`; excluded → no_import with target_status `excluded`. Sort by subject_key ascending.

### Step D — Import batch cleaning workflow
1. Fetch raw_contacts, suppression, accounts, contacts, policies; identify `batch_id` and `campaign_code` from `/api/import_batches`.
2. **Normalize** each raw row: email = lowercase + trim (whitespace stripped); phone = digits only (strip `+ - ( ) . spaces`, keep leading `1`).
   A row with empty email but a phone is still usable. A row with BOTH empty email and empty phone = `missing_contact`.
3. **Deduplicate** by normalized email (the duplicate key = normalized email):
   - Group rows sharing the same normalized email.
   - **Winner = the most recent `captured_at`**; on a timestamp tie, partner-style sources outrank self-serve forms
     (source priority roughly: badge_scan, sponsor_form, partner_upload, webinar_form, exhibitor_form, manual_upload — earlier enum = higher priority).
     (Do NOT use first-seen/earliest — that is wrong.)
   - The winner becomes a clean contact (its `clean_contact_id` = `source_row_id` = winning row_id; `captured_at` from the winning row;
     `company_name` = the winning row's raw company name). Losers are removed with reason `duplicate`.
   - `duplicate_summary.duplicate_removed_count` = number of loser rows; one `duplicate_keys` entry per group (key, winner_row_id, removed_row_ids[]), sorted by key ascending.
4. **Suppress**: any row whose normalized email OR normalized phone appears in the suppression list → removed with reason `suppressed`.
5. **removal_summary**: `unusable_removed_count` = count of `missing_contact` rows ONLY (do NOT add duplicates here);
   `suppressed_removed_count` = count of suppressed rows; `removed_rows` lists ALL removed rows (duplicates + missing + suppressed),
   sorted by row_id ascending, each with its reason ∈ {duplicate, missing_contact, suppressed}.
6. **Clean contacts** (survivors), sorted by clean_contact_id ascending:
   - `existing_account_id` = CRM account matched by email domain (else null). `existing_contact_id` = CRM contact matched by exact email (else null; a different person on the same account is still null).
   - `crm_action`: `update_existing` if existing_account_id set, else `create_account`. (no_import/suppress apply only to removed rows.)
7. **import_action_totals**: tally the `crm_action` of the surviving clean contacts
   (`create_account` / `update_existing`). `no_import` and `suppress` categories are 0 unless the template clearly wants removed-row dispositions counted.
8. **campaign_member_import_count** = number of surviving clean contacts (all of them become members of the batch campaign).

## 3. Universal normalization & formatting rules
- Email: lowercase, strip surrounding whitespace. ` " Dana.Ruiz@Foo.example " ` → `dana.ruiz@foo.example`.
- Phone: keep digits only (drop `+`, spaces, dashes, dots, parens). `+1 (415) 555-0188` → `14155550188`. Empty string when none.
- All money fields: integer USD.
- Dates: `YYYY-MM-DD`. Date arithmetic = event `end_date` + the policy day counts.
- Sorting: always ascending on the field the template names; tie-break by the next named field.
- Output: exactly one JSON object, only the keys the template declares, no extra fields, no prose.

## 4. Pitfalls learned from judge feedback (concrete corrections)

These are mistakes that the judge penalized — avoid them. Each was confirmed by a score drop when the wrong version was submitted.

1. **Dedup winner is MOST RECENT, not first-seen.** Submitting the earliest row as the winner collapsed
   the import-batch score from 0.71 to 0.21. Use latest `captured_at`; break ties by source priority (partner_upload over webinar_form).

2. **`unusable_removed_count` = missing-contact rows only.** Adding duplicates into "unusable" dropped the
   import-batch score from 0.71 to 0.57. Duplicates have their own `duplicate_summary`; only `missing_contact` rows count as unusable.

3. **Contact action is per-person, not per-account.** For a lead on an EXISTING account whose contact person
   is NEW, use `create_contact` (not `update_existing`). Mirroring the account action onto the contact dropped the
   sponsor-handoff score from 0.87 to 0.60. Match contacts by exact email/name; only reuse `update_existing` when that specific person already exists.

4. **Do not update campaign members for excluded/disqualified records.** Setting `campaign_members_update=1`
   for a disqualified existing member dropped the sponsor-handoff score from 0.87 to 0.80. Excluded records take no campaign-member action;
   `campaign_members_update` stays 0 when all eligible members are new.

5. **Sponsor finance follow-up includes `proposal_only`, not just `open_invoice`.** Narrowing finance follow-up
   to open-invoice-only (excluding proposal-only sponsors) crashed the reconciliation score from 0.54 to 0.38. The finance/unpaid
   set = every sponsor that has not fully paid = `open_invoice` + `proposal_only`. `unpaid_sponsor_total_usd` = Σ their package amounts.

6. **Proposal-only sponsor attendees are NOT created as campaign members.** Marking a proposal-only sponsor's
   badge-scanning contact as a created campaign member (attended_sponsor) crashed the reconciliation score from 0.54 to 0.38.
   Only confirmed sponsors' attendees are campaign members; proposal-only attendees stay `no_import` / excluded.

7. **`sponsor_revenue_totals` uses package/contract amounts, not paid cash.** Reporting `open_invoice` as the
   paid_amount (10000) and `proposal_only` as 0 dropped the sponsor-handoff score from 0.87 to 0.73. Use the full package `amount`
   for each status bucket; report the unpaid portion separately in `open_invoice_balance`.

8. **A no-email badge with a phone is still a qualified lead.** The badge-only-contacts template explicitly
   permits `normalized_email: ""`. Do not classify an email-less badge with a usable phone as `missing_contact`; `missing_contact`
   requires BOTH email and phone to be absent.

9. **Sort everything the template mentions.** Forgetting an ascending sort (by account_name / company_name /
   badge_id / row_id / key / rank / subject_key) silently breaks otherwise-correct content.

10. **Re-read each template's enums.** Exclusion-reason enums differ across tasks
    (`sensor_vendor_only` in one, `sensor_only` in another; `not_target_market` only in some). Use exactly the task's enum strings.

## 5. Open uncertainties (treat carefully on test tasks)

The judge scores below 1.0 on the sponsor-handoff/import/reconciliation train tasks could not be fully closed.
Likely culprits if a similar test task scores low:
- **`import_action_totals`**: whether `suppress`/`no_import` should also count removed rows (suppressed/missing)
  in addition to clean-contact create/update was judge-neutral on train; try clean-contact-only first, and if the
  whole section is wrong, also report suppress=count(suppressed) and no_import=count(missing).
- **`campaign_member_actions` `subject_key`**: the exact identifier format (email vs contact_id vs contact_name)
  and whether no_action vs update applies to already-correct existing sponsor members — verify against the template's
  wording; sort by whatever stable key you choose and keep it consistent.
- **`opportunity_summary.lead_opportunity_amount_usd`**: report as the total lead pipeline
  (qualified count × per-account lead_opportunity_amount) when the field sits next to a `_total_` field; if a task's
  template reads it as the single configured amount, switch to the per-account value.

When stuck, prefer the interpretation that keeps totals internally consistent (counts sum correctly, totals = Σ of their items)
and that matches the exact enum strings and ordering in that task's template.
