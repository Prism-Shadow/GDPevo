# HarborCRM CRM-Marketing Solver Skill

> **Purpose:** Teach a future solver to produce correct JSON for unseen HarborCRM test tasks.
> The environment is a read-only JSON API at `<remote-env-url>`.
> Always return ONE JSON object matching the task's `answer_template.json`. No prose outside JSON.

---

## 0. API Cheat Sheet

Base URL: `<remote-env-url>`  (call with `curl -s`, pipe to `jq` or `python3 -m json.tool`)

| Endpoint | Used For |
|---|---|
| `GET /api/events` | List all events (key fields: `lead_opportunity_amount`, `followup_days_after_end`, `sponsor_followup_days_after_end`, `end_date`) |
| `GET /api/events/{event_id}` | Single event detail |
| `GET /api/events/{event_id}/orders` | Sponsor orders (= same data as sponsor_packages) |
| `GET /api/events/{event_id}/sponsor_packages` | Sponsor packages: `account_id`, `amount`, `order_status`, `package_level`, `ticket_contacts` |
| `GET /api/events/{event_id}/badges` | Badge scans: `badge_id`, `badge_type`, `company_name`, `contact_name`, `email`, `phone` |
| `GET /api/finance/invoices?event_id={event_id}` | Invoices: `status` (`paid_deferred`/`open`), `paid_amount`, `amount`, `invoice_id` |
| `GET /api/crm/accounts` | CRM accounts: `account_id`, `name`, `domain`, `status` (`customer`/`prospect`/`disqualified`), `disqualified_reason` |
| `GET /api/crm/contacts` | CRM contacts: `contact_id`, `account_id`, `name`, `email`, `phone`, `opted_out` |
| `GET /api/crm/opportunities` | CRM opportunities: `account_id`, `amount`, `stage`, `event_id` |
| `GET /api/crm/campaign_members?event_id={event_id}` | Campaign members: `account_id`, `contact_id`, `status` (`attended_sponsor`/`registered_sponsor`/`attended`/...) |
| `GET /api/tradeshows` | List trade shows: `show_id`, `name`, `start_date`, `end_date` |
| `GET /api/tradeshows/{show_id}/exhibitors` | Exhibitors: `company_id`, `company_name`, `description`, `booth`, `country`, `website`, `crm_account_id` |
| `GET /api/tradeshows/{show_id}/meeting_interest` | Meeting interest: `company_name`, `interest_score`, `requested_demo`, `notes` |
| `GET /api/import_batches` | List import batches: `batch_id`, `campaign_code`, `received_at` |
| `GET /api/import_batches/{batch_id}/raw_contacts` | Raw contacts: `row_id`, `company_name`, `contact_name`, `email`, `phone`, `source_name`, `captured_at` |
| `GET /api/import_batches/{batch_id}/suppression` | Suppression list: `email`, `phone`, `reason` |
| `GET /api/policies` | Policy metadata: platform enums, sponsor status enums |

The dataset is deterministic (seed 41001). Events, tradeshows, and batches you have NOT seen in training will appear in test tasks — the same conventions apply.

---

## 1. Identify the Task Type

Read the prompt and answer template. Map to a workflow:

| Signal in prompt / template | Workflow |
|---|---|
| `event_id`, `sponsor_statuses`, `badge_decisions` or `qualified_lead_accounts`, `excluded_records` or `exclusion_counts` | **A — Event Reconciliation** |
| `show_id`, `qualified_exhibitors` or `ranked_leads`, `excluded_near_misses` or `excluded_exhibitors`, `platforms` | **B — Tradeshow Prospecting** |
| `batch_id`, `raw_contacts`, `clean_contacts`, `duplicate_summary`, `removal_summary`, `import_action_totals` | **C — Import Batch Cleaning** |

Some event tasks (train_001) output `sponsor_statuses` + `qualified_lead_accounts` + `excluded_records` + `follow_up` + `crm_action_counts`.
Other event tasks (train_004) output a more granular `badge_decisions` + `campaign_member_actions` + `opportunity_summary` + `sponsor_followup` + `badge_only_contacts` + `exclusion_counts`.
**Always follow the exact field names and structure in the task's answer template.**

---

## 2. Normalization Rules (Cross-Cutting — All Workflows)

### NAN_EMAIL(email_string)
1. Strip leading/trailing whitespace.
2. Lowercase the entire string.
3. Result = normalized email (may be `""` if input was blank/whitespace-only).

### NAN_PHONE(phone_string)
1. Extract ONLY digit characters `0-9`; discard everything else (`+`, `(`, `)`, `-`, `.`, spaces, letters).
2. Concatenate the digits.
3. Result = normalized phone (may be `""` if no digits present).

**Examples:**
| Raw input | Normalized |
|---|---|
| `" Dana.Ruiz@HelioWare.example "` | `"dana.ruiz@helioware.example"` |
| `"KENJI.SATO@monarchfoods.example"` | `"kenji.sato@monarchfoods.example"` |
| `"+1 (415) 555-0101"` | `"14155550101"` |
| `"415-555-0188"` | `"4155550188"` |
| `"1.206.555.0177"` | `"12065550177"` |
| `"206.555.0150"` | `"2065550150"` |
| `""` or `" "` | `""` |

### NAN_DOMAIN(normalized_email)
- Extract the portion after `@`. E.g. `"dana.ruiz@helioware.example"` → `"helioware.example"`.
- If email is empty → no domain.

---

## 3. Workflow A — Event Reconciliation

**Inputs:** event details, sponsor_packages, badges, invoices, CRM accounts/contacts/opportunities, campaign_members.

### Checklist

#### A1. Fetch all event data
```
GET /api/events/{event_id}
GET /api/events/{event_id}/sponsor_packages   (or /orders — same data)
GET /api/events/{event_id}/badges
GET /api/finance/invoices?event_id={event_id}
GET /api/crm/campaign_members?event_id={event_id}
GET /api/crm/accounts
GET /api/crm/contacts
GET /api/crm/opportunities    (filter by event_id if needed)
```

#### A2. Compute due dates
- `lead_due_date` = `event.end_date` + `event.followup_days_after_end` days (simple calendar addition).
- `sponsor_due_date` = `event.end_date` + `event.sponsor_followup_days_after_end` days.
- Format: `YYYY-MM-DD`.

**Verification (train data):**
| Event | end_date | lead_days | lead_due | sponsor_days | sponsor_due |
|---|---|---|---|---|---|
| neuralops_2026 | 2026-09-16 | 7 | 2026-09-23 | 3 | 2026-09-19 |
| edgeai_field_2026 | 2026-11-05 | 5 | 2026-11-10 | 2 | 2026-11-07 |

#### A3. Determine sponsor statuses

For each entry in `sponsor_packages`:

| sponsor_packages `order_status` | Invoice lookup (by account_id + event_id) | → sponsor_status |
|---|---|---|
| `confirmed` | invoice `status` == `paid_deferred` | `paid_deferred` |
| `confirmed` | invoice `status` == `open` | `open_invoice` |
| `proposal_sent` | no invoice | `proposal_only` |
| `canceled` | (any) | **EXCLUDE** from sponsor_statuses (inactive sponsor) |

**Per-sponsor fields (train_001 schema — `sponsor_statuses` array):**
| Field | Source |
|---|---|
| `account_id` | sponsor_packages.account_id |
| `account_name` | sponsor_packages.account_name |
| `status` | from decision table above |
| `package_amount` | sponsor_packages.amount (= invoice.amount if invoice exists) |
| `invoice_id` | invoice.invoice_id, or `null` if no invoice |
| `paid_amount` | invoice.paid_amount, or `0` if no invoice |
| `open_balance` | `max(0, package_amount - paid_amount)`; `0` if no invoice |

Sort `sponsor_statuses` by `account_name` ascending.

**Per-sponsor fields (train_004 schema — `sponsor_statuses` array):**
| Field | Source |
|---|---|
| `account_id` | sponsor_packages.account_id |
| `account_name` | sponsor_packages.account_name |
| `sponsor_status` | from decision table above |
| `amount_usd` | sponsor_packages.amount (integer) |

#### A4. Compute sponsor revenue totals (train_001 schema)

| Revenue field | Computation |
|---|---|
| `paid_deferred` | Σ package_amount for all sponsors with status `paid_deferred` |
| `open_invoice` | Σ package_amount for all sponsors with status `open_invoice` |
| `proposal_only` | Σ package_amount for all sponsors with status `proposal_only` |
| `open_invoice_balance` | Σ (package_amount − paid_amount) for sponsors with status `open_invoice` ONLY |

#### A5. Identify sponsor finance follow-up targets

- Include sponsors with status `open_invoice` or `proposal_only` (NOT `paid_deferred` — they are fully paid).
- `sponsor_finance_accounts` / `unpaid_sponsor_account_names`: sorted list of these account names ascending.
- `unpaid_sponsor_total_usd` (train_004): Σ of their `amount_usd`.
- `sponsor_finance_task_count` / followup: count of these sponsors.
- Due date: `sponsor_due_date` from A2.

#### A6. Classify every badge

For each badge in `badges`, determine the badge's CRM account and contact status:

1. **Is the badge's company an ACTIVE sponsor?**
   Check if there is a sponsor_package with `order_status` ∈ {`confirmed`, `proposal_sent`} whose `account_name` matches the badge's `company_name`.
   → If YES: classification = `sponsor_attendee`

2. **Is the badge's company a disqualified CRM account?**
   Check CRM accounts: is there an account whose `name` matches the badge's `company_name` AND `status` == `disqualified`?
   → If YES: classification = `existing_disqualified`

3. **Is the badge type non-business?**
   badge_type ∈ {`student`, `press`, ...} (anything that is NOT `attendee` or `sponsor`)?
   → If YES: classification = `excluded` / `non_business_badge`

4. **Is the badge's company a canceled sponsor (but NOT disqualified in CRM)?**
   sponsor_package exists with `order_status` == `canceled` for this company, and CRM account is NOT disqualified.
   → If YES: classification = `inactive_sponsor_record`

5. **Otherwise** → classification = `qualified_non_sponsor_lead`

**Classification priority (first match wins):**
```
1. active_sponsor          → sponsor_attendee
2. CRM disqualified         → existing_disqualified
3. non-business badge type  → non_business_badge
4. canceled sponsor         → inactive_sponsor_record
5. none of the above        → qualified_non_sponsor_lead
```

> **Note on priority:** A company can be BOTH a canceled sponsor AND disqualified in CRM.
> The CRM-disqualified check (priority 2) fires BEFORE the canceled-sponsor check (priority 4),
> so the reason is `existing_disqualified`. Verified: Northstar Sensors (canceled sponsor + disqualified CRM → `existing_disqualified`).

#### A7. Build excluded_records (train_001 schema)

Sources of excluded records:
1. **Badges:** Every badge that is NOT `qualified_non_sponsor_lead` becomes an excluded record.
2. **Active sponsors with NO badge for that company:** Add the first `ticket_contact` from the sponsor_package as `sponsor_attendee`.
   - If a sponsor company already has a badge, the badge contact covers it — do NOT add additional ticket_contacts.
   - If a sponsor company has a campaign member but no badge, the campaign member contact covers it — do NOT add ticket_contacts.

**Building excluded record entry:**
| Field | Source |
|---|---|
| `company_name` | Badge company_name (or CRM account name for campaign-member-based) |
| `contact_name` | Badge contact_name (or CRM contact name / first ticket_contact) |
| `reason` | From classification (sponsor_attendee / existing_disqualified / non_business_badge / inactive_sponsor_record) |

Sort by `company_name` ascending, then `contact_name` ascending.

#### A8. Build badge_decisions (train_004 schema)

For EACH badge (sorted by `badge_id` ascending):

| Field | Source |
|---|---|
| `badge_id` | badge.badge_id |
| `company_name` | badge.company_name |
| `contact_name` | badge.contact_name |
| `classification` | `sponsor_attendee` / `qualified_non_sponsor_lead` / `excluded` |
| `crm_action` | See decision table A9 |
| `exclusion_reason` | `sponsor_attendee` / `non_business_badge` / `existing_disqualified` / `missing_contact` / `null` |

#### A9. Determine CRM action for each badge (train_004)

First, determine CRM existence:
- **Account exists:** match badge's normalized email domain to CRM account `domain` field. If email empty OR domain not found → account does NOT exist.
  (Alternative: match by company name to CRM account `name`.)
- **Contact exists:** match badge's normalized email to CRM contact `email` field (exact match).
- **Campaign member exists:** check if there is an existing campaign_member for this event where account_id matches the (existing) CRM account AND contact_id matches the (existing) CRM contact.

| Account exists? | Contact exists? | Campaign member exists? | → crm_action (train_004) |
|---|---|---|---|
| No | No | No | `create_account_contact_campaign_member` |
| Yes | No | No | `create_contact_campaign_member` |
| Yes | Yes | No | `add_campaign_member` |
| Yes | Yes | Yes | `no_action` |
|—(excluded badge)—|—|—| `no_import` |

#### A10. Build campaign_member_actions (train_004)

Include ALL campaign members for the event (existing + new badge-based):

1. **Existing campaign members** (from `/api/crm/campaign_members?event_id=...`):
   - `subject_key`: `{account_id}:{contact_id}` (e.g. `acct_rivet_ai:cont_sofia_meyer`)
   - `action`: `no_action`
   - `target_status`: keep existing status (`attended_sponsor` / `registered_sponsor` / `attended`)

2. **New campaign members from badges** (badges that are NOT excluded via non_business_badge):
   - **Qualified non-sponsor lead badges** (with `crm_action` = `create_account_contact_campaign_member` or above):
     - `subject_key`: `badge:{badge_id}`
     - `action`: `create`
     - `target_status`: `attended`
   - **Sponsor attendee badges needing new contact/campaign member** (badge classified as `sponsor_attendee`, CRM action = `create_contact_campaign_member`):
     - `subject_key`: `badge:{badge_id}`
     - `action`: `create`
     - `target_status`: `attended_sponsor`
   - Note: sponsor badges where everything already exists (`no_action`) do NOT produce a new campaign member entry beyond the existing one.

3. **Excluded badges (non_business_badge):** no campaign member action (`no_import`). NOT listed.

Sort `campaign_member_actions` by `subject_key` ascending.

#### A11. Build badge_only_contacts (train_004)

Badges where the contact does NOT already exist in CRM (i.e., contact needs creation), EXCLUDING non-business badges.

For each qualifying badge:
| Field | Source |
|---|---|
| `company_name` | badge.company_name |
| `contact_name` | badge.contact_name |
| `normalized_email` | NAN_EMAIL(badge.email) — `""` if empty |
| `normalized_phone` | NAN_PHONE(badge.phone) — `""` if empty |

Sort by `company_name` ascending.

#### A12. Build qualified_lead_accounts (train_001 schema)

For each badge classified as `qualified_non_sponsor_lead`:

| Field | Source / Rule |
|---|---|
| `account_name` | badge.company_name |
| `account_id` | CRM account_id if account exists (by domain match), else `null` |
| `primary_contact` | badge.contact_name |
| `normalized_email` | NAN_EMAIL(badge.email) |
| `normalized_phone` | NAN_PHONE(badge.phone) |
| `crm_account_action` | `update_existing` if CRM account exists, else `create_account` |
| `crm_contact_action` | `update_existing` if CRM contact email matches, else `create_contact` |
| `campaign_member_action` | `add_campaign_member` (always — these are new leads) |
| `opportunity_amount` | `event.lead_opportunity_amount` (same for all qualified leads) |

Sort `qualified_lead_accounts` by `account_name` ascending.

#### A13. Compute opportunity / pipeline totals

| Schema field | Computation |
|---|---|
| `lead_pipeline_total` (train_001) | `event.lead_opportunity_amount` × qualified_lead_count |
| `lead_opportunity_amount_usd` (train_004) | `event.lead_opportunity_amount` |
| `open_opportunity_total_usd` (train_004) | `event.lead_opportunity_amount` × qualified_lead_count |
| `open_opportunity_count` (train_004) | qualified_lead_count |
| `qualified_non_sponsor_account_names` (train_004) | sorted list of qualified lead account names ascending |

#### A14. Compute CRM action counts (train_001 schema)

Count across ALL qualified_lead_accounts:
| Field | Rule |
|---|---|
| `accounts_create` | count where crm_account_action == `create_account` |
| `accounts_update` | count where crm_account_action == `update_existing` |
| `contacts_create` | count where crm_contact_action == `create_contact` |
| `contacts_update` | count where crm_contact_action == `update_existing` |
| `campaign_members_create` | count of qualified leads (all get new campaign members) |
| `campaign_members_update` | 0 (qualified leads don't have existing campaign members) |

#### A15. Compute exclusion_counts (train_004 schema)

Count badges by exclusion_reason:
| Field | Count of badges with reason... |
|---|---|
| `sponsor_attendee` | badges classified as sponsor_attendee |
| `non_business_badge` | badges with non-business type |
| `existing_disqualified` | badges whose company is disqualified in CRM |
| `missing_contact` | badges with no usable contact (empty email AND empty phone) |

#### A16. Build follow_up section (train_001 schema)

| Field | Value |
|---|---|
| `lead_due_date` | end_date + followup_days_after_end |
| `lead_task_count` | number of qualified_lead_accounts |
| `sponsor_finance_due_date` | end_date + sponsor_followup_days_after_end |
| `sponsor_finance_task_count` | number of sponsors needing finance follow-up (open_invoice + proposal_only) |
| `sponsor_finance_accounts` | sorted list of sponsor account names (open_invoice + proposal_only) ascending |

#### A17. Final assembly and sort verification

- Verify ALL sort orders match the template requirements.
- Verify ALL enum values match the template's allowed_values.
- Verify ALL required keys are present.
- Output ONE JSON object. No explanatory prose.

---

## 4. Workflow B — Tradeshow Prospecting

**Inputs:** tradeshow exhibitors, meeting_interest, CRM accounts, policies.

### Checklist

#### B1. Fetch all data
```
GET /api/tradeshows/{show_id}/exhibitors
GET /api/tradeshows/{show_id}/meeting_interest
GET /api/crm/accounts
GET /api/policies
```

#### B2. Classify each exhibitor (qualification)

Read the exhibitor `description` field. The key question: **does the company MANUFACTURE/BUILD target underwater platforms, or is it only adjacent?**

### PLATFORM EXTRACTION

Scan the description for platform keywords:

| Keyword pattern in description | → Platform enum |
|---|---|
| `AUV` or `AUVs` (autonomous underwater vehicle) | `AUV` |
| `ROV` or `ROVs` (remotely operated vehicle) | `ROV` |
| `underwater camera`, `camera module`, `camera array`, `camera system`, `camera maker`, `camera manufacturer` | `Underwater Camera` |

Platforms are listed in **enum order**: `AUV`, `ROV`, `Underwater Camera`.

### QUALIFICATION DECISION TABLE

| Description indicates... | Qualified? | relationship_type | exclusion_reason |
|---|---|---|---|
| Company **builds/manufactures/OEM-builds** target platforms (AUV, ROV, underwater camera) | YES | — | — |
| Company is a **distributor / reseller / dealer / sales agent** for others' platforms | NO | `distributor` | `distributor_only` |
| Company provides **services / consulting / analytics / rentals** using others' platforms | NO | `service_provider` | `service_only` |
| Company **only makes sensors** (no platforms, sensor-only vendor) | NO | `sensor_vendor` | `sensor_vendor_only` or `sensor_only` (per template enum) |
| Company is **research-only** (academic, lab, non-commercial) | NO | `research` | `research_only` |
| Company is **not in the target market** at all (no relevance to underwater platforms) | NO | — | `not_target_market` (if in template enum) |

> **CAUTION:** The exact exclusion_reason enum string varies by task template.
> Train_002 template uses `sensor_vendor_only`; train_005 template uses `sensor_only`.
> **Always copy the enum value from the specific answer template.**
> If the description mentions "no hardware manufacturing" → `service_provider` / `service_only`.

**Description analysis examples (generalized):**
| Description excerpt | Inference |
|---|---|
| "Builds compact AUVs and... ROVs with OEM payload bays" | Builds AUV + ROV → qualified, platforms [AUV, ROV] |
| "Designs rugged underwater camera modules" | Builds underwater cameras → qualified, [Underwater Camera] |
| "Distributor... does not manufacture platforms" | Distributor → excluded, distributor_only |
| "Sensor-only... probes for integration by platform partners" | Sensor vendor → excluded |
| "Consulting team that operates rented ROVs" | Service provider → excluded, service_only |
| "Analytics dashboard... no hardware manufacturing" | Service provider → excluded, service_only |
| "Regional reseller for imported... ROVs and... cameras" | Distributor → excluded, distributor_only |

#### B3. Determine priority tier (from meeting_interest)

Join qualified exhibitors with meeting_interest by `company_name`.

### PRIORITY TIER DECISION TABLE

| Condition | → tier |
|---|---|
| `requested_demo` == `true` AND `interest_score` >= 90 | `A` |
| `requested_demo` == `true` AND `interest_score` >= 80 | `B` |
| All other qualified leads | `C` |

This rule is used by BOTH train_002 (where only the tier is output) and train_005 (where demo/score/tier are all output).

#### B4. Determine CRM overlap (tradeshow)

For each qualified exhibitor, check the `crm_account_id` field from the exhibitor data:
- If `crm_account_id` is NOT null → the exhibitor already has a CRM account → `crm_action` = `update_existing`.
- If `crm_account_id` IS null → `crm_action` = `create_account`.

### CRM CREATE-VS-UPDATE TABLE (Tradeshow)

| Exhibitor `crm_account_id` | → crm_action | → crm_account_id (output) |
|---|---|---|
| Non-null (e.g. `"acct_reefworks"`) | `update_existing` | the account_id value |
| `null` | `create_account` | `null` |

`existing_crm_overlap_count` = number of qualified exhibitors with non-null crm_account_id.
`existing_crm_overlap_account_ids` = sorted list of these account_ids ascending.

#### B5. Opportunity sizing (train_005 schema)

### OPPORTUNITY SIZE BY TIER

| Priority tier | → opportunity_estimate_usd |
|---|---|
| A | 120000 |
| B | 90000 |
| C | 50000 |

#### B6. Rank qualified leads (train_005 schema)

Sort qualified leads by this multi-key ordering:

1. `requested_demo` == `true` BEFORE `false`
2. `interest_score` DESCENDING (higher score first)
3. Broader platform coverage (more platforms = higher rank; count of platforms DESC)
4. `company_name` ASCENDING (alphabetical tiebreaker)

Assign ranks 1, 2, 3, ... (1-based, contiguous).

#### B7. Compute aggregate counts

### AGGREGATE COUNTS TABLE

| Field | Computation |
|---|---|
| `qualified_total` / `qualified_lead_count` | number of qualified exhibitors |
| `excluded_near_misses_total` / `excluded_count` | number of excluded exhibitors |
| `platform_counts` / `platform_coverage_counts` | For each platform enum (AUV, ROV, Underwater Camera): count qualified exhibitors that have that platform. A single exhibitor with multiple platforms is counted in each. |
| `priority_counts` | For tiers A, B, C: count qualified exhibitors with that tier |
| `total_estimated_opportunity_usd` | Σ opportunity_estimate_usd across all qualified leads |

#### B8. Build output arrays

**qualified_exhibitors (train_002 schema):** sorted by `company_name` ascending.
Fields: `company_id`, `company_name`, `platforms` (enum order), `priority_tier`, `booth`, `country`, `website`.

**ranked_leads (train_005 schema):** sorted by rank ascending (per B6).
Fields: `rank`, `company_id`, `company_name`, `booth`, `country`, `website`, `platforms` (enum order), `crm_account_id`, `crm_action`, `requested_demo`, `interest_score`, `priority_tier`, `opportunity_estimate_usd`.

**excluded_near_misses (train_002):** sorted by `company_name` ascending.
Fields: `company_id`, `company_name`, `exclusion_reason`.

**excluded_exhibitors (train_005):** sorted by `company_name` ascending.
Fields: `company_id`, `company_name`, `relationship_type`, `exclusion_reason`, `crm_action` (always `no_import`).

#### B9. Top-level fields
- `show_id`: from the prompt/task.
- `campaign` (train_002 only): from the prompt text (e.g. `"oem_dissolved_oxygen_sensor"`). This is not in the API.

#### B10. Final assembly and sort verification
- Verify ALL sort orders match template requirements.
- Verify ALL enum values match template allowed_values.
- Output ONE JSON object.

---

## 5. Workflow C — Import Batch Cleaning

**Inputs:** raw_contacts, suppression list, CRM accounts/contacts, policies.

### Checklist

#### C1. Fetch all data
```
GET /api/import_batches/{batch_id}/raw_contacts
GET /api/import_batches/{batch_id}/suppression
GET /api/crm/accounts
GET /api/crm/contacts
GET /api/policies
```

Also `GET /api/import_batches` to get `campaign_code` for the batch.

#### C2. Normalize all raw contacts

For each row in `raw_contacts`:
- `norm_email` = NAN_EMAIL(row.email)
- `norm_phone` = NAN_PHONE(row.phone)

#### C3. Classify each row — REMOVAL DECISION TABLE

Process in this priority order (first match wins; each row gets exactly ONE outcome):

### ROW PROCESSING PIPELINE

```
For each raw_contact row:

  STEP 1 — Missing contact check
    IF norm_email == "" AND norm_phone == "":
        → reason = "missing_contact", crm_action = "no_import"
        → SKIP remaining steps

  STEP 2 — Suppression check
    IF norm_email matches any suppression entry's email
       OR norm_phone matches any suppression entry's phone:
        → reason = "suppressed", crm_action = "suppress"
        → SKIP remaining steps

  STEP 3 — Duplicate check (among rows that passed steps 1-2)
    Group by norm_email (only non-empty emails).
    Within each group:
        Winner = row with latest captured_at (ISO timestamp comparison).
        Tiebreaker: highest row_id (lexicographic string comparison).
    Losers:
        → reason = "duplicate", crm_action = "no_import"

  STEP 4 — Survivor
    Rows that pass all checks → clean contact
        → crm_action = "create_account" or "update_existing" (see C5)
```

> **Important:** The duplicate check groups by normalized email. Two rows with the same raw email spelled differently (e.g. `"Dana.Ruiz@HelioWare.example "` vs `"dana.ruiz@helioware.example"`) ARE duplicates because they normalize to the same value.
>
> Rows with empty emails cannot be duplicates (no key to group by).

**Duplicate winner verification (train_003):**
| Duplicate key | Rows | Winner | Why |
|---|---|---|---|
| `email:dana.ruiz@helioware.example` | fw_001 (2026-11-10T14:02), fw_002 (2026-11-14T09:05) | fw_002 | Later captured_at |
| `email:evan.blake@quartzfoods.example` | fw_003 (2026-11-10T15:20), fw_008 (2026-11-10T15:20) | fw_008 | Same timestamp → higher row_id |

#### C4. Build duplicate_summary

| Field | Value |
|---|---|
| `duplicate_removed_count` | total number of loser rows across all duplicate groups |
| `duplicate_keys` | one entry per duplicate group |

Each `duplicate_keys` entry:
| Field | Value |
|---|---|
| `key` | `"email:{normalized_email}"` |
| `winner_row_id` | the winning row's row_id |
| `removed_row_ids` | list of losing row_ids |

Sort `duplicate_keys` by `key` ascending.

#### C5. Determine CRM action for surviving clean contacts

For each surviving row:

### CRM ACCOUNT MATCHING (Import Batch)
1. Extract domain from norm_email: the part after `@`.
2. Search CRM accounts for one whose `domain` field matches this domain.
3. If found → `crm_action` = `update_existing`, `existing_account_id` = matched account_id.
4. If NOT found (or email is empty) → `crm_action` = `create_account`, `existing_account_id` = `null`.

### CRM CONTACT MATCHING (Import Batch)
1. Search CRM contacts for one whose `email` field exactly matches the row's norm_email.
2. If found → `existing_contact_id` = matched contact_id.
3. If NOT found → `existing_contact_id` = `null`.

> **Note:** The CRM contact match is by EXACT email match, not by name or domain.
> A contact person may exist in CRM under a different email — that does NOT count as a match.
> (E.g., "old.hana@riverbendchem.example" in CRM vs "hana.park@riverbendchem.example" in the raw contact → existing_contact_id = null.)

#### C6. Build clean_contacts array

For each surviving row (sorted by `clean_contact_id` ascending):

| Field | Value |
|---|---|
| `clean_contact_id` | winner's `row_id` |
| `source_row_id` | winner's `row_id` |
| `company_name` | winner's raw `company_name` (NOT normalized — taken as-is) |
| `contact_name` | winner's raw `contact_name` |
| `email` | norm_email (normalized), or `""` |
| `phone` | norm_phone (normalized digits-only), or `""` |
| `source_name` | winner's raw `source_name` |
| `captured_at` | winner's raw `captured_at` (ISO timestamp as-is) |
| `crm_action` | `create_account` or `update_existing` (from C5) |
| `existing_account_id` | matched CRM account_id, or `null` |
| `existing_contact_id` | matched CRM contact_id, or `null` |

> **Company name is NOT normalized.** If the winning row spells it "HelioWare Mfg." but CRM has "HelioWare Manufacturing", the output keeps "HelioWare Mfg." as-is.

#### C7. Build removal_summary

| Field | Value |
|---|---|
| `unusable_removed_count` | count of rows with reason `duplicate` + `missing_contact` |
| `suppressed_removed_count` | count of rows with reason `suppressed` |
| `removed_rows` | list of all removed rows |

Each `removed_rows` entry:
| Field | Value |
|---|---|
| `row_id` | the row's row_id |
| `reason` | `duplicate` / `missing_contact` / `suppressed` |

Sort `removed_rows` by `row_id` ascending.

> **unusable_removed_count** = duplicates + missing_contact (data-quality failures).
> **suppressed_removed_count** = compliance suppressions (opt-out, privacy, role account).

#### C8. Build import_action_totals

| Key | Count |
|---|---|
| `create_account` | surviving rows with crm_action = `create_account` |
| `update_existing` | surviving rows with crm_action = `update_existing` |
| `no_import` | rows removed as `duplicate` + `missing_contact` |
| `suppress` | rows removed as `suppressed` |

**Sanity check:** `create_account + update_existing + no_import + suppress` = total raw_contacts count.

#### C9. campaign_member_import_count

= number of surviving clean contacts (= `create_account` + `update_existing` count).
All surviving contacts become campaign members for the batch campaign.

#### C10. Top-level fields

| Field | Source |
|---|---|
| `batch_id` | from the prompt/task |
| `campaign_code` | from `GET /api/import_batches` → find matching batch → `campaign_code` field |

#### C11. Final assembly and sort verification
- `clean_contacts` sorted by `clean_contact_id` ascending
- `duplicate_summary.duplicate_keys` sorted by `key` ascending
- `removal_summary.removed_rows` sorted by `row_id` ascending
- All enum values match template
- Output ONE JSON object.

---

## 6. Sorting Rules Reference

| Array | Sort key | Direction |
|---|---|---|
| `sponsor_statuses` | `account_name` | ascending |
| `qualified_lead_accounts` | `account_name` | ascending |
| `excluded_records` (train_001) | `company_name` then `contact_name` | ascending, ascending |
| `badge_decisions` (train_004) | `badge_id` | ascending |
| `campaign_member_actions` (train_004) | `subject_key` | ascending |
| `badge_only_contacts` (train_004) | `company_name` | ascending |
| `qualified_exhibitors` (train_002) | `company_name` | ascending |
| `excluded_near_misses` (train_002) | `company_name` | ascending |
| `ranked_leads` (train_005) | `rank` | ascending |
| `excluded_exhibitors` (train_005) | `company_name` | ascending |
| `clean_contacts` (train_003) | `clean_contact_id` | ascending |
| `duplicate_keys` (train_003) | `key` | ascending |
| `removed_rows` (train_003) | `row_id` | ascending |
| `qualified_non_sponsor_account_names` | (string sort) | ascending |
| `unpaid_sponsor_account_names` | (string sort) | ascending |
| `sponsor_finance_accounts` | (string sort) | ascending |
| `existing_crm_overlap_account_ids` | (string sort) | ascending |

---

## 7. Enum Reference

### Sponsor status enums
- `paid_deferred` — invoice fully paid, revenue deferred
- `open_invoice` — invoice issued, not fully paid
- `proposal_only` — sponsor package proposal_sent, no invoice
- `not_sponsor` — (train_004 template) account in context but not a sponsor

### Badge classification enums
- `sponsor_attendee` — company is an active sponsor
- `qualified_non_sponsor_lead` — non-sponsor, not excluded, potential lead
- `excluded` — badge excluded (non-business, disqualified, etc.)

### Exclusion reason enums (event tasks)
- `sponsor_attendee`
- `non_business_badge`
- `existing_disqualified`
- `inactive_sponsor_record`
- `missing_contact` (train_004 template)

### Platform enums (tradeshow tasks)
1. `AUV`
2. `ROV`
3. `Underwater Camera`
(Always listed in this order.)

### Priority tier enums
- `A` — demo requested AND score ≥ 90
- `B` — demo requested AND score ≥ 80
- `C` — all other qualified leads

### Exclusion reason enums (tradeshow tasks)
- `distributor_only`
- `service_only`
- `sensor_vendor_only` (train_002 template) / `sensor_only` (train_005 template) — **check template!**
- `research_only`
- `not_target_market` (train_002 template only)

### Relationship type enums (train_005)
- `distributor`
- `service_provider`
- `sensor_vendor`
- `research`

### CRM action enums
**Tradeshow (train_005):** `create_account`, `update_existing`, `no_import`
**Event badge (train_004):** `create_account_contact_campaign_member`, `create_contact_campaign_member`, `add_campaign_member`, `update_campaign_member`, `no_action`, `no_import`
**Import batch (train_003):** `create_account`, `update_existing`, `no_import`, `suppress`
**Campaign member (train_001):** `add_campaign_member`
**Campaign member action (train_004):** `create`, `update`, `no_action`, `no_import`

### Campaign member target_status (train_004)
- `attended_sponsor` — sponsor attendee badge, new campaign member
- `registered_sponsor` — existing campaign member status (pre-registered sponsor)
- `attended` — qualified non-sponsor lead, new campaign member
- `excluded` — excluded badge (rarely used as target_status)

### Removal reason enums (import batch)
- `duplicate`
- `missing_contact`
- `suppressed`

### Source name enums (import batch)
`badge_scan`, `sponsor_form`, `partner_upload`, `webinar_form`, `exhibitor_form`, `manual_upload`

---

## 8. Critical Pitfalls & Edge Cases

1. **Exclusion reason enums vary by template.** `sensor_vendor_only` (train_002) vs `sensor_only` (train_005). Always copy from the answer template's allowed_values.

2. **Company name is NOT normalized in import batch clean_contacts.** Keep the raw spelling from the winning row.

3. **Duplicate winner = LATEST captured_at, then HIGHEST row_id.** Not first occurrence.

4. **CRM contact match is by EXACT email, not by name.** A person in CRM with a different email is NOT a match.

5. **Suppression matches by email OR phone.** A row is suppressed if EITHER field matches a suppression entry.

6. **Missing contact = BOTH email AND phone are empty** after normalization. A row with phone but no email is NOT missing_contact.

7. **`not_sponsor` sponsor_status** may appear for accounts with CRM opportunities for the event but no sponsor package — include in sponsor_statuses if the schema requires it.

8. **Sponsor finance follow-up excludes `paid_deferred` sponsors** (fully paid). Only `open_invoice` and `proposal_only` sponsors need follow-up.

9. **`open_invoice_balance`** is computed ONLY for `open_invoice` sponsors, as `package_amount - paid_amount`. Proposal_only sponsors have `open_balance = 0` (no invoice exists).

10. **Badge classification priority:** active_sponsor > existing_disqualified > non_business_badge > inactive_sponsor_record > qualified_lead. A company that is BOTH a canceled sponsor AND CRM-disqualified gets reason `existing_disqualified`.

11. **Campaign member actions include ALL existing campaign members** (with `no_action`), not just new ones. Existing sponsors who didn't badge-scan still appear (e.g., SignalForge/Owen Grant in train_004 was registered_sponsor with no badge).

12. **`subject_key` format:** existing CRM contacts use `{account_id}:{contact_id}`; new badge contacts use `badge:{badge_id}`.

13. **Tradeshow CRM matching** uses the exhibitor's `crm_account_id` field directly (not email domain matching, since exhibitors may not have emails).

14. **Event task `lead_opportunity_amount`** is per-lead, and ALL qualified leads get the SAME amount (from the event record). Don't invent per-lead amounts.

15. **All monetary values are integers** (USD, no decimals).

16. **The `campaign` string in tradeshow tasks** (e.g., `oem_dissolved_oxygen_sensor`) comes from the PROMPT, not the API. The tradeshow endpoint has no campaign field.

17. **Active sponsor = order_status in {confirmed, proposal_sent}.** Canceled = inactive = excluded from sponsor_statuses.

18. **Unusable_removed_count = duplicates + missing_contact.** Suppressed is tracked separately. The import_action_totals `no_import` bucket covers both duplicates and missing_contact.

19. **Always produce a complete JSON object.** Missing keys, wrong sort order, or wrong enum strings cause failures. Verify against the template before finalizing.

20. **Integer USD only.** No floats, no string-formatted numbers.
