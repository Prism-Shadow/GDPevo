# HarborCRM CRM-Marketing Task Skill

Solve HarborCRM post-event / prospecting / import-batch tasks against the shared
read-only HarborCRM API. Produce ONE JSON object matching the task's
`answer_template.json` — exactly its declared fields, nothing extra, no prose.

## 0. Environment

- Base URL: `<remote-env-url>` (use as the ONLY data source).
- Call with `curl -s <BASE><endpoint> | python3 -m json.tool`.
- Dataset is deterministic (seed 41001). All endpoints return JSON.

### Public GET endpoints
- `GET /api/policies` — authoritative rule constants (platform enums, sponsor status enums).
- `GET /api/events` and `GET /api/events/{event_id}`
- `GET /api/events/{event_id}/orders` (== sponsor packages)
- `GET /api/events/{event_id}/badges`
- `GET /api/events/{event_id}/sponsor_packages`
- `GET /api/finance/invoices?event_id={event_id}`
- `GET /api/crm/accounts`, `GET /api/crm/contacts`, `GET /api/crm/opportunities`
- `GET /api/crm/campaign_members?event_id={event_id}`
- `GET /api/tradeshows`, `GET /api/tradeshows/{show_id}/exhibitors`,
  `GET /api/tradeshows/{show_id}/meeting_interest`
- `GET /api/import_batches`, `GET /api/import_batches/{batch_id}/raw_contacts`,
  `GET /api/import_batches/{batch_id}/suppression`

### Authoritative policies (`/api/policies`)
- `prospecting.platform_enums` = `["AUV", "ROV", "Underwater Camera"]`
  (always emit platform lists in THIS order).
- `sponsor_handoff.status_enums` = `["paid_deferred", "open_invoice", "proposal_only", "not_sponsor"]`.
- `contact_hygiene.note`: normalize/contactable records before CRM import.

## 1. Universal output rules
- Return one JSON object only. No prose. No fields beyond the template.
- Money: integer USD. Counts: integers. Dates: `YYYY-MM-DD`.
- Sort every list exactly as the template states (usually by name/id ascending).
- `null` for absent ids (e.g. new account has `account_id: null`); empty string `""`
  for absent email/phone when the field allows it.
- Normalization: email → lowercase + trimmed; phone → digits only (keep all digits
  present in the source, including a leading country code if given).

## 2. Event reconciliation tasks (post-event sponsor + lead handoff)

Applies to tasks that reconcile one `event_id`: sponsor statuses, qualified lead
accounts, excluded records, follow-up, CRM action counts (and the badge-level
variant: badge decisions, campaign-member actions, opportunity summary).

### Event facts (from `/api/events/{event_id}`)
- `lead_followup_due_date` = `end_date` + `followup_days_after_end` days.
- `sponsor_followup_due_date` = `end_date` + `sponsor_followup_days_after_end` days.
- `lead_opportunity_amount` = per-qualified-lead opportunity amount for this event.

### Sponsor statuses
- Active sponsors = sponsor packages whose `order_status` is `confirmed` OR
  `proposal_sent`. **Exclude `canceled`** sponsors entirely from `sponsor_statuses`
  (they go to excluded records as `inactive_sponsor_record`).
- Derive each active sponsor's status from its finance invoice:
  - invoice `status=="paid_deferred"` → `paid_deferred`
  - invoice `status=="open"` → `open_invoice`
  - NO invoice (proposal_sent only) → `proposal_only`
- Per-sponsor fields: `package_amount` = sponsor package amount;
  `invoice_id` (null if none); `paid_amount` (0 if none);
  `open_balance` = invoice `amount` − `paid_amount` (0 if none).
- Revenue totals: sum the FULL deal amount per status
  (`paid_deferred`, `open_invoice`, `proposal_only`). `open_invoice_balance` =
  sum of open balances across open-invoice sponsors (reported separately).
- Sort `sponsor_statuses` by `account_name` ascending.

### Qualified non-sponsor lead accounts
A badge qualifies as a lead when ALL hold:
- `badge_type` is a business attendee type (NOT `sponsor`, NOT `student`, NOT `press`).
  `student`/`press` → excluded (`non_business_badge`).
- The badge's company is NOT an active sponsor (confirmed or proposal_sent).
  - A `badge_type:"sponsor"` badge → excluded (`sponsor_attendee`).
  - A badge whose company is an active sponsor (even proposal_only) and whose
    contact matches a sponsor `ticket_contact` → `sponsor_attendee` (NOT a lead),
    even when the badge_type itself is `attendee`.
- The badge's company is NOT a canceled sponsor → else `inactive_sponsor_record`.
- The CRM account for the company is NOT disqualified → else
  `existing_disqualified`.
- Contactability: a lead with a phone but NO email is STILL qualified (use empty
  email). `missing_contact` only when there is neither email nor phone.
- Qualified leads get `opportunity_amount` = event `lead_opportunity_amount`.
- CRM actions per qualified lead:
  - `crm_account_action`: `create_account` if no matching CRM account (by email
    domain), else `update_existing`.
  - `crm_contact_action`: `create_contact` if the badge contact is a NEW person
    (not an existing CRM contact), else `update_existing`. A new person on an
    existing account is STILL `create_contact` (do not mirror account action).
  - `campaign_member_action`: `add_campaign_member` (qualified leads get a new
    member; excluded leads get NO campaign-member action).
- `lead_pipeline_total` / `open_opportunity_total_usd` =
  `lead_opportunity_amount` × number of qualified leads.
- Sort qualified leads by `account_name` ascending.

### Excluded records
Reasons (controlled): `sponsor_attendee`, `inactive_sponsor_record`,
`non_business_badge`, `existing_disqualified`, `missing_contact`.
- `sponsor_attendee`: badge_type `sponsor`, OR attendee whose company is an
  active sponsor and contact is a sponsor ticket_contact.
- `inactive_sponsor_record`: company had a `canceled` sponsor order.
- `non_business_badge`: `student` or `press` badge types.
- `existing_disqualified`: CRM account `status=="disqualified"`.
- `missing_contact`: no email AND no phone.
- When a record matches more than one rule, `inactive_sponsor_record` is preferred
  for canceled-sponsor companies; `existing_disqualified` for non-sponsor
  disqualified accounts. (Both reason values were accepted for a record that was
  both canceled-sponsor and disqualified — prefer `inactive_sponsor_record`.)
- Sort excluded by `company_name`, then `contact_name`.

### Follow-up
- `lead_task_count` = number of qualified lead accounts.
- `sponsor_finance_accounts` (or `unpaid_sponsor_account_names`) =
  active sponsors that are NOT fully paid = `open_invoice` + `proposal_only`
  (exclude `paid_deferred`, which is fully collected; exclude canceled).
  `sponsor_finance_task_count` / count = number of those accounts.
- `unpaid_sponsor_total_usd` = sum of unpaid amounts (open balance for invoiced
  sponsors; full package amount for proposal_only sponsors with no payment).

### CRM action counts (lead handoff only)
Tally only the work implied for QUALIFIED leads (excluded records imply no action):
- `accounts_create` / `accounts_update`, `contacts_create` / `contacts_update`,
  `campaign_members_create` / `campaign_members_update` (update is 0 unless an
  excluded lead's existing member is being re-statused — generally 0).

## 3. Badge-level reconciliation variant (per-badge decisions + campaign members)

Same sponsor/lead/exclusion logic as §2, plus:

### badge_decisions (sorted by `badge_id`)
- `classification`: `sponsor_attendee` | `qualified_non_sponsor_lead` | `excluded`.
- `crm_action`:
  - new account+contact+member → `create_account_contact_campaign_member`
  - existing account, new contact+member → `create_contact_campaign_member`
  - existing account+contact, new member → `add_campaign_member`
  - existing member needing change → `update_campaign_member`
  - sponsor attendee / already-correct → `no_action`
  - excluded (non-business / disqualified / missing) → `no_import`
- `exclusion_reason`: null for qualified; the controlled reason otherwise.

### campaign_member_actions (sorted by `subject_key` ascending)
- `action`: `create` | `update` | `no_action` | `no_import`.
- `target_status`: `attended_sponsor` | `registered_sponsor` | `attended` | `excluded`.
- Qualified lead (no member) who scanned a badge → `create`, `attended`.
- Existing sponsor member already correct (e.g. `attended_sponsor`) → `no_action`,
  same status. Sponsor who registered but did not scan → `no_action`,
  `registered_sponsor`.
- Excluded badge → `no_import`, `excluded`.
- Include existing sponsor campaign members (with `no_action`) even if they have no
  badge scan, so their disposition is represented. Use the CRM `contact_id` as
  `subject_key` for existing contacts; use the normalized email (or badge id when
  no email) for new contacts.
- `exclusion_counts`: tally of `sponsor_attendee`, `non_business_badge`,
  `existing_disqualified`, `missing_contact`.

### opportunity_summary
- `qualified_non_sponsor_account_names`: sorted ascending.
- `lead_opportunity_amount_usd`: event `lead_opportunity_amount`.
- `open_opportunity_total_usd` = lead_opportunity_amount × #qualified.
- `open_opportunity_count` = #qualified.

### badge_only_contacts (sorted by `company_name`)
Normalized contact facts for qualified non-sponsor leads:
`company_name`, `contact_name`, `normalized_email` (lowercase, "" allowed),
`normalized_phone` (digits only, "" allowed).

## 4. Prospecting tasks (tradeshow exhibitor qualification)

Applies to `/api/tradeshows/{show_id}/exhibitors` + `meeting_interest` tasks.

### Qualification
- Qualified = exhibitor that BUILDS / MANUFACTURES / DESIGNS / OEM-builds a target
  platform (`AUV`, `ROV`, `Underwater Camera`). Read the `description`.
  - "Builds AUVs and ROVs" → `[AUV, ROV]`.
  - "Manufactures ROVs with camera arrays" → `[ROV, Underwater Camera]` (camera
    arrays count as building underwater cameras).
  - "Designs underwater camera modules" → `[Underwater Camera]`.
- Excluded (adjacent, not a platform builder):
  - distributor / reseller → `distributor_only` (relationship_type `distributor`)
  - service / consulting / analytics-only → `service_only` (`service_provider`)
  - sensor-only vendor → `sensor_vendor_only` / `sensor_only` (`sensor_vendor`)
  - research-only → `research_only` (`research`)
  - (some templates also allow `not_target_market`)
- `platforms` list always in enum order `AUV, ROV, Underwater Camera`.
- `crm_action`: `update_existing` if `crm_account_id` present, else
  `create_account`; excluded → `no_import`.

### Priority tier & opportunity sizing (when the template requires it)
- `A`: requested_demo AND interest_score ≥ 90 → USD 120000
- `B`: requested_demo AND interest_score ≥ 80 → USD 90000
- `C`: all other qualified leads → USD 50000
(Use the exact tier-to-USD mapping stated in the task prompt if it differs.)

### Ranking (when the template requires ranked_leads)
Order: requested_demo (true first) → interest_score descending → broader platform
coverage (more platforms first) → company_name ascending. Rank is 1-based contiguous.

### Summary aggregates
- `qualified_lead_count` / `excluded_count`.
- `existing_crm_overlap_count` + `existing_crm_overlap_account_ids` (CRM account
  ids of qualified leads already in CRM, sorted ascending).
- `total_estimated_opportunity_usd` = sum of tier opportunity amounts.
- `platform_coverage_counts`: how many qualified leads cover each platform
  (`AUV`/`ROV`/`Underwater Camera`).
- `priority_counts` (A/B/C) and `platform_counts` where the template asks.
- Note: in some prospecting templates the `qualified_exhibitors` item schema does
  NOT include `crm_action`/`opportunity` — output ONLY the declared fields.

## 5. Import-batch cleaning tasks

Applies to `/api/import_batches/{batch_id}/raw_contacts` + `suppression`.

### Deduplication
- Duplicate key = normalized email (lowercase, trimmed). Rows sharing the same
  normalized email are one group.
- Winner selection: prefer the HIGHER-priority `source_name` by the enum order
  `badge_scan > sponsor_form > partner_upload > webinar_form > exhibitor_form >
  manual_upload` (earlier = higher). `partner_upload` outranks `webinar_form`.
  Break remaining ties by latest `captured_at`, then lowest `row_id`.
- `clean_contact_id` and `source_row_id` = the winning row's `row_id`.
- `duplicate_summary`: `duplicate_removed_count` + `duplicate_keys` (sorted by key
  ascending), each with `winner_row_id` and `removed_row_ids`.

### Removals
- `suppressed`: row whose normalized email OR phone matches the batch suppression
  list → removal reason `suppressed`, final disposition `suppress`.
- `missing_contact`: row with no email AND no phone → reason `missing_contact`,
  disposition `no_import`.
- `duplicate`: losing duplicate rows → reason `duplicate`, disposition `no_import`.
- `removal_summary`: `unusable_removed_count` (= missing_contact count),
  `suppressed_removed_count` (= suppressed count), `removed_rows` sorted by
  `row_id` ascending.

### clean_contacts (survivors = dedup winners minus suppressed/missing)
Fields: `clean_contact_id`, `source_row_id`, `company_name`, `contact_name`,
`email` (normalized or ""), `phone` (digits or ""), `source_name`, `captured_at`
(from winning row), `crm_action`, `existing_account_id`, `existing_contact_id`.
- `crm_action`: `create_account` if no CRM account matches the email domain,
  else `update_existing`. (Suppressed/missing never reach clean_contacts.)
- `existing_account_id`: CRM account id whose `domain` matches the email domain,
  else null. `existing_contact_id`: matching CRM contact id, else null.
- Sort by `clean_contact_id` ascending.

### import_action_totals
Tally the FINAL disposition of EVERY raw row (not just survivors):
- `create_account`: survivors creating a new account
- `update_existing`: survivors updating an existing account
- `no_import`: duplicate losers + missing_contact rows
- `suppress`: suppressed rows
(These sum to the total raw row count.)
`campaign_member_import_count` = number of surviving cleaned contacts.

## 6. Solve procedure per task
1. Read the prompt + `answer_template.json`; identify task type
   (event reconciliation / prospecting / import batch). The TEMPLATE defines the
   exact output shape — emit only its declared fields.
2. Fetch `/api/policies` for enum constants, then the task-specific endpoints.
3. Apply the rules above; normalize email/phone; sort as specified.
4. Do not call any judge endpoint at solve time. The train-only feedback has
   already been distilled into the rules below.
5. Key pitfalls confirmed by the judge:
   - proposal_only sponsors ARE active (in sponsor_statuses AND in unpaid/finance
     follow-up) — do not drop them.
   - A lead with phone but no email is still qualified (only no-email-AND-no-phone
     is `missing_contact`).
   - An attendee badge from an active sponsor company (incl. proposal_only) whose
     contact is a sponsor ticket_contact is `sponsor_attendee`, NOT a lead.
   - New contact on an existing account → `create_contact` (not `update_existing`).
   - Dedup winner: `partner_upload` beats `webinar_form`.
   - Excluded records get NO campaign-member action; CRM action counts cover only
     qualified leads.
   - "camera arrays" / integrated cameras count as building `Underwater Camera`.
