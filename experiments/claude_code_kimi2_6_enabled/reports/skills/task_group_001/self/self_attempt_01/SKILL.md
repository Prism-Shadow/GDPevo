# HarborCRM Task Solving Skill

## Overview

HarborCRM tasks involve reconciling data from multiple API endpoints (events/tradeshows, CRM, finance, policies) into structured JSON outputs. Tasks fall into three main categories:

1. **Event/Trade Show Reconciliation** (train_001, train_004) — Post-event sponsor finance and lead handoff
2. **Trade Show Prospecting** (train_002, train_005) — Exhibitor qualification and ranking for campaigns
3. **Import Batch Preparation** (train_003) — CRM import batch deduplication, suppression, and cleaning

## Environment & API Access

- **Base URL**: Use only `GDPEVO_ENV_BASE_URL=http://34.46.77.124:8001`. Do NOT use localhost unless the remote URL itself points there.
- **Authentication**: Typically none required for these public API endpoints.
- **Request method**: GET for all listed endpoints.
- **Do not** call global list/index endpoints to discover IDs. Only query endpoints and entity IDs explicitly named in the task prompt.

## Common API Endpoint Patterns

### Events / Trade Shows
- `GET /api/events/{event_id}` — Event metadata (name, dates, lead opportunity amount, follow-up due dates)
- `GET /api/events/{event_id}/orders` — Sponsor orders
- `GET /api/events/{event_id}/badges` — Badge scans/attendees
- `GET /api/events/{event_id}/sponsor_packages` — Available sponsor tiers
- `GET /api/tradeshows` — List of trade shows
- `GET /api/tradeshows/{show_id}/exhibitors` — Exhibitor list with platforms, booth, country, website
- `GET /api/tradeshows/{show_id}/meeting_interest` — Interest scores and demo requests

### CRM
- `GET /api/crm/accounts` — Existing accounts (match by company name normalization)
- `GET /api/crm/contacts` — Existing contacts (match by email/phone normalization)
- `GET /api/crm/opportunities` — Existing opportunities
- `GET /api/crm/campaign_members?event_id={event_id}` — Campaign membership status

### Finance
- `GET /api/finance/invoices?event_id={event_id}` — Invoice status, paid amounts, open balances

### Import Batches
- `GET /api/import_batches` — List batches
- `GET /api/import_batches/{batch_id}/raw_contacts` — Raw import rows
- `GET /api/import_batches/{batch_id}/suppression` — Suppression list

### Policies
- `GET /api/policies` — Campaign policies defining qualification criteria, platform enums, priority tiers, exclusion rules. **Always fetch and read policies** — they contain the ground truth for qualification logic.

## Core Business Rules

### 1. Always Read Policies First
The `/api/policies` endpoint contains the authoritative rules for:
- What platforms/technologies qualify (e.g., AUV, ROV, Underwater Camera)
- What relationship types are excluded (distributor, service_provider, sensor_vendor, research)
- Priority tier thresholds and opportunity sizing
- Exclusion reasons and their controlled vocabulary

### 2. Sponsor vs. Non-Sponsor Separation
- **Sponsors** are handled via finance reconciliation (invoice status, open balances, follow-up dates)
- **Non-sponsor leads** are evaluated for CRM import qualification
- Never treat a sponsor attendee as a qualified non-sponsor lead
- Inactive/canceled sponsor records are excluded

### 3. CRM Account Matching
- Match exhibitors/import records to existing CRM accounts by **normalized company name** (case-insensitive, whitespace-normalized)
- If a matching account exists, set `crm_action` to `update_existing` (or equivalent)
- If no match exists, set `crm_action` to `create_account`
- If disqualified/excluded, set `crm_action` to `no_import`

### 4. Contact Normalization
- **Email**: lowercase, trimmed. Empty string when missing.
- **Phone**: digits only. Empty string when missing.
- Match existing contacts by normalized email or normalized phone.

### 5. Exclusion Rules (Common Patterns)
Records are excluded for these reasons (controlled vocabulary varies slightly by task):
- `sponsor_attendee` — Part of a sponsoring company
- `non_business_badge` — Personal/non-commercial attendee
- `existing_disqualified` — Already in CRM as disqualified
- `missing_contact` — No usable contact information
- `distributor_only` / `service_only` / `sensor_only` / `research_only` — Not a manufacturer/OEM
- `not_target_market` — Outside campaign scope

### 6. Finance Status Values
Controlled values for sponsor finance status:
- `paid_deferred` — Paid but revenue deferred
- `open_invoice` — Has unpaid invoice (report open balance separately)
- `proposal_only` — Sponsorship proposed but not contracted

### 7. Opportunity Sizing (Prospecting Tasks)
Priority tiers map to fixed USD amounts:
- **Tier A**: USD 120,000
- **Tier B**: USD 90,000
- **Tier C**: USD 50,000

Tier assignment rules (from train_005):
- **A**: Demo-requested qualified leads with interest score ≥ 90
- **B**: Demo-requested qualified leads with interest score ≥ 80
- **C**: All other qualified leads

## Sorting & Ordering Rules

Always follow the exact ordering specified in the answer template:

| Field / List | Sort Key | Direction |
|-------------|----------|-----------|
| `sponsor_statuses` | `account_name` | ascending |
| `qualified_lead_accounts` | `account_name` | ascending |
| `excluded_records` | `company_name`, then `contact_name` | ascending |
| `qualified_exhibitors` | `company_name` | ascending |
| `excluded_near_misses` | `company_name` | ascending |
| `excluded_exhibitors` | `company_name` | ascending |
| `ranked_leads` | rank (1-based contiguous) | ascending |
| `badge_decisions` | `badge_id` | ascending |
| `campaign_member_actions` | `subject_key` | ascending |
| `badge_only_contacts` | `company_name` | ascending |
| `clean_contacts` | `clean_contact_id` | ascending |
| `duplicate_keys` | `key` | ascending |
| `removed_rows` | `row_id` | ascending |
| `existing_crm_overlap_account_ids` | account ID | ascending |
| `platforms` enum | Fixed: AUV, ROV, Underwater Camera | — |
| `qualified_non_sponsor_account_names` | name | ascending |
| `unpaid_sponsor_account_names` | name | ascending |

## Ranking Logic (Prospecting Tasks)

For ranked lead lists, the sort order is:
1. **Demo requested** (true before false)
2. **Interest score** descending (higher first)
3. **Broader platform coverage** (more platforms first)
4. **Company name** ascending (alphabetical tie-breaker)

Ranks must be **1-based and contiguous** (no gaps).

## Import Batch Cleaning Rules (train_003 Pattern)

1. **Deduplicate** by key (typically normalized email or company+contact). Keep the row with the earliest `captured_at` or latest based on policy. Record winner and removed row IDs.
2. **Suppress** rows matching the suppression list (by email or other key).
3. **Remove unusable** rows missing required contact fields.
4. **CRM action assignment**: For each surviving row, check against existing CRM accounts/contacts and assign `create_account`, `update_existing`, `no_import`, or `suppress`.
5. **Campaign member count**: Count surviving cleaned contacts that are importable (not `no_import` or `suppress`).

## Output Conventions

- Return **exactly one JSON object**. No markdown code fences, no explanatory prose outside the JSON.
- Use only the keys declared in the answer template. Do not add extra fields.
- Use `null` (not empty string) for nullable fields unless the template specifies empty string.
- Dates: `YYYY-MM-DD` format.
- Currency: integer USD (no decimals).
- Counts: integers.
- Booleans: JSON `true`/`false` (not strings).
- Enum values: use exactly the allowed strings (case-sensitive).

## Common Pitfalls

1. **Forgetting to fetch policies** — The policies endpoint contains critical qualification logic that cannot be inferred from the prompt alone.
2. **Wrong base URL** — Always use the remote URL from `environment_access.md`, not localhost.
3. **Incorrect sorting** — Many tasks have multi-key sorts. Read the template carefully.
4. **Non-contiguous ranks** — After filtering, recompute ranks to be 1-based contiguous.
5. **Case-sensitive matching** — Company names and emails must be normalized before matching.
6. **Including sponsors as leads** — Sponsor attendees are never qualified non-sponsor leads.
7. **Missing open balance** — For `open_invoice` sponsors, report both the package amount and the open balance.
8. **Platform ordering** — The enum order AUV → ROV → Underwater Camera is fixed; do not alphabetize.
9. **Duplicate handling** — In import batches, removed duplicates still count toward removal totals and should be listed with reason `"duplicate"`.
10. **Campaign member count** — Only count rows that will actually be imported (exclude `no_import` and `suppress`).

## Workflow Checklist

1. Read `MANIFEST.md` and `environment_access.md`
2. Read the task prompt and answer template
3. Fetch all relevant API endpoints (do not skip policies)
4. Normalize all text fields for matching (company names, emails, phones)
5. Apply qualification/exclusion rules per policies
6. Compute derived fields (opportunity amounts, ranks, counts)
7. Sort all lists per template rules
8. Validate output against template (required keys, enum values, types)
9. Emit pure JSON only
