# HarborCRM Task Solving Skill

## Overview

HarborCRM tasks require querying a shared API and producing JSON outputs that conform to task-specific schemas. Tasks fall into three categories: **event post-handoff reconciliation**, **tradeshow prospecting**, and **import batch cleaning**. Each train task uses a different schema and business rules, so always read the prompt and template for the specific task.

## API Access

- Base URL is provided by the runner or environment file (e.g., `http://34.46.77.124:8001`).
- Query only endpoints explicitly mentioned in the task prompt.
- The CRM data (`/api/crm/accounts`, `/api/crm/contacts`, `/api/crm/opportunities`, `/api/crm/campaign_members`) is shared across tasks and must always be cross-referenced.

## Task Categories

### 1. Event Post-Event CRM Handoff (e.g., NeuralOps, EdgeAI Field Day)

**Endpoints to query:**
- `/api/events/<event_id>`
- `/api/events/<event_id>/orders`
- `/api/events/<event_id>/badges`
- `/api/events/<event_id>/sponsor_packages`
- `/api/finance/invoices?event_id=<event_id>`
- `/api/crm/accounts`, `/api/crm/contacts`, `/api/crm/opportunities`, `/api/crm/campaign_members?event_id=<event_id>`

**Key rules:**
- **Sponsor statuses**: Report active sponsors only. Map invoice status to controlled values:
  - `paid_deferred` → `paid_deferred`
  - `open` → `open_invoice`
  - No invoice + proposal → `proposal_only`
  - Canceled sponsors are **excluded** from sponsor_statuses.
- **Open balance**: For open invoices, calculate as `amount - paid_amount`.
- **Follow-up dates**: Compute from event `end_date`:
  - lead_due_date = end_date + `followup_days_after_end`
  - sponsor_finance_due_date = end_date + `sponsor_followup_days_after_end`
- **Excluded badge records**: Include in `excluded_records` with controlled reasons:
  - Sponsor attendees (badge_type = sponsor or ticket contacts from active sponsor packages) → `sponsor_attendee`
  - Canceled/inactive sponsor records → `inactive_sponsor_record`
  - Non-business badges (student, press) → `non_business_badge`
  - Attendees from CRM-disqualified accounts → `existing_disqualified`
  - Missing critical contact info (no email AND no phone, or effectively unusable) → `missing_contact`
- **Qualified non-sponsor leads**: Attendees with business badges from non-sponsor, non-disqualified accounts. Include even if email is empty (phone may suffice). If a badge lacks both email and phone, exclude as `missing_contact`.
- **Lead opportunity amount**: The event's `lead_opportunity_amount` is a **per-lead** amount. Total pipeline = count_of_qualified_leads × lead_opportunity_amount.
- **Campaign member reconciliation**: Existing campaign members must be reconciled with badge scans. Update `registered_sponsor` → `attended_sponsor` for confirmed sponsors who attended. Create campaign members for new qualified leads. `subject_key` in campaign_member_actions is typically `badge_id` for badge-based entries and `contact_id` for existing contacts without badges.
- **Badge-only contacts**: List normalized contact facts for qualified non-sponsor leads that have no CRM account/contact. Empty email string is allowed if no email was supplied.

### 2. Tradeshow Prospecting (e.g., MarineSense, AquaFarm)

**Endpoints to query:**
- `/api/tradeshows/<show_id>/exhibitors`
- `/api/tradeshows/<show_id>/meeting_interest`
- `/api/crm/accounts`, `/api/crm/contacts`
- `/api/policies`

**Key rules:**
- **Qualified leads**: Exhibitors that make or OEM-build target platforms (AUV, ROV, Underwater Camera). Use exhibitor descriptions to determine platform coverage.
- **Excluded exhibitors**: Distributors/resellers, pure service providers, sensor-only vendors, research-only. Map to controlled exclusion reasons:
  - `distributor_only`
  - `service_only`
  - `sensor_only` / `sensor_vendor_only`
  - `research_only`
- **Platform assignment**: Derive from description keywords (e.g., "ROV" → ROV, "underwater camera manufacturer" → Underwater Camera). If an ROV has camera arrays, count both ROV and Underwater Camera if both are distinct platform offerings.
- **Ranking** (when required): Sort by:
  1. Demo request (true first)
  2. Meeting interest score descending
  3. Broader platform coverage (more platforms first)
  4. Company name ascending
- **Priority tiers** (when specified):
  - `A`: demo-requested with score ≥ 90 → $120,000
  - `B`: demo-requested with score ≥ 80 → $90,000
  - `C`: all other qualified leads → $50,000
- **CRM overlap**: If an exhibitor's `crm_account_id` exists in CRM, action is `update_existing`; otherwise `create_account`.
- **Sorting**: Excluded exhibitors sorted by `company_name` ascending. Qualified exhibitors sorted by ranking rules.

### 3. Import Batch Cleaning (e.g., fall_webinar_import)

**Endpoints to query:**
- `/api/import_batches/<batch_id>/raw_contacts`
- `/api/import_batches/<batch_id>/suppression`
- `/api/import_batches`
- `/api/crm/accounts`, `/api/crm/contacts`

**Key rules:**
- **Deduplication**: Deduplicate by **normalized email** (not email+phone). When timestamps tie, prefer earlier captured_at; if still tied, prefer primary source (e.g., `webinar_form` over `partner_upload`). The winning row's company name should be used as-is (do not normalize/merge variant company names).
- **Suppression**: Remove rows matching the suppression list by email or normalized phone. Mark reason as `suppressed`.
- **Unusable rows**: Remove rows with blank/whitespace email AND no phone, or effectively no contactable info. Mark reason as `missing_contact`.
- **Normalization**:
  - Email: lowercase, trim whitespace
  - Phone: digits only; keep country code if present (e.g., `+1 (415) 555-0101` → `14155550101`; `(415) 555-0101` → `4155550101`)
- **CRM action for clean contacts**:
  - If account exists in CRM: `update_existing`
  - If account does not exist: `create_account`
  - Existing contact_ids should be populated when known; null otherwise
- **Import action totals**: Sum the `crm_action` values of surviving `clean_contacts`. Suppressed/removed rows do not contribute to action totals (they are removed, not imported).
- **Campaign member import count**: Count of all surviving clean contacts.

## Common Pitfalls

1. **Not reading the task-specific template**: Each task has a unique schema. Do not reuse answers across tasks.
2. **Incorrect sponsor exclusion**: Canceled sponsors are excluded from `sponsor_statuses` but their contacts may still appear in `excluded_records`.
3. **Wrong open balance calculation**: Use `amount - paid_amount`, not `deferred_amount`.
4. **Missing badge-only leads**: Empty email does not automatically exclude a lead if phone is present.
5. **Wrong deduplication key**: Email-only deduplication is standard; do not require phone match.
6. **Lead opportunity math**: For event handoffs, multiply per-lead amount by number of qualified leads.
7. **Subject key inconsistency**: In campaign member reconciliation, use `badge_id` for badge-based actions and `contact_id` for existing contacts without badges.
8. **Follow-up date calculation**: Always add days_after_end to the event's `end_date`.
9. **Platform coverage**: Be generous with platform assignment based on exhibitor descriptions; an ROV with camera arrays may count as both ROV and Underwater Camera if the description supports it.
10. **Sorting violations**: Pay close attention to template ordering rules (ascending by name, badge_id, rank, etc.).
