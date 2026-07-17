# HarborCRM Task Solving Skill

## Environment & API Basics

- **Base URL**: `http://34.46.77.124:8001` (from `environment_access.md`; do not use localhost).
- Only query endpoint paths and entity IDs **explicitly named in the task prompt**. Do not call global list/index endpoints to discover IDs.
- Read the task prompt carefully to identify which endpoints to call and which entity IDs are relevant.

## Core Workflow

1. Read the task `prompt.txt` to understand the business objective, relevant API endpoints, and required output schema.
2. Read `input/payloads/answer_template.json` to understand the exact required JSON structure, field types, enums, and ordering rules.
3. Query only the explicitly named API endpoints to gather data.
4. Apply business rules from the prompt (qualification criteria, exclusion reasons, ranking logic, CRM actions, opportunity sizing, deduplication rules, etc.).
5. Produce a single JSON object conforming exactly to the answer template. No prose outside the JSON.

## Common Task Patterns

### 1. Trade Show / Exhibitor Prospecting

**Typical endpoints**:
- `/api/tradeshows/{show_id}`
- `/api/tradeshows/{show_id}/exhibitors`
- `/api/tradeshows/{show_id}/meeting_interest`
- `/api/crm/accounts`
- `/api/crm/contacts`
- `/api/policies`

**Key business rules**:
- **Qualification**: Exhibitors that make or OEM-build robotics or underwater-camera platforms (per prospecting policy) are qualified. Distributors, service providers, sensor-only vendors, and research-only entities are excluded.
- **CRM overlap**: Check existing CRM accounts. If a qualified exhibitor already exists in CRM, set `crm_action: "update_existing"` and populate `crm_account_id`. Otherwise, `crm_action: "create_account"` with `crm_account_id: null`.
- **Exclusions**: Excluded exhibitors get `crm_action: "no_import"` with a controlled `exclusion_reason` (e.g., `distributor_only`, `service_only`, `sensor_only`, `research_only`).
- **Ranking**: Sort qualified leads by:
  1. `requested_demo` (true first)
  2. `interest_score` descending
  3. Broader platform coverage (more platforms first)
  4. `company_name` ascending
- **Opportunity sizing** (priority tiers):
  - `A` = USD 120,000 (demo-requested qualified leads with score ≥ 90)
  - `B` = USD 90,000 (demo-requested qualified leads with score ≥ 80)
  - `C` = USD 50,000 (all other qualified leads)
- **Platform ordering**: Platforms arrays must be ordered: `AUV`, `ROV`, `Underwater Camera`.
- **Summary counts**: `platform_coverage_counts` must include keys `AUV`, `ROV`, `Underwater Camera` (integer counts across all qualified leads).
- **Existing CRM overlap**: `existing_crm_overlap_account_ids` sorted ascending. `existing_crm_overlap_count` is the length of that list.
- **Total opportunity**: Sum of all `opportunity_estimate_usd` values for ranked leads.

### 2. Import Batch Cleaning (Contact Deduplication & Suppression)

**Typical endpoints**:
- `/api/import_batches/{batch_id}`
- `/api/import_batches/{batch_id}/raw_contacts`
- `/api/import_batches/{batch_id}/suppression`
- `/api/crm/accounts`
- `/api/crm/contacts`
- `/api/policies`

**Key business rules**:
- **Deduplication**: Remove duplicate contacts within the batch (typically by normalized email). Keep the "best" row as winner (e.g., most complete data, earliest capture, or partner upload preferred over manual). Record `duplicate_removed_count` and `duplicate_keys` with `winner_row_id` and `removed_row_ids`.
- **Suppression**: Remove contacts on the suppression list. Record `suppressed_removed_count`.
- **Unusable rows**: Remove rows missing required contact fields (e.g., missing contact name). Record `unusable_removed_count`.
- **CRM matching**: Match surviving rows against existing CRM accounts/contacts by email or company name.
  - If matched to existing account: `crm_action: "update_existing"`, populate `existing_account_id`.
  - If matched to existing contact: populate `existing_contact_id`.
  - Otherwise: `crm_action: "create_account"`.
- **Clean contacts**: Sort by `clean_contact_id` ascending (typically use the winning `source_row_id`).
  - `email`: normalized (lowercase, trimmed); empty string if none.
  - `phone`: normalized digits-only; empty string if none.
  - `source_name`: enum from allowed values (badge_scan, sponsor_form, partner_upload, webinar_form, exhibitor_form, manual_upload).
- **Import action totals**: Object with keys `create_account`, `update_existing`, `no_import`, `suppress` — all integers summing to the total raw rows.
- **Campaign member import count**: Number of surviving cleaned contacts that should be imported as campaign members (typically `create_account` + `update_existing`).
- **Removal summary**: `removed_rows` sorted by `row_id` ascending, each with `row_id` and `reason` (duplicate, missing_contact, suppressed).

### 3. Event Reconciliation (Sponsors + Badge Scans + Campaign Members)

**Typical endpoints**:
- Event details, sponsor orders, badge scans, finance invoices, CRM accounts, contacts, opportunities, campaign members, policies.

**Key business rules**:
- **Sponsor statuses**: Reconcile sponsor orders against finance invoices. Possible statuses: `paid_deferred`, `open_invoice`, `proposal_only`, `not_sponsor`. Sort by `account_name` ascending.
- **Badge decisions**: For each badge scan, classify:
  - `sponsor_attendee` → `crm_action: "no_action"` or `"create_contact_campaign_member"` depending on whether the sponsor account already exists in CRM.
  - `qualified_non_sponsor_lead` → `crm_action: "create_account_contact_campaign_member"`.
  - `excluded` → `crm_action: "no_import"` with reason (e.g., `non_business_badge`, `missing_contact`, `existing_disqualified`).
  - Sort by `badge_id` ascending.
- **Campaign member actions**: One entry per relevant subject (existing CRM contact or badge). Sort by `subject_key` ascending.
  - `action`: `create`, `update`, `no_action`, `no_import`.
  - `target_status`: `attended_sponsor`, `registered_sponsor`, `attended`, `excluded`.
- **Opportunity summary**:
  - `qualified_non_sponsor_account_names`: sorted ascending.
  - `lead_opportunity_amount_usd`: fixed amount per qualified non-sponsor lead (e.g., USD 18,000 each).
  - `open_opportunity_total_usd` and `open_opportunity_count`: from CRM opportunities linked to sponsors.
- **Sponsor followup**:
  - `unpaid_sponsor_account_names`: sorted ascending (sponsors with `open_invoice` or `proposal_only`).
  - `unpaid_sponsor_total_usd`: sum of unpaid sponsor amounts.
  - `followup_due_date`: from event data.
- **Badge-only contacts**: Normalized contacts for badge-only leads (not already in CRM). Sort by `company_name` ascending. Email lowercase trimmed; phone digits-only.
- **Exclusion counts**: Object with keys `sponsor_attendee`, `non_business_badge`, `existing_disqualified`, `missing_contact` — all integers.

## Output Conventions

- **Always produce a single JSON object**. No markdown code fences, no explanatory text.
- **Strictly follow the answer template** for the specific task. Templates vary significantly across task types.
- **Ordering matters**: Most lists have explicit sort rules (ascending by ID, name, rank, badge_id, subject_key, etc.). Pay close attention to the template's `ordering` fields.
- **Enum values**: Use only the allowed enum values specified in the template. Do not invent new values.
- **Nulls vs empty strings**: Use `null` only where the template specifies `"string or null"`. Use empty strings `""` for missing normalized emails/phones when the template expects strings.
- **Date format**: Use `YYYY-MM-DD` for dates unless the template specifies ISO timestamps.
- **Currency**: All USD amounts are integers (no decimals).
- **Counts**: All counts are integers.
- **Platform arrays**: When multiple platforms are present, always order them as `AUV`, `ROV`, `Underwater Camera`.

## Common Pitfalls

- **Do not add extra fields** beyond those declared in the answer template.
- **Do not omit required keys**, even if the value is `0` or `null`.
- **Do not call discovery endpoints** (e.g., `/api/tradeshows` without a specific ID). Only use endpoints and IDs named in the prompt.
- **Do not assume task similarity**: Even within the same domain (trade shows), different tasks may have different output schemas, ranking rules, and field requirements. Always read the specific prompt and template.
- **Check CRM overlap carefully**: An exhibitor may match an existing account by name, website, or contact email. The prompt may specify how to match.
- **Handle ties consistently**: When ranking, if all primary sort keys are equal, fall back to `company_name` ascending.
