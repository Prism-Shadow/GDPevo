---
name: harborcrm-front-of-funnel-handoff
description: SOP for HarborCRM front-of-funnel tasks — post-event sponsor/lead handoff, trade-show prospecting, and raw-contact import hygiene — using the read-only HarborCRM data API.
---

# HarborCRM Front-of-Funnel Handoff Skill

Solves four recurring task families in the HarborCRM domain:
1. **Post-event CRM handoff / reconciliation** (sponsor status + qualified non-sponsor leads).
2. **Trade-show prospecting** (qualify exhibitors by platform fit, rank, size opportunities).
3. **Raw-contact import hygiene** (normalize, dedupe, suppress, CRM-match).

Each test gives a prompt + an `answer_template.json`. **The template is authoritative**: emit exactly its keys, enums, ordering, and types — nothing more, nothing less. Per-task enum sets and schema shapes vary; always read the template first and copy its allowed values verbatim. Output JSON only, no prose.

---

## 0. The remote API (read-only, HTTP-only)

Base URL: supplied by runner (e.g. `<remote-env-url>`). Use `curl` or python `urllib`. **Never WebFetch** (forces HTTPS; host is HTTP-only).

Endpoints and what they are for:
- `GET /api/policies` — controlled value enums + notes. Sparse; most rules are inferred from data + template. Always fetch it but do not expect it to give thresholds.
- `GET /api/events/{id}` — `start_date`, `end_date`, `status`, `campaign_code`, `lead_opportunity_amount`, `followup_days_after_end`, `sponsor_followup_days_after_end`.
- `GET /api/events/{id}/orders` and `/sponsor_packages` — sponsor orders (`account_id`, `account_name`, `amount`, `package_level`, `order_status` ∈ {confirmed, proposal_sent, canceled}, `ticket_contacts`). Orders and sponsor_packages are usually the same rows.
- `GET /api/events/{id}/badges` — scanned attendees (`badge_id`, `badge_type` ∈ {sponsor, attendee, student, press, …}, `company_name`, `contact_name`, `email`, `phone`, `job_title`).
- `GET /api/finance/invoices?event_id={id}` — `invoice_id`, `amount`, `paid_amount`, `deferred_amount`, `status` ∈ {paid_deferred, open, …}, `payment_date`.
- `GET /api/crm/accounts` — `account_id`, `name`, `domain`, `status` ∈ {prospect, customer, disqualified}, `disqualified_reason`.
- `GET /api/crm/contacts` — `contact_id`, `account_id`, `name`, `email`, `phone`, `opted_out`.
- `GET /api/crm/opportunities` — `account_id`, `amount`, `event_id`, `stage`.
- `GET /api/crm/campaign_members?event_id={id}` — existing members (`account_id`, `contact_id`, `status` ∈ {attended_sponsor, registered_sponsor, attended}).
- `GET /api/tradeshows`, `/api/tradeshows/{id}/exhibitors`, `/api/tradeshows/{id}/meeting_interest`.
- `GET /api/import_batches`, `/api/import_batches/{id}/raw_contacts`, `/api/import_batches/{id}/suppression`.

Fetch only what the task family needs (see each SOP). Match accounts to companies by **email/website domain**, not by display name (names vary: "HelioWare Manufacturing" vs "HelioWare Mfg.").

---

## 1. Normalization rules (used everywhere)

- **Email**: trim surrounding whitespace, lowercase. If the result is empty/blank → empty string `""`. Domain = substring after `@` (for account matching).
- **Phone**: strip everything except digits (`[^0-9]` removed). Keep leading country-code digits if present in the source (e.g. `+1 415 555 0188` → `14155550188`; `(415) 555-0188` → `4155550188`). Do **not** invent or strip a country code that wasn't there. Empty/blank → `""`.
- A contact is **contactable** iff it has a non-empty normalized email **or** non-empty normalized phone. Email-only and phone-only are both fine.
- Output amounts as **integer USD** (no decimals, no currency symbol).

---

## 2. Sponsor status classification (event reconciliation)

For every account that has a sponsor **order/package** for the event, reconcile order + invoice:

| order_status | invoice present? | invoice paid fully? | → sponsor_status |
|---|---|---|---|
| confirmed | yes, `status=paid_deferred` and `paid_amount == amount` | yes | **paid_deferred** |
| confirmed | yes, `status=open` (paid_amount < amount) | no | **open_invoice** |
| proposal_sent | no invoice (or no payment) | — | **proposal_only** |
| canceled | — | — | **not a sponsor** → see below |

- `open_invoice` open balance = `invoice.amount − invoice.paid_amount` (use `amount`, not `deferred_amount`).
- **Canceled orders**: how to report depends on the template's `sponsor_status` enum:
  - If the enum **includes `not_sponsor`** → list the canceled/non-sponsor account with `sponsor_status = not_sponsor` (amount = its package/order amount, or 0 if none).
  - If the enum **omits `not_sponsor`** (only paid_deferred/open_invoice/proposal_only) → **exclude** the canceled account from `sponsor_statuses` and instead surface it in the exclusion list with reason `inactive_sponsor_record`.
- Revenue-by-status totals: sum **package/order `amount`** per status bucket. `open_invoice` total = full package amount of open-invoice sponsors; `open_invoice_balance` = sum of their open balances (amount − paid_amount). `proposal_only` total = sum of proposal amounts.
- Sort `sponsor_statuses` by `account_name` ascending.

**Unpaid / sponsor-finance follow-up set** = sponsors that are NOT `paid_deferred`, i.e. `open_invoice` + `proposal_only`. Their total = sum of their package amounts. (If a template clearly scopes it to "open invoices only," restrict to `open_invoice`. Default: include both.) `paid_deferred` sponsors are settled and need no finance follow-up.

---

## 3. Badge / lead classification (event reconciliation)

For each badge, classify into `sponsor_attendee` / `qualified_non_sponsor_lead` / `excluded`:

1. **sponsor_attendee** — the badge's company has ANY sponsor order for the event (confirmed OR proposal_sent — proposal-stage accounts are on the sponsor track, not the lead track) **or** the badge_type is `sponsor`. Exclusion reason `sponsor_attendee`. Not a sales lead.
2. **excluded — non_business_badge** — badge_type is non-business (`student`, `press`, `guest`, `media`, etc.). Reason `non_business_badge`.
3. **excluded — existing_disqualified** — the badge's company matches a CRM account whose `status == disqualified` (has a `disqualified_reason`). Reason `existing_disqualified`.
4. **excluded — missing_contact** — badge has neither email nor phone after normalization (not contactable). Reason `missing_contact`.
5. Otherwise → **qualified_non_sponsor_lead** (business attendee, contactable, account not disqualified, company is not a sponsor).

Precedence when several apply: sponsor_attendee → non_business_badge → existing_disqualified → missing_contact. (A disqualified-account attendee that is also a canceled sponsor's contact is genuinely ambiguous; prefer the account-level `existing_disqualified` if the CRM account is flagged disqualified, else `inactive_sponsor_record`.)

CRM action for each badge (use the template's `crm_action` enum — names differ per task):
- Qualified lead, company **not** in CRM → create account + contact + campaign member (`create_account_contact_campaign_member`, or in the leaner schema: `crm_account_action=create_account`, `crm_contact_action=create_contact`, `campaign_member_action=add_campaign_member`).
- Qualified lead, company **in** CRM but contact missing → `create_contact_campaign_member` (account `update_existing`, contact `create_contact`).
- Qualified lead already a campaign member → `update_campaign_member` / `add_campaign_member` per template; sponsor attendee already a correct member → `no_action`.
- Excluded badge → `no_import` (or `no_action` for sponsor attendees already handled).

`badge_decisions` sort by `badge_id` ascending.

---

## 4. Campaign-member actions & target status (event reconciliation)

Compare each subject (sponsor ticket contacts + qualified leads) against existing `campaign_members`:
- Already a member with the correct status → `no_action`.
- New subject who should be a member → `create`.
- Member whose status should change → `update`.
- Excluded subject → `no_import`.

`target_status` mapping:
- Sponsor account, contact **attended** (has a badge scan) → `attended_sponsor`.
- Sponsor account, **registered only** (no badge scan) → `registered_sponsor`.
- Qualified non-sponsor lead who attended → `attended`.
- Excluded → `excluded`.

Sort by `subject_key` ascending (or as the template specifies).

`crm_action_counts` (when present) tally the implied work across qualified leads (and any member updates): accounts_create/update, contacts_create/update, campaign_members_create/update. New leads each contribute one create per dimension as applicable; an existing account contributes accounts_update.

---

## 5. Opportunity & pipeline math (event reconciliation)

- Each qualified non-sponsor lead's opportunity = the event's `lead_opportunity_amount`.
- `lead_pipeline_total` / `open_opportunity_total_usd` = (count of qualified non-sponsor leads) × `lead_opportunity_amount`. `open_opportunity_count` = that count.
- `qualified_non_sponsor_account_names` = distinct company names of qualified leads, sorted ascending.

---

## 6. Follow-up due dates (event reconciliation)

- **Lead follow-up due date** = event `end_date` + `followup_days_after_end` (calendar days).
- **Sponsor finance follow-up due date** = event `end_date` + `sponsor_followup_days_after_end`.
- Format `YYYY-MM-DD`. Use the **end_date** (not start_date) as the base; single-day events have start_date==end_date.
- `lead_task_count` = number of qualified-lead handoff tasks (= qualified lead count). `sponsor_finance_task_count` = number of unpaid sponsor accounts (Section 2).

---

## 7. Trade-show prospecting SOP

Goal: from exhibitors, pick those that **manufacture / OEM-build** target underwater platforms, rank them, size opportunities, and list near-miss exclusions.

Endpoints: `/api/tradeshows/{show}/exhibitors`, `/.../meeting_interest`, `/api/crm/accounts`, `/api/policies`.

### Platform enums (fixed): `AUV`, `ROV`, `Underwater Camera`. Always list platforms in **that enum order**.
Read the exhibitor `description` to assign platforms:
- "AUV", "autonomous underwater vehicle", "AUV scout" → `AUV`.
- "ROV", "remotely operated", "inspection-class ROV", "pen-cleaning ROV" → `ROV`.
- "underwater camera", "camera modules/arrays", "optics manufacturer", "camera maker" → `Underwater Camera`.
- A maker can have multiple platforms (e.g. "builds AUVs and ROVs" → [AUV, ROV]).

### Qualified vs excluded (the key judgment — exclude near-misses):
Qualified = the company **builds/OEM-manufactures** at least one target platform. Exclude companies that only sit *adjacent* to the platform, with a controlled reason. **Use the exact exclusion enum from the template** (it differs per task):
- **Distributor / reseller / dealer / sales agent** ("does not manufacture", "imported brands") → `distributor_only` (relationship `distributor`).
- **Service / consulting / operator** ("operates rented ROVs", "analytics dashboard using partner ROV feeds", "no hardware manufacturing") → `service_only` (relationship `service_provider`).
- **Sensor-only vendor** ("sensor-only DO/salinity probes for integration by platform partners") → `sensor_vendor_only` *or* `sensor_only` (copy the template's spelling) (relationship `sensor_vendor`).
- **Research / academic lab** → `research_only` (relationship `research`).
- **Wrong market entirely** → `not_target_market` (only if the template offers it).
- All excluded exhibitors get `crm_action = no_import` and stay visible in the exclusion list.

Critical: a company that makes the *sensor* but not the *platform* is NOT qualified (it's the sensor vendor we are selling FOR, not the OEM target). A company that merely *uses* or *resells* platforms is NOT qualified.

### CRM overlap & action:
Match exhibitor to CRM account by `crm_account_id` (if exhibitor row provides it) or by website/email domain.
- Qualified + already in CRM → `crm_action = update_existing`, set `crm_account_id`.
- Qualified + not in CRM → `crm_action = create_account`, `crm_account_id = null`.
- `existing_crm_overlap_count` / `existing_crm_overlap_account_ids` count only **qualified** leads that have a CRM account; ids sorted ascending.

### Priority tier & opportunity sizing:
Join exhibitor to `meeting_interest` by company_name to get `interest_score` and `requested_demo`.
Default tiering (used when the prompt doesn't override): based on demo request + score:
- **A** = `requested_demo == true` AND `interest_score >= 90`.
- **B** = `requested_demo == true` AND `interest_score >= 80` (and not A).
- **C** = everything else qualified.
If the prompt gives explicit tier thresholds or dollar values, use those verbatim. Typical opportunity sizing: A = 120000, B = 90000, C = 50000 (USD) — but always take the prompt's stated values if given.
`total_estimated_opportunity_usd` = sum of qualified leads' opportunity estimates.

### Ranking (when the template has `rank`):
Order qualified leads by: (1) `requested_demo` true first, (2) `interest_score` descending, (3) broader platform coverage (more platforms first), (4) `company_name` ascending. Assign 1-based contiguous `rank`.

### Counts:
- `platform_coverage_counts` / `platform_counts`: count of qualified leads covering each platform (a multi-platform lead increments each of its platforms).
- `priority_counts`: count of qualified leads per tier A/B/C.
- `qualified_total` / `qualified_lead_count`, `excluded_*_total`/`excluded_count`.

Sort `qualified_exhibitors`/`ranked_leads` per template (company_name asc, or rank asc); `excluded_*` by company_name ascending.

---

## 8. Import-batch hygiene SOP

Endpoints: `/api/import_batches/{batch}/raw_contacts`, `/.../suppression`, `/api/crm/accounts`, `/api/crm/contacts`, `/api/policies`. Campaign code comes from the import_batch record (`campaign_code`).

Process raw rows in this order:

1. **Normalize** every row (Section 1): trimmed-lowercased email, digits-only phone.
2. **Drop unusable** rows = not contactable (no email AND no phone) → removal reason `missing_contact`, action `no_import`.
3. **Dedupe** remaining rows. **Key = normalized email** (fallback to normalized phone when email is empty). Within a duplicate group pick the **winner**:
   - Primary: **latest `captured_at`** (freshest record wins).
   - Tie-break: **lowest `row_id`** (ascending) when timestamps are equal.
   Losers → removal reason `duplicate`. Record `{key, winner_row_id, removed_row_ids}` per group; sort `duplicate_keys` by `key` ascending.
4. **Suppression**: a winner whose normalized email **or** phone matches any suppression-list entry → removal reason `suppressed`, action `suppress`. (Suppression matches on email or phone; reasons like global_opt_out / privacy_request / role_account all suppress.)
5. **CRM match** the survivors by **email domain → account.domain**:
   - Domain matches an existing account → `crm_action = update_existing`; set `existing_account_id`; `existing_contact_id` = that account's matching contact_id if the exact person already exists, else `null`.
   - No account match → `crm_action = create_account`; `existing_account_id = null`, `existing_contact_id = null`.

Outputs:
- `clean_contacts` = the **surviving** rows only (the `create_account` + `update_existing` set). Each item uses the **winner row's** values: `clean_contact_id` = `source_row_id` = winning row_id; company_name, contact_name, normalized email, normalized phone, `source_name`, `captured_at` (winner's), `crm_action`, `existing_account_id`, `existing_contact_id`. Sort by `clean_contact_id` ascending.
- `duplicate_summary`: `duplicate_removed_count` = total duplicate losers; `duplicate_keys` as above.
- `removal_summary`: `unusable_removed_count` = missing_contact count; `suppressed_removed_count`; `removed_rows` = every removed row `{row_id, reason}` with reason ∈ {duplicate, missing_contact, suppressed}, sorted by `row_id` ascending.
- `import_action_totals`: integer counts over the **deduped** rows (winners + suppressed + unusable, i.e. excluding duplicate losers) for `create_account`, `update_existing`, `no_import` (missing_contact rows), `suppress`.
- `campaign_member_import_count` = number of surviving cleaned contacts (the clean_contacts list length).

---

## 9. Common misjudgments to avoid

- **Don't add or rename keys/enums.** Copy the template's exact enum spellings (e.g. `sensor_vendor_only` vs `sensor_only`; presence/absence of `not_sponsor`).
- **Canceled sponsors are not active sponsors.** Either `not_sponsor` or excluded (`inactive_sponsor_record`) depending on the enum — never `proposal_only`.
- **Open-invoice total uses full package `amount`; the balance is a separate field** (amount − paid_amount). Don't put the balance in the revenue total.
- **Proposal-stage accounts are on the sponsor track**, so their attendees are `sponsor_attendee`, not qualified leads.
- **Match companies by domain, not display name** (manufacturing/Mfg., punctuation, suffixes vary).
- **Sensor-only and platform-using companies are NOT qualified prospects** — they are near-miss exclusions.
- **Use `end_date` (not start_date)** for all follow-up date arithmetic; add the event's own day-offset fields.
- **Lead opportunity amount comes from the event** (`lead_opportunity_amount`), not from CRM opportunity rows; CRM `opportunities` are usually for sponsor/closed deals, not the new leads.
- **Dedup winner = latest captured_at, tie-break lowest row_id.** A duplicate with an identical timestamp is the signal to use the row_id tie-breaker.
- **Suppression and missing-contact rows are removed, not in clean_contacts**, but still counted in `import_action_totals` and listed in `removal_summary`.
- **Contactable = email OR phone.** An empty email alone does not disqualify a row that has a phone.
- **Respect every `ordering` rule**; ties on the primary sort key fall back to the secondary key named in the template.
- Output **JSON only**, integers for all amounts/counts, dates as `YYYY-MM-DD`.
