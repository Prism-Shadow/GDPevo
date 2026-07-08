# HarborCRM Task Solving Skill

## Overview

This skill captures recurring patterns for solving HarborCRM CRM-integration tasks. Tasks involve querying a local HarborCRM API, applying business rules, and producing structured JSON output matching a provided answer template.

## Environment Setup

- The HarborCRM API is available after running `env/setup.sh`.
- Base URL is supplied by the runner; default for local runs is `http://127.0.0.1:8067`.
- Only query endpoint paths and entity IDs explicitly named in the task prompt. Do not use global list/index endpoints to discover IDs.

## Core Workflow

1. **Read the prompt** to identify the task type (event reconciliation, trade-show prospecting, batch import cleanup, etc.).
2. **Read the answer template** (`input/payloads/answer_template.json`) to understand the exact required schema, keys, enums, and sort orders.
3. **Query only the explicitly named endpoints** from the prompt.
4. **Apply business rules** (qualification, exclusion, CRM action mapping, opportunity sizing, normalization).
5. **Sort all lists** exactly as specified in the template or prompt.
6. **Produce JSON only** — no explanatory prose outside the JSON.

---

## Task-Type Patterns

### 1. Post-Event Reconciliation (e.g., `neuralops_2026`, `edgeai_field_2026`)

**Data to fetch:**
- Event details, orders, badges, sponsor packages
- Finance invoices (filtered by `event_id`)
- CRM accounts, contacts, opportunities, campaign members
- Policies (for exclusion/qualification rules)

**Key business rules:**
- **Sponsor statuses** use controlled values: `paid_deferred`, `open_invoice`, `proposal_only` (and sometimes `not_sponsor`).
- **Revenue totals** are integer USD. For `open_invoice`, report the open balance separately.
- **Exclude** from lead handoff: sponsor attendees, inactive/canceled sponsors, non-business badges, existing disqualified CRM accounts.
- **Qualified leads** are non-sponsor accounts with business badges that are not already disqualified.
- **Opportunity amount** comes from the event's configured lead opportunity amount (e.g., 42000, 18000).
- **Follow-up due dates** are derived from the event date (e.g., leads due 5 business days after event end; sponsor finance due 3 business days after).
- **CRM action counts** summarize implied account/contact/campaign-member creates and updates.

**Sorting conventions:**
- `sponsor_statuses`: by `account_name` ascending
- `qualified_lead_accounts`: by `account_name` ascending
- `excluded_records`: by `company_name` ascending, then `contact_name` ascending
- `badge_decisions`: by `badge_id` ascending
- `campaign_member_actions`: by `subject_key` ascending
- `badge_only_contacts`: by `company_name` ascending

**Normalization rules:**
- Email: lowercase, trimmed; empty string when missing
- Phone: digits only; empty string when missing

### 2. Trade-Show Prospecting (e.g., `aquafarm_robotics_2026`, `marinesense_2026`)

**Data to fetch:**
- Trade-show details (`/api/tradeshows/{show_id}`)
- Exhibitors (`/api/tradeshows/{show_id}/exhibitors`)
- Meeting interest (`/api/tradeshows/{show_id}/meeting_interest`)
- CRM accounts, policies

**Qualification rules:**
- Qualified leads are exhibitors that **make or OEM-build** robotics or underwater-camera platforms covered by the prospecting policy.
- **Exclude** distributors, service-only providers, sensor-only vendors, research-only entities.
- Existing CRM accounts should be marked for `update_existing`; new qualified exhibitors for `create_account`.
- Excluded exhibitors remain visible with a controlled `exclusion_reason` and `crm_action: no_import`.

**Ranking rules (prospecting):**
1. Demo request first (`requested_demo: true` before `false`)
2. Meeting interest score descending
3. Broader platform coverage (more platforms = higher rank)
4. Company name ascending (tie-breaker)

**Opportunity sizing by priority tier:**
- `A`: USD 120000 — demo-requested qualified leads with score ≥ 90
- `B`: USD 90000 — demo-requested qualified leads with score ≥ 80
- `C`: USD 50000 — all other qualified leads

**Platform enums:** `AUV`, `ROV`, `Underwater Camera`
- Platforms list must be sorted in the order: `AUV`, `ROV`, `Underwater Camera`

**Summary fields:**
- `qualified_lead_count`, `excluded_count`
- `existing_crm_overlap_count` and `existing_crm_overlap_account_ids` (sorted ascending)
- `total_estimated_opportunity_usd` (sum of lead opportunities)
- `platform_coverage_counts`: counts of leads covering each platform

**Excluded exhibitor schema:**
- Required: `company_id`, `company_name`, `relationship_type`, `exclusion_reason`, `crm_action`
- `relationship_type` enums: `distributor`, `service_provider`, `sensor_vendor`, `research`
- `exclusion_reason` enums: `distributor_only`, `service_only`, `sensor_only`, `research_only`
- Sort excluded exhibitors by `company_name` ascending

### 3. Batch Import Cleanup (e.g., `fall_webinar_import`)

**Data to fetch:**
- Import batch raw contacts (`/api/import_batches/{batch_id}/raw_contacts`)
- Suppression list (`/api/import_batches/{batch_id}/suppression`)
- CRM accounts and contacts (for deduplication and existing record matching)
- Policies

**Business rules:**
- **Remove duplicates** by email (keep the latest/most complete record as winner).
- **Remove suppressed** emails/domains.
- **Remove unusable** rows (missing contact name, missing email, etc.).
- **Match** remaining rows to existing CRM accounts by company name/email and to existing contacts by email.
- **CRM action** per row: `create_account`, `update_existing`, `no_import`, `suppress`.
- If a row matches an existing account but not an existing contact, action is `update_existing` for account and `create_contact` for contact.

**Output sections:**
- `clean_contacts`: import-ready rows with `clean_contact_id`, `source_row_id`, company/contact info, `crm_action`, `existing_account_id`, `existing_contact_id`
- `duplicate_summary`: count and details of duplicates removed (winner/removed mapping)
- `removal_summary`: count and reasons for all removed rows (`duplicate`, `suppressed`, `missing_contact`, etc.)
- `import_action_totals`: aggregate counts per `crm_action`
- `campaign_member_import_count`: number of clean contacts that will become campaign members

---

## Universal Conventions

### JSON Output Rules
- Return **JSON only** — no markdown, no prose, no comments.
- Match the answer template schema exactly; include all required keys.
- Use `null` (not missing keys) for nullable fields unless the template says otherwise.
- Currency amounts are always **integer USD**.
- Dates are **ISO 8601** (`YYYY-MM-DD`) unless the template specifies otherwise.

### Sorting Rules
- Always sort lists as specified in the template or prompt.
- Common sort keys: `account_name` ascending, `company_name` ascending, `badge_id` ascending, `subject_key` ascending, `rank` ascending (1-based contiguous).
- For tie-breakers, fall back to secondary keys (e.g., `contact_name`, `company_id`).

### CRM Actions
Common `crm_action` values across tasks:
- `create_account` — new account + contact
- `update_existing` — update matched account
- `create_contact` — new contact on existing account
- `no_import` — excluded or suppressed
- `no_action` — already correct state
- `add_campaign_member` / `create` / `update` — campaign member actions

### Exclusion Reasons
Common exclusion reasons:
- `sponsor_attendee`
- `non_business_badge`
- `existing_disqualified`
- `missing_contact`
- `distributor_only`
- `service_only`
- `sensor_only` / `sensor_vendor_only`
- `research_only`

### API Query Discipline
- Only call endpoints explicitly listed in the prompt.
- Do not call global list endpoints (`/api/events`, `/api/tradeshows`, etc.) to discover IDs.
- Use query parameters exactly as specified (e.g., `?event_id=neuralops_2026`).

---

## Common Pitfalls

1. **Missing sort order** — Many lists have strict ordering requirements. Check the template.
2. **Wrong opportunity amounts** — Use the event-specific lead opportunity amount, not a hardcoded default.
3. **Platform list order** — In trade-show tasks, platforms must be ordered `AUV`, `ROV`, `Underwater Camera`.
4. **Duplicate handling** — In batch imports, deduplicate by email and report the winner/removed mapping precisely.
5. **Normalization** — Emails must be lowercase and trimmed; phones digits-only.
6. **Null vs missing key** — Use `null` for fields like `crm_account_id` when there is no match; do not omit the key.
7. **Contiguous ranks** — Ranks must be 1-based and contiguous (no gaps after filtering).
8. **Open invoice balance** — For sponsors with `open_invoice`, calculate `open_balance = package_amount - paid_amount`.
