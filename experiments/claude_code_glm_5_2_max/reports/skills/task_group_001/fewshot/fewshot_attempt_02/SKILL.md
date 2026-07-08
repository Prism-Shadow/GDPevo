# HarborCRM CRM-Marketing Task Skill

A transferable playbook for solving unseen HarborCRM tasks. HarborCRM is a shared
read-only CRM-marketing dataset exposed over a small JSON API. Tasks always end
with **one JSON object** conforming to a per-task `answer_template.json`.

The dataset seeds three task families. Identify which family a task belongs to,
then apply the matching rules below.

| Family | Trigger in prompt | Train pattern |
|---|---|---|
| **A. Event sponsor / lead handoff** | "event_id", "post-event", "reconcile", sponsor orders + badges + invoices | train_001 (simple), train_004 (detailed) |
| **B. Trade-show prospecting** | "show_id", "exhibitors", "meeting_interest", "campaign" | train_002 (simple), train_005 (ranked) |
| **C. Contact-import cleaning** | "import batch", "raw_contacts", "suppression", "clean" | train_003 |

---

## 0. Environment & data access

- Base URL is given to you by the runner; if absent, use the documented default.
  Only call the public GET endpoints. Never POST / call judge endpoints.
- Endpoints (all return JSON, deterministic dataset):
  - `GET /api/events`, `/api/events/{id}`, `/api/events/{id}/orders`,
    `/api/events/{id}/badges`, `/api/events/{id}/sponsor_packages`
  - `GET /api/finance/invoices?event_id={id}`
  - `GET /api/crm/accounts`, `/api/crm/contacts`, `/api/crm/opportunities`,
    `/api/crm/campaign_members?event_id={id}`
  - `GET /api/tradeshows`, `/api/tradeshows/{id}/exhibitors`,
    `/api/tradeshows/{id}/meeting_interest`
  - `GET /api/import_batches`, `/api/import_batches/{id}/raw_contacts`,
    `/api/import_batches/{id}/suppression`
  - `GET /api/policies`
- `/api/events/{id}/orders` and `/api/events/{id}/sponsor_packages` return the
  **same** sponsor-order records; either works.
- Always read `/api/policies` first — it carries the controlled enums
  (sponsor status, platform enums) and the qualification note.

**Workflow for every task:**
1. Read the prompt → family + the exact ids (event_id / show_id / batch_id).
2. Read `/api/policies` for enums.
3. Fetch every endpoint the prompt names (and the cross-cutting CRM endpoints).
   Do not skip CRM/accounts or contacts even if not explicitly listed — you need
   them for create-vs-update decisions and disqualified-account exclusions.
4. Build the answer with the conventions below; respect the template's exact
   key names, enums, ordering, and null rules.
5. Output **one JSON object only**, no prose.

---

## 1. Universal conventions

### Email normalization
- Trim surrounding whitespace, then lowercase.
- Empty / whitespace-only → `""` (empty string).
- Used for: duplicate keys, CRM contact matching, suppression matching,
  qualified-lead `normalized_email`, badge-only contact facts.

### Phone normalization
- Strip every non-digit character; keep the country code (e.g. `+1 (415) 555-0188` → `14155550188`, `1.206.555.0177` → `12065550177`, `206.555.0150` → `2065550150`).
- Empty / whitespace-only → `""`.
- Do NOT reformat, add dashes, or strip a leading `1`.

### Currency
- All money is integer USD. No decimals, no currency symbol, no commas.

### Dates
- All dates are `YYYY-MM-DD` strings.
- Follow-up dates are **calendar-day addition** to the event `end_date`:
  - `lead_followup_due_date = end_date + followup_days_after_end`
  - `sponsor_followup_due_date = end_date + sponsor_followup_days_after_end`
  - Both `followup_days_after_end` and `sponsor_followup_days_after_end` are
    fields on the event record. Use `end_date` (not start_date), even for
    single-day events where start == end.

### Sorting (apply exactly as the template states — order matters for scoring)
- Strings ascending = lexicographic (case-sensitive; these datasets use consistent casing).
- Always sort the final list; do not rely on API order.
- When a template says "sort by X ascending, then Y ascending", apply both keys.

### Output discipline
- Return only keys declared in the template. No extra fields, no prose.
- Use the exact enum strings. `null` only where the template allows null.
- Empty string `""` is not the same as `null` — follow each field's rule.

---

## 2. Family A — Event sponsor / lead handoff

Two schema variants exist; both share the same engine.

- **Simple variant** (train_001-like): `sponsor_statuses`, `sponsor_revenue_totals`,
  `qualified_lead_accounts`, `lead_pipeline_total`, `excluded_records`,
  `follow_up`, `crm_action_counts`.
- **Detailed variant** (train_004-like): `event`, `sponsor_statuses`,
  `badge_decisions`, `campaign_member_actions`, `opportunity_summary`,
  `sponsor_followup`, `badge_only_contacts`, `exclusion_counts`.

The classification logic below is identical across variants; only the output
shape differs.

### 2.1 Sponsor status classification

Compute per sponsor order on the event. **Active sponsors** = orders whose
`order_status` is `confirmed` or `proposal_sent`. Inactive orders
(`canceled`, `no_show`, etc.) are **not** sponsor statuses — their people are
handled via exclusions (§2.4).

For each active sponsor, aggregate **all** its invoices for the event (a sponsor
may have more than one):

| Condition | `sponsor_status` |
|---|---|
| No invoice at all (e.g. `proposal_sent`) | `proposal_only` |
| Has invoices, and total open balance > 0 (any unpaid amount) | `open_invoice` |
| Has invoices, fully paid (open balance == 0) | `paid_deferred` |

Where `open_balance = sum(invoice.amount) - sum(invoice.paid_amount)` across the
sponsor's invoices. `package_amount` = the sponsor **order** `amount`.
`paid_amount` = sum of `paid_amount` across invoices. For `proposal_only`,
`invoice_id = null`, `paid_amount = 0`, `open_balance = 0`.

- For `open_invoice` with multiple invoices, report the **open** invoice's id as
  `invoice_id`. For a single-invoice sponsor, report that invoice's id.
- A sponsor with one `paid_deferred` invoice plus one `open` invoice is
  `open_invoice` (any unpaid balance wins). A sponsor whose invoices are all
  fully paid is `paid_deferred`.

`sponsor_statuses` is sorted by `account_name` ascending.

### 2.2 Sponsor revenue rollup (simple variant)

`sponsor_revenue_totals` (integer USD):
- `paid_deferred` = sum of `package_amount` over sponsors with status `paid_deferred`.
- `open_invoice` = sum of `package_amount` over `open_invoice` sponsors.
- `proposal_only` = sum of `package_amount` over `proposal_only` sponsors.
- `open_invoice_balance` = sum of `open_balance` over `open_invoice` sponsors
  (i.e. total still-owed, not the package amounts).

### 2.3 Qualified non-sponsor leads

From the event's **badge scans**, a badge becomes a qualified lead when ALL hold:
1. `badge_type` is a business type (`attendee`; also treat `sponsor`-typed
   badges whose company is an active sponsor as sponsor attendees, not leads).
2. The badge's company is **not** an active sponsor (no confirmed/proposal_sent
   order for that company).
3. The company is **not** a disqualified CRM account.
4. It is not a non-business badge (see exclusions).
5. It has usable contact info (a contact name; treat no-name / no-email-and-no-phone as missing).

Each qualified lead is sized at the event's `lead_opportunity_amount` (integer
USD, from the event record). Pipeline/opportunity totals = `lead_opportunity_amount` ×
(number of qualified leads).

- `lead_pipeline_total` (simple) = that product.
- `opportunity_summary.open_opportunity_total_usd` (detailed) = that product;
  `open_opportunity_count` = number of qualified leads;
  `lead_opportunity_amount_usd` = the per-lead amount;
  `qualified_non_sponsor_account_names` = sorted ascending.

### 2.4 Exclusions (precedence top-down)

Evaluate each badge/contact in this order; the first match wins:

| # | Condition | Exclusion reason |
|---|---|---|
| 1 | Company is an **active sponsor** (confirmed/proposal_sent order) | `sponsor_attendee` |
| 2 | Company matches a CRM account with `status == "disqualified"` | `existing_disqualified` |
| 3 | `badge_type` is non-business (`student`, `press`, `academic`, etc.) | `non_business_badge` |
| 4 | Company has an **inactive** sponsor order (`canceled`/`no_show`) and is not disqualified | `inactive_sponsor_record` |
| 5 | No contact name, or no email AND no phone | `missing_contact` |

Notes:
- A disqualified-account check (rule 2) beats inactive-sponsor (rule 4): a
  canceled sponsor whose CRM account is disqualified is `existing_disqualified`.
- The sponsor-attendee set (rule 1) is sourced from the sponsor **order
  `ticket_contacts`** (the primary/first ticket contact per active sponsor) plus
  any badge whose `badge_type == "sponsor"`. Deduplicate by
  (company_name, contact_name). When a sponsor has an existing campaign member,
  that contact is the one used.
- `non_business_badge` = any `badge_type` that isn't a business attendee
  (e.g. `student`, `press`).

`excluded_records` (simple) sorted by `company_name` asc, then `contact_name`
asc. `exclusion_counts` (detailed) counts badges per reason among
`sponsor_attendee`, `non_business_badge`, `existing_disqualified`,
`missing_contact`.

### 2.5 CRM create/update decisions (qualified leads)

Match each qualified lead to CRM:
- **Account**: match the lead's email domain to `accounts[].domain`.
  - Match found → `crm_account_action = "update_existing"`, `account_id` = that id.
  - No match → `crm_account_action = "create_account"`, `account_id = null`.
- **Contact**: match the lead's normalized email to `contacts[].email`.
  - Match found → `crm_contact_action = "update_existing"`, contact exists.
  - No match → `crm_contact_action = "create_contact"` (even if the account
    exists; a lead contact is usually new).
- **Campaign member**: qualified leads are new campaign members →
  `add_campaign_member` / `create`.

Simple variant `crm_action_counts`:
- `accounts_create` / `accounts_update` = counts of qualified leads by account action.
- `contacts_create` / `contacts_update` = counts by contact action.
- `campaign_members_create` = number of qualified leads (all new);
  `campaign_members_update` = 0 (unless a lead already had a CM, which is rare).

### 2.6 Badge decisions & campaign-member actions (detailed variant)

`badge_decisions` — one row per badge, sorted by `badge_id` ascending. Fields:
`badge_id, company_name, contact_name, classification, crm_action, exclusion_reason`.

`classification` ∈ {`sponsor_attendee`, `qualified_non_sponsor_lead`, `excluded`}
per §2.4. `exclusion_reason` is the reason enum or `null` (null for qualified
leads; `sponsor_attendee` for sponsor attendees even though they are not
"excluded" in the lead sense).

`crm_action` (badge-level) — choose by what must be created vs already exists:

| Situation | `crm_action` |
|---|---|
| Qualified lead, no existing account | `create_account_contact_campaign_member` |
| Qualified lead, existing account, no existing contact | `create_contact_campaign_member` |
| Qualified lead, existing account AND contact, no CM | `add_campaign_member` |
| Qualified lead already has a CM | `update_campaign_member` |
| Sponsor attendee with existing contact + existing CM | `no_action` |
| Sponsor attendee, account exists but no contact/CM | `create_contact_campaign_member` |
| Excluded (non-business / disqualified / missing) | `no_import` |

`campaign_member_actions` — sorted by `subject_key` ascending. Two sources:
1. **Existing campaign members** (`/crm/campaign_members?event_id=...`):
   `subject_key = "{account_id}:{contact_id}"`, `action = "no_action"`,
   `target_status` = the existing CM's `status` (e.g. `attended_sponsor`,
   `registered_sponsor`).
2. **New CMs from badges** (qualified leads + sponsor attendees lacking a CM):
   `subject_key = "badge:{badge_id}"`, `action = "create"`.
   - Qualified non-sponsor lead → `target_status = "attended"`.
   - Sponsor attendee (no existing CM) → `target_status = "attended_sponsor"`.
   - Excluded badges (non-business etc.) get **no** campaign-member action.

Note `acct_…:cont_…` sorts before `badge:…` lexicographically.

### 2.7 badge_only_contacts (detailed variant)

Normalized contact facts for badge-scanned people who do **not** already have a
matching CRM contact. Includes qualified leads and sponsor attendees whose
contact must be created. Excludes people who already have a CRM contact and
excluded badges. Sorted by `company_name` ascending. Fields:
`company_name, contact_name, normalized_email, normalized_phone`
(email/phone per §1; empty string `""` when not supplied).

### 2.8 Sponsor finance follow-up

Unpaid sponsors for finance follow-up = sponsors whose status is `open_invoice`
**or** `proposal_only` (i.e. not `paid_deferred`).
- `unpaid_sponsor_account_names` / `sponsor_finance_accounts` = sorted ascending.
- `unpaid_sponsor_total_usd` (detailed) = sum of open balance for `open_invoice`
  sponsors + sum of `package_amount` for `proposal_only` sponsors.
- `sponsor_finance_task_count` (simple) = number of unpaid sponsors.
- `followup_due_date` = `sponsor_followup_due_date` (§1 dates).
- Lead follow-up: `lead_due_date` = `lead_followup_due_date`;
  `lead_task_count` = number of qualified leads.

---

## 3. Family B — Trade-show prospecting

Two schema variants, same engine.

- **Simple** (train_002-like): `qualified_exhibitors` (+ `priority_tier`),
  `excluded_near_misses`, `aggregate_counts`.
- **Ranked** (train_005-like): `summary`, `ranked_leads` (with CRM action,
  demo/score, tier, opportunity), `excluded_exhibitors`.

Platform enums (from policy): `AUV`, `ROV`, `Underwater Camera`.
Always emit platform lists in that enum order.

### 3.1 Qualification (who builds vs who is adjacent)

Per the policy qualification note: use each exhibitor's `description` to decide
whether it **builds / manufactures / OEM-builds** a target platform, or is only
**adjacent** to them.

- **Qualified**: description says it builds/manufactures/designs/OEMs one or more
  of AUV / ROV / Underwater Camera (e.g. "builds compact AUVs and ROVs",
  "designs rugged underwater camera modules", "OEM underwater camera
  manufacturer", "manufactures ROVs with camera arrays").
- **Excluded** (adjacent only), with relationship + reason:

| Relationship | Reason (simple) | relationship_type / reason (ranked) | Description signals |
|---|---|---|---|
| Distributor / reseller / dealer | `distributor_only` | `distributor` / `distributor_only` | "distributor", "sales agent", "reseller", "dealer", "does not manufacture" |
| Service provider / consulting | `service_only` | `service_provider` / `service_only` | "consulting", "operates rented", "analytics dashboard … no hardware manufacturing", "service" |
| Sensor-only vendor | `sensor_vendor_only` | `sensor_vendor` / `sensor_only` | "sensor-only", "probes", "sensor vendor", makes sensors but no platform |
| Research / academic | `research_only` | `research` / `research_only` | research institute / lab |
| Off-theme | `not_target_market` | (not in ranked enum) | doesn't fit campaign theme |

**Mind the per-schema labels**: the simple schema uses
`exclusion_reason ∈ {distributor_only, service_only, sensor_vendor_only,
research_only, not_target_market}`. The ranked schema uses
`relationship_type ∈ {distributor, service_provider, sensor_vendor, research}`
**and** `exclusion_reason ∈ {distributor_only, service_only, sensor_only,
research_only}` (note `sensor_only`, not `sensor_vendor_only`). Always copy the
enum from the task's own template.

### 3.2 Platform assignment

From the qualified exhibitor's description, assign every target platform it
actually builds. Map description terms → enum:
- "AUV" → `AUV`
- "ROV" → `ROV`
- "underwater camera" / "camera module" / "camera array" (when built) → `Underwater Camera`
Sort the list in enum order `AUV, ROV, Underwater Camera`.

### 3.3 Priority tier & opportunity sizing

Tier is computed from the exhibitor's `meeting_interest` record (matched by
`company_name`). If no meeting-interest record exists for a qualified exhibitor,
treat `requested_demo = false` and `interest_score = 0`.

| Tier | Rule | Opportunity (ranked schema) |
|---|---|---|
| `A` | `requested_demo == true` AND `interest_score >= 90` | 120000 |
| `B` | `requested_demo == true` AND `interest_score >= 80` (and < 90) | 90000 |
| `C` | otherwise (no demo, or score < 80) | 50000 |

The simple schema outputs `priority_tier` only (still computed from
meeting-interest, even though `interest_score` is not in the output). The ranked
schema also outputs `requested_demo`, `interest_score`, and
`opportunity_estimate_usd`.

### 3.4 CRM overlap & action (ranked schema)

- A qualified exhibitor with a non-null `crm_account_id` (already in CRM) →
  `crm_action = "update_existing"`, `crm_account_id` echoed.
- A qualified exhibitor with `crm_account_id == null` →
  `crm_action = "create_account"`, `crm_account_id = null`.
- Excluded exhibitors → `crm_action = "no_import"`.

`summary.existing_crm_overlap_count` = number of qualified exhibitors already in
CRM; `existing_crm_overlap_account_ids` = their account ids sorted ascending.
`total_estimated_opportunity_usd` = sum of `opportunity_estimate_usd` over
ranked leads.

### 3.5 Ranking (ranked schema)

`ranked_leads` ordered by `rank` ascending (1-based contiguous). Sort key:
1. `requested_demo` = true before false (demo request first).
2. `interest_score` descending.
3. Broader platform coverage first (more platforms ranks higher).
4. `company_name` ascending.

### 3.6 Ordering for the simple schema

- `qualified_exhibitors` sorted by `company_name` ascending.
- `excluded_near_misses` sorted by `company_name` ascending.
- Ranked schema `excluded_exhibitors` sorted by `company_name` ascending.

### 3.7 Aggregate counts

- `qualified_total` = number of qualified exhibitors.
- `platform_counts` / `platform_coverage_counts`: for each platform enum, how
  many **qualified** exhibitors cover it (an exhibitor covering two platforms
  increments both).
- `priority_counts` (simple): A/B/C counts among qualified.
- `excluded_near_misses_total` / `excluded_count` = number of excluded exhibitors.

### 3.8 Required literal values

- `show_id` and `campaign` (when present) are `required_value`s in the template
  — copy them verbatim from the prompt/template, do not invent.

---

## 4. Family C — Contact-import cleaning

Output: `batch_id`, `campaign_code`, `clean_contacts`, `duplicate_summary`,
`removal_summary`, `import_action_totals`, `campaign_member_import_count`.

- `batch_id` = the batch id from the prompt.
- `campaign_code` = `campaign_code` from `/api/import_batches` metadata for that
  batch.
- `campaign_member_import_count` = number of surviving clean contacts.

### 4.1 Per-row normalization & fate

For each raw contact row, normalize `email` (trim+lowercase) and `phone`
(digits-only). Then classify into exactly one fate, in this precedence:

1. **`missing_contact`** — normalized email is empty AND normalized phone is
   empty (no contact channel at all). A row with a phone but no email (or vice
   versa) is **not** missing.
2. **`suppressed`** — the row's normalized email **or** normalized phone matches
   any entry in the batch's `/suppression` list (match on email if the
   suppression email is non-empty; match on phone if the suppression phone is
   non-empty). Suppression is checked per-row before dedup, so two rows sharing
   a suppressed email are both suppressed.
3. **`duplicate`** — among the remaining rows, group by normalized email
   (non-empty). Within a group of >1, pick one **winner** (§4.2); the rest are
   duplicates.
4. **clean** — the winner of each unique-email group, plus any row with no email
   (phone-only rows can't be email-deduped and survive as clean if not
   suppressed/missing).

Rows removed as duplicate or missing count toward `no_import`; rows removed as
suppressed count toward `suppress`; survivors count toward `create_account` +
`update_existing`.

### 4.2 Duplicate winner selection

Duplicate key format: `"email:{normalized_email}"`.
- **Primary: latest `captured_at` wins** (most recent timestamp).
- **Tie-break: higher source-trust** — `source_name` earlier in the enum
  `[badge_scan, sponsor_form, partner_upload, webinar_form, exhibitor_form,
  manual_upload]` wins. (The enum is a trust ranking, highest first.)
- **Final tie-break: later `row_id`** wins.

The winner's `row_id` becomes both `clean_contact_id` and `source_row_id`; the
winner's `captured_at`, `source_name`, `company_name`, `contact_name`,
normalized email/phone are used in the clean contact.

`duplicate_summary`: `duplicate_removed_count` = total loser rows;
`duplicate_keys` sorted by `key` ascending, each with `key`, `winner_row_id`,
`removed_row_ids` (the loser row_ids of that group).

### 4.3 Clean contact CRM action

For each surviving clean contact:
- Match the contact's email domain to `accounts[].domain`.
  - Match → `crm_action = "update_existing"`, `existing_account_id` = that id.
  - No match → `crm_action = "create_account"`, `existing_account_id = null`.
- Match the contact's normalized email to `contacts[].email`.
  - Match → `existing_contact_id` = that contact id.
  - No match → `existing_contact_id = null`.
- `source_name` is the winner row's `source_name` (enum above).
- `email` / `phone` are the normalized values (empty string `""` if absent).

`import_action_totals`: counts of clean contacts by `crm_action`
(`create_account`, `update_existing`) plus `no_import` (duplicate + missing
rows) plus `suppress` (suppressed rows). These four sum to the raw row count.

### 4.4 Removal summary & ordering

`removal_summary`:
- `unusable_removed_count` = number of `missing_contact` rows only (NOT
  including duplicates).
- `suppressed_removed_count` = number of `suppressed` rows.
- `removed_rows` = **all** removed rows (duplicates + missing + suppressed),
  sorted by `row_id` ascending, each `{row_id, reason}` with
  `reason ∈ {duplicate, missing_contact, suppressed}`.

`clean_contacts` sorted by `clean_contact_id` ascending.

---

## 5. Common pitfalls

- **Don't skip CRM endpoints.** Disqualified-account exclusion, contact
  create-vs-update, and CRM-overlap all need `/api/crm/accounts` and
  `/api/crm/contacts` even when the prompt doesn't list them.
- **Don't forget campaign members.** They drive `no_action` rows in the detailed
  event variant and confirm which sponsor contact is "primary".
- **Multiple invoices per sponsor exist.** Classify by aggregate open balance,
  not by the first invoice.
- **`no_show` / `canceled` orders are not active sponsors.** Exclude them from
  `sponsor_statuses`; route their attendees through the exclusion precedence.
- **Phone keeps the country code.** Just strip non-digits.
- **Empty string vs null.** Normalized email/phone use `""` when absent;
  `account_id`/`invoice_id` use `null` when absent. Follow each field's rule.
- **Per-schema enum labels differ** (e.g. `sensor_vendor_only` vs `sensor_only`).
  Always copy enums from the task's own `answer_template.json`.
- **Tier needs meeting-interest even when not output.** The simple trade-show
  schema outputs `priority_tier` but not `interest_score`; you still must fetch
  `meeting_interest` to compute the tier.
- **Sort every list.** Many points are lost to unsorted or wrongly-sorted arrays.
- **One JSON object, no prose.**
