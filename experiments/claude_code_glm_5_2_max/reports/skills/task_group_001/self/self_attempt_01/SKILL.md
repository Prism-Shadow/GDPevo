# HarborCRM CRM-Marketing Task Skill

Self-contained playbook for solving HarborCRM post-event / prospecting / import tasks.
A solver needs only this document + the task prompt (which names an `event_id`,
`show_id`, or `batch_id`) + the remote API base URL.

## 1. Environment & API

- Base URL (read-only): `<remote-env-url>`
- All endpoints return JSON. Dataset is deterministic (seed 41001). Use `curl -s <url> | python3 -m json.tool`.
- NEVER call any judge/POST/scoring endpoint. Only the public GET endpoints below.

### Endpoints (and what they give you)

| Endpoint | Purpose |
|---|---|
| `GET /health` | Dataset counts (sanity check). |
| `GET /api/policies` | Authoritative enums: sponsor status, platform enums, prospecting/sponsor notes. |
| `GET /api/events` | All events (each carries follow-up day counts + lead opportunity amount). |
| `GET /api/events/{event_id}` | Single event detail. |
| `GET /api/events/{event_id}/orders` | Sponsor orders (account, package_level, order_status, amount, ticket_contacts). |
| `GET /api/events/{event_id}/badges` | Badge scans (badge_type, company, contact, email, phone, scan_score, source). |
| `GET /api/events/{event_id}/sponsor_packages` | Same shape as orders (mirror). |
| `GET /api/finance/invoices?event_id={event_id}` | Invoices (status, amount, paid_amount, deferred_amount, payment_date). |
| `GET /api/crm/accounts` | CRM accounts (account_id, name, domain, industry, status, disqualified_reason). |
| `GET /api/crm/contacts` | CRM contacts (contact_id, account_id, name, email, phone, opted_out). |
| `GET /api/crm/opportunities` | CRM opportunities (account_id, event_id, amount, stage). |
| `GET /api/crm/campaign_members?event_id={event_id}` | Existing campaign members (account_id, contact_id, status, last_activity_date). |
| `GET /api/tradeshows` | Trade shows (show_id, name, country, dates, theme). |
| `GET /api/tradeshows/{show_id}/exhibitors` | Exhibitors (company_id, company_name, booth, country, website, crm_account_id, description). |
| `GET /api/tradeshows/{show_id}/meeting_interest` | Meeting interest (company_name, interest_score, requested_demo, notes). |
| `GET /api/import_batches` | Import batches (batch_id, campaign_code, name). |
| `GET /api/import_batches/{batch_id}/raw_contacts` | Raw import rows (row_id, company_name, contact_name, email, phone, source_name, captured_at). |
| `GET /api/import_batches/{batch_id}/suppression` | Suppression list (email, phone, reason). |

### Key per-record fields to remember

- **Event**: `end_date`, `followup_days_after_end`, `sponsor_followup_days_after_end`, `lead_opportunity_amount`, `campaign_code`.
- **Order / sponsor_package**: `order_status` ∈ {`confirmed`, `proposal_sent`, `canceled`}; `amount`; `ticket_contacts[]`; `account_id`; `account_name`.
- **Invoice**: `status` ∈ {`paid_deferred`, `open`}; `amount`; `paid_amount`; `deferred_amount`; `invoice_id`; `payment_date`.
- **Badge**: `badge_type` ∈ {`sponsor`, `attendee`, `student`, `press`}; `company_name`; `contact_name`; `email`; `phone`; `scan_score`.
- **CRM account**: `status` ∈ {`customer`, `prospect`, `disqualified`}; `disqualified_reason` (null or string); `domain`.
- **CRM contact**: `opted_out` bool.
- **Campaign member**: `status` ∈ {`attended_sponsor`, `registered_sponsor`, `attended`, ...}.
- **Exhibitor**: `crm_account_id` (null if not in CRM); `description` (used to judge platforms).
- **Meeting interest**: `requested_demo` bool; `interest_score` int.

## 2. Cross-cutting normalization rules (apply everywhere)

### Email normalization
- Lowercase, then trim leading/trailing whitespace. ` Dana.Ruiz@HelioWare.example ` → `dana.ruiz@helioware.example`.
- Treat whitespace-only / empty as empty string `""`.

### Phone normalization
- Keep digits only (strip `+`, parens, spaces, dashes, dots). `+1 (415) 555-0101` → `14155550101`; `415-555-0188` → `4155550188`; `1.206.555.0177` → `12065550177`.
- Note: a 10-digit local number and the same number with a leading `1` do **not** normalize equal — dedup/suppression matching is on the exact digit string. Email is the primary identity key; phone is secondary.

### Name / company / domain
- Company-to-account matching: prefer the **email domain** matched against `crm/accounts.domain`; fall back to exact company-name match. Fuzzy/abbreviated names (e.g. "Mfg.") must NOT be trusted — use the domain.
- Existing-contact matching: match normalized email to `crm/contacts.email`.

## 3. Task archetypes

Every task is one of three archetypes. Identify it from the prompt + answer template.

### Archetype A — Event post-event CRM handoff / reconciliation
Prompts name an `event_id` and ask for sponsor statuses, qualified lead accounts, exclusions, follow-up dates, CRM action counts. (Covers the "Summit NeuralOps" and "EdgeAI Field Day" style tasks.)

### Archetype B — Trade-show exhibitor prospecting
Prompts name a `show_id` and a campaign; ask for qualified exhibitors / ranked leads with platform coverage, priority tiers, opportunity sizing, and excluded exhibitors.

### Archetype C — Import batch cleaning
Prompts name a `batch_id`; ask for cleaned contacts, removed rows, duplicate summary, suppression handling, import action totals, and a campaign-member import count.

---

## 4. Archetype A — Event handoff/reconciliation

### 4.1 Sponsor status classification

Build the sponsor picture by joining `orders` (or `sponsor_packages`) with `invoices` for the event, keyed by `account_id`.

**Active sponsors** (appear in the sponsor status list) = orders whose `order_status` is `confirmed` or `proposal_sent`. **Canceled** orders are NOT active sponsors.

For each active sponsor, classify using its invoice:

| order_status | invoice present | invoice status | → sponsor_status |
|---|---|---|---|
| confirmed | yes | `paid_deferred` | `paid_deferred` |
| confirmed | yes | `open` | `open_invoice` |
| confirmed | no | — | `open_invoice` (treat as uninvoiced/open) |
| proposal_sent | no | — | `proposal_only` |
| canceled | — | — | excluded (see 4.3 inactive_sponsor_record) |

Per-sponsor finance fields:
- `package_amount` = order `amount`.
- `paid_amount` = invoice `paid_amount` (0 if no invoice).
- `open_balance` = `package_amount` − `paid_amount` (0 for proposal_only / fully paid).
- `invoice_id` = invoice `invoice_id` or `null` (null for proposal_only).

**Sponsor revenue totals** (integer USD):
- `paid_deferred` total = Σ `package_amount` over paid_deferred sponsors.
- `open_invoice` total = Σ `package_amount` over open_invoice sponsors.
- `proposal_only` total = Σ `package_amount` over proposal_only sponsors.
- `open_invoice_balance` = Σ `open_balance` over open_invoice sponsors (the still-unpaid portion).

> Rationale: "revenue by status" = contracted sponsor value (`package_amount`) per bucket; the unpaid balance is reported separately via `open_invoice_balance`. For paid_deferred, `paid_amount` == `package_amount` here, so the choice does not change the number.

If the task's sponsor_status enum also allows `not_sponsor` (reconciliation-style tasks), use it for accounts that appear in the reconciliation but have **no active sponsor order** (e.g. a canceled sponsor that the schema keeps listed rather than excluding). `amount_usd` for `not_sponsor` = 0.

### 4.2 Qualified non-sponsor lead accounts (from badges)

Process every badge for the event. A badge becomes a **qualified non-sponsor lead** only if ALL of these hold (checked in this precedence order; the first matching rule decides its fate):

1. **Non-business badge** → EXCLUDE, reason `non_business_badge`. Non-business = `badge_type` ∈ {`student`, `press`}. (Business = `attendee`, `sponsor`.)
2. **Sponsor attendee (active sponsor)** → EXCLUDE, reason `sponsor_attendee`. The badge's company is an **active sponsor** (confirmed order) AND the contact is in that sponsor's `ticket_contacts`, **or** `badge_type == sponsor`. These belong to the sponsor workflow, not the lead handoff.
3. **Inactive/canceled sponsor record** → EXCLUDE, reason `inactive_sponsor_record`. The badge's company has a **canceled** sponsor order (the contact is typically in its `ticket_contacts`). This takes precedence over the disqualified-account check, because the sponsor relationship is the primary signal.
4. **Existing disqualified CRM account** → EXCLUDE, reason `existing_disqualified`. The badge's company matches a CRM account with `status == disqualified` (and is not a sponsor). Match by email domain → `crm/accounts.domain`, else exact company name.
5. **Missing contact** (reconciliation tasks only) → EXCLUDE, reason `missing_contact`. Missing = **both** normalized email and normalized phone are blank. A badge with only a phone (no email) OR only an email (no phone) is still a valid lead — see badge-only contacts below.
6. Otherwise → **qualified non-sponsor lead**.

For each qualified lead:
- `opportunity_amount` = the event's `lead_opportunity_amount` (one per qualified lead account).
- `primary_contact` = badge `contact_name`.
- `normalized_email` / `normalized_phone` = normalized badge email/phone (blank string allowed when absent).
- `crm_account_action`: `update_existing` if the company matches an existing non-disqualified CRM account (by domain/name); else `create_account`.
- `crm_contact_action`: `update_existing` if the normalized email matches an existing CRM contact; else `create_contact`. (Typically leads are new contacts → `create_contact`.)
- `campaign_member_action`: `add_campaign_member` (qualified leads are not yet campaign members; if one already is, it would be an update — but qualified leads that are already members are rare).
- `account_id` = matched CRM `account_id` or `null`.

**Lead pipeline total** = Σ `opportunity_amount` over qualified lead accounts.

### 4.3 Excluded records
List the excluded badges (one row each). Fields: `company_name`, `contact_name`, `reason` ∈ {`sponsor_attendee`, `existing_disqualified`, `inactive_sponsor_record`, `non_business_badge`}. (Reconciliation tasks use `missing_contact` instead of `inactive_sponsor_record` and add it to the exclusion-counts map.) Sort by `company_name` asc, then `contact_name` asc.

### 4.4 Follow-up due dates (authoritative arithmetic from the event record)

- `lead_due_date` / `lead_followup_due_date` = `event.end_date` + `event.followup_days_after_end` calendar days → `YYYY-MM-DD`.
- `sponsor_finance_due_date` / `sponsor_followup_due_date` = `event.end_date` + `event.sponsor_followup_days_after_end` calendar days → `YYYY-MM-DD`.

Plain calendar addition (do not skip weekends). Example shape: end date `YYYY-MM-DD` + N days → the date N calendar days later (e.g. `...09-16` + 7 → `...09-23`). Always read `end_date` and the two day-count fields from the event record for the task's `event_id` — never assume a constant.

### 4.5 Sponsor finance follow-up (the "unpaid" targets)

Finance follow-up is about **collecting outstanding money**, so the targets are sponsors with an unpaid invoice balance:
- Targets = sponsors whose status is `open_invoice` AND `open_balance > 0`.
- `proposal_only` sponsors (no invoice yet) are NOT finance-follow-up targets — that is a sales/proposal matter, not a finance/collection matter.
- `paid_deferred` sponsors are paid in full → not targets.
- `sponsor_finance_task_count` / `unpaid_sponsor` count = number of target sponsors.
- `unpaid_sponsor_total_usd` = Σ `open_balance` of target sponsors (= the `open_invoice_balance` total).
- `sponsor_finance_accounts` / `unpaid_sponsor_account_names` = target account names, sorted ascending.
- `lead_task_count` = number of qualified lead accounts (one task per qualified lead).

### 4.6 CRM action counts (event handoff tasks)

Count the work implied by the **qualified lead handoff** (not sponsor attendees):
- `accounts_create` = # qualified leads with `crm_account_action == create_account`.
- `accounts_update` = # qualified leads with `crm_account_action == update_existing`.
- `contacts_create` = # qualified leads with `crm_contact_action == create_contact`.
- `contacts_update` = # qualified leads with `crm_contact_action == update_existing`.
- `campaign_members_create` = # qualified leads that are new campaign members.
- `campaign_members_update` = # qualified leads that already were campaign members (usually 0).

### 4.7 Reconciliation-task extras (badge decisions, campaign-member actions)

Some event tasks ask for a fuller reconciliation. Additional conventions:

**badge_decisions** (one per badge, sort by `badge_id` asc): `classification` ∈ {`sponsor_attendee`, `qualified_non_sponsor_lead`, `excluded`}; `exclusion_reason` ∈ {`sponsor_attendee`, `non_business_badge`, `existing_disqualified`, `missing_contact`, null}; `crm_action` per below.
- `crm_action` choices: `create_account_contact_campaign_member` (account + contact + member all new), `create_contact_campaign_member` (account exists, contact + member new), `add_campaign_member` (account + contact exist, member new), `update_campaign_member` (member exists, status changes), `no_action` (already correct), `no_import` (excluded).
- Decide by: does the account exist in CRM? does the contact exist? does the campaign member exist? Build the most specific action.

**campaign_member_actions** (reconcile existing members + badge-derived needs; sort by `subject_key` asc): `action` ∈ {`create`, `update`, `no_action`, `no_import`}; `target_status` ∈ {`attended_sponsor`, `registered_sponsor`, `attended`, `excluded`}.
- `subject_key` = a stable unique key per subject: use the CRM `contact_id` for existing contacts; otherwise normalized email; otherwise `account_name|contact_name`.
- Sponsor's ticket-contact WITH a badge (attended) → `attended_sponsor`. Sponsor's ticket-contact with NO badge (registered only) → `registered_sponsor`.
- Qualified non-sponsor lead WITH a badge → `attended`.
- Existing member already at the right status → `no_action`.
- Excluded badge (non-business / missing) → `no_import`, `excluded`.

**badge_only_contacts**: the qualified non-sponsor badge leads that are NOT yet in CRM (need contact import). Fields `company_name`, `contact_name`, `normalized_email` (lowercase trimmed, `""` allowed), `normalized_phone` (digits only, `""` allowed). Sort by `company_name` asc. A phone-only or email-only lead is valid here.

**opportunity_summary** (reconciliation): `qualified_non_sponsor_account_names` (asc); `lead_opportunity_amount_usd` = `event.lead_opportunity_amount` × (# qualified non-sponsor leads) [total new pipeline]; `open_opportunity_total_usd` / `open_opportunity_count` = Σ / count of **existing** CRM opportunities tied to the event (or to the qualified accounts) whose `stage` is open (i.e. not `closed_won`) — typically 0 for fresh badge leads.

**exclusion_counts**: integer counts per reason (`sponsor_attendee`, `non_business_badge`, `existing_disqualified`, `missing_contact`). A sponsor-attendee badge counts toward `sponsor_attendee`.

---

## 5. Archetype B — Trade-show exhibitor prospecting

### 5.1 Judging platforms from the description

Platform enums (authoritative, in this order): `AUV`, `ROV`, `Underwater Camera`.

An exhibitor **qualifies** if it **makes or OEM-builds** one or more of these target platforms. Decide from `description` + company context:
- "Builds AUVs / autonomous AUV scouts" → `AUV`.
- "Builds ROVs / inspection-class ROVs / pen-cleaning ROVs" → `ROV`.
- "Designs underwater camera modules / OEM underwater camera manufacturer" → `Underwater Camera`.
- A company that builds e.g. "ROVs **with** camera arrays" → `ROV` only (the camera is a component of the ROV, not a standalone camera platform). Only assign a platform when the company manufactures that platform as a product line.
- A company that explicitly builds two platform lines ("Builds AUVs and ROVs") → `[AUV, ROV]`.

Always emit `platforms` sorted in enum order: `AUV`, `ROV`, `Underwater Camera`.

### 5.2 Excluded exhibitors (adjacent / not-target)

Exhibitors that do NOT build a target platform are excluded with a relationship type → reason:

| relationship_type | description signals | exclusion_reason (full-list tasks) | exclusion_reason (ranked-lead tasks) |
|---|---|---|---|
| `distributor` | reseller / sales agent / "does not manufacture" / imported brands | `distributor_only` | `distributor_only` |
| `service_provider` | consulting / operates rented platforms / analytics dashboard / no hardware mfg | `service_only` | `service_only` |
| `sensor_vendor` | sensor-only probes / sensors for integration, no platform | `sensor_vendor_only` | `sensor_only` |
| `research` | research lab / academic | `research_only` | `research_only` |
| (none of the above, just off-target) | doesn't fit target market | `not_target_market` | — |

**Watch the enum per task**: some tasks use `sensor_vendor_only` + `not_target_market`; others use `sensor_only` with no `not_target_market`. Read the answer template's allowed values and use that task's exact strings. `crm_action` for excluded = `no_import`.

### 5.3 Priority tier & opportunity sizing (apply to all prospecting tasks)

Priority is driven by **meeting interest** (join exhibitor ↔ meeting_interest by `company_name`):

- **Tier A**: `requested_demo == true` AND `interest_score >= 90`.
- **Tier B**: `requested_demo == true` AND `80 <= interest_score < 90`.
- **Tier C**: everything else (no demo, or demo with `interest_score < 80`, or no meeting-interest record at all → treat as `requested_demo=false`, `interest_score=0`).

Opportunity sizing by tier (fixed policy constants, integer USD):
- A = `120000`, B = `90000`, C = `50000`.

### 5.4 CRM overlap (ranked-lead tasks)

- If the exhibitor has a non-null `crm_account_id` → `crm_action = update_existing`, and it counts toward `existing_crm_overlap`.
- If `crm_account_id` is null → `crm_action = create_account`.
- `existing_crm_overlap_count` = # **qualified** leads with a CRM account; `existing_crm_overlap_account_ids` = their `account_id`s sorted ascending.
- `total_estimated_opportunity_usd` = Σ opportunity estimates over qualified leads.

### 5.5 Ranking (ranked-lead tasks)

Sort qualified leads by, in order:
1. `requested_demo` = true first (demo-requesters ahead of non-demo).
2. `interest_score` descending.
3. Broader platform coverage first = more platforms ahead (descending count of platforms).
4. `company_name` ascending.

Assign `rank` 1-based contiguous. Emit `platforms` in enum order.

### 5.6 Aggregate counts

- `qualified_total` / `qualified_lead_count` = # qualified.
- `platform_counts` / `platform_coverage_counts` = for each platform enum, # **qualified** leads that have that platform.
- `priority_counts` = for each tier A/B/C, # qualified leads at that tier.
- `excluded_near_misses_total` / `excluded_count` = # excluded exhibitors.

Sort `qualified_exhibitors` / `ranked_leads` per the task's ordering rule (company_name asc, or rank asc). Sort excluded lists by `company_name` asc.

---

## 6. Archetype C — Import batch cleaning

### 6.1 Pipeline (order matters)

For each `raw_contact` row, normalize email + phone first. Then apply removals in this precedence:

1. **missing_contact** — if normalized email is blank AND normalized phone is blank (no usable contact channel). → remove, reason `missing_contact`, `crm_action = no_import`. (Do this before suppression so a blank phone can't spuriously match a suppression entry whose phone is blank.)
2. **suppressed** — if the row's normalized email OR normalized phone matches any suppression entry's `email`/`phone` (skip blank values when matching, so empty never matches empty). → remove, reason `suppressed`, `crm_action = suppress`.
3. **duplicate** — among the remaining rows, group by normalized email (primary key). Within each group keep one **winner**, remove the rest, reason `duplicate`. (Rows with a blank email are not grouped/deduped by email — they survive individually unless caught above.)

### 6.2 Duplicate winner selection

- Winner = the row with the **earliest** `captured_at` (first capture wins).
- Tie-break: lowest `row_id` (lexicographic/string order).
- `clean_contact_id` and `source_row_id` both = the winner's `row_id`. `captured_at` = the winner's timestamp. Company/contact/email/phone = the **winner's** normalized values.

### 6.3 Duplicate summary

`duplicate_keys` (sorted by `key` asc): one entry per duplicate group with `key` = normalized email, `winner_row_id`, `removed_row_ids` (sorted). `duplicate_removed_count` = total rows removed as duplicates.

### 6.4 Removal summary

`removed_rows` (sorted by `row_id` asc): every removed row with `row_id` + `reason` ∈ {`duplicate`, `missing_contact`, `suppressed`}.
- `unusable_removed_count` = # `missing_contact` rows.
- `suppressed_removed_count` = # `suppressed` rows.

### 6.5 Clean contacts & CRM action

Surviving clean contacts (sorted by `clean_contact_id` = winner `row_id` asc). For each, decide `crm_action` ∈ {`create_account`, `update_existing`, `no_import`, `suppress`}:
- Match the contact's company to CRM: by email domain → `crm/accounts.domain`, else exact company name.
- If a non-disqualified CRM account matches → `update_existing` (account exists; contact may still be new). `existing_account_id` = the account_id.
- If no CRM account matches → `create_account`. `existing_account_id = null`.
- `existing_contact_id` = matched CRM contact_id by normalized email, else null. (A new contact on an existing account still → `update_existing` at the account level with `existing_contact_id = null`.)
- `email` = normalized email or `""`; `phone` = normalized digits-only phone or `""`.

### 6.6 Import action totals & campaign-member count

`import_action_totals`: count clean contacts by `crm_action` (`create_account`, `update_existing`) plus removed rows (`no_import` = missing_contact count, `suppress` = suppressed count). Duplicate-removed rows are NOT counted here (they have no action — only the winner acts). So `create_account + update_existing + no_import + suppress` = (#clean) + (#missing) + (#suppressed); duplicates excluded.

`campaign_member_import_count` = # surviving clean contacts (each becomes a member of the batch's campaign, `campaign_code` from `import_batches`).

`batch_id` = the batch id; `campaign_code` = the batch's campaign code.

---

## 7. Sorting rules (quick reference)

| List | Sort by |
|---|---|
| sponsor_statuses | `account_name` asc |
| qualified_lead_accounts | `account_name` asc |
| excluded_records | `company_name` asc, then `contact_name` asc |
| qualified_exhibitors | `company_name` asc |
| excluded_near_misses / excluded_exhibitors | `company_name` asc |
| ranked_leads | `rank` asc (1-based) |
| badge_decisions | `badge_id` asc |
| campaign_member_actions | `subject_key` asc |
| badge_only_contacts | `company_name` asc |
| clean_contacts | `clean_contact_id` asc |
| duplicate_summary.duplicate_keys | `key` asc |
| removal_summary.removed_rows | `row_id` asc |
| existing_crm_overlap_account_ids | account id asc |
| qualified_non_sponsor_account_names / unpaid_sponsor_account_names | string asc |

## 8. Output discipline

- Return ONE JSON object only, matching the provided answer template's keys exactly.
- Do not add fields not in the template; do not emit prose outside the JSON.
- All money = integer USD. All counts = integers. All dates = `YYYY-MM-DD`.
- Use the template's exact enum strings (they vary between tasks — e.g. `sensor_vendor_only` vs `sensor_only`, presence of `not_target_market`/`not_sponsor`/`missing_contact`). Always re-read the template's allowed values for the task at hand and use those.

## 9. Cross-task consistency checks

When self-checking, verify the same convention is applied everywhere:
- A canceled sponsor is excluded (Archetype A) and is NEVER a qualified lead, never in sponsor revenue totals.
- `paid_deferred` ⇒ `paid_amount == package_amount` ⇒ `open_balance == 0` ⇒ not a finance follow-up target.
- `open_invoice` ⇒ `open_balance = package_amount − paid_amount > 0` ⇒ IS a finance follow-up target; its `package_amount` is in the `open_invoice` revenue total and its `open_balance` is in `open_invoice_balance`.
- `proposal_only` ⇒ no invoice ⇒ `open_balance == 0` ⇒ not a finance follow-up target; its `package_amount` is in the `proposal_only` revenue total.
- Follow-up due dates derive ONLY from the event record's `end_date` + the two `*_followup_days_after_end` fields — never guess.
- Priority/opportunity constants (tiers 90/80, USD 120000/90000/50000) are policy-level and identical across all prospecting tasks.
- Email is the identity/dedup key; phone is match-only on the exact digit string; normalization is lowercase+trim for email and digits-only for phone in every archetype.
